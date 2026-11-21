# Registro de ideas del investigador

Cada idea se apunta ANTES de probarla y no se cambia después de ver resultados.
Estados: EN COLA · EN CURSO · DESCARTADA · CANDIDATA PARA OBSERVAR · SOLO OBSERVAR (en el marcador).

---

## I-001 · GIRO hacia abajo funciona y GIRO hacia arriba va al revés
- De dónde sale: marcador del 6-nov-2026 (GIRO↓ 14 casos a 20 sesiones, 79 % de aciertos; GIRO↑ 10 casos, 30 %), en plena caída del mercado.
- Estado: CERRADA el 20-nov-2026 — SIN SEÑAL PROPIA (ver nota 20-nov). (Antes: SOLO OBSERVAR; con pocos casos y el mercado cayendo era lo esperable aunque la señal no valgase nada.)
- Se revisa cuando GIRO↑ y GIRO↓ tengan 30 episodios cada uno a 20 sesiones.
- Nota 13-nov-2026: las cifras de arriba (14 y 10 casos) estaban medidas con precios congelados en el 2-nov (fallo mío, arreglado). Con precios al día: GIRO↑ n 30 (30 % de aciertos, exceso −5,1 pts, t −2,2) y GIRO↓ n 26 (73 %, +7,4, t 3,2). Control de azar (mismo activo, mismas fechas; estudios/control_azar_marcador.py): neto −0,4 (t −0,2) y +1,0 (t 0,4): es el comportamiento de los activos (semis, plata, temáticos), no de la señal. Se cierra cuando GIRO↓ llegue a 30.
- Nota 20-nov-2026 (cierre): con precios al día GIRO↓ n 31 (74 %, IC 57–86, exceso +8,5, t 3,9) y GIRO↑ n 34 (26 %, IC 15–43, exceso −5,4, t −2,5). Control de azar (mismo activo, mismas fechas): GIRO↑ +0,1 (t 0,1) y GIRO↓ +0,9 (t 0,4); agrupado por fechas (18 y 17 fechas): t 0,4 y −0,3. Lo que se ve es lo que hacían esos activos (semis, plata, temáticos), no la señal. No se reabre salvo con 3-6 meses más de datos nuevos.

## I-002 · VIX ≥ 20 y precio bajo su media de 200 sesiones mejoran las compras tras caídas
- De dónde sale: pista del estudio de suelos (23-oct-2026), sin probar limpiamente.
- Regla exacta: en SPY, QQQ, DIA, IWM y RSP, el primer día que el ETF cae −5 % (SPY/RSP/DIA) o −10 % (QQQ/IWM) desde su máximo de 52 semanas; grupo A = ese día VIX ≥ 20 y cierre bajo la media de 200 sesiones; grupo B = el resto. Rendimiento a 60 y 120 sesiones desde la apertura siguiente.
- La confirma: A gana a B en aprender (≤2018) y en comprobar (2019-2022), con t > 2 contando episodios.
- La tumba: diferencia < 1 punto o de signo distinto en los dos trozos.
- Variantes máximas: 3 (VIX ≥ 20, ≥ 25, ≥ 30).
- Estado: DESCARTADA (6-nov-2026). Ver estudios/i002.md: en aprender dif −0,9 pts, en comprobar −5,6 pts; caja sin abrir.

## I-003 · Detector de semis (especificación pendiente de Pe)
- De dónde sale: idea de Pe para la mesa de SEMIS.
- Regla exacta: SOXX cayendo (cierre bajo el de hace 5 sesiones) y CMF y OBV de SMH negativos N sesiones seguidas (N = 3, 5, 8). Tabla de lo que pasó a T+1, T+5, T+10, T+21 y T+30 con IC de Wilson y N, rotulada "frecuencia histórica, no predicción".
- Nota: no hay datos del flujo de órdenes minoristas; CMF/OBV de SMH es solo una aproximación.
- La confirma / la tumba: es contexto, no señal; se informa la tabla y si difiere de cualquier día con caída parecida de SOXX.
- Variantes máximas: 3 (los tres N).
- Estado: EN COLA.

## I-004 · «Se va el pánico» (VIX/VIX3M vuelve bajo 1,0) ¿es mejor entrada que un viernes cualquiera de una caída parecida?
- Apuntada el 13-nov-2026, ANTES de calcular ningún rendimiento (solo conté episodios por umbral).
- De dónde sale: es la bala 1 del plan de Pe (saltó el 9-nov) y está en «pistas vivas» («se va el pánico, mejor momento»). El marcador no la mide.
- Regla exacta: pánico = VIX/VIX3M (cierres CBOE, historiales/, VIX3M desde 18-sep-2009) ≥ umbral de arranque; «se va» = primer cierre posterior con VIX/VIX3M < 1,0, y SPY al menos −3 % bajo su máximo de 52 semanas ese día. Episodios separados ≥ 20 sesiones (cuenta el primero). Entrada = cierre del primer viernes ≥ ese día (Pe actúa los viernes). Rendimiento del SPY ajustado (con dividendos) a 20, 60 y 120 sesiones.
- Azar justo: viernes de la misma etapa, con el SPY a ±2,5 puntos de la caída que tenía el episodio, con VIX/VIX3M < 1,0 ese viernes y a más de 20 sesiones de cualquier episodio. Exceso del episodio = su rendimiento − la media de sus viernes parecidos. Se promedia por episodios (no por días).
- Trozos: aprender = episodios hasta 2018; comprobar = 2019-2022; caja cerrada 2023 en adelante NO se abre salvo que pase los dos primeros.
- Variantes (5, no más): C-60 (arranque ≥ 1,00; PRINCIPAL; 36 episodios hasta 2022), B-60 (arranque ≥ 1,05; 16), A-60 (arranque ≥ 1,10 = regla exacta del detector; solo 9, descriptiva), C-20 y C-120 (otros plazos del principal).
- La confirma: exceso medio ≥ +1,0 punto a 60 sesiones en aprender Y en comprobar, t > 2 con todos los episodios y ≥ 60 % de episodios con exceso positivo.
- La tumba: exceso < +1 punto en cualquiera de los dos trozos, o signo distinto entre ellos.
- Aviso previo: con la regla exacta (A) solo hay 9 episodios hasta 2022: no puede pasar de «orientativo». Las variantes B y C NO son la regla congelada del detector; sirven para ver si el concepto («el pánico se va → mejor entrada») tiene algo.
- Estado: DESCARTADA (13-nov-2026). Ver estudios/i004.md. Principal C-60 (36 episodios): exceso −1,5 pts (t −1,2); en aprender −2,7 (t −2,4) y en comprobar +1,2 (t 0,35); 15 de 36 por encima del azar justo. Regla exacta (9 episodios): inconcluyente. Caja 2023+ sin abrir.

## I-005 · «Se va el pánico» frente a comprar con el pánico TODAVÍA vivo (pregunta que dejó abierta I-004)
- Apuntada el 13-nov-2026, sin calcular nada todavía.
- De dónde sale: I-004 compara con viernes SIN pánico; la pista original decía que «se va el pánico» es mejor que comprar dentro del pánico.
- Regla exacta: mismos episodios y la misma entrada (primer viernes tras «se va») que I-004 variante C-60; comparar con viernes de la misma mitad de la historia, caída del SPY a ±2,5 puntos, con VIX/VIX3M ≥ 1,0 ese viernes (pánico vivo) y a más de 20 sesiones de cualquier episodio. Medir a 60 sesiones el rendimiento del SPY y la peor caída posterior.
- La confirma: «se va» gana al pánico vivo ≥ +1 punto a 60 sesiones en aprender (≤2018) y en comprobar (2019-2022), t > 2, o reduce la peor caída posterior en ≥ 2 puntos en las dos mitades.
- La tumba: diferencia < 1 punto o signo distinto entre las dos mitades.
- Variantes máximas: 3 (rendimiento a 20, 60 y 120 sesiones; el principal es 60).
- Estado: DESCARTADA (20-nov-2026). Ver estudios/i005.md. Principal (60 ses.): 28 episodios con viernes comparables (de 36); aprender −2,46 pts (N 22, t −1,92), comprobar +10,80 (N 6, t 2,90), todos +0,38 (t 0,24): signo distinto entre mitades → tumbada. En 2019-22 el «azar» son solo 3 viernes (covid, 2020): esa mitad no sirve para juzgar. A 20 y 120 sesiones tampoco. Caja 2023+ sin abrir.

## I-006 · ¿Importa lo rápido que la caída del S&P va del −5 % al −10 %? (¿llega después al −20 %?)
- Apuntada el 20-nov-2026, SIN calcular nada todavía (ni siquiera contar episodios por grupo).
- De dónde sale: hoy el SPY tocó su −10 % 11 sesiones después de su −5 % (5-nov → 20-nov) y se pregunta qué dice la historia de caídas así de rápidas. Lo ya medido (7-nov) es que la velocidad hasta el −5 % no separa y que lo que separa es que se alargue; la velocidad ENTRE el −5 % y el −10 % no se ha mirado.
- Regla exacta: S&P 500 diario 1927-2026 (`datos.sp500()`, cierres). Episodios = caídas que tocan −10 % bajo el máximo de 252 sesiones (`datos.caidas(sp, 0.10)`), cada una con su primer día en −5 % desde el MISMO pico (`datos.caidas(sp, 0.05)` emparejada por fecha de pico). Velocidad v = sesiones entre el toque del −5 % y el del −10 %. «Rápida» = v ≤ V; «lenta» = v > V. Resultado = la caída llega a −20 % bajo ese pico (`datos.caidas(sp, 0.20)`, mismo pico) antes de recuperar el máximo. Se compara el % que llega a −20 % en rápidas y en lentas, con N e intervalo de Wilson.
- Trozos: 1927-1974 y 1975-2022 (el S&P de 1950-2022 es lo que se parece a hoy; solo hay ~4 episodios en 2019-22, así que no se usa 2019-22 como «comprobar»). La caja 2023+ queda cerrada.
- La confirma: la diferencia de % que llega a −20 % entre rápidas y lentas es ≥ 15 puntos y del mismo signo en las dos mitades, con N ≥ 8 en cada celda y p < 0,05 (Fisher) con todos los episodios.
- La tumba: diferencia < 15 puntos en cualquiera de las dos mitades, signo distinto, o alguna celda con N < 8 (entonces «no concluyente»).
- Variantes máximas: 3 (V = 10, 15 y 20 sesiones; la principal es V = 15).
- Aviso previo: es una pregunta sobre el S&P (SPY), no sobre el QQQ ni los apalancados; es frecuencia histórica, no predicción.
- Estado: EN COLA (para el viernes 27-nov-2026).

---

Contador de ideas probadas (cuantas más, más exigente hay que ser): **3** (I-002, I-004 e I-005; todas descartadas). I-001 se cerró sin probarla como idea propia (control de azar del marcador).
