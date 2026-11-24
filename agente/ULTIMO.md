# Informe del compañero — 2026-11-23 (lunes)
## En una frase
Rebote fuerte el lunes (SPY +4,7 %, QQQ +7 %, VIX de 35,9 a 26,6): **el S&P pasa a normal lo comprado en x3 en el −10 %** (recuperó 1/3 de la caída). El Nasdaq sigue sin salir en el plan por el fallo de siempre, y el pánico sigue «vivo».

## 1. ¿Funciona todo? (vigilante)
🟠 Un solo aviso nuevo y menor: el build de las 01:10 NY corrió con la sesión de EE. UU. sin cerrar, así que el put/call por volumen de opciones de hoy es provisional (fíate del dato por posiciones abiertas, el de T-1). Todos los archivos están al día (0 sesiones de retraso). Sin fallo de la terminal anoche.
Sigue igual:
- 🔴 **El plan de rebajas sigue sin calcular el Nasdaq** (desde el 20-nov, 4.º informe seguido). `plan_rebajas_estado.json` solo trae el SPY. Causa: `rotacion.py` línea 24898, `d = (daily or {}).get(sym)`: el QQQ no está en `daily` y el código salta con `continue` sin avisar. Arreglo propuesto: `d = OPER_QQQ.get("d") if sym == "QQQ" else (daily or {}).get(sym)`.
- Cable de señales: 55 fechas de 60 (se llena hacia el 1-dic; el 2-dic empieza a borrar días maduros).
- `preparar.py`: la máquina vuelve a restaurar el fallo del marcador congelado (7.º día); lo he parcheado en sitio y ejecutado de nuevo. Sin el parche GIRO↑ sale con 10 casos en vez de 35.
- Avisos inocuos de siempre (IV descartada, put/call fuera de banda, pesos del QQQ de Invesco 406, `universo_close` parado). Ya están `agente/fondeo/` y `agente/herramientas/fondeo.py`: gracias por moverlos.

## 2. El Plan de rebajas
Cierre del lunes 23-nov (precios de Yahoo; % del plan, sin importes):
| Escalón | Producto | Estado |
|---|---|---|
| S&P −10 % | x3 | comprado con el cierre del 20-nov. **HOY PASA A NORMAL**: el SPY cerró en 722,29, justo en el 1/3 de la caída (722,29). Hay que cambiar esos x3 por S&P normal |
| Nasdaq −20 % | x3 | **tocó el 20-nov** (QQQ 608,45 con línea 610,29). *La terminal no lo muestra (fallo de arriba).* Cálculo mío: pasa a normal con un cierre ≥ ~659,9; hoy cerró en 651,03, le falta +1,4 % |
| S&P −15 % | x3 | línea 664,38, falta −8,0 % |
| Nasdaq −25 % | x3 | línea 572,14, falta −12,1 % |
| S&P −20 % | x2 | línea 625,30, falta −13,4 % |
| Nasdaq −30 % / −40 % / −50 % | x2 / normal o x3 / ídem | sin tocar (−40 %/−50 % en x3 solo si el VIX cierra ≥ 40; hoy 26,6) |
**Cuándo se actúa:** el paso a normal del S&P saltó con el cierre del lunes (ya pasado); la primera ocasión es el martes 24 al abrir. **Ojo:** si mañana el QQQ cierra por encima de ~659,9, la terminal **no** te avisará del paso a normal del Nasdaq (no lo calcula): hay que mirarlo a mano.
Pánico: **sigue vivo** (VIX/VIX3M 1,044; se va con el primer cierre por debajo de 1,0). Que el VIX haya bajado de 35,9 a 26,6 no basta: lo que cuenta es esa ratio. El detector no marca «se va el pánico» hoy. Jueves 26 cerrado; viernes 27 media sesión.

## 3. Qué dice hoy la terminal
Caídas desde el máximo de 52 semanas: SPY −7,6 % (ayer −11,8 %), QQQ −14,7 % (−20,2 %), IWM −12,7 %, DIA −8,9 %, MAGS −11,2 %, RSP −5,1 %. VIX 26,6. Dinero: SALE DE TODO (6 sectores salen, 0 entran); ya no es VENTA EXTREMA. Centinela LIQUIDEZ. Notas de los índices: BAJA/FLOJA (solo contexto). Acciones en mínimos de 52 semanas: 0,6 % (ayer 13,2 %). Bono 10 años 4,92 % (línea 4,5 %, a 42 pb; dato a vigilar, no una bala); MOVE 101 (percentil 90; ayer 106).
**Cosas que se pueden pasar por alto (3):**
1. **Dos sitios que se contradicen (sigue):** detector y balas dicen «QQQ −20 % tocado», el plan de rebajas no lo tiene (ver sección 2).
2. **Un rebote de +4,7 % en un día con el pánico aún vivo.** En lo ya estudiado, la caída no se acaba solo porque haya un día verde grande: el SPY sigue en −7,6 % y la ratio de miedo no ha bajado de 1,0. Lo digo como contexto, no como señal.
3. **Los x3 comprados el viernes y devueltos a normal el lunes:** el sistema obliga a venderlos al pasar el 1/3; si la caída sigue después, el escalón −10 % ya no vuelve a comprarse (una vez por caída). Es lo que dice la regla, no un fallo.

## 4. Marcador (n a 20 sesiones)
GIRO↓ 32 casos, acierta 72 % (IC 55–84), exceso +8,0 pts (t 3,7); GIRO↑ 35 casos, 26 % (IC 14–42), exceso −5,7 (t −2,7). Con el control de azar del 20-nov no hay señal propia (I-001 cerrada). Resto: pocos casos, solo orientativo (SUELO 17, EARLY 15, FLOW 18, t < 2). Con ~15 señales alguna sale buena por azar. Señales del plan (NIVEL, BALA, PÁNICO del 20-nov): se miden a 20 sesiones, hacia el 22-dic. Cesta semanal: 5 de 12 semanas mejor que el SPY.

## 6. Propuestas para Pe
1. **Arreglar el plan de rebajas para que lea el Nasdaq** (`rotacion.py` ~24898; arreglo en la sección 1). Hoy ya cuesta: el paso a normal del Nasdaq no saldrá. Lo desmentiría: que en la pestaña «Hoy» ya aparezcan filas del Nasdaq (yo solo veo los archivos).
2. **Ampliar el cable de señales** (`rotacion.py` línea 3031, `[-60:]`) antes del 2-dic.

## 7. Lo que necesito de Pe
- Subir el arreglo de `agente/preparar.py` (línea 237: `start=str(desde)` → `start=pd.Timestamp(desde).strftime("%Y-%m-%d")`) o decirme que no importa.
- Decidir lo del Nasdaq y lo del cable. Nada más. No digo compra ni vende: la terminal marca y tú decides.
