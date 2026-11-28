"""I-006 · ¿Importa lo rápido que la caída del S&P va del −5 % al −10 %? (¿llega después al −20 %?)
Reglas fijadas el 20-nov-2026 en agente/ideas.md (no se tocan después de ver resultados).
Uso (desde la raíz del repo):  python agente/estudios/i006.py

Detalles de implementación que NO dependen del resultado (fijados antes de calcular):
- Episodio = fila de datos.caidas(sp, 0.10). Su toque del −5 % = la fila de datos.caidas(sp, 0.05) con la MISMA fecha de pico;
  si no hay pareja exacta, el primer cierre ≥ 5 % bajo ese mismo pico (se cuenta cuántas veces pasa).
- v = sesiones entre el toque del −5 % y el del −10 % (posiciones en la serie). 'Rápida' = v ≤ V; 'lenta' = v > V.
- Resultado = la caída llega a −20 % bajo ese pico antes de recuperarlo (prof ≤ −20, comprobado con la fila de caidas(sp, 0.20)).
- Episodios sin resolver (el de 2026) se excluyen del resultado. Trozos por fecha del toque del −10 %:
  A = 1927-1974, B = 1975-2022. La caja (2023 en adelante) NO se abre.
- Veredicto: CONFIRMA si en A y en B la diferencia rápidas−lentas es ≥ 15 pts del mismo signo, las 4 casillas tienen N ≥ 8 y
  Fisher (todos A+B) p < 0,05; 'NO CONCLUYENTE' si alguna casilla tiene N < 8; si no, TUMBADA.
"""
import math
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "agente/herramientas")
import datos  # noqa: E402

V_LISTA = (10, 15, 20)  # la principal es 15


def fisher_dos_colas(a, b, c, d):
    """Fisher exacto de dos colas para [[a,b],[c,d]]."""
    n1, n2, k = a + b, c + d, a + c
    tot = n1 + n2

    def p(x):
        return math.comb(n1, x) * math.comb(n2, k - x) / math.comb(tot, k)

    lo, hi = max(0, k - n2), min(n1, k)
    p0 = p(a)
    return min(1.0, sum(p(x) for x in range(lo, hi + 1) if p(x) <= p0 * (1 + 1e-9)))


def main():
    sp = datos.sp500().dropna()
    idx = sp.index
    c = sp.values
    n = len(sp)
    pos = {d: i for i, d in enumerate(idx)}
    print(f"S&P 500: {n} cierres, {idx[0].date()} → {idx[-1].date()}")
    wd = pd.Series(idx.dayofweek).groupby(idx.year < 1953).value_counts().unstack(fill_value=0)
    print("Días de la semana (False=1953+, True=hasta 1952; 5 = sábado):\n", wd.to_string())

    E10 = datos.caidas(sp, 0.10)
    E05 = datos.caidas(sp, 0.05)
    E20 = datos.caidas(sp, 0.20)
    print(f"episodios: −5 % {len(E05)}, −10 % {len(E10)}, −20 % {len(E20)}")
    m5 = E05.drop_duplicates("pico").set_index("pico")
    p20 = set(E20["pico"])

    filas = []
    for _, r in E10.iterrows():
        ip, i10 = pos[r.pico], pos[r.toca]
        P = c[ip]
        if r.pico in m5.index:
            t5, emparejado = m5.loc[r.pico, "toca"], True
            i5 = pos[t5]
        else:
            emparejado = False
            i5 = next(j for j in range(ip, i10 + 1) if c[j] / P - 1 <= -0.05)
        v = i10 - i5
        sin_resolver = (not r.recupera) and (i10 + 750 >= n)
        llega20 = bool(r.prof <= -20.0)
        coincide = (llega20 == (r.pico in p20))
        filas.append(dict(pico=r.pico, t5=idx[i5], t10=r.toca, v=v, prof=r.prof, recupera=r.recupera, llega20=llega20,
                          sin_resolver=sin_resolver, emparejado=emparejado, coincide_E20=coincide,
                          sesiones_pico_a_10=i10 - ip))
    D = pd.DataFrame(filas)
    D["anio"] = D.t10.dt.year
    D["trozo"] = np.where(D.anio <= 1974, "A", np.where(D.anio <= 2022, "B", "caja"))
    print("sin pareja exacta en −5 %:", int((~D.emparejado).sum()), "| llega20 ≠ fila de caidas(0.20):", int((~D.coincide_E20).sum()))
    print(D.groupby("trozo").size().to_dict(), "| sin resolver:", int(D.sin_resolver.sum()))
    D.to_csv("/tmp/agente/i006_episodios.csv", index=False)

    U = D[(~D.sin_resolver) & (D.trozo != "caja")].copy()
    print(f"\nEpisodios usados: {len(U)} (A {int((U.trozo=='A').sum())}, B {int((U.trozo=='B').sum())}); llegan a −20 %: "
          f"{int(U.llega20.sum())} de {len(U)} ({100*U.llega20.mean():.0f} %)")
    print("v (sesiones del −5 % al −10 %): mediana", U.v.median(), "| cuartiles", U.v.quantile([.25, .75]).tolist(),
          "| máx", U.v.max())

    for V in V_LISTA:
        print(f"\n=== V = {V}{'  (PRINCIPAL)' if V == 15 else ''} ===")
        res = {}
        for t in ("A", "B", "A+B"):
            S = U if t == "A+B" else U[U.trozo == t]
            f, l = S[S.v <= V], S[S.v > V]
            kf, nf, kl, nl = int(f.llega20.sum()), len(f), int(l.llega20.sum()), len(l)
            pf = 100 * kf / nf if nf else float("nan")
            pl = 100 * kl / nl if nl else float("nan")
            wf, wl = datos.wilson(kf, nf), datos.wilson(kl, nl)
            pv = fisher_dos_colas(kf, nf - kf, kl, nl - kl) if nf and nl else float("nan")
            print(f"  {t:3s} rápidas {kf}/{nf} = {pf:.0f} % (IC {wf[0]}–{wf[1]}) | lentas {kl}/{nl} = {pl:.0f} % (IC {wl[0]}–{wl[1]})"
                  f" | dif {pf-pl:+.0f} pts | Fisher p {pv:.3f}")
            res[t] = (nf, nl, pf - pl if nf and nl else float("nan"), pv)
        celdas_ok = all(res[t][0] >= 8 and res[t][1] >= 8 for t in ("A", "B"))
        mism = (res["A"][2] * res["B"][2] > 0) if not (math.isnan(res["A"][2]) or math.isnan(res["B"][2])) else False
        grande = abs(res["A"][2]) >= 15 and abs(res["B"][2]) >= 15
        if not celdas_ok:
            ver = "NO CONCLUYENTE (alguna casilla con N < 8)"
        elif mism and grande and res["A+B"][3] < 0.05:
            ver = "CONFIRMA"
        else:
            ver = "TUMBADA"
        print("  Veredicto:", ver)

    h = D[D.trozo == "caja"]
    print("\nEpisodios de la caja (solo se cuentan, NO se miden resultados):", len(h), "→", [str(x.date()) for x in h.t10])
    ult = D.iloc[-1]
    print("Episodio actual (sin resolver):", ult.pico.date(), "−5 %", ult.t5.date(), "−10 %", ult.t10.date(), "v =", ult.v)


if __name__ == "__main__":
    main()
