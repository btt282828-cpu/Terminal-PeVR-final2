# Informe del compañero — 2026-11-25 (miércoles, modo DIARIO)
## En una frase
Día tranquilo en el plan: el SPY cerró en 716,70 (−8,3 % desde su máximo) y el QQQ en 633,93 (−16,9 %); no salta ningún escalón ni paso a normal, y el pánico sigue «vivo» y algo más fuerte que ayer. El fallo del Nasdaq en el plan de rebajas sigue sin arreglar (6.º informe).

## 1. ¿Funciona todo? (vigilante)
🟢 El vigilante no marca nada nuevo: todo grabado al día, sin fallo de la terminal anoche.
Sigue igual:
- 🔴 **El plan de rebajas sigue sin calcular el Nasdaq** (desde el 20-nov). `plan_rebajas_estado.json` solo trae el SPY. Causa: `rotacion.py` ~línea 24898 (el QQQ no está en `daily` y el código lo salta sin avisar). Arreglo propuesto: leer `OPER_QQQ["d"]` cuando el símbolo sea QQQ, como ya hacen las líneas 23052 y 20779.
- Cable de señales: 57 fechas de 60. Se llena el 1-dic; el 2-dic empieza a borrar días.
- `preparar.py`: la máquina volvió a restaurar el fallo (9.º día); lo parcheé y volví a ejecutar. Sin el parche el marcador sale congelado (GIRO↑ con 10 casos en vez de 35).
- Avisos inocuos de siempre. `ideas.md` sigue con I-007 y contador 4.

## 2. El Plan de rebajas
Cierre del miércoles 25-nov (precios de Yahoo; % del plan, sin importes):
| Escalón | Producto | Estado |
|---|---|---|
| S&P −10 % | x3 → normal | comprado el 20-nov; pasó a normal el 23-nov. Nada nuevo hoy |
| Nasdaq −20 % | x3 | tocó el 20-nov (*la terminal no lo muestra, ver sección 1*). Mi cálculo: pasa a normal con un cierre ≥ ~659,9; hoy cerró en 633,93, le falta +4,1 % |
| S&P −15 % | x3 | línea 664,38; falta −7,3 % |
| Nasdaq −25 % | x3 | línea 572,14; falta −9,7 % |
| S&P −20 % | x2 | línea 625,30; falta −12,8 % |
| Nasdaq −30 % / −40 % / −50 % | x2 / normal o x3 / ídem | sin tocar (x3 en −40/−50 solo si el VIX cierra ≥ 40; hoy 28,3) |
**Hoy no toca ninguna acción del plan.** El pánico **sigue vivo** desde el 20-nov: VIX/VIX3M 1,076 (ayer 1,035, anteayer 1,044). Se va con el primer cierre por debajo de 1,0; el detector no marca «se va el pánico». Jueves 26 EE. UU. cerrado; viernes 27 media sesión.

## 3. Qué dice hoy la terminal
Caídas desde el máximo de 52 semanas: SPY −8,3 % (ayer −8,0 %), QQQ −16,9 % (−16,4 %), IWM −11,7 %, DIA −7,9 %, MAGS −13,0 %, RSP −3,8 %. VIX 28,3 (ayer 26,4). Dinero: SALE DE TODO (5 sectores salen, 1 entra). Centinela LIQUIDEZ. Notas de los índices BAJA/FLOJA (solo contexto). Acciones en mínimos de 52 semanas: 0,45 %. Bono 10 años 4,85 % (línea 4,5 %, a 35 pb; dato a vigilar, no una bala); MOVE 97,5 (percentil 84).
**Cosas que se pueden pasar por alto:**
1. **Dos sitios que se contradicen (sigue):** detector y balas dicen «QQQ −20 % tocado»; el plan de rebajas, que es el único plan, no lo tiene.
2. **El miedo sube sin que el índice caiga:** el SPY casi no se movió (−0,3 %) y el QQQ cedió −0,7 %, pero el VIX subió de 26,4 a 28,3 y el cociente VIX/VIX3M de 1,035 a 1,076. Es decir, el pánico se aleja de la salida (que es bajar de 1,0). Contexto, no señal.
3. Nada más fuera de lo normal.

## 4. Marcador (n a 20 sesiones)
GIRO↓ 33 casos, acierta 73 % (IC 56–85), exceso +7,8 pts (t 3,7); GIRO↑ 35 casos, 26 % (IC 14–42), exceso −5,7 (t −2,7). Con el control de azar del 20-nov (I-001) no hay señal propia. EARLY (15 casos) y SUELO (18) pocos casos, solo orientativo. Con ~15 señales alguna sale buena por azar. Señales del plan (NIVEL, BALA, PÁNICO del 20-nov): se miden a 20 sesiones, hacia el 22-dic. Cesta semanal: 5 de 12 semanas mejor que el SPY.

## 6. Propuestas para Pe
1. **Arreglar el plan de rebajas para que lea el Nasdaq** (`rotacion.py` ~24898). Lo desmentiría: que «Hoy» ya muestre filas del Nasdaq.
2. **Ampliar el cable de señales** (`rotacion.py` ~3031, `[-60:]`) antes del 2-dic.

## 7. Lo que necesito de Pe
- Subir el arreglo de `agente/preparar.py` (línea ~237: `start=str(desde)` → `start=pd.Timestamp(desde).strftime("%Y-%m-%d")`) o decirme que no importa.
- Decidir lo del Nasdaq del plan y lo del cable. Nada más. No digo compra ni vende: la terminal marca y tú decides.
