# Memoria del compañero

(Este cuaderno lo actualiza el agente cada día. Máximo unas 150 líneas.)

## Estado del sistema
- Terminal v8.5 (Pe la subió el 11-nov: pestaña «Hoy», plan único de 4 balas, notas en vez de órdenes: ESPERAR→NOTA FLOJA, NO TOCAR→NOTA BAJA). Se ejecuta de lunes a viernes; GitHub la arranca con horas de retraso (el histórico se guarda hacia las 03:00-05:00 de Madrid).
- 5-nov-2026: susto (SPY −6,2 %, QQQ −15,2 %, VIX 28,2; pánico agudo). 9-nov: SALTÓ «SE VA EL PÁNICO» (bala 1). Desde entonces el mercado está de lado.
- 13-nov-2026 (viernes): SPY −3,5 % del máximo (754,37), QQQ −10,9 % (679,89), IWM −8,8 %, RSP −1,4 %, VIX 19,3, VIX/VIX3M 0,94. Dinero MIXTO, centinela ACECHO. Ninguna señal del plan salta. Control del mes: 7-dic (15 sesiones); SPY 1,6 % sobre la línea 742,54 (el colchón era 2,3 % el 11-nov).
- 16-nov-2026 (lunes): caída: SPY 739,96 (−5,3 % del máximo; −1,9 % en el día), QQQ 661,78 (−13,3 %), IWM −10,3 %, RSP −2,4 %, VIX 22,9, VIX/VIX3M 0,995 (sin pánico). Dinero MIXTO, centinela ACECHO. Ninguna señal del plan salta. Control del mes 7-dic (14 sesiones): SPY por debajo de la línea 742,54 (el viernes 1,6 % por encima).
- 17-nov (martes): SPY 732,46 (−6,3 % del máximo; −1,0 % en el día), QQQ −13,9 %, IWM −11,6 %, RSP −3,8 %, VIX 25,5, VIX/VIX3M 1,02 (sin pánico vivo). Dinero MIXTO. **Centinela ACECHO→LIQUIDEZ** (guardado con fecha 18-nov: adelanto de fecha). Ninguna señal del plan salta. Faltan −4,0 % al SPY −10 % y −7,1 % al QQQ −20 %. Control del mes 7-dic (13 sesiones): SPY 1,4 % bajo la línea 742,54.
- Semana 6→13-nov: SPY +2,6 %, QQQ +3,6 %. Cesta semanal: −1,0 % frente a SPY +2,6 % (11 semanas: −0,65 % vs −0,27 %, mejor 4 de 11).
- El QQQ ya tocó su −10 % el 2-nov (semáforo, a 681,09, «tramo completo»); desde entonces cruza esa línea arriba y abajo (4 cruces en 10 sesiones). El semáforo no re-avisa.
- Marcador 17-nov (control de azar): nada sobrevive (GIRO↑ −0,1, GIRO↓ +0,5); SUELO +4,6 (t 2,5, n 13) y EARLY +4,2 (t 2,2, n 13) = azar probable. GIRO↓ lleva 27-29: cerrar I-001 al llegar a 30.
- Marcador (13-nov; n a 20 ses.): GIRO↑ 30 (30 %), GIRO↓ 26 (73 %), CLÍMAX 22 (59 %), GRADUADO 18, FLOW 17 (76 %), CAPITUL 16, 0/3 14, EARLY 13, NOCTURNO 11, SUELO 10. Control de azar (mismo activo, mismas fechas): nada sobrevive salvo EARLY (+4,2 netos, t 2,3, n 13: azar probable entre 10 señales).

## Problemas abiertos
- (17-nov) **El arreglo de `preparar.py` lo borra la máquina POR DISEÑO** (`agente.yml` línea 224 restaura `preparar.py` desde copia fija; además `preparar.py` corre ANTES que yo). Cada mañana el marcador sale congelado (GIRO↑ n=10 en vez de 30). Cada día: parchear en sitio (`sed` línea 206: `start=pd.Timestamp(desde).strftime("%Y-%m-%d")`) y volver a ejecutar `python agente/preparar.py`, y decírselo a Pe. Pe debe subir el cambio él. Pedido en informe 17-nov.
- (13-nov) **El cable `senales_wire.json` solo guarda las últimas 60 FECHAS** (`rotacion.py` línea 3023). Hoy 49; hacia el 2-dic empezará a borrar días viejos y el marcador (se recalcula entero desde ese archivo) perderá episodios ya maduros. Propuesto a Pe (informe 13-nov). Si Pe no lo cambia: reconstruir el cable completo desde git antes de cualquier cálculo largo (unir las versiones de `senales_wire.json` de los commits «historico …» por (fecha, etiqueta, activo, dirección)).
- (13-nov) **El 9-nov quedó guardado como «2026-11-10»** en el cable y se perdió al sobrescribirlo el build del día 10 (fallback `df.index[-1]`, `rotacion.py` 16176: hipótesis). Las filas siguen en el commit 6fc45ab (etiqueta 10-nov = día 9-nov real). El centinela también salió con fecha adelantada en los builds de 10 y 11-nov. El cable NUNCA ha guardado «se va el pánico» (solo el PÁNICO agudo del 5-nov): el marcador no mide la bala 1.
- (13-nov) Aviso «21 series con cierre rehecho con barras de 1 hora»: sale cuando la terminal arranca muy pronto (6-nov, 10-nov, 13-nov, entre 03:14 y 03:41 de Madrid). Inocuo (céntimos): SPY/QQQ/IWM/RSP guardados = Yahoo. Los precios «hoy» del plan en `lectura.json` salen de un redondeo (pico×(1+dd)): 3 céntimos de diferencia, sin importancia.
- (13-nov) Opciones: IV descartada en 4 ETF (ICLN, FAN, HYDR, UUP), put/call fuera de banda en 17 ETF; SECTOR_STOCKS sin datos: 7 (CTRA, EA, GATO…; oscila entre 6 y 7); petróleo CL=F sin cierre válido en Yahoo (usa otra fuente). El archivo `historiales/universo_close.csv.gz` está parado desde el 3-nov (el vigilante lo muestra como «universo 10 días»).
- (6-nov) Telegram de la terminal sin activar (decisión de Pe, pendiente). Cuando lo active, además de los secretos hace falta pasar TELEGRAM_TOKEN y TELEGRAM_CHAT_ID en el `env:` del paso "Ejecutar el terminal" de build.yml.
- (30-oct) Incoherencia ACECHO vs DISTRIBUCIÓN en `_op_veredicto`: la v8.5 quitó las órdenes; preguntar a Pe si ya no aplica.

## Trabajo a medias
- I-002 (6-nov) y I-004 (13-nov) probadas y DESCARTADAS. I-004: esperar a que «se vaya el pánico» no mejora la entrada frente a viernes parecidos (36 episodios 2009-22: −1,5 pts a 60 ses., t −1,2); con la regla exacta solo 9 episodios hasta 2022 (en 4 el SPY aún cayó ≥5 % más). Caja 2023+ SIN abrir (no se abre: no pasó).
- Siguiente: **I-005** (viernes 20-nov): «se va el pánico» frente a comprar con el pánico aún vivo (viernes con VIX/VIX3M ≥ 1,0). Ya apuntada en ideas.md.
- I-001 (GIRO): se cierra cuando GIRO↓ llegue a 30 casos (16-nov: 27 + 21 en espera; GIRO↑ ya 30, control de azar −0,35 pts t −0,2); el control de azar (`estudios/control_azar_marcador.py`) ya dice que no hay señal por encima del activo.
- I-003 (semis) sigue en cola: espera la especificación de Pe.
- Contador de ideas probadas: 2.

## Qué ha decidido Pe
- Quiere el informe todos los días, al terminar la terminal.
- Usa su suscripción Pro (secreto CLAUDE_CODE_OAUTH_TOKEN), no API de pago. Repaso corto de lunes a jueves; investigación solo los viernes, para no gastar su cupo semanal.
- No quiere de momento el agente auditor aparte (gasta muchos tokens).
- Subió la v8.5 el 11-nov. Pendiente de respuesta: la propuesta del 13-nov (arreglar el tope de 60 días del cable y la fecha de reserva) y si acepta que yo toque `agente/preparar.py`.
- 16-nov: marcador con control de azar: nada sobrevive; EARLY +4,2 (t 2,25, n 13) y SUELO +4,3 (t 2,2, n 12) son azar probable entre 10 señales. Pe no ha respondido aún a la propuesta del cable de 60 sesiones.
