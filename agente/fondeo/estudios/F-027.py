"""F-027: Russell 2000 (us2000) con las mismas reglas. Variantes A-E fijadas en ideas.md."""
import sys, numpy as np, pandas as pd
sys.path.insert(0,"agente/herramientas"); from fondeo import *
m=minutos("us2000"); h=velas(m,"1h")
m1=sistema_actual("us2000"); cd=caida("us2000")
print("N motor1",len(m1),"N caida",len(cd))
print("== A motor 1 us2000 =="); print(resumen(m1, azar(m,m1)))
print("== B caída us2000 =="); print(resumen(cd, azar(m,cd)))
P=plan_completo()
def con(extra):
    Q={k:v.copy() for k,v in P.items()}; Q.update(extra); return Q
c=cd.copy()
m1h=m1.copy(); m1h["peso"]=m1h.peso*0.5; cdh=cd.copy()
V={"base":{}, "C +motor1 us2000 peso1":{"us2000":m1}, "D +caída us2000 0,5":{"caída us2000":cd},
   "E +ambas medio peso":{"us2000":m1h,"caída us2000":cd}}
for n,x in V.items():
    print("\n######",n); print(tabla_retos(con(x),"5ers",["colchon"]))
    print(tabla_retos(con(x),"ftmo1",[0.01]))
