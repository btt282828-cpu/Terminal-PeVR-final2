"""I-004 (13-nov-2026): ¿«se va el pánico» (VIX/VIX3M vuelve bajo 1,0) es mejor entrada que un viernes cualquiera
de una caída parecida?  Diseño apuntado en agente/ideas.md ANTES de calcular rendimientos.

Uso (desde la raíz del repositorio):  python agente/estudios/i004.py
La caja cerrada (2023 en adelante) NO se usa para los episodios ni para los viernes de comparación.
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
SEPARACION = 20      # sesiones mínimas entre episodios (y entre episodio y viernes de comparación)
DD_MIN = -3.0        # el SPY al menos -3 % bajo su máximo de 52 semanas el día en que «se va»
BANDA = 2.5          # viernes de comparación: caída a ±2,5 puntos de la del episodio
B = 5000
rng = np.random.default_rng(4)


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
ultima = np.r_[np.asarray(semana[1:] != semana[:-1]), True]   # última sesión de cada semana (el viernes)
VIERNES = S[ultima]


def episodios(inicio):
    """Estado del detector: arranca con t3 >= inicio; «se va» = primer cierre con t3 < 1,0. Devuelve [(arranque, se_va)]."""
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


def variante(nombre, inicio, h):
    ev = episodios(inicio)
    pos_ev = [entrada(E) for _, E in ev]
    filas = []
    for (ini, E), p in zip(ev, pos_ev):
        mitad = "aprender" if E <= FIN_APRENDER else "comprobar"
        lo, hi = (INICIO_ERA, FIN_APRENDER) if mitad == "aprender" else (FIN_APRENDER + pd.Timedelta(days=1), FIN_ERA)
        # viernes de comparación
        cand = []
        for q_date in VIERNES[(VIERNES >= lo) & (VIERNES <= hi)]:
            q = S.get_loc(q_date)
            if q + h >= len(C):
                continue
            if abs(DD.iloc[q] - DD.iloc[p]) > BANDA:
                continue
            if not (T3.iloc[q] < 1.0):
                continue
            if any(abs(q - pp) < SEPARACION for pp in pos_ev):
                continue
            cand.append(q)
        r = fwd(p, h)
        rc = np.array([fwd(q, h) for q in cand])
        pc = np.array([peor60(q) for q in cand])
        filas.append(dict(salida=E.date(), arranque=ini.date(), entrada=S[p].date(), dd=round(DD.iloc[p], 1), mitad=mitad,
                          ret=100 * r, ctrl=100 * rc.mean() if len(rc) else np.nan, exceso=100 * (r - rc.mean()) if len(rc) else np.nan,
                          nctrl=len(rc), peor60=100 * peor60(p), peor60_ctrl=100 * pc.mean() if len(pc) else np.nan,
                          _rc=rc))
    return pd.DataFrame(filas)


def resumen(df, etiqueta):
    d = df.dropna(subset=["exceso"])
    n = len(d)
    if n == 0:
        return f"{etiqueta}: sin episodios"
    ex = d.exceso.values
    t = ex.mean() / (ex.std(ddof=1) / math.sqrt(n)) if n > 2 and ex.std(ddof=1) > 0 else float("nan")
    pos = int((ex > 0).sum())
    lo, hi = wilson(pos, n)
    return (f"{etiqueta:<22} N={n:2d}  ret medio {d.ret.mean():6.2f}%  azar {d.ctrl.mean():6.2f}%  exceso {ex.mean():6.2f} pts  "
            f"t={t:5.2f}  >0: {pos}/{n} ({100*pos/n:3.0f}%, IC {lo:3.0f}-{hi:3.0f})  peor ret {d.ret.min():6.1f}%  peor exceso {ex.min():6.1f}")


def aleatorio(df):
    d = df.dropna(subset=["exceso"])
    d = d[d._rc.apply(len) > 0]
    if not len(d):
        return float("nan"), float("nan")
    obs = d.ret.mean() / 100
    sims = np.array([np.mean([rng.choice(x) for x in d._rc]) for _ in range(B)])
    return (1 + (sims >= obs).sum()) / (B + 1), sims.mean() * 100


VARIANTES = [("C-60 (>=1,00) PRINCIPAL", 1.00, 60), ("B-60 (>=1,05)", 1.05, 60), ("A-60 (>=1,10 exacta)", 1.10, 60),
             ("C-20 (>=1,00)", 1.00, 20), ("C-120 (>=1,00)", 1.00, 120)]

if __name__ == "__main__":
    print(f"SPY {S[0].date()} → {S[-1].date()}; t3 {t3.index[0].date()} → {t3.index[-1].date()}; era de estudio hasta {FIN_ERA.date()}")
    guardar = {}
    for nombre, u, h in VARIANTES:
        df = variante(nombre, u, h)
        guardar[nombre] = df
        print("\n===", nombre, "· episodios:", len(df))
        for m in ("aprender", "comprobar"):
            print(resumen(df[df.mitad == m], m))
        print(resumen(df, "TODOS"))
        p, mc = aleatorio(df)
        print(f"  azar aleatorio (1 viernes por episodio, {B} sorteos): media {mc:.2f}%  p(azar >= episodios) = {p:.3f}")
        print(f"  peor caída posterior (60 ses.): episodios {df.peor60.mean():.1f}% de media, azar {df.peor60_ctrl.mean():.1f}%; peor episodio {df.peor60.min():.1f}%")
    # detalle de la variante exacta A a 20 / 60 / 120 ses. (descriptivo)
    print("\n=== DETALLE variante exacta A (arranque >= 1,10), SPY ===")
    d20, d60, d120 = (variante("A", 1.10, h) for h in (20, 60, 120))
    det = d60[["arranque", "salida", "entrada", "dd", "mitad", "ret", "ctrl", "exceso", "nctrl", "peor60"]].copy()
    det["ret20"], det["ret120"] = d20.ret.values, d120.ret.values
    print(det.round(1).to_string(index=False))
    print("\n=== DETALLE variante principal C-60 por episodio ===")
    print(guardar["C-60 (>=1,00) PRINCIPAL"][["salida", "entrada", "dd", "mitad", "ret", "ctrl", "exceso", "nctrl", "peor60"]].round(1).to_string(index=False))
