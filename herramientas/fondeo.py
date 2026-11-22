"""Laboratorio de FONDEO del compañero. No lo puedes modificar (la máquina lo restaura antes de guardar).

USO RÁPIDO (en Python, desde la raíz del repositorio):
    import sys; sys.path.insert(0, "agente/herramientas"); from fondeo import *
    m   = minutos("spx")               # velas de 1 minuto de OANDA: dict de arrays t (s UTC), open, high, low, close, volume
    h   = velas(m, "1h")               # DataFrame OHLCV (vale "15min", "1h", "4h"...); índice en UTC, como OANDA/TradingView
    ind = indicadores(h)               # dict: atr (Wilder 14), cmf (20), estado (>=1 = Flujo verde), ses (día de mercado), bpd
    base = sistema_actual("spx")       # operaciones del sistema de Pe (la LÍNEA BASE a batir); viernes=True = cierre del viernes
    cd  = caida("nas")                 # segundo motor del robot: compra en el −2,4 % desde el máximo de 20 días (medio riesgo)
    ops = operar(m, h, entradas)       # tus entradas -> operaciones simuladas minuto a minuto (costes incluidos)
    az  = azar(m, ops)                 # las mismas operaciones en momentos al azar (mismo tamaño de stop): el azar justo
    print(resumen(ops, az))            # N, operaciones/año, R medio, t, acierto, por tramos y frente al azar
    print(tabla_retos({"spx": o1, "nas": o2}, "ftmo1", [0.01, 0.0125]))   # retos simulados con las reglas de cada firma
    print(tabla_retos(plan_completo(), "5ers", ["colchon", 0.02]))        # el plan entero de Pe en The5ers

ENTRADAS para operar(): lista de dicts {"i": índice de la vela de h a cuyo CIERRE se entra, "stop": precio}.
    Opcional: "tp1" y "tp2" (en R; por defecto 0.75 y 2.0), "dir" (1 compra, -1 venta), "peso" (tamaño relativo, 1 = normal).
    Se entra a la apertura del minuto siguiente al cierre de la vela. Mitad sale en tp1; la otra mitad pasa a breakeven y busca tp2.
    Máximo 10 días. Una sola operación abierta a la vez por activo (las entradas que llegan con una abierta se saltan).
    Costes: 1,5 pb por ida y vuelta + financiación del 6 % anual. Si stop y objetivo caen en el mismo minuto, cuenta el stop.
    viernes=True: cierre obligatorio el viernes a las 16:30 de Nueva York y sin entradas hasta el domingo.

FIRMAS en tabla_retos(): "ftmo1" (10 %, diario 3 %, máximo 10 % que sube con el mayor cierre diario, regla del mejor día 50 %),
    "ftmo2" (10 % + 5 %, diario 5 %, máximo 10 % fijo), "fn_instant" (cobro a +5 %, sin diario, 6 % que sube y se para en el
    saldo inicial), "ftp_instant" (igual con diario 6 %), "5ers" (The5ers Hyper Growth: 10 %, máximo 6 % fijo, y al −3 % en el
    día NO quema: pausa el día y sigue al siguiente). Un intento empezando cada mes. "≤12 m" solo cuenta intentos con 12
    meses de datos. Riesgo "colchon" = el riesgo cambia cada día con el saldo: (saldo + 6 %) / 3, entre 0,5 % y 4 % (F-017).

EL PLAN DE Pe (11-nov-2026), tal cual lo lleva el robot PeVR_Fondeo v2.2 en 5 gráficos:
    · mínimo + Flujo verde (sistema_actual) en S&P, Nasdaq y EUR/JPY, a riesgo entero;
    · caída desde el máximo (caida) en Nasdaq y S&P, a MEDIO riesgo cada una (peso 0,5).
    plan_completo() devuelve las cinco listas de operaciones. Flujo verde = CMF(20) > 0,025, como el indicador y el robot
    (hasta la v3 este archivo usaba 0,05 por error: las cifras viejas de la línea base no son comparables).

ACTIVOS: spx, nas, us30, us2000, de30, eurjpy, eurusd, xau (descarga con descargar(["us2000"]) si no están).
LÍNEA DE COMANDOS: python agente/herramientas/fondeo.py --descargar [--activos spx,nas] [--base]
    (variables: FONDEO_ACTIVOS, FONDEO_CAIDA, FONDEO_RIESGO, FONDEO_VIERNES, FONDEO_SOMBRA_DESDE)
"""
import os, sys, glob, json, calendar, datetime as dt, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd

DATOS = os.environ.get("FONDEO_DATOS", "/tmp/agente/fondeo")
ACTIVOS = {"spx": "OANDA_SPX500USD_US-SPX-500", "nas": "OANDA_NAS100USD_US-Nas-100", "us30": "OANDA_US30USD_US-Wall-St-30",
           "us2000": "OANDA_US2000USD_US-Russ-2000", "de30": "OANDA_DE30EUR_Germany-30", "eurjpy": "OANDA_EURJPY_EURJPY",
           "eurusd": "OANDA_EURUSD_EURUSD", "xau": "OANDA_XAUUSD_Gold"}
COSTE, FIN, MAXMIN = 1.5e-4, 0.06, 10 * 1440
TRAMOS = (("2003-15", 2003, 2015), ("2016-22", 2016, 2022), ("2023-26", 2023, 2026))
TROZOS = (("aprender ≤2018", 2003, 2018), ("comprobar 2019-22", 2019, 2022), ("caja 2023-hoy", 2023, 2100))

# ───────────────────────────── datos ─────────────────────────────
def _url(repo, y, mth):
    last = calendar.monthrange(y, mth)[1]
    return f"https://raw.githubusercontent.com/bunqii/{repo}/main/1/{repo}_1_{y}-{mth:02d}-01_to_{y}-{mth:02d}-{last:02d}.parquet"

def descargar(activos=("spx", "nas"), desde=2003):
    """Baja los ficheros mensuales que falten (y siempre los dos últimos meses, que se actualizan a diario)."""
    hoy = dt.date.today(); res = {}
    for a in activos:
        repo = ACTIVOS[a]; carpeta = os.path.join(DATOS, repo); os.makedirs(carpeta, exist_ok=True)
        f_faltan = os.path.join(carpeta, "_no_existen.json")
        faltan = set(json.load(open(f_faltan))) if os.path.exists(f_faltan) else set()
        tareas = []
        for y in range(desde, hoy.year + 1):
            for mth in range(1, 13):
                if (y, mth) > (hoy.year, hoy.month): break
                url = _url(repo, y, mth); dest = os.path.join(carpeta, url.rsplit("/", 1)[1])
                reciente = (hoy.year - y) * 12 + hoy.month - mth <= 1
                if url in faltan and not reciente: continue
                if os.path.exists(dest) and os.path.getsize(dest) > 0 and not reciente: continue
                tareas.append((url, dest, reciente))
        def baja(t):
            url, dest, reciente = t
            for _ in range(3):
                try:
                    with urllib.request.urlopen(url, timeout=60) as r: datos = r.read()
                    open(dest + ".tmp", "wb").write(datos); os.replace(dest + ".tmp", dest); return "ok"
                except urllib.error.HTTPError as e:
                    if e.code == 404: return "404" if not reciente else "404r"
                except Exception: pass
            return "error"
        with ThreadPoolExecutor(12) as ex: rs = list(ex.map(baja, tareas))
        faltan |= {t[0] for t, r in zip(tareas, rs) if r == "404"}
        json.dump(sorted(faltan), open(f_faltan, "w"))
        n = len(glob.glob(os.path.join(carpeta, "*.parquet")))
        res[a] = dict(ficheros=n, bajados=rs.count("ok"), errores=rs.count("error"))
    return res

_CACHE = {}
def minutos(activo):
    """Velas de 1 minuto (OANDA, bunqii). Devuelve dict de arrays numpy: t (segundos UTC), open, high, low, close, volume."""
    if activo in _CACHE: return _CACHE[activo]
    fs = sorted(glob.glob(os.path.join(DATOS, ACTIVOS[activo], "*.parquet")))
    if not fs: raise FileNotFoundError(f"No hay datos de {activo}: ejecuta descargar(['{activo}'])")
    x = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True).drop_duplicates("time").sort_values("time")
    m = {k: x[k].values.astype(float) for k in ("open", "high", "low", "close", "volume")}
    m["t"] = x.time.values.astype(np.int64); _CACHE[activo] = m
    return m

def velas(m, tf="1h", quitar=500):
    """Agrupa el minuto en velas (índice UTC, como OANDA en TradingView). Quita las primeras 'quitar' velas."""
    idx = pd.to_datetime(m["t"], unit="s", utc=True)
    x = pd.DataFrame({k: m[k] for k in ("open", "high", "low", "close", "volume")}, index=idx)
    h = x.resample(tf).agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    return h.dropna(subset=["close"]).iloc[quitar:]

# ─────────────────────────── indicadores ───────────────────────────
def wilder(x, n=14):
    out = np.full(len(x), np.nan); a = np.nan
    for i, v in enumerate(x):
        if i == n - 1: a = np.nanmean(x[:n]); out[i] = a
        elif i >= n: a = a + (v - a) / n; out[i] = a
    return out

def _roll(x, n, f): return getattr(pd.Series(np.asarray(x, float)).rolling(n), f)().values

def _tendencia(src, w=20):
    y = np.asarray(src, float); k = np.arange(w)[::-1].astype(float)
    sxy = np.convolve(y, k, "valid"); sy = np.convolve(y, np.ones(w), "valid")
    sx = w * (w - 1) / 2; sxx = (w - 1) * w * (2 * w - 1) / 6
    slope = np.r_[np.full(w - 1, np.nan), (w * sxy - sx * sy) / (w * sxx - sx * sx)]
    sd = pd.Series(y).rolling(w).std(ddof=0).values
    return np.where(sd > 0, slope / np.where(sd > 0, sd, 1) * w, 0.0)

def dias_mercado(h):
    """Número de día de mercado de cada vela (la sesión empieza a las 17:00 de Nueva York)."""
    ny = h.index.tz_convert("America/New_York")
    return pd.factorize((ny + pd.Timedelta(hours=7)).normalize())[0]

def indicadores(h, lenCMF=20, umbral=0.025):
    o, hi, l, c, v = [h[k].values.astype(float) for k in ("open", "high", "low", "close", "volume")]
    pc = np.r_[c[0], c[:-1]]; atr = wilder(np.maximum(hi - l, np.maximum(abs(hi - pc), abs(l - pc))), 14)
    rng = hi - l; mfm = np.where(rng > 0, ((c - l) - (hi - c)) / np.where(rng > 0, rng, 1), 0.0); mfv = mfm * v
    vs = _roll(v, lenCMF, "sum"); ms = _roll(mfv, lenCMF, "sum"); cmf = np.where(vs > 0, ms / np.where(vs > 0, vs, 1), np.nan)
    obv = np.cumsum(np.sign(np.nan_to_num(np.diff(c, prepend=np.nan))) * v); adl = np.cumsum(mfv)
    flujo = (_tendencia(obv) + _tendencia(adl)) / 2; precio = _tendencia(c); hay = ~np.isnan(cmf)
    dist = hay & (precio > 0.5) & (flujo < -0.5) & (cmf < -umbral); acum = hay & (precio < -0.5) & (flujo > 0.5) & (cmf > umbral)
    estado = np.where(~hay, 0, np.where(dist, -2, np.where(acum, 2, np.where(cmf > umbral, 1, np.where(cmf < -umbral, -1, 0)))))
    ses = dias_mercado(h); bpd = int(np.median(pd.Series(ses).value_counts().values))
    return dict(atr=atr, cmf=cmf, estado=estado, ses=ses, bpd=bpd)

def senales_base(h, ind, D=3):
    """Señales del sistema actual: mínimo bajo el suelo de D días, mínimo de las últimas bpd velas y Flujo en verde."""
    L = h.low.values; ses = ind["ses"]; bpd = ind["bpd"]; est = ind["estado"]; n = len(L)
    ini = pd.Series(np.arange(n)).groupby(ses).first().reindex(range(ses.max() + 1)).ffill().astype(int).values
    sig = []; us = -10**9
    for t in range(max(200, bpd * D + 1), n - 1):
        a = ini[max(0, ses[t] - D)]; b = t - bpd
        if b <= a: continue
        if not (L[t] < L[a:b].min() and L[t] <= L[max(0, t - bpd + 1):t + 1].min()): continue
        if est[t] >= 1 and t - us > bpd: sig.append(t); us = t
    return sig

# ─────────────────────────── simulación ───────────────────────────
def _primero(a): return int(np.argmax(a)) if a.any() else None
def _buscar(cond, j0, fin):
    w = 256
    while True:
        j1 = min(j0 + w, fin); k = _primero(cond(j0, j1))
        if k is not None: return j0 + k
        if j1 == fin: return None
        w *= 8

def _bloqueo(m):
    if "_bloq" not in m:
        ny = pd.to_datetime(m["t"], unit="s", utc=True).tz_convert("America/New_York")
        wd = ny.dayofweek.values; hm = ny.hour.values * 60 + ny.minute.values
        b = ((wd == 4) & (hm >= 16 * 60 + 30)) | (wd == 5) | ((wd == 6) & (hm < 18 * 60))
        m["_bloq"] = b; m["_idxb"] = np.flatnonzero(b)
    return m["_bloq"], m["_idxb"]

def simular(m, j0, st, t1, t2, d=1, viernes=False):
    """Una operación desde el minuto j0 (entrada a su apertura). t1/t2 = precios de los objetivos. d = 1 compra, -1 venta."""
    T, O, H, L, C = m["t"], m["open"], m["high"], m["low"], m["close"]
    if j0 >= len(T) - 2: return None
    fin = min(j0 + MAXMIN, len(T) - 1)
    if viernes:
        b, ib = _bloqueo(m)
        if b[j0]: return None
        k = np.searchsorted(ib, j0)
        if k < len(ib): fin = min(fin, max(j0 + 1, ib[k] - 1))
    e = O[j0]; r = (e - st) * d
    if r <= 0: return None
    if (t1 - e) * d <= 0.25 * r: t1 = e + d * r
    if (t2 - t1) * d <= 0.25 * r: t2 = t1 + d * r
    if d == 1:
        cs = lambda a, z: L[a:z] <= st; ct = lambda x: (lambda a, z: H[a:z] >= x); cb = lambda a, z: L[a:z] <= e
        gap = lambda k, x: min(x, O[k])
    else:
        cs = lambda a, z: H[a:z] >= st; ct = lambda x: (lambda a, z: L[a:z] <= x); cb = lambda a, z: H[a:z] >= e
        gap = lambda k, x: max(x, O[k])
    inf = 10**12
    ks = _buscar(cs, j0, fin); k1 = _buscar(ct(t1), j0, fin)
    ks = inf if ks is None else ks; k1 = inf if k1 is None else k1
    if ks <= k1 and ks < inf: kA, xA = ks, gap(ks, st); kB, xB = ks, gap(ks, st)
    elif k1 < inf:
        kA, xA = k1, t1
        k2 = _buscar(ct(t2), k1, fin); kbe = _buscar(cb, k1 + 1, fin)
        c = [(k, x) for k, x in ((kbe, None), (k2, t2)) if k is not None]
        if c:
            kB, xB = min(c, key=lambda z: (z[0], 0 if z[1] is None else 1))
            if xB is None: xB = gap(kB, e)
        else: kB, xB = fin, C[fin]
    else: kA, xA = fin, C[fin]; kB, xB = fin, C[fin]
    dias = ((T[kA] - T[j0]) + (T[kB] - T[j0])) / 2 / 86400
    coste = e * COSTE + e * FIN * dias / 365
    return dict(t=int(T[j0]), fin_t=int(max(T[kA], T[kB])), e=e, dir=d,
                R=(d * (0.5 * (xA - e) + 0.5 * (xB - e)) - coste) / r, RA=d * (xA - e) / r, RB=d * (xB - e) / r,
                riesgo=r / e * 100, tp1R=d * (t1 - e) / r, tp2R=d * (t2 - e) / r)

def operar(m, h, entradas, viernes=False):
    """Simula una lista de entradas (ver arriba). Devuelve un DataFrame de operaciones."""
    T = m["t"]; c = h.close.values; tc = h.index.values.astype("datetime64[s]").astype(np.int64)
    paso = int(np.median(np.diff(tc[-200:]))); ops = []; libre = -1
    for en in sorted(entradas, key=lambda z: z["i"]):
        i = int(en["i"]); t_ent = tc[i] + paso
        if t_ent < libre: continue
        d = int(en.get("dir", 1)); st = float(en["stop"]); ref = c[i]; rr = (ref - st) * d
        if rr <= 0: continue
        j0 = int(np.searchsorted(T, t_ent))
        q = simular(m, j0, st, ref + d * en.get("tp1", 0.75) * rr, ref + d * en.get("tp2", 2.0) * rr, d, viernes)
        if q:
            q["peso"] = float(en.get("peso", 1.0)); q["i"] = i; ops.append(q); libre = q["fin_t"]
    return pd.DataFrame(ops)

def sistema_actual(activo, D=3, viernes=False, tf="1h"):
    """El sistema del robot: señal de senales_base, entrada en la siguiente vela verde (≤ bpd velas), stop = mínimo más bajo
    hasta la vela verde − 0,5 ATR, mitad a 0,75 R y la otra a 2 R con breakeven."""
    m = minutos(activo); h = velas(m, tf); ind = indicadores(h)
    o, l, c, A = h.open.values, h.low.values, h.close.values, ind["atr"]; bpd = ind["bpd"]; ent = []
    for s in senales_base(h, ind, D):
        j = next((k for k in range(s + 1, min(s + 1 + bpd, len(c) - 1)) if c[k] > o[k]), None)
        if j is not None: ent.append(dict(i=j, stop=l[s:j + 1].min() - 0.5 * A[j]))
    return operar(m, h, ent, viernes)

def caida(activo, N=20, paso=0.024, stop=0.036, peso=0.5, viernes=False):
    """Segundo motor del robot (F-012/F-014/F-019): compra cuando el precio toca un 'paso' (2,4 %) por debajo del máximo de los
    últimos N días (sin contar la vela en curso). Stop un 3,6 % bajo la entrada, mitad a 1 R, la otra a 2 R con breakeven,
    10 días como mucho. Una operación a la vez; solo vuelve a comprar cuando ese máximo de referencia ha cambiado de valor.
    peso = 0,5: va a medio riesgo. Columna 'bajo' = % bajo el máximo de N días al entrar."""
    m = minutos(activo); h = velas(m, "1h"); bpd = indicadores(h)["bpd"]
    H, L = h.high.values, h.low.values; tc = h.index.values.astype("datetime64[s]").astype(np.int64)
    T, Lm, O = m["t"], m["low"], m["open"]
    ref = pd.Series(H).rolling(N * bpd).max().shift(1).values
    with np.errstate(invalid="ignore"):
        idx = np.flatnonzero(~np.isnan(ref) & (L <= ref * (1 - paso)))
    ops = []; libre = -1; ult = None
    for t in idx:
        if tc[t] < libre or ref[t] == ult: continue
        nivel = ref[t] * (1 - paso); a0 = np.searchsorted(T, tc[t]); a1 = np.searchsorted(T, tc[t] + 3600)
        kk = np.flatnonzero(Lm[a0:a1] <= nivel)
        if not len(kk): continue
        j0 = a0 + kk[0] + 1
        if j0 >= len(T) - 2: break
        e = O[j0]; st = e * (1 - stop); r = e - st
        q = simular(m, j0, st, e + r, e + 2 * r, 1, viernes)
        if q:
            q["peso"] = float(peso); q["bajo"] = (1 - e / ref[t]) * 100; ops.append(q); libre = q["fin_t"]; ult = ref[t]
    return pd.DataFrame(ops)

def plan_completo(activos=("spx", "nas", "eurjpy"), caidas=("nas", "spx"), viernes=False):
    """Las operaciones del plan entero de Pe: {"spx": ..., "nas": ..., "eurjpy": ..., "caída nas": ..., "caída spx": ...}."""
    o = {a: sistema_actual(a, viernes=viernes) for a in activos}
    for a in caidas: o[f"caída {a}"] = caida(a, viernes=viernes)
    return o

def azar(m, ops, K=10, dias=180, seed=7, viernes=False):
    """Para cada operación, K entradas al azar (±dias) con el mismo tamaño de stop, la misma dirección y los mismos objetivos en R."""
    T = m["t"]; rng = np.random.default_rng(seed); out = []
    for q in ops.itertuples():
        a = np.searchsorted(T, q.t - dias * 86400); b = np.searchsorted(T, q.t + dias * 86400)
        for j in rng.integers(a, max(a + 1, b - 1), K):
            e = m["open"][j]; r = e * q.riesgo / 100; d = int(getattr(q, "dir", 1))
            x = simular(m, int(j), e - d * r, e + d * q.tp1R * r, e + d * q.tp2R * r, d, viernes)
            if x: out.append(x)
    return pd.DataFrame(out)

# ─────────────────────────── informes ───────────────────────────
def _anio(o): return pd.to_datetime(o.t, unit="s").dt.year

def resumen(ops, az=None, tramos=TRAMOS + TROZOS):
    """Tabla con N, operaciones/año, R medio, t, acierto y peor racha, por tramos y frente al azar."""
    if len(ops) == 0: return "sin operaciones"
    def fila(o, nombre):
        if len(o) < 2: return dict(tramo=nombre, N=len(o))
        r = o.R.values; t = r.mean() / (r.std(ddof=1) / np.sqrt(len(r))) if r.std() > 0 else np.nan
        racha = mx = 0
        for v in r: racha = racha + 1 if v < 0 else 0; mx = max(mx, racha)
        return dict(tramo=nombre, N=len(o), R=round(r.mean(), 3), t=round(t, 2), acierto=round((r > 0).mean() * 100),
                    peor_racha=mx)
    y = _anio(ops); anos = max((ops.t.max() - ops.t.min()) / 86400 / 365.25, 0.1)
    filas = [dict(fila(ops, "todo"), ops_año=round(len(ops) / anos, 1))]
    for nombre, a, b in tramos: filas.append(fila(ops[(y >= a) & (y <= b)], nombre))
    T = pd.DataFrame(filas)
    if az is not None and len(az):
        ya = _anio(az); T["azar_R"] = [round(az.R.mean(), 3)] + [round(az.R[(ya >= a) & (ya <= b)].mean(), 3) for _, a, b in tramos]
        T["ventaja"] = (T.R - T.azar_R).round(3)
    return T.to_string(index=False)

def diario(ops_por_activo, riesgo, desde="2003-06-01", hasta=None):
    """Serie diaria del resultado (fracción de la cuenta) cerrando cada operación el día que termina (NY)."""
    hasta = hasta or dt.date.today().isoformat(); dias = pd.bdate_range(desde, hasta); r = pd.Series(0.0, index=dias)
    for O in ops_por_activo.values():
        if len(O) == 0: continue
        t = pd.to_datetime(O.fin_t.values, unit="s", utc=True).tz_convert("America/New_York").normalize().tz_localize(None)
        peso = O.peso.values if "peso" in O else 1.0
        r = r.add(pd.Series(O.R.values * riesgo * peso, index=t).groupby(level=0).sum(), fill_value=0)
    return r.reindex(dias, fill_value=0.0)

FIRMAS = {"ftmo1": dict(fases=[0.10], diaria=0.03, total=0.10, tipo="eod", mejor=0.5),
          "ftmo2": dict(fases=[0.10, 0.05], diaria=0.05, total=0.10, tipo="fijo", mejor=None),
          "fn_instant": dict(fases=[0.05], diaria=None, total=0.06, tipo="para", mejor=None),
          "ftp_instant": dict(fases=[0.05], diaria=0.06, total=0.06, tipo="para", mejor=None),
          "5ers": dict(fases=[0.10], diaria=None, total=0.06, tipo="fijo", mejor=None, pausa=0.03)}
COLCHON = lambda e: min(0.04, max(0.005, (e + 0.06) / 3))   # riesgo según el saldo (e = saldo sobre el inicio, 0.02 = +2 %)

def retos(serie, firma="ftmo1", politica=None):
    """Un intento empezando el primer día de cada mes. Devuelve inicio, resultado (pasa/quema/sigue), meses y meses de datos.
    politica: None = la serie ya viene en fracción de cuenta (de diario(ops, riesgo)). Si es una función f(saldo) -> riesgo,
    la serie tiene que venir en R del día (diario(ops, 1.0)) y cada día se multiplica por el riesgo que toque."""
    F = FIRMAS[firma]; r = serie.values; dias = serie.index; fin = dias[-1]; pausa = F.get("pausa")
    ini = pd.Series(range(len(dias)), index=dias).groupby([dias.year, dias.month]).first().values; out = []
    for i0 in ini:
        eq = top = base = 1.0; fase = 0; pos = []; res = "sigue"; j = len(r) - 1
        for i in range(i0, len(r)):
            ri = r[i] * politica(eq - 1.0) if politica else r[i]
            if pausa: ri = max(ri, -pausa)
            peor = eq * (1 + min(ri, 0))
            suelo = {"fijo": 1 - F["total"], "eod": max(top, 1.0) - F["total"], "para": min(top - F["total"], 1.0)}[F["tipo"]]
            if (F["diaria"] and peor <= eq - F["diaria"]) or peor <= suelo: res = "quema"; j = i; break
            dd = eq * ri; eq += dd; top = max(top, eq)
            if dd > 0: pos.append(dd)
            if eq >= base + F["fases"][fase] and (F["mejor"] is None or max(pos) <= F["mejor"] * sum(pos)):
                fase += 1
                if fase == len(F["fases"]): res = "pasa"; j = i; break
                eq = top = base = 1.0; pos = []
        out.append(dict(inicio=dias[i0], res=res, meses=(j - i0 + 1) / 21, datos=(fin - dias[i0]).days / 30.4))
    return pd.DataFrame(out)

def tabla_retos(ops_por_activo, firma="ftmo1", riesgos=(0.01, 0.0125), tramos=TRAMOS):
    filas = []
    for rk in riesgos:
        if rk == "colchon": R = retos(diario(ops_por_activo, 1.0), firma, COLCHON); et = "colchón"
        else: R = retos(diario(ops_por_activo, rk), firma); et = f"{rk*100:.2f}%"
        for nombre, a, b in tramos:
            x = R[(R.inicio.dt.year >= a) & (R.inicio.dt.year <= b)]
            if len(x) == 0: continue
            f = dict(firma=firma, riesgo=et, tramo=nombre, intentos=len(x),
                     pasa=round((x.res == "pasa").mean() * 100), quema=round((x.res == "quema").mean() * 100))
            for mm in (3, 6, 12, 18):
                y = x[x.datos >= mm]; f[f"≤{mm}m"] = round(((y.res == "pasa") & (y.meses <= mm)).mean() * 100) if len(y) else None
            med = x.meses[x.res == "pasa"].median(); f["mediana_m"] = None if pd.isna(med) else round(float(med), 1)
            filas.append(f)
    return pd.DataFrame(filas).to_string(index=False)

def sombra(ops_por_activo, desde, riesgo=0.0125, firma="ftmo1"):
    """Reto en la sombra con datos reales desde 'desde' (AAAA-MM-DD): operaciones, saldo y estado frente a las reglas."""
    F = FIRMAS[firma]; t0 = pd.Timestamp(desde, tz="UTC").timestamp(); filas = []
    for a, O in ops_por_activo.items():
        if len(O):
            for q in O[O.t >= t0].itertuples():
                filas.append(dict(activo=a, entrada=pd.to_datetime(q.t, unit="s", utc=True).tz_convert("Europe/Madrid").strftime("%d-%m %H:%M"),
                                  salida=pd.to_datetime(q.fin_t, unit="s", utc=True).tz_convert("Europe/Madrid").strftime("%d-%m %H:%M"),
                                  precio=round(q.e, 1), R=round(q.R, 2), peso=float(getattr(q, "peso", 1.0)), abierta=q.fin_t > dt.datetime.now(dt.timezone.utc).timestamp() - 3600))
    nuevas = {a: O[O.t >= t0] for a, O in ops_por_activo.items() if len(O)}   # solo cuenta lo abierto desde 'desde'
    s = diario(nuevas, riesgo, desde=desde); eq = (1 + s).cumprod()
    return pd.DataFrame(filas), dict(saldo_pct=float(round((eq.iloc[-1] - 1) * 100, 2)), peor_pct=float(round((eq.min() - 1) * 100, 2)),
                                     objetivo_pct=F["fases"][0] * 100, firma=firma, riesgo_pct=riesgo * 100)

def linea_base(sombra_desde=None, activos=("spx", "nas", "eurjpy"), riesgo=0.01, viernes=True, caidas=("nas", "spx")):
    """Texto en Markdown con la línea base (el plan de Pe: mínimo + Flujo verde en S&P, Nasdaq y EUR/JPY a riesgo entero y la
    caída desde el máximo en Nasdaq y S&P a medio riesgo), sus retos en FTMO 1 paso y The5ers y, si se pide, el reto en la
    sombra con datos reales."""
    o = {a: sistema_actual(a, viernes=viernes) for a in activos}
    oc = {f"caída {a}": caida(a, viernes=viernes) for a in caidas}
    todo = {**o, **oc}
    txt = [f"# Fondeo · línea base (plan de Pe, {riesgo*100:.2f} % por operación; cierre del viernes: {'sí' if viernes else 'no'})",
           f"- Mínimo + Flujo verde (CMF > 0,025): {', '.join(a.upper() for a in activos)}, riesgo entero.",
           f"- Caída desde el máximo (−2,4 % del máximo de 20 días, stop 3,6 %, 1 R / 2 R): "
           f"{', '.join(a.upper() for a in caidas) or 'ninguna'}, medio riesgo cada una.", ""]
    for a in todo:
        txt += [f"## {a.upper()}", "```", resumen(todo[a]) if len(todo[a]) else "sin operaciones", "```"]
    txt += ["## Retos con el plan entero", "```", tabla_retos(todo, "5ers", ["colchon", 0.02]), tabla_retos(todo, "ftmo1", [riesgo]), "```"]
    if oc:
        txt += ["## Retos solo con el mínimo + Flujo verde (para comparar)", "```", tabla_retos(o, "5ers", ["colchon"]),
                tabla_retos(o, "ftmo1", [riesgo]), "```"]
    d = diario(todo, riesgo)
    txt += [f"Peor día de la historia con el plan entero al {riesgo*100:.2f} %: {d.min()*100:.2f} % "
            f"(FTMO 1 paso quema al −3 % en el día; The5ers pausa el día al −3 %)."]
    if oc:
        txt += ["", "## Vigilancia de la caída (tarea F-021)"]
        for a, O in oc.items():
            if len(O) == 0: continue
            y = pd.to_datetime(O.t, unit="s").dt.year; r20 = O.R.rolling(20).mean().dropna(); u = float(r20.iloc[-1])
            p10 = float(r20.quantile(0.10)); bajo0 = float((r20 < 0).mean() * 100)
            txt += [f"- {a}: {len(O)} operaciones; R medio de las 20 últimas {u:+.2f} (histórico {O.R.mean():+.2f}; "
                    f"2023-hoy {O.R[y >= 2023].mean():+.2f}). En la historia, las 20 últimas estuvieron bajo 0 el {bajo0:.0f} % "
                    f"del tiempo y bajo {p10:+.2f} solo el 10 %. "
                    + (f"⚠️ Ahora está en ese 10 % peor: avisa a Pe." if u <= p10 else "Dentro de lo normal.")]
            if sombra_desde:
                n = O[O.t >= pd.Timestamp(sombra_desde, tz="UTC").timestamp()]
                txt += [f"  Operaciones nuevas desde {sombra_desde}: {len(n)}" + (f", R medio {n.R.mean():+.2f}" if len(n) else "")
                        + (" ⚠️ 20 o más nuevas con media bajo 0 R: avisa a Pe." if len(n) >= 20 and n.R.mean() < 0 else "")]
    if sombra_desde:
        op, est = sombra(todo, sombra_desde, riesgo=riesgo)
        txt += [f"## Reto en la sombra desde {sombra_desde} (plan entero, {riesgo*100:.2f} %; las caídas a la mitad)",
                f"Estado: {est}", f"Objetivo +10 % en las dos firmas. Suelo: −6 % fijo en The5ers; −10 % desde el mayor cierre en FTMO.",
                "", op.to_string(index=False) if len(op) else "Sin operaciones todavía."]
    for a in todo: todo[a].to_pickle(os.path.join(DATOS, f"base_{a.replace('caída ', 'caida_')}.pkl"))
    return "\n".join(txt)

if __name__ == "__main__":
    args = sys.argv[1:]
    act = ("spx", "nas")
    if "--activos" in args: act = tuple(args[args.index("--activos") + 1].split(","))
    if "--descargar" in args: print(json.dumps(descargar(act), ensure_ascii=False), file=sys.stderr)
    if "--base" in args:
        desde = os.environ.get("FONDEO_SOMBRA_DESDE")
        plan = tuple(os.environ.get("FONDEO_ACTIVOS", "spx,nas,eurjpy").split(","))
        cds = tuple(x for x in os.environ.get("FONDEO_CAIDA", "nas,spx").split(",") if x)
        print(linea_base(desde, plan, float(os.environ.get("FONDEO_RIESGO", "0.01")), os.environ.get("FONDEO_VIERNES", "si") == "si", cds))
