# Informe del compañero — 2026-11-10
## En una frase
Sistema sano (un solo aviso menor). El mercado cedió algo del rebote de ayer, no salta ninguna señal nueva del plan y el pánico sigue «ido» desde el 9-nov. Hoy es martes: se observa, se actúa el viernes al cierre.

## 1. ¿Funciona todo? (vigilante)
🟠 **Aviso nuevo, menor:** el ETF SDOG (dividendo, no es núcleo) no tenía aún la vela diaria en Yahoo y la terminal rehízo el cierre del 10-nov con barras de 1 hora (`rotacion.py`, función `_fresco_una`, línea ~1526). Consecuencia: el cierre de SDOG puede diferir unos céntimos del oficial; no afecta al plan ni a los índices. Mañana debería corregirse solo.
🟢 Todo lo demás grabado y al día; no hay log de fallo. Siguen abiertos los pendientes de la memoria (Telegram de la terminal sin activar; 6 acciones sin datos en Yahoo; petróleo CL=F; incoherencia ACECHO vs DISTRIBUCIÓN): sin cambios.

## 2. Señales del plan (lo que ha cambiado respecto a ayer)
Ninguna ha saltado hoy.
1. **Se va el pánico:** ya saltó el 9-nov. Hoy sigue sin pánico vivo (VIX/VIX3M 0,943; ayer 0,955). Sin cambios.
2. **SPY −10 %:** en 703,46; hoy 749,89, faltan −6,2 % (ayer −6,5 %). El SPY está a −4,1 % del máximo (ayer −3,7 %).
3. **QQQ −20 %:** en 610,29; hoy 674,75, faltan −9,6 % (ayer −10,2 %). QQQ a −11,6 % del máximo (ayer −10,9 %). Rendición total: NO (1,1 % de 20 en mínimos; 1 de 6 sectores sacando dinero; VIX/VIX3M 0,94 de 1,10).
4. **Bajista:** SPY −20 % (625,30) falta −16,6 %; QQQ −30 % (534,00) falta −20,9 %. Lejos.
5. **Control del mes:** el 7-dic, faltan 18 sesiones. Ojo: el SPY (749,89) está solo un 1,0 % por encima de la línea de 742,54 (la que separa «corrección normal», 9 % de seguir a −10 %, de «atascado», 57 %). Hoy está del lado bueno, pero con muy poco margen.

## 3. Qué dice hoy la terminal
Día de pequeño retroceso tras el rebote de ayer: SPY −0,4 %, QQQ −0,7 %, VIX 19,5. Dinero: AMPLIO (5 sectores entran, 1 sale; ni EMPUJE ni VENTA EXTREMA). Centinela: ACECHO. Veredictos: QQQ NO TOCAR; SPY, DIA, IWM, RSP y MAGS ESPERAR (el SPY mejora de NO TOCAR a ESPERAR respecto a ayer). Sin pánico agudo.
Lo que se puede pasar por alto:
- **Entra dinero en amplio, pero el precio no acompaña:** ayer MIXTO (3 entran, 2 salen), hoy AMPLIO (5 entran, 1 sale) con el SPY y el QQQ bajando. Es una pista a vigilar, no una conclusión: sin EMPUJE (el dato que mira la terminal) no hay nada que concluir.
- **La caída sigue siendo de tecnología:** RSP (las 500 a partes iguales) solo −1,5 % frente a QQQ −11,6 %. IWM empeora de −7,2 % a −7,8 %.
- **Posible fallo del cable (hipótesis, sin confirmar):** la señal «SE VA EL PÁNICO» que ayer entró en el cable de señales (`senales_wire.json`) ya no está hoy; tampoco unas filas CAPITUL/FLOW de ayer. Parece que cada noche se reescriben las filas con fecha de la última sesión y se pierde lo que el evento generó el día anterior. El código que la crea solo lo hace el día del evento (`rotacion.py` ~línea 16091, `if "se_va" in eventos`). Consecuencia: el marcador no podrá contar ese episodio. Propongo revisarlo (ver sección 6); no lo toco.

## 4. Marcador (qué señales van funcionando con datos nuevos)
Sin cambios respecto a ayer en los números: todo «orientativo» (ninguna señal llega a 30 casos a 20 sesiones). GIRO↓ 79 % (n 14), GIRO↑ 30 % (n 10), CLÍMAX 77 % (n 13), FLOW 77 % (n 17). Con el mercado cayendo es lo esperable y con ~15 señales alguna sale bien por azar. Siguen fallando 0/3 (18 %), EARLY (18 %), SUELO (29 %), y hoy el cable trae más SUELO (KWEB, URA, SLV), 0/3 (KWEB, EWP) y EARLY (DRAM, HYDR, DRIV): señales que hasta ahora no aciertan, con cautela. Hoy se contradicen en el mismo ETF: XLI sale con CLÍMAX↓ y GRADUADO↑ a la vez; UFO con CLÍMAX↓ y GIRO↑. Ninguna de las dos señales tiene casos suficientes para decidir cuál vale. Cesta semanal: −0,62 % de media frente a SPY −0,55 % (mejor 4 de 10 semanas). Nada demostrado.

## 5. Investigación (solo viernes)
Hoy no toca (modo diario).

## 6. Propuestas para Pe (como mucho 2)
1. **Revisar por qué el cable pierde la señal «SE VA EL PÁNICO» al día siguiente** (y las filas CAPITUL/FLOW). Por qué: es la señal 1 de tu plan y el marcador debería contarla; con la pérdida, el episodio de ayer no se medirá. Qué la desmentiría: que la fila esté guardada en otro sitio (p. ej. en el histórico del marcador) y solo desaparezca del cable por diseño.

## 7. Lo que necesito de Pe
- Nada urgente. El viernes al cierre es cuando se decide; hoy solo se observa.
- Pendientes tuyos: activar o no el Telegram de la terminal; especificar I-003 (semis); decidir lo de ACECHO vs DISTRIBUCIÓN; decir si quieres que se revise lo del cable (propuesta 1).
