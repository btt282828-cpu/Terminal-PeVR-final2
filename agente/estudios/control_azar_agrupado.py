"""Control de azar del marcador, versión AGRUPADA POR FECHA (20-nov-2026). Es una comprobación del notario, no una idea nueva.
Igual que control_azar_marcador.py (neto = exceso del episodio - media del exceso del MISMO activo en todas las fechas
del periodo del cable), pero añade lo que aquel no cuenta: varias señales el mismo día (activos distintos, mismo mercado)
no son pruebas independientes. Aquí se promedian los netos de cada fecha y la t se calcula entre FECHAS.
Uso (desde la raíz del repo, tras preparar.py):  python agente/estudios/control_azar_agrupado.py
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
    s = px[sym].dropna()
    r = s.shift(-H) / s - 1
    rs = (spy.shift(-H) / spy - 1).reindex(s.index)
    x = (r - rs).dropna()
    return x[(x.index >= desde) & (x.index <= hasta)]


def t_de(v):
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
    filas.append(dict(senal=r.senal, d=r.d, sym=r.sym, dir=r.dir, y=r.x20 - r.dir * base.mean() * 100))
Y = pd.DataFrame(filas)
print(f"\n{'señal':<9}{'N ep.':>6}{'N fechas':>9}{'neto medio':>11}{'t episodios':>13}{'t por fechas':>14}")
for s, g in Y.groupby("senal"):
    if len(g) < 8:
        continue
    por_fecha = g.groupby("d").y.mean()
    print(f"{s:<9}{len(g):>6}{len(por_fecha):>9}{g.y.mean():>11.2f}{t_de(g.y):>13.2f}{t_de(por_fecha):>14.2f}")
