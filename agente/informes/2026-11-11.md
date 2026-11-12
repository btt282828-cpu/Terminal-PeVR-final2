# Informe del compañero — 2026-11-11 (versión revisada tras la terminal v8.5)
## En una frase
La terminal funciona y ha pasado a la v8.5 (la que subiste hoy); no salta ninguna señal nueva del plan. El mercado rebotó (SPY −2,8 % desde el máximo, QQQ −9,5 %) y el pánico sigue «ido» desde el 9-nov. Hoy es miércoles: se observa, se actúa el viernes al cierre.

## 1. ¿Funciona todo? (vigilante)
🟠 Un aviso nuevo, menor: la terminal corrió a las 01:41 de Nueva York, antes de que cierre la sesión de opciones del día 12, así que el dato de volumen de opciones (PCR-vol) de hoy es provisional. Consecuencia: no te fíes de ese número; usa el PCR-OI (el de posiciones abiertas, de ayer). No toca nada del plan ni de las señales.
Otros avisos que ya estaban (sin cambios): ETF jóvenes DRAM y NCLD; IV descartada por poco plausible en unos 51 ETF; petróleo CL=F sin cierre válido en Yahoo (usa otra fuente).
Cambios menores respecto a ayer: (a) ahora son 7 acciones de SECTOR_STOCKS sin datos (ayer 6; incluidas CTRA, EA, GATO…), (b) el put/call de SIL y FXI sale fuera de banda y la terminal no lo publica (dato roto o cadena fina). Todos los archivos del histórico están al día.
Nota: hoy la terminal se ejecutó dos veces para la misma fecha (la segunda ya con v8.5). Los archivos de estado no se duplican (mismo número de elementos), y la v8.5 está hecha para que repetir el build no borre señales.

## 2. Señales del plan (lo que ha cambiado)
Ninguna ha saltado hoy.
1. **Se va el pánico:** saltó el 9-nov (en el plan nuevo es la bala 1 desde esa fecha). Hoy VIX/VIX3M 0,91, sin pánico vivo. Sin cambios.
2. **SPY −10 %:** en 703,46; hoy 759,81, faltan −7,4 %. SPY a −2,8 % del máximo.
3. **QQQ −20 %:** en 610,29; hoy 690,39, faltan −11,6 %. QQQ a −9,5 % del máximo. Rendición total: NO (0,6 % de 20 en mínimos; 1 de 6 sectores sacando dinero; VIX/VIX3M 0,91 de 1,10).
4. **Bajista:** SPY −20 % (625,30) falta −17,7 %; QQQ −30 % (534,00) falta −22,7 %. Lejos.
5. **Control del mes:** el 7-dic, faltan 17 sesiones. SPY un 2,3 % por encima de la línea de 742,54: del lado «corrección normal» (9 % sigue a −10 %). Queda un mes: orientativo.

## 3. Qué dice hoy la terminal
Rebote: VIX 17,5. Dinero MIXTO (4 sectores entran, 1 sale; sin EMPUJE ni VENTA EXTREMA). Centinela: ACECHO. Sin pánico agudo.
Con la v8.5 los veredictos ya no dan órdenes, sino una nota: SPY NOTA FLOJA (4), QQQ NOTA BAJA (2), DIA y IWM NOTA MEDIA (7), RSP NOTA ALTA (10), MAGS NOTA BAJA (3). Son las mismas puntuaciones de ayer con otro nombre: ESPERAR = NOTA FLOJA, NO TOCAR = NOTA BAJA, por eso no es un cambio del mercado.
Lo que se puede pasar por alto:
- **Cambio de etiquetas, no de mercado:** si comparas con mensajes anteriores, «NO TOCAR» ahora se llama «NOTA BAJA». La propia v8.5 dice que la nota baja mirada de 2021 a 2026 fue seguida de subidas mayores: no la leas como aviso de peligro.
- **La caída es de tecnología, no de todo el mercado:** QQQ −9,5 % y MAGS −7,9 %, pero RSP (S&P a partes iguales) solo −0,7 %. Parecido a 2000 y 2022 según lo ya estudiado, y distinto de una crisis general como 2008. El QQQ está a medio punto de su nivel de −10 %.
- **SUELO en FXI y SIL el mismo día en que el put/call de FXI y SIL sale roto:** coincidencia de ETF con datos de opciones poco fiables; no sé si la señal SUELO usa opciones (no lo he comprobado). Con SUELO acertando solo 29 % (n 7) no merece más atención.
No hay nada más fuera de lo normal.

## 4. Marcador (qué señales van funcionando con datos nuevos)
Todo orientativo (ninguna llega a 30 casos a 20 sesiones). GIRO↓ 79 % (n 14), CLÍMAX 77 % (n 13), FLOW 76 % (n 17), GIRO↑ 30 % (n 10); 0/3 18 %, EARLY 18 %, SUELO 29 %. Con el mercado cayendo y unas 15 señales, que alguna salga bien es puro azar esperable. Hoy el cable trae 20 señales; contradicciones en el mismo ETF: XLI con CLÍMAX↓ y GRADUADO↑, EWP con CLÍMAX↓ y 0/3↑. Cesta semanal: −0,62 % de media frente a SPY −0,55 % (mejor 4 de 10 semanas, IC 17–69 %). Nada demostrado.

## 5. Investigación (solo viernes)
Hoy no toca (modo diario).

## 6. Propuestas para Pe
Ninguna.

## 7. Lo que necesito de Pe
- Nada urgente. El viernes al cierre se decide; hoy solo se observa.
- Pendientes tuyos: activar o no el Telegram de la terminal; especificar I-003 (semis); decidir lo de ACECHO vs DISTRIBUCIÓN (ahora que la v8.5 quitó las órdenes, puede que ya no aplique: dímelo).
