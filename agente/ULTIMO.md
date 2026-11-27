# Informe del compañero — 2026-11-26 (jueves, modo FONDEO; EE. UU. cerrado por Acción de Gracias)
## En una frase
Día sin sesión en EE. UU.: la terminal no tiene datos nuevos (el último cierre sigue siendo el del 25-nov), no toca nada del plan de rebajas y el pánico sigue «vivo». En fondeo, probé el Russell 2000 con las mismas reglas del robot: pierde, descartado.

## 1. ¿Funciona todo? (vigilante)
🟢 La terminal anoche acabó bien. Los cinco 🟠 del vigilante (semáforo, estructura, DIX, amplitud, notas de índices «no tienen el 26-nov») son simplemente el festivo: no es un fallo.
Sigue igual:
- 🔴 **El plan de rebajas sigue sin calcular el Nasdaq** (desde el 20-nov, 7.º informe). Causa: `rotacion.py` ~línea 24898 (el QQQ no está en `daily` y el código lo salta sin avisar). Arreglo: leer `OPER_QQQ["d"]` para el QQQ, como ya hacen las líneas 23052 y 20779.
- Cable de señales: 57 fechas de 60; se llena el 1-dic y el 2-dic empieza a borrar días.
- `preparar.py`: la máquina volvió a restaurar el fallo (10.º día); lo parcheé y repetí. Sin el parche el marcador sale congelado.

## 2. El Plan de rebajas
Sin sesión hoy: nada cambia respecto al cierre del 25-nov (SPY 716,70, −8,3 % desde el máximo; QQQ 633,93, −16,9 %).
| Escalón | Estado |
|---|---|
| S&P −10 % x3 | comprado el 20-nov; pasó a normal el 23-nov |
| Nasdaq −20 % x3 | tocó el 20-nov (*la terminal no lo muestra*); pasa a normal con un cierre ≥ ~659,9 (le falta +4,1 %) |
| S&P −15 % x3 | línea 664,38; falta −7,3 % |
| Nasdaq −25 % x3 | línea 572,14; falta −9,7 % |
| S&P −20 % x2 | línea 625,30; falta −12,8 % |
| Nasdaq −30 %, −40 %, −50 % | sin tocar |
**Hoy no toca ninguna acción.** Pánico vivo desde el 20-nov (cociente VIX/VIX3M 1,076 el 25-nov); se va con el primer cierre por debajo de 1,0. Mañana viernes es media sesión (cierra 19:00 Bilbao): ahí se verá.

## 3. Qué dice hoy la terminal
Datos del 25-nov, sin cambios: dinero SALE DE TODO, centinela LIQUIDEZ, notas BAJA/FLOJA (solo contexto), bono 10 años 4,85 % (línea 4,5 %; dato a vigilar, no una bala), MOVE 97,5.
Cosas que se pueden pasar por alto:
1. **Contradicción que sigue:** detector y balas dicen «QQQ −20 % tocado»; el plan de rebajas no lo tiene.
2. **Fuera de la bolsa de EE. UU., el Nasdaq de OANDA rebotó mucho:** el 25-nov llegó a caer hasta ~24.975 puntos y cerró en ~25.950, y en la madrugada del 26 subió hasta ~26.200. Es contexto, no señal.

## 4. Marcador (n a 20 sesiones)
GIRO↓ 33 casos, acierta 73 % (IC 56–85), exceso +7,8 pts (t 3,7); GIRO↑ 35 casos, 26 % (IC 14–42), exceso −5,7 (t −2,7): con el control de azar del 20-nov no hay señal propia. Resto con pocos casos: solo orientativo. Con ~15 señales alguna sale buena por azar. Cesta semanal: 5 de 12 semanas mejor que el SPY.

## 5b. Fondeo
**Reto en la sombra (desde 9-nov, plan entero 1 %, caídas a medio riesgo):** saldo −0,3 %, peor momento −0,75 % (límites: −6 % The5ers, objetivo +10 %). 10 operaciones: 6 del motor 1 (5 ganadas, 1 perdida) y 4 de caída.
- ⚠️ **Dos operaciones de caída parecen abiertas ahora**, aunque el fichero las marque cerradas: entraron el 25-nov a las 23:01 (UTC) y los datos de OANDA se cortan el 26-nov ~08:00 UTC, así que la tabla las «cierra» al último precio (Nasdaq +0,23 R, S&P +0,10 R, a medio peso). No es un resultado real. Las pérdidas anteriores de caída (−1,02 R las dos, 17-20 nov) fueron una a la vez en los dos índices.
- Motor 1: EUR/JPY 2 ganadas, S&P 2 ganadas, Nasdaq 1 ganada y 1 perdida (−1,02 R el 16-nov).
- **Vigilancia de la caída (F-021): sin ⚠️.** Nasdaq: R medio de las 20 últimas −0,10 (histórico +0,12; en la historia estuvieron bajo 0 el 26 % del tiempo): normal. S&P: +0,09, normal. Nuevas desde el 9-nov: Nasdaq 2 operaciones (−0,39 R medio), S&P 2 (−0,46); pocas para concluir.

**Tres ideas nuevas (escritas antes de probar, en `fondeo/ideas.md`):** F-027 Russell 2000 con las mismas reglas (ángulo c); F-028 cerrar la caída a las 72 h si no está por encima de la entrada (ángulo b); F-029 la segunda caída entra a peso 0,25 si la otra ya está abierta (ángulo a).
**Elegida: F-027** (el Russell estaba como «aún no probado»; más operaciones habría acelerado el reto).
**Resultado: descartada.** Motor 1 en Russell: N 349, **−0,12 R** de media (t −2,27); en 2023-26 −0,31 R (t −2,74), peor que entrar al azar. Caída en Russell: N 480, +0,03 R (t 0,67), no distinguible del azar. Añadirlas al plan en The5ers empeora la quema: en 2016-22 pasa de 24 % a 30-38 %, y en 2023-26 de 0 % a 2-11 %; solo acelera algo el «≤3 meses» en 2003-22. Cuenta: 5 variantes + 2 diagnósticos; contador de fondeo 15 ideas probadas. Estudio en `agente/fondeo/estudios/F-027.*`.

## 6. Propuestas para Pe
1. **Arreglar el plan de rebajas para que lea el Nasdaq** (`rotacion.py` ~24898). Lo desmentiría: que «Hoy» ya muestre filas del Nasdaq.
2. **Ampliar el cable de señales** (`rotacion.py` ~3031, `[-60:]`) antes del 2-dic.

## 7. Lo que necesito de Pe
- Subir el arreglo de `agente/preparar.py` (línea ~237: `start=str(desde)` → `start=pd.Timestamp(desde).strftime("%Y-%m-%d")`) o decirme que no importa.
- Decidir lo del Nasdaq del plan y lo del cable. Nada más. No digo compra ni vende: la terminal marca y tú decides.
