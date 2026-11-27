# Ideas de fondeo (F-00X)

Cada idea se apunta ANTES de probarla: regla exacta, por qué podría funcionar, qué la confirma, qué la tumba y cuántas
variantes se miran (5 como mucho). Lo apuntado no se cambia después de ver resultados.
Estado: pendiente / en curso / descartada / candidata para demo.

## Lista de partida (opcional; puesta por Pe y su asistente el 9-nov-2026). Lo importante son tus ideas propias

- **F-001 · Mismo sistema en el Russell 2000 (US2000).** Reglas congeladas, sin tocar nada. Es el único índice grande de
  EE. UU. sin probar: si el sistema tiene algo propio de los índices americanos, debería asomar aquí. Confirma: positivo en
  comprobar 2019-22 y gana al azar. Tumba: negativo o igual que el azar. Variantes: 1 (y la versión con cierre del viernes).
  Si pasa, mirar si añadirlo a S&P + Nasdaq mejora la tabla de retos.
- **F-002 · Gestión del riesgo del reto (sin tocar la señal).** Tamaño según la situación del reto, por ejemplo: 1,25 %
  normal; 0,75 % si la cuenta está más de un 4 % por debajo de su máximo; 1,5 % cuando falte menos de un 3 % para el objetivo.
  Necesita un simulador de retos con tamaño que cambia (créalo en `fondeo_extra.py`). Confirma: más "≤ 12 m" sin más quema en
  2016-22 y 2023-26. Variantes: 3 reglas como mucho, fijadas antes.
- **F-003 · Tamaño según el miedo del mercado.** Peso 1,5 con VIX ≥ 20 y 0,5 con VIX < 15 (VIX diario en `historiales/`).
  Viene de la pista viva "VIX alto mejora las entradas tras caídas". Confirma: mejora los retos en aprender y comprobar.
- **F-004 · Hora de la señal.** ¿Las señales de la sesión de Nueva York (15:30-22:00 de Madrid) rinden distinto que las de la
  noche? Solo 2 grupos, fijados antes. Si una franja pierde en aprender y en comprobar, saltarla.
- **F-005 · Una segunda entrada sin solapar.** Si el stop salta y en las 23 velas siguientes sale otra señal válida, ¿la
  segunda rinde como la primera o peor? Sirve para decidir si el robot debe esperar tras una pérdida.
- **F-006 · Zona de ruido en el Nasdaq como segundo motor** (intradía, casi sin correlación con el sistema). Ya medida aparte;
  aquí solo interesa si sumarla a escala 0,5 mejora la tabla de retos. Es larga: partirla en varias sesiones.

- **F-007 · Otros activos con la regla fijada antes de mirar.** Hay datos de 1 minuto de OANDA (bunqii) para: Russell 2000,
  Australia 200, Hong Kong 33, Francia 40, China A50, Brent, bono de 10 años de EE. UU., GBP/JPY, AUD/JPY, CAD/JPY, NZD/JPY,
  CHF/JPY, cobre, platino, gas natural, bitcoin, EUR/GBP y EUR/AUD (nombres de repositorio `OANDA_<SIMBOLO>_<Nombre>`, por
  ejemplo `OANDA_GBPJPY_GBPJPY`; añádelos a `ACTIVOS` en tu `fondeo_extra.py`). Regla, fijada hoy: un activo entra solo si
  gana en 2016-22 Y en 2023-26 y en los dos tramos le gana al azar. Con 18 probados, alguno puede pasar por suerte: si pasa,
  primero unas semanas en la sombra.

- **F-008 · Caída + base de 2-3 días + rotura al alza (idea de Pe, PROBADA por el asistente el 9-nov; no repetir).**
  Caída ≥ K veces el rango diario mediano (K 2,5 o 3,5) desde el máximo de 10 días; B (2 o 3) días sin perder el mínimo;
  base estrecha (≤ 60 % de la caída); entrada al cierre de la vela de 1 h que rompe el máximo de la base; stop bajo el mínimo
  − 0,5 ATR; 0,75 R / 2 R. Código en la sesión del asistente (`base_rotura.py`). Resultados (aprender / comprobar / caja):
  EUR/JPY ≈ 0 R en total, negativo en comprobar en las 4 variantes (solo bien desde 2023); S&P ≈ 0 o negativo y peor que el
  azar; **Nasdaq +0,09 a +0,19 R y gana al azar en aprender y caja, pero pierde en comprobar 2019-22 (−0,06 a −0,28) en las
  4 variantes**. Descartada como regla; el Nasdaq queda como pista que depende de la época. 12 pruebas para el contador.

- **F-009 · Rejilla de objetivos (PROBADA por el asistente el 9-nov; no repetir).** Tres activos, listón del CMF 0,025, 15
  combinaciones distintas de TP1 (0,5 / 0,75 / 1 / 1,5 / 2 R) y TP2 (1,5 / 2 / 3 / 4 R). TP1 = 0,75 es claramente lo mejor
  (+0,05 R; las demás +0,02-0,03 y negativas en aprender y comprobar). Con TP1 0,75, TP2 = 2 / 3 / 4 da lo mismo (+0,052 /
  +0,054 / +0,054; caja +0,27 / +0,31 / +0,31; comprobar +0,005 / −0,008 / −0,042). TP1 más alto sube la quema del reto en
  2023-26 (6-26 %). Se queda 0,75 / 2.
- **F-010 · Otras salidas para la mitad B (PROBADA por el asistente el 9-nov; no repetir).** La A sigue en 0,75 R; la B en
  breakeven tras TP1 y luego: stop que sube detrás del precio a 1/2/3/4 ATR(1 h) de la entrada, cierre 4/24/72/120 h después
  de TP1, u objetivo en el máximo de 1/3/5 días antes de la señal. Ninguna mejora de forma consistente a TP2 = 2 R (+0,052 R).
  La mejor en R, el stop que sube a 3 ATR (+0,063 R; caja +0,30), empeora el reto: en 2016-22 aprueba en ≤6 m el 23 % frente
  al 33 % y quema el 45 % frente al 37 %; en 2023-26 quema el 9 % frente al 2 %. Cerrar por tiempo es peor en todo.
  Se queda el objetivo fijo de 2 R.

- **F-011 · Divergencia del VERDE del Koncorde en un mínimo nuevo, 1 h (idea de Pe; PROBADA por el asistente el 9-nov; no
  repetir).** Mínimo de 2 días por debajo del mínimo anterior (5-60 velas); en el anterior el verde (marrón + débiles) bajó de
  0 o de −25; en el nuevo, más arriba (variante: y aún bajo 0); entrada en la siguiente vela verde, stop bajo el mínimo
  − 0,5 ATR, 0,75 / 2 R. Sola: EUR/JPY −0,12 a −0,14 R y peor que el azar en las 4 variantes; S&P ≈ 0; Nasdaq +0,03 a
  +0,08 hasta 2022 pero −0,06 a −0,10 desde 2023. Unas 32-45 señales al año: es muy común. Como filtro del sistema actual
  (listón 0,025): ~60 % de sus entradas ya la tienen; con/sin divergencia S&P +0,08/+0,06, Nasdaq +0,09/+0,11, EUR/JPY
  +0,02/−0,06, con los tramos al revés según el activo. No se usa.

- **F-012 · Caída del 2,4 % desde el máximo (idea de Pe; PROBADA por el asistente el 9-nov) → CANDIDATA en el Nasdaq.**
  Máximo de referencia de 20 o 60 días; entrada a mercado al tocar máximo × (1 − 2,4 %); stop 1,2 % o 2,4 % bajo la entrada;
  mitad A en máximo × (1 − 1,2 %) (recupera la mitad de la caída), mitad B en el máximo con breakeven tras A; 10 días.
  EUR/JPY: −0,03 a −0,13 R (solo bien desde 2023). S&P: +0,00 a +0,14, con 2003-18 ≈ 0 o negativo. **Nasdaq: positiva en
  las 4 variantes (+0,10 a +0,17 R)**; la de máximo de 20 días y stop 2,4 %: +0,114 R, 19 al año, 58 % de acierto, aprender
  +0,08 (azar −0,02), comprobar +0,11 (+0,02), caja +0,24 (+0,03). El 31 % cae a ≤2 días de una entrada del sistema en el
  Nasdaq (esas −0,06 R; las demás +0,19). Sumada al plan al 1 % en FTMO 1 paso: aprueba en ≤6 m el 51 % (antes 24 %) en
  2023-26 y el 14-17 % (antes 2 %) en 2016-22, pero quema el 13 % en 2023-26 (antes 0 %) y el peor día pasa a −4,3 %.
  Las quemas de más no vienen de que coincida con el sistema (dejar las dos a la vez es mejor que una sola a la vez: con una
  sola, 2023-26 baja a 34 % en ≤6 m y quema 17 %), sino de rachas de stops cuando el mercado sigue cayendo: 2018 (−8,6 R),
  2022 (−7,3 R) y seis stops seguidos de enero a abril de 2025. Freno «tras 2 stops seguidos, esperar a un máximo nuevo de
  20 días»: no ayuda (2019-22 pasa a −0,03 R; quemas iguales). **Mejor versión: la caída a mitad de riesgo** (peso 0,5):
  FTMO 1 paso 1 %: 2023-26 ≤6 m 34 %, ≤12 m 86 %, quema 0 %; 2016-22 ≤6 m 13 %, ≤12 m 39 %, quema 23 %; peor día −3,7 %.
  The5ers 2 %: 2023-26 ≤6 m 78 %, ≤12 m 94 %, quema 6 %; 2016-22 ≤6 m 39 %, ≤12 m 54 %, quema 33 %.
  Pendiente: decisión de Pe, indicador y seguirla en la sombra (a mitad de riesgo). Código: `caida24.py` en la sesión del asistente.

- **F-014 · Caída del Nasdaq: por qué recompra y variantes (PROBADA por el asistente el 10-nov) → cambiar el stop a 3,6 % y los objetivos a 1R/2R.**
  La F-012 no es «una compra por caída»: el máximo de 20 días cambia de valor casi en cada vela cuando el mercado baja, así que
  recompra tras cada salida mientras el precio siga un 2,4 % bajo el máximo. 75 variantes (5 formas de entrar × stop 1,2/2,4/3,6 % ×
  5 salidas), eligiendo con 2003-18. El orden de 2003-18 NO se mantiene después (correlación −0,10 con 2019-22 y −0,17 con la
  caja): afinar stops y objetivos es ruido. Lo único estable es el grupo: stop 3,6 % (caída máxima media −15 R frente a −29 R con
  2,4 % y −45 R con 1,2 %). El «primer toque» puro de Pe (una sola compra al −2,4 %) no gana al azar en 2003-22.
  Elegida con 2003-18: entrada como ahora, stop 3,6 %, mitad a 1R y mitad a 2R. Nasdaq (sistema/azar): aprender +0,106/−0,027,
  comprobar +0,092/+0,060, caja +0,222/+0,097; 18 al año; peor bache −9,6 R (la actual −23,6 R), peor racha 6 (21). S&P como
  contraste: +0,056/−0,065, +0,175/+0,046, +0,162/+0,090. Ojo: desde 2019 buena parte es estar comprado en un Nasdaq que sube
  (el azar también gana). En el reto, sumada a mitad de riesgo: The5ers 2 %, 2016-22 ≤12 m 64 % y quema 27 % (la actual 57 % y 35 %).
- **F-015 · Otras velas (PROBADA, descartada).** El mismo sistema en 30 min, 2 h y 4 h: solo funciona en 1 h. 4 h en el Nasdaq
  queda en +0,05 R (poco); 30 min y 2 h, cero o negativo.
- **F-016 · Qué pone el CMF en el sistema de 1 h (PROBADA): es la pieza que funciona.** Todos los mínimos nuevos sin filtro:
  S&P −0,010 R, Nasdaq +0,032. Con CMF > 0,025: +0,070 y +0,097. Con CMF rojo: −0,025 y +0,020. En 2023-26: verde +0,20/+0,30,
  sin filtro +0,01/−0,08, rojo −0,10/−0,12. OBV, RSI < 30, volumen 1,5x y vela que cierra arriba no lo igualan. (En 2003-18 del
  Nasdaq el filtro no ayudaba.)
- **F-017 · Riesgo según el colchón (PROBADA) → candidata para The5ers.** Riesgo por operación = (lo que queda hasta el −6 %) / 3,
  entre 0,5 % y 4 %: empieza en 2 %, sube al ganar y baja al perder. Frente a 2 % fijo: 2016-22 ≤3 m 29 % (17 %), quema 21 %
  (26 %), mediana 4,4 meses (5,8); 2023-26 ≤3 m 55 % (43 %), quema 0 % (4 %), mediana 2,8 (3,2). Aproximada con la serie diaria.
  En el robot 2.1: «Riesgo según el colchón».
- **F-018 · Cazar las caídas que se le escapan al indicador (PROBADA el 11-nov, descartada salvo lo que ya había).** Censo con
  zigzag del 2,5 % en 1 h desde 2003: Nasdaq 857 caídas de 2,5 % o más (37 al año), el sistema entra cerca del suelo en el 15 %
  (13 % en 2023-26); S&P 597 caídas, 12 % (14 %). Por qué se escapan: Flujo rojo en el suelo 53 % (65 % en el S&P 2023-26),
  no se rompe el suelo de 3 días 26 %, Flujo neutro 4 %, espera tras otra señal ≤ 3 %, stop antes del suelo 1-3 %.
  15 reglas × 2 índices, escritas antes: C1 verde tardío (1 y 3 días), C2 suelo recuperado (1 y 3 días), C3a-d niveles desde
  el máximo de 252 días (cada 2,5 %; solo −2,5/−5/−10; con vela verde), C4 segundo intento tras el stop, C5a/b señales
  bloqueadas por la espera, C6 Flujo verde en 4 h, C7 verde dentro de la zona de caída sin romper el suelo. Dos azares: el de
  siempre y «caída igual» (entradas al azar a la misma distancia del máximo del año ±1 punto).
  **Resultado: ningún disparador con stop corto gana a los dos azares en los tres tramos y los dos índices.** Solo las rejillas
  de niveles con stop ancho (3,6 %, 1 R / 2 R) son positivas en todas partes, y **no ganan a «caída igual»**: lo que paga es
  estar comprado dentro de la caída con stop ancho, no el disparador. No repetir con otros disparadores.
- **F-019 · La caída también en el S&P, a medio riesgo (PROBADA el 11-nov) → adoptada en el plan y en el robot 2.2.** Mismas
  reglas que en el Nasdaq (F-014), sin tocar nada. S&P (sistema/azar): aprender +0,056/−0,065, comprobar +0,175/+0,046, caja
  +0,162/+0,090; 14,8 al año; años malos 2008 −8,9 R, 2018 −4,4, 2022 −6,5 (Nasdaq: 18 al año; 2008 −4,2, 2022 −4,3).
  Correlación diaria entre las dos caídas 0,21 (mensual 0,58); el 49 % de las entradas del S&P cae a 1 día de una del Nasdaq:
  no son dos apuestas independientes, por eso van a medio riesgo cada una. Cobertura del censo: 15 % → 63 %.
  Reto con el plan entero (The5ers, colchón): 2016-22 ≤3 m 31 %, ≤6 m 56 %, ≤12 m 69 %, quema 24 %, mediana 3,7 meses (solo
  con la caída del Nasdaq: 29/49/64/21/4,4); 2023-26 64/80/100, quema 0 %, mediana 2,1 (55/83/100/0/2,8). FTMO 1 % 2023-26:
  ≤6 m 49 % (32 %). Escalera cada 2,4 % en los dos: cubre el 88 % pero quema el 33 % en FTMO 2016-22 → no adoptada.
  Mapa de profundidad (compra de prueba cada 4 h, stop 3,6 %): a menos de 2,5 % del máximo del año −0,06 R en 2003-18; entre
  2,5 y 10 % casi siempre positivo; más hondo, errático → no se pondera por profundidad.
- **F-020 · El sistema según la zona de la caída (PROBADA el 11-nov, descartada).** R del motor 1 según a qué distancia del
  máximo del año salta la señal (menos de 2,5 %, 2,5-10 %, más de 10 %): sin patrón estable entre tramos ni entre índices.
  No se cambia el tamaño.
- **F-021 · TAREA FIJA: vigilar las dos caídas en la sombra.** No es una idea que probar: es seguimiento. `fondeo_base.md` trae
  cada martes y jueves el R medio de las 20 últimas operaciones de cada caída y de las nuevas desde el inicio de la sombra.
  Aviso a Pe (primera línea del Telegram) si pone ⚠️: las 20 últimas en el 10 % peor de su historia, o 20 operaciones nuevas
  con media bajo 0 R. Es la pieza más nueva y la que no gana a «caída igual»: si falla, es la primera que se apaga.
- **F-022 · Fusionar los dos indicadores en un robot (PROBADA el 12-nov, descartada: se queda como está).** Escrito antes:
  F1 una sola posición por índice (el primero que llegue); F2 igual con la caída a riesgo entero; F3a indicador solo si el
  precio está ≥ 2,4 % bajo el máximo de 20 días; F3b caída solo con Flujo verde (CMF > 0,025); F4 caída a riesgo entero si
  el Flujo está verde; F5 caída a riesgo entero si el indicador entró en los 3 días anteriores. Base: los dos por separado.
  **Hallazgo clave: cuando coinciden, la caída sale PEOR.** Caída con Flujo verde frente a sin él (aprender / comprobar /
  caja): Nasdaq −0,045 / −0,231 / +0,126 frente a +0,147 / +0,215 / +0,291; S&P −0,168 / +0,023 / +0,080 frente a
  +0,134 / +0,239 / +0,200. Con el indicador en los 3 días anteriores, también peor en el Nasdaq en los tres tramos. La caída
  funciona justo cuando el Flujo está rojo, que es cuando el indicador no salta: por eso se complementan.
  Retos (The5ers colchón, ≤ 3 m en 2023-26 / 2016-22, quema 2016-22): base 64 / 31 / 24 %; F1 43 / 20 / 26 % (peor día al
  1 % −2,20 % en vez de −3,65 %); F3b 50 / 26 / 32 %; F3a 52 / 24 / 12 % (el filtro no es estable en el Nasdaq); F4 64 /
  35 / 35 %; F5 59 / 32 / 23 %. Ninguna gana a la base sin subir la quema o frenar. No repetir.

## Preguntas abiertas que dejó la revisión (por si te inspiran; no son órdenes)
- La caída gana por estar dentro con stop ancho. ¿Hay una forma de estar dentro **más barata** (menos días expuesto, o salir
  antes cuando el mercado sigue cayendo) que no empeore la tabla de retos? Ojo: afinar stops y objetivos ya se vio que es ruido.
- Los años malos de la caída (2008, 2018, 2022) son mercados que siguen cayendo. Las pistas vivas de la terminal (pánico
  vivo, VENTA EXTREMA) ¿avisan a tiempo para ir a medio tamaño? Solo con datos que existan en 1 h o al cierre anterior.
- En The5ers, el −3 % del día pausa. ¿Compensa un tope propio más bajo (por ejemplo −2 %) con cinco gráficos abiertos?

## Ideas propias del agente
(las apunta el agente; 3 por sesión de fondeo)

### Sesión del 24-nov-2026 (escritas ANTES de probar)
- **F-023 · [DESCARTADA 24-nov: ocurre lo contrario; ver estudios/F-023.md] Miedo alto = caída más pequeña (ángulo a, gestión).** Los años malos de la caída (2008, 2018, 2022) son mercados con
  miedo. Regla: la operación de «caída» (NAS y SPX) entra con el peso de siempre (0,5) salvo que el VIX del cierre ANTERIOR sea
  ≥ 30; entonces peso 0 (A) o 0,25 (B). Variantes (5 como mucho, fijadas ya): A = VIX≥30 → peso 0; B = VIX≥30 → peso 0,25;
  C = VIX≥25 → peso 0; D = VIX/VIX3M ≥ 1,0 (solo desde 2009) → peso 0; E = lo contrario: VIX≥30 → peso 1 (porque la pista
  viva dice que VIX alto mejora las entradas). VIX diario de `historiales/cboe_vix.csv` (desde 1990). Confirma: la caída con VIX
  alto rinde peor en aprender (≤2018) Y en comprobar (2019-22), y al aplicar la regla The5ers (colchón) baja la quema o sube
  «≤ 12 m» en 2003-15 y 2016-22 sin empeorar 2023-26. Tumba: R igual o mejor con VIX alto, o la mejora solo sale en un tramo,
  o N < 30 con VIX alto. Frente al azar «caída igual».
- **F-024 · Tope propio de −2 % al día con 5 gráficos (ángulo a).** Si el plan pierde ≥ 2 % en el día (en R × riesgo), no se abre
  nada más ese día. Pregunta abierta de la revisión: ¿compensa frente a la pausa de The5ers al −3 %? Pendiente (necesita
  simulador propio en `fondeo_extra.py`).
- **F-026 · (apuntada tras ver F-023; NO es limpia) Caída al doble con el VIX en «backwardation».** En F-023 salió que la caída
  con VIX/VIX3M ≥ 1,0 (cierre anterior) rinde mucho más (NAS +0,45 R N 42; SPX +0,28 N 46; positivo en los tres tramos). Pero
  lo vi mirando todos los tramos, incluida la caja, así que NO puede dar «candidata»: solo vale como pista. Para volverla limpia
  habría que esperar a datos nuevos (la sombra) o a otro activo. Regla única: peso 1,0 en lugar de 0,5 si ratio ≥ 1,0.
  Ojo: con tan pocos casos (42 y 46 en 15 años) es fácil que sea suerte, y esos días son justo los de caída fuerte.
- **F-025 · Lo contrario de lo que falla (ángulo f):** EUR/JPY pierde hasta 2022 y solo gana desde 2023. Antes de darle la
  vuelta hay que ver si pierde ANTES de costes y en los tres tramos; si es ruido, se descarta. Pendiente.

### Sesión del 26-nov-2026 (escritas ANTES de probar)
- **F-027 · [DESCARTADA 26-nov: el motor 1 pierde (−0,12 R, caja −0,31) y la caída es ~0; añadirlos sube la quema; ver estudios/F-027.md] Russell 2000 (US2000) con las mismas reglas (ángulo c).** Sin tocar ningún número:
  motor 1 (`sistema_actual("us2000")`) y caída (`caida("us2000")`, 2,4 % / stop 3,6 %). Variantes (5, fijadas ya): A = motor 1
  solo; B = caída sola; C = plan de Pe + motor 1 de US2000 a peso 1; D = plan de Pe + caída de US2000 a peso 0,5; E = plan de Pe
  + las dos de US2000 a medio peso. Confirma: R > 0 en aprender (≤2018) Y comprobar (2019-22), gana al azar justo (y a «caída
  igual» en la caída) con N ≥ 30 por tramo, y al añadirla a `plan_completo()` en The5ers (colchón) sube «≤ 12 m» o baja la quema
  en 2003-15 y 2016-22 sin empeorar 2023-26 ni el peor día (−3,65 %). Tumba: R ≤ 0 en algún tramo, N < 30, no gana al azar, o
  el reto no mejora (el Russell se mueve casi como el S&P: puede ser la misma apuesta repetida).
- **F-028 · Salida por tiempo en la caída (ángulo b; pregunta abierta «estar dentro más barato»).** Si a las 72 h de la entrada
  la operación no está por encima de la entrada, se cierra a mercado (en vez de esperar 10 días). Variantes: 48 h, 72 h, 120 h.
  Confirma: R medio igual o mejor y menos días expuestos, y mejor tabla de retos en comprobar y caja. Tumba: R peor en
  cualquiera de los dos índices (afinar salidas suele ser ruido). Pendiente.
- **F-029 · Segunda caída a peso reducido si la otra ya está abierta (ángulo a).** El 49 % de las entradas del S&P cae a 1 día
  de una del Nasdaq (la del 17-nov perdió las dos a la vez). Regla: la caída del S&P (o del Nasdaq, la que llegue segunda) entra a
  peso 0,25 si la otra está abierta. Variantes: 0,25 y 0. Confirma: baja la quema sin bajar «≤ 12 m» en 2003-15 y 2016-22.
  Tumba: cuando coinciden las dos, la segunda rinde igual o mejor. Pendiente.

## Contador
Ideas probadas: 15 (F-027: 5 variantes + 2 diagnósticos; F-023: 5 variantes + diagnóstico por grupos; F-008: 12 pruebas; F-009: 15; F-010: 11; F-011: 12 + filtro; F-012: 15; F-014: 75 + 12 de contraste; F-015: 8; F-016: 22; F-017: 8; F-018: 30 (15 reglas × 2 índices); F-019: 6 mezclas de reto; F-020: 6; F-022: 6 variantes × 2 índices)
Con tantas pruebas, una idea que salga bien por los pelos no significa nada.
