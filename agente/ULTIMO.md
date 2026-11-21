# Informe del compañero — 2026-11-20 (viernes, modo semanal)
## En una frase
Viernes de caída fuerte: el SPY pierde otro 3,6 % en el día (−11,8 % desde su máximo) y el QQQ otro 5,7 % (−20,2 %). Con el cierre del viernes han saltado **a la vez** el SPY −10 % (bala 2) y el QQQ −20 % (bala 3, **SIN rendición total**), y ha empezado un pánico nuevo (VIX 35,9). Además la investigación de esta semana (I-005) sale negativa: no hay datos de que esperar a «se va el pánico» sea mejor que entrar con el pánico vivo.

## 1. ¿Funciona todo? (vigilante)
🟢 Todo grabado y sin avisos nuevos. El único aviso del día es el de siempre (un cierre rehecho con barras de 1 hora, céntimos de diferencia). Sigue igual desde hace días: opciones y acciones sin datos, `universo_close` parado desde el 3-nov (17 días; sin consecuencias hoy).
**Marcador congelado, 5.º día:** la máquina volvió a dejar `agente/preparar.py` sin mi arreglo (lo restaura por diseño). Lo parcheé en sitio y regeneré el resumen: con el arreglo GIRO↑ tiene 34 casos medidos; sin él, 10.
**Cable de señales:** 54 fechas de 60. Se llena el 1-dic y el 2-dic empieza a borrar días ya maduros (ver propuesta 2).

## 2. Señales del plan (una línea cada una; lo que ha cambiado)
**Saltaron con el cierre del viernes 20-nov:**
- **SPY −10 % (bala 2): TOCADO.** Cierre 689,81; la línea estaba en 703,46.
- **QQQ −20 % (bala 3): TOCADO.** Cierre 608,45; la línea, en 610,29 (lo cruzó por solo un 0,3 %). **Rendición total: NO.** Cumple 2 de las 3 condiciones: sectores sacando dinero 7 de 8 (sin contar tecnología; hace falta ≥ 6) y VIX/VIX3M 1,16 (hace falta ≥ 1,10). **Le falta la amplitud:** 13,2 % de las acciones del S&P en mínimos de 52 semanas, hace falta 20 % (ayer 9,2 %: sube ~4 puntos por día).

**Sin saltar:**
- **Se va el pánico (bala 1): no.** Al revés: **pánico vivo nuevo desde hoy** (VIX/VIX3M 1,16; ayer 1,05. VIX 35,9; ayer 28,4). El anterior empezó el 5-nov y se fue el 9-nov. Este se irá con el primer cierre de VIX/VIX3M por debajo de 1,0: hoy habría que bajar 0,16. (Hoy hay también «pánico agudo», que es solo una foto del día y no es lo mismo que «pánico vivo».)
- **Bajista:** SPY −20 % en 625,30 (falta −9,3 %); QQQ −30 % en 534,00 (falta −12,2 %). El Russell (IWM) está en −15,7 % y su −20 % (243,51) está a −5,1 %: más cerca que el SPY. Si lo toca antes, el propio plan cambia el S&P por Russell en la bala 4.
- **Control del mes (7-dic, 10 sesiones):** sin cambios de regla, pero el SPY ya está más abajo (−11,8 %) que la franja que mide (−5 a −10 %); solo se aplicaría si para entonces vuelve a esa franja.

## 3. Qué dice hoy la terminal
Caídas desde el máximo de 52 semanas: SPY −11,8 %, DIA −11,6 %, QQQ −20,2 %, IWM −15,7 %, MAGS −17,5 %, RSP −7,5 %. En el día: SPY −3,6 %, QQQ −5,7 %, IWM −2,9 %, RSP −2,0 % (la caída la lidera el Nasdaq). Dinero: **VENTA EXTREMA** (0 sectores entran, 7 salen; salida de dinero en el 64 % de las acciones y entrada en el 14 %). Notas: todas BAJA. Centinela LIQUIDEZ (el más defensivo: por la jerarquía del sistema manda). Semáforo: rojo con pánico agudo en SPY, DIA y QQQ. Otros datos: DIX 38,8 (percentil 1 de su historial) y GEX negativo (−2,2 mil millones) por segundo día seguido; no son señales demostradas.
**Historia de la casilla de hoy (rejilla de ciclos de la propia terminal; frecuencia histórica, no predicción):** el SPY lleva 33 sesiones desde su máximo del 6-oct y está en −11,8 %: caída «MADURA». En las 15 caídas del S&P de 1950-2025 con esa edad y esa profundidad, la caída extra mediana hasta el suelo fue −4,4 %, el 21 % (unos 3 de 15; intervalo de confianza aproximado 7-45 %) cayó 10 % más y la rentabilidad media a 60 sesiones fue +4,5 % (N = 15: solo orientativo; la terminal no guarda el recuento exacto). El DIA (−11,7 %, N 20) y el IWM (−15,7 %, N 7) tienen casillas parecidas; el QQQ **no tiene casilla con historia** (solo 2 caídas desde 1999 llegaron al −20/−30 % en 22-42 sesiones).
**Calendario:** el jueves 26 EE. UU. está cerrado (Acción de Gracias) y el viernes 27, el siguiente día de actuar, es media sesión (cierra a las 13:00 de Nueva York = 19:00 en Bilbao), con poco volumen. Esta semana el oro (GLD) ha caído un −9,2 % (más que el SPY) mientras el bono largo (TLT) subía +2,6 %: en esta caída el oro no está haciendo de refugio.

**Cosas que se pueden pasar por alto (3):**
1. **La bala 3 queda fijada «SIN rendición» hoy.** El código decide «con o sin rendición» solo el día del toque y lo guarda (`rotacion.py` línea 23714; `balas_estado.json`: bala 3, rendición = false). Si el lunes o el martes la amplitud llega al 20 %, la línea viva dirá «rendición total hoy: SÍ» pero el texto de la bala 3 seguirá diciendo «SIN rendición total → media bala»: dos mensajes contrarios en la misma pestaña. Lo señalo, no lo toco (propuesta 1).
2. **Segundo pánico en la misma caída:** la bala 1 ya está «dada» el 9-nov (una por caída, línea 23703). Cuando este pánico se vaya, la tarjeta del pánico dirá «SE VA HOY: es la señal de la bala 1» (línea 24084), pero la fila de la bala 1 seguirá «dada el 9-nov». Hay que decidir si esa segunda «se va el pánico» cuenta como bala 1 nueva (propuesta 1). Hoy el semáforo ha vuelto a marcar «guarda el resto» en SPY, DIA y QQQ.
3. **Etiqueta engañosa en el QQQ:** con −20,2 % tras 33 sesiones, la tabla de caídas lo llama **«CORRECCIÓN»** (línea 23432). No es una señal: es la etiqueta por defecto cuando no encaja en RÁPIDA, MADURA ni LARGA. Un QQQ en −20 % es, en el lenguaje habitual, mercado bajista; no te quedes con la palabra.

## 4. Marcador (precios al día; todo orientativo salvo lo que diga)
- **GIRO↓** 31 casos a 20 sesiones: acierto 74 % (IC 57–86), exceso +8,5 pts (t 3,9). **GIRO↑** 34 casos: 26 % (IC 15–43), exceso −5,4 (t −2,5): «va al revés». Las dos ya pasan de 30 casos.
- **Control de azar** (mismo activo, mismas fechas; `estudios/control_azar_marcador.py`): GIRO↑ +0,1 pts netos (t 0,1) y GIRO↓ +0,9 (t 0,4). Lo que se ve es lo que hacían esos activos (semis, plata, temáticos), no la señal. **I-001 queda cerrada: sin señal propia.**
- **SUELO** +4,8 netos (n 16, t 3,07) y **EARLY** +4,1 (n 15, t 2,3). Nuevo control agrupado por fechas (varias señales el mismo día no son pruebas separadas; `estudios/control_azar_agrupado.py`): SUELO t 2,84 con 10 fechas, EARLY t 1,96 con 11. Con 10 señales mirándose a la vez, el mejor sale por azar con facilidad: sigue sin ser una prueba (n < 30, un solo trimestre, en plena caída). SUELO queda **en vigilancia**: se mira otra vez al llegar a 30 casos.
- Resto con |t| < 1,7. Las señales del plan ya están en el cable (NIVEL SPY/DIA/QQQ, BALA SPY ×2, PÁNICO SPY): se medirán a 20 sesiones, hacia el 22-dic.

## 5. Investigación — I-005 (viernes)
**«Se va el pánico» frente a comprar con el pánico todavía vivo → DESCARTADA.** La regla la apunté el 13-nov, antes de calcular nada, y no la he cambiado. Mismos episodios que I-004 (36 de 2009-22; 28 con viernes comparables). Rendimiento del SPY a 60 sesiones; «azar» = viernes con VIX/VIX3M ≥ 1,0 y caída del SPY parecida (±2,5 pts):

| Trozo | Episodios | «Se va» menos «pánico vivo» | t |
|---|---|---|---|
| aprender (2009-18) | 22 | **−2,5 pts** | −1,9 |
| comprobar (2019-22) | 6 | +10,8 pts | 2,9 |
| todos | 28 | +0,4 pts | 0,2 |

- Criterio apuntado: confirma si gana ≥ +1 pt en las dos mitades; tumba si el signo cambia. **Cambia: tumbada.** Peor caída posterior en 60 sesiones: en aprender, −5,1 % tras «se va» frente a −3,8 % entrando con el pánico vivo (peor, no mejor).
- **Aviso importante:** en 2019-22 el «azar» son solo **3 viernes** (31-ene, 28-feb y 6-mar de 2020: el covid). Esa mitad no puede juzgar nada; 8 de los 36 episodios se quedaron sin viernes comparable. Lo sólido es 2009-18: ahí esperar a «se va» fue 2,5 pts peor, sin llegar a ser significativo (7 de 22 por encima del azar).
- Variantes miradas: 3 (20, 60 y 120 sesiones). A 20: −0,5 / +11,5; a 120: −3,5 / −0,5 (aprender / comprobar). Caja cerrada 2023+ **sin abrir** (no pasó).
- **Qué significa:** no hay datos de que esperar a «se va el pánico» mejore la entrada frente a entrar con el pánico vivo. Junto con I-004 (tampoco mejora frente a viernes sin pánico), la pista «se va el pánico = mejor momento» se queda **sin apoyo en el SPY de 2009-22**. No prueba que esperar sea peor, y no mide los apalancados ni 2000/2008 (el VIX3M empieza en 2009). No cambia ningún plan. Ideas probadas: 3 (todas descartadas). Detalle: `estudios/i005.md`.
- Para la semana que viene dejo apuntada **I-006** (¿importa lo rápido que la caída va del −5 % al −10 %?, solo S&P 1927-2026). No se ha calculado nada.

## Semana (13 → 20-nov)
- **Mercado:** SPY 754,37 → 689,81 (−8,6 %); QQQ −10,5 %; IWM −7,5 %; RSP −6,2 %; DIA −8,0 %; oro −9,2 %; bono largo +2,6 %. VIX 19,3 → 35,9; VIX/VIX3M 0,94 → 1,16.
- **Detector:** SPY de −3,5 % a −11,8 % del máximo; QQQ de −10,9 % a −20,2 %. Dinero: MIXTO → SALE DE TODO → VENTA EXTREMA. Centinela: ACECHO → LIQUIDEZ (desde el 18-nov). Plan: de «ninguna señal» a bala 2 y 3 saltadas.
- **Marcador:** GIRO↓/GIRO↑ llegan a 30 casos y el control de azar los deja sin señal propia (I-001 cerrada). Nada se ha confirmado.
- **Cesta semanal:** esta semana −4,7 % frente a SPY −8,6 % (mejor que el SPY por 3,9 pts). En 12 semanas: −0,99 % frente a −0,96 %; mejor que el SPY 5 de 12 (IC 19–68 %). Una semana buena en una caída es lo que se espera de una cesta defensiva; no demuestra nada.
- **Propuestas pendientes para que decidas** (la 1 es nueva, la 2 lleva desde el 13-nov): ver abajo.

## 6. Propuestas para Pe
1. **Decidir dos reglas del plan de balas antes de que se usen** (yo no las toco): (a) ¿la «rendición total» de la bala 3 vale solo el día del toque (como está) o también si llega los días siguientes?; (b) ¿una segunda «se va el pánico» dentro de la misma caída es una bala 1 nueva? Por qué: hoy las dos quedan decididas por el código sin que lo hayas elegido tú (líneas 23714 y 23703 de `rotacion.py`). La desmentiría: que me digas que así lo querías.
2. **(Repetida, con fecha límite) Ampliar el cable de señales** (`rotacion.py` línea 3023, hoy 60 fechas): el 2-dic empezaría a borrar días maduros y el marcador se recalcula entero desde ese archivo. La desmentiría: que ese archivo no pierda fechas en diciembre. Si no se cambia, reconstruyo el cable desde git antes de cualquier cálculo largo.

## 7. Lo que necesito de Pe
- Contestar las dos preguntas de la propuesta 1 (cuando puedas; la (a) importa si la amplitud llega al 20 % esta semana).
- Decidir lo del cable antes del 2-dic.
- Subir tú el arreglo de `agente/preparar.py` (línea 206: `start=str(desde)` → `start=pd.Timestamp(desde).strftime("%Y-%m-%d")`) o decirme que no importa: sin él el marcador sale congelado cada mañana y lo reparo yo a mano.
- Nada más. No digo compra ni vende: la terminal marca las balas y tú decides.
