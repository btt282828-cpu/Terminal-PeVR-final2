# Informe del compañero — 2026-11-16 (lunes, modo diario)
## En una frase
Hoy el mercado ha caído con fuerza (SPY −1,9 %, QQQ −2,7 %, VIX de 19,3 a 22,9) y el SPY ya está a −5,3 % de su máximo, pero no salta ninguna señal del plan. Además, mi arreglo del marcador del viernes había desaparecido y lo he vuelto a poner.

## 1. ¿Funciona todo? (vigilante)
La terminal salió bien y todos los archivos están al día. Solo un aviso 🟠 nuevo: **la web de Invesco (los pesos del QQQ) devolvió un error 406** y la terminal usó los pesos guardados del 12-nov. Es inofensivo: los pesos de un ETF cambian muy poco en 2 días. Si se repite varios días, habría que mirarlo.
Sin cambios de fondo desde el viernes: opciones, `universo_close` parado desde el 3-nov, etc. (no los repito).

**Fallo mío (mi arreglo había desaparecido):** el viernes arreglé `agente/preparar.py` (el marcador pedía los precios a Yahoo con una fecha con hora y la librería devolvía una tabla vacía sin avisar). Esta mañana el arreglo no estaba: el marcador volvía a medir con precios parados hacia el 2-nov. Lo he vuelto a poner (2 cambios de una línea: fecha sin hora y «repo» si Yahoo viene vacío) y he regenerado los datos: ahora los precios llegan al 16-nov. **Hay que comprobar mañana que sigue puesto** (`grep -n strftime agente/preparar.py`). Si desaparece otra vez, es que la máquina lo restaura desde otra copia, y te lo tendré que decir a ti.

## 2. Señales del plan (lo que ha cambiado)
Ninguna ha saltado hoy.
1. **Se va el pánico:** saltó el 9-nov. Hoy VIX/VIX3M 0,995 (el viernes 0,94): sube hacia 1,0 pero el pánico vivo exige ≥ 1,10, así que **no** hay pánico nuevo. Tampoco pánico agudo.
2. **SPY −10 %:** línea 703,46; hoy 739,96; falta −4,9 %. SPY a −5,3 % del máximo (viernes −3,5 %).
3. **QQQ −20 %:** línea 610,29; hoy 661,78; falta −7,8 %. QQQ a −13,3 % (viernes −10,9 %). Rendición total: NO (5,8 % de 20 en mínimos; 1 de 6 sectores sacando dinero; VIX/VIX3M 0,99 de 1,10).
4. **Bajista:** SPY −20 % (625,30) falta −15,5 %; QQQ −30 % (534,00) falta −19,3 %.
5. **Control del mes:** 7-dic, faltan 14 sesiones. **SPY cierra hoy en 739,96, por debajo de la línea 742,54** (el viernes estaba un 1,6 % por encima). Si el 7-dic siguiera así (entre −5 y −10 %), el histórico 1927-2026 dice −10 % luego el 57 % de las veces (N = 122 caídas de ese tipo, frecuencia histórica, no predicción). Faltan 3 semanas: hoy es solo una foto.

## 3. Qué dice hoy la terminal
VIX 22,9. Dinero MIXTO (entran 3 sectores, sale 1; sin EMPUJE ni VENTA EXTREMA). Centinela ACECHO. Notas: SPY FLOJA (4), QQQ BAJA (1; el viernes 2), DIA MEDIA (6), IWM FLOJA (4), RSP ALTA (8), MAGS BAJA (3). Caídas desde máximo: IWM −10,3 %, MAGS −10,5 %, DIA −5,4 %, RSP −2,4 %.
Lo que se puede pasar por alto (hoy son dos):
- **La caída de hoy no se parece a la del susto del 5-nov:** entonces hubo pánico agudo; hoy el VIX9D (23,15) está casi igual que el VIX (22,9) y el VIX3M (23,02): las tres curvas casi planas, sin el pánico de corto plazo disparado. Dicho claro: ha bajado el mercado, pero el miedo no se ha desbordado todavía. Y el dinero no «se va» de forma generalizada (1 sector saliendo de 6). Eso no dice qué hará mañana.
- **Sigue siendo una caída de tecnología:** RSP (S&P a partes iguales) saca ALTA (8) y está a solo −2,4 %, mientras el QQQ saca 1 y está a −13,3 %. Lo ya estudiado: repartir entre índices ayudó cuando la caída la lideró un sector (2000, 2022), no en una crisis de todo el sistema (2008). Hoy el mercado amplio aún no muestra crisis general.
- Pequeña rareza (sin importancia para el plan): el aviso de «PLAN SPY» usa como máximo 779,09 y el detector de caídas usa 781,6 aprox. (por eso el SPY sale −5,0 % en uno y −5,3 % en otro). Tiene pinta de máximo de cierre contra máximo intradía; no lo he comprobado.

## 4. Marcador (qué señales van funcionando con datos nuevos)
Con los precios ya al día (hasta el 16-nov), todo sigue «orientativo»; las cifras solo se pueden comparar con las del viernes 13-nov:
- **GIRO↑** llega a **30 casos** (acierto 30 %, IC 17–48 %, exceso −5,1 puntos frente al SPY, t −2,2): el script lo etiqueta «VA AL REVÉS». **GIRO↓**: 27 casos, 70 % (IC 52–84 %), exceso +6,9 (t 3,1).
- **Control de azar** (mismo activo, mismas fechas, `estudios/control_azar_marcador.py`): GIRO↑ −0,35 puntos (t −0,2) y GIRO↓ +0,7 (t 0,3). Es decir, no hay señal por encima de lo que ya hacía el activo; las dos marcan los mismos valores (semis, plata) que rindieron peor que el SPY. CLÍMAX −0,4, FLOW +0,8, NOCTURNO +0,4, 0/3 +1,1, CAPITUL +1,2, GRADUADO +1,9: nada (|t| < 1,1).
- **EARLY** (+4,2 puntos, t 2,25, n 13) y **SUELO** (+4,3, t 2,2, n 12) salen algo por encima, pero con 10 señales mirándose a la vez es normal que dos así salgan por azar, y con n < 15 no se puede decir nada. Anotadas, no tomadas en serio. (El viernes EARLY y SUELO llevaban +4,2 y ~0.)
- **I-001 (GIRO):** GIRO↑ ya tiene 30; GIRO↓ lleva 27 (25 con línea base) y hay 21 en espera. Lo cerraré cuando GIRO↓ llegue a 30. Adelanto: el control de azar ya dice que no hay señal por encima del activo.
- Cable de hoy: CAPITUL (REMX, IBIT, DRIV), GRADUADO (DRAM, IWM, ITA, ITB), GIRO ICLN↑, 0/3 y SUELO FXI↑, SUELO URA↑, EARLY (DRAM, HYDR, NCLD). Muchos son alcistas tras una caída: cuentan como un episodio cada uno, y con el mercado cayendo hoy sus próximos 20 días dependerán de lo que haga el mercado. Cesta semanal: 11 semanas, −0,65 % de media frente a SPY −0,27 %; mejor 4 de 11 (IC 15–65 %); sin semana nueva hasta el viernes.

## 5. Investigación (solo viernes)
Hoy no se investiga. Toca I-005 el viernes 20-nov («se va el pánico» frente a comprar con el pánico aún vivo), salvo que me pidas otra cosa.

## 6. Propuestas para Pe
1. **(Repetida del viernes, sigue pendiente de tu respuesta)** El cable de señales solo guarda 60 sesiones (`rotacion.py` línea 3023) y empezará a borrar días viejos hacia el 2-dic; además el 9-nov se guardó con fecha 10-nov. Me gustaría que decidieras si lo cambias tú. Si no, reconstruyo el cable desde git antes de cualquier cálculo. Qué la desmentiría: que el tope no exista (lo verifiqué el viernes: hoy hay 50 fechas en el cable).
2. Nada más hoy.

## 7. Lo que necesito de Pe
- Que me confirmes si quieres que siga tocando `agente/preparar.py` (el arreglo del viernes se perdió, no sé cómo; lo he rehecho).
- Lo de arriba sobre el cable de 60 sesiones, cuando te venga bien (no es urgente hasta el 2-dic).
