# Informe del compañero — 2026-11-19 (jueves, modo diario)
## En una frase
Día de caída fuerte: el SPY pierde otro 2 % (−8,4 % desde su máximo, a −1,7 % de la línea del −10 %), el VIX sube a 28,4 y los 6 sectores sacan dinero. Ninguna señal del plan ha saltado todavía, pero la del SPY −10 % está ya muy cerca.

## 1. ¿Funciona todo? (vigilante)
🟠 Un aviso nuevo y sin importancia: el cierre de SDOG del 19-nov se rehízo con barras de 1 hora porque Yahoo aún no daba la barra diaria (céntimos de diferencia; no afecta a SPY/QQQ/IWM/RSP). Lo demás sigue igual que otros días (opciones, acciones sin datos, `universo_close` parado desde el 3-nov): sin consecuencias.

**Marcador congelado, 4.º día.** La máquina volvió a dejar `agente/preparar.py` sin mi arreglo (lo restaura por diseño). Lo parcheé en sitio y regeneré el resumen: con el arreglo GIRO↑ sale con 32 casos; sin él, con 10. Solución real: que lo subas tú (propuesta 1).

**Cable de señales:** unas 53 fechas de 60 posibles; hacia el 2-dic empezará a borrar días viejos.

## 2. Señales del plan (lo que ha cambiado)
Ninguna ha saltado hoy.
1. **Se va el pánico:** saltó el 9-nov. Hoy no hay pánico vivo: VIX/VIX3M 1,052 (ayer 1,01), por debajo de 1,10; VIX 28,4 (ayer 24,6). Se acerca, pero no ha vuelto.
2. **SPY −10 %:** línea 703,46; hoy 715,89; falta −1,7 % (ayer −3,7 %). Es la más cercana y se ha acercado dos puntos en un día.
3. **QQQ −20 %:** línea 610,29; hoy 645,07; falta −5,4 % (ayer −7,5 %). QQQ a −15,4 %. Rendición total: NO (9,2 % de 20 acciones del S&P en mínimos; 6 de 6 sectores sacando dinero; VIX/VIX3M 1,05 de 1,10). Ya cumple una de las tres condiciones (sectores); le faltan las otras dos.
4. **Bajista:** SPY −20 % (625,30) falta −12,7 %; QQQ −30 % (534,00) falta −17,2 %.
5. **Control del mes:** 7-dic, faltan 11 sesiones. SPY 715,89, un 3,6 % bajo la línea 742,54 (ayer 1,7 %). Si el 7-dic siguiera entre −5 y −10 %, el histórico 1927-2026 da −10 % después el 57 % de las veces (N = 122 caídas; frecuencia histórica, no predicción).

## 3. Qué dice hoy la terminal
Detector de caídas: SPY −8,4 %, DIA −9,9 %, QQQ −15,4 %, IWM −13,2 %, MAGS −13,0 %, RSP −5,6 %. Dinero: **SALE DE TODO** (0 sectores entran, 6 salen), sin EMPUJE ni VENTA EXTREMA. Notas: todas BAJA salvo RSP FLOJA (5). Centinela LIQUIDEZ (el más defensivo; por la jerarquía del sistema manda sobre cualquier otro panel).
Cosas que se pueden pasar por alto:
- **El RSP (el S&P con todas las acciones por igual) tocó hoy su −5 %** en el semáforo (avisa «un cuarto, ¼R»; no es pánico agudo). Es la primera vez en este episodio: la caída ya no es solo de los grandes (el 13-nov el RSP estaba a −1,4 %, hoy a −5,6 %). Y el DIA está a −9,9 %: roza su −10 %.
- **Caída más profunda que la del 5-nov, pero distinta.** VIX parecido (28,4 vs 28,2) y SPY más abajo (−8,4 % vs −6,2 %), pero el VIX/VIX3M está en 1,05, no en 1,10+. Es lo que el detector llama «no pánico agudo». No hay rendición y no digo qué hará mañana.
- **Mañana es viernes**, el día en que Pe puede actuar. Lo que dice el sistema ahora: notas BAJA, centinela LIQUIDEZ, el SPY aún sin tocar el −10 % ni «se va el pánico» nuevo. Lo que puede cambiar en el cierre de mañana: SPY −10 % (si cierra bajo 703,46, un −1,7 % más).
Nada más fuera de lo normal.

## 4. Marcador (con precios al día; todo orientativo salvo lo que diga)
- **GIRO↓** 30 casos: acierto 73 % (IC 56–86), exceso +8,4 pts (t 3,7). **GIRO↑** 32 casos: 28 % (IC 16–45), exceso −5,9 (t −2,6) → «va al revés».
- **Control de azar** (mismo activo, mismas fechas): GIRO↑ −0,3 pts (t −0,1) y GIRO↓ +1,0 (t 0,4): lo que se ve es lo que hacían esos activos (semis, plata), no la señal; I-001 (GIRO) queda en «sin señal propia». Resto con |t| < 1,3. **SUELO +4,6 (t 2,7, n 14) y EARLY +4,2 (t 2,1, n 13)**: con 10 señales mirándose a la vez, dos así salen por azar; no se toman en serio.
- Cesta semanal sin semana nueva hasta el viernes (11 semanas: −0,65 % frente a SPY −0,27 %; mejor que el SPY 4 de 11).
- Señales de hoy: CAPITUL (COPX, DIA, TAN)↑, NIVEL RSP↑, GRADUADO (KRE, DRAM, IWM, ITA)↑, GIRO↓ (WDC, STX, NCLD: semis y datos), FLOW XRT↓, SUELO (EWP, EWZ)↑, EARLY (DRAM, HYDR, DRIV)↑, SENT SPY↑. Casi todas alcistas tras una caída: lo que hagan dependerá del mercado.

## 5. Investigación (solo viernes)
Hoy no. Mañana viernes toca I-005 («se va el pánico» frente a comprar con el pánico aún vivo), si el modo semanal lo permite.

## 6. Propuestas para Pe
1. **Subir tú el arreglo de `agente/preparar.py`** (línea 206: `start=str(desde)` → `start=pd.Timestamp(desde).strftime("%Y-%m-%d")`). Yo no puedo hacer que persista. La desmentiría: que mañana el marcador salga con GIRO↑ en unos 32 casos sin tocar yo nada.
2. **(Repetida)** El cable de señales guarda solo 60 fechas (`rotacion.py` línea 3023); hacia el 2-dic borrará días ya maduros. La desmentiría: que ese archivo no pierda fechas en diciembre.

## 7. Lo que necesito de Pe
- Subir el arreglo de `preparar.py` o decirme que no importa.
- Decidir lo del cable de 60 fechas antes del 2-dic.
