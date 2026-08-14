# -*- coding: utf-8 -*-
"""
config.py — PARAMETROS DEL TERMINAL  (v4, entrega 2)

COMO FUNCIONA
  Este archivo esta VACIO de efecto por defecto: todo esta comentado con #.
  Si borras la # de una linea, ESE valor manda y sustituye al de rotacion.py.
  Si borras este archivo entero, el terminal sigue funcionando igual.

  O sea: no puedes romper nada tocando aqui. Solo cambias lo que descomentes.

REGLA
  Cambia UN parametro por semana y anota que cambiaste. Si tocas cinco a la vez
  y el resultado empeora, no sabras cual fue.

  Los valores que ves comentados son EXACTAMENTE los que usa hoy el terminal.
"""

# ====================================================================
# QUE MIRA EL TERMINAL (universo)
# ====================================================================
# BENCH = "SPY"                                   # indice de referencia

# SECTORS = ["XLK","XLF","XLE","XLV","XLY","XLP","XLI","XLB","XLU","XLRE","XLC"]

# THEMATIC = ["FXI","EEM","ITA","MAGS","EWG","EWP","COPX","URA","LIT"]   # EWG=Alemania(DAX), EWP=España(IBEX); COPX=cobre, URA=uranio, LIT=litio

# EXTRA = ["JETS","SMH","KRE","XBI","GDX","IGV","SOXX","ITB","KWEB","GRID","PAVE","FIW","CGW","HYDR",
#          "XRT","XOP","OIH","ARKF","ARKK","CIBR","SKYY","BOTZ","TAN","ICLN","FAN","XME","SIL","SLV","EWJ","INDA","EWZ","VGK","IBIT","DRIV","EWY","MOO","QTUM","ARKX","UFO"]   # ...+ infraestructura de IA: red eléctrica (GRID), construcción (PAVE), agua EE.UU. (FIW), global (CGW) e hidrógeno (HYDR) + Bitcoin (IBIT) + espacio (ARKX)

# SATELLITES = ["IWM","DIA","TLT","GLD","HYG","UUP","LQD","EMB","RSP"]     # para riesgo y regimen macro (+crédito IG/emergente y S&P equiponderado para los sintéticos de pulso)

# WATCHLIST = ["RKLB", "PCT", "OPEN", "OKLO", "QUBT", "UBER", "AA", "AMBA", "AUR"]


# ====================================================================
# CARTERA
# ====================================================================
# CARTERA_CAPITAL = 1000                           # € a repartir en la "cartera de la semana" (Lider+Mejorando)

# CARTERA_PESO_MAX = 34   # tope de % por posicion en la cartera semanal; lo que no se reparte va a LIQUIDEZ

# MAX_POSICIONES = 7                               # tope de posiciones (las N de mayor impulso); 0 = sin tope -> prioriza los subsectores fuertes

# PESO = "volatilidad"                             # reparto: "igual" | "volatilidad" (inversa, mas a lo estable) | "impulso"

# BUFFER = 1.0                                     # histeresis: entra si fuerza>100+BUFFER y sale si <100-BUFFER (menos latigazos)

# CARTERA_SCORE_MIN = 3                            # la cartera no entra en ETFs con scoring < este valor (0 = desactivado). 3 = fuera solo los "evitar" (<=2); 4 = solo "comprar" (estricto, muy concentrado). La distribución oculta SIEMPRE se excluye aparte.

# CARTERA_DUAL_MOMENTUM = True                     # la cartera exige tambien momentum ABSOLUTO positivo (no entra en lo que sube vs S&P pero pierde dinero)

# CARTERA_LIDER_PRIMERO = True                      # True = la cartera prioriza los LÍDER (flujo confirmado) antes que los MEJORANDO, y dentro de cada grupo ordena por impulso. Evita que un rebote acelerado (Mejorando) le quite el sitio a un líder confirmado. False = ordena solo por impulso (puede colar rebotes por delante de líderes).

# CARTERA_EXIGE_FLUJO = True                        # True = la cartera excluye a los que tienen el dinero SALIENDO de verdad (CMF < -0.05, mismo umbral que todo el panel; el flujo PLANO entre -0.05 y +0.05 NO expulsa). Asi Cartera y Operativa cuentan la misma historia sin echar a sectores sanos con flujo plano (XLF/XLV). False = la cartera entra solo por impulso.

# CARTERA_AVISA_TENDENCIA = True                   # True = la cartera NO expulsa a los que están bajo su media de 40 semanas, pero les pone una etiqueta de aviso "⚠ rebote bajo tendencia, mira el gráfico" (tú decides con el gráfico). False = sin aviso.


# ====================================================================
# SALIDAS Y RIESGO
# ====================================================================
# SALIDA_MA_SEMANAS = 10                            # media móvil semanal para la señal de SALIDA (stop de tendencia). 10 = rápida (protege más plusvalía, algún latigazo) · 20 = media · 30 = lenta (aguanta toda la tendencia pero devuelve más arriba). Cuando el precio CIERRA el viernes por debajo de esta media, es señal de salir.

# SALIDA_BANDA_K = 1.0                              # banda anti-latigazo = K × volatilidad semanal del propio ETF (26s). Cerrar bajo la media DENTRO de la banda = solo aviso (1ª semana); hace falta confirmación (2ª semana) o ruptura clara (fuera de la banda) para SALIR. Sube K (1.5) si aún te da latigazos; bájalo (0.5) si te saca tarde.

# SALIDA_STOP_K = 2.5                               # stop duro estilo chandelier: pico de 12 semanas − K × volatilidad. Si el precio cae por debajo, SALIR aunque la media aún no lo confirme (protege de desplomes rápidos que la media tarda en ver).

# TREND_FILTER = True                              # solo invertir si el S&P > su media de 40 semanas (~200d); si no, liquidez

# TREND_MA_WEEKS = 40                              # media para el filtro de tendencia del mercado

# DD_THRESHOLDS = [2.5, 5, 10, 20]                 # umbrales para la tabla de caidas

# DD_GAP_PP = 0.5                                   # los cubos grandes (>=10%) saltan a partir de (umbral - esto): capta el hueco nocturno del futuro/CFD que el SPY no registra en su sesion de contado (p.ej. -10% salta a partir de -9.5%)

# CASH_PLAN = [(5, 30), (10, 30), (20, 40)]        # (caida % desde maximo, % de cartera a desplegar)

# STRESS_DD = [-5, -10, -20]                       # escenarios de caida del S&P para el stress-test


# ====================================================================
# CENTINELA (regimen)
# ====================================================================
# CENTINELA_SPREAD_ON = 0.8        # spread por encima → el dinero está en alta beta (RISK-ON)

# CENTINELA_SPREAD_OFF = -0.8      # spread por debajo → liderazgo defensivo (LIQUIDEZ)

# CENTINELA_CAIDA_3S = -0.8        # caída del spread en 3 semanas que dispara el aviso de DISTRIBUCIÓN


# ====================================================================
# CLIMA / PETARDAZOS
# ====================================================================
# CLIMA_VENTANA = 3                # sesiones hacia atrás que se revisan (si el petardazo fue el lunes y ejecutas el miércoles, se sigue marcando)

# CLIMA_Z = 2.2                    # umbral: |retorno del día| >= 2.2× su desviación típica diaria (60 sesiones previas a ese día)

# CLIMA_VOL_FUERTE = 1.3           # si además el volumen de ese día fue >= 1.3× su media de 20, se anota "con volumen" (señal más fiable)

# FLUJO_NOCTURNO_MIN = 2.0         # gap acumulado de 20 sesiones (en %) a partir del cual se marca acumulación extranjera


# ====================================================================
# CESTAS SINTETICAS
# ====================================================================
# SINT_MIN_RS = 50      # percentil minimo de fuerza relativa para entrar al cesto

# SINT_MAX_HI = 90      # % del maximo de 52s por encima del cual se considera "extendida" (fuera del cesto)

# SINT_TOP = 5          # tope de acciones en el cesto

# SINT_MIN_N = 2        # si pasan menos de estas, avisa (cesto demasiado fino)


# ====================================================================
# SENAL CONTRARIA
# ====================================================================
# CONTRARIAN_ON = True                             # activa el modulo de senal contraria (ledger fuera-de-muestra + tamano sugerido)

# CONTRARIAN_SIZE_PCT = 2.0                        # % de cartera por senal mientras la muestra fuera-de-muestra sea corta (<20 casos)

# CONTRARIAN_MAX_SIGS = 3                          # maximo de senales simultaneas (tope de exposicion contraria = SIZE x MAX)

# CONTRARIAN_HORIZON_W = 4                         # horizonte de evaluacion en semanas (el de tu estadistica)


# ====================================================================
# ACCIONES LIDERES
# ====================================================================
# STOCK_LEADERS = True                             # añade el panel de acciones lideres (descarga mas datos)

# LEADERS_TOP_N = 6                                # cuantas acciones mostrar por sector

# LEADERS_MIN_RS = 90                              # umbral de "lider" (percentil)


# ====================================================================
# DATOS Y VENTANAS
# ====================================================================
# WEEKS = 70                                       # semanas de historico a usar

# TAIL = 8                                         # longitud de la estela del RRG

# DATA_PRIMARY = "yahoo"                            # fuente principal: "yahoo" (mas fresco; Stooq no responde en algunas IPs/regiones) o "stooq". La otra queda de respaldo

# TOPUP_YAHOO = True                               # rellenar la ultima barra que falte con Yahoo (frescura); util en local, en la nube puede limitar

# DIX_ON = True

# ISM_MANUAL = 54.0                                # ISM manufacturas (no esta limpio en FRED gratis): actualizalo a mano el 1er dia habil de cada mes. Ult.: 54.0 (mayo-2026)

# BACKTEST = True                                  # calcular el backtest de la estrategia

# MEAN_REVERSION = True                            # calcula la rentabilidad media anual (10a) y la del año (YTD) de cada ETF -> panel "margen vs su media" (descarga ~10a por ETF, algo mas lento; pon False para desactivar)

# RRG_SOLO_SECTORES = False                        # True = en el RRG solo los 11 sectores SPDR (mas limpio)


# ====================================================================
# INTELIGENCIA ARTIFICIAL
# ====================================================================
# IA_AUTO = True                                   # ejecutar automaticamente el prompt maestro en cada build (si hay API key)

# IA_AUTO_MODEL = "claude-sonnet-4-6"              # modelo del analisis largo. Alternativas: "claude-opus-4-6" (mejor y mas caro), "claude-haiku-4-5" (mas barato)

# IA_WEB_SEARCH = True                             # permitir a la IA buscar en la web (13F, VIX, earnings...); suma coste por busqueda

# IA_MAX_TOKENS = 2000                             # longitud maxima de cada respuesta

# IA_PROVIDER = "anthropic"                        # PRECONFIGURADO en Anthropic (pago por uso, con busqueda web en vivo). Solo falta tu key en anthropic_key.txt

# AI_MODEL = "claude-haiku-4-5"                    # modelo del comentario corto (editable segun tu cuenta)


# ====================================================================
# RUTAS
# ====================================================================
# SITE_DIR = "site"                                # carpeta que publica GitHub Pages

# CACHE_DIR = "cache_rotacion"

# SEGUIMIENTO_DIR = "historico_seguimiento_NO_BORRAR"


# ====================================================================
# AMPLITUD ESTILO McCLELLAN
# ====================================================================
# El -100 es el umbral clasico del NYSE. Sobre el S&P 500 puede no ser el
# equivalente: el panel te muestra el umbral por percentil de tu propia serie.
# Si ese numero es muy distinto de -100, prueba a poner aqui el del percentil.
# MCC_UMBRAL = -100.0

# Cierres por encima del umbral que confirman la senal (tu regla: 2)
# MCC_CONFIRMACIONES = 2
