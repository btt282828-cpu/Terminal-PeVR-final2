"""Control de azar del marcador (13-nov-2026). NO es una idea nueva: es la comprobación del notario.
Pregunta: el «exceso frente al SPY» de cada señal ¿es de la señal, o es lo que ese mismo activo hacía en esa época
con o sin señal?  Se resta, a cada episodio, la media del exceso a 20 sesiones del MISMO activo en todas las fechas
posibles del periodo del cable (misma exposición, mismas fechas).  y = dir * (exceso del episodio - media del activo).
Uso (desde la raíz del repo, tras preparar.py):  python agente/estudios/control_azar_marcador.py
"""
import importlib.util
import json
import math

import numpy as np
import pandas as pd

spec = importlib.util.spec_from_file_location("preparar", "agente/preparar.py")
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)

H = 20
m = json.load(open("agente/hoy/marcador.json"))
E = pd.DataFrame(m["episodios"])
E["d"] = pd.to_datetime(E.date)
px, fuente = P.precios(list(E.sym.unique()) + ["SPY"], E.d.min() - pd.Timedelta(days=10))
print("precios:", fuente, "hasta", px.index.max().date())
spy = px["SPY"].dropna()


def exceso_serie(sym, desde, hasta):
    """exceso a H sesiones (activo - SPY), para cada sesión de entrada entre desde y hasta."""
    s = px[sym].dropna()
    r = s.shift(-H) / s - 1
    rs = (spy.shift(-H) / spy - 1).reindex(s.index)
    x = (r - rs).dropna()
    return x[(x.index >= desde) & (x.index <= hasta)]


def wilson_t(v):
    v = np.asarray(v, float)
    n = len(v)
    return v.mean() / (v.std(ddof=1) / math.sqrt(n)) if n > 2 and v.std(ddof=1) > 0 else float("nan")


ok = E[(E.e20 == "ok") & E.x20.notna()].copy()
f0 = E.d.min() + pd.Timedelta(days=1)
f1 = ok.d.max() + pd.Timedelta(days=1)
filas = []
for _, r in ok.iterrows():
    base = exceso_serie(r.sym, f0, f1)
    if len(base) < 10:
        continue
    filas.append(dict(senal=r.senal, sym=r.sym, dir=r.dir, x=r.x20, base=base.mean() * 100, y=r.x20 - r.dir * base.mean() * 100))
Y = pd.DataFrame(filas)
print(f"\nepisodios medidos a {H} ses.: {len(ok)}; con línea base del activo: {len(Y)}; fechas de entrada posibles {f0.date()} → {f1.date()}\n")
print(f"{'señal':<9}{'N':>4}{'exceso (marcador)':>19}{'  línea base del activo':>24}{'  exceso neto':>14}{'  t neto':>9}")
for s, g in Y.groupby("senal"):
    if len(g) < 8:
        continue
    print(f"{s:<9}{len(g):>4}{g.x.mean():>19.2f}{(g.dir*g.base).mean():>24.2f}{g.y.mean():>14.2f}{wilson_t(g.y):>9.2f}")
print("\nActivos más repetidos en GIRO↑ y GIRO↓ (episodios medidos):")
for s in ("GIRO↑", "GIRO↓"):
    g = Y[Y.senal == s]
    print(s, g.sym.value_counts().head(8).to_dict())
