# Informe del compañero — 2026-11-20 (viernes; repaso semanal rehecho el domingo 22-nov con la terminal v8.7)
## En una frase
Sigue pendiente lo del viernes: el SPY (−11,8 %) y el QQQ (−20,2 %) tocaron a la vez sus escalones (S&P −10 %, Nasdaq −20 %), con VIX 35,9 y pánico vivo; el primer mercado abierto para actuar es el lunes 23. **Ojo: la terminal nueva (v8.7) tiene un fallo: su «plan de rebajas» no calcula el Nasdaq, así que enseña el escalón del S&P pero NO el del Nasdaq, que también ha tocado.**

## 1. ¿Funciona todo? (vigilante)
Formalmente 🟢 (todo grabado, sin avisos nuevos). Pero al leer la terminal nueva encuentro cosas que el vigilante no ve:
- 🔴 **El plan de rebajas no calcula el Nasdaq (los 5 escalones del QQQ).** `plan_rebajas_estado.json` solo trae el S&P (3 filas) y nada del QQQ. Causa: `compute_plan_rebajas` (`rotacion.py` línea 24900) lee los precios con `daily.get(sym)`, pero el QQQ no está en `daily` (el detector lo toma de `OPER_QQQ["d"]`, líneas 23052 y 23504); sin dato, el código se salta el QQQ **sin dar ningún aviso**. Lo he comprobado con precios de Yahoo: máximo del QQQ 762,86 (6-oct), línea del −20 % 610,29, cierre del viernes 608,45 → el escalón tocó el 20-nov y la terminal no lo marca. Arreglo (una línea): `d = OPER_QQQ.get("d") if sym == "QQQ" else (daily or {}).get(sym)`. Mismo fallo menor en la línea 24497 (cambio del día del QQQ en «Caída en curso»). No he podido ver la web, solo el código y los archivos.
- 🟠 **Pestaña «Caída en curso»: la probabilidad de recesión (3 %, «modo NORMAL», 0 alarmas) sale de UNA sola fuente de cinco.** En `caida_estado.json` solo consta el mercado de apuestas; no hay ni una serie de FRED guardada en `historiales/` (curva de tipos, paro, Sahm, crédito). Desde aquí FRED responde bien, así que lo que falla es la descarga en la máquina de GitHub. «0 alarmas» aquí significa «no hay datos», no «todo tranquilo».
- 🟠 **Subidas de hoy:** (a) tu `agente/ideas.md` subido esta mañana **borró mi registro** (volvió a I-004 «en cola» y contador 0, sin I-005 ni I-006): lo he restaurado desde git; (b) `fondeo/ideas.md` y `herramientas/fondeo.py` están en la raíz del repositorio, no donde los busca mi manual: `agente/fondeo/` no existe y en `agente/herramientas/` solo está `datos.py`. Yo solo puedo escribir dentro de `agente/` y no puedo cambiar `fondeo.py`, así que tienes que moverlos tú (no afecta hoy, que es modo semanal; sí el martes); (c) el `preparar.py` nuevo sigue con el fallo del marcador congelado (6.º día): lo he parcheado en sitio y vuelto a ejecutar (sin el parche GIRO↑ sale con 10 casos en vez de 34).
- Sigue igual desde hace días: un cierre rehecho con barras de 1 hora (céntimos), IV descartada en 5 ETF, put/call fuera de banda en 15, 6 acciones sin datos, pesos del QQQ de Invesco con error 406 (se usan los del 12-nov), petróleo sin cierre válido, `universo_close` parado desde el 3-nov (sin consecuencias).
- **Cable de señales:** 54 fechas de 60 (13-ago → 20-nov). Se llena el 1-dic y el 2-dic empieza a borrar días ya maduros (propuesta 2).

## 2. El plan (la terminal v8.7 dice que el único es el «plan de rebajas»; las 4 balas siguen guardadas)
**Plan de rebajas (cierre del 20-nov; % del plan, sin importes).** Escalón = línea desde el máximo; «x3/x2» = ETF apalancado. Pasa a normal al recuperar 1/3 de la caída (1/2 los hondos) y todo queda en normal al volver al máximo.
| Escalón | % plan | Producto | Línea | Estado |
|---|---|---|---|---|
| S&P −10 % | 10 | x3 | 703,46 | **TOCADO el 20-nov** (cierre 689,81) |
| Nasdaq −20 % | 10 | x3 | 610,29 | **TOCADO el 20-nov** (cierre 608,45) · *la terminal no lo muestra (fallo de arriba)* |
| S&P −15 % | 10 | x3 | 664,38 | falta −3,7 % |
| Nasdaq −25 % | 15 | x3 | 572,14 | falta −6,0 % |
| S&P −20 % | 10 | x2 | 625,30 | falta −9,4 % |
| Nasdaq −30 % | 15 | x2 | 534,00 | falta −12,2 % |
| Nasdaq −40 % | 15 | x3 solo si el VIX cierra ≥ 40; si no, normal | 457,72 | falta −24,8 % |
| Nasdaq −50 % | 15 | ídem | 381,43 | falta −37,3 % |
El VIX está en 35,9: aún por debajo del 40 que pide el plan para los escalones hondos en x3. Si el SPY no bajase más del cierre del viernes, su paso a normal quedaría hacia 720,4 (1/3 de la caída desde 781,62); para el QQQ, hacia 660 (cálculo mío con la misma regla, porque la terminal no lo calcula).
**Las 4 balas (`balas_estado.json`, siguen guardándose; mi manual aún las trata como el plan):** bala 1 (se va el pánico) dada el 9-nov; **bala 2 (SPY −10 %) y bala 3 (QQQ −20 %, SIN rendición total) saltaron el 20-nov**; bala 4 (SPY −20 % o QQQ −30 %) sin saltar. Rendición total: cumple 2 de 3 (sectores 7 de 8, VIX/VIX3M 1,16); falta la amplitud: 13,2 % de acciones en mínimos, hace falta 20 % (ayer 9,2 %). El plan de rebajas **no usa la rendición** para repartir el escalón del Nasdaq: es una diferencia de diseño entre los dos planes (pregunta para Pe).
**Pánico:** vivo desde el 20-nov (VIX/VIX3M 1,16; ayer 1,05). Se va con el primer cierre por debajo de 1,0. El plan de rebajas no tiene un escalón de «se va el pánico». **Control del mes (7-dic):** el SPY ya está más abajo (−11,8 %) que la franja que mide (−5 a −10 %); solo se aplicaría si vuelve a ella. Russell (IWM) −15,7 %: su −20 % (243,51) a −5,1 %.
**Cuándo se actúa:** lo que saltó con el cierre del viernes se actúa con ese cierre; como es fin de semana, el primer mercado abierto es el lunes 23. Jueves 26 EE. UU. cerrado; viernes 27 media sesión (cierra a las 19:00 en Bilbao).

## 3. Qué dice hoy la terminal
Caídas desde el máximo de 52 semanas: SPY −11,8 %, DIA −11,6 %, QQQ −20,2 %, IWM −15,7 %, MAGS −17,5 %, RSP −7,5 % (la caída la lidera el Nasdaq y los grandes). En el día: SPY −3,6 %, QQQ −5,7 %. VIX 35,9. Dinero: **VENTA EXTREMA** (0 sectores entran, 7 salen). Centinela LIQUIDEZ. Notas de los índices: todas BAJA (solo contexto; medida el 10-nov, la nota va al revés). DIX 38,8 (percentil 1) y GEX negativo por segundo día; no son señales demostradas. Volumen en dólares de los 8 apalancados de compra (tu idea, I-007): hoy hay pico (z 2,4; ver sección 5).
**Bono y MOVE (dato a vigilar, no una bala):** el 10 años cierra en 4,91 %, a 41 puntos básicos de tu línea del 4,5 % (−4 pb en un mes, −24 pb en 5 sesiones). El MOVE (volatilidad de los bonos) está en 106 (percentil 96 del año): salta el aviso de «tensión» de hoy. El bono largo (TLT) subió +2,6 % en la semana mientras el oro cayó −9,2 %.
**Pestaña nueva «Caída en curso» (v8.7, solo informa):** suelo 49 % = media de 41 % por el ciclo (caídas parecidas del S&P, 15 casos) y 57 % por el miedo (solo **10 casos**: intervalo de confianza ancho, 31-83 %). Es la frecuencia de caídas parecidas que ya habían hecho suelo, no un pronóstico. Ya había dicho el viernes: casilla «MADURA» del S&P (33 sesiones desde su máximo): extra mediana −4,4 %, el 21 % cae ≥ 10 % más, +4,5 % a 60 sesiones (N 15, orientativo); el QQQ no tiene casilla con historia.
**Cosas que se pueden pasar por alto (3):**
1. **Dos sitios que se contradicen:** el detector y las balas dicen «QQQ −20 % tocado»; el plan de rebajas (la tabla de «Hoy» por el código) no lo tiene. Y al arreglarlo, el escalón saldrá como «comprado el 20-nov», no como «HOY TOCA»: el cartel de hoy solo sale el día del cierre.
2. **«Recesión 3 %, modo NORMAL, 0 alarmas» con 4 de 5 fuentes sin descargar** (sección 1): con el VIX en 36 no te quedes con «NORMAL».
3. **Importes en euros en archivos públicos.** El repositorio es público y la terminal v8.7 escribe el importe total del plan en `rotacion.py` (línea 24844) y el importe de la compra de ayer dentro de `plan_rebajas_estado.json` (campo «avisado»). Yo no los copio, pero cualquiera puede leerlos. Mejor guardarlos fuera del repositorio.

## 4. Marcador (mismo día de mercado que el viernes: los números no cambian)
- **GIRO↓** 31 casos a 20 sesiones: acierto 74 % (IC 57–86), exceso +8,5 pts (t 3,9). **GIRO↑** 34 casos: 26 % (IC 15–43), exceso −5,4 (t −2,5): «va al revés». Con el control de azar (mismo activo, mismas fechas) no hay señal propia: GIRO↑ +0,1 pts (t 0,1), GIRO↓ +0,9 (t 0,4). **I-001 cerrada.**
- **SUELO** (n 16): acierto 56 %, exceso +2,9 (t 1,4); con el control de azar +4,8 netos (t 3,07; agrupado por fechas t 2,84 con 10 fechas) y **EARLY** +4,1 (n 15, t 2,3; por fechas 1,96): sigue en vigilancia, con 10 señales mirándose a la vez el mejor sale bueno por azar. Resto con |t| < 1,8. FLOW 18 casos, 78 %, t 1,7.
- Filas nuevas por el `preparar.py` actualizado (todas n = 1, no dicen nada): BALA 1 / SE VA EL PÁNICO (9-nov: el SPY perdió −2,3 % en las 5 sesiones siguientes), BALA 2, BALA 3, MOVE. El cable no guardó nunca el «se va el pánico» del 9-nov; ahora el marcador lo reconstruye desde `balas_estado.json`.
- Señales del plan en el cable (NIVEL SPY/DIA/QQQ, BALA ×2, PÁNICO SPY del 20-nov): se medirán a 20 sesiones, hacia el 22-dic.

## 5. Investigación
**I-005 (viernes 20-nov, ya cerrada): «se va el pánico» frente a entrar con el pánico vivo → DESCARTADA.** 28 episodios del SPY 2009-22 (60 sesiones): aprender −2,5 pts (t −1,9), comprobar +10,8 (solo 3 viernes de comparación, todos de 2020), todos +0,4 (t 0,2). Signo distinto entre mitades: no hay datos que apoyen esperar a «se va el pánico». No prueba que esperar sea peor. Detalle: `estudios/i005.md`.
**I-007 (hoy; idea tuya del 9-nov: volumen en dólares de los apalancados de compra) → DESCARTADA: sin ventaja visible, y muy pocos casos para decir más.**
Regla apuntada antes de calcular (`ideas.md`): *pico* = el volumen en dólares de TQQQ, UPRO, SPXL, SSO, QLD, SOXL, TECL y TNA sumados (en logaritmos) 2 desviaciones por encima de su media de los 252 días anteriores; *caída* = SPY ≥ 8 % bajo su máximo. Se compara cada episodio de pico con días parecidos SIN pico (misma mitad de la historia, caída ±2,5 pts, mismo estado de miedo), contando episodios y no días. SPY a 60 sesiones:
| Principal (z ≥ 2, caída ≥ 8 %) | Aprender 2010-18 | Comprobar 2019-22 |
|---|---|---|
| Exceso de los días con pico | −0,7 pts (N 6, t −0,4) | −0,1 pts (N 2) |
- Criterio apuntado: confirma con ≥ +1 pt en las dos mitades y ≥ 8 episodios en cada una. No se cumple ni lo uno ni lo otro (13 episodios en total, pero solo 8 con días parecidos suficientes). Las otras 4 variantes (z ≥ 3; pico en cualquiera de los 3 últimos días; caída ≥ 5 %; solo con VIX/VIX3M ≥ 1,0) tampoco muestran ventaja: con caída ≥ 5 % (21 episodios) sale −2,4 pts (t −1,7), es decir, si acaso los días con pico rinden algo peor. El script también calcula la caja 2023-26 (sale en la tabla, 4 episodios en la variante ≥ 5 %); no la uso para decidir.
- **Lo descriptivo (sin azar, solo para tu pregunta «¿separa las V de las caídas que siguieron?»):** de las 10 caídas del SPY de ≥ 10 % desde 2010, hubo pico en 6 (2010, 2011, 2016, feb-2018, 2020 y 2025) y no en 4 (2015, 4.º trimestre de 2018, 2022 —quedó en z 1,98, a un pelo del umbral— y 2023). El máximo del pico coincidió con el suelo solo en 2018 y 2025; en 2020 el primer pico fue el 27-feb y el suelo el 23-mar, y en 2011 llegó dos meses antes del suelo. En los 5 casos cuyo primer pico llegó con el SPY entre −10 y −12 % (2010, 2011, 2016, 2018 y 2020), 4 siguieron cayendo (−4, −7, −2 y −22 puntos más; 2018 no). Sirve como «ya hay miedo», no como «ya es el suelo». Frecuencia histórica con N = 5-6, no predicción.
- **Hoy:** z = 2,4 con el SPY en −11,7 %: hay pico, como en esas caídas que acababan de empezar a dar miedo. No lo meto en la terminal: con este tamaño de muestra no aporta nada medible a lo que ya mide la terminal (pánico, rendición).
- Variantes miradas: 5 (las apuntadas). Ideas probadas: 4 (todas descartadas). Detalle: `estudios/i007.md`. Queda en cola para el viernes 27-nov **I-006** (¿importa lo rápido que la caída va del −5 % al −10 %?).

## Semana (13 → 20-nov)
- **Mercado:** SPY 754,37 → 689,81 (−8,6 %); QQQ −10,5 %; IWM −7,5 %; RSP −6,2 %; DIA −8,0 %; oro −9,2 %; bono largo +2,6 %. VIX 19,3 → 35,9; VIX/VIX3M 0,94 → 1,16.
- **Detector:** SPY de −3,5 % a −11,8 % del máximo; QQQ de −10,9 % a −20,2 %. Dinero: MIXTO → SALE DE TODO → VENTA EXTREMA. Centinela: ACECHO → LIQUIDEZ (18-nov).
- **Cesta semanal:** −4,7 % frente a SPY −8,6 %. En 12 semanas: −0,99 % frente a −0,96 %; mejor que el SPY 5 de 12 (IC 19–68 %). Una semana buena en una caída es lo esperable de una cesta defensiva; no demuestra nada.
- **Pendiente de que decidas:** propuestas 1 y 2.

## 6. Propuestas para Pe
1. **Arreglar el plan de rebajas para que lea el Nasdaq** (una línea, `rotacion.py` 24900; ver sección 1). Por qué: hoy el plan único solo enseña 3 de sus 8 escalones y se salta el que ya tocó en el Nasdaq, sin avisar. Qué lo desmentiría: que en la pestaña «Hoy» (que no puedo ver) ya aparezcan las filas del Nasdaq; entonces el fallo estaría solo en el archivo guardado.
2. **(Repetida, con fecha límite 2-dic) Ampliar el cable de señales** (`rotacion.py` línea 3023, hoy 60 fechas). Por qué: el marcador se recalcula entero desde ese archivo y el 2-dic empezaría a perder días maduros. Qué lo desmentiría: que ese archivo no pierda fechas en diciembre. Si no se cambia, reconstruyo el cable desde git antes de cualquier cálculo largo.

## 7. Lo que necesito de Pe
- Decirme **cuál manda: las 4 balas (mi manual, subido hoy a las 08:34) o el plan de rebajas (terminal v8.7)**. Mi manual aún dice «un solo plan: las 4 balas»; la terminal y el `preparar.py` nuevo dicen que el único plan es el de rebajas. Si manda el de rebajas, mis dos preguntas del 20-nov sobre las balas (rendición posterior al toque; segundo «se va el pánico») dejan de tener sentido.
- Mover `fondeo/ideas.md` a `agente/fondeo/ideas.md` y `herramientas/fondeo.py` a `agente/herramientas/fondeo.py` (el martes los necesito).
- Subir el arreglo de `agente/preparar.py` (línea 231: `start=str(desde)` → `start=pd.Timestamp(desde).strftime("%Y-%m-%d")`) o decirme que no importa.
- Decidir lo del cable antes del 2-dic y dónde guardar los importes del plan (sección 3, punto 3).
- Nada más. No digo compra ni vende: la terminal marca los escalones y tú decides.
