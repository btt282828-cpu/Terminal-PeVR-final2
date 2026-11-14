# Informe del compañero — 2026-11-13 (viernes, modo semanal)
## En una frase
La terminal funcionó y hoy no salta ninguna señal del plan (la única de la semana fue «se va el pánico», el lunes 9). El mercado rebotó en la semana pero lo viene soltando desde el miércoles. He encontrado y arreglado un fallo mío (el marcador llevaba días midiendo con precios parados en el 2-nov), he visto un fallo del registro de señales de la terminal que necesita tu decisión, y la idea de la semana (¿es «se va el pánico» mejor entrada que un viernes cualquiera?) ha salido que no. Hoy es viernes: el día en que tú decides.

## 1. ¿Funciona todo? (vigilante)
🟠 **Aviso «nuevo»: 21 series con el cierre rehecho con barras de 1 hora.** En el fondo no es nuevo: ya salió el 6-nov y el 10-nov (3 de las 14 noches guardadas, siempre con la terminal arrancando muy pronto, entre las 03:14 y las 03:41 de Madrid, cuando Yahoo aún no ha publicado la barra diaria de esas series). Efecto: diferencias de céntimos. He contrastado con Yahoo: SPY 754,37, QQQ 679,89, IWM 277,54 y RSP 221,16, idénticos a lo que guardó la terminal. (La línea del plan dice «hoy 754,34»: es un redondeo de mi script de lectura, 3 céntimos; no importa.)
Avisos viejos, sin cambios de fondo: ETF jóvenes DRAM y NCLD; volatilidad implícita descartada por poco creíble (ahora 4 ETF: ICLN, FAN, HYDR, UUP; antes 2); put/call fuera de banda en 17 ETF (antes 13); 7 acciones de SECTOR_STOCKS sin datos (CTRA, EA, GATO…; ayer 6); petróleo CL=F sin cierre válido en Yahoo (usa otra fuente). Nada que afecte al plan.

**Un fallo mío, ya arreglado: el marcador medía con precios parados en el 2-nov.** Mi script le pedía los precios a Yahoo con una fecha de inicio con hora («2026-08-03 00:00:00»); la versión actual de la librería (1.8) lo rechaza y devuelve una tabla vacía sin avisar, y el script caía al archivo de precios del repositorio, cuyo último dato es del 2-nov (y que no trae acciones sueltas como LRCX o AMAT). Por eso los informes del 6 al 12-nov decían «sin cambios» en el marcador: no era que no hubiera pasado nada, es que no se estaba midiendo. Arreglo (3 retoques en `agente/preparar.py`, reversibles con git): fecha sin hora; si Yahoo llega vacío ya no dice «yahoo»; y un aviso ámbar si los precios van más de 4 días por detrás de las señales. Hoy el marcador ya mide con precios hasta el 13-nov (sección 4). Mañana lunes compruebo que el arreglo sigue puesto.

**Dos fallos del registro de la terminal que he encontrado leyendo el código (no los he tocado):**
1. **El cable de señales solo guarda las últimas 60 sesiones** (`rotacion.py` línea 3023: `dates = sorted(...)[-60:]`). Hoy guarda 49 días; hacia el 2-dic empezará a borrar los más viejos, y el marcador (que se recalcula entero cada día desde ese archivo) perderá con ellos las señales que ya maduraron. Con 60 sesiones solo caben unas 39 sesiones de señales ya medibles a 20 sesiones: las señales que salen menos de ~0,8 veces al día (casi todas menos GIRO) no podrán llegar nunca a 30 casos. Eso choca con querer «3-6 meses de datos nuevos». (Los días borrados siguen en el histórico de git: no se pierden para siempre.)
2. **El 9-nov se guardó con fecha 10-nov.** El build de ese día guardó sus 21 señales del cable con la etiqueta «2026-11-10»; la noche siguiente el build del día 10 escribió su propio «2026-11-10» encima y el 9-nov desapareció: hoy el cable no tiene ninguna señal del 9-nov, el día de «se va el pánico». Causa probable: la fecha de reserva `df.index[-1]` (`rotacion.py` línea 16176) — es una hipótesis, no la he podido comprobar. El centinela también salió con fecha adelantada en los builds de los días 10 y 11-nov. El plan no se ve afectado (sale del semáforo, que tenía la fecha buena). Los datos del 9-nov siguen en git (commit 6fc45ab, filas del «10-nov»).

## 2. Señales del plan (lo que ha cambiado)
Ninguna ha saltado hoy.
1. **Se va el pánico:** saltó el 9-nov. Hoy VIX/VIX3M 0,94, sin pánico vivo. Sin cambios.
2. **SPY −10 %:** línea en 703,46; hoy 754,37; falta −6,7 %. SPY a −3,5 % de su máximo (ayer −3,1 %).
3. **QQQ −20 %:** línea en 610,29; hoy 679,89; falta −10,2 %. QQQ a −10,9 % (ayer −9,8 %). Rendición total: NO (2,4 % de 20 en mínimos; 1 de 6 sectores sacando dinero; VIX/VIX3M 0,94 de 1,10).
4. **Bajista:** SPY −20 % (625,30) falta −17,1 %; QQQ −30 % (534,00) falta −21,5 %. Lejos.
5. **Control del mes:** 7-dic, faltan 15 sesiones. SPY a un 1,6 % por encima de la línea de 742,54 (ayer 2,0 %, el miércoles 2,3 %): sigue del lado «corrección normal» (9 % sigue a −10 %), pero el colchón se estrecha.

## 3. Qué dice hoy la terminal
VIX 19,3 (ayer 18,7). Dinero MIXTO (entran 3 sectores, sale 1; ayer 2 y 0; sin EMPUJE ni VENTA EXTREMA). Centinela ACECHO. Sin pánico agudo. Notas de los índices: SPY FLOJA (4), QQQ BAJA (2, ayer 3), DIA MEDIA (7), IWM MEDIA (6, ayer FLOJA 5), RSP ALTA (10, el máximo), MAGS FLOJA (5).
Lo que se puede pasar por alto:
- **El QQQ está pegado a su línea de −10 %:** desde el 2-nov la ha cruzado 4 veces en 10 sesiones (hoy otra vez por debajo, −10,9 %). El semáforo solo marcó el primer toque (2-nov, a 681,09; hoy cierra a 679,89), así que no avisa de nuevo. No es señal del plan (la tuya es el −20 %). Ya estudiado el 7-nov: esperar «un mes» antes de comprar el −10 % del QQQ no mejora.
- **La caída es de la tecnología grande, no del mercado entero:** RSP (S&P a partes iguales) saca la nota máxima, 10 de 10, y está a solo −1,4 % de su máximo, mientras el QQQ saca 2 y está a −10,9 %. Lo ya estudiado: repartir entre índices ayudó cuando la caída la lideró un sector (2000, 2022) y no en una crisis de todo el sistema (2008: todos −52/−59 %). Hoy el mercado amplio no muestra crisis general (2,4 % de acciones en mínimos).
- **Desde el día de «se va el pánico» (lunes 9) el mercado está de lado:** SPY +0,2 %, QQQ +0,1 %, RSP +0,1 %, IWM −1,8 %. El rebote del miércoles (SPY 759,81) se ha ido soltando dos sesiones seguidas.

## 4. Marcador (qué señales van funcionando con datos nuevos)
**Ojo: las cifras de los informes del 6 al 12-nov estaban congeladas en el 2-nov (ver sección 1); no se pueden comparar con las de hoy.** Con precios al día (hasta el 13-nov), todo sigue «orientativo» salvo que GIRO↑ llega a 30 casos a 20 sesiones:
- **GIRO↑:** acierta 30 % (n 30, IC 17–48 %), exceso −5,1 puntos frente al SPY (t −2,2): el script lo etiqueta «VA AL REVÉS». **GIRO↓:** 73 % (n 26, IC 54–86 %), exceso +7,4 (t 3,2).
- **Control de azar (nuevo, `agente/estudios/control_azar_marcador.py`):** a cada episodio le resto lo que ese mismo activo hacía frente al SPY en esas mismas fechas, con o sin señal. Resultado: GIRO↑ queda en −0,4 puntos (t −0,2) y GIRO↓ en +1,0 (t 0,4). Es decir, GIRO↑ y GIRO↓ marcan casi los mismos activos (semis como LRCX, AMAT, SNDK, plata, temáticos) que simplemente rindieron unos 5-6 puntos peor que el SPY en este periodo: lo que parecía «la señal funciona» y «la señal va al revés» es el comportamiento del activo, no de la señal. Con el mercado cayendo y tecnología llevando la caída, es lo esperable.
- Las demás, con ese control: 0/3, CAPITUL, CLÍMAX, FLOW, GRADUADO, NOCTURNO, SUELO sin nada (|t| < 1,6). **EARLY** es la única con algo: +4,2 puntos netos (t 2,3, n 13). Con 10 señales mirándose a la vez, una así sale por azar con facilidad; no la tomo en serio.
- Las que antes parecían buenas se desinflan al sumar casos: CLÍMAX pasa de 77 % (n 13) a 59 % (n 22, IC 39–77 %); GIRO↓ de 79 % (n 14) a 73 % (n 26). FLOW sigue en 76 % (n 17, IC 53–90 %, exceso +2,2, t 1,6, neto +0,8).
- I-001 (GIRO) se revisa cuando GIRO↓ también llegue a 30 casos (le faltan 4; hay 22 en espera). Adelanto: el control de azar ya dice que no hay señal por encima del activo.
El cable de hoy repite las mismas señales alcistas de ayer (GRADUADO en IWM/ITA/ITB/XLI; 0/3 y SUELO en FXI/JETS): cuentan como un solo episodio. DRAM sale a la vez con CLÍMAX↓ (bajista) y EARLY↑ (alcista): ETF de 33 semanas de vida, sin valor.
Cesta semanal: 11 semanas, −0,65 % de media frente a SPY −0,27 %; mejor que el SPY 4 de 11 (IC 15–65 %). Esta semana la cesta (4 ETF) hizo −1,0 % frente a +2,6 % del SPY: un mal resultado, anotado con sus fallos.

## 5. Investigación (viernes)
**I-004 · ¿«Se va el pánico» es mejor entrada que un viernes cualquiera de una caída parecida? → TUMBADA** (ideas probadas: 2; ambas descartadas).
- **Qué hice:** tomé cada vez que el VIX/VIX3M volvió por debajo de 1,0 tras haber estado en 1,0 o más, con el SPY al menos un 3 % bajo su máximo: 36 episodios entre 2009 y 2022 (el VIX a 3 meses solo existe desde sept-2009). Como tú actúas los viernes, entré el primer viernes después y miré el SPY (con dividendos) a 20, 60 y 120 sesiones. Lo comparé, episodio a episodio, con los viernes de una caída parecida (±2,5 puntos) sin pánico: el azar justo. La caja cerrada (2023 en adelante) no se ha abierto. Variantes probadas: 5, las apuntadas antes.
- **Resultado principal (60 sesiones):** los episodios ganaron de media +3,6 % y los viernes parecidos +5,2 %: exceso −1,5 puntos (t = −1,2). Por trozos: hasta 2018 (25 episodios) −2,7 puntos, t −2,4; 2019-2022 (11 episodios) +1,2 puntos, t 0,35. Mejoraron al azar justo 15 de 36 (42 %, intervalo 27–58 %). A 20 y 120 sesiones, plano (+0,5 y −0,5 puntos). Tras entrar, el SPY aún cayó de media un 4,3 % más (en el azar justo, 3,1 %); el peor caso, −14,7 % (oct-dic 2018).
- **Conclusión:** no hay ventaja demostrada en esperar a que se vaya el pánico. Mi criterio («+1 punto en los dos trozos») no se cumple y en el primer trozo sale incluso negativo. La pista «se va el pánico = mejor momento» no se sostiene frente a un viernes cualquiera de una caída parecida. Lo que NO he probado: si es mejor que comprar con el pánico todavía vivo (queda apuntado como I-005 para el viernes 20).
- **Con la regla exacta del detector** (VIX/VIX3M ≥ 1,10 antes de irse) solo hay 9 episodios hasta 2022: no se puede concluir nada, pero sí ver qué pasó. «Se va el pánico» no ha sido el suelo: en 4 de 9 casos (44 %, IC 19–73 %) el SPY aún cayó un 5 % o más en los 60 días siguientes. Frecuencia histórica, no predicción.

| Se fue el pánico | Entrada (viernes) | SPY bajo su máximo ese viernes | SPY a 20 / 60 / 120 ses. | Peor caída en esos 60 días |
|---|---|---|---|---|
| 10-may-2010 | 14-may-2010 | −6,7 % | −3,8 / −0,9 / +6,4 % | −9,8 % |
| 31-ago-2011 | 2-sep-2011 | −13,7 % | −6,2 / +2,4 / +17,7 % | −6,2 % |
| 20-oct-2014 | 24-oct-2014 | −2,7 % | +5,2 / +5,5 / +7,9 % | −0,1 % |
| 2-sep-2015 | 4-sep-2015 | −9,7 % | +3,6 / +10,0 / +1,6 % | −1,9 % |
| 14-feb-2018 | 16-feb-2018 | −4,7 % | −0,6 / −0,3 / +5,3 % | −5,3 % |
| 16-oct-2018 | 19-oct-2018 | −5,8 % | −0,9 / −4,2 / +6,1 % | −14,7 % |
| 4-ene-2019 | 4-ene-2019 | −13,4 % | +7,8 / +13,8 / +16,6 % | ninguna |
| 7-ago-2019 | 9-ago-2019 | −3,5 % | +2,3 / +5,9 / +11,4 % | −2,6 % |
| 24-abr-2020 | 24-abr-2020 | −16,0 % | +4,4 / +15,4 / +24,0 % | −0,5 % |

Límites: solo desde 2009 (sin 2000-02 ni 2008); 2018 y 2020 pesan mucho; no se mira cuánto se invierte ni en qué ETF. Guardado en `agente/estudios/i004.py` y `i004.md`.

## 6. Propuestas para Pe
1. **Arreglar el registro del cable (dos líneas de `rotacion.py`).** Qué: en la línea 3023 cambiar el tope de 60 días por uno muy grande (el archivo crece unas 25 filas al día: sin problema), y en la línea 16176 usar la sesión esperada (`sesion_esperada()`) en vez de `df.index[-1]` como fecha de reserva. Por qué: sin esto el marcador nunca podrá acumular 3-6 meses y el 9-nov ya se perdió. Qué la desmentiría: que el tope de 60 sea a propósito (por ejemplo para aligerar la web) o que prefieras medir siempre sobre una ventana móvil de 60 sesiones.

## 7. Lo que necesito de Pe
- Decidir si se toca esa línea (yo no puedo cambiar `rotacion.py`). Si prefieres que no se toque, avísame y reconstruyo el cable completo desde git cada viernes.
- Avisarme si NO quieres que yo toque `agente/preparar.py` (lo he hecho hoy para arreglar los precios del marcador; se revierte con `git checkout`).
- Pendientes tuyos de antes: activar o no el Telegram de la terminal; especificar I-003 (semis); decir si lo de ACECHO vs DISTRIBUCIÓN ya no aplica tras la v8.5.

## Semana (6-nov → 13-nov)
- SPY 735,29 → 754,37 (+2,6 %); QQQ +3,6 %; RSP +2,4 %; IWM +1,4 %; VIX 25,6 → 19,3; VIX/VIX3M 1,04 → 0,94.
- Señal del plan de la semana: solo «se va el pánico» (lunes 9). Ninguna otra. El control del mes sigue fijado para el 7-dic.
- Marcador: arreglado (medía con precios del 2-nov). Con precios al día, GIRO↑ llega a 30 casos y «va al revés», pero con el control de azar no queda nada. Cesta: −1,0 % frente a SPY +2,6 %.
- Investigación: I-004 tumbada; I-005 apuntada para el viernes 20.
- Pendientes para decidir este viernes: la propuesta 1 (arreglo del registro del cable).
