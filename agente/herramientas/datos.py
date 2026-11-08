"""
DATOS PARA LAS INVESTIGACIONES DEL AGENTE (sin IA).

El workflow los descarga en /tmp/agente/datos antes de que entre el agente (los viernes),
así el agente gasta sus pasos en pensar y no en descargar.

Uso dentro de un estudio:
    import sys; sys.path.insert(0, "agente/herramientas"); import datos
    spy = datos.ohlc("SPY")          # apertura/máximo/mínimo/cierre AJUSTADOS (o, h, l, c), desde 1995; también acciones del S&P
    sp = datos.sp500()               # S&P 500 diario desde 1927 (índice de precio), empalmado con el SPY hasta hoy
    cl, hi = datos.universo()        # cierres y máximos de los 88 ETF de la terminal desde 2000 (del repositorio)
    x3 = datos.apalancado(spy.c, 3)  # ETF apalancado diario simulado, con costes
    E = datos.caidas(sp, 0.05)       # todas las caídas que tocaron −5 % desde el máximo de 52 semanas
    lo, hi = datos.wilson(12, 30)    # intervalo de confianza del 95 % de 12 aciertos en 30

Línea de comandos:  python agente/herramientas/datos.py --descargar
"""
import os
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

DIR = Path(os.environ.get("AGENTE_DATOS", "/tmp/agente/datos"))
RAIZ = Path(__file__).resolve().parents[2]
HIST = RAIZ / "historico_seguimiento_NO_BORRAR"
FUENTES = {
    # precios diarios de todas las acciones del S&P (con su pertenencia histórica) y de ~30 ETF, 1995 → hoy
    "prices.parquet": "https://github.com/Johnbrick123/sp500-data/releases/download/data/prices.parquet",
    "membership_intervals.parquet": "https://github.com/Johnbrick123/sp500-data/releases/download/data/membership_intervals.parquet",
    # S&P 500 diario desde 1885 (índice de precio)
    "sp500_1885.csv": "https://raw.githubusercontent.com/SteelCerberus/us-market-data/main/data/us_market_data.csv",
}


def descargar(forzar=False):
    DIR.mkdir(parents=True, exist_ok=True)
    for nombre, url in FUENTES.items():
        dst = DIR / nombre
        if dst.exists() and dst.stat().st_size > 0 and not forzar:
            continue
        for intento in range(3):
            try:
                print("descargando", nombre, "…", flush=True)
                urllib.request.urlretrieve(url, dst)
                print("  ok", round(dst.stat().st_size / 1e6, 1), "MB")
                break
            except Exception as e:  # noqa: BLE001
                print("  fallo:", type(e).__name__, e)


_PRECIOS = None


def _tabla(ticker, columnas):
    import pyarrow.dataset as ds
    global _PRECIOS
    if _PRECIOS is None:
        _PRECIOS = ds.dataset(str(DIR / "prices.parquet"))
    x = _PRECIOS.to_table(filter=ds.field("ticker") == ticker, columns=["date"] + columnas).to_pandas()
    if x.empty:
        raise KeyError(f"{ticker} no está en prices.parquet")
    x["date"] = pd.to_datetime(x["date"])
    return x.set_index("date").sort_index()


def ohlc(ticker):
    """Velas diarias AJUSTADAS (dividendos y desdoblamientos) de un ETF o acción del S&P: columnas o, h, l, c, v."""
    x = _tabla(ticker, ["open", "high", "low", "close", "adj_close", "volume"])
    f = x.adj_close / x.close
    d = pd.DataFrame({"o": x.open * f, "h": x.high * f, "l": x.low * f, "c": x.adj_close, "v": x.volume})
    return d[(d.h >= d.l) & (d.c > 0)]


def sp500():
    """S&P 500 diario (cierre, índice de precio) desde 1927, empalmado con el SPY (sin dividendos) hasta hoy."""
    h = pd.read_csv(DIR / "sp500_1885.csv", usecols=["Date", "Close"], parse_dates=["Date"]).set_index("Date").Close
    h = h[h.index >= "1927-01-01"]
    try:
        spy = _tabla("SPY", ["close"]).close
        d0 = h.index[-1]
        if d0 in spy.index:
            h = pd.concat([h, spy[spy.index > d0] * (h.loc[d0] / spy.loc[d0])])
    except Exception as e:  # noqa: BLE001
        print("sp500: sin empalme con SPY:", e)
    return h.sort_index().rename("c")


def universo():
    """Cierres y máximos diarios ajustados de los 88 ETF de la terminal desde 2000 (los guarda la terminal)."""
    cl = pd.read_csv(HIST / "historiales" / "universo_close.csv.gz", index_col=0, parse_dates=True)
    hi = pd.read_csv(HIST / "historiales" / "universo_high.csv.gz", index_col=0, parse_dates=True)
    return cl, hi


def apalancado(cierre, L, coste=0.0095, financiacion=0.02):
    """ETF apalancado diario simulado: L × rendimiento − (L−1) × financiación − coste anual."""
    r = cierre.pct_change().fillna(0)
    extra = (L - 1) * financiacion / 252 + (coste / 252 if L > 1 else 0)
    return (1 + L * r - extra).cumprod()


def caidas(cierre, umbral=0.05, ventana=252, max_ses=750):
    """Episodios que tocan `umbral` bajo el máximo de `ventana` sesiones (como el detector de la terminal).
    Columnas: pico, toca, s_toca (sesiones del pico al toque), suelo, s_suelo, prof (%), recupera, s_total."""
    c = cierre.dropna().values
    idx = cierre.dropna().index
    mx = pd.Series(c).rolling(ventana, min_periods=60).max().values
    filas, armado, i, n = [], True, 0, len(c)
    while i < n:
        if np.isnan(mx[i]):
            i += 1
            continue
        if c[i] >= mx[i]:
            armado = True
        if armado and c[i] / mx[i] - 1 <= -umbral:
            armado = False
            P = mx[i]
            a = max(0, i - ventana + 1)
            ip = a + int(np.argmax(c[a:i + 1]))
            j, fin = i, min(n, i + max_ses)
            while j < fin and c[j] < P:
                j += 1
            seg = c[i:j] if j > i else c[i:i + 1]
            kb = int(np.argmin(seg))
            filas.append(dict(pico=idx[ip], toca=idx[i], s_toca=i - ip, suelo=idx[i + kb], s_suelo=i + kb - ip,
                              prof=round((seg[kb] / P - 1) * 100, 2), recupera=bool(j < n and c[min(j, n - 1)] >= P),
                              s_total=j - ip))
        i += 1
    return pd.DataFrame(filas)


def wilson(k, n, z=1.96):
    """Intervalo de confianza del 95 % (en %) de k aciertos en n casos."""
    if n == 0:
        return (None, None)
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (round(100 * (c - h), 1), round(100 * (c + h), 1))


if __name__ == "__main__":
    if "--descargar" in sys.argv:
        descargar(forzar="--forzar" in sys.argv)
