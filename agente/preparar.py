"""
PREPARACIÓN DIARIA DEL AGENTE — sin IA: gratis, rápida y siempre igual.

Hace dos trabajos antes de que entre el agente:
  1) VIGILANTE: ¿se ha grabado hoy todo lo de la terminal? ¿hay avisos nuevos en
     SALUD DEL BUILD? ¿algún archivo del histórico ha encogido (datos perdidos)?
  2) MARCADOR: qué ha pasado DESPUÉS de cada señal del cable (senales_wire.json)
     y de cada cesta semanal (track_record.json). Son datos que ninguna regla vio
     al diseñarse: es la única prueba limpia de si una señal vale.

Escribe en agente/hoy/:  vigilante.json · marcador.json · lectura.json · resumen.md · telegram_sin_ia.txt
Uso:  python agente/preparar.py            (en GitHub, con internet)
      python agente/preparar.py --sin-internet   (precios solo del repo)
No toca nada fuera de agente/hoy/.
"""
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
HIST = RAIZ / "historico_seguimiento_NO_BORRAR"
SALIDA = RAIZ / "agente" / "hoy"
NY = ZoneInfo("America/New_York")

SIN_INTERNET = "--sin-internet" in sys.argv
HORIZONTES = (5, 10, 20)          # sesiones después de la entrada
SEPARACION_EPISODIO = 14          # días naturales: la misma señal repetida dentro de este plazo cuenta UNA vez
MAPA_SIMBOLOS = {"MERCADO": "SPY", "F&G": "SPY"}

# Archivos que la terminal debe grabar CADA noche de mercado
ESENCIALES = {
    "semaforo_estado.json": lambda d: d.get("ultimo"),
    "estructura_estado.json": lambda d: d[-1]["date"] if d else None,
    "dix_estado.json": lambda d: d[-1]["date"] if d else None,
    "amplitud_estado.json": lambda d: d[-1]["date"] if d else None,
    "operativa_indices.json": lambda d: d[-1]["date"] if d else None,
    "centinela_estado.json": lambda d: d[-1]["date"] if d else None,
    "options_iv.json": lambda d: max((f for v in d.values() if isinstance(v, dict) for f in v), default=None),
}
# Archivos que solo cambian cuando pasa algo (se informan, no son error)
INFORMATIVOS = {
    "senales_wire.json": lambda d: d[-1]["date"] if d else None,
    "despertares.json": lambda d: d[-1]["date"] if d else None,
    "senales_contrarias.json": lambda d: d[-1]["date"] if d else None,
    "track_record.json": lambda d: d[-1]["date"] if d else None,
    "plan_spy_estado.json": lambda d: d.get("ultimo"),
}


# ───────────────────────── utilidades ─────────────────────────
def leer(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        return {"__error__": f"{type(e).__name__}: {e}"}


def fecha_mercado_esperada():
    """Último día de mercado que la terminal ya debería haber cerrado."""
    forzada = os.environ.get("FECHA_MERCADO")
    if forzada:
        return pd.Timestamp(forzada).date()
    ahora = datetime.now(NY)
    d = ahora.date()
    if ahora.weekday() >= 5 or ahora.hour < 16:
        d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def sesiones_entre(a, b):
    """Días laborables desde a (exclusivo) hasta b (inclusivo). Negativo si a > b."""
    if a is None:
        return None
    a, b = pd.Timestamp(a).date(), pd.Timestamp(b).date()
    if a >= b:
        return 0
    return int(np.busday_count(a + timedelta(days=1), b + timedelta(days=1)))


def tamano(d):
    if isinstance(d, list):
        return len(d)
    if isinstance(d, dict):
        if d and all(isinstance(v, dict) for v in d.values()):
            return sum(len(v) for v in d.values())
        return len(d)
    return 0


def version_anterior(ruta_rel):
    """Contenido del archivo en el commit anterior que tocó el histórico."""
    try:
        commits = subprocess.run(
            ["git", "-C", str(RAIZ), "log", "-2", "--format=%H", "--", "historico_seguimiento_NO_BORRAR"],
            capture_output=True, text=True, timeout=30).stdout.split()
        if len(commits) < 2:
            return None
        txt = subprocess.run(["git", "-C", str(RAIZ), "show", f"{commits[1]}:{ruta_rel}"],
                             capture_output=True, text=True, timeout=30)
        return json.loads(txt.stdout) if txt.returncode == 0 else None
    except Exception:  # noqa: BLE001
        return None


def wilson(aciertos, n, z=1.96):
    if n == 0:
        return (None, None)
    p = aciertos / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    medio = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (round(100 * (centro - medio), 1), round(100 * (centro + medio), 1))


# ───────────────────────── 1) VIGILANTE ─────────────────────────
def vigilante():
    esperada = fecha_mercado_esperada()
    res = {"fecha_mercado_esperada": str(esperada), "rojo": [], "ambar": [], "verde": [], "archivos": {}}

    for nombre, sacar in {**ESENCIALES, **INFORMATIVOS}.items():
        d = leer(HIST / nombre)
        if isinstance(d, dict) and "__error__" in d:
            res["rojo"].append(f"{nombre}: no se puede leer ({d['__error__']})")
            continue
        try:
            ultima = sacar(d)
        except Exception as e:  # noqa: BLE001
            ultima = None
            res["ambar"].append(f"{nombre}: formato inesperado ({type(e).__name__})")
        retraso = sesiones_entre(ultima, esperada)
        res["archivos"][nombre] = {"ultima_fecha": ultima, "sesiones_de_retraso": retraso, "elementos": tamano(d)}
        if nombre in ESENCIALES:
            if retraso is None:
                res["rojo"].append(f"{nombre}: sin fecha")
            elif retraso >= 2:
                res["rojo"].append(f"{nombre}: lleva {retraso} sesiones sin grabarse (última {ultima})")
            elif retraso == 1:
                res["ambar"].append(f"{nombre}: no tiene el día {esperada} (última {ultima}); puede ser festivo o retraso")
        # ¿ha encogido respecto a la noche anterior?
        antes = version_anterior(f"historico_seguimiento_NO_BORRAR/{nombre}")
        if antes is not None:
            t0, t1 = tamano(antes), tamano(d)
            res["archivos"][nombre]["elementos_antes"] = t0
            if t0 >= 10 and t1 < 0.8 * t0:
                res["rojo"].append(f"{nombre}: ha encogido de {t0} a {t1} elementos (¿datos perdidos?)")

    # historiales (se refrescan una vez por semana / mes)
    meta = leer(HIST / "historiales" / "_meta.json")
    if isinstance(meta, dict) and "__error__" not in meta:
        for k, v in meta.items():
            if isinstance(v, dict) and v.get("fecha"):
                dias = (pd.Timestamp(esperada) - pd.Timestamp(v["fecha"])).days
                limite = 40 if k == "universo" else 10
                res["archivos"][f"historiales/{k}"] = {"ultima_fecha": v["fecha"], "dias": dias}
                if dias > limite:
                    res["ambar"].append(f"historiales/{k}: último refresco hace {dias} días")
                if v.get("errores") or v.get("error"):
                    res["ambar"].append(f"historiales/{k}: error al refrescar → {v.get('errores') or v.get('error')}")

    # SALUD DEL BUILD: avisos nuevos y resueltos respecto a la ejecución anterior
    sb = leer(HIST / "salud_build.json")
    if isinstance(sb, list) and sb:
        ult = sb[-1]
        res["salud_build_ultima"] = ult.get("ts")
        ts = pd.Timestamp(ult.get("ts", "1970-01-01").replace(" UTC", ""))
        if (pd.Timestamp(esperada) - ts.normalize()).days > 1:
            res["rojo"].append(f"salud_build.json: la última ejecución registrada es {ult.get('ts')}")
        op = ult.get("opciones", {})
        if op and not op.get("corrio", True):
            res["rojo"].append("opciones: la descarga de cadenas NO se ejecutó")
        claves = lambda e: {a.get("o"): a.get("m") for a in e.get("avisos", [])}  # noqa: E731
        hoy_av = claves(ult)
        ayer_av = claves(sb[-2]) if len(sb) > 1 else {}
        res["avisos_hoy"] = [f"{k}: {v}" for k, v in hoy_av.items()]
        res["avisos_nuevos"] = [f"{k}: {v}" for k, v in hoy_av.items() if k not in ayer_av]
        res["avisos_resueltos"] = [k for k in ayer_av if k not in hoy_av]
        for a in res["avisos_nuevos"]:
            res["ambar"].append(f"aviso NUEVO en SALUD DEL BUILD → {a[:220]}")
    else:
        res["rojo"].append("salud_build.json vacío o ilegible")

    if not res["rojo"] and not res["ambar"]:
        res["verde"].append("Todo grabado y sin avisos nuevos")
    return res


# ───────────────────────── 2) MARCADOR ─────────────────────────
def precios(simbolos, desde):
    """Cierres ajustados. Primero Yahoo (en GitHub hay internet); lo que falte, del repo."""
    simbolos = sorted(set(simbolos))
    px = pd.DataFrame()
    fuente = "repo"
    if not SIN_INTERNET:
        try:
            import yfinance as yf
            d = yf.download(simbolos, start=str(desde), auto_adjust=True, progress=False, threads=True)
            c = d["Close"] if isinstance(d.columns, pd.MultiIndex) else d[["Close"]].rename(columns={"Close": simbolos[0]})
            px = c.dropna(how="all")
            px.index = pd.to_datetime(px.index).tz_localize(None).normalize()
            fuente = "yahoo"
        except Exception as e:  # noqa: BLE001
            print("Yahoo no disponible:", type(e).__name__, e)
    try:
        u = pd.read_csv(HIST / "historiales" / "universo_close.csv.gz", index_col=0, parse_dates=True)
        u = u[u.index >= pd.Timestamp(desde)]
        if px.empty:
            px = u
        else:
            faltan = [s for s in u.columns if s in simbolos and (s not in px.columns or px[s].notna().sum() < 5)]
            px = px.drop(columns=[s for s in faltan if s in px.columns]).join(u[faltan], how="outer")
            fuente += "+repo" if faltan else ""
    except Exception as e:  # noqa: BLE001
        print("universo_close no disponible:", e)
    return px.sort_index(), fuente


def episodios(w):
    """Una señal repetida día tras día cuenta como UN episodio (la primera)."""
    w = w.sort_values("date")
    ultima = {}
    keep = []
    for i, r in w.iterrows():
        k = (r.tag, r.sym, r.dir)
        if k in ultima and (r.date - ultima[k]).days <= SEPARACION_EPISODIO:
            ultima[k] = r.date        # sigue el mismo episodio
            continue
        ultima[k] = r.date
        keep.append(i)
    return w.loc[keep]


def resultado(px, sym, fecha, h):
    """Rendimiento desde el CIERRE de la sesión siguiente a la señal hasta h sesiones después."""
    if sym not in px.columns:
        return None, "sin_precio"
    s = px[sym].dropna()
    if s.empty:
        return None, "sin_precio"
    pos = s.index.searchsorted(pd.Timestamp(fecha), side="right")   # primera sesión DESPUÉS de la señal
    if pos >= len(s):
        return None, "pendiente"
    if pos + h >= len(s):
        return None, "pendiente"
    return float(s.iloc[pos + h] / s.iloc[pos] - 1), "ok"


def marcador():
    w = leer(HIST / "senales_wire.json")
    if not isinstance(w, list) or not w:
        return {"error": "senales_wire.json vacío o ilegible"}
    w = pd.DataFrame(w)
    w["date"] = pd.to_datetime(w["date"])
    w["sym"] = w["sym"].replace(MAPA_SIMBOLOS)
    w = w[w["dir"] != 0]
    ep = episodios(w)
    px, fuente = precios(list(ep.sym.unique()) + ["SPY"], ep.date.min() - pd.Timedelta(days=10))

    filas = []
    for _, r in ep.iterrows():
        f = {"date": r.date.date().isoformat(), "tag": r.tag, "sym": r.sym, "dir": int(r.dir)}
        for h in HORIZONTES:
            ret, est = resultado(px, r.sym, r.date, h)
            spy, _ = resultado(px, "SPY", r.date, h)
            f[f"r{h}"] = None if ret is None else round(100 * r.dir * ret, 2)
            f[f"x{h}"] = None if (ret is None or spy is None or r.sym == "SPY") else round(100 * r.dir * (ret - spy), 2)
            f[f"e{h}"] = est
        filas.append(f)
    E = pd.DataFrame(filas)

    # si una etiqueta sale en las dos direcciones (p. ej. GIRO), se mide cada una por separado
    dobles = set(E.groupby("tag")["dir"].nunique().loc[lambda x: x > 1].index)
    E["senal"] = [t + ("↑" if d > 0 else "↓") if t in dobles else t for t, d in zip(E.tag, E.dir)]
    tabla = []
    for tag, g in E.groupby("senal"):
        fila = {"senal": tag, "episodios": len(g), "dias_en_cable": int((w.tag == tag).sum())}
        for h in HORIZONTES:
            ok = g[g[f"e{h}"] == "ok"]
            n = len(ok)
            fila[f"n{h}"] = n
            fila[f"pendientes{h}"] = int((g[f"e{h}"] == "pendiente").sum())
            if n:
                aciertos = int((ok[f"r{h}"] > 0).sum())
                lo, hi = wilson(aciertos, n)
                xs = ok[f"x{h}"].dropna()
                fila[f"media{h}"] = round(ok[f"r{h}"].mean(), 2)
                fila[f"acierto{h}"] = round(100 * aciertos / n, 1)
                fila[f"ic{h}"] = [lo, hi]
                fila[f"exceso_spy{h}"] = round(xs.mean(), 2) if len(xs) else None
                fila[f"t_exceso{h}"] = (round(xs.mean() / (xs.std(ddof=1) / math.sqrt(len(xs))), 2)
                                        if len(xs) > 2 and xs.std(ddof=1) > 0 else None)
        n20 = fila.get("n20", 0)
        if n20 < 10:
            fila["veredicto"] = "muy pocos casos: no se puede decir nada"
        elif n20 < 30:
            fila["veredicto"] = "pocos casos: solo orientativo"
        elif (fila.get("t_exceso20") or 0) > 2 and (fila.get("ic20") or [0])[0] > 50:
            fila["veredicto"] = "PROMETEDORA (aún sin corregir por haber muchas señales)"
        elif (fila.get("t_exceso20") or 0) < -2:
            fila["veredicto"] = "VA AL REVÉS de lo que dice"
        else:
            fila["veredicto"] = "sin ventaja visible frente al SPY"
        tabla.append(fila)

    # Cesta semanal (track_record): semana siguiente frente al SPY
    cesta = []
    tr = leer(HIST / "track_record.json")
    if isinstance(tr, list) and len(tr) > 1:
        for a, b in zip(tr[:-1], tr[1:]):
            pa, pb = a.get("px", {}), b.get("px", {})
            rs = [pb[s] / pa[s] - 1 for s in a.get("basket", []) if s in pa and s in pb and pa[s]]
            if rs and "SPY" in pa and "SPY" in pb:
                cesta.append({"semana": a.get("week"), "cesta": round(100 * np.mean(rs), 2),
                              "spy": round(100 * (pb["SPY"] / pa["SPY"] - 1), 2), "n_etf": len(rs)})
    resumen_cesta = None
    if cesta:
        C = pd.DataFrame(cesta)
        C["exceso"] = C.cesta - C.spy
        resumen_cesta = {"semanas": len(C), "media_cesta": round(C.cesta.mean(), 2), "media_spy": round(C.spy.mean(), 2),
                         "exceso_medio": round(C.exceso.mean(), 2), "semanas_mejor_que_spy": int((C.exceso > 0).sum()),
                         "ic_mejor": list(wilson(int((C.exceso > 0).sum()), len(C)))}

    ultima = w.date.max()
    hoy = w[w.date == ultima][["tag", "sym", "dir"]].to_dict("records")
    return {"fuente_precios": fuente, "ultima_senal": ultima.date().isoformat(),
            "senales_ultimo_dia": hoy, "tabla": sorted(tabla, key=lambda f: -f["episodios"]),
            "cesta_semanal": resumen_cesta, "cesta_detalle": cesta[-8:],
            "episodios": E.to_dict("records")}


# ───────────────────────── informe para el agente ─────────────────────────
def _f(x, suf=""):
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x}{suf}"


def resumen_md(v, m):
    L = [f"# Datos del día — mercado {v['fecha_mercado_esperada']}",
         f"_Generado {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC por agente/preparar.py (sin IA)._", "",
         "## 1. Vigilante"]
    for nivel, icono in (("rojo", "🔴"), ("ambar", "🟠"), ("verde", "🟢")):
        L += [f"- {icono} {x}" for x in v[nivel]]
    if v.get("avisos_resueltos"):
        L.append(f"- ✅ Avisos que ya NO salen: {', '.join(v['avisos_resueltos'])}")
    L += ["", "## 2. Marcador fuera de muestra (señales del cable)",
          f"Precios: {m.get('fuente_precios')}. Entrada al cierre de la sesión siguiente a la señal. "
          "Una señal repetida en 14 días cuenta una vez. 'acierto' = se movió en la dirección que decía; "
          "'exceso' = frente al SPY en el mismo plazo; IC = intervalo de confianza del 95 % (Wilson).", "",
          "| Señal | Episodios | n a 20 ses. | Media 5 / 20 ses. | Acierto 20 ses. (IC) | Exceso SPY 20 ses. (t) | Veredicto |",
          "|---|---|---|---|---|---|---|"]
    for f in m.get("tabla", []):
        ic = f.get("ic20") or [None, None]
        L.append(f"| {f['senal']} | {f['episodios']} | {f.get('n20', 0)} (+{f.get('pendientes20', 0)} pend.) | "
                 f"{_f(f.get('media5'), ' %')} / {_f(f.get('media20'), ' %')} | "
                 f"{_f(f.get('acierto20'), ' %')} ({_f(ic[0])}–{_f(ic[1])}) | "
                 f"{_f(f.get('exceso_spy20'))} (t {_f(f.get('t_exceso20'))}) | {f['veredicto']} |")
    c = m.get("cesta_semanal")
    if c:
        L += ["", f"**Cesta semanal (track_record):** {c['semanas']} semanas, cesta {c['media_cesta']} % de media frente a "
                  f"SPY {c['media_spy']} %; mejor que el SPY {c['semanas_mejor_que_spy']} de {c['semanas']} "
                  f"(IC {c['ic_mejor'][0]}–{c['ic_mejor'][1]} %)."]
    L += ["", f"**Señales del último día ({m.get('ultima_senal')}):** " +
          ", ".join(f"{s['tag']} {s['sym']}{'↑' if s['dir'] > 0 else '↓'}" for s in m.get("senales_ultimo_dia", []))]
    return "\n".join(L) + "\n"


# ───────────────────────── 3) LECTURA DEL DÍA Y MENSAJE (sin IA) ─────────────────────────
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
IMPORTANTES = ("NIVEL", "PÁNICO", "PLAN SPY", "RÉGIMEN", "RISK")


def _n(x, dec=1):
    return "—" if x is None else f"{x:.{dec}f}".replace(".", ",")


def lectura():
    """Lo esencial que marca hoy la terminal, sacado tal cual de sus archivos (sin interpretar)."""
    r = {}
    s = leer(HIST / "semaforo_estado.json")
    if isinstance(s, dict) and s.get("log"):
        u = s["log"][-1]
        mer = s.get("mercado") or {}
        r["caidas"] = {"fecha": u.get("date"), "dd": u.get("dd", {}), "vix": u.get("vix"),
                       "agudo": u.get("agudo"), "en_minimos": u.get("nl"),
                       "vix_vix3m": u.get("t3"), "panico_vivo": u.get("panico_vivo"),
                       "panico_desde": mer.get("panico_desde"), "panico_se_fue": mer.get("panico_se_fue"),
                       "eventos": u.get("eventos") or []}
    o = leer(HIST / "operativa_indices.json")
    if isinstance(o, list) and o:
        r["indices"] = {k: (v.get("ver"), v.get("score")) for k, v in o[-1].get("idx", {}).items()}
    e = leer(HIST / "estructura_estado.json")
    if isinstance(e, list) and e:
        u = e[-1]
        r["dinero"] = {k: u.get(k) for k in ("lectura", "sect_entra", "sect_sale", "empuje", "extrema")}
    c = leer(HIST / "centinela_estado.json")
    if isinstance(c, list) and c:
        r["centinela"] = c[-1].get("estado")
    p = leer(HIST / "plan_spy_estado.json")
    if isinstance(p, dict) and p.get("activo"):
        r["plan_spy"] = sorted(p.get("tocados", {}), key=float)
    return r


def telegram_sin_ia(v, m, lec):
    f = pd.Timestamp(v["fecha_mercado_esperada"])
    L = [f"🤖 Compañero (sin IA) · {DIAS[f.weekday()]} {f:%d-%m}"]
    if v["rojo"]:
        L.append(f"🔴 Sistema: {len(v['rojo'])} problema(s): " + " | ".join(x[:90] for x in v["rojo"][:2]))
    elif v["ambar"]:
        L.append("🟠 Sistema: " + " | ".join(x[:90] for x in v["ambar"][:2]))
    else:
        L.append("🟢 Sistema: todo grabado, sin avisos nuevos")
    cd = lec.get("caidas")
    if cd:
        dd = ", ".join(f"{k} {_n(x)} %" for k, x in cd["dd"].items() if x is not None and x <= -3)
        L.append(f"📉 Caídas: {dd or 'nada por debajo de −3 %'} · VIX {_n(cd['vix'])}")
        ev = cd.get("eventos") or []
        if "se_va" in ev:
            L.append(f"🟢 HOY SE VA EL PÁNICO (VIX/VIX3M {_n(cd.get('vix_vix3m'), 2)}): mira en la terminal en qué ETF tienes reserva")
        elif cd.get("panico_vivo"):
            L.append(f"🔥 Pánico vivo desde el {str(cd.get('panico_desde'))[8:10]}-{str(cd.get('panico_desde'))[5:7]}: "
                     f"se va cuando VIX/VIX3M baje de 1,0 (hoy {_n(cd.get('vix_vix3m'), 2)})")
        elif cd.get("agudo"):
            L.append("🔥 Pánico agudo hoy")
        if "rendicion" in ev:
            L.append("🔥 RENDICIÓN TOTAL hoy")
    if lec.get("indices"):
        L.append("🚦 Índices: " + ", ".join(f"{k} {ver}" for k, (ver, _) in lec["indices"].items()))
    di = lec.get("dinero")
    if di:
        extra = " · VENTA EXTREMA" if di.get("extrema") else (" · EMPUJE" if di.get("empuje") else "")
        L.append(f"🧩 Dinero: {di.get('lectura')} (entran {di.get('sect_entra')} sectores, salen {di.get('sect_sale')}){extra}"
                 f" · centinela {lec.get('centinela', '—')}")
    if lec.get("plan_spy"):
        L.append("🎯 Plan SPY: tocados " + ", ".join(f"−{t} %" for t in lec["plan_spy"]))
    tabla = m.get("tabla", [])
    if tabla:
        maduras = [t for t in tabla if t.get("n20", 0) >= 30]
        if maduras:
            L.append("🧾 Marcador (≥30 casos): " + "; ".join(
                f"{t['senal']} acierta {_n(t.get('acierto20'), 0)} % (IC {_n((t.get('ic20') or [None])[0], 0)}–"
                f"{_n((t.get('ic20') or [None, None])[1], 0)})" for t in maduras[:3]))
        else:
            top = max(tabla, key=lambda t: t.get("n20", 0))
            L.append(f"🧾 Marcador: ninguna señal tiene aún 30 casos para juzgarla (la que más: {top['senal']}, {top.get('n20', 0)})")
    c = m.get("cesta_semanal")
    if c:
        L.append(f"🧺 Cesta semanal: mejor que el SPY {c['semanas_mejor_que_spy']} de {c['semanas']} semanas")
    hoy = m.get("senales_ultimo_dia", [])
    if hoy:
        imp = [f"{x['tag']} {x['sym']}" for x in hoy if x["tag"] in IMPORTANTES]
        L.append(f"📡 Cable: {len(hoy)} señales" + (" · " + ", ".join(imp[:5]) if imp else ""))
    return "\n".join(L)[:1500]


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    v = vigilante()
    try:
        m = marcador()
    except Exception as e:  # noqa: BLE001 — el marcador nunca debe tumbar al vigilante
        m = {"error": f"{type(e).__name__}: {e}", "tabla": []}
        v["ambar"].append(f"El marcador falló: {m['error']}")
    (SALIDA / "vigilante.json").write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
    (SALIDA / "marcador.json").write_text(json.dumps(m, ensure_ascii=False, default=str), encoding="utf-8")
    lec = lectura()
    (SALIDA / "lectura.json").write_text(json.dumps(lec, ensure_ascii=False, indent=1), encoding="utf-8")
    (SALIDA / "resumen.md").write_text(resumen_md(v, m), encoding="utf-8")
    tg = telegram_sin_ia(v, m, lec)
    (SALIDA / "telegram_sin_ia.txt").write_text(tg, encoding="utf-8")
    print(resumen_md(v, m))
    print("──── Telegram (sin IA) ────")
    print(tg)


if __name__ == "__main__":
    main()
