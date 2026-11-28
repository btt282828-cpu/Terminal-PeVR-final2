# Informe del compañero — 2026-11-27 (viernes, modo SEMANAL; media sesión en EE. UU.)
## En una frase
El pánico se ha ido por un pelo (cociente VIX/VIX3M 0,9996) y el mercado ha rebotado fuerte en la semana (SPY +5,6 %, QQQ +7,0 %). Hoy no toca ninguna compra del Plan de rebajas, pero el QQQ está a solo +1,4 % de la línea de «paso a normal» y la terminal no lo avisará, porque sigue sin calcular el Nasdaq.

## 1. ¿Funciona todo? (vigilante)
🟢 La terminal acabó bien anoche y todos los archivos llegan al 27-nov.
- 🟠 Aviso nuevo (SNDK), pequeño: esta acción dividió 8 por 1 el 20-nov y, según mi consulta a Yahoo de hoy, le faltan las barras del 23 al 25-nov y el cierre del 27. El aviso sale de `rotacion.py` ~1704-1708 (`ffill(limit=1)`: tapa 1 semana el hueco de Yahoo; funciona como se diseñó). Ojo: `track_record.json` guarda para SNDK el 27-nov un precio de 94,39, que es el cierre del 19-nov (dato viejo). Afecta a una acción dentro del sintético «Almacén» y a su panel semanal; no toca el plan.
- 🔴 **Sigue: el Plan de rebajas no calcula el Nasdaq** (8.º informe, desde el 20-nov). Causa: `rotacion.py` línea ~24898 (`d = (daily or {}).get(sym)`: el QQQ no está en `daily`, lo salta con `continue` sin avisar). Arreglo: leer `OPER_QQQ["d"]`, como ya hacen las líneas 23052 y 20779. `plan_rebajas_estado.json` solo tiene el S&P.
- 🟠 **Cable de señales: 58 fechas de 60** (`rotacion.py` línea 3031, `[-60:]`). Se llena el mar 1-dic y el mié 2-dic empieza a borrar días: quedan dos ejecuciones.
- `preparar.py`: la máquina restauró otra vez el fallo (11.º día); lo parcheé y repetí, el marcador de abajo ya lleva precios al día. El manual ya recoge el Plan de rebajas: lo de «¿qué plan manda?» queda resuelto.

## 2. El Plan de rebajas
Hoy **no toca ningún escalón**. Cierre del 27-nov: SPY 728,32 (−6,8 % desde el máximo del 6-oct, 781,62), QQQ 650,99 (−14,7 %; máximo 762,86).
| Escalón | Línea | Estado |
|---|---|---|
| S&P −10 % x3 | 703,46 | comprado el 20-nov; pasó a normal el 23-nov (con 722,29) |
| Nasdaq −20 % x3 | 610,29 | tocó el 20-nov (cierre 608,45) — *la terminal no lo muestra*. Pasa a normal con cierre ≥ **659,92**; hoy 650,99: falta +1,4 % |
| S&P −15 % x3 | 664,38 | falta −8,8 % |
| Nasdaq −25 % x3 | 572,14 | falta −12,1 % |
| S&P −20 % x2 | 625,30 | falta −14,1 % |
| Nasdaq −30 % x2 | 534,00 | falta −18,0 % |
| Nasdaq −40 % / −50 % | 457,72 / 381,43 | sin tocar (x3 solo con VIX ≥ 40) |
Ojo: la terminal no mandará aviso de «paso a normal» del Nasdaq; la línea de 659,92 hay que mirarla a mano.

## 3. Qué dice hoy la terminal
- **Pánico:** hoy «SE VA EL PÁNICO» (VIX 23,81 / VIX3M 23,82 = 0,9996). Lo dice el detector (`panico_vivo` falso, evento «se_va»). Era la bala 1 del plan viejo; el plan único de rebajas no tiene escalón para eso. Lo medido (I-004, I-005) no respalda que sea mejor momento de entrada que otros días.
- **Dinero:** SALE DE TODO (entra 1 sector, salen 5), sin EMPUJE ni VENTA EXTREMA. Centinela LIQUIDEZ. Notas de los índices (solo contexto): SPY 2, QQQ 1, DIA 3, IWM 2, RSP 6.
- **Bono 10 años 4,94 %** (línea 4,5 %: a 44 pb; −11 pb en un mes), MOVE 95 (percentil 81). Dato a vigilar, no una bala. DIX 42,5 (percentil 14); el GEX ya es positivo (el 20-nov era negativo).
- **«Caída en curso»:** probabilidad de suelo 72 % (7 de cada 10; ayer 58 %); recesión 3 %.
Cosas que se pueden pasar por alto:
1. **El «se va» es por un pelo y en media sesión.** La terminal enseña «1,00» y parece que no ha bajado de 1: es 0,9996. Según la definición del detector, solo un nuevo cierre ≥ 1,10 reabre el pánico, aunque el lunes el cociente vuelva a 1,02.
2. **El salto de suelo 58 → 72 % viene de una sola casilla:** «SE FUE» vale 84 % en una tabla fija (`rotacion.py` línea 24036) apoyada en **solo 10 caídas del S&P** de 2009-2026 (con el margen, entre 5 y 9 de cada 10). No he podido comprobarla: la definición de «suelo hecho» no está en el repositorio. Lo apunto como I-010. No es una señal.
3. **La caída la han llevado los grandes de la tecnología:** RSP (el S&P con el mismo peso para todos) está solo −2,6 % de su máximo; SPY −6,8 %, QQQ −14,7 %.

## 4. Marcador (n a 20 sesiones; precios al día)
- GIRO↓ 33 casos, acierta 73 % (IC 56–85), exceso +7,8 pts (t 3,7). GIRO↑ 38 casos, 24 % (IC 13–39), exceso −6,6 (t −3,2). **Control de azar de hoy** (mismo activo, mismas fechas): GIRO↑ neto −0,4 (t −0,2) y GIRO↓ +0,2 (t 0,1): lo que se ve es lo que hacían esos activos, no la señal. Sigue cerrada (I-001).
- En vigilancia (no son prueba): **SUELO** 18 casos, neto +4,4 pts (t 3,0; por fechas 2,8, solo 12 fechas) y **EARLY** 15 casos, neto +4,2 (t 2,3; por fechas 1,9). Con ~15 señales alguna sale buena por azar; SUELO se re-mira a los 30 casos.
- Resto con pocos casos: solo orientativo. Señales del plan (NIVEL, PÁNICO, BALA…): se miden a 20 sesiones desde ~22-dic.
- **Cesta semanal:** la de la semana pasada (INDA y FIW) subió ≈ +2,5 % frente al +5,6 % del SPY; en total mejor que el SPY 5 de 13 semanas.

## 5. Investigación (viernes)
**I-006 · ¿Importa lo rápido que la caída del S&P va del −5 % al −10 %? → DESCARTADA** (estudio en `agente/estudios/i006.*`; reglas fijadas el 20-nov).
- Qué miré: las 48 caídas del S&P desde 1927 que tocaron −10 % (45 usables; las 3 de 2023 en adelante, la caja, sin abrir). Y si después llegaron a −20 %.
- Resultado: de las **rápidas** (del −5 % al −10 % en 15 sesiones o menos) llegaron a −20 % 6 de 23 (unas 3 de cada 10; margen: de 1 a 5 de cada 10). De las **lentas**, 12 de 22 (5-6 de cada 10; margen: de 3 a 7 de cada 10). En general, 4 de cada 10 caídas de −10 % siguieron hasta −20 %.
- Lo que dice: en las dos mitades de la historia (1927-74 y 1975-2022) las rápidas se alargan **menos**, no más; pero el contraste no pasa el listón que me puse (p = 0,07; hacía falta menos de 0,05) y depende de 3 casos. Con otra definición razonable de «llegar a −20 %» la diferencia se encoge a la mitad. **No es una regla.**
- La caída de 2026 es «rápida» (11 sesiones). Frecuencia histórica, no una predicción: y el SPY ya ha rebotado a −6,8 %, así que ese dato ya no describe dónde estamos.
- Variantes miradas: 3 (V = 10, 15 y 20; V = 10 «no concluyente» por pocos casos, V = 20 sale igual que 15). Ideas probadas en total: 5, todas descartadas.

## 5b. Fondeo
Hoy no toca (martes y jueves). Sin cambios en lo pendiente: `fondeo_base.md` no se ha generado hoy.

## 6. Propuestas para Pe
1. **Arreglar el Nasdaq del Plan de rebajas** (`rotacion.py` ~24898). Lo desmentiría: que «Hoy» ya muestre filas del Nasdaq y avise del paso a normal.
2. **Ampliar el cable de señales** (`rotacion.py` 3031, `[-60:]`) antes del mié 2-dic; si no, se empiezan a borrar días.

## 7. Lo que necesito de Pe
- Subir el arreglo de `agente/preparar.py` (línea 237: `start=str(desde)` → `start=pd.Timestamp(desde).strftime("%Y-%m-%d")`) o decirme que no importa.
- Decidir lo del Nasdaq y lo del cable (arriba). Nada más. No digo compra ni vende: la terminal marca y tú decides.

## Semana (20 → 27-nov)
- **Mercado:** SPY +5,6 %, QQQ +7,0 %, IWM +6,7 %, DIA +5,5 %, RSP +5,3 %, oro +3,6 %, TLT −0,2 %. VIX de 35,9 a 23,8; cociente VIX/VIX3M de 1,16 a 0,9996 (pánico vivo del 20 al 27-nov). Bono 10 años 4,91 → 4,94 %.
- **Plan de rebajas:** nada nuevo esta semana salvo el paso a normal del S&P −10 % (23-nov). Pendiente: Nasdaq −20 % (línea 659,92).
- **Marcador:** sin señal que se pueda juzgar con 30 casos; GIRO sin señal propia tras el control de azar.
- **Investigación:** I-006 (velocidad de la caída) descartada; ideas probadas: 5. El viernes 4-dic va I-008 (el bono de Pe: 4,5 %) y el 11-dic I-010 (la tabla del miedo de «Caída en curso», que hoy subió el suelo a 72 %).
- **Pendientes para decidir hoy:** (1) Nasdaq del plan, (2) cable de 60 fechas antes del 2-dic, (3) subir el arreglo de `preparar.py`, (4) el importe total del plan sigue escrito en `rotacion.py` línea 24842 (repositorio público), (5) faltan las series de la Fed (`fred_*.csv`): la recesión sale de una sola fuente.
