#!/usr/bin/env python3
"""I-007 (22-nov-2026): volumen en dólares de los ETF apalancados «de compra» y caídas del SPY.
Reglas fijadas en agente/ideas.md ANTES de calcular nada. Uso:  python3 agente/estudios/i007.py
Datos: Yahoo (8 ETF apalancados sin ajustar: cierre x volumen; SPY ajustado) y VIX / VIX3M de historiales/."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

RAIZ = Path(__file__).resolve().parents[2]
HIST = RAIZ / "historico_seguimiento_NO_BORRAR" / "historiales"
ETFS = ["TQQQ", "UPRO", "SPXL", "SSO", "QLD", "SOXL", "TECL", "TNA"]
VENT = 252
SALIDA = Path("/tmp/agente/i007_out.json")


def bajar():
    d = yf.download(ETFS, start="2006-01-01", end="2026-11-23", auto_adjust=False, progress=False, threads=True)
    dv = (d["Close"] * d["Volume"]).astype(float).where(d["Volume"] > 0)
    spy = yf.download("SPY", start="1999-01-01", end="2026-11-23", auto_adjust=True, progress=False)
    spy.columns = [c[0] if isinstance(c, tuple) else c for c in spy.columns]
    return dv, spy


def serie_z(dv):
    """z de ln(suma de dólares) frente a los 252 días anteriores, con los ETF que existían en toda esa ventana."""
    arr = dv.values
    z = np.full(len(dv), np.nan)
    nset = np.zeros(len(dv), dtype=int)
    for i in range(VENT, len(dv)):
        w = arr[i - VENT:i + 1]
        ok = ~np.isnan(w).any(axis=0)
        if ok.sum() == 0:
            continue
        L = np.log(w[:, ok].sum(axis=1))
        prev = L[:-1]
        sd = prev.std(ddof=1)
        if sd > 0:
            z[i] = (L[-1] - prev.mean()) / sd
        nset[i] = int(ok.sum())
    return pd.Series(z, index=dv.index), pd.Series(nset, index=dv.index)


def leer_cboe(nombre):
    d = pd.read_csv(HIST / nombre)
    d.columns = [str(c).strip().upper() for c in d.columns]
    return pd.Series(pd.to_numeric(d["CLOSE"], errors="coerce").values,
                     index=pd.to_datetime(d["DATE"], format="mixed", errors="coerce")).dropna().sort_index()


def trozo(f):
    return "aprender" if f.year <= 2018 else "comprobar" if f.year <= 2022 else "caja"


def episodios(df, zmin, ddmax, act=1):
    zz = df["z"].rolling(act, min_periods=1).max() if act > 1 else df["z"]
    flag = ((zz >= zmin) & (df["dd"] <= -ddmax)).values
    eps, ult = [], -10 ** 9
    for i in np.flatnonzero(flag):
        if i - ult >= 10:
            eps.append(i)
        ult = i
    return eps


def evaluar(df, eps, ddmax, fear_only=False):
    """Exceso de cada episodio frente a sus días parecidos (sin pico, misma mitad, caída ±2,5 pts, mismo miedo)."""
    filas = []
    tr = df.index.map(trozo)
    for i in eps:
        r = df.iloc[i]
        if fear_only and not (r["ratio"] >= 1.0):
            continue
        ctrl = df[(tr == trozo(df.index[i])) & (df["dd"] <= -ddmax) & (df["z"] < 1.0)
                  & ((df["dd"] - r["dd"]).abs() <= 0.025) & ((df["ratio"] >= 1.0) == (r["ratio"] >= 1.0))]
        fila = {"fecha": str(df.index[i].date()), "trozo": trozo(df.index[i]), "dd": float(r["dd"]), "z": float(r["z"]),
                "ratio": (None if pd.isna(r["ratio"]) else float(r["ratio"])), "n_ctrl": int(len(ctrl))}
        for h in ("f20", "f60", "w60"):
            if pd.isna(r[h]):
                fila[h] = None
                fila["ex_" + h] = None
                continue
            c = ctrl[h].dropna()
            fila[h] = float(r[h])
            fila["ex_" + h] = float(r[h] - c.mean()) if len(c) >= 3 else None
        filas.append(fila)
    return filas


def resumen(filas, clave):
    out = {}
    for t in ("aprender", "comprobar", "caja", "todos"):
        x = np.array([f[clave] for f in filas if f[clave] is not None and (t == "todos" or f["trozo"] == t)], dtype=float)
        if len(x) == 0:
            out[t] = {"N": 0}
            continue
        sd = x.std(ddof=1) if len(x) > 1 else np.nan
        out[t] = {"N": int(len(x)), "media_pts": round(100 * x.mean(), 2),
                  "t": (round(float(x.mean() / (sd / np.sqrt(len(x)))), 2) if len(x) > 1 and sd > 0 else None),
                  "pos": round(float((x > 0).mean()), 2)}
    return out


def main():
    dv, spy = bajar()
    z, nset = serie_z(dv)
    c = spy["Close"].astype(float)
    dd = c / spy["High"].astype(float).rolling(252, min_periods=60).max() - 1
    vix, v3 = leer_cboe("cboe_vix.csv"), leer_cboe("cboe_vix3m.csv")
    ratio = (vix / v3).dropna()
    df = pd.DataFrame({"c": c, "dd": dd}).join(z.rename("z"), how="left").join(ratio.rename("ratio"), how="left")
    df["ratio"] = df["ratio"].ffill(limit=5)
    n = len(df)
    for h, k in ((20, "f20"), (60, "f60")):
        df[k] = df["c"].shift(-h) / df["c"] - 1
    df["w60"] = [(df["c"].iloc[i + 1:i + 61].min() / df["c"].iloc[i] - 1) if i + 60 < n else np.nan for i in range(n)]
    df = df[(df.index >= "2010-01-01") & df["z"].notna() & df["dd"].notna()].copy()
    res = {"n_dias": int(len(df)), "primer_dia": str(df.index[0].date()), "ultimo_dia": str(df.index[-1].date()),
           "hoy": {"fecha": str(df.index[-1].date()), "z": round(float(df["z"].iloc[-1]), 2), "dd": round(float(df["dd"].iloc[-1]), 4),
                   "ratio": (None if pd.isna(df["ratio"].iloc[-1]) else round(float(df["ratio"].iloc[-1]), 2)),
                   "etf_en_la_suma": int(nset.reindex(df.index).iloc[-1])},
           "dias_pico_z2": int((df["z"] >= 2).sum()), "dias_pico_z2_en_caida8": int(((df["z"] >= 2) & (df["dd"] <= -0.08)).sum()),
           "top_z": [(str(f.date()), round(float(r["z"]), 2), round(float(r["dd"]), 3)) for f, r in df.sort_values("z", ascending=False).head(15).iterrows()]}
    variantes = {"V1_z2_dd8": dict(zmin=2, ddmax=0.08), "V2_z3_dd8": dict(zmin=3, ddmax=0.08),
                 "V3_z2_3dias_dd8": dict(zmin=2, ddmax=0.08, act=3), "V4_z2_dd5": dict(zmin=2, ddmax=0.05),
                 "V5_z2_dd8_miedo": dict(zmin=2, ddmax=0.08, fear_only=True)}
    res["variantes"] = {}
    for nombre, p in variantes.items():
        eps = episodios(df, p["zmin"], p["ddmax"], p.get("act", 1))
        filas = evaluar(df, eps, p["ddmax"], p.get("fear_only", False))
        res["variantes"][nombre] = {"episodios_total": len(filas),
                                    "ex_f60": resumen(filas, "ex_f60"), "ex_f20": resumen(filas, "ex_f20"), "ex_w60": resumen(filas, "ex_w60"),
                                    "lista": filas if nombre == "V1_z2_dd8" else None}
    # descriptivo: caídas del SPY >= 10 % desde 2010
    caidas, armada, s = [], True, None
    dd_ = df["dd"].values
    for i in range(len(df)):
        if armada and dd_[i] <= -0.10:
            s, armada = i, False
        if (not armada) and (dd_[i] > -0.03 or i == len(df) - 1):
            e = i
            seg = df.iloc[s:e + 1]
            sp = seg[seg["z"] >= 2]
            fila = {"inicio": str(seg.index[0].date()), "fin": str(seg.index[-1].date()), "dd_min": round(float(seg["dd"].min()), 3),
                    "fecha_min": str(seg["c"].idxmin().date()), "z_max": round(float(seg["z"].max()), 2), "fecha_zmax": str(seg["z"].idxmax().date()),
                    "n_dias_z2": int(len(sp))}
            if len(sp):
                j = df.index.get_loc(sp.index[0])
                fila.update({"primer_pico": str(sp.index[0].date()), "dd_en_pico": round(float(df["dd"].iloc[j]), 3),
                             "f20": None if pd.isna(df["f20"].iloc[j]) else round(float(df["f20"].iloc[j]), 3),
                             "f60": None if pd.isna(df["f60"].iloc[j]) else round(float(df["f60"].iloc[j]), 3),
                             "w60": None if pd.isna(df["w60"].iloc[j]) else round(float(df["w60"].iloc[j]), 3)})
            caidas.append(fila)
            armada = True
    res["caidas10"] = caidas
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("variantes", "caidas10")}, ensure_ascii=False, indent=1))
    for nombre, v in res["variantes"].items():
        print("\n==", nombre, "episodios:", v["episodios_total"])
        for k in ("ex_f60", "ex_f20", "ex_w60"):
            print("  ", k, json.dumps(v[k], ensure_ascii=False))
    print("\nCAÍDAS del SPY >= 10 % desde 2010:")
    for f in caidas:
        print("  ", json.dumps(f, ensure_ascii=False))


if __name__ == "__main__":
    main()
