"""F-023: caída con peso menor cuando el VIX (cierre anterior) es alto. Variantes A-E fijadas en ideas.md."""
import sys, numpy as np, pandas as pd
sys.path.insert(0,"agente/herramientas"); from fondeo import *
H="historico_seguimiento_NO_BORRAR/historiales/"
def cargar(f):
    d=pd.read_csv(H+f); d.index=pd.to_datetime(d.DATE,format="%m/%d/%Y"); return d.CLOSE.astype(float)
vix=cargar("cboe_vix.csv"); v3=cargar("cboe_vix3m.csv"); ratio=(vix/v3).dropna()
P=plan_completo()
def previo(serie,O):
    d=pd.to_datetime(O.t.values,unit="s",utc=True).tz_convert("America/New_York").normalize().tz_localize(None)
    s=serie.copy(); idx=s.index
    pos=idx.searchsorted(d,side="left")-1   # último cierre ESTRICTAMENTE anterior al día de entrada
    ok=pos>=0
    return pd.Series(np.where(ok,s.values[np.clip(pos,0,None)],np.nan),index=O.index)
for k in ("caída nas","caída spx"):
    O=P[k]; O["vix"]=previo(vix,O); O["rat"]=previo(ratio,O)
    # ratio solo si el dato previo no es muy viejo
    O.loc[pd.to_datetime(O.t,unit="s")<pd.Timestamp("2009-10-15"),"rat"]=np.nan
TR=TRAMOS+TROZOS
def grupos():
    print("== R por grupo de VIX (cierre anterior) ==")
    for k in ("caída nas","caída spx"):
        O=P[k]; y=pd.to_datetime(O.t,unit="s").dt.year
        for nom,m in [("VIX<20",O.vix<20),("20-30",(O.vix>=20)&(O.vix<30)),("VIX>=30",O.vix>=30),("rat>=1",O.rat>=1.0),("rat<1",O.rat<1.0)]:
            fila=[]
            for tn,a,b in [("todo",2003,2026)]+[(t[0],t[1],t[2]) for t in TR]:
                x=O[m&(y>=a)&(y<=b)]
                fila.append(f"{tn}: N{len(x)} R{x.R.mean():+.2f}" if len(x) else f"{tn}: N0")
            print(k,nom,"|"," | ".join(fila))
grupos()
def variante(nombre,regla):
    Q={a:o.copy() for a,o in P.items()}
    for k in ("caída nas","caída spx"):
        O=Q[k]; O["peso"]=regla(O)
    return Q
V={"base":lambda O:O.peso,
 "A skip VIX>=30":lambda O:np.where(O.vix>=30,0.0,O.peso),
 "B 0,25 VIX>=30":lambda O:np.where(O.vix>=30,0.25*0.5/0.5*0.5,O.peso),
 "C skip VIX>=25":lambda O:np.where(O.vix>=25,0.0,O.peso),
 "D skip rat>=1":lambda O:np.where(O.rat>=1.0,0.0,O.peso),
 "E peso1 VIX>=30":lambda O:np.where(O.vix>=30,1.0,O.peso)}
# B: peso 0,25 absoluto (la base es 0,5)
V["B 0,25 VIX>=30"]=lambda O:np.where(O.vix>=30,0.25,O.peso)
for n,f in V.items():
    Q=variante(n,f); print("\n######",n)
    print(tabla_retos(Q,"5ers",["colchon"]))
