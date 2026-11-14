# Memoria del compañero

(Este cuaderno lo actualiza el agente cada día. Máximo unas 150 líneas.)

## Estado del sistema
- Terminal v8.5 (Pe la subió el 11-nov: pestaña «Hoy», plan único de 4 balas, notas en vez de órdenes: ESPERAR→NOTA FLOJA, NO TOCAR→NOTA BAJA). Se ejecuta de lunes a viernes; GitHub la arranca con horas de retraso (el histórico se guarda hacia las 03:00-05:00 de Madrid).
- 5-nov-2026: susto (SPY −6,2 %, QQQ −15,2 %, VIX 28,2; pánico agudo). 9-nov: SALTÓ «SE VA EL PÁNICO» (bala 1). Desde entonces el mercado está de lado.
- 13-nov-2026 (viernes): SPY −3,5 % del máximo (754,37), QQQ −10,9 % (679,89), IWM −8,8 %, RSP −1,4 %, VIX 19,3, VIX/VIX3M 0,94. Dinero MIXTO, centinela ACECHO. Ninguna señal del plan salta. Control del mes: 7-dic (15 sesiones); SPY 1,6 % sobre la línea 742,54 (el colchón era 2,3 % el 11-nov).
- Semana 6→13-nov: SPY +2,6 %, QQQ +3,6 %. Cesta semanal: −1,0 % frente a SPY +2,6 % (11 semanas: −0,65 % vs −0,27 %, mejor 4 de 11).
- El QQQ ya tocó su −10 % el 2-nov (semáforo, a 681,09, «tramo completo»); desde entonces cruza esa línea arriba y abajo (4 cruces en 10 sesiones). El semáforo no re-avisa.
- Marcador CON PRECIOS AL DÍA (13-nov; n a 20 ses.): GIRO↑ 30 (30 %), GIRO↓ 26 (73 %), CLÍMAX 22 (59 %), GRADUADO 18, FLOW 17 (76 %), CAPITUL 16, 0/3 14, EARLY 13, NOCTURNO 11, SUELO 10. Control de azar (mismo activo, mismas fechas): nada sobrevive salvo EARLY (+4,2 netos, t 2,3, n 13: azar probable entre 10 señales).

## Problemas abiertos
- (13-nov) **ARREGLADO por mí, verificar el lunes 16-nov:** el marcador medía con precios parados en el 2-nov. Causa: `agente/preparar.py` pasaba `start=str(Timestamp)` («2026-08-03 00:00:00») a `yf.download`; yfinance 1.8 falla en silencio (0 filas) y el script caía al archivo `universo_close.csv.gz` del repo (último dato 3-nov, sin acciones sueltas). Por eso los informes del 6 al 12-nov decían «sin cambios». Arreglo: fecha sin hora, `fuente` honesta y aviso ámbar si los precios van >4 días atrás. Comprobar el lunes con `grep -n strftime agente/preparar.py` y que `marcador.json` traiga `ultimo_precio` = fecha reciente; si la máquina deshizo el cambio, decírselo a Pe. NO comparar cifras del marcador anteriores al 13-nov con las nuevas.
- (13-nov) **El cable `senales_wire.json` solo guarda las últimas 60 FECHAS** (`rotacion.py` línea 3023). Hoy 49; hacia el 2-dic empezará a borrar días viejos y el marcador (se recalcula entero desde ese archivo) perderá episodios ya maduros. Propuesto a Pe (informe 13-nov). Si Pe no lo cambia: reconstruir el cable completo desde git antes de cualquier cálculo largo (unir las versiones de `senales_wire.json` de los commits «historico …» por (fecha, etiqueta, activo, dirección)).
- (13-nov) **El 9-nov quedó guardado como «2026-11-10»** en el cable y se perdió al sobrescribirlo el build del día 10 (fallback `df.index[-1]`, `rotacion.py` 16176: hipótesis). Las filas siguen en el commit 6fc45ab (etiqueta 10-nov = día 9-nov real). El centinela también salió con fecha adelantada en los builds de 10 y 11-nov. El cable NUNCA ha guardado «se va el pánico» (solo el PÁNICO agudo del 5-nov): el marcador no mide la bala 1.
- (13-nov) Aviso «21 series con cierre rehecho con barras de 1 hora»: sale cuando la terminal arranca muy pronto (6-nov, 10-nov, 13-nov, entre 03:14 y 03:41 de Madrid). Inocuo (céntimos): SPY/QQQ/IWM/RSP guardados = Yahoo. Los precios «hoy» del plan en `lectura.json` salen de un redondeo (pico×(1+dd)): 3 céntimos de diferencia, sin importancia.
- (13-nov) Opciones: IV descartada en 4 ETF (ICLN, FAN, HYDR, UUP), put/call fuera de banda en 17 ETF; SECTOR_STOCKS sin datos: 7 (CTRA, EA, GATO…; oscila entre 6 y 7); petróleo CL=F sin cierre válido en Yahoo (usa otra fuente). El archivo `historiales/universo_close.csv.gz` está parado desde el 3-nov (el vigilante lo muestra como «universo 10 días»).
- (6-nov) Telegram de la terminal sin activar (decisión de Pe, pendiente). Cuando lo active, además de los secretos hace falta pasar TELEGRAM_TOKEN y TELEGRAM_CHAT_ID en el `env:` del paso "Ejecutar el terminal" de build.yml.
- (30-oct) Incoherencia ACECHO vs DISTRIBUCIÓN en `_op_veredicto`: la v8.5 quitó las órdenes; preguntar a Pe si ya no aplica.

## Trabajo a medias
- I-002 (6-nov) y I-004 (13-nov) probadas y DESCARTADAS. I-004: esperar a que «se vaya el pánico» no mejora la entrada frente a viernes parecidos (36 episodios 2009-22: −1,5 pts a 60 ses., t −1,2); con la regla exacta solo 9 episodios hasta 2022 (en 4 el SPY aún cayó ≥5 % más). Caja 2023+ SIN abrir (no se abre: no pasó).
- Siguiente: **I-005** (viernes 20-nov): «se va el pánico» frente a comprar con el pánico aún vivo (viernes con VIX/VIX3M ≥ 1,0). Ya apuntada en ideas.md.
- I-001 (GIRO): se cierra cuando GIRO↓ llegue a 30 casos (hoy 26 + 22 en espera); el control de azar (`estudios/control_azar_marcador.py`) ya dice que no hay señal por encima del activo.
- I-003 (semis) sigue en cola: espera la especificación de Pe.
- Contador de ideas probadas: 2.

## Qué ha decidido Pe
- Quiere el informe todos los días, al terminar la terminal.
- Usa su suscripción Pro (secreto CLAUDE_CODE_OAUTH_TOKEN), no API de pago. Repaso corto de lunes a jueves; investigación solo los viernes, para no gastar su cupo semanal.
- No quiere de momento el agente auditor aparte (gasta muchos tokens).
- Subió la v8.5 el 11-nov. Pendiente de respuesta: la propuesta del 13-nov (arreglar el tope de 60 días del cable y la fecha de reserva) y si acepta que yo toque `agente/preparar.py`.
