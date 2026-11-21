"""I-005 (20-nov-2026): «se va el pánico» frente a comprar con el pánico TODAVÍA vivo.
Diseño apuntado en agente/ideas.md el 13-nov-2026, ANTES de calcular ningún rendimiento. No se ha cambiado después.

Mismos episodios y la misma entrada que I-004 variante C-60 (arranque con VIX/VIX3M >= 1,00; «se va» = primer cierre
con VIX/VIX3M < 1,0 y el SPY al menos -3 % bajo su máximo de 52 semanas; episodios separados >= 20 sesiones;
entrada = cierre del primer viernes >= ese día; SPY ajustado).
Azar justo (lo único que cambia respecto a I-004): viernes de la MISMA mitad de la historia, con la caída del SPY a
±2,5 puntos de la del episodio, con VIX/VIX3M >= 1,0 ESE viernes (pánico vivo) y a más de 20 sesiones de cualquier
entrada de episodio. Exceso del episodio = su rendimiento - la media de sus viernes parecidos; se promedia por episodio.
Plazos (3 variantes, no más): 20, 60 (principal) y 120 sesiones. Además se mide la peor caída posterior en 60 sesiones.

Trozos: aprender = episodios hasta 2018; comprobar = 2019-2022; la caja cerrada (2023 en adelante) NO se abre.

Uso (desde la raíz del repositorio):  python agente/estudios/i005.py
"""
import math
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "agente/herramientas")
import datos  # noqa: E402

HIST = "historico_seguimiento_NO_BORRAR/historiales/"
FIN_APRENDER = pd.Timestamp("2018-12-31")
FIN_ERA = pd.Timestamp("2022-12-31")      # la caja 2023+ queda cerrada
INICIO_ERA = pd.Timestamp("2009-09-18")   # primer día de VIX3M en el archivo CBOE
SEPARACION = 20
DD_MIN = -3.0
BANDA = 2.5
ARRANQUE = 1.00      # la variante C de I-004 (la principal)
B = 5000
rng = np.random.default_rng(5)


def cargar(f):
    d = pd.read_csv(HIST + f)
    d["DATE"] = pd.to_datetime(d["DATE"], format="%m/%d/%Y")
    return d.set_index("DATE")["CLOSE"]


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (100 * (c - h), 100 * (c + h))


spy = datos.ohlc("SPY")
S = spy.index
C = spy.c.values
DD = ((spy.c / spy.h.rolling(252, min_periods=200).max() - 1) * 100)
t3 = (cargar("cboe_vix.csv") / cargar("cboe_vix3m.csv")).dropna()
T3 = t3.reindex(S, method="ffill")
semana = S.to_period("W-SUN")
ultima = np.r_[np.asarray(semana[1:] != semana[:-1]), True]
VIERNES = S[ultima]


def episodios(inicio):
    ev, vivo, ini, ult_pos = [], False, None, None
    for d, t in t3.items():
        if d > FIN_ERA:
            break
        if not vivo and t >= inicio:
            vivo, ini = True, d
        elif vivo and t < 1.0:
            vivo = False
            x = DD.get(d)
            if x is not None and x == x and x <= DD_MIN:
                pos = S.searchsorted(d)
                if ult_pos is None or pos - ult_pos >= SEPARACION:
                    ev.append((ini, d))
                    ult_pos = pos
    return ev


def entrada(E):
    i = VIERNES.searchsorted(E)
    return S.get_loc(VIERNES[i])


def fwd(p, h):
    return C[p + h] / C[p] - 1 if p + h < len(C) else np.nan


def peor60(p):
    seg = C[p + 1:p + 61]
    return (seg.min() / C[p] - 1) if len(seg) else np.nan


def variante(h):
    ev = episodios(ARRANQUE)
    pos_ev = [entrada(E) for _, E in ev]
    filas = []
    for (ini, E), p in zip(ev, pos_ev):
        mitad = "aprender" if E <= FIN_APRENDER else "comprobar"
        lo, hi = (INICIO_ERA, FIN_APRENDER) if mitad == "aprender" else (FIN_APRENDER + pd.Timedelta(days=1), FIN_ERA)
        cand = []
        for q_date in VIERNES[(VIERNES >= lo) & (VIERNES <= hi)]:
            q = S.get_loc(q_date)
            if q + h >= len(C):
                continue
            if abs(DD.iloc[q] - DD.iloc[p]) > BANDA:
                continue
            if not (T3.iloc[q] >= 1.0):          # <<< lo único que cambia respecto a I-004: pánico VIVO ese viernes
                continue
            if any(abs(q - pp) < SEPARACION for pp in pos_ev):
                continue
            cand.append(q)
        r = fwd(p, h)
        rc = np.array([fwd(q, h) for q in cand])
        pc = np.array([peor60(q) for q in cand])
        filas.append(dict(salida=E.date(), arranque=ini.date(), entrada=S[p].date(), dd=round(DD.iloc[p], 1), mitad=mitad,
                          ret=100 * r, ctrl=100 * rc.mean() if len(rc) else np.nan,
                          exceso=100 * (r - rc.mean()) if len(rc) else np.nan, nctrl=len(rc),
                          peor60=100 * peor60(p), peor60_ctrl=100 * pc.mean() if len(pc) else np.nan,
                          dpeor=100 * (peor60(p) - pc.mean()) if len(pc) else np.nan, _rc=rc))
    return pd.DataFrame(filas)


def tstat(x):
    x = np.asarray(x, float)
    n = len(x)
    return x.mean() / (x.std(ddof=1) / math.sqrt(n)) if n > 2 and x.std(ddof=1) > 0 else float("nan")


def resumen(df, etiqueta):
    d = df.dropna(subset=["exceso"])
    n = len(d)
    if n == 0:
        return f"{etiqueta:<10}: sin episodios"
    ex = d.exceso.values
    pos = int((ex > 0).sum())
    lo, hi = wilson(pos, n)
    dp = d.dpeor.values
    return (f"{etiqueta:<10} N={n:2d}  ret medio {d.ret.mean():6.2f}%  azar(pánico vivo) {d.ctrl.mean():6.2f}%  "
            f"exceso {ex.mean():6.2f} pts  t={tstat(ex):5.2f}  >0: {pos}/{n} ({100*pos/n:3.0f}%, IC {lo:3.0f}-{hi:3.0f})  "
            f"peor ret {d.ret.min():6.1f}%  | peor caída 60s: ep {d.peor60.mean():6.1f}% azar {d.peor60_ctrl.mean():6.1f}% "
            f"dif {dp.mean():5.2f} pts (t {tstat(dp):5.2f})")


def aleatorio(df):
    d = df.dropna(subset=["exceso"])
    d = d[d._rc.apply(len) > 0]
    if not len(d):
        return float("nan"), float("nan")
    obs = d.ret.mean() / 100
    sims = np.array([np.mean([rng.choice(x) for x in d._rc]) for _ in range(B)])
    return (1 + (sims >= obs).sum()) / (B + 1), sims.mean() * 100


if __name__ == "__main__":
    print(f"SPY {S[0].date()} → {S[-1].date()}; t3 {t3.index[0].date()} → {t3.index[-1].date()}; era de estudio hasta {FIN_ERA.date()}")
    res = {}
    for nombre, h in (("20 ses.", 20), ("60 ses. PRINCIPAL", 60), ("120 ses.", 120)):
        df = variante(h)
        res[h] = df
        print("\n===", nombre, "· episodios:", len(df))
        for m in ("aprender", "comprobar"):
            print(resumen(df[df.mitad == m], m))
        print(resumen(df, "TODOS"))
        p, mc = aleatorio(df)
        print(f"  azar aleatorio (1 viernes de pánico vivo por episodio, {B} sorteos): media {mc:.2f}%  p(azar >= episodios) = {p:.3f}")
    print("\n=== DETALLE principal (60 sesiones) por episodio ===")
    print(res[60][["salida", "entrada", "dd", "mitad", "ret", "ctrl", "exceso", "nctrl", "peor60", "peor60_ctrl"]].round(1).to_string(index=False))
    n_sin = int((res[60].nctrl == 0).sum())
    print(f"\nEpisodios sin ningún viernes de comparación (excluidos del promedio): {n_sin}")
