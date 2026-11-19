# Informe del compañero — 2026-11-18 (miércoles, modo diario)
## En una frase
El mercado ha vuelto a bajar un poco (SPY −6,6 % de su máximo, QQQ −13,6 %), el centinela sigue en **LIQUIDEZ** y no salta ninguna señal del plan. El marcador vuelve a salir congelado por la máquina y lo he reparado otra vez solo para hoy.

## 1. ¿Funciona todo? (vigilante)
🟢 La terminal salió bien: todo grabado y sin avisos nuevos. Siguen los avisos viejos de siempre (opciones, acciones sin datos, `universo_close` parado desde el 3-nov): sigue igual, sin consecuencias para ti.

**Marcador congelado, otra vez (3.er día).** `agente/preparar.py` volvió a salir sin mi arreglo (la máquina lo restaura por diseño). Lo parcheé en sitio y volví a generar el resumen: con el arreglo el marcador tiene los precios al día. Sin él, hoy GIRO↑ aparecía con 10 casos en vez de 30. Solución real: que lo subas tú (ver propuesta 1).

**Cable de señales:** 52 fechas guardadas de 60 posibles. Hacia el 2-dic empezará a borrar días viejos (sigue pendiente tu decisión).

## 2. Señales del plan (lo que ha cambiado)
Ninguna ha saltado hoy.
1. **Se va el pánico:** saltó el 9-nov. Hoy VIX/VIX3M 1,011 (ayer 1,019); VIX 24,6 (ayer 25,5). Sin pánico vivo ni agudo.
2. **SPY −10 %:** línea 703,46; hoy 730,19; falta −3,7 % (ayer −4,0 %). SPY a −6,6 % del máximo.
3. **QQQ −20 %:** línea 610,29; hoy 659,49; falta −7,5 % (ayer −7,1 %). QQQ a −13,6 %. Rendición total: NO (6,8 % de 20 acciones del S&P en mínimos; 3 de 6 sectores sacando dinero; VIX/VIX3M 1,01 de 1,10).
4. **Bajista:** SPY −20 % (625,30) falta −14,4 %; QQQ −30 % (534,00) falta −19,0 %.
5. **Control del mes:** 7-dic, faltan 12 sesiones. SPY 730,19, un 1,7 % bajo la línea 742,54 (ayer 1,4 %). Si el 7-dic siguiera entre −5 y −10 %, el histórico 1927-2026 da −10 % después el 57 % de las veces (N = 122 caídas; frecuencia histórica, no predicción).

## 3. Qué dice hoy la terminal
Detector de caídas: SPY −6,6 %, DIA −7,9 %, QQQ −13,6 %, IWM −11,3 %, MAGS −10,6 %, RSP −3,9 %. Dinero MIXTO (entran 2 sectores, salen 3), sin EMPUJE ni VENTA EXTREMA. Notas: todas BAJA salvo RSP MEDIA (6), y DIA pasó de FLOJA a BAJA (4→2). **Centinela LIQUIDEZ** (el estado más defensivo; por la jerarquía del sistema pesa más que cualquier otro panel).
Cosas que se pueden pasar por alto:
- **Caída lenta, sin miedo agudo.** Con el SPY casi igual que el 5-nov (−6,2 %), el VIX/VIX3M está en 1,01, no en 1,10+. Es el rasgo que separa «susto que pasa» de «rendición». Hoy no hay rendición; no digo qué hará mañana.
- Un detalle de fechas, ya conocido: el centinela guarda sus estados con un día de adelanto (el «19-nov» es el cierre del 18). No cambia nada del estado.
Nada más fuera de lo normal.

## 4. Marcador (con precios al día; todo orientativo salvo lo que diga)
- **GIRO↑** 30 casos: acierto 27 % (IC 14–44), exceso −6,0 pts (t −2,9) → «va al revés». **GIRO↓** 28 casos: 75 % (IC 57–87), exceso +8,2 (t 3,9), le faltan 2 para 30.
- **Control de azar** (mismo activo, mismas fechas): GIRO↑ −1,0 pts (t −0,6) y GIRO↓ +1,3 (t 0,7): lo que se ve es lo que hacían esos activos (semis, plata), no la señal. Resto: 0/3 +1,4, CAPITUL +0,7, CLÍMAX −0,8, FLOW +1,3, GRADUADO +1,9, NOCTURNO +0,5, todos |t| < 1,3. **SUELO +4,7 (t 2,7, n 14) y EARLY +4,2 (t 2,2, n 13)**: con 10 señales mirándose a la vez, dos así salen por azar; no se toman en serio (y EARLY por sí sola acierta solo 15 %).
- Cesta semanal sin semana nueva hasta el viernes (11 semanas: −0,65 % de media frente a SPY −0,27 %; mejor que el SPY 4 de 11).
- Señales de hoy: CAPITUL (REMX, COPX, TAN)↑, GRADUADO (DRAM, IWM, ITA, ITB)↑, GIRO↓ (STX, NCLD, KLAC), 0/3 EWP↑, SUELO URA↑, EARLY (DRAM, HYDR, NCLD)↑, SENT SPY↑. Casi todas alcistas tras una caída: lo que hagan dependerá del mercado.

## 5. Investigación (solo viernes)
Hoy no. El viernes 20-nov toca I-005 («se va el pánico» frente a comprar con el pánico aún vivo).

## 6. Propuestas para Pe
1. **Subir tú el arreglo de `agente/preparar.py`** (línea 206: `start=str(desde)` → `start=pd.Timestamp(desde).strftime("%Y-%m-%d")`). Yo no puedo hacer que persista. La desmentiría: que mañana el marcador salga con GIRO↑ en 30 casos sin tocar yo nada.
2. **(Repetida)** El cable de señales guarda solo 60 fechas (`rotacion.py` línea 3023); hacia el 2-dic borrará días ya maduros. La desmentiría: que ese archivo no pierda fechas en diciembre.

## 7. Lo que necesito de Pe
- Subir el arreglo de `preparar.py` o decirme que no importa.
- Decidir lo del cable de 60 fechas antes del 2-dic.
