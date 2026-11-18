# Informe del compañero — 2026-11-17 (martes, modo diario)
## En una frase
El mercado ha seguido cayendo (SPY −1,0 % en el día, ya −6,3 % de su máximo; QQQ −13,9 %; VIX 25,5) y el centinela ha pasado de ACECHO a **LIQUIDEZ**, pero no salta ninguna señal del plan. Además, mi arreglo del marcador ha vuelto a desaparecer: es la máquina quien lo borra.

## 1. ¿Funciona todo? (vigilante)
La terminal salió bien (🟢): todo grabado y sin avisos nuevos. Siguen los avisos de siempre (opciones: IV de FAN descartada, put/call raro en 14 ETF, 6 acciones sin datos, petróleo CL=F sin cierre válido, pesos del QQQ de Invesco con error 406 → se usan los del 12-nov, `universo_close` parado desde el 3-nov). Nada que cambie nada para ti.

**Mi arreglo del marcador, perdido otra vez.** El marcador pedía precios a Yahoo con una fecha con hora y se quedaba con precios viejos (esta mañana: GIRO↑ con 10 casos en vez de 30). El lunes lo arreglé; hoy el archivo `agente/preparar.py` estaba otra vez como antes. Ya sé por qué: el flujo (`agente.yml`, línea 224) **restaura `preparar.py` desde una copia fija antes de guardar**, así que cualquier cambio mío se deshace por diseño. Hoy lo he vuelto a parchear solo para esta mañana y he regenerado el resumen (precios de Yahoo al 17-nov), pero mañana volverá a salir congelado. Solución real (la tienes que hacer tú o dejármela hacer): cambiar en `agente/preparar.py`, línea 206, `start=str(desde)` por `start=pd.Timestamp(desde).strftime("%Y-%m-%d")` y subirlo tú.

## 2. Señales del plan (lo que ha cambiado)
Ninguna ha saltado hoy.
1. **Se va el pánico:** saltó el 9-nov. Hoy VIX/VIX3M 1,02 (ayer 0,995): sube, pero el «pánico vivo» exige ≥ 1,10; no hay pánico nuevo ni agudo.
2. **SPY −10 %:** línea 703,46; hoy 732,46; falta −4,0 % (ayer −4,9 %). SPY a −6,3 % del máximo (ayer −5,3 %).
3. **QQQ −20 %:** línea 610,29; hoy 656,98; falta −7,1 % (ayer −7,8 %). QQQ a −13,9 %. Rendición total: NO (6,5 % de 20 acciones del S&P en mínimos; 2 de 6 sectores sacando dinero; VIX/VIX3M 1,02 de 1,10). Se acerca, pero falta mucho en las tres condiciones.
4. **Bajista:** SPY −20 % (625,30) falta −14,6 %; QQQ −30 % (534,00) falta −18,7 %.
5. **Control del mes:** 7-dic, faltan 13 sesiones. SPY cierra en 732,46, un 1,4 % por debajo de la línea 742,54 (ayer 0,3 % por debajo). Si el 7-dic siguiera entre −5 y −10 %, el histórico 1927-2026 da −10 % después el 57 % de las veces (N = 122 caídas de ese tipo; frecuencia histórica, no predicción). Hoy solo es una foto.

## 3. Qué dice hoy la terminal
VIX 25,5 (ayer 22,9). Dinero MIXTO (entra 1 sector, salen 2); sin EMPUJE ni VENTA EXTREMA. Notas: SPY BAJA (3), QQQ BAJA (2), DIA FLOJA (4), IWM BAJA (2), **RSP MEDIA (6; ayer ALTA 8)**, MAGS BAJA (3). Caídas desde máximo: IWM −11,6 %, MAGS −11,2 %, DIA −6,9 %, RSP −3,8 %.
Cosas que se pueden pasar por alto (dos):
- **El centinela pasó de ACECHO a LIQUIDEZ** (el estado más defensivo del ciclo; en el código, línea ~10804 de `rotacion.py`). Ayer te decía que el mercado amplio aún aguantaba; hoy lo amplio también se debilita (RSP de ALTA a MEDIA, de −2,4 % a −3,8 %). Por la jerarquía del sistema, el centinela pesa más que cualquier otro panel. Ojo a la fecha: el centinela guarda este estado con fecha 18-nov (sale con un día de adelanto, el fallo de fechas que ya conocíamos); el estado es el del cierre del 17.
- **Sigue sin ser un pánico de verdad:** VIX/VIX3M 1,02. El 5-nov, con el mismo SPY a −6,2 %, sí hubo pánico agudo. Hoy cae más despacio y con el miedo contenido; no sé qué hará mañana. Sin tendencia al pánico no hay «rendición» (condición del bala 3).
Pequeña rareza que sigo sin comprobar: el PLAN SPY usa como máximo 779,09 y el detector 781,6 (por eso −5,x % en uno y −6,3 % en otro; parece máximo de cierre frente a intradía).

## 4. Marcador (con precios al día; todo orientativo)
- **GIRO↑** 30 casos: acierto 30 % (IC 17–48 %), exceso −5,1 puntos frente al SPY (t −2,2). **GIRO↓** 29 casos: 72 % (IC 54–85 %), exceso +7,5 (t 3,5). Pero con el **control de azar** (mismo activo, mismas fechas; `estudios/control_azar_marcador.py`): GIRO↑ −0,1 pts (t −0,05) y GIRO↓ +0,5 (t 0,2). Es decir, **no hay señal por encima de lo que ya hacía el activo** (semis y plata, que rindieron peor/mejor que el SPY).
- Resto del control de azar (n 11-23): 0/3 +1,1, CAPITUL +0,7, CLÍMAX −0,8, FLOW +1,2, GRADUADO +1,9, NOCTURNO +0,5; todos |t| < 1,3: nada. **SUELO +4,6 (t 2,5, n 13) y EARLY +4,2 (t 2,2, n 13)**: con 10 señales mirándose a la vez, dos así salen por azar; no se toman en serio.
- Cesta semanal sin semana nueva hasta el viernes (11 semanas: −0,65 % de media frente al SPY −0,27 %; mejor 4 de 11).
- Cable de hoy: RÉGIMEN SPY↓, CAPITUL (REMX, TAN, IBIT), GRADUADO (KRE, DRAM, IWM, ITA), GIRO↓ (STX, LRCX, KLAC), 0/3 y SUELO FXI↑, SUELO URA↑, EARLY (DRAM, HYDR, NCLD), SENT SPY↑. Casi todas son alcistas tras una caída: con el mercado cayendo, lo que hagan dependerá del mercado.

## 5. Investigación (solo viernes)
Hoy no se investiga. El viernes 20-nov toca I-005 («se va el pánico» frente a comprar con el pánico aún vivo).

## 6. Propuestas para Pe
1. **Arreglar `agente/preparar.py` tú mismo** (línea 206, ver arriba), porque yo no puedo hacer que persista. Qué la desmentiría: que el marcador de mañana ya salga con GIRO↑ en 30 casos sin tocar nada.
2. **(Repetida, pendiente)** El cable de señales solo guarda 60 sesiones (`rotacion.py` línea 3023); hacia el 2-dic empezará a borrar días maduros. Si no lo cambias, reconstruyo el cable desde git antes de cualquier cálculo.

## 7. Lo que necesito de Pe
- Subir el arreglo de `preparar.py` (o decirme que no te importa el marcador congelado cada mañana).
- Decidir lo del cable de 60 sesiones antes del 2-dic.
