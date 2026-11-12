# Informe del compañero — 2026-11-11
## En una frase
Sistema sano y sin avisos. El mercado rebotó con fuerza (SPY +1,3 %, QQQ +2,3 %), no salta ninguna señal nueva del plan y el pánico sigue «ido» desde el 9-nov. Hoy es miércoles: se observa, se actúa el viernes al cierre.

## 1. ¿Funciona todo? (vigilante)
🟢 Todo grabado y al día; no hay log de fallo. El aviso menor de ayer (SDOG con cierre rehecho por barras de 1 hora) no se ha repetido: se corrigió solo. Siguen abiertos los pendientes de la memoria (Telegram de la terminal sin activar; 6 acciones sin datos en Yahoo; petróleo CL=F; incoherencia ACECHO vs DISTRIBUCIÓN): sin cambios.

## 2. Señales del plan (lo que ha cambiado respecto a ayer)
Ninguna ha saltado hoy.
1. **Se va el pánico:** saltó el 9-nov. Hoy VIX/VIX3M 0,91 (ayer 0,94), sin pánico vivo. Sin cambios.
2. **SPY −10 %:** en 703,46; hoy 759,81, faltan −7,4 % (ayer −6,2 %). El SPY está a −2,8 % del máximo (ayer −4,1 %).
3. **QQQ −20 %:** en 610,29; hoy 690,39, faltan −11,6 % (ayer −9,6 %). QQQ a −9,5 % del máximo (ayer −11,6 %). Rendición total: NO (0,6 % de 20 en mínimos; 1 de 6 sectores sacando dinero; VIX/VIX3M 0,91 de 1,10).
4. **Bajista:** SPY −20 % (625,30) falta −17,7 %; QQQ −30 % (534,00) falta −22,7 %. Lejos.
5. **Control del mes:** el 7-dic, faltan 17 sesiones. El SPY (759,81) está ahora un 2,3 % por encima de la línea de 742,54 (ayer solo 1,0 %): del lado bueno («corrección normal», 9 % de seguir a −10 %) y con más margen. Aún queda un mes: orientativo.

## 3. Qué dice hoy la terminal
Día de rebote: SPY +1,3 %, QQQ +2,3 %, VIX 17,5 (ayer 19,5). Dinero: MIXTO (4 sectores entran, 1 sale; ni EMPUJE ni VENTA EXTREMA). Centinela: ACECHO. Veredictos: QQQ y MAGS NO TOCAR; SPY, DIA, IWM y RSP ESPERAR (MAGS vuelve de ESPERAR a NO TOCAR). Sin pánico agudo.
Lo que se puede pasar por alto:
- **Rebote sin confirmación del dinero:** ayer el dinero era AMPLIO con el precio bajando; hoy el precio sube con dinero solo MIXTO. Vaivén normal; sin EMPUJE no hay nada que concluir.
- **El rebote lo lidera la tecnología, que es la que más cayó:** QQQ recupera 2 puntos de caída (−11,6 → −9,5 %), el SPY 1,3 y RSP está ya en −0,7 %. La caída de esta vez ha sido de tecnología, no de todo el mercado (como en 2000 y 2022, según lo ya estudiado); el QQQ sigue a −9,5 %, al borde de su nivel de −10 %.
- **Corrección a la hipótesis de ayer sobre el cable:** dije que `senales_wire.json` había perdido la fila «SE VA EL PÁNICO». Comprobado hoy en el histórico: ese archivo nunca contuvo esa fila (el 9-nov no tiene ninguna fila con esa fecha; solo guarda unas etiquetas concretas, y el código `rotacion.py` ~16091 crea esa alerta para el aviso en pantalla). Así que probablemente no es un fallo, sino que el marcador simplemente no mide «SE VA EL PÁNICO». Retiro la propuesta de ayer; queda como duda menor: ¿quieres que el marcador la mida? (No es urgente.)

## 4. Marcador (qué señales van funcionando con datos nuevos)
Todo sigue «orientativo» (ninguna señal llega a 30 casos a 20 sesiones). GIRO↓ 79 % (n 14), GIRO↑ 30 % (n 10), CLÍMAX 77 % (n 13), FLOW 76 % (n 17). Con el mercado cayendo es lo esperable y con ~15 señales alguna sale bien por azar. Siguen sin acertar 0/3 (18 %), EARLY (18 %), SUELO (29 %). Hoy el cable vuelve a traer SUELO (FXI, SIL, SLV), 0/3 (FXI, EWP) y EARLY (DRAM, HYDR, DRIV): cautela. Contradicciones en el mismo ETF: XLI sale con CLÍMAX↓ y GRADUADO↑; EWP con CLÍMAX↓ y 0/3↑; FXI con 0/3↑ y SUELO↑ (estas dos del mismo lado). Ninguna tiene casos suficientes para decidir cuál vale. Cesta semanal: −0,62 % de media frente a SPY −0,55 % (mejor que el SPY 4 de 10 semanas, IC 17–69 %). Nada demostrado.

## 5. Investigación (solo viernes)
Hoy no toca (modo diario).

## 6. Propuestas para Pe (como mucho 2)
Ninguna nueva. (Retiro la de ayer sobre el cable: ver sección 3.)

## 7. Lo que necesito de Pe
- Nada urgente. El viernes al cierre es cuando se decide; hoy solo se observa.
- Pendientes tuyos: activar o no el Telegram de la terminal; especificar I-003 (semis); decidir lo de ACECHO vs DISTRIBUCIÓN.
