# Informe del compañero — 2026-11-24 (martes, modo FONDEO)
## En una frase
Día de poco movimiento en el plan: el SPY cerró en 718,78 (−8,0 % desde su máximo) y el QQQ en 638,10 (−16,4 %); no salta ningún escalón nuevo ni paso a normal, y el pánico sigue «vivo». El fallo del Nasdaq en el plan de rebajas sigue sin arreglar (5.º informe).

## 1. ¿Funciona todo? (vigilante)
🟢 El vigilante no marca nada nuevo: todo grabado al día, sin fallo de la terminal anoche.
Sigue igual:
- 🔴 **El plan de rebajas sigue sin calcular el Nasdaq** (desde el 20-nov). `plan_rebajas_estado.json` solo trae el SPY. Causa: `rotacion.py` ~línea 24898 (`d = (daily or {}).get(sym)`; el QQQ no está en `daily`, y el código lo salta sin avisar). Arreglo: leer `OPER_QQQ.get("d")` cuando `sym == "QQQ"`, como ya hacen las líneas 23052 y 20779.
- Cable de señales: 56 fechas de 60. Se llena el 1-dic; el 2-dic empieza a borrar días.
- `preparar.py`: la máquina volvió a restaurar el fallo del marcador congelado (8.º día); lo parcheé y volví a ejecutar. Sin el parche GIRO↑ sale con 10 casos en vez de 35.
- Avisos inocuos de siempre.

## 2. El Plan de rebajas
Cierre del martes 24-nov (precios de Yahoo; % del plan, sin importes):
| Escalón | Producto | Estado |
|---|---|---|
| S&P −10 % | x3 → normal | comprado el 20-nov; pasó a normal el 23-nov. Nada nuevo hoy |
| Nasdaq −20 % | x3 | tocó el 20-nov (*la terminal no lo muestra, ver sección 1*). Mi cálculo: pasa a normal con un cierre ≥ ~659,9; hoy cerró en 638,10, le falta +3,4 % |
| S&P −15 % | x3 | línea 664,38; falta −7,6 % |
| Nasdaq −25 % | x3 | línea 572,14; falta −10,3 % |
| S&P −20 % | x2 | línea 625,30; falta −13,0 % |
| Nasdaq −30 % / −40 % / −50 % | x2 / normal o x3 / ídem | sin tocar (x3 en −40/−50 solo si el VIX cierra ≥ 40; hoy 26,4) |
**Hoy no toca ninguna acción del plan.** El pánico **sigue vivo** desde el 20-nov: VIX/VIX3M 1,035 (ayer 1,044); se va con el primer cierre por debajo de 1,0. El detector no marca «se va el pánico». Jueves 26 cerrado; viernes 27 media sesión.

## 3. Qué dice hoy la terminal
Caídas desde el máximo de 52 semanas: SPY −8,0 % (ayer −7,6 %), QQQ −16,4 % (−14,7 %), IWM −12,2 %, DIA −8,2 %, MAGS −12,1 %, RSP −4,6 %. VIX 26,4. Dinero: SALE DE TODO (5 sectores salen, 0 entran). Centinela LIQUIDEZ. Notas de los índices BAJA/FLOJA (solo contexto). Acciones en mínimos de 52 semanas: 2,4 %. Bono 10 años 4,90 % (línea 4,5 %, a 40 pb; dato a vigilar, no una bala); MOVE 98,8 (percentil 88; baja desde 106 el 20-nov).
**Cosas que se pueden pasar por alto:**
1. **Dos sitios que se contradicen (sigue):** detector y balas dicen «QQQ −20 % tocado»; el plan de rebajas, que es el único plan, no lo tiene.
2. **El rebote del lunes se ha dado un poco la vuelta:** el martes el QQQ cedió −2,0 % y el SPY −0,5 % con el pánico aún vivo. Contexto, no señal.
3. Nada más fuera de lo normal.

## 4. Marcador (n a 20 sesiones)
GIRO↓ 32 casos, acierta 72 % (IC 55–84), exceso +8,0 pts (t 3,7); GIRO↑ 35 casos, 26 % (IC 14–42), exceso −5,7 (t −2,7). Con el control de azar del 20-nov (I-001) no hay señal propia. Resto: pocos casos, solo orientativo. Con ~15 señales alguna sale buena por azar. Señales del plan (NIVEL, BALA, PÁNICO del 20-nov): se miden a 20 sesiones, hacia el 22-dic. Cesta semanal: 5 de 12 semanas mejor que el SPY.

## 5b. Fondeo
**Reto en la sombra (desde el 9-nov, plan entero al 1 %, FTMO 1 paso):** saldo −0,47 %, peor momento −0,75 %, objetivo +10 %. Operaciones cerradas: 8 (spx 2 ganadas +0,35 R; nas 1 ganada +0,36 y 1 perdida −1,02; eurjpy 2 ganadas +0,27 y +0,26; las dos caídas, nas y spx, paradas en −1,02 R, entradas el 17-nov y cortadas el 20-nov). **Ninguna abierta ahora.** Sin alertas: 8 pérdidas seguidas no, −6 % no.
**Vigilancia de la caída (F-021):** NAS: R medio de las 20 últimas −0,10 (histórico +0,12); SPX +0,12 (histórico +0,10). Dentro de lo normal (en la historia, −0,10 pasa el 25 % del tiempo). Desde el 9-nov cada caída lleva 1 operación nueva, las dos perdedoras: aún no hay nada que juzgar. Sin ⚠️.
**Tres ideas nuevas (apuntadas antes de probar en `agente/fondeo/ideas.md`):**
- F-023 (gestión): bajar o quitar la caída cuando el VIX está alto. **Elegida.**
- F-024 (gestión): tope propio de −2 % al día con cinco gráficos. Pendiente (necesita simulador propio).
- F-025 (lo contrario): darle la vuelta a EUR/JPY. Pendiente; solo vale si pierde antes de costes en los tres tramos.
**Resultado de F-023: descartada, y sale lo contrario.** La caída con VIX ≥ 30 (cierre anterior) rinde mejor, no peor: Nasdaq +0,22 R (78 operaciones) y S&P +0,17 (74) frente a +0,12 y +0,11 con VIX bajo 20. Quitar o reducir esas entradas **empeora** el reto en The5ers en 2003-15 y 2016-22 (por ejemplo, quitarlas con VIX ≥ 30: en 2016-22 quema 24 % → 31 % y aprueba en ≤12 m 69 % → 61 %); en 2023-26 no cambia. Doblarlas (E) da lo mismo que no tocar. Lo que se aprende: con el miedo alto, la caída **no** hay que apagarla. Hoy el miedo está alto (VIX 26, ratio 1,035).
**Pista (sin limpiar, F-026):** con VIX/VIX3M ≥ 1,0 la caída rinde mucho (Nasdaq +0,45 R en 42 operaciones, S&P +0,28 en 46), en los tres tramos. Pero lo vi mirando todos los tramos, caja incluida, y son pocos casos: es una pista, no una candidata. Lo medirá la sombra con datos nuevos. 5 variantes más un diagnóstico. Contador de ideas de fondeo probadas: 14.

## 6. Propuestas para Pe
1. **Arreglar el plan de rebajas para que lea el Nasdaq** (`rotacion.py` ~24898, ver sección 1). Lo desmentiría: que «Hoy» ya muestre filas del Nasdaq.
2. **Ampliar el cable de señales** (`rotacion.py` ~3031, `[-60:]`) antes del 2-dic.

## 7. Lo que necesito de Pe
- Subir el arreglo de `agente/preparar.py` (línea ~237: `start=str(desde)` → `start=pd.Timestamp(desde).strftime("%Y-%m-%d")`) o decirme que no importa.
- Decidir lo del Nasdaq del plan y lo del cable. Nada más. No digo compra ni vende: la terminal marca y tú decides.
