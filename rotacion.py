#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROTACION - Smart-Money Flow Terminal (version de escritorio)
============================================================
Descarga datos REALES de fin de dia (gratis, sin API key) de:
  1) Stooq  (fuente principal, sin key)
  2) Yahoo / yfinance  (respaldo automatico, sin key)

Calcula la rotacion sectorial estilo RRG (RS-Ratio / RS-Momentum),
detecta giros tempranos, amplitud, apetito de riesgo y un regimen
macro automatico deducido del propio mercado. Genera un panel HTML
con el mismo aspecto del terminal y lo abre en tu navegador.

USO
---
  python rotacion.py

Se ejecuta despues del cierre de Wall Street (datos de fin de dia).
La primera vez instala solas las librerias que falten.

OPCIONAL (macro mas rico): pon tu key gratuita de FRED abajo en CONFIG.
"""

import sys, subprocess, importlib, os, json, math, time, webbrowser, datetime as dt
import logging
from logging.handlers import RotatingFileHandler

# ======================================================================
# SALUD DEL BUILD — cambio 1 de la revision senior: los fallos de CALCULO
# nunca mas seran silenciosos. Todo aviso queda en tres sitios a la vez:
#   1) consola (como siempre),
#   2) rotacion.log rotatorio junto al script (5 archivos x 1MB, auto-.gitignore),
#   3) el panel "SALUD DEL BUILD" del propio terminal (pestana PRO).
# Filosofia intacta: el build NUNCA se rompe; pero ahora deja rastro de
# todo lo que degrado, para que un numero raro no pase por bueno.
# ======================================================================
SALUD_BUILD = []          # [(origen, mensaje)] acumulado durante la ejecucion
_SALUD_MAX = 120          # tope duro para no inflar memoria/HTML

def _setup_log():
    lg = logging.getLogger("rotacion")
    if lg.handlers:
        return lg
    lg.setLevel(logging.INFO)
    try:
        base = os.path.dirname(os.path.abspath(__file__))
    except Exception:
        base = "."
    ruta = os.path.join(base, "rotacion.log")
    try:
        fh = RotatingFileHandler(ruta, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        lg.addHandler(fh)
        # el log no debe acabar en GitHub: auto-.gitignore (mismo patron que las API keys)
        if os.path.isdir(os.path.join(base, ".git")):
            gi = os.path.join(base, ".gitignore")
            try:
                cont = open(gi, "r", encoding="utf-8").read() if os.path.exists(gi) else ""
                if "rotacion.log" not in cont:
                    with open(gi, "a", encoding="utf-8") as f:
                        f.write(("" if (not cont or cont.endswith(chr(10))) else chr(10)) + "rotacion.log*" + chr(10))
            except Exception:
                pass
    except Exception:
        pass                                              # sin permiso de escritura: consola y panel siguen funcionando
    return lg

_LOG = _setup_log()

def _avisar(origen, msg, nivel="warning"):
    """Registra una degradacion de datos/calculo en consola + log + panel de salud.
    origen: nombre corto de la funcion/fuente ('options.XLB', 'refresco_yahoo', ...).
    Los avisos identicos se agrupan (contador) para no inundar con 40 repeticiones."""
    try:
        m = str(msg)[:180]
        getattr(_LOG, nivel, _LOG.warning)("[%s] %s", origen, m)
        print(f"  ⚠ [{origen}] {m}")
        for i, (o, t, n) in enumerate(SALUD_BUILD):
            if o == origen and t == m:
                SALUD_BUILD[i] = (o, t, n + 1)
                return
        if len(SALUD_BUILD) < _SALUD_MAX:
            SALUD_BUILD.append((origen, m, 1))
    except Exception:
        pass                                              # el sistema de avisos jamas puede tumbar el build


# ======================================================================
# DEGRADACIONES SILENCIOSAS  (v4 — entrega 1)
# _avisar() cuenta lo que YA se detectaba. _deg() cuenta lo que hasta ahora
# se tragaba un "except: pass" dentro de funciones de CALCULO. No imprime
# nada por consola (evita el ruido de 170 avisos): solo agrega por origen y
# se muestra RESUMIDO en el panel SALUD DEL BUILD. Sirve para responder a
# "por que este numero salio raro un viernes".
# ======================================================================
_DEG = {}                 # {origen: [veces, ultimo_error]}
_DEG_MAX = 200

def _deg(origen, err=""):
    """Anota una degradacion silenciosa. Nunca lanza. Nunca imprime."""
    try:
        o = str(origen)[:60]
        e = (type(err).__name__ + ": " + str(err)) if isinstance(err, BaseException) else str(err)
        if o in _DEG:
            _DEG[o][0] += 1
            _DEG[o][1] = e[:110]
        elif len(_DEG) < _DEG_MAX:
            _DEG[o] = [1, e[:110]]
    except Exception:
        pass

def _deg_resumen(top=25):
    """Lista [(origen, veces, ultimo_error)] ordenada por frecuencia."""
    try:
        return sorted(([o, v[0], v[1]] for o, v in _DEG.items()),
                      key=lambda x: -x[1])[:top]
    except Exception:
        return []

# ----------------------------------------------------------------------
# CONFIG  (lo unico que quizas quieras tocar)
# ----------------------------------------------------------------------
BENCH = "SPY"                                   # indice de referencia
SECTORS = ["XLK","XLF","XLE","XLV","XLY","XLP","XLI","XLB","XLU","XLRE","XLC"]
# Tematicos / regionales: China, Emergentes, Espacio-Defensa, 7 Magnificos
THEMATIC = ["FXI","EEM","ITA","MAGS","EWG","EWP","COPX","URA","LIT"]   # EWG=Alemania(DAX), EWP=España(IBEX); COPX=cobre, URA=uranio, LIT=litio
# Extra utiles para detectar rotaciones (viajes, semis, banca regional, biotech, mineras oro, software, vivienda, China tech)
EXTRA = ["DRAM","NCLD","JETS","SMH","KRE","XBI","GDX","IGV","SOXX","ITB","KWEB","GRID","PAVE","FIW","CGW","HYDR",
         "XRT","XOP","OIH","ARKF","ARKK","CIBR","SKYY","BOTZ","TAN","ICLN","FAN","XME","SIL","SLV","EWJ","INDA","EWZ","VGK","IBIT","DRIV","EWY","MOO","QTUM","ARKX","UFO"]   # ...+ infraestructura de IA: red eléctrica (GRID), construcción (PAVE), agua EE.UU. (FIW), global (CGW) e hidrógeno (HYDR) + Bitcoin (IBIT) + espacio (ARKX)
SATELLITES = ["IWM","DIA","TLT","GLD","HYG","UUP","LQD","EMB","RSP"]     # para riesgo y regimen macro (+crédito IG/emergente y S&P equiponderado para los sintéticos de pulso)

# Acciones de agua (componentes de FIW) que CREO disponibles como CFD en XTB.
# OJO: no puedo verificarlo en vivo desde aqui y XTB cambia su catalogo; esto es un
# punto de partida con las large-caps mas liquidas. VERIFICALO tu en el buscador de
# instrumentos de XTB antes de operar. Anade o quita tickers a mano segun lo que veas.
# === ACCIONES SUELTAS PARA CESTAS SINTETICAS (v4.7) ===
# No todo tema tiene ETF. El almacenamiento (discos duros y SSD) es el caso claro:
# el sector entero son TRES empresas cotizadas, demasiado pocas para que alguien
# lance un fondo. Van diluidas dentro de DRAM (que es 73% Samsung + SK Hynix +
# Micron, o sea memoria, no almacenamiento), asi que su pulso propio no se ve.
# Estas acciones se descargan como cualquier otro simbolo y se promedian en una
# cesta que entra al RRG como una bolita mas. Mismo mecanismo que el sintetico
# de agua (FIW) que ya usas.
ACCIONES_SINTETICAS = ["WDC", "STX", "SNDK",       # almacenamiento: discos duros y SSD
                       "ASML", "LRCX", "AMAT", "KLAC"]  # equipos semi: las maquinas que fabrican el chip

XTB_CFD_AGUA = {"ECL","ROP","AWK","FERG","XYL","A","WAT","IDXX","IEX","PNR","MAS","J","ACM","VLTO"}

# === GRUPOS para organizar los paneles (selector del RRG y bloques de tablas) ===
GRUPO_SECTORES = SECTORS + ["IWM","DIA","RSP"]                             # 11 basicos + small caps + S&P equiponderado (amplitud)
GRUPO_SUBSECTORES = ["XBI","KRE","JETS","ITB","ITA","XRT","XOP","OIH","ARKX","UFO"]          # temas EE.UU. no-IA (biotech, banca regional, viajes, vivienda, defensa, espacio)
GRUPO_TECH        = ["SMH","SOXX","IGV","MAGS","ARKF","ARKK","CIBR","SKYY","BOTZ","DRIV","QTUM"]  # tech e innovacion: chips, software, megacaps, fintech, innovacion, ciber, nube, robotica
GRUPO_LIMPIA      = ["TAN","ICLN","FAN","LIT","HYDR"]                               # energia limpia: solar, limpia global, eolica, baterias, hidrogeno
GRUPO_MATERIALES  = ["XME","GDX","COPX","URA","SIL","SLV","MOO"]                    # materiales y metales: mineria, oro, cobre, uranio, plata, agronegocio
GRUPO_IAINFRA     = ["GRID","PAVE","FIW","CGW"]                                     # infraestructura: red electrica, construccion, agua EE.UU., agua global
COMMODITIES = ["COPX","URA","LIT"]
GRUPO_INTERNAC = ["EEM","FXI","KWEB","EWG","EWP","EWJ","INDA","EWZ","VGK","EWY"]    # internacional: emergentes, China, Alemania, Espana, Japon, India, Brasil, Europa, Corea (chivato de semis)
GRUPO_REFUGIO  = ["UUP","TLT","HYG","GLD","IBIT","LQD","EMB"]                              # macro / refugio: dolar, bonos largos, credito HY/IG/emergente, oro
# === SINTETICOS: cestas fusionadas de sectores interconectados (suben y bajan juntos) ===
# Cada sintetico es un indice equiponderado de sus miembros -> UNA bolita en el RRG que resume el tema.
# Solo para LECTURA (RRG y monitor): no entran en scoring, cartera, candidato ni suelo.
# Diseño del RELOJ: 2 de ALTA BETA (donde está el dinero cuando el mercado paga),
# 2 DEFENSIVOS (el termómetro: cuando lideran, es aviso de liquidez — NO destino de compra)
# y 2 de PULSO (crédito y amplitud: los canarios que suelen avisar ANTES que el precio).
SINTETICOS = {
    "S-EXPLOSIVO": {"nombre": "Alta beta growth", "corto": "Sint. Explosivo",
                    "members": ["SMH", "XBI", "ARKK", "KWEB", "TAN"],
                    "desc": "chips + biotech + innovación + China tech + solar: la beta alta pura, donde el rebote paga"},
    "S-ALMACEN": {"nombre": "Almacenamiento (discos y SSD)", "corto": "Sint. Almacén",
                  "members": ["WDC", "STX", "SNDK"],
                  "desc": "Western Digital + Seagate + SanDisk: el dato que hay que GUARDAR, no el que se procesa. "
                          "No existe ETF de almacenamiento porque el sector entero son estas tres. Dentro de DRAM van "
                          "diluidas (ese fondo es 73% memoria coreana), asi que aqui se ve su pulso propio. "
                          "Historia distinta a la del HBM: el HBM lo mueve la demanda de aceleradores, esto lo mueve "
                          "el almacenamiento masivo en centros de datos"},
    "S-DUROS":  {"nombre": "Activos duros alta beta", "corto": "Sint. Duros",
                 "members": ["GDX", "SIL", "COPX", "URA", "IBIT"],
                 "desc": "mineras oro/plata + cobre + uranio + bitcoin: la base del patrón que clavó el suelo de oro/BTC/mineras"},
    "S-DEFENSA": {"nombre": "Defensivo puro", "corto": "Sint. Defensa",
                  "members": ["XLP", "XLU", "XLV"],
                  "desc": "básico + utilities + salud: cuando lidera, el dinero se esconde → AVISO de liquidez (no destino)"},
    "S-REFUGIO": {"nombre": "Huida a seguridad", "corto": "Sint. Refugio",
                  "members": ["GLD", "TLT", "UUP"],
                  "desc": "oro + bonos largos + dólar: si lidera junto a S-DEFENSA, el miedo es real"},
    "S-CREDITO": {"nombre": "Pulso del crédito", "corto": "Sint. Crédito",
                  "members": ["HYG", "LQD", "EMB"],
                  "desc": "high yield + IG + emergente: el crédito suele avisar ANTES que la bolsa; si se rompe, no hay suelo que valga"},
    "S-AMPLITUD": {"nombre": "Amplitud real", "corto": "Sint. Amplitud",
                   "members": ["RSP", "IWM"],
                   "desc": "S&P equiponderado + small caps: ¿sube el mercado o solo cuatro gigantes? La subida estrecha es frágil"},
    # === CASCADA DEL CAPEX DE IA: los eslabones por los que va bajando el dinero ===
    # Un euro de capex de un hiperescalador NO llega a todos a la vez: primero paga el chip, luego la
    # obra, luego la electricidad y al final la materia prima. Cada eslabon es un sintetico para poder
    # ver EN QUE PUNTO de la cadena esta el dinero hoy y hacia donde se mueve. "orden" = posicion en la
    # cadena (0 = quien paga, 1-4 = la cadena, 5 = el retorno). Solo LECTURA, como el resto.
    # EL CIRCULO SE CIERRA: C0 son los que SUELTAN el dinero y C5 los que tienen que DEVOLVERLO en
    # forma de ingresos. Si C5 se muere mientras C1-C4 vuelan, el capex no se esta monetizando — y
    # ese es el aviso temprano de que la cadena entera se puede cortar.
    # NOTA HONESTA: falta el eslabon de EQUIPOS (ASML/LRCX/AMAT). No hay ETF de equipos semi en tu
    # universo UCITS, asi que habria que montarlo con acciones sueltas, al estilo del sintetico FIW.
    "C0-HIPER": {"nombre": "Cascada 0 · Hiperescaladores", "corto": "C0 Hiper", "grupo": "cascada", "orden": 0,
                 "members": ["MAGS"],
                 "desc": "quien SUELTA el dinero: megacaps que financian el capex. Proxy imperfecto (MAGS lleva también nombres que no son hiperescaladores)"},
    "CE-EQUIPOS": {"nombre": "Cascada 1b · Equipos", "corto": "C1b Equipos", "grupo": "cascada", "orden": 1.5,
                   "members": ["ASML", "LRCX", "AMAT", "KLAC"],
                   "desc": "las MAQUINAS que fabrican el chip (litografia, grabado, deposicion, metrologia). "
                           "Cobran ANTES que nadie, cuando la fabrica se decide a ampliar, asi que suelen girarse "
                           "primero cuando el capex se recorta. Era el eslabon que faltaba en la cascada: no hay ETF "
                           "de equipos semi en universo UCITS, por eso va como cesta de acciones sueltas"},
    "C1-SILICIO": {"nombre": "Cascada 1 · Silicio", "corto": "C1 Silicio", "grupo": "cascada", "orden": 1,
                   "members": ["SMH", "SOXX", "DRAM"],
                   "desc": "chips y memoria: el primer eslabón, se cobra al firmar el pedido. DRAM (memoria/HBM) es hoy el cuello de botella real del capex, más que la lógica"},
    "C2-OBRA": {"nombre": "Cascada 2 · Obra y red", "corto": "C2 Obra", "grupo": "cascada", "orden": 2,
                "members": ["PAVE", "GRID", "FIW", "CGW"],
                "desc": "construcción, red eléctrica, agua y refrigeración del centro de datos"},
    "C3-ENERGIA": {"nombre": "Cascada 3 · Energía", "corto": "C3 Energía", "grupo": "cascada", "orden": 3,
                   "members": ["XLU", "URA", "XLE"],
                   "desc": "la electricidad que se lo come todo: utilities, uranio y energía"},
    "C4-MATERIA": {"nombre": "Cascada 4 · Materia prima", "corto": "C4 Materia", "grupo": "cascada", "orden": 4,
                   "members": ["COPX", "XME", "SIL", "SLV"],
                   "desc": "cobre, metales y plata: el último eslabón y el de MAYOR beta (apalancamiento operativo de las mineras)"},
    "C5-RETORNO": {"nombre": "Cascada 5 · Retorno (software)", "corto": "C5 Retorno", "grupo": "cascada", "orden": 5,
                   "members": ["SKYY", "IGV", "CIBR", "NCLD"],
                   "desc": "quien tiene que DEVOLVER el dinero: nube y software que venden el servicio. Si esto no tira, el capex no se monetiza"},
}
CARTERA_PESO_MAX = 34   # tope de % por posicion en la cartera semanal; lo que no se reparte va a LIQUIDEZ
# --- SECTORES EXPLOSIVOS: los que mas se mueven cuando rebotan (beta alta). El modo cazador de suelos
#     vigila SOLO estos tras una caida fuerte, para entrar en el giro en vez de estar siempre invertido. ---
SECTORES_EXPLOSIVOS = ["SMH", "SOXX", "XBI", "ARKK", "ARKF", "KWEB", "FXI", "XME", "COPX", "GDX",
                       "URA", "SLV", "TAN", "IBIT", "QTUM", "LABU", "MAGS", "IGV", "KRE", "TNA", "ARKX", "SIL",
                       "XOP", "OIH", "LIT", "UFO"]
# etiqueta legible del "porque son explosivos"
EXPLOSIVO_TIPO = {
    "SMH": "chips",
    "DRAM": "memoria/HBM",
    "NCLD": "neocloud", "SOXX": "chips", "MAGS": "megacaps tech", "IGV": "software", "QTUM": "cuántica",
    "ARKK": "innovación", "ARKF": "fintech", "XBI": "biotech", "LABU": "biotech x3",
    "KWEB": "China tech", "FXI": "China", "XME": "metales", "COPX": "cobre", "GDX": "oro mineras",
    "URA": "uranio", "SLV": "plata", "TAN": "solar", "IBIT": "bitcoin", "KRE": "banca regional", "TNA": "small caps x3",
    "ARKX": "espacio", "UFO": "espacio puro", "SIL": "plata mineras",
    "XOP": "petróleo E&P", "OIH": "serv. petroleros", "LIT": "litio/baterías",
}
# --- MESAS DE PÓKER (pestaña PRO): cada mesa = un tema explosivo con su análisis de rebote completo
#     (Wilson 95%, Kelly, cubos históricos). prefs = orden de preferencia del ETF; lead_keys = de qué
#     ETF tomar el desglose de acciones para el washout (solo los que tienen SECTOR_STOCKS). ---
DESKS_POKER = [
    {"id": "SEMIS", "emoji": "🎰", "titulo": "SEMIS DESK", "prefs": ["SMH", "SOXX"], "lead_keys": ["SMH"],
     "veh": "el rebote se juega LARGO (SMH contado; SOXL solo con mano fuerte y stop) — <b style='color:#FF5252'>SOXS es la apuesta CONTRARIA</b>: si esperas rebote y tienes SOXS, estás contra tu propia mano y su decay −3x te cobra cada día",
     "riesgo": "Semis es el sector más noticioso (Corea, aranceles, resultados NVDA): el gap te puede saltar el stop. Tamaño pequeño SIEMPRE"},
    {"id": "MATERIALES", "emoji": "⛏️", "titulo": "MATERIALES DESK", "prefs": ["XME", "XLB"], "lead_keys": ["XLB"],
     "veh": "el rebote se juega LARGO y en contado (XME es el músculo minero de beta alta; XLB la versión tranquila). Sin par apalancado limpio en tu universo: si quieres beta extra, sube tamaño DENTRO del límite, no apalances",
     "riesgo": "Materiales baila con el dólar y con China: un UUP fuerte o un dato chino malo aborta el rebote aunque el patrón fuera perfecto. Cruza siempre con S-DUROS y FXI"},
    {"id": "BIOTECH", "emoji": "🧬", "titulo": "BIOTECH DESK", "prefs": ["XBI"], "lead_keys": ["XBI"],
     "veh": "el rebote se juega LARGO (XBI contado; LABU 3x solo con mano muy fuerte y stop — su decay diario es de los peores del mercado)",
     "riesgo": "Biotech es binario por naturaleza (FDA, ensayos, M&A): las acciones hacen ±30% en un día y el ETF amortigua pero no inmuniza. El gap te puede saltar el stop: tamaño pequeño SIEMPRE"},
    {"id": "ENERGIA", "emoji": "🛢️", "titulo": "ENERGÍA DESK", "prefs": ["XOP", "XLE"], "lead_keys": ["XLE"],
     "veh": "el rebote se juega LARGO y en contado (XOP es el músculo E&P de beta alta; XLE la versión integrada tranquila; OIH el derivado de servicios, aún más nervioso)",
     "riesgo": "Energía baila con el crudo y la OPEP: un titular de producción o inventarios aborta el patrón aunque fuera perfecto. Cruza con el dólar (UUP fuerte = viento en contra)"},
    {"id": "MINERAS", "emoji": "⚒️", "titulo": "MINERAS DESK", "prefs": ["GDX", "SIL"], "lead_keys": ["XLB"],
     "veh": "el rebote se juega LARGO y en contado (GDX = beta sobre el oro, SIL sobre la plata: amplifican al metal en AMBOS sentidos)",
     "riesgo": "Si GLD/SLV corrigen, las mineras caen el doble — vigila S-DUROS y el dólar. Y tu regla aquí ya demostrada: el suelo de oro/BTC/mineras se compró con el patrón, no con la noticia"},
    {"id": "COBRE", "emoji": "🟠", "titulo": "COBRE DESK", "prefs": ["COPX", "XME"], "lead_keys": ["XLB"],
     "veh": "el rebote se juega LARGO y en contado (COPX = mineras de cobre puras, beta alta sobre el precio del cobre; XME la versión más diversificada de metales si COPX no tiene mano). Sin par apalancado limpio en tu universo: si quieres beta extra, sube tamaño DENTRO del límite, no apalances",
     "riesgo": "El cobre es el termómetro del ciclo industrial global: baila con China (mayor consumidor del planeta), el dólar y los datos macro. Un dato chino flojo o un dólar fuerte aborta el rebote aunque el patrón fuera perfecto. Cruza siempre con FXI y S-DUROS"},
    {"id": "ESPACIO", "emoji": "🚀", "titulo": "ESPACIO DESK", "prefs": ["ARKX", "UFO", "ITA"], "lead_keys": ["ITA"],
     "veh": "el rebote se juega LARGO y en contado (ARKX y UFO son los pure-play — UFO sigue un indice de espacio y es mas puro, pero es un ETF pequeno: menos liquidez y horquillas mas anchas; ITA el primo defensa con contratos gubernamentales). Historia corta del ETF: los cubos tienen menos muestra, fíate más del IC ancho que del % central",
     "riesgo": "Espacio es tema de flujos minoristas y noticias de lanzamientos (RKLB, ASTS…): movimientos de +/−10% en días. El tamaño manda y el stop es sagrado"},
]
# --- DIX (Dark Index, SqueezeMetrics): % comprador en dark pools sobre el S&P 500. Dato de MERCADO
#     (no por sector), diario con 1 día de retraso. DIX alto en plena caída = acumulación institucional
#     oculta → confirmador del CENTINELA para el modo ACECHO/REENTRADA. Si la web no responde, el
#     terminal sigue sin él (no es crítico). ---
DIX_ON = True
DIX_URL = "https://squeezemetrics.com/monitor/static/DIX.csv"
# --- CENTINELA: umbrales del reloj de régimen (spread = ratio RRG medio de alta beta − defensivos) ---
CENTINELA_SPREAD_ON = 0.8        # spread por encima → el dinero está en alta beta (RISK-ON)
CENTINELA_SPREAD_OFF = -0.8      # spread por debajo → liderazgo defensivo (LIQUIDEZ)
CENTINELA_CAIDA_3S = -0.8        # caída del spread en 3 semanas que dispara el aviso de DISTRIBUCIÓN
# --- CLIMA (🟡 clímax / 🟣 capitulación): vela diaria anómala vs la volatilidad típica del propio ETF ---
CLIMA_VENTANA = 3                # sesiones hacia atrás que se revisan (si el petardazo fue el lunes y ejecutas el miércoles, se sigue marcando)
CLIMA_Z = 2.2                    # umbral: |retorno del día| >= 2.2× su desviación típica diaria (60 sesiones previas a ese día)
CLIMA_VOL_FUERTE = 1.3           # si además el volumen de ese día fue >= 1.3× su media de 20, se anota "con volumen" (señal más fiable)
# --- FLUJO NOCTURNO (🌏 acumulación extranjera): para los internacionales, la compra de verdad ocurre en su
#     bolsa local (Hong Kong, Tokio...) y el ETF americano abre ya subido de gap. El CMF solo mide la sesión USA,
#     así que puede decir "sale dinero" mientras el activo acumula en Asia — el punto ciego que ocultó a China. ---
FLUJO_NOCTURNO_SYMS = set(GRUPO_INTERNAC) | {"IBIT"}   # también IBIT: bitcoin cotiza 24h y el gap manda
FLUJO_NOCTURNO_MIN = 2.0         # gap acumulado de 20 sesiones (en %) a partir del cual se marca acumulación extranjera
                        # (regla anti-anomalia: si el filtro de flujo deja 1-2 supervivientes, no les cae el 100%)
# --- Chequeo de COHERENCIA SECTORIAL: si un ETF entra en cartera por su fuerza como bloque pero su
#     tema dominante esta DEBILITANDOSE/REZAGADO en el mercado US, se avisa (no se veta: tu decides).
#     Mapa: ETF -> (tema legible, [ETFs-US espejo de ese tema]). Solo para internacionales/tematicos. ---
COHERENCIA_TEMA = {
    "EWY":  ("semiconductores", ["SMH", "SOXX"]),          # Corea = Samsung + SK Hynix (chivato de semis)
    "EWT":  ("semiconductores", ["SMH", "SOXX"]),          # Taiwan = TSMC (por si se anade)
    "EEM":  ("semis + China", ["SMH", "SOXX", "KWEB"]),    # Emergentes = TSMC + Tencent + Samsung: NO es apuesta EM pura, es semis+China disfrazada
    "INDA": ("tecnología", ["XLK", "IGV"]),                # India = mucho IT services
    "KWEB": ("tecnología china", ["XLK"]),
    "FXI":  ("financiero/China", ["XLF"]),
    "EWG":  ("industrial", ["XLI"]),                        # Alemania = industria/autos
    "EWJ":  ("financiero/industrial", ["XLF", "XLI"]),     # Japon = value, no tech
    "EWP":  ("financiero", ["XLF"]),                        # Espana = bancos
    "VGK":  ("financiero/industrial", ["XLF", "XLI"]),
    "EWZ":  ("materiales/energía", ["XME", "XLE"]),         # Brasil = commodities
    "SMH":  ("semiconductores", ["SMH"]),
    "SOXX": ("semiconductores", ["SMH"]),
    "IGV":  ("software", ["IGV"]),
    "DRIV": ("automoción/tech", ["XLK", "XLY"]),
    "QTUM": ("tecnología", ["XLK"]),
}
GRUPO = {}
for _s in GRUPO_SECTORES:    GRUPO[_s] = "sector"
for _s in GRUPO_SUBSECTORES: GRUPO[_s] = "subsector"
for _s in GRUPO_TECH:        GRUPO[_s] = "tech"
for _s in GRUPO_LIMPIA:      GRUPO[_s] = "limpia"
for _s in GRUPO_MATERIALES:  GRUPO[_s] = "materiales"
for _s in GRUPO_IAINFRA:     GRUPO[_s] = "iainfra"
for _s in GRUPO_INTERNAC:    GRUPO[_s] = "internac"
for _s in GRUPO_REFUGIO:     GRUPO[_s] = "refugio"
for _s in SINTETICOS:        GRUPO[_s] = SINTETICOS[_s].get("grupo", "sintetico")
GRUPO_NOMBRE = {"sector": "Sectores", "subsector": "Subsectores EE.UU.", "tech": "Tech e innovación", "limpia": "Energía limpia", "materiales": "Materiales y metales", "iainfra": "IA infraestructura", "internac": "Internacional", "refugio": "Macro / refugio", "sintetico": "Sintéticos", "cascada": "Cascada IA"}
GRUPO_ORDEN = ("sector", "subsector", "tech", "limpia", "materiales", "iainfra", "internac", "refugio", "sintetico", "cascada")

# Clasificacion en 3 grupos para los paneles (selector del RRG y bloques de las tablas)
GROUPS = {
    "sector":        ["XLK","XLF","XLE","XLV","XLY","XLP","XLI","XLB","XLU","XLRE","XLC","IWM","DIA"],
    "subsector":     ["SMH","SOXX","IGV","XBI","KRE","JETS","ITB","MAGS","ITA","DRAM","NCLD"],
    "internacional": ["EEM","FXI","KWEB","EWG","EWP","TLT","HYG","UUP","GLD","GDX","COPX","URA","LIT","IBIT"],
}
GROUP_LABEL = {"sector": "Sectores", "subsector": "Subsectores EE.UU.", "internacional": "Internacional y macro"}
GROUP_OF = {t: g for g, lst in GROUPS.items() for t in lst}
def group_of(sym):
    return GROUP_OF.get(sym, "subsector")
WEEKS = 70                                       # semanas de historico a usar
TAIL = 8                                         # longitud de la estela del RRG
RRG_SOLO_SECTORES = False                        # True = en el RRG solo los 11 sectores SPDR (mas limpio)
TOPUP_YAHOO = True                               # rellenar la ultima barra que falte con Yahoo (frescura); util en local, en la nube puede limitar
DATA_PRIMARY = "yahoo"                            # fuente principal: "yahoo" (mas fresco; Stooq no responde en algunas IPs/regiones) o "stooq". La otra queda de respaldo
# --- Acciones lideres por sector (fuerza relativa estilo RS Rating 1-99) ---
STOCK_LEADERS = True                             # añade el panel de acciones lideres (descarga mas datos)
LEADERS_TOP_N = 6                                # cuantas acciones mostrar por sector
LEADERS_MIN_RS = 90                              # umbral de "lider" (percentil)
# Universo para calcular el percentil RS:
#   "sp500"  = las ~500 del S&P 500 (percentil de mercado real; mas lento; por defecto)
#   "sector" = ~164 acciones de SECTOR_STOCKS (mas rapido)
RS_UNIVERSE = "sp500"
MCC_UMBRAL = -100.0                             # umbral del oscilador de amplitud (el clasico del NYSE)
MCC_CONFIRMACIONES = 2                          # cierres por encima del umbral que confirman la senal
SP500_FALLBACK = ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","GOOG","AVGO","TSLA","BRK-B","JPM","LLY","V",
    "UNH","XOM","MA","COST","HD","PG","JNJ","ORCL","ABBV","NFLX","BAC","KO","CRM","CVX","MRK","AMD","PEP",
    "TMO","WFC","ADBE","LIN","CSCO","ACN","MCD","ABT","DHR","GE","TXN","DIS","INTU","QCOM","CAT","VZ","AMGN",
    "PM","IBM","NOW","CMCSA","UNP","SPGI","RTX","PFE","HON","GS","LOW","T","COP","ISRG","BKNG","NEE","UBER",
    "MS","BLK","AXP","SCHW","ETN","C","TJX","ADP","DE","BSX","MDT","GILD","LMT","SYK","VRTX","REGN","CB",
    "MU","PLD","ADI","MMC","SBUX","PANW","BA","SO","AMAT","KLAC","LRCX","DUK","CEG","SHW","ICE","WM","ANET",
    "CRWD","CDNS","SNPS","MRVL","NKE","FCX","NEM","CL","TGT","ORLY","CMG","MCO","APH","FTNT","WELL","EQIX",
    "AON","CME","PNC","USB","TFC","COF","AIG","MET","PRU","AFL","ALL","TRV","BK","ITW","TT","CMI","ROP","CARR",
    "OTIS","GEV","PCAR","PWR","AME","FAST","ODFL","CTAS","RSG","VRSK","EFX","URI","NSC","EMR","GD","FDX","PH",
    "MDLZ","MO","STZ","SYY","KR","ADM","HSY","KDP","MNST","CHD","CLX","K","MKC","TAP","HRL","KMB","GIS","KHC",
    "VLO","MPC","PSX","OXY","KMI","DVN","OKE","HAL","BKR","FANG","TRGP","WMB","SLB","EOG","CTRA","EQT",
    "ELV","CI","HUM","CNC","MOH","CVS","BDX","EW","ZBH","BAX","DXCM","IDXX","IQV","A","MTD","WAT","HOLX","ALGN",
    "STE","RVTY","COO","ZTS","DGX","LH","WST","TFX","HSIC","XRAY","MRNA","BIIB","INCY","RMD","BMY","GEHC",
    "GM","F","ROST","YUM","HLT","AZO","RCL","CCL","NCLH","DHI","LEN","NVR","PHM","MGM","LVS","WYNN","APTV",
    "LULU","TSCO","DRI","DPZ","GRMN","EXPE","POOL","BBY","ULTA","KMX","DECK","RL","TPR","WHR","MHK","MAR",
    "EA","TTWO","WBD","OMC","IPG","LYV","FOXA","FOX","NWSA","MTCH","PARA","CHTR","TMUS","CMCSA","VZ","DIS",
    "INTC","TXN","QCOM","AMAT","MCHP","MPWR","ON","GLW","HPQ","HPE","DELL","WDC","STX","NTAP","KEYS","CDW",
    "TYL","FSLR","ENPH","TER","SWKS","QRVO","ZBRA","TRMB","PTC","ANSS","AKAM","JNPR","FFIV","GEN","NXPI",
    "BRK-B","SPG","DLR","O","PSA","CCI","VICI","EXR","AVB","EQR","INVH","MAA","ESS","UDR","ARE","VTR","DOC",
    "IRM","SBAC","REG","KIM","FRT","HST","CPT","BXP","AMT",
    "VMC","MLM","PPG","ALB","IFF","IP","PKG","AVY","BALL","AMCR","CF","MOS","FMC","EMN","CE","LYB","STLD","NUE",
    "DOW","DD","CTVA","APD","ECL",
    "D","VST","SRE","EXC","XEL","ED","PEG","WEC","ES","AEE","DTE","PPL","FE","CMS","CNP","ATO","NI","LNT",
    "EVRG","AES","PNW","NRG","AEP",
    "GD","NOC","FDX","UPS","CSX","ADP","EMR","TT","CMI","ROP","PAYX","BR","EXPD","CHRW","DAL","UAL","LUV",
    "TDG","GWW","JCI","PNR","ALLE","NDSN","ROK","SNA","SWK","TXT","MAS","BLDR","AXON","LHX","LDOS","J","DOV","XYL","IR",
    "AMP","TROW","BEN","IVZ","WTW","ACGL","HIG","CINF","L","NDAQ","MKTX","CBOE","FIS","FI","GPN","PYPL","SYF","DFS",
    "FITB","HBAN","RF","CFG","KEY","MTB","NTRS","STT","PFG","PGR","AFL"]
SECTOR_STOCKS = {
    "XLK":  ["AAPL","MSFT","NVDA","AVGO","ORCL","CRM","AMD","ADBE","ACN","CSCO","INTC","IBM","QCOM","NOW","TXN"],
    "XLF":  ["BRK-B","JPM","V","MA","BAC","WFC","GS","AXP","MS","SPGI","BLK","C","SCHW","CB","PGR"],
    "XLE":  ["XOM","CVX","COP","SLB","EOG","MPC","PSX","WMB","OXY","VLO","KMI","DVN"],
    "XLV":  ["LLY","UNH","JNJ","ABBV","MRK","TMO","ABT","ISRG","DHR","PFE","AMGN","BMY","GILD","VRTX","CVS"],
    "XLY":  ["AMZN","TSLA","HD","MCD","BKNG","LOW","NKE","SBUX","TJX","CMG","ORLY","MAR","GM","F"],
    "XLP":  ["COST","WMT","PG","KO","PEP","PM","MDLZ","CL","MO","TGT","KMB","GIS","KHC"],
    "XLI":  ["GE","CAT","RTX","HON","UNP","BA","DE","UBER","ETN","LMT","UPS","ADP","NOC","CSX","EMR"],
    "XLB":  ["LIN","SHW","FCX","ECL","NEM","APD","CTVA","DOW","NUE","DD","VMC","MLM"],
    "XLU":  ["NEE","SO","DUK","CEG","AEP","D","VST","SRE","EXC","XEL","ED","PEG"],
    "XLRE": ["PLD","AMT","EQIX","WELL","SPG","DLR","O","PSA","CCI","CBRE","VICI","EXR"],
    "XLC":  ["META","GOOGL","NFLX","DIS","TMUS","T","VZ","CMCSA","CHTR","EA","TTWO","WBD"],
    "SMH":  ["NVDA","AVGO","AMD","QCOM","TXN","MU","LRCX","AMAT","KLAC","ADI","MRVL","NXPI"],
    "IGV":  ["MSFT","ORCL","CRM","NOW","ADBE","PANW","CRWD","INTU","SNPS","CDNS","FTNT","WDAY","DDOG","TEAM"],
    "FIW":  ["AWK","ROP","XYL","WAT","FERG","A","VLTO","PNR","MLI","IDXX","ECL","IEX","J","MAS","WMS","STN","CNM","WTS","ACM","TTEK","BMI","ITRI","FELE","MWA","ZWS"],
    "XBI":  ["VRTX","REGN","GILD","ALNY","EXEL","UTHR","INSM","NBIX","ARWR","BEAM","ALKS","TGTX","KRYS","INCY","IONS","BMRN","SRPT","HALO"],
    "KRE":  ["TFC","FITB","RF","HBAN","KEY","CFG","MTB","WBS","ZION","EWBC","WAL","FHN","CFR","ONB","PB"],
    "JETS": ["DAL","UAL","AAL","LUV","ALK","SKYW","ALGT","JBLU","BA","BKNG","EXPE","ABNB"],
    "ITB":  ["DHI","LEN","NVR","PHM","TOL","KBH","MTH","TMHC","BLDR","SHW","MAS","LOW","HD","MHK"],
    "ITA":  ["RTX","BA","LMT","GD","NOC","GE","TDG","LHX","HWM","AXON","HEI","TXT","CW","HII","LDOS"],
    # Red electrica (GRID): grandes de referencia + las pequenas/medianas del tema (POWL, AMSC, MYRG, ITRI, IESC, PRIM, AZZ)
    "GRID": ["ETN","PWR","VRT","HUBB","NVT","GNRC","ITRI","AMSC","POWL","MYRG","PRIM","IESC","AZZ"],
}
FRED_API_KEY = ""                                # DEJAR VACIO: la key va en los Secrets de GitHub (FRED_API_KEY), NO aqui (repo publico)
ISM_MANUAL = 54.0                                # ISM manufacturas (no esta limpio en FRED gratis): actualizalo a mano el 1er dia habil de cada mes. Ult.: 54.0 (mayo-2026)
# --- Analisis con IA (opcional): comentario automatico en el panel ---
# --- EVENTOS PUNTUALES con fecha (editable): se pintan en la pestaña News. Formato ("YYYY-MM-DD", "texto") ---
EVENTOS_MERCADO = [
    ("2026-07-27", "Kimi K3 (Moonshot): publicación de PESOS ABIERTOS — hasta hoy todo benchmark es autoinformado; verificación independiente desde esta fecha. Confirma → presión extra en SMH/SOXX/EEM/EWY e IBIT; decepciona → rally de alivio en semis justo al cierre de la ventana τ"),
]

ANTHROPIC_API_KEY = ""                           # opcional: https://console.anthropic.com (de pago por uso)
AI_MODEL = "claude-haiku-4-5"                    # modelo del comentario corto (editable segun tu cuenta)
# --- IA AUTOMATICA en Modo Claude: al ejecutar el terminal, se lanza el prompt MAESTRO con tus datos ---
IA_AUTO = True                                   # ejecutar automaticamente el prompt maestro en cada build (si hay API key)
IA_AUTO_EXTRA = ["news"]   # ademas del maestro "resumen", se auto-ejecuta "news" (pestana News). Anade mas si quieres (cada uno suma coste)  # TODOS los prompts se auto-ejecutan (deja [] para solo el maestro; cada uno suma tiempo y coste)
IA_AUTO_MODEL = "claude-sonnet-4-6"              # modelo del analisis largo. Alternativas: "claude-opus-4-6" (mejor y mas caro), "claude-haiku-4-5" (mas barato)
IA_WEB_SEARCH = True                             # permitir a la IA buscar en la web (13F, VIX, earnings...); suma coste por busqueda
IA_MAX_TOKENS = 2000                             # longitud maxima de cada respuesta
# --- Proveedor de la IA automatica ---
# "anthropic"     -> API de Anthropic (pago por uso, la unica con busqueda web integrada aqui)
# "openai_compat" -> CUALQUIER API compatible OpenAI: Gemini (tier GRATUITO), DeepSeek, OpenRouter, Groq...
#                    Ejemplo Gemini gratis: key gratuita en https://aistudio.google.com/apikey
IA_PROVIDER = "anthropic"                        # PRECONFIGURADO en Anthropic (pago por uso, con busqueda web en vivo). Solo falta tu key en anthropic_key.txt
IA_COMPAT_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"   # URL base del proveedor compatible
IA_COMPAT_MODEL = "gemini-2.0-flash"                                          # modelo del proveedor compatible
IA_COMPAT_KEY = ""                               # key del proveedor compatible (o variable de entorno IA_COMPAT_KEY)
# --- Biblioteca de prompts (los 9 de Pedro): el maestro se auto-ejecuta; el resto, copiables o via IA_AUTO_EXTRA ---
IA_PROMPTS = [
    ("resumen", "🧑‍🏫 RESUMEN PARA HUMANOS (el maestro diario)",
     "Eres mi analista de confianza y me lo explicas TODO en lenguaje muy sencillo, como a un amigo listo que NO sabe de finanzas. "
     "Con los datos de mi terminal que van debajo, escribe un resumen corto y claro con esta estructura EXACTA, sin tecnicismos "
     "(si usas una palabra financiera, explicala entre parentesis con palabras normales):\n"
     "1) COMO ESTA EL MERCADO HOY - dos frases: hay que tener miedo o tranquilidad, y el dinero entra o sale en general.\n"
     "2) MIS POSICIONES, UNA A UNA - para cada ETF de mi cartera: sigo dentro o me salgo, una frase cada uno.\n"
     "3) LO MEJOR PARA ESTA SEMANA - las 2-3 oportunidades mas claras y por que, sin jerga.\n"
     "4) LO QUE DEBO EVITAR - que NO tocar y por que, una linea cada cosa.\n"
     "5) EL PELIGRO DE LA SEMANA - la unica cosa que mas podria estropear mis inversiones, y que vigilar.\n"
     "6) QUE HACER EL LUNES - pasos concretos, como una lista de la compra.\n"
     "Reglas: maximo una carilla. Nada de tablas. Frases cortas. Si mi terminal y tu no coincidis, dilo claro. "
     "Recuerda mi norma: el dinero que se mueve manda sobre las historias bonitas. Cierra con una frase de animo realista. No es asesoramiento; yo decido."),
    ("news", "📰 News — solo lo que mueve TUS posiciones",
     "Eres el filtro de noticias de un inversor de rotacion sectorial. Busca en la web SOLO los 6-8 catalizadores CON FECHA "
     "de las proximas 2 semanas que puedan mover de verdad este universo: semiconductores (SMH/SOXX), biotech (XBI), banca regional (KRE), "
     "financieras (XLF), retail (XRT), salud (XLV), energia (XLE/XOP), oro y mineras (GLD/GDX), bitcoin (IBIT), China/emergentes (KWEB/FXI/EEM), "
     "Alemania (EWG/DAX). Incluye: FOMC y datos macro clave, resultados de empresas que arrastran a esos ETFs (megacaps, semis, bancos regionales, "
     "mineras grandes), decisiones regulatorias o geopoliticas con fecha. Para CADA una: fecha exacta, que es, que ETF(s) toca y en que direccion, "
     "y el escenario que la invalidaria. PROHIBIDO: opiniones de analistas, price targets, rumores sin fecha, noticias ya cotizadas. "
     "Ordena por fecha. Cierra con una linea: LA NOTICIA MAS PELIGROSA DE LA SEMANA y por que."),
    ("sectorial", "🕰 Rotación sectorial — 30 años de precursores",
     "Analiza los últimos 30 años y encuentra qué indicadores (tipos de interés, inflación, ISM, PMI, curva de tipos, desempleo, beneficios empresariales, dólar y petróleo) han anticipado las rotaciones entre tecnología, financieras, industriales, energía, consumo, salud y utilities."),
    ("flujos", "💸 Flujos institucionales",
     "Detecta qué sectores están recibiendo entradas de dinero institucional durante las últimas cuatro semanas comparándolo con los últimos cinco años."),
    ("liderazgo", "🏁 Liderazgo antes de que se vea",
     "¿Qué industrias están mostrando fortaleza relativa frente al S&P 500 antes de que el mercado general las reconozca?"),
    ("ocultas", "🕵️ Rotaciones ocultas",
     "Busca acciones que estén rompiendo máximos de 52 semanas mientras el sector todavía no aparece entre los mejores del S&P 500."),
    ("ciclo", "🕐 Ciclo económico",
     "Según los datos macro actuales, ¿en qué fase del ciclo económico está Estados Unidos y qué sectores suelen liderar históricamente esa fase?"),
    ("insiders", "🐋 Insiders y grandes fondos",
     "Cruza compras de insiders, posiciones de hedge funds y cambios en las carteras de Berkshire Hathaway, Bridgewater, Pershing Square y otros grandes gestores para detectar posibles rotaciones."),
    ("narrativas", "🗣 Narrativas emergentes",
     "¿Qué temas empiezan a aparecer cada vez más en las conferencias de resultados (earnings calls) antes de que el mercado los descuente?"),
    ("multifactor", "🧮 Ranking multifactor",
     "Construye un ranking semanal de sectores utilizando fortaleza relativa, beneficios revisados al alza, momentum, volumen institucional y valoración."),
    ("gestor", "🎖 GESTOR DE HEDGE FUND MACRO (el maestro)",
     "Actúa como un gestor de un hedge fund macro. Analiza diariamente datos macroeconómicos de EE. UU., flujos institucionales, fortaleza relativa de sectores, revisiones de beneficios, mercado de bonos, dólar, VIX, materias primas y amplitud de mercado. Identifica qué sectores tienen mayor probabilidad de liderar durante las próximas 2 a 8 semanas y explica por qué. Asigna una probabilidad a cada escenario y señala qué datos invalidarían esa hipótesis."),
]

def ia_data_block(snap, fecha):
    """Bloque de datos + reglas de la casa que se inyecta a CADA prompt (auto o copiado)."""
    return ("\n\n=== DATOS DE MI TERMINAL PeVR (cierre " + str(fecha) + ") ===\n" + str(snap) +
            "\n\nInstrucciones: usa estos datos de mi terminal como base primaria (RRG, flujo CMF/OBV, scoring, régimen). "
            "Si el prompt necesita datos que NO están aquí (13F, insiders, earnings calls, VIX, revisiones de beneficios, series de 30 años), "
            "búscalos en la web y cita la fuente de cada dato. Cuando mi terminal y tu análisis diverjan, señálalo explícitamente: "
            "mi regla es que el flujo confirma y la narrativa propone. Sé concreto y accionable, con probabilidades cuando sea posible, "
            "y termina siempre con qué datos invalidarían tu conclusión. No es asesoramiento; yo decido.")
# --- Avisos automaticos (opcional). Rellena uno de los dos ---
TELEGRAM_TOKEN = ""                              # token del bot de Telegram (via @BotFather)
TELEGRAM_CHAT_ID = ""                            # tu chat id (via @userinfobot)
WEBHOOK_URL = ""                                 # alternativa: webhook de Discord/Slack
# (en GitHub se pueden poner como Secrets; ver README)
BACKTEST = True                                  # calcular el backtest de la estrategia
# --- Optimizaciones de la estrategia ---
TREND_FILTER = True                              # solo invertir si el S&P > su media de 40 semanas (~200d); si no, liquidez
TREND_MA_WEEKS = 40                              # media para el filtro de tendencia del mercado
MAX_POSICIONES = 7                               # tope de posiciones (las N de mayor impulso); 0 = sin tope -> prioriza los subsectores fuertes
PESO = "volatilidad"                             # reparto: "igual" | "volatilidad" (inversa, mas a lo estable) | "impulso"
BUFFER = 1.0                                     # histeresis: entra si fuerza>100+BUFFER y sale si <100-BUFFER (menos latigazos)
# --- Plan de liquidez / entrada escalonada (guia: caidas del S&P 500 desde maximos) ---
CASH_PLAN = [(5, 30), (10, 30), (20, 40)]        # (caida % desde maximo, % de cartera a desplegar)
DD_THRESHOLDS = [2.5, 5, 10, 20]                 # umbrales para la tabla de caidas
DD_GAP_PP = 0.5                                   # los cubos grandes (>=10%) saltan a partir de (umbral - esto): capta el hueco nocturno del futuro/CFD que el SPY no registra en su sesion de contado (p.ej. -10% salta a partir de -9.5%)
CARTERA_CAPITAL = 1000                           # € a repartir en la "cartera de la semana" (Lider+Mejorando)
CARTERA_DUAL_MOMENTUM = True                     # la cartera exige tambien momentum ABSOLUTO positivo (no entra en lo que sube vs S&P pero pierde dinero)
# --- ETFs apalancados (Direxion, salvo nota); para la "via apalancada" de la pantalla Operativa ---
# Verificado 24-jun-2026. OJO: decay diario en mercados laterales = su mayor riesgo. Verifica disponibilidad en tu broker.
LEVERAGED = {
    "XLK": ("TECL", "x3"), "XLF": ("FAS", "x3"), "XLE": ("ERX", "x2"), "XLV": ("CURE", "x3"),
    "XLY": ("WANT", "x3"), "XLI": ("DUSL", "x3"), "XLU": ("UTSL", "x3"), "XLRE": ("DRN", "x3"),
    "SMH": ("SOXL", "x3"), "SOXX": ("SOXL", "x3"), "XBI": ("LABU", "x3"), "KRE": ("DPST", "x3"),
    "ITB": ("NAIL", "x3"), "ITA": ("DFEN", "x3"), "JETS": ("TPOR", "x3"), "GDX": ("NUGT", "x2"),
    "FXI": ("YINN", "x3"), "IWM": ("TNA", "x3"),
}
# --- Cesto sintetico (pantalla Operativa): las mas fuertes NO extendidas de cada subsector en compra ---
SINT_MIN_RS = 50      # percentil minimo de fuerza relativa para entrar al cesto
SINT_MAX_HI = 90      # % del maximo de 52s por encima del cual se considera "extendida" (fuera del cesto)
SINT_TOP = 5          # tope de acciones en el cesto
SINT_MIN_N = 2        # si pasan menos de estas, avisa (cesto demasiado fino)
CARTERA_SCORE_MIN = 3                            # la cartera no entra en ETFs con scoring < este valor (0 = desactivado). 3 = fuera solo los "evitar" (<=2); 4 = solo "comprar" (estricto, muy concentrado). La distribución oculta SIEMPRE se excluye aparte.
CARTERA_AVISA_TENDENCIA = True                   # True = la cartera NO expulsa a los que están bajo su media de 40 semanas, pero les pone una etiqueta de aviso "⚠ rebote bajo tendencia, mira el gráfico" (tú decides con el gráfico). False = sin aviso.
CARTERA_LIDER_PRIMERO = True                      # True = la cartera prioriza los LÍDER (flujo confirmado) antes que los MEJORANDO, y dentro de cada grupo ordena por impulso. Evita que un rebote acelerado (Mejorando) le quite el sitio a un líder confirmado. False = ordena solo por impulso (puede colar rebotes por delante de líderes).
SALIDA_MA_SEMANAS = 10                            # media móvil semanal para la señal de SALIDA (stop de tendencia). 10 = rápida (protege más plusvalía, algún latigazo) · 20 = media · 30 = lenta (aguanta toda la tendencia pero devuelve más arriba). Cuando el precio CIERRA el viernes por debajo de esta media, es señal de salir.
SALIDA_BANDA_K = 1.0                              # banda anti-latigazo = K × volatilidad semanal del propio ETF (26s). Cerrar bajo la media DENTRO de la banda = solo aviso (1ª semana); hace falta confirmación (2ª semana) o ruptura clara (fuera de la banda) para SALIR. Sube K (1.5) si aún te da latigazos; bájalo (0.5) si te saca tarde.
SALIDA_STOP_K = 2.5                               # stop duro estilo chandelier: pico de 12 semanas − K × volatilidad. Si el precio cae por debajo, SALIR aunque la media aún no lo confirme (protege de desplomes rápidos que la media tarda en ver).
CARTERA_EXIGE_FLUJO = True                        # True = la cartera excluye a los que tienen el dinero SALIENDO de verdad (CMF < -0.05, mismo umbral que todo el panel; el flujo PLANO entre -0.05 y +0.05 NO expulsa). Asi Cartera y Operativa cuentan la misma historia sin echar a sectores sanos con flujo plano (XLF/XLV). False = la cartera entra solo por impulso.

# === LISTA DE VIGILANCIA (pestaña "Vigilancia") ===
# Acciones que vigilas / tienes y crees que a largo plazo lo haran bien. El terminal te dice su FASE y si empieza a ACUMULAR (dinero entrando) antes de la siguiente subida.
WATCHLIST = ["RKLB", "PCT", "OPEN", "OKLO", "QUBT", "UBER", "AA", "AMBA", "AUR"]
WATCH_NAMES = {"RKLB": "Rocket Lab", "PCT": "PureCycle", "OPEN": "Opendoor", "OKLO": "Oklo (nuclear)",
               "QUBT": "Quantum Computing", "UBER": "Uber", "AA": "Alcoa", "AMBA": "Ambarella", "AUR": "Aurora Innovation"}

# === TU CARTERA REAL (para el "Plan de rotacion de mi cartera") ===
# Cada linea: ("TICKER", "BROKER", importe_en_euros). Acepta ETFs (XLF), acciones (MS), apalancados (TQQQ, SOXL) y los de Europa (EWG, EWP).
# Si dejas la lista vacia, el panel no aparece. Pegame capturas de XTB/Robinhood/DEGIRO y te las convierto a estas lineas.
MI_CARTERA = [
    # Formato: ("TICKER", "BROKER", euros_de_EXPOSICION_actual, apalancamiento_del_producto, "tipo")
    # - En acciones/ETFs al contado: euros = valor actual de la posicion, apalancamiento 1.
    # - En CFDs: euros = valor NOCIONAL mostrado por XTB (la exposicion real), apalancamiento 1 (ya es nocional).
    # - En productos de reset diario (2x/3x/5x): euros = valor de la posicion y el apalancamiento del PRODUCTO,
    #   porque su variacion diaria es N veces la del indice.
    # Extraida de capturas del 04-jul-2026. Los sufijos -CFD/-ETF/-ETC/-PERP/-2X/-3L/-5L se ignoran al mapear.
    #
    # ============ XTB (~7.172 EUR equity · suma de posiciones ~9.682 EUR por el nocional de los CFD) ============
    ("RKLB",            "XTB", 612, 1, "etf"),      # Rocket Lab (+611%)
    ("R2K-UCITS",       "XTB", 1095, 1, "etf"),     # SPDR Russell 2000 US Small Cap UCITS
    ("OPEN",            "XTB", 130, 1, "etf"),      # Opendoor (4 posiciones consolidadas: 128.13+0.81+0.46+0.40)
    ("AA",              "XTB", 294, 1, "etf"),      # Alcoa
    ("ARKG-CFD",        "XTB", 149, 1, "cfd"),      # Genomic Revolution CFD
    ("CTVA-CFD",        "XTB", 223, 1, "cfd"),      # Corteva CFD
    ("DRTS",            "XTB", 92, 1, "etf"),       # Alpha Tau Medical
    ("XLV-CFD",         "XTB", 285, 1, "cfd"),      # Health Care Select Sector CFD
    ("PAK-ETF",         "XTB", 163, 1, "etf"),      # MSCI Pakistan Swap (+31.7%)
    ("CCL",             "XTB", 214, 1, "etf"),      # Carnival
    ("TSLA",            "XTB", 133, 1, "etf"),      # Tesla
    ("U-CFD",           "XTB", 254, 1, "cfd"),      # Unity Software CFD
    ("ERO",             "XTB", 227, 1, "etf"),      # Ero Copper
    ("SEDG",            "XTB", 91, 1, "etf"),       # SolarEdge
    ("AAPL-CFD",        "XTB", 268, 1, "cfd"),      # Apple CFD
    ("STOXX600-CONSTR", "XTB", 186, 1, "etf"),      # iShares STOXX Europe 600 Construction & Materials
    ("GLD-ETC",         "XTB", 41, 1, "etf"),       # iShares Physical Gold (+63.8%)
    ("RDW",             "XTB", 113, 1, "etf"),      # Redwire
    ("AUR",             "XTB", 202, 1, "etf"),      # Aurora Innovation
    ("DAX-2X",          "XTB", 469, 2, "etf_lev"),  # DAX Daily 2x Long (reset diario)
    ("MAS",             "XTB", 72, 1, "etf"),       # Masco
    ("MSCI-CHINA",      "XTB", 328, 1, "etf"),      # Xtrackers MSCI China ETF
    ("XLU-CFD",         "XTB", 199, 1, "cfd"),      # Utilities Select Sector CFD
    ("VNM-ETF",         "XTB", 104, 1, "etf"),      # Xtrackers FTSE Vietnam Swap
    ("BCP",             "XTB", 18, 1, "etf"),       # Millennium BCP
    ("DHI-CFD",         "XTB", 416, 1, "cfd"),      # DR Horton CFD
    ("TOI",             "XTB", 50, 1, "etf"),       # Oncology Institute
    ("FSLR",            "XTB", 101, 1, "etf"),      # First Solar
    ("SOFI",            "XTB", 100, 1, "etf"),      # SoFi
    ("SHOP",            "XTB", 48, 1, "etf"),       # Shopify
    ("MTW",             "XTB", 39, 1, "etf"),       # Manitowoc
    ("AMBA",            "XTB", 97, 1, "etf"),       # Ambarella
    ("SGL",             "XTB", 22, 1, "etf"),       # SGL Carbon
    ("VST",             "XTB", 145, 1, "etf"),      # Vistra Energy
    ("SPCE",            "XTB", 23, 1, "etf"),       # Virgin Galactic
    ("CRSP-CFD",        "XTB", 105, 1, "cfd"),      # CRISPR CFD (-40%)
    ("FERG-CFD",        "XTB", 202, 1, "cfd"),      # Ferguson CFD (agua)
    ("OKLO-CFD",        "XTB", 182, 1, "cfd"),      # Oklo CFD (-20%)
    ("MSCI-INDIA",      "XTB", 276, 1, "etf"),      # iShares MSCI India
    ("UBER-CFD",        "XTB", 195, 1, "cfd"),      # Uber CFD (-34.5%)
    ("CHINA-TECH-ETF",  "XTB", 63, 1, "etf"),       # UBS Solactive China Technology
    ("U",               "XTB", 76, 1, "etf"),       # Unity Software accion
    ("LEU",             "XTB", 55, 1, "etf"),       # Centrus Energy (-45%)
    ("OKLO",            "XTB", 43, 1, "etf"),       # Oklo accion (-51%)
    ("QUBT",            "XTB", 55, 1, "etf"),       # Quantum Computing (-47%)
    ("MP-CFD",          "XTB", 187, 1, "cfd"),      # MP Materials CFD (-116% sobre margen)
    ("MSCI-CHINA-TECH", "XTB", 530, 1, "etf"),      # iShares MSCI China Tech
    ("MSCI-CHINA-CFD",  "XTB", 534, 1, "cfd"),      # iShares MSCI China CFD (-59.8%)
    ("TMC",             "XTB", 124, 1, "etf"),      # TMC the metals company (-35.7%)
    ("WWR",             "XTB", 53, 1, "etf"),       # Westwater (-60.3%)
    #
    # ============ ROBINHOOD (~1.573 EUR) — USD convertido a ~0.874 EUR/USD ============
    ("BTC-PERP",  "Robinhood", 28, 1, "perp"),      # perpetuo BTCUSD Largo 5x, nocional 0.00051 BTC
    ("TNA",       "Robinhood", 542, 3, "etf_lev"),  # 8.526 uds
    ("TQQQ",      "Robinhood", 256, 3, "etf_lev"),
    ("LABU",      "Robinhood", 115, 3, "etf_lev"),
    ("DPST",      "Robinhood", 102, 3, "etf_lev"),
    ("FAS",       "Robinhood", 97, 3, "etf_lev"),
    ("RETL",      "Robinhood", 82, 3, "etf_lev"),
    ("CURE",      "Robinhood", 66, 3, "etf_lev"),   # salud 3x
    ("CCJ",       "Robinhood", 57, 1, "etf"),       # Cameco
    ("AAL",       "Robinhood", 48, 1, "etf"),       # American Airlines
    ("HOOG",      "Robinhood", 33, 1, "etf"),       # Hooglund
    ("SPCX-PVT",  "Robinhood", 5, 1, "etf"),        # SpaceX (privada, token)
    ("OPAI-PVT",  "Robinhood", 6, 1, "etf"),        # OpenAI (privada, token)
    ("KRE",       "Robinhood", 1, 1, "etf"),
    ("SOL",       "Robinhood", 91, 1, "cripto"),    # Solana
    ("CRIPTO-RESTO", "Robinhood", 65, 1, "cripto"), # GRAM+XRP+ETH+AVNT+BTC+RENDER+EURC+ONDO+USDC (polvo)
    #
    # ============ DEGIRO (equity ~1.906 EUR · las posiciones suman ~2.262: revisa si hay efectivo NEGATIVO) ============
    ("AMRQ",   "DEGIRO", 102, 1, "etf"),            # Amaroq (minera oro Groenlandia)
    ("MNST",   "DEGIRO", 428, 1, "etf"),            # Monster Beverage
    ("NAS",    "DEGIRO", 78, 1, "etf"),             # Norwegian Air Shuttle
    ("PCT",    "DEGIRO", 479, 1, "etf"),            # PureCycle
    ("UBER",   "DEGIRO", 65, 1, "etf"),             # Uber accion
    ("TLT-5L", "DEGIRO", 269, 5, "bono_lev"),       # Leverage Shares 5x Long 20+Y Treasury
    ("R2K-UCITS", "DEGIRO", 767, 1, "etf"),         # SPDR Russell 2000 UCITS
    ("SLV-3L", "DEGIRO", 74, 3, "plata_lev"),       # WisdomTree Silver 3x Daily
]
# --- Mapa de alias -> ETF de referencia del terminal (para que el plan de rotacion pueda evaluar cada posicion) ---
ALIAS2ETF = {
    # XTB
    "RKLB": "ITA", "R2K-UCITS": "IWM", "OPEN": "ITB", "AA": "XME", "ARKG": "XBI", "CTVA": "MOO",
    "DRTS": "XBI", "CCL": "JETS", "U": "IGV", "ERO": "COPX", "SEDG": "TAN",
    "STOXX600-CONSTR": "VGK", "GLD": "GLD", "RDW": "ITA", "AUR": "BOTZ", "DAX-2X": "EWG",
    "MAS": "ITB", "MSCI-CHINA": "FXI", "VNM": None, "BCP": "VGK", "DHI": "ITB", "TOI": "XLV",
    "FSLR": "TAN", "SOFI": "ARKF", "SHOP": "IGV", "MTW": "XLI", "AMBA": "SMH", "SGL": "XLB",
    "VST": "XLU", "SPCE": "ITA", "CRSP": "XBI", "FERG": "FIW", "OKLO": "URA",
    "MSCI-INDIA": "INDA", "UBER": "XLY", "CHINA-TECH-ETF": "KWEB", "LEU": "URA", "QUBT": "QTUM",
    "MP": "XME", "MSCI-CHINA-TECH": "KWEB", "MSCI-CHINA-CFD": "FXI", "TMC": "XME", "WWR": "URA",
    "PAK": None,
    # Robinhood
    "RETL": "XRT", "CCJ": "URA", "AAL": "JETS", "SOL": "IBIT", "BTC": "IBIT",
    # DEGIRO
    "AMRQ": "GDX", "NAS": "JETS", "PCT": "XLB", "MNST": "XLP", "TLT": "TLT", "SLV": "SLV",
}
# --- Nombres legibles de las posiciones de MI_CARTERA (para el tooltip de tickers) ---
CARTERA_NOMBRES = {
    "RKLB": "Rocket Lab (espacio)", "R2K-UCITS": "SPDR Russell 2000 US Small Cap UCITS", "OPEN": "Opendoor Technologies",
    "AA": "Alcoa (aluminio)", "ARKG-CFD": "ARK Genomic Revolution (CFD)", "CTVA-CFD": "Corteva Agriscience (CFD)",
    "DRTS": "Alpha Tau Medical", "XLV-CFD": "Health Care Select Sector (CFD)", "PAK-ETF": "MSCI Pakistan Swap",
    "CCL": "Carnival (cruceros)", "TSLA": "Tesla", "U-CFD": "Unity Software (CFD)", "U": "Unity Software",
    "ERO": "Ero Copper (cobre)", "SEDG": "SolarEdge", "AAPL-CFD": "Apple (CFD)",
    "STOXX600-CONSTR": "STOXX Europe 600 Construcción y Materiales", "GLD-ETC": "iShares Physical Gold",
    "RDW": "Redwire (espacio)", "AUR": "Aurora Innovation (conducción autónoma)", "DAX-2X": "DAX Daily 2x Long",
    "MAS": "Masco (construcción)", "MSCI-CHINA": "Xtrackers MSCI China UCITS", "XLU-CFD": "Utilities Select Sector (CFD)",
    "VNM-ETF": "Xtrackers FTSE Vietnam Swap", "BCP": "Millennium BCP", "DHI-CFD": "DR Horton (CFD, vivienda)",
    "TOI": "Oncology Institute", "FSLR": "First Solar", "SOFI": "SoFi Technologies", "SHOP": "Shopify",
    "MTW": "Manitowoc (grúas)", "AMBA": "Ambarella (semis visión)", "SGL": "SGL Carbon", "VST": "Vistra Energy",
    "SPCE": "Virgin Galactic", "CRSP-CFD": "CRISPR Therapeutics (CFD)", "FERG-CFD": "Ferguson (CFD, agua)",
    "OKLO-CFD": "Oklo (CFD, nuclear)", "OKLO": "Oklo (nuclear)", "MSCI-INDIA": "iShares MSCI India",
    "UBER-CFD": "Uber (CFD)", "UBER": "Uber", "CHINA-TECH-ETF": "UBS Solactive China Technology",
    "LEU": "Centrus Energy (uranio)", "QUBT": "Quantum Computing Inc", "MP-CFD": "MP Materials (CFD, tierras raras)",
    "MSCI-CHINA-TECH": "iShares MSCI China Tech UCITS", "MSCI-CHINA-CFD": "iShares MSCI China (CFD)",
    "TMC": "TMC the metals company", "WWR": "Westwater Resources",
    "BTC-PERP": "Perpetuo BTC/USD 5x largo", "TNA": "Small caps Russell 2000 x3", "TQQQ": "Nasdaq-100 x3",
    "LABU": "Biotech x3", "DPST": "Banca regional x3", "FAS": "Financieras x3", "RETL": "Retail x3",
    "CURE": "Salud x3", "CCJ": "Cameco (uranio)", "AAL": "American Airlines", "HOOG": "Hooglund",
    "SPCX-PVT": "SpaceX (token privado)", "OPAI-PVT": "OpenAI (token privado)", "SOL": "Solana",
    "CRIPTO-RESTO": "Resto cripto (polvo)", "AMRQ": "Amaroq Minerals (oro Groenlandia)", "MNST": "Monster Beverage",
    "NAS": "Norwegian Air Shuttle", "PCT": "PureCycle Technologies", "TLT-5L": "Treasury 20+ años x5 largo",
    "SLV-3L": "Plata x3 diario",
}
# --- Datos de margen por broker (para el stress-test; actualizalos cuando cambien) ---
BROKER_INFO = {
    # equity = valor de la cuenta EUR · margen_libre = capital disponible · nivel_margen = % que muestra el broker (equity/margen requerido)
    # stopout = nivel de margen al que el broker EMPIEZA A CERRARTE posiciones el solo
    "XTB":       {"equity": 7172, "margen_libre": 5.94, "nivel_margen": 104.87, "stopout": 50},
    "Robinhood": {"equity": 1573, "margen_libre": None, "nivel_margen": None,   "stopout": None},
    "DEGIRO":    {"equity": 1906, "margen_libre": None, "nivel_margen": None,   "stopout": None},
}
STRESS_DD = [-5, -10, -20]                       # escenarios de caida del S&P para el stress-test
# beta aproximada frente al S&P por TIPO de activo (choque de 1 dia; orientativa, no exacta)
STRESS_BETA = {"etf": 1.0, "etf_lev": 1.0, "cfd": 1.0, "cesta": 1.0, "perp": 1.8, "cripto": 1.8,
               "bono_lev": -0.2, "plata_lev": 0.8}
# --- Senal contraria 0/3 (tu estadistica: 65% de acierto a 4 semanas, +2.2% de media; muestra 70 sem = IN-SAMPLE) ---
CONTRARIAN_ON = True                             # activa el modulo de senal contraria (ledger fuera-de-muestra + tamano sugerido)
CONTRARIAN_SIZE_PCT = 2.0                        # % de cartera por senal mientras la muestra fuera-de-muestra sea corta (<20 casos)
CONTRARIAN_MAX_SIGS = 3                          # maximo de senales simultaneas (tope de exposicion contraria = SIZE x MAX)
CONTRARIAN_HORIZON_W = 4                         # horizonte de evaluacion en semanas (el de tu estadistica)

# --- Indicador Pine v6 para TradingView: el MISMO flujo (CMF + distribucion oculta) del terminal ---
PINE_SCRIPT = '''//@version=6
indicator("Flujo PeVR — CMF + distribución oculta", shorttitle="Flujo PeVR", overlay=false)

// === Ajustes (mismos umbrales que el terminal ROTACION) ===
lenCMF   = input.int(20, "Longitud del CMF", minval=2)
lenOBV   = input.int(20, "Media del OBV", minval=2)
lookDiv  = input.int(13, "Velas para la divergencia precio/flujo", minval=4)
umbral   = input.float(0.05, "Umbral CMF (±)", step=0.01)
verOBV   = input.bool(true, "Mostrar OBV vs su media (normalizado)")

// === CMF (Chaikin Money Flow) ===
mfm = high == low ? 0.0 : ((2 * close - low - high) / (high - low))
mfv = mfm * volume
cmf = math.sum(mfv, lenCMF) / math.sum(volume, lenCMF)

// === OBV y su media ===
obv   = ta.obv
obvMa = ta.sma(obv, lenOBV)

// === Distribución oculta: el precio SUBE pero el dinero SALE ===
precioSube = close > close[lookDiv]
dineroSale = cmf < -umbral or (obv < obvMa and cmf < 0)
distOculta = precioSube and dineroSale

// === Acumulación oculta: el precio CAE pero el dinero ENTRA ===
acumOculta = close < close[lookDiv] and cmf > umbral and obv > obvMa

// === Pintado ===
colCmf = cmf > umbral ? color.new(#2FD08A, 0) : cmf < -umbral ? color.new(#F4607A, 0) : color.new(#93A4BC, 40)
plot(cmf, "CMF", style=plot.style_columns, color=colCmf)
hline(0, "Cero", color=color.new(#93A4BC, 60))
hline(0.05, "+0.05 (entra dinero)", color=color.new(#2FD08A, 70), linestyle=hline.style_dotted)
hline(-0.05, "-0.05 (sale dinero)", color=color.new(#F4607A, 70), linestyle=hline.style_dotted)

obvRel = verOBV ? (obv - obvMa) / (ta.stdev(obv, 100) + 1e-9) * 0.05 : na
plot(obvRel, "OBV vs media (escalado)", color=color.new(#4CC2E0, 25), linewidth=1)

plotshape(distOculta, "Distribución oculta", style=shape.triangledown, location=location.top, color=color.new(#F4B740, 0), size=size.tiny)
plotshape(acumOculta, "Acumulación oculta", style=shape.triangleup, location=location.bottom, color=color.new(#4CC2E0, 0), size=size.tiny)
bgcolor(distOculta ? color.new(#F4B740, 88) : acumOculta ? color.new(#4CC2E0, 92) : na)

// === Alertas ===
alertcondition(distOculta, "Flujo PeVR: Distribución oculta", "{{ticker}}: el precio sube pero el dinero SALE (distribución oculta)")
alertcondition(acumOculta, "Flujo PeVR: Acumulación oculta", "{{ticker}}: el precio cae pero el dinero ENTRA (acumulación)")
alertcondition(ta.crossover(cmf, 0.05), "Flujo PeVR: CMF cruza +0.05", "{{ticker}}: el dinero empieza a ENTRAR (CMF > +0.05)")
alertcondition(ta.crossunder(cmf, -0.05), "Flujo PeVR: CMF cruza -0.05", "{{ticker}}: el dinero empieza a SALIR (CMF < -0.05)")
'''
MEAN_REVERSION = True                            # calcula la rentabilidad media anual (10a) y la del año (YTD) de cada ETF -> panel "margen vs su media" (descarga ~10a por ETF, algo mas lento; pon False para desactivar)
# Vehiculos apalancados x3 por activo (informativo; MUY arriesgados, ver avisos)
LEV3X = {"SPY":"SPXL/UPRO", "QQQ":"TQQQ", "MAGS":"TQQQ", "XLK":"TECL", "XLF":"FAS",
         "XLE":"ERX", "XLV":"CURE", "XLI":"DUSL", "XLB":"—", "XLU":"UTSL", "XLRE":"DRN",
         "XLY":"WANT", "XLP":"—", "XLC":"—", "IWM":"TNA", "FXI":"YINN", "EEM":"EDC",
         "ITA":"DFEN", "GLD":"—", "TLT":"TMF", "SMH":"SOXL", "KRE":"DPST", "XBI":"LABU",
         "GDX":"NUGT", "JETS":"—", "IGV":"TECL*", "SOXX":"SOXL", "ITB":"NAIL", "KWEB":"CWEB*"}
# Empresa lider (mayor posicion) de cada ETF — ORIENTATIVO, cambia con el tiempo
TOP_HOLDING = {
    "XLK":"NVDA / MSFT / AAPL", "XLF":"BRK.B / JPM", "XLE":"XOM / CVX", "XLV":"LLY / UNH",
    "XLY":"AMZN / TSLA", "XLP":"COST / WMT", "XLI":"GE / CAT", "XLB":"LIN / SHW",
    "XLU":"NEE / SO", "XLRE":"PLD / AMT", "XLC":"META / GOOGL", "IWM":"muy diversificado",
    "MAGS":"los 7 (AAPL,MSFT,NVDA...)", "FXI":"BABA / Tencent", "EEM":"TSM / Tencent",
    "ITA":"GE Aero / RTX / BA", "JETS":"aerolineas + BKNG", "SMH":"NVDA / TSM / AVGO",
    "KRE":"banca regional (div.)", "XBI":"biotech equiponderado", "GDX":"NEM / AEM",
    "IGV":"MSFT / CRM / ORCL",
    "SOXX":"NVDA / AVGO / AMD", "ITB":"DHI / LEN / NVR", "KWEB":"BABA / Tencent / PDD",
    "EWG":"SAP / Siemens / Allianz", "EWP":"Iberdrola / Inditex / Santander",
    "COPX":"Freeport / Antofagasta / Ivanhoe", "URA":"Cameco / Kazatomprom / NexGen", "LIT":"Albemarle / SQM / Ganfeng",
    "GRID":"Eaton / Quanta / GE Vernova", "PAVE":"Eaton / Trane / Quanta",
    "FIW":"Ferguson / Xylem / Veralto", "CGW":"American Water / Veolia / Xylem",
    "HYDR":"Plug Power / Bloom / ITM Power",
}
SITE_DIR = "site"                                # carpeta que publica GitHub Pages
STATIC_DIR = "static"                            # iconos, manifest, service worker
# El terminal completo vive en /pro/ para dejar la raiz a la web publica (La Estela),
# que es el enlace que se reparte. Ojo: una ruta poco adivinable NO es seguridad —
# si el workflow publica site/ entero, /pro/ es accesible para quien lo pruebe.
OUTPUT_HTML = os.path.join(SITE_DIR, "pro", "index.html")
CACHE_DIR = "cache_rotacion"
# ----------------------------------------------------------------------

NAMES = {
    # NUEVOS (v4.6) — fondos MUY jovenes: DRAM salio el 02-abr-2026, NCLD despues.
    # Hasta ~40 semanas de historia el scoring saldra INCOMPLETO (sin SMA40 no puede
    # puntuar precio>SMA40 ni momentum 3m) y el RRG tendra estela corta. El CMF y el
    # volumen SI son validos a partir de 30 sesiones: eso es lo que hay que mirar.
    "DRAM": "Memorias / HBM",
    "NCLD": "Neocloud (GPU en alquiler)",
    "SPY":("S&P 500","Indice (referencia)","bench"),
    "XLK":("Technology","Tecnologia","ciclico"),
    "XLF":("Financials","Financiero","ciclico"),
    "XLE":("Energy","Energia","sensible"),
    "XLV":("Health Care","Salud","defensivo"),
    "XLY":("Cons. Discretionary","Consumo discrecional","ciclico"),
    "XLP":("Cons. Staples","Consumo basico","defensivo"),
    "XLI":("Industrials","Industrial","ciclico"),
    "XLB":("Materials","Materiales","sensible"),
    "XLU":("Utilities","Servicios publicos","defensivo"),
    "XLRE":("Real Estate","Inmobiliario","sensible"),
    "XLC":("Comm. Services","Comunicaciones","ciclico"),
    "IWM":("Russell 2000","Small caps","ciclico"),
    "DIA":("Dow Jones 30","Industriales clásicas (value)","ciclico"),
    "TLT":("20Y Treasuries","Bonos largos","defensivo"),
    "GLD":("Gold","Oro","defensivo"),
    "IBIT":("iShares Bitcoin Trust","Bitcoin (ETF)","especulativo"),
    "HYG":("High Yield","Credito HY","ciclico"),
    "UUP":("US Dollar","Dolar","macro"),
    "FXI":("China Large-Cap","China","ciclico"),
    "EEM":("Emerging Markets","Emergentes","ciclico"),
    "ITA":("Aerospace & Defense","Espacio y defensa","ciclico"),
    "MAGS":("Magnificent 7","7 Magnificos","ciclico"),
    "JETS":("Airlines / Travel","Viajes y aerolineas","ciclico"),
    "SMH":("Semiconductors","Semiconductores","ciclico"),
    "KRE":("Regional Banks","Banca regional","ciclico"),
    "XBI":("Biotech","Biotecnologia","ciclico"),
    "GDX":("Gold Miners","Mineras de oro","sensible"),
    "IGV":("Software","Software","ciclico"),
    "SOXX":("Semiconductors (iShares)","Semis (iShares)","ciclico"),
    "ITB":("Home Construction","Construccion / vivienda","ciclico"),
    "KWEB":("China Internet","China tecnologica","ciclico"),
    "EWG":("Germany (DAX proxy)","Alemania / DAX","ciclico"),
    "EWP":("Spain (IBEX proxy)","España / IBEX 35","ciclico"),
    "COPX":("Copper Miners","Cobre (mineras)","ciclico"),
    "URA":("Uranium","Uranio","ciclico"),
    "LIT":("Lithium & Battery","Litio y baterías","ciclico"),
    "GRID":("Smart Grid Infra","Red eléctrica (IA)","ciclico"),
    "PAVE":("US Infrastructure","Infraestructura EE.UU. (IA)","ciclico"),
    "FIW":("US Water","Agua EE.UU. (IA)","ciclico"),
    "CGW":("Global Water","Agua global (IA)","ciclico"),
    "HYDR":("Global Hydrogen","Hidrógeno (IA/energía)","ciclico"),
    "XRT":("Retail (SPDR)","Retail / consumo minorista","ciclico"),
    "XOP":("Oil & Gas E&P","Petróleo y gas (E&P)","sensible"),
    "OIH":("Oil Services","Servicios petroleros","sensible"),
    "ARKF":("Fintech Innovation","Fintech (ARK)","ciclico"),
    "ARKK":("ARK Innovation","Innovación (ARK)","ciclico"),
    "CIBR":("Cybersecurity","Ciberseguridad","ciclico"),
    "SKYY":("Cloud Computing","Nube (cloud)","ciclico"),
    "BOTZ":("Robotics & AI","Robótica e IA","ciclico"),
    "TAN":("Solar","Solar","ciclico"),
    "ICLN":("Clean Energy","Energía limpia global","ciclico"),
    "FAN":("Wind Energy","Eólica","ciclico"),
    "XME":("Metals & Mining","Minería y metales","sensible"),
    "SIL":("Silver Miners","Mineras de plata","sensible"),
    "SLV":("Silver","Plata","sensible"),
    "EWJ":("Japan","Japón","ciclico"),
    "INDA":("India","India","ciclico"),
    "EWZ":("Brazil","Brasil","ciclico"),
    "VGK":("Europe","Europa","ciclico"),
    "EURUSD":("Euro / Dolar","EUR/USD","macro"),
    "DRIV":("Global X Autonomous & EV — señal del tema automoción innovadora; en España se compra vía WisdomTree WCAR UCITS","Automoción innov.","tech"),
    "EWY":("iShares MSCI South Korea — el chivato asiático de los semis (Samsung + SK Hynix)","Corea del Sur","internac"),
    "MOO":("VanEck Agribusiness — agro y alimentación (el hogar natural de tu Corteva)","Agronegocio","materiales"),
    "QTUM":("Defiance Quantum — computación cuántica (el hogar natural de tu QUBT)","Computación cuántica","tech"),
    "UFO":("Procure Space — el ETF de espacio mas puro por indice (satelites, lanzadores, telecom espacial); ETF pequeno y menos liquido que ARKX: el flujo puede ser mas ruidoso","Espacio (puro)","ciclico"),
    "ARKX":("ARK Space Exploration — el pure-play espacial (RKLB, satélites, defensa-espacio)","Espacio (ARK)","ciclico"),
    "LQD":("Investment Grade Bonds","Crédito IG","defensivo"),
    "EMB":("Emerging Markets Bonds","Crédito emergente","sensible"),
    "RSP":("S&P 500 Equal Weight — el S&P sin el peso de los gigantes","S&P equiponderado","ciclico"),
    "S-EXPLOSIVO":("Sintético alta beta growth (SMH+XBI+ARKK+KWEB+TAN)","Sint. Explosivo","sintetico"),
    "CE-EQUIPOS":("Cascada IA 1b — Equipos semi (ASML+LRCX+AMAT+KLAC): quien cobra ANTES que nadie","C1b Equipos","cascada"),
    "S-ALMACEN":("Sintético almacenamiento (WDC+STX+SNDK) — el dato que se GUARDA, no el que se procesa","Sint. Almacén","sintetico"),
    "S-DUROS":("Sintético activos duros alta beta (GDX+SIL+COPX+URA+IBIT) — la base oro/BTC/mineras","Sint. Duros","sintetico"),
    "S-DEFENSA":("Sintético defensivo puro (XLP+XLU+XLV) — termómetro, no destino","Sint. Defensa","sintetico"),
    "S-REFUGIO":("Sintético huida a seguridad (GLD+TLT+UUP)","Sint. Refugio","sintetico"),
    "S-CREDITO":("Sintético pulso del crédito (HYG+LQD+EMB) — el canario que avisa antes","Sint. Crédito","sintetico"),
    "S-AMPLITUD":("Sintético amplitud real (RSP+IWM) — ¿sube el mercado o solo cuatro gigantes?","Sint. Amplitud","sintetico"),
    "C0-HIPER":("Cascada IA 0 — Hiperescaladores (MAGS): quien suelta el dinero","C0 Hiper","cascada"),
    "C1-SILICIO":("Cascada IA 1 — Silicio (SMH+SOXX): el primer eslabón del capex","C1 Silicio","cascada"),
    "C2-OBRA":("Cascada IA 2 — Obra y red (PAVE+GRID+FIW+CGW)","C2 Obra","cascada"),
    "C3-ENERGIA":("Cascada IA 3 — Energía (XLU+URA+XLE)","C3 Energía","cascada"),
    "C4-MATERIA":("Cascada IA 4 — Materia prima (COPX+XME+SIL+SLV): el eslabón de mayor beta","C4 Materia","cascada"),
    "C5-RETORNO":("Cascada IA 5 — Retorno (SKYY+IGV+CIBR): quien debe devolver el gasto en ingresos","C5 Retorno","cascada"),
}
QUAD = {
    "leading":  ("Lider","#2FD08A","Liderazgo confirmado"),
    "weakening":("Debilitandose","#F4B740","Riesgo de recogida de beneficios"),
    "lagging":  ("Rezagado","#F4607A","Evitar / infraponderar"),
    "improving":("Mejorando","#4CC2E0","Acumulacion temprana"),
}

# ----------------------------------------------------------------------
# Bootstrap de dependencias
# ----------------------------------------------------------------------
def ensure(pkg, imp=None, optional=False):
    try:
        return importlib.import_module(imp or pkg)
    except ImportError:
        print(f"  Instalando {pkg} ...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", pkg])
            return importlib.import_module(imp or pkg)
        except Exception as e:
            if optional:
                print(f"  (Aviso) No se pudo instalar {pkg}: {e}")
                return None
            raise

print("Preparando librerias...")
pd = ensure("pandas")
# --- yfinance: scraper NO oficial que Yahoo rompe periodicamente. En GitHub Actions cada build
#     instala la ULTIMA version: un release roto un martes cambia el terminal sin tocar nada.
#     YF_PIN fija una version probada (p.ej. "yfinance==0.2.66"); vacio = ultima (comportamiento
#     antiguo). La version usada se imprime SIEMPRE para poder correlacionar builds raros. ---
YF_PIN = ""
yf = ensure(YF_PIN or "yfinance", imp="yfinance", optional=True)
try:
    if yf is not None:
        print(f"  yfinance {yf.__version__}" + ("  (pin activo)" if YF_PIN else "  (SIN pin: ultima version — considera fijar YF_PIN)"))
except Exception:
    pass
requests = ensure("requests")
import pandas as pd  # noqa
from io import StringIO

# ----------------------------------------------------------------------
# Descarga de datos (Stooq -> Yahoo -> cache)
# ----------------------------------------------------------------------
def fetch_stooq(sym, start, end):
    """Descarga OHLCV diario directamente de Stooq (sin libreria intermedia)."""
    url = f"https://stooq.com/q/d/l/?s={sym.lower()}.us&i=d"
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        txt = r.text
        if not txt or "Close" not in txt.splitlines()[0]:
            return None
        df = pd.read_csv(StringIO(txt))
        if "Date" not in df.columns or "Close" not in df.columns or len(df) < 30:
            return None
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
        out = df[cols].copy()
        return out[out.index >= pd.Timestamp(start)]
    except Exception as _dege:
        _deg("fetch_stooq:836", _dege)
        return None

def fetch_yahoo(sym, start, end):
    # NOTA auto_adjust=True: los cierres van AJUSTADOS por dividendos/splits (correcto para retornos
    # y flujo). Si validas a mano contra la web de Yahoo veras diferencias crecientes hacia atras:
    # no es un error, es el Adjusted Close. Los niveles absolutos de indices usan auto_adjust=False.
    if yf is None:
        return None
    try:
        df = yf.download(sym, start=start, end=end + dt.timedelta(days=1), interval="1d",
                         progress=False, auto_adjust=True)
        if df is None or len(df) < 30:
            return None
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)
        cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
        return df[cols].sort_index()
    except Exception as e:
        # mensaje SIN el simbolo a proposito: _avisar agrupa avisos identicos con contador, asi un
        # rate-limit masivo sale como "descarga fallida ×40" y no inunda el panel de salud
        _avisar("yahoo", f"descarga fallida: {type(e).__name__}")
        return None

def cache_path(sym):
    return os.path.join(CACHE_DIR, f"{sym}.csv")

def save_cache(sym, dframe):
    os.makedirs(CACHE_DIR, exist_ok=True)
    dframe.to_csv(cache_path(sym))

def load_cache(sym):
    p = cache_path(sym)
    if os.path.exists(p):
        try:
            return pd.read_csv(p, index_col=0, parse_dates=True).sort_index()
        except Exception as _dege:
            _deg("load_cache:872", _dege)
            return None
    return None

# El seguimiento NO va en la cache (la cache es desechable y se borra para liberar espacio o forzar datos frescos).
# Va en su propia carpeta, con nombre de "no me borres", y se hace copia de seguridad en cada guardado.
SEGUIMIENTO_DIR = "historico_seguimiento_NO_BORRAR"
TRACK_FILE = os.path.join(SEGUIMIENTO_DIR, "track_record.json")
TRACK_BAK = os.path.join(SEGUIMIENTO_DIR, "track_record.bak.json")
_OLD_TRACK = os.path.join(CACHE_DIR, "track_record.json")          # ubicacion antigua (dentro de la cache)

# ======================================================================
# CONFIG EXTERNA  (v4 — entrega 2)
# Si existe config.py con lineas descomentadas, SUS valores mandan sobre los
# de arriba. Si no existe, o esta todo comentado, no cambia absolutamente nada.
# El terminal NUNCA se cae por culpa de config.py.
# ======================================================================
_CFG_APLICADOS = []
try:
    import config as _cfg
    for _k in dir(_cfg):
        if _k.startswith("_"):
            continue
        if _k in globals():
            _nuevo, _viejo = getattr(_cfg, _k), globals()[_k]
            if _nuevo != _viejo:
                globals()[_k] = _nuevo
                _CFG_APLICADOS.append(f"{_k}: {_viejo!r} -> {_nuevo!r}"[:90])
    # constantes DERIVADAS: hay que recalcularlas si su origen ha cambiado
    GRUPO_SECTORES = SECTORS + ["IWM", "DIA", "RSP"]
    for _s in GRUPO_SECTORES:
        GRUPO[_s] = "sector"
    OUTPUT_HTML = os.path.join(SITE_DIR, "pro", "index.html")
    TRACK_FILE = os.path.join(SEGUIMIENTO_DIR, "track_record.json")
    TRACK_BAK = os.path.join(SEGUIMIENTO_DIR, "track_record.bak.json")
    _OLD_TRACK = os.path.join(CACHE_DIR, "track_record.json")
    if _CFG_APLICADOS:
        print(f"  ⚙ config.py: {len(_CFG_APLICADOS)} parametro(s) sustituido(s)")
        for _c in _CFG_APLICADOS:
            print(f"     · {_c}")
except ImportError:
    pass                                   # sin config.py: comportamiento original intacto
except Exception as _e:
    _avisar("config", f"config.py existe pero fallo al leerlo ({_e}); se usan los valores de rotacion.py")
try:
    # migracion: si tienes histórico en la cache vieja y aun no en la nueva, lo traslado para no perderlo
    if os.path.exists(_OLD_TRACK) and not os.path.exists(TRACK_FILE):
        os.makedirs(SEGUIMIENTO_DIR, exist_ok=True)
        import shutil as _sh
        _sh.copy2(_OLD_TRACK, TRACK_FILE)
except Exception:
    pass

def semana_trading(fecha):
    """Etiqueta de SEMANA DE TRADING: la ventana sabado..viernes, nombrada por el viernes que la cierra.
    Lun/mar/mie/jue/vie de la misma semana -> misma etiqueta. Sabado/domingo -> la semana que viene.
    Evita el bug de que el lunes (nueva semana ISO) creara un registro distinto al viernes anterior."""
    try:
        d = pd.Timestamp(fecha)
        wd = d.weekday()               # 0=lun..6=dom
        if wd == 5:                    # sabado
            friday = d + pd.Timedelta(days=6)
        elif wd == 6:                  # domingo
            friday = d + pd.Timedelta(days=5)
        else:                          # lun..vie -> el viernes de esta misma semana
            friday = d + pd.Timedelta(days=(4 - wd))
        return friday.strftime("%G-W%V")
    except Exception:
        return str(fecha)


def update_track_record(basket, px_now, datestr, marked=None):
    # Guarda un snapshot por semana ISO {week, date, basket, marked, px:{ticker:cierre}} y devuelve el historico ordenado.
    # px_now debe incluir los tickers del basket + SPY/QQQ/IWM. Asi cada semana puede valorar la cesta de la anterior.
    os.makedirs(SEGUIMIENTO_DIR, exist_ok=True)
    recs = []
    if os.path.exists(TRACK_FILE):
        try:
            with open(TRACK_FILE, "r", encoding="utf-8") as fh:
                recs = json.load(fh)
        except Exception as _dege:
            _deg("update_track_record:918", _dege)
            # si el principal está corrupto, intento recuperar desde la copia de seguridad
            try:
                with open(TRACK_BAK, "r", encoding="utf-8") as fh:
                    recs = json.load(fh)
            except Exception as _dege:
                _deg("update_track_record:923", _dege)
                recs = []
    wk = semana_trading(datestr)
    px_clean = {k: float(v) for k, v in px_now.items() if v is not None and v == v}
    ya_existe = any(r.get("week") == wk for r in recs)
    # Solo se GRABA una cesta nueva cuando la semana ha cerrado (viernes o fin de semana).
    # Entre semana (lun-jue) se observa pero NO se registra: evita abrir una semana a medias con datos provisionales.
    try:
        _hoy_wd = dt.date.today().weekday()   # 0=lun..6=dom
    except Exception:
        _hoy_wd = 4
    if not ya_existe and _hoy_wd < 4:
        print(f"  TRACK: semana {wk} aun en curso (hoy es {['lunes','martes','miercoles','jueves','viernes','sabado','domingo'][_hoy_wd]}). "
              "No se graba hasta el cierre del VIERNES — entre semana solo se observa.")
        recs.sort(key=lambda r: r.get("week", ""))
        return recs
    if ya_existe:
        # NO sobrescribir: el registro de la semana se CONGELA con el primer build (idealmente el viernes).
        # Re-ejecutar a media semana no debe mover la fecha/precio de entrada ni la cesta registrada.
        try:
            dia = pd.Timestamp(datestr).strftime("%A")
        except Exception:
            dia = str(datestr)
        print(f"  TRACK: la semana {wk} ya esta registrada (congelada). Re-ejecucion en {dia} NO la altera — solo el primer cierre de la semana cuenta.")
        recs.sort(key=lambda r: r.get("week", ""))
        return recs
    snap = {"week": wk, "date": str(datestr), "basket": list(basket), "marked": list(marked or []), "px": px_clean}
    recs.append(snap)
    recs.sort(key=lambda r: r.get("week", ""))
    try:
        with open(TRACK_FILE, "w", encoding="utf-8") as fh:
            json.dump(recs, fh, ensure_ascii=False, indent=0)
        with open(TRACK_BAK, "w", encoding="utf-8") as fh:        # copia de seguridad
            json.dump(recs, fh, ensure_ascii=False, indent=0)
    except Exception:
        pass
    return recs

def pct_desde_entrada(recs, sym, key, cur_week, in_now, cur_px, df=None):
    """% desde el inicio de la RACHA continua actual de sym en recs[key] (reinicia si sale y vuelve).
       in_now = si esta en el set esta semana; cur_px = precio actual. Devuelve (pct, semanas) o None.
       Robusto a HUECOS: si una semana de la racha no guardo precio, sigue buscando hacia atras el
       precio valido mas antiguo (antes se quedaba en cur_px y daba 0% — el bug de CIBR/KRE)."""
    if not in_now or not cur_px or cur_px <= 0:
        return None
    timeline = []
    for r in sorted(recs or [], key=lambda r: r.get("week", "")):
        if r.get("week") == cur_week:
            continue
        timeline.append((r.get("week"), sym in r.get(key, []), (r.get("px", {}) or {}).get(sym)))
    timeline.append((cur_week, True, cur_px))            # semana actual (aun no persistida)
    entry_px, entry_wk, weeks = cur_px, cur_week, 0
    for wk, inset, px in reversed(timeline):
        if inset:
            if px and px > 0:
                entry_px = px                            # sigue actualizando: acaba en el mas antiguo de la racha
                entry_wk = wk
            weeks += 1
        else:
            break
    # fallback: si el precio de entrada quedo igual al actual por huecos, recuperarlo de la serie diaria
    if df is not None and entry_wk and entry_px == cur_px and weeks > 1 and sym in getattr(df, "columns", []):
        try:
            s = df[sym].dropna()
            import pandas as _pd
            wkstart = _pd.Timestamp(entry_wk.split("/")[0]) if "/" in str(entry_wk) else None
            # entry_wk viene como ISO week "%G-W%V"; convertimos a fecha del viernes de esa semana
            import datetime as _dt
            yr, wk2 = str(entry_wk).split("-W")
            monday = _dt.date.fromisocalendar(int(yr), int(wk2), 1)
            friday = monday + _dt.timedelta(days=4)
            idx = s.index.searchsorted(_pd.Timestamp(friday))
            if 0 <= idx < len(s):
                entry_px = float(s.iloc[idx])
        except Exception:
            pass
    if not entry_px or entry_px <= 0:
        return None
    return ((cur_px / entry_px - 1) * 100, weeks)


def compute_track_perf(recs, benches=("SPY", "QQQ", "IWM"), ew_universe=None):
    # A partir de los snapshots, retorno semanal de la cesta del sistema (equiponderada) vs benchmarks
    # y vs una cesta de TODOS los sectores equiponderada (ew_universe), y acumulado encadenado.
    if not recs or len(recs) < 2:
        return None
    ew_universe = list(ew_universe) if ew_universe else list(SECTORS)
    weeks = []
    cum = {"sys": 1.0, "ew": 1.0}
    for b in benches:
        cum[b] = 1.0
    for i in range(len(recs) - 1):
        a, b = recs[i], recs[i + 1]
        pxa, pxb = a.get("px", {}), b.get("px", {})
        bk = [t for t in a.get("basket", []) if t in pxa and t in pxb and pxa[t]]
        if not bk:
            continue
        sysret = sum((pxb[t] / pxa[t] - 1.0) for t in bk) / len(bk)
        row = {"week": b["week"], "date": b["date"], "basket": a.get("basket", []), "sys": sysret, "bench": {}}
        cum["sys"] *= (1.0 + sysret)
        row["cum_sys"] = cum["sys"] - 1.0
        # cesta de TODOS los sectores equiponderada (referencia: ¿la selección bate a tenerlo todo por igual?)
        ewbk = [t for t in ew_universe if t in pxa and t in pxb and pxa[t]]
        if ewbk:
            ewret = sum((pxb[t] / pxa[t] - 1.0) for t in ewbk) / len(ewbk)
            row["ew"] = ewret
            cum["ew"] *= (1.0 + ewret)
        else:
            row["ew"] = None
        row["cum_ew"] = cum["ew"] - 1.0
        for bm in benches:
            if bm in pxa and bm in pxb and pxa[bm]:
                r = pxb[bm] / pxa[bm] - 1.0
                row["bench"][bm] = r
                cum[bm] *= (1.0 + r)
            row[f"cum_{bm}"] = cum[bm] - 1.0
        weeks.append(row)
    if not weeks:
        return None
    return {"weeks": weeks, "cum": {k: cum[k] - 1.0 for k in cum},
            "pending": {"week": recs[-1]["week"], "date": recs[-1]["date"], "basket": recs[-1].get("basket", [])},
            "n": len(weeks)}

def topup_recent(sym, d, end):
    # rellena con Yahoo las barras mas recientes que Stooq aun no tenga (frescura del ultimo dia).
    # devuelve (dataframe, n_barras_anyadidas)
    if not TOPUP_YAHOO or yf is None or d is None or d.empty:
        return d, 0
    try:
        last = d.index[-1]
        y = yf.download(sym, start=(last - dt.timedelta(days=4)),
                        end=end + dt.timedelta(days=1), interval="1d",
                        progress=False, auto_adjust=True)
        if y is None or y.empty:
            return d, 0
        if hasattr(y.columns, "nlevels") and y.columns.nlevels > 1:
            y.columns = y.columns.get_level_values(0)
        cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in y.columns]
        newer = y[cols][y.index > last]
        if newer.empty:
            return d, 0
        # GUARDIA DE ESCALA (la misma de refrescar_con_yahoo, que aqui faltaba): si Yahoo devuelve otra
        # escala (ticker mal interpretado, serie ajustada vs sin ajustar tras un split), concatenar
        # corromperia CMF/OBV/retornos con un salto ficticio. Solo se añade si el primer dato nuevo
        # esta a <25% del ultimo de la base (misma escala, movimiento de 1-2 sesiones plausible).
        try:
            _ratio = float(newer["Close"].iloc[0]) / float(d["Close"].dropna().iloc[-1])
            if not (0.8 <= _ratio <= 1.25):
                _avisar(f"topup.{sym}", f"refresco Yahoo DESCARTADO: escala incompatible con Stooq (ratio {_ratio:.2f}); la serie sigue 1 sesion vieja")
                return d, 0
        except Exception:
            return d, 0
        d = pd.concat([d, newer]).sort_index()
        d = d[~d.index.duplicated(keep="last")]
        return d, len(newer)
    except Exception:
        return d, 0

def _ohlcv_valido(sym, d, fuente):
    """Validacion ESTRUCTURAL de lo descargado antes de aceptarlo: cierres > 0, High >= Low,
    fechas sin duplicar y sin huecos groseros. Si la fuente devuelve barras corruptas (pasa con
    splits mal procesados), se descarta y se prueba la siguiente fuente en vez de tragarselo."""
    try:
        c = d["Close"].dropna()
        if not len(c) or (c <= 0).any():
            _avisar(f"valida.{sym}", f"{fuente}: cierres <= 0 o serie vacia — fuente descartada, se prueba la siguiente")
            return False
        if {"High", "Low"}.issubset(d.columns):
            hl = d[["High", "Low"]].dropna()
            if len(hl) and (hl["High"] < hl["Low"]).any():
                _avisar(f"valida.{sym}", f"{fuente}: barras con High < Low (datos corruptos) — fuente descartada")
                return False
        if d.index.duplicated().any():
            _avisar(f"valida.{sym}", f"{fuente}: fechas duplicadas en la serie (revisar)")
        ses = len(pd.bdate_range(d.index[0], d.index[-1]))
        if ses and len(d) < ses * 0.85:
            _avisar(f"valida.{sym}", f"{fuente}: posibles huecos ({len(d)} barras de ~{ses} sesiones esperadas)")
    except Exception:
        pass
    return True

def get_ohlcv(sym, start, end):
    pairs = ([(fetch_yahoo, "yahoo"), (fetch_stooq, "stooq")] if DATA_PRIMARY == "yahoo"
             else [(fetch_stooq, "stooq"), (fetch_yahoo, "yahoo")])
    for fn, nm in pairs:
        d = fn(sym, start, end)
        if d is not None and len(d) >= 30 and _ohlcv_valido(sym, d, nm):
            save_cache(sym, d)
            return d, nm
    # --- FALLBACK A CACHE: antes era SILENCIOSO y sin limite de edad (un rate-limit de Yahoo podia
    #     pintar el dashboard entero con precios de hace semanas sin una sola señal visual). Ahora:
    #     se mide la edad en sesiones, se avisa al panel de salud y a partir de 5 sesiones el simbolo
    #     se EXCLUYE — mejor ausente que viejo disfrazado de fresco. ---
    c = load_cache(sym)
    if c is not None:
        try:
            edad = max(0, len(pd.bdate_range(c.index[-1].date(), dt.date.today())) - 1)
        except Exception as _dege:
            _deg("get_ohlcv:1120", _dege)
            edad = 0
        if edad > 5:
            _avisar(f"datos.{sym}", f"sin fuente viva y cache de hace {edad} sesiones: simbolo EXCLUIDO del build")
            return None, "—"
        if edad >= 1:
            _avisar(f"datos.{sym}", f"Yahoo y Stooq sin respuesta: usando CACHE con {edad} sesion(es) de retraso — las señales de este simbolo van viejas")
        else:
            _avisar(f"datos.{sym}", "Yahoo y Stooq sin respuesta: usando CACHE guardada hoy")
        return c, (f"cache-{edad}d" if edad else "cache")
    return None, "—"

def to_weekly_close(series):
    # ultimo cierre disponible de cada semana, etiquetado por el VIERNES de esa semana (consistente entre
    # simbolos) PERO sin pasar de HOY: asi la semana en curso queda en UNA sola fila alineada y con fecha
    # real (no un viernes futuro), aunque Yahoo de a unos el viernes y a otros solo el jueves.
    s = series.dropna()
    if s.empty:
        return s
    last = s.groupby(s.index.to_period("W-FRI")).tail(1).copy()
    fri = last.index.to_period("W-FRI").to_timestamp(how="end").normalize()
    hoy = pd.Timestamp(dt.date.today())
    last.index = fri.where(fri <= hoy, hoy)   # la semana en curso se etiqueta HOY, no su viernes futuro
    return last

def download_all():
    end = dt.date.today()
    start = end - dt.timedelta(days=int(WEEKS * 7 * 1.6) + 60)
    symbols = [BENCH] + SECTORS + SATELLITES + THEMATIC + EXTRA + ACCIONES_SINTETICAS
    weekly = {}
    daily = {}
    sources = {}
    print(f"\nDescargando {len(symbols)} simbolos (OHLCV diario)...")
    for sym in symbols:
        d, src = get_ohlcv(sym, start, end)
        if d is None or "Close" not in d.columns:
            print(f"  {sym:5s}  sin datos")
            sources[sym] = "—"
            continue
        if src == "stooq":   # intentar refrescar el ultimo dia con Yahoo
            d, added = topup_recent(sym, d, end)
            if added:
                src = "stooq+yf"
                save_cache(sym, d)
        daily[sym] = d
        weekly[sym] = to_weekly_close(d["Close"])
        sources[sym] = src
        print(f"  {sym:5s}  {src:9s}  {len(weekly[sym])} semanas  ult {weekly[sym].index[-1].date()}")
        time.sleep(0.25)   # cortesia con la fuente
    # alinear: union de fechas + arrastre LIMITADO A 1 SEMANA. El ffill sin limite fabricaba cierres
    # (un simbolo caido semanas mostraba 0% de movimiento ficticio en el RRG). Ahora: 1 semana de
    # arrastre como maximo (avisado), y si ni con esas tiene dato reciente, el simbolo se EXCLUYE.
    df = pd.DataFrame(weekly).sort_index()
    if df.shape[1] > 0:
        min_obs = max(30, int(0.7 * df.shape[0]))
        df = df.dropna(axis=1, thresh=min_obs)
    _antes = df.copy()
    df = df.ffill(limit=1)
    try:
        _rell = {c: int((_antes[c].iloc[-8:].isna() & df[c].iloc[-8:].notna()).sum()) for c in df.columns}
        _rell = {c: n for c, n in _rell.items() if n}
        if _rell:
            _avisar("panel.semanal", "cierre semanal ARRASTRADO 1 sem (sin dato esa semana) en: "
                    + ", ".join(f"{c}×{n}" for c, n in sorted(_rell.items())))
    except Exception:
        pass
    _colgados = [c for c in df.columns if df[c].iloc[-min(len(df), 6):].isna().any()]
    if _colgados:
        for c in _colgados:
            _avisar(f"datos.{c}", "sin cierre semanal reciente ni con arrastre de 1 sem: EXCLUIDO del panel semanal")
        df = df.drop(columns=_colgados)
    df = df.dropna()
    if len(df) > WEEKS:
        df = df.iloc[-WEEKS:]
    # --- SANEADOR DE SALTOS IMPOSIBLES: un solo valor corrupto de Yahoo (un pico de escala, p.ej. SPY
    #     742 -> 74.2 una semana) NO se ve a simple vista pero ENVENENA todo: el backtest (rentabilidad
    #     y drawdown del benchmark), la fuerza relativa del RRG (todo se mide contra SPY) y el plan de
    #     caidas. Ningun ETF sin apalancar se mueve >60% en una semana: por encima de eso es error de
    #     dato. Se detecta el pico (salta y vuelve), se REPARA arrastrando el valor bueno anterior (no
    #     se inventa: se elimina la basura) y se AVISA con simbolo y semana para que quede en el panel. ---
    UMBRAL_SALTO = 0.60
    try:
        reparados = []
        for c in df.columns:
            col = df[c]
            r = col.pct_change()
            for i in range(1, len(col) - 1):
                a, b, d2 = col.iloc[i - 1], col.iloc[i], col.iloc[i + 1]
                if a and b and d2 and abs(b / a - 1) > UMBRAL_SALTO and abs(d2 / b - 1) > UMBRAL_SALTO:
                    # pico aislado: iloc[i] es el valor malo -> lo sustituyo por el anterior (bueno)
                    df.iloc[i, df.columns.get_loc(c)] = a
                    reparados.append(f"{c}@{col.index[i].date()}")
            # salto FINAL sin retorno (posible cambio de escala persistente en la ultima barra): umbral
            # mas alto (80%) para NO reparar por error un movimiento real fuerte de la ultima semana
            if len(col) >= 2 and col.iloc[-2] and abs(col.iloc[-1] / col.iloc[-2] - 1) > 0.80:
                df.iloc[-1, df.columns.get_loc(c)] = col.iloc[-2]
                reparados.append(f"{c}@{col.index[-1].date()}(final)")
        # --- CAMBIOS DE ESCALA PERSISTENTES: un salto que NO vuelve (Yahoo mezclo ^GSPC ~7400 con SPY
        #     ~740 en parte de la serie). Ya reparados los picos, cualquier salto >60% que queda es una
        #     frontera de escala: REESCALO todo el tramo ANTERIOR para que cuadre con el reciente (el
        #     que coincide con el precio en vivo). Recorro de atras hacia delante (el final es la
        #     referencia buena) para encadenar varias fronteras si las hubiera. NO se inventa nada: se
        #     corrige un factor de escala. Se avisa fuerte porque afectaba a backtest/RRG/drawdown. ---
        reparados_escala = []
        for c in df.columns:
            _loc = df.columns.get_loc(c)
            j = len(df) - 1
            while j >= 2:
                a, b = df.iloc[j - 1, _loc], df.iloc[j, _loc]
                if a and b and abs(b / a - 1) > UMBRAL_SALTO:
                    factor = b / a                      # reescala [0:j] para que empalme con df[j]
                    df.iloc[:j, _loc] = df.iloc[:j, _loc] * factor
                    reparados_escala.append(f"{c}@{df.index[j].date()} (x{factor:.3g})")
                j -= 1
        if reparados_escala:
            _avisar("datos.escala", "cambio(s) de ESCALA persistente(s) corregido(s) reescalando el tramo antiguo al reciente: "
                    + ", ".join(reparados_escala[:10]) + (f" y {len(reparados_escala)-10} mas" if len(reparados_escala) > 10 else "")
                    + " — Yahoo mezcló escalas; afectaba a backtest/RRG/drawdown")
        if reparados:
            _avisar("datos.saltos", "valores corruptos (salto >60% imposible sin apalancar) REPARADOS arrastrando el bueno anterior: "
                    + ", ".join(reparados[:12]) + (f" y {len(reparados)-12} mas" if len(reparados) > 12 else "")
                    + " — afectaban a backtest/RRG/drawdown")
    except Exception as _e:
        _avisar("datos.saltos", f"saneador de saltos no pudo ejecutarse: {_e}")
    #     Dos fuentes independientes y no se cotejaban nunca: este es el unico chequeo automatico real
    #     de "¿coincide con lo publicado?" posible sin fuente de pago. Tolerancia 1.5% (ajuste por
    #     dividendos de Yahoo puede desviar fechas antiguas; el ultimo cierre comun debe cuadrar). ---
    try:
        if BENCH in daily and daily[BENCH] is not None:
            _src_b = str(sources.get(BENCH, ""))
            _sec = (fetch_stooq(BENCH, end - dt.timedelta(days=45), end) if _src_b.startswith("yahoo")
                    else fetch_yahoo(BENCH, end - dt.timedelta(days=60), end))
            if _sec is not None and "Close" in _sec.columns:
                _a = daily[BENCH]["Close"].dropna(); _b = _sec["Close"].dropna()
                _com = _a.index.intersection(_b.index)
                if len(_com):
                    _f = _com[-1]
                    _dif = abs(float(_a.loc[_f]) / float(_b.loc[_f]) - 1) * 100
                    if _dif > 1.5:
                        _avisar("verifica.SPY", f"Yahoo y Stooq DISCREPAN un {_dif:.1f}% en el cierre del {_f.date()}: "
                                                "no te fies de las señales de hoy sin mirar el precio en el broker")
                    else:
                        print(f"  verificacion cruzada SPY ({_f.date()}): fuentes coinciden (dif {_dif:.2f}%)")
    except Exception:
        pass
    used = [v for v in sources.values() if v not in ("—",)]
    if used and not any("stooq" in v for v in used):
        print("  AVISO: Stooq no respondio en ninguna descarga (probable LIMITE DIARIO de Stooq por su IP, "
              "agravado por el universo de ~500 acciones). Se ha usado Yahoo. El cupo se restablece al dia siguiente; "
              "puedes bajar RS_UNIVERSE a 'sector' o poner DATA_PRIMARY='yahoo'.")
    return df, daily, sources

# ----------------------------------------------------------------------
# Motor RRG
# ----------------------------------------------------------------------
def rolling_z(s, win):
    m = s.rolling(win).mean()
    sd = s.rolling(win).std(ddof=0).replace(0, 1e-9)
    return (s - m) / sd

def add_sinteticos(df):
    """Construye los indices SINTETICOS: para cada cesta, cada miembro se rebasea a 100 en el
    primer punto comun y se promedia (equiponderado, rebalanceo implicito semanal). El resultado
    es UNA serie por tema que entra al RRG como una bolita mas — el pulso del bloque entero."""
    for key, cfg in SINTETICOS.items():
        try:
            members = [m for m in cfg["members"] if m in df.columns]
            # Minimo 2 miembros para que una cesta sea "el pulso de un bloque". EXCEPCION: si la cesta
            # se DISEÑO con un solo miembro (p.ej. C0-HIPER = MAGS, el unico proxy de hiperescaladores
            # en un universo UCITS), es legitima. Lo que NO se permite es una cesta de 3 que se ha
            # quedado en 1 por falta de datos: eso seria presentar un ETF suelto como si fuera el bloque.
            _disenada_sola = len(cfg["members"]) == 1
            if len(members) < (1 if _disenada_sola else 2):
                continue
            sub = df[members].dropna()
            if len(sub) < 20:
                continue
            comp = (sub / sub.iloc[0]).mean(axis=1) * 100.0
            df[key] = comp.reindex(df.index)
        except Exception as _dege:
            _deg("add_sinteticos:1299", _dege)
            continue
    return df


def compute_rrg(df):
    bench = df[BENCH]
    n = len(df)
    smooth_span = max(4, min(10, n // 6))
    z_win = max(8, min(26, n // 2))
    mom_span = max(4, min(10, n // 7))
    z_win2 = max(6, min(20, n // 3))
    SCALE = 2.4
    out = {}
    for sym in df.columns:
        if sym == BENCH:
            continue
        rs = df[sym] / bench
        smooth = rs.ewm(span=smooth_span).mean()
        ratio = (100 + SCALE * rolling_z(smooth, z_win)).clip(86, 114)
        mom_in = ratio - ratio.ewm(span=mom_span).mean()
        mom = (100 + SCALE * rolling_z(mom_in, z_win2)).clip(86, 114)
        d = pd.DataFrame({"ratio": ratio, "mom": mom}).dropna()
        if len(d) < 2:
            continue
        tail = d.iloc[-TAIL:]
        tail_dates = [ix.strftime("%d %b") for ix in tail.index]
        last = d.iloc[-1]; prev = d.iloc[-2]
        sma20 = df[sym].rolling(min(20, n - 1)).mean().iloc[-1]
        spark = rs.iloc[-min(24, len(rs)):].tolist()
        rel1 = float(rs.iloc[-1] / rs.iloc[-2] - 1) * 100 if len(rs) >= 2 else 0.0
        rel4 = float(rs.iloc[-1] / rs.iloc[-5] - 1) * 100 if len(rs) >= 5 else 0.0
        out[sym] = {
            "ratio": float(last["ratio"]), "mom": float(last["mom"]),
            "dmom": float(last["mom"] - prev["mom"]),
            "quad": quad_of(last["ratio"], last["mom"]),
            "pquad": quad_of(prev["ratio"], prev["mom"]),
            "tail": [[float(r.ratio), float(r.mom)] for r in tail.itertuples()],
            "tail_dates": tail_dates,
            "trend": bool(df[sym].iloc[-1] > sma20),
            "group": NAMES.get(sym, ("", "", ""))[2],
            "spark": [float(x) for x in spark],
            "rel1": round(rel1, 1), "rel4": round(rel4, 1),
            "ratio_series": ratio.reindex(df.index).tolist(),   # alineadas al indice (None al inicio)
            "mom_series": mom.reindex(df.index).tolist(),
        }
    return out

def quad_of(ratio, mom):
    if ratio >= 100 and mom >= 100: return "leading"
    if ratio >= 100 and mom < 100:  return "weakening"
    if ratio < 100 and mom < 100:   return "lagging"
    return "improving"

def build_alerts(rrg):
    out = []
    for s, d in rrg.items():
        q, p = d["quad"], d["pquad"]
        if q == "weakening" and p == "leading":
            out.append((s, "warn", "Pierde liderazgo -> posible recogida de beneficios. Ajusta stop / reduce."))
        elif q == "improving" and p == "lagging":
            out.append((s, "in", "Entra flujo -> acumulacion temprana. Vigilar para sobreponderar."))
        elif q == "leading" and p == "improving":
            out.append((s, "lead", "Liderazgo confirmado -> tendencia relativa al alza."))
        elif q == "lagging" and p == "weakening":
            out.append((s, "down", "Ruptura a la baja -> infraponderar / evitar."))
        elif q == "leading" and d["dmom"] < -1.2:
            out.append((s, "warn", "Impulso enfriandose dentro del liderazgo -> primera senal de aviso."))
    order = {"warn": 0, "in": 1, "down": 2, "lead": 3}
    return sorted(out, key=lambda x: order[x[1]])

def breadth_risk(rrg):
    syms = list(rrg.keys())
    if not syms:
        return {"leaders": 0, "uptrend": 0}, {"score": 0, "label": "Neutral"}
    leaders = round(100 * sum(1 for s in syms if rrg[s]["ratio"] >= 100) / len(syms))
    uptrend = round(100 * sum(1 for s in syms if rrg[s]["trend"]) / len(syms))
    off = [rrg[s]["ratio"] for s in syms if rrg[s]["group"] in ("ciclico", "sensible")]
    deff = [rrg[s]["ratio"] for s in syms if rrg[s]["group"] == "defensivo"]
    avg = lambda a: sum(a) / len(a) if a else 100
    score = avg(off) - avg(deff)
    label = "Risk-ON" if score > 1.5 else "Risk-OFF" if score < -1.5 else "Neutral"
    return {"leaders": leaders, "uptrend": uptrend}, {"score": round(score, 1), "label": label}

# ----------------------------------------------------------------------
# Flujo de dinero por volumen (OBV + Acumulacion/Distribucion)
# ----------------------------------------------------------------------
import numpy as np

def _trend(values, win=20):
    """Tendencia de una serie: cuantas desv. tipicas se mueve a lo largo de la ventana."""
    y = pd.Series(values).dropna().values
    if len(y) < 5:
        return 0.0
    y = y[-win:]
    sd = y.std() or 1.0
    z = (y - y.mean()) / sd
    x = np.arange(len(z))
    b = np.polyfit(x, z, 1)[0]
    return float(b * len(z))

def compute_volume_flow(daily, only=None):
    out = {}
    for sym, d in daily.items():
        if only is not None:
            if sym != only:
                continue
        elif sym == BENCH:
            continue
        if not {"Close", "Volume"}.issubset(d.columns):
            continue
        dd = d.dropna(subset=["Close", "Volume"]).copy()
        if len(dd) < 30:
            continue
        close = dd["Close"]; vol = dd["Volume"].astype(float)
        obv = (np.sign(close.diff().fillna(0)) * vol).cumsum()
        # CMF: None = NO CALCULABLE (sin High/Low o sin volumen). Antes se dejaba en 0.0 y salia al
        # terminal como "Neutro" medido — un dato ausente disfrazado de flujo neutro. Ahora el hueco
        # se declara (N/D) y los consumidores ya comprueban `cmf is not None` en todo el script.
        cmf = None
        if {"High", "Low"}.issubset(dd.columns):
            hi, lo = dd["High"], dd["Low"]
            rng = (hi - lo).replace(0, np.nan)
            mfm = (((close - lo) - (hi - close)) / rng).fillna(0)
            mfv = mfm * vol
            adl = mfv.cumsum()
            win = min(20, len(dd))                      # CMF de 20 sesiones (Chaikin Money Flow)
            vsum = vol.iloc[-win:].sum()
            cmf = float(mfv.iloc[-win:].sum() / vsum) if vsum else None
        else:
            adl = obv
            _avisar(f"flow.{sym}", "sin columnas High/Low: CMF no calculable — se marca N/D (antes salia 0.0 como si fuera neutro real)")
        # OBV vs su propia media (EMA ~50 sesiones = 10 semanas): tendencia y cruce reciente
        obv_ema = obv.ewm(span=50, min_periods=10).mean()
        obv_above = bool(obv.iloc[-1] > obv_ema.iloc[-1]) if obv_ema.notna().any() else False
        obv_cross = False
        if len(obv) > 7 and obv_ema.notna().iloc[-7]:
            obv_cross = bool(obv.iloc[-1] > obv_ema.iloc[-1] and obv.iloc[-7] <= obv_ema.iloc[-7])
        obv_t, adl_t, price_t = _trend(obv), _trend(adl), _trend(close)
        flow = (obv_t + adl_t) / 2
        # volumen relativo: volumen de hoy vs su media de 20 sesiones (>1.3x = ruptura con volumen)
        vol20 = float(vol.iloc[-20:].mean()) if len(vol) >= 20 else float(vol.mean())
        vol_rel = round(float(vol.iloc[-1]) / vol20, 2) if vol20 > 0 else 1.0
        vol_rel5 = round(float(vol.iloc[-5:].mean()) / vol20, 2) if (vol20 > 0 and len(vol) >= 5) else vol_rel   # volumen medio 5 sesiones vs 20 (atencion suavizada, menos ruido que 1 dia)
        vol_break = bool(vol_rel >= 1.3 and close.iloc[-1] > close.iloc[-2])   # ruptura al alza con volumen
        # --- CLIMA de las ÚLTIMAS 3 SESIONES (no solo hoy: si el petardazo fue el lunes y ejecutas el
        #     miércoles, se seguía viendo en todos lados pero un detector de "solo hoy" ya no lo miraba).
        #     🟡 CLIMAX = subida anómala (retorno >= CLIMA_Z × su sigma diaria de las 60 sesiones previas a ESE día):
        #                 si algo sube 1-1.5% al día y un día hace +3-4% y sale en portadas, suele ser agotamiento, no fuerza.
        #     🟣 CAPITULACION = lo mismo al revés: pánico de un día; la gente "se olvida" del ETF justo ahí —
        #                 el cazador de suelos empieza a vigilar (vigilar, NO comprar: falta que el flujo frene).
        #     El volumen NO es requisito (la vela anómala ES la noticia); si además vino con volumen
        #     >= CLIMA_VOL_FUERTE× se anota "con volumen" (más fiable). Manda el día MÁS RECIENTE que califique.
        ret_d = close.pct_change().dropna()
        clima, zday, ret1d, clima_hace, clima_vol = None, None, None, None, None
        if len(ret_d) >= 45:
            for _k in range(1, max(1, min(CLIMA_VENTANA, len(ret_d) - 40)) + 1):
                _rk = float(ret_d.iloc[-_k])
                _prev = ret_d.iloc[-(_k + 60):-_k]
                _sd = float(_prev.std()) if len(_prev) >= 35 else 0.0
                if not _sd or _sd <= 0:
                    continue
                _z = _rk / _sd
                if abs(_z) < CLIMA_Z:
                    continue
                _vk = None
                try:
                    _vprev = vol.iloc[-(_k + 20):-_k]
                    if len(_vprev) >= 10 and float(_vprev.mean()) > 0:
                        _vk = round(float(vol.iloc[-_k]) / float(_vprev.mean()), 2)
                except Exception as _dege:
                    _deg("compute_volume_flow:1469", _dege)
                    _vk = None
                clima = "climax" if _z > 0 else "capitulacion"
                zday, ret1d = round(_z, 1), round(_rk * 100, 1)
                clima_hace, clima_vol = _k - 1, _vk       # hace: 0=hoy, 1=ayer, 2=anteayer
                break
        # --- FLUJO NOCTURNO vs SESIÓN USA: retorno acumulado de los GAPS de apertura (20 sesiones) frente al
        #     de las sesiones USA. En internacionales (+IBIT), gap acumulado claramente positivo con CMF <= 0
        #     = 🌏 ACUMULACIÓN EXTRANJERA: el dinero entra donde el CMF no mira (su bolsa local). ---
        noct20, ses20, acum_ext = None, None, False
        try:
            if "Open" in dd.columns and len(dd) >= 25:
                _op = dd["Open"].astype(float)
                _gap = (_op / close.shift(1) - 1).iloc[-20:]
                _ses = (close / _op - 1).iloc[-20:]
                if len(_gap.dropna()) >= 15:
                    noct20 = round(float(_gap.dropna().sum()) * 100, 1)
                    ses20 = round(float(_ses.dropna().sum()) * 100, 1)
                    if sym in FLUJO_NOCTURNO_SYMS and noct20 >= FLUJO_NOCTURNO_MIN and cmf is not None and cmf <= 0:
                        acum_ext = True
        except Exception as _dege:
            _deg("compute_volume_flow:1489", _dege)
            pass
        # --- CMF MEJORANDO (flujo por tramos): CMF muestreado hoy / -1s / -2s / -3s. Tres subidas seguidas =
        #     "dejó de empeorar y gira" — aún no es CMF>0 (posición completa) pero ya justifica MANGA PEQUEÑA. ---
        cmf_mejora = False
        try:
            if {"High", "Low"}.issubset(dd.columns) and len(dd) >= 40:
                _cser = (mfv.rolling(20).sum() / vol.rolling(20).sum()).dropna()
                if len(_cser) >= 16:
                    _s0, _s1, _s2, _s3 = (float(_cser.iloc[-1]), float(_cser.iloc[-6]),
                                          float(_cser.iloc[-11]), float(_cser.iloc[-16]))
                    cmf_mejora = bool(_s0 > _s1 > _s2 > _s3)
        except Exception as _dege:
            _deg("compute_volume_flow:1501", _dege)
            pass
        diverg = None
        if cmf is not None and price_t > 0.5 and flow < -0.5 and cmf < -0.05:
            diverg = "distribucion oculta"   # precio sube pero sale dinero (CMF claramente negativo) -> aviso
        elif cmf is not None and price_t < -0.5 and flow > 0.5 and cmf > 0.05:
            diverg = "acumulacion oculta"     # precio baja pero entra dinero (CMF claramente positivo) -> temprano
        # margen anti-confusion: si el CMF esta pegado a cero (-0.05..+0.05), NO se marca divergencia
        # (dos indicadores discrepando con dinero neto ~0 es ruido, no senal)
        # etiqueta de flujo derivada DIRECTAMENTE del CMF (el mismo numero de las tablas), para que todo el
        # panel diga lo mismo: nunca "Neutro" en un sitio y "-0.06" en otro. El OBV/ADL se sigue usando aparte
        # para la 'distribucion oculta' (diverg), que es la senal fuerte.
        label = ("Acumulacion" if cmf > 0.05 else "Distribucion" if cmf < -0.05 else "Neutro") if cmf is not None else "N/D"
        out[sym] = {"flow": round(flow, 2), "label": label, "diverg": diverg,
                    "cmf": (round(cmf, 3) if cmf is not None else None), "cmf_pos": bool(cmf is not None and cmf > 0),
                    "obv_above": obv_above, "obv_cross": obv_cross,
                    "vol_rel": vol_rel, "vol_break": vol_break, "vol_rel5": vol_rel5,
                    "clima": clima, "zday": (round(zday, 1) if zday is not None else None),
                    "ret1d": (round(ret1d, 1) if ret1d is not None else None),
                    "clima_hace": clima_hace, "clima_vol": clima_vol,
                    "noct20": noct20, "ses20": ses20, "acum_ext": acum_ext, "cmf_mejora": cmf_mejora,
                    "obv_spark": obv.iloc[-min(40, len(obv)):].tolist()}
    return out

# ----------------------------------------------------------------------
# Heatmap de fuerza relativa temporal (sector vs indice en varios plazos)
# ----------------------------------------------------------------------
def compute_heatmap(daily):
    # Para cada ETF: su rendimiento MENOS el del indice en 1 sem / 1 mes / 3 meses / 6 meses.
    # Verde = bate al mercado; rojo = lo hace peor. Rojo largo + verde corto = rotacion temprana.
    if BENCH not in daily:
        return None
    bench = daily[BENCH]["Close"].dropna()
    wins = [("1 sem", 5), ("1 mes", 21), ("3 meses", 63), ("6 meses", 126)]

    def ret(s, n):
        s = s.dropna()
        if len(s) <= n:
            return None
        return float(s.iloc[-1] / s.iloc[-1 - n] - 1)

    rows = []
    for sym in SECTORS + THEMATIC + EXTRA:
        if sym not in daily or "Close" not in daily[sym]:
            continue
        s = daily[sym]["Close"]
        vals = []
        for _, n in wins:
            r, b = ret(s, n), ret(bench, n)
            vals.append(None if (r is None or b is None) else round((r - b) * 100, 1))
        short_pos = any(v is not None and v > 0 for v in vals[:2])
        long_neg = any(v is not None for v in vals[2:]) and all((v is None or v < 0) for v in vals[2:])
        rows.append({"sym": sym, "vals": vals, "turning": short_pos and long_neg})
    rows.sort(key=lambda r: (not r["turning"], -(r["vals"][1] if r["vals"][1] is not None else -999)))
    return {"cols": [w[0] for w in wins], "rows": rows}

def compute_probabilities(df, rrg, fwd=4):
    # Base historica honesta: para cada ETF y semana, cuenta cuantas senales ESTRUCTURALES
    # cumplia (0-3: precio>media40, RS-momentum>=100, momentum absoluto 3m>0) y mira el
    # retorno a 'fwd' semanas vista. Agrega: % de veces que subio y retorno medio por nivel.
    buckets = {0: [], 1: [], 2: [], 3: []}
    for sym in [c for c in df.columns if c in rrg]:
        s = df[sym]
        if len(s) < 40 + fwd:
            continue
        sma = s.rolling(40).mean()
        abs13 = s / s.shift(13) - 1
        mser = pd.Series(rrg[sym]["mom_series"], index=df.index)
        fwd_ret = s.shift(-fwd) / s - 1
        for i in range(40, len(s) - fwd):
            if pd.isna(sma.iloc[i]) or pd.isna(abs13.iloc[i]) or pd.isna(fwd_ret.iloc[i]):
                continue
            m = mser.iloc[i]
            if m is None or m != m:
                continue
            sc = int(s.iloc[i] > sma.iloc[i]) + int(m >= 100) + int(abs13.iloc[i] > 0)
            buckets[sc].append(float(fwd_ret.iloc[i]))
    stats = {}
    for sc, rets in buckets.items():
        if rets:
            n = len(rets)
            stats[sc] = {"n": n, "pup": round(100 * sum(1 for r in rets if r > 0) / n),
                         "avg": round(100 * sum(rets) / n, 1)}
        else:
            stats[sc] = {"n": 0, "pup": None, "avg": None}
    return {"stats": stats, "fwd": fwd, "weeks": len(df)}

def compute_mean_reversion(symbols):
    # Rentabilidad media anual (CAGR ~10a) vs lo que lleva en el año (YTD). Contexto de extension, NO senal.
    if not MEAN_REVERSION:
        return {}
    out = {}
    start = dt.date.today() - dt.timedelta(days=365 * 11)
    y0 = pd.Timestamp(dt.date(dt.date.today().year, 1, 1))
    for sym in symbols:
        try:
            d, _ = get_ohlcv(sym, start, dt.date.today())
            if d is None or "Close" not in d.columns:
                continue
            c = d["Close"].dropna()
            if len(c) < 250:
                continue
            yrs = (c.index[-1] - c.index[0]).days / 365.25
            if yrs < 1.5:
                continue
            cagr = ((c.iloc[-1] / c.iloc[0]) ** (1.0 / yrs) - 1.0) * 100
            cy = c[c.index >= y0]
            ytd = ((c.iloc[-1] / cy.iloc[0] - 1.0) * 100) if len(cy) > 1 else None
            out[sym] = {"cagr": round(float(cagr), 1),
                        "ytd": round(float(ytd), 1) if ytd is not None else None,
                        "yrs": round(yrs, 1),
                        "margen": round(float(cagr - ytd), 1) if ytd is not None else None}
        except Exception:
            continue
    return out

def compute_early(df, rrg):
    # Zona de ENTRADA TEMPRANA: impulso girándose al alza pero AÚN SIN EXTENDER.
    # Pilla el principio del movimiento (abajo-izquierda del RRG que empieza a curvarse),
    # antes de que sea un líder caro. Filtros: impulso acelerando, fuerza baja, poco estirado.
    rows = []
    for sym in SECTORS + THEMATIC + EXTRA:
        if sym not in df.columns or sym not in rrg:
            continue
        s = df[sym].dropna()
        if len(s) < 16:
            continue
        sma = s.rolling(min(40, len(s))).mean().iloc[-1]
        ext = float(s.iloc[-1] / sma - 1) * 100               # extensión sobre su media de 40s (%)
        ratio = float(rrg[sym]["ratio"]); mom = float(rrg[sym]["mom"])
        mser = [x for x in rrg[sym].get("mom_series", []) if x is not None]
        accel = float(mser[-1] - mser[-5]) if len(mser) >= 5 else 0.0   # aceleración del impulso (4 sem)
        early = (accel > 0) and (mom >= 99) and (ratio <= 101) and (ext <= 6)
        if early:
            score = accel * 1.0 + max(0.0, 101 - ratio) * 0.5 + max(0.0, 6 - ext) * 0.3
            rows.append({"sym": sym, "ratio": round(ratio, 1), "mom": round(mom, 1),
                         "accel": round(accel, 1), "ext": round(ext, 1),
                         "quad": rrg[sym]["quad"], "score": score})
    rows.sort(key=lambda r: -r["score"])
    return rows

def compute_mi_cartera_plan(holdings, rrg, scores, flow, chosen, df=None):
    # Compara TU cartera real con las señales y da acciones concretas por posicion.
    if not holdings:
        return None
    universe = set(SECTORS + THEMATIC + EXTRA + SATELLITES)
    # acciones -> su ETF de sector
    stock2etf = {}
    for etf, sts in SECTOR_STOCKS.items():
        for st in sts:
            stock2etf.setdefault(st.upper(), etf)
    # apalancados -> su subyacente (prefiriendo lo que seguimos)
    lev2base = {}
    for base, lev in LEV3X.items():
        for l in lev.replace("*", "").split("/"):
            l = l.strip().upper()
            if l and (l not in lev2base or base in universe):
                lev2base[l] = base

    def resolve(t):
        t = t.upper()
        # limpiar sufijos de instrumento: AAPL-CFD -> AAPL, GLD-ETC -> GLD, TLT-5L -> TLT...
        base_t = t
        for suf in ("-CFD", "-ETF", "-ETC", "-PERP", "-PVT", "-5L", "-3L", "-2X"):
            if base_t.endswith(suf):
                base_t = base_t[: -len(suf)]
                break
        # 1) alias explicito (acciones/ETFs UCITS mapeados a su ETF de referencia del terminal)
        for key in (t, base_t):
            if key in ALIAS2ETF:
                al = ALIAS2ETF[key]
                if al is None:
                    return None, "no seguido"
                return al, ("vía alias" if al != key else "ETF")
        # 2) universo directo, apalancados y acciones de SECTOR_STOCKS
        for key in (t, base_t):
            if key in universe:
                return key, "ETF"
            if key in lev2base:
                return lev2base[key], "apalancado"
            if key in stock2etf:
                return stock2etf[key], "acción"
        return None, "no seguido"

    sc_map = {r["sym"]: r for r in scores} if scores else {}
    rows = []
    held_bases = set()
    for row in holdings:
        tk, broker, eur = row[0], row[1], row[2]
        tipo = row[4] if len(row) >= 5 else "etf"
        if tipo == "cesta":
            rows.append({"tk": tk, "broker": broker, "eur": eur, "base": None, "kind": "cesta",
                         "act": "detallar", "col": "#5B8CFF",
                         "why": "cesta agregada: pega las posiciones una a una en MI_CARTERA para evaluarlas."})
            continue
        base, kind = resolve(tk)
        if base is None or base not in rrg:
            rows.append({"tk": tk, "broker": broker, "eur": eur, "base": None, "kind": kind,
                         "act": "no seguido", "col": "#5E708A",
                         "why": "no está en el universo del panel; el tool no puede evaluarlo."})
            continue
        held_bases.add(base)
        quad = rrg[base]["quad"]
        sc = sc_map.get(base, {}).get("score")
        distrib = sc_map.get(base, {}).get("distrib", False)
        qn = QUAD.get(quad, (quad, "#888"))[0]
        if distrib:
            act, col, why = "VENDER / ROTAR", "#F4607A", f"distribución oculta (sale dinero) en {base}."
        elif quad == "lagging" or (sc is not None and sc <= 2):
            act, col, why = "VENDER / ROTAR", "#F4607A", f"{base} en {qn}" + (f", scoring {sc}/5" if sc is not None else "") + " → fuera."
        elif quad == "weakening":
            act, col, why = "REDUCIR / VIGILAR", "#F4B740", f"{base} en {qn}: impulso girándose, recoger beneficios / poner stop."
        elif quad in ("leading", "improving") and (sc is None or sc >= 3):
            act, col, why = "MANTENER", "#2FD08A", f"{base} en {qn}" + (f", scoring {sc}/5" if sc is not None else "") + ": sigue fuerte."
        else:
            act, col, why = "VIGILAR", "#9FB0C8", f"{base} en {qn}, scoring {sc}/5."
        via = "" if (base == tk.upper()) else f" (vía {base})"
        # --- VEREDICTO DE CORTE vs AGUANTE + trampa de esperanza ---
        # ¿Cuánto ha caído esta posición desde su máximo reciente? ¿El flujo aún sale (trampa) o ya frena (base)?
        corte = None
        f = (flow or {}).get(base, {}) or {}
        cmf = f.get("cmf")
        dd_pos = None
        if df is not None and base in getattr(df, "columns", []):
            try:
                ser = df[base].dropna()
                if len(ser) >= 10:
                    dd_pos = float(ser.iloc[-1] / ser.iloc[-min(52, len(ser)):].max() * 100) - 100
            except Exception:
                dd_pos = None
        _sale = (cmf is not None and cmf < -0.05)
        _frena = (cmf is not None and cmf >= -0.05)
        if act.startswith("VENDER") or act.startswith("REDUCIR"):
            if _sale and dd_pos is not None and dd_pos <= -8:
                corte = ("trampa", "#F4607A", f"⛔ El sistema dice CORTAR: cae {dd_pos:.0f}% y el dinero SIGUE saliendo (CMF {cmf:+.2f}). "
                         "Aguantar aquí es «esperar a recuperar» — la trampa de esperanza que hace grandes las pérdidas pequeñas.")
            elif _frena and dd_pos is not None and dd_pos <= -8:
                corte = ("base", "#F4B740", f"⚠ Señal de salida PERO el flujo ha dejado de sangrar (CMF {cmf:+.2f}) tras caer {dd_pos:.0f}%. "
                         "Zona de posible suelo: si vas a darle margen, ponle un stop concreto — no lo dejes «a ver si sube».")
            elif _sale:
                corte = ("trampa", "#F4607A", f"El dinero sale (CMF {cmf:+.2f}) — la señal de salida está confirmada por flujo.")
        # 🌏 divergencia señalada, no reconciliada: en internacionales el CMF americano no ve la compra
        # de la bolsa local (gap nocturno). No cambia la ACCIÓN — pero se avisa para decidir con criterio.
        try:
            _fb2 = (flow or {}).get(base, {}) or {}
            if _fb2.get("acum_ext") and corte and corte[0] == "trampa":
                corte = (corte[0], corte[1], corte[2] + f" ⚠ PERO 🌏 su gap nocturno es {_fb2.get('noct20', 0):+.1f}% en 20 sesiones: "
                         "en este internacional la compra ocurre en su bolsa local y el CMF americano la infravalora — divergencia señalada; decide con el cierre del viernes.")
        except Exception:
            pass
        rows.append({"tk": tk, "broker": broker, "eur": eur, "base": base, "kind": kind,
                     "act": act, "col": col, "why": why, "quad": qn, "sc": sc, "via": via,
                     "dd_pos": dd_pos, "cmf": cmf, "corte": corte})
    # ROTAR HACIA: lo que recomienda la cartera y aún no tienes
    rec = []
    for s, d in (chosen or []):
        if s not in held_bases:
            sc = sc_map.get(s, {}).get("score")
            rec.append({"sym": s, "quad": QUAD.get(d["quad"], (d["quad"], "#888"))[0], "sc": sc})
    total = sum(r[2] for r in holdings if isinstance(r[2], (int, float)))
    return {"rows": rows, "rotar_hacia": rec, "total": total,
            "n_vender": sum(1 for r in rows if r["act"].startswith("VENDER")),
            "n_mantener": sum(1 for r in rows if r["act"] == "MANTENER")}


def compute_apalancamiento(holdings, broker_info):
    """Consolida la exposicion REAL (importe x apalancamiento) de los 3 brokers y simula
    el impacto de caidas del S&P (STRESS_DD) sobre el equity de cada broker.
    Aproximacion de choque de 1 dia: perdida = importe x apalancamiento x beta_tipo x caida.
    OJO: los productos de reset diario en un tramo de varios dias con volatilidad pierden MAS
    que esto (decay); el escenario es el suelo optimista, no el pesimista."""
    if not holdings:
        return None
    rows, por_broker = [], {}
    for row in holdings:
        tk, broker, eur = row[0], row[1], row[2]
        lev = row[3] if len(row) >= 4 else 1
        tipo = row[4] if len(row) >= 5 else "etf"
        if not isinstance(eur, (int, float)) or eur <= 0:
            continue
        beta = STRESS_BETA.get(tipo, 1.0)
        expo = eur * lev
        stress = {dd: eur * lev * beta * (dd / 100.0) for dd in STRESS_DD}
        rows.append({"tk": tk, "broker": broker, "eur": eur, "lev": lev, "tipo": tipo,
                     "beta": beta, "expo": expo, "stress": stress})
        b = por_broker.setdefault(broker, {"eur": 0.0, "expo": 0.0,
                                           "stress": {dd: 0.0 for dd in STRESS_DD}})
        b["eur"] += eur
        b["expo"] += expo
        for dd in STRESS_DD:
            b["stress"][dd] += stress[dd]
    tot_eur = sum(b["eur"] for b in por_broker.values()) or 1.0
    tot_expo = sum(b["expo"] for b in por_broker.values())
    tot_stress = {dd: sum(b["stress"][dd] for b in por_broker.values()) for dd in STRESS_DD}
    # por broker: equity tras el choque y, si hay datos de margen, el nivel de margen estimado
    brokers = []
    for name, b in por_broker.items():
        info = (broker_info or {}).get(name, {}) or {}
        equity = info.get("equity") or b["eur"]
        esc = {}
        for dd in STRESS_DD:
            loss = b["stress"][dd]
            eq_after = equity + loss
            nivel = info.get("nivel_margen")
            # aprox.: el margen requerido no cambia -> el nivel cae en proporcion al equity
            nivel_after = (nivel * eq_after / equity) if (nivel and equity) else None
            stopout = info.get("stopout")
            estado = "ok"
            pct_loss = (loss / equity * 100) if equity else 0
            if nivel_after is not None and stopout is not None:
                if nivel_after <= stopout:
                    estado = "STOP-OUT"
                elif nivel_after <= stopout * 1.6:
                    estado = "margin call"
                elif nivel_after <= 100:
                    estado = "sin margen libre"
            elif eq_after <= 0 or pct_loss <= -95:
                estado = "cuenta a cero"
            elif pct_loss <= -70:
                estado = "riesgo de liquidación"       # perpetuos/apalancados: el broker liquida mucho antes de llegar aqui
            elif pct_loss <= -45:
                estado = "pérdida severa"
            esc[dd] = {"loss": loss, "eq_after": eq_after, "pct": (loss / equity * 100 if equity else 0),
                       "nivel_after": nivel_after, "estado": estado}
        brokers.append({"broker": name, "eur": b["eur"], "expo": b["expo"],
                        "lev_ef": (b["expo"] / equity if equity else 0),
                        "equity": equity, "info": info, "esc": esc})
    brokers.sort(key=lambda x: -x["expo"])
    tot_equity = sum(x["equity"] for x in brokers) or tot_eur
    return {"rows": rows, "brokers": brokers, "tot_eur": tot_equity, "tot_expo": tot_expo,
            "lev_ef": tot_expo / tot_equity, "tot_stress": tot_stress}


def compute_candidato(cartera_syms, leaders, flow, scores, rrg):
    """De los ETFs que ESTAN en la cartera de la semana, analiza sus acciones (fuerza relativa,
    aceleracion, fase, extension) y elige UN candidato por sector + UN top absoluto.
    Criterio cuantitativo, sin discrecion: el sistema elige, tu solo ejecutas (o no)."""
    if not cartera_syms or not leaders:
        return None
    sc_map = {r["sym"]: r for r in (scores or [])}
    per = []
    for etf in cartera_syms:
        rows = leaders.get(etf) or []
        best, best_pts, razones = None, -1e9, []
        for r in rows:
            rs = r.get("rs") or 0
            hi = r.get("hi") or 0
            drs = r.get("drs") if r.get("drs") is not None else 0
            ph = r.get("phase")
            if rs < 55 or ph == "baja":
                continue                                  # ni debiles ni cayendo
            pts = float(rs)                               # base: percentil de fuerza (1-99)
            pts += min(max(drs, -25), 25) * 1.2           # aceleracion 3m del percentil
            pts += {"sube": 12, "base": 8}.get(ph, 0)     # fase sana suma
            if ph == "distrib":
                pts -= 14                                  # techo formandose resta
            if hi > 92:
                pts -= (hi - 92) * 2.0                     # extendida sobre maximos: peor entrada
            if hi < 55:
                pts -= (55 - hi) * 0.5                     # demasiado hundida: cuchillo cayendo
            if pts > best_pts:
                best_pts, best = pts, r
        if not best:
            continue
        par = sc_map.get(etf, {}) or {}
        f = (flow or {}).get(etf, {}) or {}
        cmf = f.get("cmf")
        etf_boost = (par.get("score") or 0) * 3.0
        if cmf is not None and cmf > 0.05:
            etf_boost += 10
        if par.get("distrib"):
            etf_boost -= 30
        why = []
        why.append(f"RS {best['rs']}")
        if best.get("drs"):
            why.append(f"acelera {best['drs']:+d}")
        pe, pl, _pc = PHASE_INFO.get(best.get("phase"), ("", "?", ""))
        why.append(f"fase {pe} {pl}")
        why.append(f"{best['hi']}% del max 52s")
        if par.get("score") is not None:
            why.append(f"ETF {etf} {par['score']}/5")
        if cmf is not None:
            why.append("flujo del sector " + ("entra" if cmf > 0.05 else "sale" if cmf < -0.05 else "plano"))
        per.append({"etf": etf, "stock": best, "pts": round(best_pts, 1),
                    "tot": round(best_pts + etf_boost, 1), "score_etf": par.get("score"),
                    "cmf": cmf, "why": " · ".join(why)})
    if not per:
        return None
    per.sort(key=lambda x: -x["tot"])
    return {"per": per, "top": per[0]}


# --- SENAL CONTRARIA 0/3: ledger fuera-de-muestra + tamano sugerido ---
CONTRA_FILE = os.path.join(SEGUIMIENTO_DIR, "senales_contrarias.json")
CONTRA_BAK = os.path.join(SEGUIMIENTO_DIR, "senales_contrarias.bak.json")
WIRE_FILE = os.path.join(SEGUIMIENTO_DIR, "senales_wire.json")
WIRE_BAK = os.path.join(SEGUIMIENTO_DIR, "senales_wire.bak.json")
CENTINELA_FILE = os.path.join(SEGUIMIENTO_DIR, "centinela_estado.json")

def update_wire_ledger(items, close_date):
    """Persiste las senales del wire por fecha de CIERRE (idempotente: re-ejecutar el mismo dia
    sobreescribe ese dia, no duplica). Solo guarda senales con activo concreto (sym)."""
    os.makedirs(SEGUIMIENTO_DIR, exist_ok=True)
    recs = []
    if os.path.exists(WIRE_FILE):
        try:
            with open(WIRE_FILE, "r", encoding="utf-8") as fh:
                recs = json.load(fh)
        except Exception as _dege:
            _deg("update_wire_ledger:1909", _dege)
            try:
                with open(WIRE_BAK, "r", encoding="utf-8") as fh:
                    recs = json.load(fh)
            except Exception as _dege:
                _deg("update_wire_ledger:1913", _dege)
                recs = []
    d = str(close_date)
    recs = [r for r in recs if r.get("date") != d]
    for it in (items or []):
        if it.get("sym"):
            recs.append({"date": d, "tag": it["tag"], "sym": it["sym"], "dir": int(it.get("dir", 0))})
    dates = sorted({r["date"] for r in recs})[-60:]
    keep = set(dates)
    recs = [r for r in recs if r["date"] in keep]
    try:
        with open(WIRE_FILE, "w", encoding="utf-8") as fh:
            json.dump(recs, fh, ensure_ascii=False, indent=0)
        with open(WIRE_BAK, "w", encoding="utf-8") as fh:
            json.dump(recs, fh, ensure_ascii=False, indent=0)
    except Exception:
        pass
    return recs

def analyze_wire_persistence(recs, k=8):
    """Linea de tiempo de las ultimas k sesiones por senal (tag+activo): racha final en la misma
    direccion, recurrencia y contradicciones. Un dia es ruido; tres seguidos en la misma direccion
    es un patron confirmandose; direcciones alternas es mercado de dos caras."""
    if not recs:
        return None
    dates = sorted({r["date"] for r in recs})[-k:]
    if len(dates) < 2:
        return None
    idx = {d: i for i, d in enumerate(dates)}
    sigs = {}
    for r in recs:
        if r["date"] not in idx:
            continue
        key = (r.get("tag"), r.get("sym"))
        sigs.setdefault(key, [None] * len(dates))[idx[r["date"]]] = int(r.get("dir", 0))
    out = []
    for (tag, sym), tl in sigs.items():
        pres = [v for v in tl if v is not None]
        if not pres:
            continue
        streak, dcur = 0, None
        for v in reversed(tl):
            if v is None:
                break
            if dcur is None:
                dcur = v
            if v == dcur:
                streak += 1
            else:
                break
        contradice = (len(tl) >= 2 and tl[-1] is not None and tl[-2] is not None and tl[-1] != tl[-2])
        ndirs = len(set(pres))
        if streak >= 3:
            verd, lvl = f"CONFIRMÁNDOSE — {streak} sesiones seguidas", "alta"
        elif contradice:
            verd, lvl = "⚠ contradice la sesión anterior — ruido", "ruido"
        elif ndirs > 1 and len(pres) >= 2:
            verd, lvl = "dos direcciones — mercado indeciso", "ruido"
        elif streak == 2:
            verd, lvl = "2 sesiones — a una de confirmar", "media"
        elif len(pres) >= 3:
            verd, lvl = f"recurrente ({len(pres)}/{len(dates)})", "media"
        else:
            verd, lvl = "puntual — sin validez aún", "baja"
        out.append({"tag": tag, "sym": sym, "tl": tl, "streak": streak, "n": len(pres),
                    "verd": verd, "lvl": lvl, "today": tl[-1] is not None,
                    "dir": tl[-1] if tl[-1] is not None else pres[-1], "contradice": contradice})
    out.sort(key=lambda x: (not x["today"], -x["streak"], -x["n"]))
    return {"dates": dates, "sigs": out[:14]}


def compute_contrarian(rrg, scores, flow):
    """Detecta las senales contrarias de esta semana: activos con 0-1/3 senales estructurales
    (los mas machacados), giro VERTICAL del impulso y flujo que NO sale. Es tu patron 0/3."""
    _sc3 = {}
    for r in (scores or []):
        _sc3[r["sym"]] = sum(1 for _, v in r["parts"][:3] if v)
    sigs = []
    for s, d in rrg.items():
        if s == BENCH:
            continue
        tail = d.get("tail") or []
        if len(tail) < 5:
            continue
        r_now, m_now = tail[-1]
        r_prev, m_prev = tail[-4]
        dmom, drat = m_now - m_prev, r_now - r_prev
        abajo = (d["quad"] == "lagging") or (r_now <= 96.5 and m_now <= 102)
        if not abajo or dmom < 1.5:
            continue
        vert = dmom / max(0.6, abs(drat))
        if vert < 1.8:
            continue
        n3 = _sc3.get(s)
        if n3 is None or n3 > 1:
            continue                                       # solo 0/3 y 1/3: lo dormido de verdad
        cmf = ((flow or {}).get(s, {}) or {}).get("cmf")
        if cmf is not None and cmf < -0.05:
            continue                                       # si el dinero SALE, ni contraria ni nada
        sigs.append({"sym": s, "n3": n3, "vert": round(vert, 1), "dmom": round(dmom, 1), "cmf": cmf})
    sigs.sort(key=lambda x: (x["n3"], -x["vert"]))
    return sigs[:CONTRARIAN_MAX_SIGS]

def update_contrarian_ledger(sigs, px_now, datestr, df):
    """Persiste las senales de esta semana y evalua las que ya maduraron (>= horizonte).
    Esto construye la estadistica FUERA DE MUESTRA: la unica que valida de verdad tu 64%."""
    os.makedirs(SEGUIMIENTO_DIR, exist_ok=True)
    recs = []
    if os.path.exists(CONTRA_FILE):
        try:
            with open(CONTRA_FILE, "r", encoding="utf-8") as fh:
                recs = json.load(fh)
        except Exception as _dege:
            _deg("update_contrarian_ledger:2025", _dege)
            try:
                with open(CONTRA_BAK, "r", encoding="utf-8") as fh:
                    recs = json.load(fh)
            except Exception as _dege:
                _deg("update_contrarian_ledger:2029", _dege)
                recs = []
    try:
        wk = pd.Timestamp(datestr).strftime("%G-W%V")
    except Exception:
        wk = str(datestr)
    have = {(r.get("week"), r.get("sym")) for r in recs}
    for s in (sigs or []):
        key = (wk, s["sym"])
        px = px_now.get(s["sym"])
        if key not in have and px:
            recs.append({"week": wk, "date": str(datestr), "sym": s["sym"], "px": float(px),
                         "n3": s["n3"], "vert": s["vert"]})
    recs.sort(key=lambda r: (r.get("week", ""), r.get("sym", "")))
    try:
        with open(CONTRA_FILE, "w", encoding="utf-8") as fh:
            json.dump(recs, fh, ensure_ascii=False, indent=0)
        with open(CONTRA_BAK, "w", encoding="utf-8") as fh:
            json.dump(recs, fh, ensure_ascii=False, indent=0)
    except Exception:
        pass
    # evaluacion de las maduras con las series semanales
    outs = []
    for r in recs:
        sym = r.get("sym")
        if sym not in df.columns:
            continue
        s = df[sym].dropna()
        try:
            d0 = pd.Timestamp(r.get("date"))
        except Exception:
            continue
        i = int(s.index.searchsorted(d0))
        if i >= len(s):
            continue
        if i + CONTRARIAN_HORIZON_W < len(s):
            ret = float(s.iloc[i + CONTRARIAN_HORIZON_W] / s.iloc[i] - 1.0)
            outs.append({"sym": sym, "week": r.get("week"), "ret": ret})
    stats = None
    if outs:
        wins = sum(1 for o in outs if o["ret"] > 0)
        rets = [o["ret"] for o in outs]
        avg = sum(rets) / len(rets)
        wl = [x for x in rets if x > 0]
        ll = [-x for x in rets if x <= 0]
        avg_w = (sum(wl) / len(wl)) if wl else 0.0
        avg_l = (sum(ll) / len(ll)) if ll else 0.0
        p = wins / len(outs)
        kelly = (p - (1 - p) / (avg_w / avg_l)) if (avg_w > 0 and avg_l > 0) else None
        stats = {"n": len(outs), "wins": wins, "winrate": round(100 * p),
                 "avg": round(100 * avg, 2), "avg_w": round(100 * avg_w, 2),
                 "avg_l": round(100 * avg_l, 2),
                 "kelly4": (round(max(0.0, kelly) / 4 * 100, 1) if kelly is not None else None)}
    return {"recs": recs, "stats": stats, "week": wk}



# ======================================================================
# FLOW SCORE y CONFIDENCE SCORE   (v4.2)
#
# IMPORTANTE, para que no se malinterprete lo que hacen:
#
#   FLOW SCORE (0-100) no es inteligencia nueva. Es la MISMA informacion de
#   flujo que ya calcula el terminal (CMF, OBV, divergencia, volumen), puesta
#   en una sola cifra para poder ordenar y comparar de un vistazo. Nada mas.
#
#   CONFIDENCE SCORE (0-100) mide CALIDAD DEL DATO, no probabilidad de acierto.
#   Responde a "¿cuanto me puedo fiar de lo que pone en pantalla para este
#   ETF?", NO a "¿va a subir?". Un ETF puede tener confianza 95 y caer un 20%:
#   significaria que el dato era solido y la lectura fue clara, no que acertara.
#   Deliberadamente NO existe aqui ningun motor de probabilidades: con ~70
#   semanas de muestra cualquier porcentaje de acierto seria ruido con decimales.
# ======================================================================


# ======================================================================
# OSCILADOR DE AMPLITUD ESTILO McCLELLAN   (v4.4)
#
# QUE ES Y QUE NO ES — leelo antes de operarlo:
#
#   El McClellan original (NYMO) se calcula con los avances y descensos de los
#   ~2.800 titulos del NYSE. Ese dato NO lo dan Yahoo, Stooq ni FRED, asi que
#   el terminal NO puede calcular el NYMO de verdad.
#
#   Lo que SI calcula esto es la MISMA FORMULA (publicada por los McClellan en
#   1969, de dominio publico) aplicada al universo de acciones que el terminal
#   ya descarga cada dia: el S&P 500. Se usa la version AJUSTADA POR RATIO:
#       RANA = (avances - descensos) / (avances + descensos) * 1000
#       oscilador = EMA 19 sesiones (10% trend) - EMA 39 sesiones (5% trend)
#   El ajuste por ratio existe justamente para que la escala no dependa de
#   cuantos valores tenga el universo.
#
#   AUN ASI NO ES EL NYMO. El S&P 500 son grandes valores; el NYSE incluye
#   small caps, ADRs, fondos cerrados y fondos de bonos, que se mueven distinto.
#   CONSECUENCIA PRACTICA: el umbral -100 esta calibrado sobre el NYSE y aqui
#   NO se traslada tal cual. Por eso el panel calcula ADEMAS el umbral
#   equivalente por PERCENTIL sobre la propia serie, y backtestea los dos.
#
#   Y como todo lo de esta casa: es CONTEXTO, no disparador. La senal es diaria;
#   las decisiones se siguen tomando con el cierre del viernes.
# ======================================================================

def compute_mcclellan(stock_close, min_acciones=100):
    """Devuelve la serie del oscilador (pandas Series) + diagnostico.
       None si no hay acciones suficientes: no se inventa una serie."""
    try:
        if not stock_close or len(stock_close) < min_acciones:
            return None
        px = pd.DataFrame({k: v for k, v in stock_close.items() if v is not None and len(v) > 60})
        if px.shape[1] < min_acciones:
            return None
        px = px.sort_index()
        dif = px.diff()
        adv = (dif > 0).sum(axis=1)
        dec = (dif < 0).sum(axis=1)
        tot = adv + dec
        rana = ((adv - dec) / tot.replace(0, np.nan) * 1000).dropna()
        if len(rana) < 60:
            return None
        # EMAs de Haurlan: 10% trend (=19 sesiones) y 5% trend (=39 sesiones)
        e19 = rana.ewm(alpha=0.10, adjust=False).mean()
        e39 = rana.ewm(alpha=0.05, adjust=False).mean()
        osc = (e19 - e39).dropna()
        # los primeros valores estan "calentando" las EMAs: se descartan
        osc = osc.iloc[39:]
        if len(osc) < 30:
            return None
        return {"osc": osc, "n_acciones": int(px.shape[1]), "n_sesiones": int(len(osc)),
                "ultimo": float(osc.iloc[-1]), "adv": int(adv.iloc[-1]), "dec": int(dec.iloc[-1])}
    except Exception as _dege:
        _deg("compute_mcclellan", _dege)
        return None


def mcc_disparos(osc, umbral=-100.0, confirmaciones=2):
    """Localiza la senal de Pedro: cierra por DEBAJO del umbral y despues
       encadena N cierres POR ENCIMA. Devuelve las fechas del disparo."""
    fechas, armado, seguidos = [], False, 0
    try:
        for fecha, v in osc.items():
            if v < umbral:
                armado, seguidos = True, 0
            elif armado:
                seguidos += 1
                if seguidos >= confirmaciones:
                    fechas.append(fecha)
                    armado, seguidos = False, 0
    except Exception as _dege:
        _deg("mcc_disparos", _dege)
    return fechas


def mcc_backtest(osc, bench, umbral=-100.0, confirmaciones=2, horizontes=(5, 10, 21)):
    """Que paso DESPUES de cada disparo, medido sobre el indice de referencia.
       Frecuencia observada con Wilson 95% y N a la vista. NO es una prediccion."""
    def _wilson(p, n, z=1.96):
        if not n:
            return (None, None)
        d = 1 + z * z / n
        c = (p + z * z / (2 * n)) / d
        m = z * math.sqrt(max(0.0, p * (1 - p) / n + z * z / (4 * n * n))) / d
        return (round(100 * max(0.0, c - m), 1), round(100 * min(1.0, c + m), 1))
    try:
        fechas = mcc_disparos(osc, umbral, confirmaciones)
        if not fechas or bench is None or not len(bench):
            return {"n_disparos": len(fechas), "umbral": umbral, "filas": []}
        b = bench.dropna().sort_index()
        filas = []
        for h in horizontes:
            rets = []
            for f in fechas:
                try:
                    pos = b.index.searchsorted(f)
                    if pos >= len(b) or pos + h >= len(b):
                        continue          # disparo demasiado reciente: aun no se sabe
                    rets.append(float(b.iloc[pos + h] / b.iloc[pos] - 1) * 100)
                except Exception:
                    continue
            n = len(rets)
            if not n:
                filas.append({"h": h, "n": 0})
                continue
            pos_pct = sum(1 for r in rets if r > 0) / n
            lo, hi = _wilson(pos_pct, n)
            filas.append({"h": h, "n": n, "pos": round(100 * pos_pct, 1),
                          "lo": lo, "hi": hi,
                          "media": round(sum(rets) / n, 2),
                          "peor": round(min(rets), 2), "mejor": round(max(rets), 2)})
        return {"n_disparos": len(fechas), "umbral": umbral, "filas": filas,
                "ultima": str(fechas[-1].date()) if hasattr(fechas[-1], "date") else str(fechas[-1])}
    except Exception as _dege:
        _deg("mcc_backtest", _dege)
        return {"n_disparos": 0, "umbral": umbral, "filas": []}


def mcc_umbral_percentil(osc, pct=10.0):
    """El -100 del NYSE no se traslada a otro universo. Esto devuelve el nivel
       que en ESTA serie deja por debajo el mismo % de sesiones."""
    try:
        return round(float(np.percentile(osc.dropna().values, pct)), 1)
    except Exception as _dege:
        _deg("mcc_umbral_percentil", _dege)
        return None



# ======================================================================
# AVISO DE HISTORIAL CORTO  (v4.6)
# DRAM (02-abr-2026) y NCLD son fondos recien salidos. Con menos de 40 semanas
# NO EXISTE la media de 40 semanas, asi que su scoring sale incompleto por fuerza:
# no es que puntuen mal, es que faltan datos para puntuarlos. Sin este aviso, un
# 2/5 de DRAM se lee igual que un 2/5 de XLK, y no significan lo mismo.
# El CMF y el volumen SI son fiables desde 30 sesiones: eso es lo que hay que mirar
# en ellos mientras tanto.
# ======================================================================
MIN_SEMANAS_FIABLE = 40

def semanas_de_historia(sym, df):
    try:
        if df is None or sym not in df.columns:
            return 0
        return int(df[sym].dropna().shape[0])
    except Exception as _dege:
        _deg("semanas_de_historia", _dege)
        return 0

def aviso_historial(sym, df):
    """Devuelve el texto de aviso, o '' si el ETF ya tiene historial suficiente."""
    n = semanas_de_historia(sym, df)
    if not n or n >= MIN_SEMANAS_FIABLE:
        return ""
    return f"historial corto: {n} de {MIN_SEMANAS_FIABLE} semanas — sin media de 40s, el scoring va incompleto; mira el CMF"


def compute_flow_score(sym, flow):
    """0-100 a partir del flujo YA calculado. None si no hay CMF (regla de la casa:
       sin dato no se inventa un numero, se devuelve None)."""
    f = (flow or {}).get(sym) or {}
    cmf = f.get("cmf")
    if cmf is None:
        return None
    det = []
    # 1) CMF: el nucleo. -0.20..+0.20 -> 0..45 puntos
    c = max(-0.20, min(0.20, float(cmf)))
    p_cmf = (c + 0.20) / 0.40 * 45
    det.append(("CMF %+.2f" % cmf, round(p_cmf, 1), 45))
    # 2) OBV por encima de su media: el volumen acumulado acompana
    p_obv = 15.0 if f.get("obv_above") else 0.0
    det.append(("OBV sobre su media", p_obv, 15))
    # 3) sin distribucion oculta (precio sube y dinero sale) -> penaliza fuerte
    dv = f.get("diverg")
    p_div = 0.0 if dv == "distribucion oculta" else (15.0 if dv == "acumulacion oculta" else 12.0)
    det.append(("distribucion oculta" if dv == "distribucion oculta" else
                ("acumulacion oculta" if dv == "acumulacion oculta" else "sin divergencia"), p_div, 15))
    # 4) CMF girando al alza (3 tramos seguidos subiendo)
    p_gir = 10.0 if f.get("cmf_mejora") else 0.0
    det.append(("CMF mejorando 3 tramos", p_gir, 10))
    # 5) volumen relativo: hay participacion detras del movimiento
    vr = f.get("vol_rel5") or f.get("vol_rel")
    p_vol = 0.0
    if vr is not None:
        p_vol = max(0.0, min(10.0, (float(vr) - 0.8) / 0.7 * 10))
    det.append(("volumen relativo %s" % (("%.2fx" % vr) if vr is not None else "n/d"), round(p_vol, 1), 10))
    # 6) acumulacion extranjera nocturna (solo aplica a internacionales)
    p_ext = 5.0 if f.get("acum_ext") else 0.0
    det.append(("acumulacion en su bolsa local", p_ext, 5))
    total = p_cmf + p_obv + p_div + p_gir + p_vol + p_ext
    return {"score": int(round(max(0, min(100, total)))), "det": det}


def compute_confidence(sym, df, flow, scores_row, ultimo_cierre_dias=None):
    """0-100 de CALIDAD DEL DATO. Cuatro bloques, todos verificables:
         historial (30) + coherencia entre fuentes (25) + integridad (25) + frescura (20)
       Devuelve tambien el detalle para poder ensenarlo y discutirlo."""
    det = []
    # --- 1) HISTORIAL: cuantas barras hay detras del calculo (max 30) ---
    n = 0
    try:
        if df is not None and sym in df.columns:
            n = int(df[sym].dropna().shape[0])
    except Exception as _dege:
        _deg("compute_confidence:historial", _dege)
    p_hist = max(0.0, min(30.0, n / 104.0 * 30))     # 104 semanas (2 anos) = pleno
    det.append(("historial: %d barras" % n, round(p_hist, 1), 30))
    # --- 2) COHERENCIA: cuanto se ponen de acuerdo las 5 senales del scoring ---
    #     No importa si son buenas o malas: importa que digan LO MISMO. 5-0 o 0-5
    #     es una lectura limpia; 3-2 es un empate y no deberia inspirar confianza.
    p_coh, txt_coh = 0.0, "sin scoring"
    try:
        parts = (scores_row or {}).get("parts") or []
        if parts:
            si = sum(1 for _, v in parts if v)
            tot = len(parts)
            desacuerdo = min(si, tot - si) / (tot / 2.0)      # 0 = unanime, 1 = empate
            p_coh = (1 - desacuerdo) * 25
            txt_coh = "coherencia %d/%d senales de acuerdo" % (max(si, tot - si), tot)
    except Exception as _dege:
        _deg("compute_confidence:coherencia", _dege)
    det.append((txt_coh, round(p_coh, 1), 25))
    # --- 3) INTEGRIDAD: ¿el dato base esta completo y no hubo fallos mudos? ---
    f = (flow or {}).get(sym) or {}
    p_int, faltas = 25.0, []
    if f.get("cmf") is None:
        p_int -= 12; faltas.append("sin CMF")
    if not f.get("obv_spark"):
        p_int -= 6; faltas.append("sin OBV")
    if (f.get("vol_rel5") or f.get("vol_rel")) is None:
        p_int -= 4; faltas.append("sin volumen")
    try:
        if any(sym in str(k) for k in _DEG):
            p_int -= 3; faltas.append("hubo fallos silenciosos")
    except Exception:
        pass
    p_int = max(0.0, p_int)
    det.append(("integridad: " + (", ".join(faltas) if faltas else "dato completo"), round(p_int, 1), 25))
    # --- 4) FRESCURA: cuantos dias hace del ultimo cierre usado ---
    p_fresh = 20.0
    if ultimo_cierre_dias is not None:
        p_fresh = max(0.0, 20.0 - max(0, int(ultimo_cierre_dias) - 4) * 4.0)
    det.append(("frescura: cierre de hace %s dias" % (ultimo_cierre_dias if ultimo_cierre_dias is not None else "?"),
                round(p_fresh, 1), 20))
    total = int(round(max(0, min(100, p_hist + p_coh + p_int + p_fresh))))
    etiqueta = ("ALTA" if total >= 75 else "MEDIA" if total >= 50 else
                "BAJA" if total >= 25 else "INSUFICIENTE")
    return {"score": total, "etiqueta": etiqueta, "det": det, "n": n}



# ======================================================================
# VERSION LITE — PAGINA PUBLICA / COMERCIAL   (v4.3)
#
# QUE ES: una pagina reducida, generada en el MISMO build (cero descargas
# extra), pensada para un suscriptor que no tiene el contexto de Pedro.
#
# QUE NUNCA SALE AQUI, y es deliberado:
#   - la cartera real, los importes en euros y los brokers
#   - el apalancamiento consolidado y el nivel de margen de XTB
#   - las candidatas via CFD (dependen del catalogo de un broker concreto)
#   - cualquier dato personal
# Es informacion privada y ademas su publicacion tendria implicaciones bajo
# MiFID II / CNMV. La version publica habla del MERCADO, no de una persona.
#
# QUE SI SALE: veredicto, regimen (CENTINELA), sectores de la semana a peso
# igual, flujo + confianza en el dato, track record y plan de caidas.
# El track record va DELANTE a proposito: es lo unico que hace creible el
# resto, e incluye las semanas malas.
# ======================================================================
LITE_HTML = os.path.join(SITE_DIR, "lite", "index.html")

def _lite_mod(titulo, cuerpo, sub=""):
    _s = f"<div class='sub'>{sub}</div>" if sub else ""
    return f"<section><h2>{esc(titulo)}</h2>{_s}{cuerpo}</section>"

def build_html_lite(fecha, centinela=None, chosen=None, scores=None, flow=None,
                    df=None, track=None, dd=None, regime=None, risk=None):
    """Pagina publica reducida. Cada bloque va en su propio try: si un dato falta,
       ese bloque no se dibuja y el resto de la pagina sale igual."""
    C = {"bg": "#0A0E14", "card": "#111721", "line": "#1E2735", "tx": "#D6DEEA",
         "dim": "#7A8698", "grn": "#2FD08A", "red": "#F4607A", "amb": "#FFB000"}
    H = []

    # ---------- 1. VEREDICTO ----------
    try:
        if not (centinela or {}).get("estado"):
            raise ValueError("sin centinela")
        _est = centinela["estado"]
        _col = {"RISK-ON": C["grn"], "DISTRIBUCION": C["amb"],
                "DISTRIBUCIÓN": C["amb"], "LIQUIDEZ": C["red"]}.get(_est, C["dim"])
        _conf = " · confirmado" if (centinela or {}).get("confirmado") else " · sin confirmar"
        _que = (centinela or {}).get("que") or ""
        H.append(_lite_mod("Régimen de mercado",
                 f"<div class='big' style='color:{_col}'>{esc(_est)}</div>"
                 f"<div class='sub'>{esc(_conf.strip(' ·'))}</div>"
                 + (f"<p>{esc(_que)}</p>" if _que else "")
                 + (f"<p class='dim'>Se invalida si: {esc((centinela or {}).get('inval'))}</p>"
                    if (centinela or {}).get("inval") else ""),
                 "Dónde está el dinero y qué implica"))
    except ValueError:
        pass                       # sin regimen calculado: el bloque no se dibuja
    except Exception as _dege:
        _deg("lite:veredicto", _dege)

    # ---------- 2. TRACK RECORD (delante: es lo que da credibilidad) ----------
    try:
        if track and track.get("weeks"):
            _w = track["weeks"]
            _cum = track.get("cum") or {}
            _sis = _cum.get("sistema")
            _spy = _cum.get("SPY")
            _t = ("<table><tr><th>semana</th><th>sistema</th><th>SPY</th></tr>")
            for _r in _w[-12:]:
                _v = _r.get("sistema")
                _b = _r.get("SPY")
                _c = C["grn"] if (_v or 0) >= 0 else C["red"]
                _t += (f"<tr><td>{esc(_r.get('week', ''))}</td>"
                       f"<td style='color:{_c}'>{_v:+.1f}%</td>"
                       f"<td class='dim'>{(f'{_b:+.1f}%' if _b is not None else '—')}</td></tr>")
            _t += "</table>"
            _res = ""
            if _sis is not None:
                _cc = C["grn"] if _sis >= 0 else C["red"]
                _res = (f"<div class='big' style='color:{_cc}'>{_sis * 100:+.1f}%</div>"
                        f"<div class='sub'>acumulado en {len(_w)} semanas"
                        + (f" · SPY {_spy * 100:+.1f}%" if _spy is not None else "") + "</div>")
            H.append(_lite_mod("Track record", _res + _t,
                     "Cadena real: incluye las posiciones que ganaron Y las que perdieron. "
                     "Resultados pasados no garantizan resultados futuros."))
    except Exception as _dege:
        _deg("lite:track", _dege)

    # ---------- 3. SECTORES DE LA SEMANA (a peso igual, sin importes) ----------
    try:
        _lista = chosen
        if not _lista:
            # si no se pasa, se derivan del propio scoring: puntuacion 4/5 o mas
            _lista = [r["sym"] for r in sorted((scores or []),
                      key=lambda r: -(r.get("score") or 0)) if (r.get("score") or 0) >= 4]
        if _lista:
            _b = ""
            for _c in list(_lista)[:8]:
                _sy = _c if isinstance(_c, str) else (_c.get("sym") or "")
                if _sy:
                    _b += f"<span class='tag'>{esc(_sy)}</span>"
            if _b:
                H.append(_lite_mod("Sectores de la semana", f"<div class='tags'>{_b}</div>",
                         "A peso igual. Se decide con el cierre del viernes y se ejecuta el lunes. "
                         "No es una recomendación personalizada."))
    except Exception as _dege:
        _deg("lite:sectores", _dege)

    # ---------- 4. FLUJO + CONFIANZA EN EL DATO ----------
    try:
        _srow = {r["sym"]: r for r in (scores or [])}
        _dias = None
        try:
            _dias = int((pd.Timestamp.today().normalize() - df.index[-1].normalize()).days)
        except Exception:
            pass
        _fil = []
        for _sy in (SECTORS + THEMATIC):
            _fs = compute_flow_score(_sy, flow)
            if _fs is None:
                continue
            _fil.append((_sy, _fs, compute_confidence(_sy, df, flow, _srow.get(_sy), _dias)))
        if _fil:
            _fil.sort(key=lambda x: -x[1]["score"])
            _t = "<table><tr><th>ETF</th><th>flujo</th><th>confianza en el dato</th></tr>"
            for _sy, _fs, _cf in _fil[:12]:
                _c = C["grn"] if _fs["score"] >= 65 else (C["amb"] if _fs["score"] >= 40 else C["red"])
                _t += (f"<tr><td><b>{esc(_sy)}</b></td>"
                       f"<td style='color:{_c}'>{_fs['score']}</td>"
                       f"<td class='dim'>{_cf['score']} · {_cf['etiqueta']}</td></tr>")
            _t += "</table>"
            H.append(_lite_mod("Flujo y calidad del dato", _t,
                     "Flujo 0–100 resume CMF, OBV, divergencia y volumen. Confianza mide la CALIDAD "
                     "DEL DATO (historial, coherencia entre señales, integridad, frescura), no la "
                     "probabilidad de acertar."))
    except Exception as _dege:
        _deg("lite:flujo", _dege)

    # ---------- 5. PLAN DE CAIDAS ----------
    try:
        if dd and dd.get("rungs"):
            _act = dd.get("dd")
            _cab = (f"<div class='big' style='color:{C['amb'] if (_act or 0) < -5 else C['dim']}'>"
                    f"{_act:+.1f}%</div><div class='sub'>caída actual del S&P desde máximos</div>"
                    if _act is not None else "")
            _t = "<table><tr><th>escalón</th><th>nivel S&P</th><th>alcanzado</th></tr>"
            for _r in dd["rungs"][:5]:
                _t += (f"<tr><td>−{esc(_r.get('thr'))}%</td>"
                       f"<td class='dim'>{esc(_r.get('level'))}</td>"
                       f"<td class='dim'>{'sí' if _r.get('hit') else 'no'}</td></tr>")
            _t += "</table>"
            H.append(_lite_mod("Escalones de caída del S&P 500", _cab + _t,
                     "Referencia de niveles, no predicción."))
    except Exception as _dege:
        _deg("lite:caidas", _dege)

    cuerpo = "\n".join(H) if H else "<section><p>Sin datos disponibles en esta ejecución.</p></section>"
    return f"""<!DOCTYPE html><html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rotación · lectura semanal</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;padding:16px;background:{C['bg']};color:{C['tx']};
 font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
 max-width:760px;margin:0 auto}}
header{{padding:8px 0 20px}}
h1{{font-size:19px;letter-spacing:3px;margin:0;font-weight:600}}
h2{{font-size:12px;letter-spacing:1.6px;text-transform:uppercase;color:{C['dim']};
 margin:0 0 8px;font-weight:600}}
section{{background:{C['card']};border:1px solid {C['line']};border-radius:10px;
 padding:16px;margin-bottom:12px}}
.big{{font-size:30px;font-weight:700;letter-spacing:-.5px;margin:2px 0}}
.sub{{font-size:12px;color:{C['dim']};margin-bottom:8px}}
.dim{{color:{C['dim']}}}
p{{margin:8px 0;font-size:14px}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
th{{text-align:left;font-size:10px;letter-spacing:1px;text-transform:uppercase;
 color:{C['dim']};font-weight:600;padding:4px 0;border-bottom:1px solid {C['line']}}}
td{{padding:7px 0;border-bottom:1px solid {C['line']}}}
tr:last-child td{{border-bottom:none}}
.tags{{display:flex;flex-wrap:wrap;gap:6px}}
.tag{{background:#16202E;border:1px solid {C['line']};border-radius:6px;
 padding:5px 11px;font-size:14px;font-weight:600}}
footer{{font-size:11px;color:{C['dim']};line-height:1.6;padding:14px 4px 30px}}
</style></head><body>
<header><h1>ROTACIÓN</h1>
<div class="sub">Lectura semanal de flujos · datos de cierre {esc(fecha)}</div></header>
{cuerpo}
<footer>
El flujo confirma, la narrativa propone. El sistema observa durante la semana y decide
con el cierre del viernes.<br><br>
<b>Aviso.</b> Este documento tiene finalidad exclusivamente informativa y no constituye
asesoramiento financiero, recomendación personalizada ni oferta de compra o venta de
instrumentos financieros. No tiene en cuenta la situación financiera, objetivos ni
tolerancia al riesgo de ningún destinatario concreto. Los datos proceden de cierres de
mercado con retardo y pueden contener errores. Las frecuencias históricas que aparecen
describen lo ya ocurrido y no predicen resultados futuros. Invertir conlleva riesgo de
pérdida, incluida la pérdida total del capital. Cada persona es responsable de sus
propias decisiones y debe consultar a un asesor autorizado.
</footer></body></html>"""


def compute_scores(df, rrg, daily, flow):
    # Puntuacion 0-5 por ETF (deliverable para decidir en 5 min):
    #  +1 precio > su SMA de 40 semanas | +1 RS-momentum subiendo (vs SPY)
    #  +1 momentum absoluto 3m > 0 | +1 OBV por encima de su media | +1 CMF > 0
    rows = []
    for sym in SECTORS + THEMATIC + EXTRA:
        if sym not in df.columns or sym not in rrg:
            continue
        s = df[sym].dropna()
        if len(s) < 16:
            continue
        sma = s.rolling(min(40, len(s))).mean().iloc[-1]
        price_above = bool(s.iloc[-1] > sma)
        rs_rising = bool(rrg[sym]["mom"] >= 100)
        n = min(13, len(s) - 1)
        abs_mom = float(s.iloc[-1] / s.iloc[-1 - n] - 1)
        abs_pos = bool(abs_mom > 0)
        f = flow.get(sym, {})
        diverg = f.get("diverg")
        distrib = (diverg == "distribucion oculta")     # precio sube pero el dinero sale
        obv_ok = bool(f.get("obv_above")) and not distrib  # no se puntua "entra dinero" si hay distribucion
        cmf_ok = bool(f.get("cmf_pos"))
        parts = [("precio>SMA40", price_above), ("RS subiendo", rs_rising),
                 ("mom.abs>0", abs_pos), ("OBV>media", obv_ok), ("CMF>0", cmf_ok)]
        score = sum(1 for _, v in parts if v)
        rows.append({"sym": sym, "score": score, "parts": parts, "distrib": distrib, "above_sma": price_above,
                     "obv_cross": bool(f.get("obv_cross")), "abs_mom": round(abs_mom * 100, 1)})
    rows.sort(key=lambda r: (-r["score"], -r["abs_mom"]))
    return rows

def heatmap_color(v):
    if v is None:
        return "background:#141A26;color:#3A4658"
    x = max(-1.0, min(1.0, v / 8.0))
    if x >= 0:
        return f"background:rgba(47,208,138,{0.12 + 0.78*x:.2f});color:#06140C"
    return f"background:rgba(244,96,122,{0.12 + 0.78*(-x):.2f});color:#1A0608"


def _px_en_fecha(serie, fecha):
    """Precio en la primera sesion >= fecha (busqueda por fecha en una serie)."""
    try:
        s = serie.dropna()
        idx = s.index.searchsorted(pd.Timestamp(fecha))
        if idx >= len(s):
            idx = len(s) - 1
        return float(s.iloc[idx])
    except Exception as _dege:
        _deg("_px_en_fecha:2132", _dege)
        return None

# --- PROXY DE OPCIONES para ETFs con opciones ILIQUIDAS: se leen las 2-3 acciones mas grandes
#     del ETF (sus opciones si tienen volumen) y se PROMEDIAN, diluyendo el ruido idiosincratico
#     de una sola empresa. Es SEÑAL DE APOYO etiquetada como tal: la principal sigue siendo el
#     CMF del ETF completo. Editable: anade pares ETF -> [acciones] cuando salgan mas iliquidos. ---
OPCIONES_PROXY = {
    "KRE":  ["USB", "TFC", "FITB"],      # banca regional: US Bancorp, Truist, Fifth Third
    "EWG":  ["SAP", "DB"],               # Alemania: SAP y Deutsche Bank (ADRs con opciones liquidas)
    "ITB":  ["DHI", "LEN"],              # constructoras: D.R. Horton, Lennar
    "FIW":  ["AWK", "XYL"],              # agua: American Water Works, Xylem
    "CIBR": ["PANW", "CRWD"],            # ciberseguridad: Palo Alto, CrowdStrike
}

COBERTURA_CESTAS = [
    ("SEMIS",  "Semiconductores",      ["SMH", "SOXX"]),
    ("IA",     "IA en sentido amplio", ["XLK", "IGV", "SKYY", "BOTZ", "CIBR", "QTUM", "MAGS"]),
    ("MERCADO", "Mercado (referencia)", ["SPY", "QQQ"]),
]


def compute_cobertura(options, rrg=None, flow=None, min_hist=8):
    """🛡 PANEL DE COBERTURA — ¿se estan protegiendo en semis y en IA?

    Mide el SKEW: lo que cuesta el seguro de caida frente al billete de loteria de subida.
    Concretamente, volatilidad implicita del put un 5% por debajo MENOS la del call un 5%
    por encima (ya lo calcula compute_options por ETF; aqui se agrega y se pone en contexto).

    Cuando los grandes se cubren, pagan mas por los puts y ese hueco se ensancha. Un skew
    alto en absoluto NO dice nada por si solo: el seguro de caida siempre cuesta mas que el
    de subida, en todo momento y en todo activo. Lo que informa es el skew CONTRA SU PROPIA
    HISTORIA — por eso todo aqui es percentil, no valor bruto, y por eso hace falta que el
    historico se llene antes de que el panel diga nada.

    La lectura que vale es la DIVERGENCIA, el mismo patron que la distribucion oculta pero
    en el mercado de opciones: el precio sube y a la vez la cobertura se encarece = alguien
    con dinero esta comprando el rebote y asegurandolo al mismo tiempo. Eso es no fiarse.

    LIMITE, y hay que decirlo cada vez: esto NO son flujos institucionales. Los flujos de
    verdad (order flow, prime brokerage) no son publicos, y los 13F llegan con ~3,5 meses de
    retraso. El skew mide lo que se PAGA por protegerse, no quien compra. Es un proxy.
    """
    if not options:
        return None
    try:
        _f = os.path.join(SEGUIMIENTO_DIR, "options_iv.json")
        hist = json.load(open(_f, encoding="utf-8")) if os.path.exists(_f) else {}
    except Exception as _dege:
        _deg("compute_cobertura:2180", _dege)
        hist = {}

    hoy = str(dt.date.today())

    def _rank_skew(sym, val):
        """Percentil del skew de hoy contra la propia historia de ese ETF."""
        serie = hist.get(sym) or {}
        prev = [v.get("skew") for k, v in serie.items()
                if k != hoy and isinstance(v, dict) and v.get("skew") is not None]
        if len(prev) < min_hist:
            return None, len(prev)
        return int(round(100 * sum(1 for x in prev if x <= val) / len(prev))), len(prev)

    def _skew_hace(sym, n=5):
        """Skew de hace ~n registros, para ver si se esta abriendo o cerrando."""
        serie = hist.get(sym) or {}
        ks = sorted(k for k, v in serie.items()
                    if k != hoy and isinstance(v, dict) and v.get("skew") is not None)
        if len(ks) < n:
            return None
        return serie[ks[-n]].get("skew")

    cestas = []
    for cid, titulo, syms in COBERTURA_CESTAS:
        miembros = []
        for s in syms:
            o = (options or {}).get(s) or {}
            sk = o.get("skew")
            if sk is None:
                continue
            rk, n = _rank_skew(s, sk)
            ant = _skew_hace(s)
            miembros.append({
                "sym": s, "skew": round(float(sk), 4),
                "rank": rk, "n": n,
                "delta": (round(float(sk) - float(ant), 4) if ant is not None else None),
                "pcr_oi": o.get("pcr_oi"), "iv": o.get("iv"), "iv_rank": o.get("iv_rank"),
                "proxy": bool(o.get("proxy")), "iliquido": bool(o.get("iliquido")),
            })
        if not miembros:
            cestas.append({"id": cid, "titulo": titulo, "miembros": [], "estado": "SIN DATOS",
                           "col": "#5F6A7B", "lectura": "la cadena de opciones no respondio para esta cesta",
                           "rank": None, "delta": None, "n_min": 0})
            continue

        ranks = [m["rank"] for m in miembros if m["rank"] is not None]
        deltas = [m["delta"] for m in miembros if m["delta"] is not None]
        rank_m = (sum(ranks) / len(ranks)) if ranks else None
        delta_m = (sum(deltas) / len(deltas)) if deltas else None
        n_min = min((m["n"] for m in miembros), default=0)

        # direccion del precio de la cesta (para detectar la divergencia)
        quads = [(rrg.get(m["sym"], {}) or {}).get("quad") for m in miembros] if rrg else []
        subiendo = sum(1 for q in quads if q in ("leading", "improving")) > len(quads) / 2 if quads else None

        if rank_m is None:
            estado, col = "AUN SIN BASE", "#5F6A7B"
            lectura = (f"faltan registros: hacen falta {min_hist} lecturas guardadas del skew y hay {n_min}. "
                       "El panel se llena solo, un registro por ejecucion.")
        elif rank_m >= 75:
            estado, col = "COBERTURA CARA", "#F4607A"
            lectura = "el seguro de caida esta caro frente a su propia historia: se estan protegiendo"
            if subiendo:
                estado = "COBERTURA CARA + PRECIO SUBIENDO"
                lectura = ("el precio sube Y la cobertura se encarece a la vez. Alguien compra el rebote "
                           "y lo asegura: es el mismo patron que la distribucion oculta, pero en opciones")
        elif rank_m <= 25:
            estado, col = "COBERTURA BARATA", "#2FD08A"
            lectura = ("nadie paga por protegerse frente a lo habitual: complacencia. No es senal de compra, "
                       "es ausencia de miedo — y el miedo barato es cuando conviene comprarlo, no venderlo")
        else:
            estado, col = "NORMAL", "#9FB0C8"
            lectura = "el coste de protegerse esta en su rango de siempre: sin informacion util"

        if delta_m is not None and abs(delta_m) >= 0.01 and rank_m is not None:
            lectura += (f" · se esta {'ABRIENDO' if delta_m > 0 else 'CERRANDO'} "
                        f"({delta_m:+.3f} en ~5 registros)")

        cestas.append({"id": cid, "titulo": titulo, "miembros": miembros, "estado": estado,
                       "col": col, "lectura": lectura,
                       "rank": (round(rank_m) if rank_m is not None else None),
                       "delta": (round(delta_m, 4) if delta_m is not None else None),
                       "n_min": n_min, "subiendo": subiendo})

    # comparacion relativa: ¿se cubren MAS en semis/IA que en el mercado entero?
    ref = next((c for c in cestas if c["id"] == "MERCADO" and c["rank"] is not None), None)
    for c in cestas:
        c["vs_mercado"] = (c["rank"] - ref["rank"]) if (ref and c["rank"] is not None
                                                       and c["id"] != "MERCADO") else None
    return {"cestas": cestas, "min_hist": min_hist,
            "listo": any(c["rank"] is not None for c in cestas)}


def compute_options(symbols, flow=None, daily=None, max_syms=40):
    """OPTIONS DESK — descarga cadenas de opciones de Yahoo (gratis) y calcula por ETF: put/call
    (volumen y OI), IV y su percentil aprox, skew y max pain. Si el ETF sale ILIQUIDO y tiene
    proxy definido, se analizan sus 2-3 acciones mas grandes y se promedian (señal de apoyo,
    etiquetada). La divergencia con el CMF del ETF es lo valioso. Best-effort, nunca rompe."""
    if yf is None:
        return None
    hoy = pd.Timestamp.today().normalize()
    flow = flow or {}
    # --- FASE DE SESION: el campo 'volume' de Yahoo se resetea cada dia. Un build antes o durante la
    #     sesion USA lee volumen PARCIAL (por la manyana europea, ~0): el PCR-vol es provisional y el
    #     ETF puede parecer iliquido sin serlo. Se avisa y el disparo de proxy pasa a exigir que
    #     TAMBIEN falle el OI (que es T-1 y si es estable a cualquier hora). ---
    vol_parcial = False
    try:
        from zoneinfo import ZoneInfo
        _ny = dt.datetime.now(ZoneInfo("America/New_York"))
        if _ny.weekday() < 5 and _ny.hour < 16:
            vol_parcial = True
            _avisar("options", f"build a las {_ny:%H:%M} NY (sesion USA no cerrada): volumen de opciones PARCIAL — "
                               "el PCR-vol de hoy es provisional; fiate mas del PCR-OI (T-1). El build 'bueno' es el del cierre")
    except Exception as _dege:
        _deg("compute_options:2295", _dege)
        pass

    def _analiza(tkr, spot_hint=None):
        """Analiza la cadena de UN ticker. Devuelve dict con metricas crudas o None."""
        try:
            tk = yf.Ticker(tkr)
            exps = tk.options
            if not exps:
                return None
            futuras = [e for e in exps if pd.Timestamp(e) >= hoy]
            if not futuras:
                return None
            # cada cadena se descarga UNA sola vez y se reutiliza (PCR usa 3 vtos, IV usa el de ~30d)
            _chains = {}
            def _get_chain(e):
                if e not in _chains:
                    try:
                        c = tk.option_chain(e)
                        _chains[e] = c if (c.calls is not None and len(c.calls) and c.puts is not None and len(c.puts)) else None
                    except Exception as _dege:
                        _deg("compute_options:2315", _dege)
                        _chains[e] = None
                return _chains[e]
            # MEJORA 1: PCR / OI / liquidez agregados sobre los 3 vencimientos mas cercanos (>=5d), no
            # sobre uno solo. Asi cuadra con el put/call "de portada" que muestran las webs (agregan
            # todas las fechas) y una sola fecha floja no decide. El max pain SI se queda en el
            # vencimiento mas cercano, porque es intrinsecamente por-fecha (el strike donde mas
            # opciones vencen sin valor en ESA expiracion; agregarlo no significaria nada).
            exps_pcr = [e for e in futuras if (pd.Timestamp(e) - hoy).days >= 5][:3] or futuras[:1]
            exp0 = exps_pcr[0]
            ch0 = _get_chain(exp0)
            if ch0 is None:
                return None
            calls, puts = ch0.calls, ch0.puts
            cvol = pvol = coi = poi = 0.0
            n_exp_pcr = 0
            for e in exps_pcr:
                ce = _get_chain(e)
                if ce is None:
                    continue
                cvol += float(ce.calls["volume"].fillna(0).sum())
                pvol += float(ce.puts["volume"].fillna(0).sum())
                coi  += float(ce.calls["openInterest"].fillna(0).sum())
                poi  += float(ce.puts["openInterest"].fillna(0).sum())
                n_exp_pcr += 1
            _liq_vol = (cvol >= 300 and pvol >= 100)
            _liq_oi = (coi >= 1000 and poi >= 500)
            # MEJORA 2: si el volumen viene PARCIAL (build antes del cierre USA, volumen a medio llenar),
            # no sirve para juzgar liquidez ni PCR. Mandamos SOLO por OI (estable, T-1): ni marcamos
            # iliquido por volumen flojo, ni publicamos un pcr_vol provisional que enganye.
            if vol_parcial:
                pcr_vol = None
                iliq = not _liq_oi
            else:
                pcr_vol = (pvol / cvol) if (cvol > 0 and _liq_vol) else None
                iliq = not (_liq_vol or _liq_oi)
            pcr_oi = (poi / coi) if (coi > 0 and _liq_oi) else None
            # --- CLAMP SIMÉTRICO DEL PUT/CALL. El filtro era ASIMÉTRICO: censuraba el extremo de miedo
            #     (>3.5) pero dejaba pasar el de complacencia. Un P/C de 0.2 (5 calls por cada put) es
            #     rarísimo en un ETF sectorial y casi siempre es cadena fina o dato roto — pero generaba
            #     "CONFIANZA" y, peor, la narrativa alcista "posible suelo / manos fuertes" sobre ETFs
            #     cuyo flujo estaba sangrando. Ahora la banda es simétrica en escala logarítmica
            #     (1/3.5 = 0.29): fuera de [0.29, 3.5] no es lectura, es artefacto.
            _PCR_HI, _PCR_LO = 3.5, 1 / 3.5
            _pcr_raros = []
            if pcr_vol is not None and not (_PCR_LO <= pcr_vol <= _PCR_HI):
                _pcr_raros.append(f"vol {pcr_vol:.2f}")
                pcr_vol = None
            if pcr_oi is not None and not (_PCR_LO <= pcr_oi <= _PCR_HI):
                _pcr_raros.append(f"OI {pcr_oi:.2f}")
                pcr_oi = None
            if _pcr_raros:
                _pcr_descartados.append(f"{tkr} ({', '.join(_pcr_raros)})")
            # --- SPOT: cierre diario (hint) -> fast_info validado -> NADA. Jamas se inventa: el antiguo
            #     fallback a la mediana de strikes podia desviarse 5-15% y contaminaba ATM, skew y max pain.
            spot = spot_hint
            if spot is None:
                try:
                    _fp = float(tk.fast_info["lastPrice"])
                    spot = _fp if _fp > 0 else None
                except Exception as _dege:
                    _deg("compute_options:2375", _dege)
                    spot = None
            if spot is None or spot <= 0:
                _avisar(f"options.{tkr}", "sin spot fiable (ni cierre diario ni fast_info): cadena NO analizada para no inventar el ATM")
                return None
            # --- IV y SKEW sobre el vencimiento mas cercano a ~30 dias (tenor ESTABLE): el primer
            #     vencimiento >=5d salta de semana en semana y mezclaba en options_iv.json IVs de 5, 9 y
            #     12 dias — el IV rank comparaba peras con manzanas por la estructura temporal de vol. ---
            exp_iv = min(futuras, key=lambda e: abs((pd.Timestamp(e) - hoy).days - 30))
            dte_iv = int((pd.Timestamp(exp_iv) - hoy).days)
            calls_iv, puts_iv = calls, puts
            if exp_iv != exp0:
                ch2 = _get_chain(exp_iv)
                if ch2 is not None:
                    calls_iv, puts_iv = ch2.calls, ch2.puts
                else:
                    exp_iv, dte_iv = exp0, int((pd.Timestamp(exp0) - hoy).days)
            def _calidad(dfo):
                """Strikes con cotizacion VIVA. Etapa 1: bid y ask > 0 e IV plausible. Fuera de horario
                Yahoo pone bid/ask a 0 en muchas cadenas: etapa 2 relaja bid/ask pero exige cruce
                reciente (<=5d) e IV en rango. Sin este filtro, un strike zombi con IV de hace dias
                (a veces 200-500%) entraba en la media ATM y la desplazaba varios puntos."""
                d = dfo.dropna(subset=["impliedVolatility"]).copy()
                if not len(d):
                    return d
                d = d[d["impliedVolatility"].between(0.03, 3.0)]
                e1 = d.iloc[0:0]
                try:
                    if {"bid", "ask"}.issubset(d.columns):
                        e1 = d[(d["bid"].fillna(0) > 0) & (d["ask"].fillna(0) > 0)]
                except Exception as _dege:
                    _deg("compute_options:2405", _dege)
                    e1 = d.iloc[0:0]
                if len(e1):
                    return e1
                try:
                    if "lastTradeDate" in d.columns:
                        _lt = pd.to_datetime(d["lastTradeDate"], utc=True, errors="coerce")
                        d = d[_lt >= (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=5))]
                except Exception as _dege:
                    _deg("compute_options:2413", _dege)
                    pass
                return d
            cq, pq = _calidad(calls_iv), _calidad(puts_iv)
            def _iv_near(dfo):
                d = dfo.copy()
                if not len(d):
                    return None
                d["dist"] = (d["strike"] - spot).abs()
                return float(d.nsmallest(4, "dist")["impliedVolatility"].mean())
            iv_c, iv_p = _iv_near(cq), _iv_near(pq)
            iv_atm = ((iv_c + iv_p) / 2) if (iv_c is not None and iv_p is not None) else (iv_c if iv_c is not None else iv_p)
            skew = None
            try:
                if len(pq) and len(cq):
                    p_otm = pq.iloc[(pq["strike"] - spot * 0.95).abs().argsort()[:1]]
                    c_otm = cq.iloc[(cq["strike"] - spot * 1.05).abs().argsort()[:1]]
                    if len(p_otm) and len(c_otm):
                        skew = float(p_otm["impliedVolatility"].iloc[0] - c_otm["impliedVolatility"].iloc[0])
                        if abs(skew) > 0.18:      # >18 ptos de vol entre put y call 5% OTM = cadena rota, no señal
                            skew = None
            except Exception as _dege:
                _deg("compute_options:2434", _dege)
                pass
            if iliq:
                skew = None
            maxpain = None
            try:
                strikes = sorted(set(calls["strike"]).union(set(puts["strike"])))
                coi_by = calls.set_index("strike")["openInterest"].fillna(0)
                poi_by = puts.set_index("strike")["openInterest"].fillna(0)
                best, bestval = None, None
                for K in strikes:
                    dolor = sum(float(coi_by.get(k, 0)) * max(K - k, 0) for k in strikes) + \
                            sum(float(poi_by.get(k, 0)) * max(k - K, 0) for k in strikes)
                    if bestval is None or dolor < bestval:
                        best, bestval = K, dolor
                maxpain = best
            except Exception as _dege:
                _deg("compute_options:2450", _dege)
                pass
            mp_dist = None
            if maxpain and spot:
                mp_dist = (maxpain / spot - 1) * 100
                if abs(mp_dist) > 12:
                    maxpain, mp_dist = None, None
            return {"exp": exp0, "pcr_vol": pcr_vol, "pcr_oi": pcr_oi, "iv": iv_atm, "skew": skew,
                    "maxpain": maxpain, "mp_dist": mp_dist, "spot": spot, "iliquido": iliq,
                    "dte_iv": dte_iv, "n_exp_pcr": n_exp_pcr}
        except Exception as e:
            _avisar(f"options.{tkr}", f"cadena de opciones no analizada: {type(e).__name__}: {e}")
            return None

    out = {}
    _iv_descartadas = []   # se agrupan en UN solo aviso al final (evita inundar el panel de salud)
    _pcr_descartados = []  # put/call fuera de banda plausible (cadena fina o dato roto)
    for s in symbols[:max_syms]:
        spot = None
        try:
            if daily and s in daily and daily[s] is not None:
                spot = float(daily[s]["Close"].dropna().iloc[-1])
        except Exception as _dege:
            _deg("compute_options:2472", _dege)
            pass
        m = _analiza(s, spot_hint=spot)
        if m is None:
            continue
        proxy_lbl = None
        # --- ETF iliquido con proxy definido: promediar sus acciones grandes. OJO: solo si fallan
        #     VOLUMEN y OI a la vez. Antes bastaba pcr_vol=None, y en builds de la manyana europea
        #     (volumen USA ~0) KRE y compania se leian via acciones sin ser iliquidos de verdad. ---
        if (m["iliquido"] or (m.get("pcr_vol") is None and m.get("pcr_oi") is None)) and s in OPCIONES_PROXY:
            hijos = []
            for tkr in OPCIONES_PROXY[s]:
                h = _analiza(tkr)
                if h and not h["iliquido"] and h.get("pcr_vol") is not None:
                    hijos.append((tkr, h))
            if len(hijos) >= 2:
                def _media(campo):
                    vals = [h[campo] for _, h in hijos if h.get(campo) is not None]
                    return (sum(vals) / len(vals)) if vals else None
                m = {"exp": hijos[0][1]["exp"], "pcr_vol": _media("pcr_vol"), "pcr_oi": _media("pcr_oi"),
                     "iv": _media("iv"), "skew": _media("skew"),
                     "maxpain": None, "mp_dist": None,        # el max pain de una accion no aplica al ETF
                     "spot": spot, "iliquido": False,
                     "dte_iv": hijos[0][1].get("dte_iv"),
                     "n_exp_pcr": hijos[0][1].get("n_exp_pcr")}
                proxy_lbl = "+".join(t for t, _ in hijos)
        # --- CLAMP DE IV: el campo impliedVolatility de Yahoo por strike es basura en pre-market o en
        #     strikes sin cruce (a veces 3-5% o 120-165% para ETFs de renta variable). Un rango fijo no
        #     basta: XLK a 70% "cabe" en cualquier banda pero su IV real es ~18%. Filtramos por
        #     plausibilidad REAL, comparando contra la volatilidad realizada del propio ETF:
        #       (1) banda absoluta [4%, 150%]  -> corta lo groseramente imposible aunque no haya realizada.
        #       (2) ratio IV/realizada fuera de 0.35x-4.0x -> error de dato, no una prima de riesgo real.
        #     Si no pasa: IV = "no fiable" (None) y NO se guarda en el historico (no envenena el IV rank). ---
        if m.get("iv") is not None:
            _ivv = float(m["iv"])
            _mal = not (0.04 <= _ivv <= 1.5)
            _rvnow = None
            try:
                if daily and s in daily and daily[s] is not None:
                    _rc = daily[s]["Close"].pct_change().dropna()
                    if len(_rc) > 40:
                        _rvs = (_rc.rolling(21).std() * (252 ** 0.5)).dropna()
                        if len(_rvs):
                            _rvnow = float(_rvs.iloc[-1])
            except Exception as _dege:
                _deg("compute_options:2516", _dege)
                _rvnow = None
            if _rvnow and _rvnow > 0 and not (0.35 <= _ivv / _rvnow <= 4.0):
                _mal = True
            if _mal:
                _iv_descartadas.append(f"{s} {_ivv*100:.0f}%" + (f"/{_rvnow*100:.0f}r" if _rvnow else ""))
                m["iv"] = None
        # IV percentil: solo con el historial del PROPIO ETF (en modo proxy tambien vale: comparamos
        # la IV media de sus grandes contra la vol realizada del ETF — aproximacion honesta)
        iv_pct = None
        try:
            if daily and s in daily and daily[s] is not None and m.get("iv") is not None:
                rc = daily[s]["Close"].pct_change().dropna()
                if len(rc) > 120:
                    rv = (rc.rolling(21).std() * (252 ** 0.5)).dropna()
                    if len(rv) > 60:
                        iv_pct = int(round(100 * float((rv < m["iv"]).mean())))
        except Exception as _dege:
            _deg("compute_options:2533", _dege)
            pass
        cmf = (flow.get(s, {}) or {}).get("cmf")
        diverg = None
        pcr_vol, skew = m.get("pcr_vol"), m.get("skew")
        if cmf is not None and pcr_vol is not None and not m["iliquido"]:
            if cmf > 0.05 and (pcr_vol > 1.3 or (skew is not None and skew > 0.06)):
                diverg = "flujo entra pero compran protección (posible distribución oculta)"
            elif cmf < -0.05 and pcr_vol < 0.7:
                diverg = "flujo sale pero apuestan alcista (posible suelo / manos fuertes)"
            if diverg and proxy_lbl:
                diverg += " — leído en sus acciones grandes, señal de apoyo"
        out[s] = {"exp": m.get("exp"), "pcr_vol": (round(pcr_vol, 2) if pcr_vol is not None else None),
                  "pcr_oi": (round(m["pcr_oi"], 2) if m.get("pcr_oi") is not None else None),
                  "iv": (round(m["iv"] * 100, 1) if m.get("iv") is not None else None),
                  "iv_pct": iv_pct, "skew": (round(skew * 100, 1) if skew is not None else None),
                  "maxpain": m.get("maxpain"),
                  "mp_dist": (round(m["mp_dist"], 1) if m.get("mp_dist") is not None else None),
                  "spot": (round(m["spot"], 2) if m.get("spot") else None), "cmf": cmf,
                  "diverg": diverg, "iliquido": m["iliquido"], "proxy": proxy_lbl,
                  "dte_iv": m.get("dte_iv"), "vol_parcial": vol_parcial,
                  "n_exp_pcr": m.get("n_exp_pcr")}
    # --- IV RANK REAL: se guarda la IV de cada ETF en cada ejecucion (historico propio) y, con >=10
    #     observaciones, se calcula el rank contra SU historia. El "IV pct" contra vol realizada sale
    #     inflado siempre (el seguro cotiza con prima de riesgo por naturaleza); el rank propio no. ---
    try:
        os.makedirs(SEGUIMIENTO_DIR, exist_ok=True)
        _ivf = os.path.join(SEGUIMIENTO_DIR, "options_iv.json")
        _hist = {}
        if os.path.exists(_ivf):
            try:
                _hist = json.load(open(_ivf, encoding="utf-8"))
            except Exception as _dege:
                _deg("compute_options:2565", _dege)
                _hist = {}
        _hoyk = str(dt.date.today())
        def _iv_de(v):
            # formato nuevo: {"iv": x, "dte": n, "proxy": bool}; formato viejo: float suelto
            return (v.get("iv") if isinstance(v, dict) else v)
        for s, o in out.items():
            if o.get("iv") is None and o.get("skew") is None:
                continue
            serie = _hist.setdefault(s, {})
            serie[_hoyk] = {"iv": o.get("iv"), "dte": o.get("dte_iv"), "proxy": bool(o.get("proxy")),
                            "skew": o.get("skew")}
            if len(serie) > 250:
                for k in sorted(serie)[:len(serie) - 250]:
                    serie.pop(k, None)
            # rank COMPARABLE: mismo modo (directo vs proxy) y tenor similar (+-7 dias). Antes se
            # mezclaban IVs de vencimientos distintos y de acciones-proxy con las del propio ETF.
            # Migracion suave: si aun no hay 10 observaciones comparables, se usa el historico entero
            # (comportamiento antiguo) para no dejar el rank en blanco mientras se llena.
            _dte0 = o.get("dte_iv")
            comp = [_iv_de(v) for k, v in serie.items()
                    if k != _hoyk and isinstance(v, dict) and v.get("iv") is not None
                    and bool(v.get("proxy")) == bool(o.get("proxy"))
                    and (v.get("dte") is None or _dte0 is None or abs(v["dte"] - _dte0) <= 7)]
            vals = comp if len(comp) >= 10 else [x for x in (_iv_de(v) for k, v in serie.items() if k != _hoyk) if x is not None]
            if len(vals) >= 10:
                o["iv_rank"] = int(round(100 * sum(1 for v in vals if v <= o["iv"]) / len(vals)))
                o["iv_rank_comparable"] = bool(len(comp) >= 10)
        try:
            _tmp = _ivf + ".tmp"
            json.dump(_hist, open(_tmp, "w", encoding="utf-8"))
            os.replace(_tmp, _ivf)
        except Exception as _dege:
            _deg("compute_options:2597", _dege)
            pass
    except Exception as _e_iv:
        _avisar("options.iv_rank", f"historial de IV no persistido (el IV pct usara la aproximacion): {_e_iv}")
    # UN solo aviso para TODAS las IVs descartadas (en vez de uno por ETF, que inundaba el panel).
    # En builds pre-mercado Yahoo da IVs por strike corruptas en casi todos: es NORMAL, no un fallo.
    if _iv_descartadas:
        _extra = " — build con la bolsa USA cerrada: a esta hora Yahoo da IVs poco fiables en casi todos; el build del cierre las trae limpias" if vol_parcial else ""
        _avisar("options.iv", f"IV descartada por no plausible en {len(_iv_descartadas)} ETF(s) "
                f"(no fiable vs su volatilidad realizada; no ensucia el rank): {', '.join(_iv_descartadas[:16])}"
                + (f" y {len(_iv_descartadas)-16} mas" if len(_iv_descartadas) > 16 else "") + _extra)
    if _pcr_descartados:
        _avisar("options.pcr", f"put/call fuera de banda plausible [0.29-3.5] en {len(_pcr_descartados)} ETF(s) "
                f"— cadena fina o dato roto: NO se publica ni genera narrativa alcista/bajista: {', '.join(_pcr_descartados[:12])}"
                + (f" y {len(_pcr_descartados)-12} mas" if len(_pcr_descartados) > 12 else ""))
    return out or None

def _vd_card(v):
    """Tarjeta compacta de un veredicto: ETF, las tres vías como chips, la frase en cristiano."""
    _dir_col = {"COMPRAR": "#2FD08A", "VENDER": "#F4607A"}.get(str(v.get("dir", "")).split()[0] if v.get("dir") else "", "#8FA3C0")
    _tag = " <span style='font-size:9px;color:#5B8CFF'>EN CARTERA</span>" if v.get("en_cart") else ""
    _chips = (f"<span style='font-size:9.5px;color:#8FA3C0;background:#0A1220;border-radius:4px;padding:1px 6px;margin-right:3px'>RRG: {esc(v['via_rrg'])}</span>"
              f"<span style='font-size:9.5px;color:#8FA3C0;background:#0A1220;border-radius:4px;padding:1px 6px;margin-right:3px'>flujo: {esc(v['via_flujo'])}</span>"
              f"<span style='font-size:9.5px;color:#8FA3C0;background:#0A1220;border-radius:4px;padding:1px 6px'>{esc(v['via_opc'])}</span>")
    return (f"<div style='margin:5px 0;padding:9px 12px;background:#0E1626;border-left:3px solid {v['cl_col']};border-radius:8px'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center'>"
            f"<div><b style='color:#E6EDF6;font-size:13px'>{v['sym']}</b>{_tag} "
            f"<span style='font-size:10px;color:{_dir_col};font-weight:700'>{esc(str(v.get('dir','')))}</span></div>"
            f"<div style='font-size:9px;color:{v['cl_col']}'>{esc(v['claridad'])} · {v['score']}/100</div></div>"
            f"<div style='margin:4px 0 3px'>{_chips}</div>"
            f"<div style='font-size:12px;color:#C9D6EA;line-height:1.55'>{esc(v['frase'])}</div></div>")

def veredicto_unico(fichas, options=None):
    """VEREDICTO ÚNICO: coge cada ficha (que YA cruza flujo+RRG+opciones+suelos+centinela+correlación+
    coherencia+póker+τ) y la resume en UNA sola línea en cristiano, más una etiqueta de claridad de señal.
    Ordena todo el universo de mayor a menor claridad. Es la vista de 'una mirada y lo entiendo todo'."""
    if not fichas:
        return None
    opt = options or {}
    out = []
    for f in fichas:
        s = f["sym"]
        direc = f.get("dir", f.get("direc", "ESPERAR"))
        score = f.get("score", 50)
        quad = f.get("quad", "")
        flu = f.get("flu_lbl", "neutro")
        o = opt.get(s, {})
        # --- las tres vías, cada una en una palabra ---
        via_rrg = {"leading": "líder", "improving": "mejorando", "weakening": "perdiendo fuerza",
                   "lagging": "rezagado"}.get(quad, "—")
        via_flujo = {"ENTRANDO": "entra dinero", "SALIENDO": "sale dinero", "neutro": "dinero quieto"}.get(flu, "—")
        if o.get("iliquido"):
            via_opc = "opciones sin lectura fiable"
        elif o.get("diverg") and "protección" in o["diverg"]:
            via_opc = "pero se cubren en opciones"
        elif o.get("diverg") and "suelo" in o["diverg"]:
            via_opc = "y en opciones apuestan al alza"
        elif o.get("pcr_vol") is not None and o["pcr_vol"] > 1.3:
            via_opc = "miedo en opciones"
        elif o.get("pcr_vol") is not None and o["pcr_vol"] < 0.7:
            via_opc = "confianza en opciones"
        else:
            via_opc = "opciones neutras"
        # --- coinciden las vías o se contradicen ---
        alcista_flujo = flu == "ENTRANDO"
        defensivo_opc = bool(o.get("diverg") and "protección" in o.get("diverg", ""))
        alcista_rrg = quad in ("leading", "improving")
        contradiccion = (alcista_flujo and defensivo_opc)
        # --- frase única en cristiano según la dirección del sistema ---
        if direc == "VENDER":
            frase = f"Toca salir: {via_rrg}, {via_flujo}. El sistema lo saca de la cartera."
            claridad, cl_col, orden = "SEÑAL CLARA", "#F4607A", 0
        elif direc.startswith("COMPRAR"):
            frase = f"Todo a favor: {via_rrg}, {via_flujo} y {via_opc}. La entrada más limpia."
            claridad, cl_col, orden = "SEÑAL CLARA", "#2FD08A", 0
        elif contradiccion:
            frase = f"Ojo: {via_rrg} y {via_flujo}, {via_opc}. Suben con una mano y se cubren con la otra — si estás dentro, con stop; si no, no es entrada limpia."
            claridad, cl_col, orden = "SEÑAL MIXTA", "#F4B740", 1
        elif o.get("diverg") and "suelo" in o.get("diverg", ""):
            frase = f"Posible suelo: {via_flujo} pero en opciones apuestan al alza. A veces es la huella de manos fuertes. Vigilar, no perseguir."
            claridad, cl_col, orden = "A VIGILAR", "#4CC2E0", 2
        elif f.get("veto_coh") or (f.get("concl", "").startswith("Lo frena su tema espejo")):
            frase = f"Su gráfico va bien pero lo frena su tema espejo en EE.UU. No fiarse de la fuerza local hasta que el espejo mejore."
            claridad, cl_col, orden = "A VIGILAR", "#4CC2E0", 2
        elif alcista_rrg and alcista_flujo:
            frase = f"Bien pero en espera: {via_rrg}, {via_flujo}, {via_opc}. Lo frena el mercado, no él. Mantener sin añadir."
            claridad, cl_col, orden = "EN ESPERA", "#8FA3C0", 3
        elif quad == "lagging" and not alcista_flujo:
            frase = f"Fuera de juego: {via_rrg}, {via_flujo}. Nada que hacer aquí ahora."
            claridad, cl_col, orden = "EVITAR", "#6B7B94", 4
        else:
            frase = f"Sin señal fuerte: {via_rrg}, {via_flujo}, {via_opc}. Esperar a que se defina."
            claridad, cl_col, orden = "EN ESPERA", "#8FA3C0", 3
        # nota de póker (rebote táctico), si la hay
        pk = f.get("poker")
        extra = ""
        if pk is not None and pk >= 7:
            extra = f" · 🎰 rebote táctico {pk}/10 (aparte de la rotación, en contado)"
        out.append({"sym": s, "en_cart": f.get("en_cart"), "dir": direc, "score": score,
                    "via_rrg": via_rrg, "via_flujo": via_flujo, "via_opc": via_opc,
                    "frase": frase + extra, "claridad": claridad, "cl_col": cl_col,
                    "orden": (0 if f.get("en_cart") else orden + 1)})
    # cartera primero, luego por claridad de señal (0=más clara), y dentro por score
    out.sort(key=lambda x: (x["orden"], -x["score"]))
    return out or None

def explicar_opciones(options, flow=None, rrg=None, cartera=None):
    """Traduce el OPTIONS DESK a LENGUAJE LLANO, ETF a ETF, cruzado con el flujo (CMF) y el cuadrante RRG.
    Analogia unica en todo el texto: un PUT es un SEGURO contra caidas; un CALL es una APUESTA a subir;
    la IV es el PRECIO del seguro. Devuelve lista de dicts ordenada: cartera primero, divergencias despues."""
    if not options:
        return None
    flow, rrg, cartera = flow or {}, rrg or {}, set(cartera or [])
    _Q = {"leading": "es de los líderes del mercado", "improving": "está mejorando (dejando de ser débil)",
          "weakening": "está perdiendo fuerza", "lagging": "está entre los rezagados"}
    out = []
    for s, o in options.items():
        frases = []
        g = rrg.get(s, {})
        cmf = (flow.get(s, {}) or {}).get("cmf")
        # 1) situacion del ETF en una frase
        est = _Q.get(g.get("quad"), "")
        flu = ("y el dinero de contado ESTÁ ENTRANDO" if (cmf is not None and cmf > 0.05)
               else "y el dinero de contado ESTÁ SALIENDO" if (cmf is not None and cmf < -0.05)
               else "con el dinero de contado quieto")
        if est:
            frases.append(f"El ETF {est}, {flu}.")
        # 2) que dicen las opciones, en cristiano
        pcr, ivp, sk, mp = o.get("pcr_vol"), o.get("iv_pct"), o.get("skew"), o.get("mp_dist")
        if o.get("proxy"):
            frases.append(f"Las opciones del propio ETF apenas se mueven, así que miro las de sus empresas más grandes ({o['proxy'].replace('+', ', ')}) — es una pista de apoyo, no la señal principal.")
        if o.get("iliquido"):
            frases.append("Sus opciones se mueven muy poco (mercado ilíquido): no hay lectura fiable aquí, ignóralas y guíate por el flujo de contado.")
        # INCOHERENCIA CORREGIDA: antes se decía "ignóralas" y a continuación se soltaban afirmaciones
        # sobre seguros, IV y skew de esa MISMA cadena ilíquida (el caso XRT: "ignóralas" + "el seguro
        # está caro, esperan algo gordo"). Si no hay lectura fiable, no se afirma nada de opciones.
        _fiable = not o.get("iliquido")
        _combo = (_fiable and pcr is not None and pcr < 0.7 and sk is not None and sk > 6)
        if _fiable and pcr is not None:
            if _combo:
                frases.append(f"Se compran pocos seguros ({pcr:.1f} por apuesta alcista), pero los pocos que se compran se pagan CAROS y contra caídas: confianza en la superficie, cobertura discreta por debajo.")
            elif pcr > 1.3:
                frases.append(f"En opciones se compran {pcr:.1f} seguros contra caídas por cada apuesta a subir: hay MIEDO.")
            elif pcr < 0.7:
                frases.append(f"Casi nadie compra seguro (solo {pcr:.1f} por apuesta alcista): CONFIANZA, a veces exceso de ella.")
            else:
                frases.append("Los seguros y las apuestas alcistas están equilibrados: sin señal fuerte por aquí.")
        if _fiable and o.get("iv_rank") is not None:
            if o["iv_rank"] >= 85:
                frases.append(f"El seguro está más caro que el {o['iv_rank']}% de los últimos meses: esperan movimiento fuerte pronto (mira News: suele haber un catalizador con fecha).")
            elif o["iv_rank"] <= 15:
                frases.append("El seguro está más barato que de costumbre: nadie espera sustos a corto plazo.")
        elif _fiable and ivp is not None:
            # aproximacion IV-vs-movimiento-real: el seguro SIEMPRE cotiza con prima, asi que solo los extremos dicen algo
            if ivp >= 97:
                frases.append("El seguro está caro incluso para lo habitual (y el seguro casi siempre cuesta más que el movimiento real): esperan algo gordo.")
            elif ivp <= 20:
                frases.append("El seguro está barato: nadie espera sustos a corto plazo.")
        if _fiable and sk is not None and sk > 6 and not _combo:
            frases.append("Además pagan un EXTRA por protegerse de caídas concretamente (no de subidas): temen el lado de abajo.")
        elif _fiable and sk is not None and sk < 0:
            frases.append("Curioso: la apuesta a subir cuesta MÁS que el seguro — apetito alcista poco habitual.")
        if _fiable and mp is not None and abs(mp) >= 2:
            frases.append(f"El vencimiento de opciones «tira» del precio hacia un {mp:+.1f}% desde aquí (efecto imán del tercer viernes; se disipa al pasar).")
        # 3) VEREDICTO: el cruce de las dos vias (contado vs opciones), en una frase
        if o.get("iliquido"):
            ver, vcol, prio = "— Opciones ilíquidas: aquí no aportan nada, decide solo con el flujo de contado.", "#8FA3C0", 3
            out.append({"sym": s, "frases": frases, "ver": ver, "vcol": vcol,
                        "en_cart": s in cartera, "prio": (0 if s in cartera else prio)})
            continue
        defensivo = bool((pcr is not None and pcr > 1.3) or (sk is not None and sk > 6))
        confiado = bool(pcr is not None and pcr < 0.7)
        if cmf is not None and cmf > 0.05 and defensivo:
            ver, vcol, prio = "⚠ Suben con una mano y se protegen con la otra: si estás dentro, mantén pero con stop puesto; si estás fuera, no es entrada limpia.", "#F4B740", 0
        elif cmf is not None and cmf > 0.05 and not defensivo:
            ver, vcol, prio = "✓ Todo alineado: entra dinero y nadie compra pánico. La señal más limpia que da este panel.", "#2FD08A", 2
        elif cmf is not None and cmf < -0.05 and confiado:
            ver, vcol, prio = "🎯 El contado vende pero en opciones apuestan a subir: a veces es la huella de manos fuertes en un suelo. Vigilar, no perseguir.", "#4CC2E0", 1
        elif cmf is not None and cmf < -0.05 and defensivo:
            ver, vcol, prio = "✗ Dinero saliendo Y miedo en opciones: las dos vías dicen lo mismo — no es tu sitio ahora.", "#F4607A", 1
        else:
            ver, vcol, prio = "— Sin lectura clara: las opciones no añaden nada al flujo esta semana.", "#8FA3C0", 3
        if o.get("proxy") and prio <= 2:
            ver += " (Leído en sus acciones grandes, no en el ETF: tómalo como apoyo, la señal que manda es el flujo.)"
        out.append({"sym": s, "frases": frases, "ver": ver, "vcol": vcol,
                    "en_cart": s in cartera, "prio": (0 if s in cartera else prio)})
    out.sort(key=lambda x: (x["prio"], x["sym"]))
    return out or None

# ----------------------------------------------------------------------
# HISTORIAL COMPLETO DE EPISODIOS: cada entrada->salida que el sistema ha dado,
# PERDIDAS INCLUIDAS. Un episodio = racha de semanas consecutivas dentro de la cesta.
# Entrada = precio grabado el viernes de entrada; salida = precio grabado el viernes
# en que el sistema lo saco (o valoracion actual si sigue abierto). El acumulado
# encadena TODOS los episodios del ETF (compuesto), sin borrar los malos: la
# transparencia de los fallos es parte del producto (el edge es evitar perdidas,
# y eso solo se demuestra ensenando tambien las que no se evitaron).
# ----------------------------------------------------------------------
def episodios_cartera(recs, df=None, cur_week=None):
    try:
        rows = sorted([r for r in (recs or []) if r.get("week")], key=lambda r: r.get("week", ""))
        if len(rows) < 2:
            return None
        todos = sorted({s for r in rows for s in r.get("basket", [])})
        out = []
        for s in todos:
            eps, dentro, ent_px, ent_wk, ent_spy = [], False, None, None, None
            for r in rows:
                en_cesta = s in r.get("basket", [])
                px = (r.get("px", {}) or {}).get(s)
                spy = (r.get("px", {}) or {}).get("SPY")
                if en_cesta and not dentro:
                    dentro, ent_px, ent_wk, ent_spy = True, px, r.get("week"), spy
                elif not en_cesta and dentro:
                    # salida: el viernes en que YA NO esta. Precio de salida = px grabado ese viernes
                    # (el ledger graba todo el universo); si falta, por fecha en df.
                    sal_px = px
                    if (sal_px is None or sal_px != sal_px) and df is not None and s in df.columns and r.get("date"):
                        sal_px = _px_en_fecha(df[s], r.get("date"))
                    ret = ((sal_px / ent_px - 1) * 100) if (ent_px and sal_px) else None
                    rspy = ((spy / ent_spy - 1) * 100) if (ent_spy and spy) else None
                    eps.append({"in": ent_wk, "out": r.get("week"), "ret": ret, "spy": rspy, "abierto": False})
                    dentro, ent_px, ent_wk, ent_spy = False, None, None, None
            if dentro:
                # episodio abierto: valorar al ultimo dato disponible
                ult = rows[-1]
                sal_px = (ult.get("px", {}) or {}).get(s)
                spy_f = (ult.get("px", {}) or {}).get("SPY")
                if (sal_px is None) and df is not None and s in df.columns:
                    try:
                        sal_px = float(df[s].dropna().iloc[-1])
                    except Exception:
                        sal_px = None
                ret = ((sal_px / ent_px - 1) * 100) if (ent_px and sal_px) else None
                rspy = ((spy_f / ent_spy - 1) * 100) if (ent_spy and spy_f) else None
                eps.append({"in": ent_wk, "out": None, "ret": ret, "spy": rspy, "abierto": True})
            eps_val = [e for e in eps if e["ret"] is not None]
            if not eps_val:
                continue
            acum = 1.0
            for e in eps_val:
                acum *= (1 + e["ret"] / 100)
            acum = (acum - 1) * 100
            acum_spy = 1.0
            spy_ok = all(e["spy"] is not None for e in eps_val)
            if spy_ok:
                for e in eps_val:
                    acum_spy *= (1 + e["spy"] / 100)
                acum_spy = (acum_spy - 1) * 100
            else:
                acum_spy = None
            out.append({"sym": s, "eps": eps, "n": len(eps_val),
                        "gan": sum(1 for e in eps_val if e["ret"] > 0),
                        "acum": round(acum, 1),
                        "acum_spy": (round(acum_spy, 1) if acum_spy is not None else None),
                        "abierto": any(e["abierto"] for e in eps)})
        out.sort(key=lambda x: -x["acum"])
        return out or None
    except Exception as e:
        _avisar("episodios", f"historial de episodios no calculado: {e}")
        return None

# ----------------------------------------------------------------------
# FICHAS DE DECISION (pestana Operativa rediseñada): recopila TODO lo que ya
# calcula el terminal (RRG, flujo, scores, suelos, centinela, plan, correlaciones)
# y lo sintetiza en una ficha por activo: score 0-100, semaforos, direccion,
# motivos a favor/en contra y ranking con deduplicacion de exposiciones gemelas.
# Principio: MENOS ES MAS — la pantalla decide, el detalle queda plegado.
# ----------------------------------------------------------------------
PADRE_SECTOR = {"SMH": "XLK", "SOXX": "XLK", "IGV": "XLK", "SKYY": "XLK", "CIBR": "XLK", "QTUM": "XLK",
                "BOTZ": "XLI", "ARKK": "XLK", "ARKF": "XLF", "ARKX": "XLI", "UFO": "XLI", "DRIV": "XLY",
                "XBI": "XLV", "KRE": "XLF", "ITB": "XLY", "XRT": "XLY", "JETS": "XLI",
                "XOP": "XLE", "OIH": "XLE", "TAN": "XLU", "ICLN": "XLU", "FAN": "XLU", "HYDR": "XLU",
                "GRID": "XLU", "PAVE": "XLI", "XME": "XLB", "GDX": "XLB", "SIL": "XLB", "SLV": "XLB",
                "MOO": "XLB", "FIW": "XLU", "CGW": "XLU",
                "KWEB": "XLK", "FXI": "XLF", "EWJ": "XLF", "INDA": "XLK", "EWZ": "XLB",
                "VGK": "XLF", "EWY": "XLK", "EWG": "XLI", "EWP": "XLF", "MAGS": "XLK", "IBIT": None}
GEMELOS_FIJOS = [("SMH", "SOXX"), ("XLE", "XOP", "OIH"), ("TAN", "ICLN", "FAN"),
                 ("GDX", "SIL"), ("KWEB", "FXI"), ("ARKK", "ARKF"), ("FIW", "CGW")]

def _semaforo(v):
    return "🟢" if v >= 65 else ("🟡" if v >= 45 else "🔴")

def compute_fichas(df, daily, rrg, flow, scores, suelo, centinela, plan, chosen, mi_syms, analogos=None, tau=None, desks=None, options=None):
    try:
        score_by = {r["sym"]: r for r in (scores or [])}
        suelo_by = {r["sym"]: r for r in (suelo or [])}
        poker_by = {d["sym"]: d for d in (desks or []) if d and d.get("sym")}
        universo = [s for s in (SECTORS + THEMATIC + EXTRA) if s in rrg and s in df.columns]
        rets_w = df.pct_change().iloc[-26:]                       # 26 semanas para correlaciones
        # --- contexto de mercado (igual para todos) ---
        dd_now = (plan or {}).get("dd", 0) or 0
        est_cent = (centinela or {}).get("estado", "")
        mkt = {"ROTACION": 78, "ACUMULACION": 82, "TRANSICION": 55, "DISTRIBUCION": 25}.get(est_cent, 55)
        mkt = max(5, min(95, mkt + (10 if dd_now > -2 else (-12 if dd_now <= -5 else 0))))
        cartera_set = set(chosen or []) | set(mi_syms or [])
        vols = {}
        for s in universo:
            try:
                dd_ = daily.get(s)
                vols[s] = float(dd_["Close"].pct_change().iloc[-63:].std()) if dd_ is not None else None
            except Exception as _dege:
                _deg("compute_fichas:2898", _dege)
                vols[s] = None
        vlist = sorted(v for v in vols.values() if v is not None)
        def _volpct(s):
            v = vols.get(s)
            if v is None or not vlist:
                return 50
            return int(100 * sum(1 for x in vlist if x <= v) / len(vlist))
        fichas = []
        for s in universo:
            g = rrg[s]; f = flow.get(s, {}); sc = score_by.get(s, {}); su = suelo_by.get(s)
            quad, cmf = g["quad"], f.get("cmf")
            distrib = (f.get("diverg") == "distribucion oculta")
            # componente ETF (fuerza propia)
            base_q = {"leading": 78, "improving": 60, "weakening": 38, "lagging": 22}[quad]
            c_etf = base_q + (10 if g.get("trend") else 0) + max(-12, min(12, (g["mom"] - 100) * 2.5))
            c_etf = max(3, min(97, c_etf))
            # sector padre
            padre = PADRE_SECTOR.get(s, s if s in SECTORS else None)
            if padre and padre in rrg:
                gq = rrg[padre]["quad"]
                c_sec = {"leading": 82, "improving": 62, "weakening": 38, "lagging": 20}[gq] + max(-8, min(8, rrg[padre]["dmom"] * 3))
                sec_lbl = f"{padre} {gq}"
            else:
                c_sec, sec_lbl = c_etf, "—"
            c_sec = max(3, min(97, c_sec))
            # industria = fuerza del ETF RELATIVA a su padre (RS 13 semanas)
            c_ind = 50
            if padre and padre in df.columns and s in df.columns:
                try:
                    rsp = (df[s] / df[padre]).dropna()
                    ch = float(rsp.iloc[-1] / rsp.iloc[-min(13, len(rsp) - 1) - 1] - 1) * 100
                    c_ind = max(5, min(95, 50 + ch * 3))
                except Exception as _dege:
                    _deg("compute_fichas:2931", _dege)
                    pass
            # flujo institucional
            if cmf is None:
                c_flu, flu_lbl = 50, "sin dato"
            else:
                c_flu = 85 if cmf > 0.10 else 70 if cmf > 0.05 else 50 if cmf > -0.05 else 32 if cmf > -0.10 else 15
                if f.get("obv_above"): c_flu = min(97, c_flu + 8)
                if f.get("cmf_mejora"): c_flu = min(97, c_flu + 8)
                if distrib: c_flu = max(3, c_flu - 22)
                flu_lbl = "ENTRANDO" if cmf > 0.05 else "SALIENDO" if cmf < -0.05 else "neutro"
            # riesgo (mas alto = mas seguro)
            vp = _volpct(s)
            c_rie = 100 - vp
            hi52 = None
            try:
                dcl = daily.get(s)["Close"].dropna()
                hi52 = float(dcl.iloc[-1] / dcl.iloc[-252:].max() * 100)
            except Exception as _dege:
                _deg("compute_fichas:2949", _dege)
                pass
            if hi52 is not None:
                if hi52 >= 97: c_rie -= 12                       # extendida en maximos
                if hi52 <= 72 and not (su and su["pts"] >= 8): c_rie -= 15   # cuchillo cayendo sin suelo
            if s in SECTORES_EXPLOSIVOS: c_rie -= 8
            c_rie = max(3, min(97, c_rie))
            # correlacion con lo ya abierto
            c_cor, cor_lbl = 85, "libre"
            try:
                otros = [x for x in cartera_set if x != s and x in rets_w.columns]
                if otros and s in rets_w.columns:
                    cmax, cwho = 0.0, ""
                    for o in otros:
                        cv = rets_w[s].corr(rets_w[o])
                        if cv == cv and abs(cv) > cmax:
                            cmax, cwho = abs(cv), o
                    c_cor = 88 if cmax < .5 else 60 if cmax < .8 else 28
                    cor_lbl = f"max {cmax:.2f} con {cwho}" if cwho else "libre"
            except Exception as _dege:
                _deg("compute_fichas:2968", _dege)
                pass
            # divergencia de OPCIONES (antes del score): flujo entra pero compran proteccion = 2a via de distribucion
            _opt = (options or {}).get(s) if options else None
            _opt_prot = bool(_opt and _opt.get("diverg") and "protección" in _opt["diverg"])
            if _opt_prot:
                c_flu = max(3, c_flu - 8)                      # dos vías discrepan: baja el flujo antes de puntuar
            # score global ponderado (0-100): ETF y flujo son el núcleo; sector, mercado, riesgo y correlación modulan
            score = int(round(c_etf * .25 + c_flu * .25 + c_sec * .15 + mkt * .15 + c_rie * .10 + c_cor * .10))
            # --- FILTRO DE COHERENCIA: un ETF internacional NO puede salir fuerte si su tema espejo US está débil.
            #     EEM/EWY/INDA son semis+China disfrazados: cuando SMH/KWEB sangran, ellos sangran (lección Samsung jul-2026).
            #     Veto duro: si el espejo está en Debilitándose/Rezagado -> nunca COMPRAR, solo ESPERAR, y se penaliza el score. ---
            veto_coh, coh_txt = False, ""
            _coh = COHERENCIA_TEMA.get(s)
            if _coh:
                tema, espejos = _coh
                quads_esp = [rrg[e]["quad"] for e in espejos if e in rrg]
                if quads_esp:
                    espejos_vivos = [e for e in espejos if e in rrg]
                    debiles = [e for e, q in zip(espejos_vivos, quads_esp) if q in ("weakening", "lagging")]
                    # semis (SMH/SOXX) tienen peso dominante en EEM/EWY: con UNO débil basta.
                    # Para el resto, se exige mayoría de los espejos débiles.
                    semis_debil = any(e in ("SMH", "SOXX") for e in debiles)
                    umbral = 1 if semis_debil else (len(quads_esp) // 2 + (len(quads_esp) % 2))
                    if len(debiles) >= max(1, umbral):
                        veto_coh = True
                        _pen = 14 if len(debiles) == len(quads_esp) else 9
                        score = max(3, score - _pen)
                        c_sec = min(c_sec, 38)          # su "sector" hereda la debilidad del tema real
                        coh_txt = f"tema {tema} débil en EE.UU. ({'/'.join(debiles)} {'/'.join(set(q for q in quads_esp if q in ('weakening','lagging')))}): la fuerza local no es fiable"
            # --- JETS: NO es solapamiento con un sector US. Su motor real es crudo (coste) + dólar + ciclo de viajes.
            #     Regla propia: crudo al alza (XOP/OIH fuertes) o dólar fuerte = viento en contra estructural. ---
            jets_txt = ""
            if s == "JETS":
                crudo_fuerte = any(rrg.get(x, {}).get("quad") in ("leading", "improving") for x in ("XOP", "OIH"))
                dolar_fuerte = False
                try:
                    if "UUP" in df.columns:
                        _uu = df["UUP"].dropna()
                        dolar_fuerte = float(_uu.iloc[-1] / _uu.iloc[-min(5, len(_uu) - 1) - 1] - 1) > 0.01
                except Exception as _dege:
                    _deg("compute_fichas:3008", _dege)
                    pass
                if crudo_fuerte or dolar_fuerte:
                    _mot = " + ".join([m for m, ok in [("crudo subiendo (coste de combustible)", crudo_fuerte),
                                                       ("dólar fuerte", dolar_fuerte)] if ok])
                    c_rie = max(3, c_rie - 12)
                    jets_txt = f"viento en contra estructural: {_mot}"
            # prob. exito 4 semanas: frecuencia historica del propio ETF en el MISMO cuadrante + mismo signo de flujo
            prob = None
            try:
                rat = pd.Series(g["ratio_series"], index=df.index)
                mo = pd.Series(g["mom_series"], index=df.index)
                sw = df[s]
                fwd4 = sw.shift(-4) / sw - 1
                mq = rat.combine(mo, lambda a, b: quad_of(a, b) if a == a and b == b else None)
                mask = (mq == quad) & fwd4.notna()
                n = int(mask.sum())
                if n >= 8:
                    p = float((fwd4[mask] > 0).mean())
                    den = 1 + 1.96 ** 2 / n
                    ctr = (p + 1.96 ** 2 / (2 * n)) / den
                    rad = 1.96 * math.sqrt(max(p * (1 - p), 1e-9) / n + 1.96 ** 2 / (4 * n * n)) / den
                    prob = {"p": int(round(p * 100)), "lo": int(round((ctr - rad) * 100)),
                            "hi": int(round((ctr + rad) * 100)), "n": n}
            except Exception as _dege:
                _deg("compute_fichas:3032", _dege)
                pass
            # direccion
            en_cart = s in cartera_set
            es_suelo = bool(su and su["pts"] >= 8 and not su.get("sangra"))
            if en_cart and (distrib or (quad == "lagging" and g["pquad"] == "weakening") or score < 38):
                direc, dcol = "VENDER", "#F4607A"
            elif veto_coh:
                direc, dcol = "ESPERAR", "#F4B740"          # veto duro: el tema espejo US manda, no la fuerza local
            elif score >= 68 and c_flu >= 50 and mkt >= 45 and quad in ("leading", "improving") and not distrib:
                direc, dcol = "COMPRAR", "#2FD08A"
            elif es_suelo and c_flu >= 40:
                direc, dcol = "COMPRAR (suelo)", "#4CC2E0"
            else:
                direc, dcol = "ESPERAR", "#F4B740"
            # proximo lider temprano
            lider_temp = (not veto_coh) and (quad in ("improving",) or (quad == "lagging" and g["dmom"] > 0.5)) and \
                         g["ratio"] < 100 and (f.get("cmf_mejora") or (cmf is not None and cmf > 0))
            # motivos a favor / en contra (max 5 / 3)
            favor, contra = [], []
            if quad == "leading": favor.append("líder confirmado del RRG")
            if quad == "improving": favor.append("entrando en Mejorando (acumulación temprana)")
            if cmf is not None and cmf > 0.05: favor.append(f"dinero institucional entrando (CMF {cmf:+.2f})")
            if f.get("obv_cross"): favor.append("cruce alcista del OBV")
            if f.get("vol_break"): favor.append("ruptura con volumen")
            if g.get("trend"): favor.append("precio sobre su media de 20 semanas")
            if es_suelo: favor.append(f"suelo DURMIENTES {su['pts']}/10, dejó de sangrar")
            if lider_temp: favor.append("🌱 síntomas de próximo líder (RS acelera antes de girar)")
            if c_ind >= 65: favor.append("más fuerte que su propio sector")
            if distrib: contra.append("⚠ distribución oculta: precio sube, dinero SALE")
            if hi52 is not None and hi52 >= 97: contra.append("extendida en máximos: mala entrada")
            if hi52 is not None and hi52 <= 72 and not es_suelo: contra.append("cuchillo cayendo sin señal de suelo")
            if c_cor <= 30: contra.append(f"duplica exposición ya abierta ({cor_lbl})")
            if c_sec <= 35: contra.append(f"su sector padre está débil ({sec_lbl})")
            if tau and tau.get("activa") and quad == "lagging": contra.append("ventana τ activa: presión vendedora mecánica sobre losers hasta " + tau["win_fin"])
            if coh_txt: contra.insert(0, "🌐 " + coh_txt)     # el más importante para internacionales: va primero
            if jets_txt: contra.insert(0, "✈ " + jets_txt)
            # divergencia de OPCIONES: si el flujo entra pero compran proteccion, es confirmacion por 2a via
            if _opt and _opt.get("diverg"):
                if "protección" in _opt["diverg"]:
                    contra.insert(0, f"🎯 opciones: {_opt['diverg']} (P/C {_opt.get('pcr_vol')})")
                elif "suelo" in _opt["diverg"] and es_suelo:
                    favor.insert(0, "🎯 opciones: apuestan alcista pese al flujo débil (posible manos fuertes)")
            if mkt <= 35: contra.append("el mercado está en distribución: bajar tamaño")
            if prob and prob["n"] < 15: contra.append(f"muestra corta (n={prob['n']}): confianza baja")
            # conclusion con invalidacion (falsable) — debe nombrar la restriccion REAL que frena, no un gatillo generico
            if direc.startswith("COMPRAR"):
                concl = "Se invalida si el CMF cae bajo −0.05 o pierde su media de 20 semanas al cierre del viernes."
            elif direc == "VENDER":
                concl = "Se revierte si recupera Mejorando con CMF > 0 dos viernes seguidos."
            else:
                _etf_listo = quad in ("leading", "improving") and c_flu >= 50 and not distrib
                _extendida = (hi52 is not None and hi52 >= 97)
                if veto_coh:
                    concl = "Lo frena su tema espejo en EE.UU., no su gráfico. Gatillo: que el espejo salga de Debilitándose/Rezagado; hasta entonces la fuerza local no es fiable."
                elif _etf_listo and mkt < 45:
                    concl = "El activo está listo; lo frena el MERCADO (régimen en distribución). Gatillo: régimen fuera de distribución dos viernes." + \
                            (" Si además gira el régimen, la entrada es el retroceso a la media de 20 semanas, no el máximo." if _extendida else " Mientras tanto: mantener sin añadir.")
                elif _extendida:
                    concl = "Fuerte pero extendida: la entrada es el retroceso a la media de 20 semanas sin que el flujo se gire (CMF ≥ 0), no perseguir el máximo."
                elif quad in ("lagging", "improving"):
                    concl = "Gatillo para entrar: giro confirmado + CMF > 0, confirmado en cierre de viernes."
                else:
                    concl = "Gatillo: recuperar impulso (mom > 100) con flujo no negativo, confirmado en cierre de viernes."
            fichas.append({"sym": s, "score": score, "direc": direc, "dcol": dcol,
                           "c": {"mercado": int(round(mkt)), "sector": int(round(c_sec)), "industria": int(round(c_ind)),
                                 "etf": int(round(c_etf)), "flujo": int(round(c_flu)), "riesgo": int(round(c_rie)),
                                 "corr": int(round(c_cor))},
                           "quad": quad, "cmf": cmf, "flu_lbl": flu_lbl, "cor_lbl": cor_lbl,
                           "sec_lbl": sec_lbl, "hi52": (round(hi52) if hi52 is not None else None),
                           "rel1": g.get("rel1"), "rel4": g.get("rel4"), "abs13": sc.get("abs_mom"),
                           "prob": prob, "favor": favor[:5], "contra": contra[:3], "concl": concl,
                           "en_cart": en_cart, "suelo": es_suelo, "lider_temp": lider_temp,
                           "veto_coh": bool(veto_coh),
                           "poker": (poker_by.get(s, {}).get("pts") if s in poker_by else None)})
        # --- deduplicacion: gemelos fijos + correlacion semanal > .92 -> un solo representante ---
        grupo_de = {}
        for gpo in GEMELOS_FIJOS:
            pres = [x for x in gpo if x in {ff["sym"] for ff in fichas}]
            for x in pres:
                grupo_de[x] = pres[0]
        try:
            syms = [ff["sym"] for ff in fichas]
            for i, a in enumerate(syms):
                for b in syms[i + 1:]:
                    if a in rets_w.columns and b in rets_w.columns and a not in grupo_de and b not in grupo_de:
                        cv = rets_w[a].corr(rets_w[b])
                        if cv == cv and cv > .92:
                            grupo_de[a] = a; grupo_de[b] = a
        except Exception as _dege:
            _deg("compute_fichas:3121", _dege)
            pass
        raiz = {}
        for ff in fichas:
            r = grupo_de.get(ff["sym"], ff["sym"])
            raiz.setdefault(r, []).append(ff)
        finales = []
        for r, miembros in raiz.items():
            miembros.sort(key=lambda x: -x["score"])
            jefe = miembros[0]
            if len(miembros) > 1:
                jefe = dict(jefe)
                jefe["gemelos"] = [{"sym": m["sym"], "score": m["score"], "direc": m["direc"]} for m in miembros[1:]]
                # coherencia: los gemelos heredan la senal del mejor (una sola recomendacion por exposicion)
                # ...y el jefe hereda la mesa de poker del grupo (el desk puede apuntar al gemelo, p.ej. SMH bajo SOXX)
                _pk = [m.get("poker") for m in miembros if m.get("poker") is not None]
                if _pk:
                    jefe["poker"] = max(_pk)
            finales.append(jefe)
        finales.sort(key=lambda x: -x["score"])
        return finales
    except Exception as e:
        _avisar("fichas", f"SISTEMA DE FICHAS caído — Operativa y Veredicto sin panel de decisión: {e}", nivel="error")
        return None

# ----------------------------------------------------------------------
# Backtest causal: sobreponderar Lider+Mejorando vs comprar y mantener el indice
# ----------------------------------------------------------------------
def backtest(df, rrg, hold=("leading", "improving"), trend=None, max_pos=None, weight=None, buffer=None):
    trend = TREND_FILTER if trend is None else trend
    max_pos = MAX_POSICIONES if max_pos is None else max_pos
    weight = PESO if weight is None else weight
    buffer = BUFFER if buffer is None else buffer
    idx = list(df.index)
    rets = df.pct_change()
    # RED DE SEGURIDAD: ningun ETF sin apalancar rinde >60% en una semana. Si un dato corrupto se
    # colase (un cambio de escala que el saneador no reparo), un retorno de +900% o -90% destrozaria
    # la curva de equity y daria una rentabilidad/drawdown del benchmark absurdos (el sintoma del
    # "-22.8% vs SPY" con el mercado en maximos). Capamos a +-60% SOLO lo groseramente imposible.
    _CAP = 0.60
    _capados = int((rets.abs() > _CAP).sum().sum())
    if _capados:
        rets = rets.clip(lower=-_CAP, upper=_CAP)
        _avisar("backtest.cap", f"{_capados} retorno(s) semanal(es) imposible(s) (>60%) capados en el backtest: "
                                "habia un dato corrupto que habria falseado la rentabilidad/drawdown del benchmark")
    bench_ret = rets[BENCH].tolist()
    sectors = list(rrg.keys())
    R = {s: rrg[s]["ratio_series"] for s in sectors}
    M = {s: rrg[s]["mom_series"] for s in sectors}
    ok = lambda v: v is not None and v == v
    # filtro de tendencia del mercado: S&P vs su media de TREND_MA_WEEKS
    spy = df[BENCH]
    ma = spy.rolling(min(TREND_MA_WEEKS, len(spy)), min_periods=5).mean().tolist()
    spyl = spy.tolist()
    # volatilidad movil (13s) para el peso por volatilidad inversa
    vol = {s: rets[s].rolling(13, min_periods=4).std().tolist() for s in sectors}
    held = set()   # para la histeresis
    eq_s, eq_b = [1.0], [1.0]; wins = weeks = 0; in_mkt = 0
    for i in range(1, len(idx)):
        br = bench_ret[i] if bench_ret[i] == bench_ret[i] else 0.0
        bull = not (trend and ok(ma[i-1]) and spyl[i-1] < ma[i-1])
        chosen = []
        if bull:
            for s in sectors:
                rr, mm = R[s][i-1], M[s][i-1]
                if not (ok(rr) and ok(mm)):
                    held.discard(s); continue
                q = quad_of(rr, mm)
                strong = q in hold and rr > 100 + buffer and mm > 100 - buffer
                weak = not (q in hold) or rr < 100 - buffer or mm < 100 - buffer
                if strong:
                    held.add(s)
                elif weak:
                    held.discard(s)
                if s in held:
                    chosen.append(s)
            # tope: las de mayor impulso
            if max_pos and len(chosen) > max_pos:
                chosen = sorted(chosen, key=lambda s: -(M[s][i-1] or 0))[:max_pos]
        if chosen:
            ws = {}
            for s in chosen:
                if weight == "volatilidad":
                    v = vol[s][i-1] if ok(vol[s][i-1]) and vol[s][i-1] > 1e-6 else 0.02
                    ws[s] = 1.0 / v
                elif weight == "impulso":
                    ws[s] = max(0.1, (M[s][i-1] or 100) - 99)
                else:
                    ws[s] = 1.0
            tot = sum(ws.values()) or 1.0
            r = 0.0
            for s in chosen:
                ri = rets[s].iloc[i]
                r += (ws[s] / tot) * (ri if ri == ri else 0.0)
            in_mkt += 1
        else:
            r = 0.0   # liquidez (mercado bajista o nada elegido)
        eq_s.append(eq_s[-1] * (1 + r))
        eq_b.append(eq_b[-1] * (1 + br))
        weeks += 1
        if r > br:
            wins += 1
    def mdd(curve):
        peak = curve[0]; worst = 0.0
        for v in curve:
            peak = max(peak, v); worst = min(worst, v / peak - 1)
        return worst * 100
    return {
        "eq_s": eq_s, "eq_b": eq_b, "dates": [str(d.date()) for d in idx],
        "tot_s": round((eq_s[-1] - 1) * 100, 1), "tot_b": round((eq_b[-1] - 1) * 100, 1),
        "mdd_s": round(mdd(eq_s), 1), "mdd_b": round(mdd(eq_b), 1),
        "winrate": int(round(100 * wins / max(weeks, 1))), "weeks": weeks,
        "exposure": int(round(100 * in_mkt / max(weeks, 1))),
    }


# ----------------------------------------------------------------------
# Caidas del S&P 500: frecuencia anual, probabilidad y plan de liquidez
# ----------------------------------------------------------------------
def compute_seasonality(close, ahead=5):
    # Estacionalidad por MEDIA-QUINCENA (1H = dias 1-15, 2H = 16-fin de mes) sobre el historico largo.
    # Para el periodo actual y los proximos: % de años con retorno positivo y retorno medio.
    s = close.dropna()
    if s is None or len(s) < 252 * 8:
        return None
    d = pd.DataFrame({"c": s})
    d["year"] = d.index.year
    d["month"] = d.index.month
    d["half"] = np.where(d.index.day <= 15, 1, 2)
    grp = d.groupby(["year", "month", "half"])["c"]
    ret = (grp.last() / grp.first() - 1).reset_index()
    stats = {}
    for (m, h), g in ret.groupby(["month", "half"]):
        vals = g["c"].dropna().values
        if len(vals) >= 5:
            stats[(m, h)] = {"avg": round(100 * float(vals.mean()), 2),
                             "pup": int(round(100 * float((vals > 0).mean()))), "n": int(len(vals))}
    mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    today = dt.date.today()
    m, h = today.month, (1 if today.day <= 15 else 2)
    rows = []
    for k in range(ahead + 1):
        st = stats.get((m, h))
        rows.append({"label": f"{'1ª' if h == 1 else '2ª'} mitad de {mes[m-1]}",
                     "now": k == 0, "pup": st["pup"] if st else None, "avg": st["avg"] if st else None,
                     "n": st["n"] if st else 0})
        if h == 1:
            h = 2
        else:
            h = 1; m = 1 if m == 12 else m + 1
    return {"rows": rows, "years": int(s.index.year.nunique())}


def _fetch_long(stooq_sym, etf_fallback, yahoo_sym):
    """Historia LARGA de un indice (Stooq -> ETF -> Yahoo). Devuelve (close, fuente, hl) donde hl=High/Low o None."""
    start = dt.date.today() - dt.timedelta(days=365 * 60)
    try:
        r = requests.get(f"https://stooq.com/q/d/l/?s={stooq_sym}&i=d", timeout=20,
                         headers={"User-Agent": "Mozilla/5.0"})
        df = pd.read_csv(StringIO(r.text))
        if "Close" in df.columns and len(df) > 1000:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date").sort_index()
            hl = df[["High", "Low"]] if {"High", "Low"}.issubset(df.columns) else None
            return df["Close"], stooq_sym.upper(), hl
    except Exception:
        pass
    if etf_fallback:
        d, _ = get_ohlcv(etf_fallback, start, dt.date.today())
        if d is not None and "Close" in d.columns:
            hl = d[["High", "Low"]] if {"High", "Low"}.issubset(d.columns) else None
            return d["Close"].sort_index(), etf_fallback, hl
    if yf is not None:
        try:
            g = yf.download(yahoo_sym, start=start, progress=False, auto_adjust=False)   # sin ajustar: % de caída fieles al índice real
            c = g["Close"]
            if hasattr(c, "columns"):
                c = c.iloc[:, 0]
            hl = None
            if {"High", "Low"}.issubset(g.columns):
                h, l = g["High"], g["Low"]
                if hasattr(h, "columns"):
                    h = h.iloc[:, 0]
                if hasattr(l, "columns"):
                    l = l.iloc[:, 0]
                hl = pd.DataFrame({"High": h, "Low": l}).dropna()
            return c.dropna().sort_index(), yahoo_sym, hl
        except Exception:
            pass
    return None, "—", None

def fetch_long_close():
    """Historia LARGA del S&P 500 para estadistica de caidas."""
    return _fetch_long("^spx", "SPY", "^GSPC")

def drawdown_stats(close, thresholds, hl=None):
    close = close.dropna()
    if len(close) < 250:
        return None, None
    years = sorted(set(close.index.year))
    cur_year = dt.date.today().year
    today_md = (dt.date.today().month, dt.date.today().day)

    def count(peak_src, trough_src):
        counts = {t: {y: 0 for y in years} for t in thresholds}
        rest_hit = {t: set() for t in thresholds}
        roll_peak = peak_src.rolling(252, min_periods=20).max()   # pico de las ~52 semanas previas (pico reciente), no el maximo historico
        in_ev = {t: False for t in thresholds}
        for date, p in peak_src.items():
            peak = roll_peak.loc[date]
            if peak is None or peak != peak or peak <= 0:
                continue
            dd = (trough_src.loc[date] / peak - 1) * 100
            in_window = (date.month, date.day) >= today_md
            for t in thresholds:
                eff = (t - DD_GAP_PP) if t >= 10 else t   # cubos grandes (>=10%) captan el hueco nocturno del futuro/CFD
                if not in_ev[t] and dd <= -eff:
                    in_ev[t] = True
                    counts[t][date.year] += 1
                elif in_ev[t] and dd > -eff / 2.0:
                    in_ev[t] = False
                if dd <= -eff and in_window and date.year < cur_year:
                    rest_hit[t].add(date.year)
        return counts, rest_hit

    basis = "cierre"
    counts, rest_hit = count(close, close)
    if hl is not None and {"High", "Low"}.issubset(hl.columns):
        hh = hl["High"].reindex(close.index).ffill().dropna()
        ll = hl["Low"].reindex(close.index).ffill().dropna()
        idx = hh.index.intersection(ll.index)
        if len(idx) > 250:
            counts, rest_hit = count(hh.loc[idx], ll.loc[idx])   # intradía: pico=máx de High, caída con Low
            basis = "intradía"
    complete = [y for y in years if y < cur_year]
    last20 = [y for y in complete if y >= cur_year - 20]
    def stats(t, yrs):
        if not yrs:
            return 0.0, 0
        vals = [counts[t][y] for y in yrs]
        return round(sum(vals) / len(yrs), 1), int(round(100 * sum(1 for v in vals if v >= 1) / len(yrs)))
    out = {}
    for t in thresholds:
        a20, p20 = stats(t, last20)
        af, pf = stats(t, complete)
        rest = int(round(100 * len(rest_hit[t] & set(complete)) / len(complete))) if complete else 0
        out[t] = {"avg20": a20, "prob20": p20, "avgfull": af, "probfull": pf,
                  "ytd": counts[t].get(cur_year, 0), "rest": rest}
    meta = {"start": years[0], "end": years[-1], "n20": len(last20), "nfull": len(complete),
            "cur_year": cur_year, "basis": basis}
    return out, meta

def fetch_dix():
    """DIX (Dark Index, SqueezeMetrics): porcentaje comprador de la actividad en DARK POOLS sobre el
    S&P 500. Dato de MERCADO COMPLETO (no existe por sector en fuentes gratuitas y frescas: el desglose
    FINRA ATS llega con 2-4 semanas de retraso), diario y con 1 dia de decalaje. Lectura: DIX >= 45%
    historicamente precede a retornos positivos (los institucionales COMPRAN en la oscuridad); un DIX
    alto EN PLENA CAIDA es la acumulacion oculta a escala de indice — el mismo patron del durmiente,
    pero del mercado entero. GEX (gamma de dealers): negativo = los dealers amplifican los movimientos
    (gasolina para el giro); muy positivo = mercado anclado. Devuelve dict o None si la web no responde."""
    try:
        r = requests.get(DIX_URL, timeout=25, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        if r.status_code != 200 or not r.text:
            return None
        from io import StringIO
        d = pd.read_csv(StringIO(r.text))
        cols = {c.strip().lower(): c for c in d.columns}
        if "dix" not in cols or "date" not in cols:
            return None
        d["_fecha"] = pd.to_datetime(d[cols["date"]], errors="coerce")
        d = d.dropna(subset=["_fecha"]).sort_values("_fecha")
        dix = pd.to_numeric(d[cols["dix"]], errors="coerce").dropna()
        if len(dix) < 30:
            return None
        if float(dix.max()) <= 1.5:          # el CSV viene en fraccion (0.43): normalizo a %
            dix = dix * 100.0
        last = float(dix.iloc[-1]); m5 = float(dix.iloc[-5:].mean())
        yr = dix.iloc[-252:]
        pct = int(round(float((yr <= last).mean() * 100)))
        gex = None
        if "gex" in cols:
            _g = pd.to_numeric(d[cols["gex"]], errors="coerce").dropna()
            if len(_g):
                gex = float(_g.iloc[-1])
        if m5 >= 45.5:
            senal, scol = "acumulación oculta institucional", "#2FD08A"
        elif m5 >= 43.5:
            senal, scol = "compra dark pool normal-alta", "#7FD8A0"
        elif m5 >= 41.0:
            senal, scol = "neutro", "#9FB0C8"
        else:
            senal, scol = "compra dark pool débil (sin red)", "#F4607A"
        return {"last": round(last, 1), "m5": round(m5, 1), "pct": pct, "gex": gex,
                "senal": senal, "scol": scol, "fecha": str(d["_fecha"].iloc[-1].date()),
                "spark": [float(x) for x in dix.iloc[-40:]]}
    except Exception as _dege:
        _deg("fetch_dix:3416", _dege)
        return None


def fetch_fear_greed():
    """Indice Fear & Greed de CNN (0-100, sentimiento contrario). Devuelve dict o None si falla."""
    try:
        r = requests.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
                         timeout=20, headers={
                             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                           "(KHTML, like Gecko) Chrome/123.0 Safari/537.36",
                             "Accept": "application/json"})
        fg = r.json().get("fear_and_greed", {})
        sc = fg.get("score")
        if sc is None:
            return None
        def _g(k):
            v = fg.get(k)
            return round(float(v)) if v is not None else None
        return {"score": round(float(sc)), "rating": (fg.get("rating") or "").strip(),
                "prev": _g("previous_close"), "week": _g("previous_1_week"),
                "month": _g("previous_1_month"), "year": _g("previous_1_year")}
    except Exception as _dege:
        _deg("fetch_fear_greed:3438", _dege)
        return None

def cash_plan(close, hl=None):
    """Plan de liquidez. FIX: el pico ahora es el MAXIMO INTRADIA real (Highs), no solo el maximo de cierres,
    y se registra la FECHA del ultimo dato para detectar series desfasadas (Stooq suele llegar con 1 dia de retraso).
    Esa combinacion (pico de cierres + dato viejo) hacia que el terminal marcara menos caida de la real."""
    close = close.dropna()
    peak_close = float(close.cummax().iloc[-1])
    peak = peak_close
    if hl is not None and "High" in getattr(hl, "columns", []):
        try:
            hi_max = float(hl["High"].dropna().cummax().iloc[-1])
            peak = max(peak, hi_max)                      # ATH intradia real (lo que mira todo el mundo)
        except Exception:
            pass
    last = float(close.iloc[-1])
    try:
        fecha = close.index[-1].date()
    except Exception:
        fecha = None
    # ¿dato viejo? dias habiles entre el ultimo dato y hoy (0 = fresco; >=1 = falta al menos una sesion)
    stale = 0
    if fecha is not None:
        try:
            stale = max(0, len(pd.bdate_range(fecha, dt.date.today())) - 1)
            # si hoy es habil y el mercado USA aun no ha cerrado, no cuentes hoy como sesion perdida
            if stale >= 1 and dt.date.today().weekday() < 5 and dt.datetime.now().hour < 22:
                stale -= 1
        except Exception:
            pass
    rungs = []
    for thr, pct in CASH_PLAN:
        level = peak * (1 - thr / 100)
        rungs.append({"thr": thr, "pct": pct, "level": round(level, 2), "hit": last <= level})
    return {"peak": round(peak, 2), "peak_close": round(peak_close, 2), "last": round(last, 2),
            "dd": round((last / peak - 1) * 100, 1),
            "dd_close": round((last / peak_close - 1) * 100, 1),
            "fecha": str(fecha) if fecha else "?", "stale": stale, "rungs": rungs}

def refrescar_con_yahoo(close, hl, ysym):
    """Stooq suele llegar con 1 sesion de RETRASO: anade los ultimos dias frescos desde Yahoo
    (auto_adjust=False: son indices, sin dividendos). Este retraso era la causa de que el terminal
    marcara menos caida desde ATH de la real. Devuelve (close, hl) actualizados."""
    if yf is None or close is None or not len(close.dropna()):
        return close, hl
    try:
        g = yf.download(ysym, period="10d", progress=False, auto_adjust=False)
        if g is None or not len(g):
            return close, hl
        c = g["Close"]
        if hasattr(c, "columns"):
            c = c.iloc[:, 0]
        c = c.dropna()
        c.index = pd.to_datetime(c.index).tz_localize(None).normalize()
        base = close.dropna().copy()
        base.index = pd.to_datetime(base.index).tz_localize(None).normalize() if getattr(base.index, "tz", None) is not None else pd.to_datetime(base.index).normalize()
        nuevos = c[c.index > base.index[-1]]
        # GUARDIA DE ESCALA: si la serie base es SPY (~740) y el refresco es ^GSPC (~7400), añadir
        # mezclaria escalas y corromperia el drawdown con un salto de 10x. Solo se añade si el primer
        # dato nuevo esta a <20% del ultimo de la base (misma escala, movimiento plausible).
        if len(nuevos):
            _ratio = float(nuevos.iloc[0]) / float(base.iloc[-1])
            if not (0.8 <= _ratio <= 1.25):
                _avisar(f"refresco.{ysym}", f"refresco DESCARTADO: escala incompatible (ratio {_ratio:.2f}); la serie sigue sin mezclar y el drawdown puede ir 1 sesion viejo")
                nuevos = nuevos.iloc[0:0]
        if len(nuevos):
            base = pd.concat([base, nuevos])
            print(f"  [{ysym}] serie larga refrescada con Yahoo: +{len(nuevos)} sesion(es), ultima {nuevos.index[-1].date()}")
        close = base
        if {"High", "Low"}.issubset(g.columns):
            h, l = g["High"], g["Low"]
            if hasattr(h, "columns"): h = h.iloc[:, 0]
            if hasattr(l, "columns"): l = l.iloc[:, 0]
            nhl = pd.DataFrame({"High": h, "Low": l}).dropna()
            nhl.index = pd.to_datetime(nhl.index).tz_localize(None).normalize()
            if hl is not None and len(hl):
                bhl = hl.copy()
                bhl.index = pd.to_datetime(bhl.index).normalize()
                add = nhl[nhl.index > bhl.index[-1]]
                hl = pd.concat([bhl, add]) if len(add) else bhl
            else:
                hl = nhl
    except Exception as e:
        _avisar(f"refresco.{ysym}", f"no se pudo refrescar con Yahoo ({e}); el drawdown puede ir 1 sesion viejo")
    return close, hl

def fetch_es_futuro():
    """Ultimo precio del FUTURO del S&P (ES=F). El futuro cotiza casi 24h: es la referencia mas fresca
    que existe del indice (lo que Pedro ve en el broker). Best-effort; None si falla."""
    if yf is None:
        return None
    try:
        g = yf.download("ES=F", period="5d", interval="1h", progress=False, auto_adjust=False)
        if g is None or not len(g):
            return None
        c = g["Close"]
        if hasattr(c, "columns"):
            c = c.iloc[:, 0]
        c = c.dropna()
        if not len(c):
            return None
        ts = c.index[-1]
        try:
            ts = ts.tz_convert("Europe/Madrid").strftime("%d %b %H:%M")
        except Exception:
            ts = str(ts)[:16]
        return {"last": round(float(c.iloc[-1]), 2), "ts": ts}
    except Exception as _dege:
        _deg("fetch_es_futuro:3546", _dege)
        return None

# ----------------------------------------------------------------------
# CALENDARIO tau — ciclo intramensual de momentum (Nathan/Suominen/Tasa 2026):
# la venta forzada de LOSERS por demanda de liquidez de fin de mes se concentra en
# 6 sesiones que terminan 4 dias antes de fin de mes. Con T+1 (EE.UU., 2024) la
# presion se desplaza 1 sesion hacia fin de mes -> ventana efectiva [tau-8, tau-3].
# tau = ULTIMA sesion del mes. Es un OVERLAY informativo, no un sistema.
# ----------------------------------------------------------------------
def _nyse_bdays(d0, d1):
    """Sesiones NYSE aproximadas entre d0 y d1 (incl.): laborables menos festivos NYSE."""
    from pandas.tseries.holiday import (AbstractHolidayCalendar, Holiday, nearest_workday,
                                        USMartinLutherKingJr, USPresidentsDay, GoodFriday,
                                        USMemorialDay, USLaborDay, USThanksgivingDay)
    class _NYSE(AbstractHolidayCalendar):
        rules = [Holiday("NewYear", month=1, day=1, observance=nearest_workday),
                 USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay,
                 Holiday("Juneteenth", month=6, day=19, start_date="2022-01-01", observance=nearest_workday),
                 Holiday("July4", month=7, day=4, observance=nearest_workday),
                 USLaborDay, USThanksgivingDay,
                 Holiday("Christmas", month=12, day=25, observance=nearest_workday)]
    hols = _NYSE().holidays(pd.Timestamp(d0) - pd.Timedelta(days=5), pd.Timestamp(d1) + pd.Timedelta(days=5))
    days = pd.bdate_range(d0, d1)
    return [d for d in days if d not in set(hols)]

def calendario_tau(hoy=None):
    """Estado del ciclo intramensual: VENTANA (presion vendedora sobre losers), REBOTE
    (mejor zona del mes para el cazador de suelos) o NEUTRO. Todo en sesiones NYSE."""
    try:
        hoy = pd.Timestamp(hoy or dt.date.today()).normalize()
        ini_mes = hoy.replace(day=1)
        fin_mes = (ini_mes + pd.offsets.MonthEnd(0))
        ses = _nyse_bdays(ini_mes, fin_mes)
        if not ses:
            return None
        tau = ses[-1]                                   # ultima sesion del mes
        idx_tau = len(ses) - 1
        # VERIFICADO CONTRA EL PAPER COMPLETO (Nathan/Suominen/Tasa, SSRN 6426026):
        # - Ventana base PreTOM = [tau-9, tau-4] (6 sesiones). La reforma T+1 (may-2024) movio el dia
        #   marginal de venta de tau-4 a tau-3 (DiD +85.9 pb, t=2.68) pero el paper NO retesta el borde
        #   izquierdo -> conservador: ventana [tau-9, tau-3], 7 sesiones.
        # - La presion vendedora sigue elevada hasta fin de mes (TAQ) y amaina en los PRIMEROS dias del
        #   mes siguiente; ~70% del castigo revierte en la semana Post. Los "momentum crashes" (= rallies
        #   violentos de losers) se concentran en month-start [tau+1, tau+3] -> ESA es la zona de rebote.
        win = ses[max(0, idx_tau - 9): max(0, idx_tau - 2)]        # [tau-9 .. tau-3]
        transicion = ses[max(0, idx_tau - 2):]                      # [tau-2 .. tau]: presion amainando, aun residual
        sig_ini = fin_mes + pd.Timedelta(days=1)
        rebote = _nyse_bdays(sig_ini, sig_ini + pd.Timedelta(days=10))[:3]   # [tau+1 .. tau+3] del mes siguiente
        # los 3 PRIMEROS dias habiles del mes actual son la zona rebote del mes ANTERIOR
        primeras3 = [d.normalize() for d in ses[:3]]
        estado, col = "NEUTRO", "#8FA3C0"
        if hoy in [d.normalize() for d in win]:
            estado, col = "VENTANA ACTIVA", "#F4B740"
        elif hoy in [d.normalize() for d in transicion]:
            estado, col = "TRANSICIÓN", "#4CC2E0"
        elif hoy in [d.normalize() for d in rebote] or hoy in primeras3:
            estado, col = "ZONA REBOTE", "#2FD08A"
        # si hoy no es sesion (finde/festivo), estado del proximo dia habil informativamente
        _f = lambda d: d.strftime("%d %b")
        # sesiones que faltan para que ARRANQUE la ventana (si aun no llego)
        faltan_v = len([d for d in ses if hoy < d.normalize() <= win[0].normalize()]) if win and hoy < win[0] else 0
        return {"estado": estado, "col": col, "tau": _f(tau),
                "win_ini": _f(win[0]) if win else "?", "win_fin": _f(win[-1]) if win else "?",
                "trans_ini": _f(transicion[0]) if transicion else "?", "trans_fin": _f(transicion[-1]) if transicion else "?",
                "reb_ini": _f(rebote[0]) if rebote else "?", "reb_fin": _f(rebote[-1]) if rebote else "?",
                "faltan_ventana": faltan_v,
                "activa": estado == "VENTANA ACTIVA", "transicion": estado == "TRANSICIÓN",
                "rebote": estado == "ZONA REBOTE"}
    except Exception as e:
        _avisar("tau", f"calendario τ no calculado (el overlay desaparece este build): {e}")
        return None

# ----------------------------------------------------------------------
# MOTOR DE ANALOGOS (aprendizaje estadistico simple y AUDITABLE):
# compara el estado actual del S&P con TODOS los dias desde 1990 usando k-vecinos
# sobre rasgos normalizados (retornos 1m/3m/6m, distancia al maximo 52s, volatilidad,
# pendiente de la MA200). Devuelve que paso DESPUES en los episodios mas parecidos.
# Frecuencias historicas con intervalo de Wilson — NO una prediccion.
# ----------------------------------------------------------------------
def compute_analogos(close, desde="1990-01-01", k=50, sep=21):
    try:
        s = close.dropna()
        s = s[s.index >= pd.Timestamp(desde)]
        if len(s) < 800:
            return None
        r = s.pct_change()
        f = pd.DataFrame(index=s.index)
        f["r21"] = s.pct_change(21)
        f["r63"] = s.pct_change(63)
        f["r126"] = s.pct_change(126)
        f["dd52"] = s / s.rolling(252, min_periods=60).max() - 1
        f["vol21"] = r.rolling(21).std() * math.sqrt(252)
        ma200 = s.rolling(200, min_periods=100).mean()
        f["slope200"] = ma200.pct_change(20)
        f = f.dropna()
        if len(f) < 600:
            return None
        z = (f - f.mean()) / (f.std() + 1e-12)
        hoy_v = z.iloc[-1].values
        fwd21 = s.shift(-21) / s - 1
        fwd63 = s.shift(-63) / s - 1
        # candidatos: con futuro conocido y a >1 anyo de hoy (sin contaminar con el propio episodio)
        cand = z.iloc[:-1]
        mask = fwd63.reindex(cand.index).notna() & (cand.index < (s.index[-1] - pd.Timedelta(days=365)))
        cand = cand[mask]
        dist = ((cand - hoy_v) ** 2).sum(axis=1) ** 0.5
        elegidos = []
        for fecha in dist.sort_values().index:
            if all(abs((fecha - e).days) > sep for e in elegidos):
                elegidos.append(fecha)
            if len(elegidos) >= k:
                break
        if len(elegidos) < 15:
            return None
        f21 = fwd21.reindex(elegidos).dropna() * 100
        f63 = fwd63.reindex(elegidos).dropna() * 100
        def _wil(p, n, zz=1.96):
            den = 1 + zz * zz / n
            ctr = (p + zz * zz / (2 * n)) / den
            rad = zz * math.sqrt(max(p * (1 - p), 1e-9) / n + zz * zz / (4 * n * n)) / den
            return int(round(100 * (ctr - rad))), int(round(100 * (ctr + rad)))
        def _st(x):
            n = len(x)
            p = float((x > 0).mean()) if n else 0.0
            lo, hi = _wil(p, n) if n else (0, 0)
            return {"n": n, "pos": int(round(p * 100)), "lo": lo, "hi": hi,
                    "med": round(float(x.median()), 1), "p5": round(float(x.quantile(.05)), 1),
                    "p95": round(float(x.quantile(.95)), 1)}
        top = [{"fecha": e.strftime("%b %Y"), "fwd63": round(float(fwd63.loc[e]) * 100, 1)}
               for e in elegidos[:6] if e in fwd63.index and fwd63.loc[e] == fwd63.loc[e]]
        est = f.iloc[-1]
        return {"n": len(elegidos), "m1": _st(f21), "m3": _st(f63), "top": top,
                "estado": {"r21": round(float(est["r21"]) * 100, 1), "r63": round(float(est["r63"]) * 100, 1),
                           "dd52": round(float(est["dd52"]) * 100, 1), "vol21": round(float(est["vol21"]) * 100, 1)},
                "desde": str(pd.Timestamp(desde).year)}
    except Exception as e:
        _avisar("analogos", f"motor de análogos no calculado: {e}")
        return None

def fetch_fx():
    """EUR/USD avanzado para la cobertura divisa (Stooq -> Yahoo)."""
    c = None
    try:
        r = requests.get("https://stooq.com/q/d/l/?s=eurusd&i=d", timeout=20,
                         headers={"User-Agent": "Mozilla/5.0"})
        df = pd.read_csv(StringIO(r.text))
        if "Close" in df.columns and len(df) > 60:
            df["Date"] = pd.to_datetime(df["Date"])
            c = df.set_index("Date")["Close"].sort_index()
    except Exception:
        c = None
    if c is None and yf is not None:
        try:
            g = yf.download("EURUSD=X", period="3y", progress=False)["Close"]
            if hasattr(g, "columns"):
                g = g.iloc[:, 0]
            c = g.dropna()
        except Exception:
            c = None
    if c is None or len(c) < 60:
        return None
    last = float(c.iloc[-1])
    ma50 = float(c.rolling(min(50, len(c))).mean().iloc[-1])
    ma200 = float(c.rolling(min(200, len(c))).mean().iloc[-1])
    def roc(k):
        return round(float(c.iloc[-1] / c.iloc[-min(k, len(c) - 1)] - 1) * 100, 1) if len(c) > k else None
    win = c.iloc[-min(252, len(c)):]
    hi52, lo52 = float(win.max()), float(win.min())
    pos = round(100 * (last - lo52) / ((hi52 - lo52) or 1e-9))   # 0=minimo 52s, 100=maximo 52s
    cross = "alcista (50>200)" if ma50 > ma200 else "bajista (50<200)"
    # fuerza de tendencia del euro: combinacion de posicion vs medias y momentum
    score = (last > ma50) + (last > ma200) + (ma50 > ma200) + (roc(65) or 0 > 0)
    return {"last": round(last, 4), "ma50": round(ma50, 4), "ma200": round(ma200, 4),
            "roc1m": roc(22), "roc3m": roc(65), "roc6m": roc(130),
            "hi52": round(hi52, 4), "lo52": round(lo52, 4), "pos": pos, "cross": cross,
            "above50": last > ma50, "above200": last > ma200, "strong": score >= 3,
            "spark": [float(x) for x in c.iloc[-min(160, len(c)):].tolist()]}

# ----------------------------------------------------------------------
# Acciones lideres por sector (RS Rating 1-99, estilo IBD/O'Neil)
# ----------------------------------------------------------------------
def fetch_stock_universe():
    print(f"\n[Universo RS: '{RS_UNIVERSE}']")
    if RS_UNIVERSE == "sp500":
        closes = fetch_sp500_universe()
        if len(closes) >= 150:
            # Asegurar que TODAS las acciones de SECTOR_STOCKS (las de agua de FIW incluidas) entren
            # en el ranking aunque NO sean del S&P 500 (p.ej. MLI Mueller) o falten en la lista (p.ej. FERG).
            # Sin esto, esas acciones no tienen percentil y desaparecen del panel.
            extra = sorted({t for lst in SECTOR_STOCKS.values() for t in lst if t not in closes})
            if extra:
                print(f"  +{len(extra)} acciones de SECTOR_STOCKS fuera del S&P (incluye agua FIW: MLI, FERG, etc.)...")
                start = dt.date.today() - dt.timedelta(days=500)
                for t in extra:
                    try:
                        d, _ = get_ohlcv(t, start, dt.date.today())
                        if d is not None and "Close" in d.columns and len(d) > 200:
                            closes[t] = d["Close"].dropna()
                    except Exception:
                        pass
                    time.sleep(0.15)
            return closes
        print("  (S&P 500 insuficiente; uso la lista por sectores)")
    tickers = sorted({t for lst in SECTOR_STOCKS.values() for t in lst})
    start = dt.date.today() - dt.timedelta(days=500)
    closes = {}
    print(f"\nDescargando {len(tickers)} acciones para el ranking de lideres...")
    for i, t in enumerate(tickers):
        d, _ = get_ohlcv(t, start, dt.date.today())
        if d is not None and "Close" in d.columns and len(d) > 200:
            closes[t] = d["Close"].dropna()
        if (i + 1) % 20 == 0:
            print(f"  ...{i + 1}/{len(tickers)}")
        time.sleep(0.15)
    print(f"  acciones con datos: {len(closes)}")
    return closes

def sp500_tickers():
    for url in ("https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv",
                "https://datahub.io/core/s-and-p-500-companies/r/constituents.csv"):
        try:
            r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            df = pd.read_csv(StringIO(r.text))
            col = "Symbol" if "Symbol" in df.columns else df.columns[0]
            ts = [str(t).strip().upper().replace(".", "-") for t in df[col].dropna()]
            ts = list(dict.fromkeys(ts))
            if len(ts) > 400:
                print(f"  lista S&P 500 obtenida: {len(ts)} valores")
                return ts
        except Exception:
            continue
    print(f"  (no pude bajar la lista del S&P; uso respaldo de {len(set(SP500_FALLBACK))})")
    return list(dict.fromkeys(SP500_FALLBACK))

def _yf_batch_closes(tickers):
    closes = {}
    if yf is None:
        return closes
    for i in range(0, len(tickers), 80):
        chunk = tickers[i:i + 80]
        try:
            data = yf.download(chunk, period="2y", interval="1d", progress=False,
                               auto_adjust=True, threads=True)
            if data is None or len(data) == 0:
                continue
            if isinstance(data.columns, pd.MultiIndex):
                cl = data["Close"]
            else:
                cl = data[["Close"]].rename(columns={"Close": chunk[0]})
            for t in cl.columns:
                s = cl[t].dropna()
                if len(s) > 200:
                    closes[str(t)] = s
        except Exception as _dege:
            _deg("_yf_batch_closes:3800", _dege)
            continue
        time.sleep(0.4)
    return closes

def fetch_sp500_universe():
    tickers = sp500_tickers()
    print(f"\nDescargando el S&P 500 ({len(tickers)} acciones) para el RS...")
    closes = _yf_batch_closes(tickers)
    print(f"  via yfinance: {len(closes)}")
    # completar lo que falte por la via fiable (Stooq/Yahoo individual)
    missing = [t for t in tickers if t not in closes]
    if missing:
        print(f"  completando {len(missing)} por descarga individual (tarda un poco)...")
        start = dt.date.today() - dt.timedelta(days=500)
        for i, t in enumerate(missing):
            d, _ = get_ohlcv(t, start, dt.date.today())
            if d is not None and "Close" in d.columns and len(d) > 200:
                closes[t] = d["Close"].dropna()
            time.sleep(0.12)
            if (i + 1) % 50 == 0:
                print(f"    ...{i + 1}/{len(missing)}")
    print(f"  acciones del S&P con datos: {len(closes)}")
    return closes

def _phase(s, drs):
    """Clasifica la FASE de una accion (modelo de 4 fases) con su propia serie de precios.
    base = lateral abajo acumulando · sube = tendencia alcista sana · distrib = lateral arriba (techo) ·
    baja = bajando · lateral = medio sin sesgo. Usa media 30 semanas + posicion en rango 52s + aceleracion RS."""
    try:
        s = s.dropna()
    except Exception as _dege:
        _deg("_phase:3831", _dege)
        return None
    if s is None or len(s) < 170:
        return None
    price = float(s.iloc[-1])
    win = s.iloc[-252:]
    hi = price / (float(win.max()) or 1e-9) * 100
    lo = float(win.min())
    pos = (price - lo) / (((float(win.max()) - lo)) or 1e-9) * 100
    ma = s.rolling(150).mean()                 # media 30 semanas (~150 sesiones)
    if pd.isna(ma.iloc[-1]):
        ma = s.rolling(50).mean()
    ma_now = float(ma.iloc[-1])
    j = -21 if len(ma.dropna()) > 21 else 0
    ma_past = float(ma.dropna().iloc[j]) if len(ma.dropna()) else ma_now
    ma_slope = (ma_now / ma_past - 1) if ma_past else 0.0
    above = price > ma_now
    d = drs or 0
    if (not above) and ma_slope < -0.002:
        return "baja"
    if above and ma_slope > 0.002:
        if hi >= 88 and d <= 0:                 # arriba pero el impulso ya no acompaña = techo
            return "distrib"
        return "sube"
    if hi >= 85:                                # plana pegada a maximos = distribucion
        return "distrib"
    if pos <= 50:                               # plana en la parte baja = acumulacion
        return "base"
    return "lateral"


# fase -> (emoji, etiqueta, color)
PHASE_INFO = {
    "base":    ("🟦", "base/acumulación", "#5AA9E6"),
    "sube":    ("🟢", "subiendo",         "#2FD08A"),
    "distrib": ("🟠", "distribución",     "#F4B740"),
    "baja":    ("🔴", "cayendo",          "#F4607A"),
    "lateral": ("⚪", "lateral",          "#9FB0C8"),
}


def compute_rs_leaders(stock_close):
    OFF = 65   # ~3 meses (dias de bolsa) para medir la aceleracion del percentil
    def score_at(s, off):
        end = len(s) - 1 - off
        if end < 252:
            return None
        f = lambda k: float(s.iloc[end] / s.iloc[end - k] - 1)
        return 2 * f(63) + f(126) + f(189) + f(252)
    perf, perf_then, hi52 = {}, {}, {}
    for sym, s in stock_close.items():
        s = s.dropna()
        if len(s) < 260:
            continue
        sc = score_at(s, 0)
        if sc is None:
            continue
        perf[sym] = sc
        hi52[sym] = round(float(s.iloc[-1] / s.iloc[-252:].max()) * 100)
        st = score_at(s, OFF)
        if st is not None:
            perf_then[sym] = st
    if len(perf) < 5:
        return None, 0
    order = sorted(perf.items(), key=lambda kv: kv[1])
    n = len(order)
    rs = {sym: int(round(1 + 98 * i / (n - 1))) for i, (sym, _) in enumerate(order)}
    # percentil de hace 3 meses (mismo metodo) para la aceleracion
    rs_then = {}
    if len(perf_then) >= 5:
        ot = sorted(perf_then.items(), key=lambda kv: kv[1])
        nt = len(ot)
        rs_then = {sym: int(round(1 + 98 * i / (nt - 1))) for i, (sym, _) in enumerate(ot)}
    out = {}
    for sec, stocks in SECTOR_STOCKS.items():
        rows = []
        for st in stocks:
            if st in rs:
                drs = (rs[st] - rs_then[st]) if st in rs_then else None
                rows.append({"sym": st, "rs": rs[st], "hi": hi52.get(st, 0), "drs": drs,
                             "phase": _phase(stock_close.get(st), drs)})
        rows.sort(key=lambda x: -x["rs"])
        if rows:
            out[sec] = rows
    # amplitud REAL del sector: % de sus acciones por encima de su media de 50 sesiones (detecta falso liderazgo)
    breadth = {}
    for sec, stocks in SECTOR_STOCKS.items():
        above = tot = 0
        for st in stocks:
            s = stock_close.get(st)
            if s is None:
                continue
            s = s.dropna()
            if len(s) < 55:
                continue
            tot += 1
            if float(s.iloc[-1]) > float(s.iloc[-50:].mean()):
                above += 1
        if tot >= 3:
            breadth[sec] = {"pct": round(100 * above / tot), "n": tot}
    return out, n, breadth


# ----------------------------------------------------------------------
def pct_change(df, sym, weeks=13):
    if sym not in df.columns or len(df) <= weeks:
        return None
    return float(df[sym].iloc[-1] / df[sym].iloc[-1 - weeks] - 1) * 100

def detect_regime(df, rrg, risk, fred_sig=None):
    sig = {
        "Bonos (TLT)": pct_change(df, "TLT"),
        "Credito HY (HYG)": pct_change(df, "HYG"),
        "Oro (GLD)": pct_change(df, "GLD"),
        "Dolar (UUP)": pct_change(df, "UUP"),
        "Apetito riesgo": risk["score"],
    }
    tlt = sig["Bonos (TLT)"] or 0          # <0 => tipos al alza
    hyg = sig["Credito HY (HYG)"] or 0
    gld = sig["Oro (GLD)"] or 0
    uup = sig["Dolar (UUP)"] or 0
    rk = risk["score"]
    scores = {
        "reflacion":   (tlt < -1) * 2 + (rk > 1) * 2 + (hyg > 0) * 1 + (uup < 1) * 1,
        "goldilocks":  (rk > 1) * 2 + (gld < 2) * 1 + (hyg > 0) * 1 + (-2 < tlt < 2) * 1,
        "riskoff":     (rk < -1) * 2 + (hyg < -1) * 2 + (gld > 1) * 1 + (tlt > 1) * 1 + (uup > 1) * 1,
        "estanflacion":(gld > 3) * 2 + (tlt < -1) * 1 + (rk < 0) * 1,
        "pivote":      (tlt > 2) * 2 + (uup < -1) * 1 + (rrg.get("XLK", {}).get("quad") in ("leading", "improving")) * 1,
    }
    # señales macro reales de FRED (si hay key): tienen mas peso que las de mercado
    if fred_sig:
        curve = fred_sig.get("curve_chg", 0) or 0     # pendiente 2s10s, +=empinando
        y10 = fred_sig.get("dgs10_chg", 0) or 0       # tipo 10A, +=al alza
        hyo = fred_sig.get("hy_chg", 0) or 0          # diferencial HY, +=stress de credito
        scores["reflacion"] += (y10 > 0) * 2 + (curve > 0) * 1
        scores["riskoff"] += (hyo > 0.2) * 3 + (curve < 0) * 1
        scores["pivote"] += (y10 < 0) * 2 + (curve > 0.1) * 1
        scores["estanflacion"] += (y10 < 0 and gld > 2) * 1
    best = max(scores, key=scores.get)
    labels = {
        "reflacion": "Reflacion / tipos al alza",
        "goldilocks": "Goldilocks / desinflacion",
        "riskoff": "Risk-off / desaceleracion",
        "estanflacion": "Estanflacion / shock de oferta",
        "pivote": "Pivote dovish / recortes Fed",
    }
    favor = {
        "reflacion": ["XLF","XLE","XLI","XLB","IWM"], "goldilocks": ["XLK","XLY","XLC","IWM"],
        "riskoff": ["XLP","XLU","XLV","GLD","TLT"], "estanflacion": ["XLE","XLB","GLD"],
        "pivote": ["XLRE","XLU","XLK","GLD","IWM"],
    }
    hurt = {
        "reflacion": ["XLU","XLRE","TLT","XLK"], "goldilocks": ["XLP","XLU","GLD"],
        "riskoff": ["XLY","XLK","IWM","HYG","XLE"], "estanflacion": ["XLY","XLK","TLT","XLF"],
        "pivote": ["XLF"],
    }
    sig = {k: (round(v, 1) if v is not None else None) for k, v in sig.items()}
    return {"id": best, "label": labels[best], "favor": favor[best], "hurt": hurt[best], "sig": sig}

def conviction(rrg, regime):
    buy, avoid = [], []
    for s, d in rrg.items():
        if d["quad"] in ("improving", "leading") and s in regime["favor"]:
            buy.append(s)
        if d["quad"] in ("weakening", "lagging") and s in regime["hurt"]:
            avoid.append(s)
    return buy, avoid

# ----------------------------------------------------------------------
# FRED opcional (macro real) + avisos automaticos
# ----------------------------------------------------------------------
def _fred_key():
    """Resuelve la key de FRED: variable de entorno (Secret de GitHub / entorno del PC) ->
    archivo local 'clave_fred*' junto al script o en la carpeta actual (NO se sube; esta en .gitignore)
    -> constante FRED_API_KEY. Tolerante con Windows: acepta clave_fred.txt.txt, BOM y comillas."""
    k = os.environ.get("FRED_API_KEY", "") or FRED_API_KEY
    if k:
        return k.strip()
    import glob
    try:
        here = os.path.dirname(os.path.abspath(__file__))
    except Exception:
        here = os.getcwd()
    seen = []
    for d in (here, os.getcwd()):
        if d and d not in seen:
            seen.append(d)
    for d in seen:
        try:
            for p in sorted(glob.glob(os.path.join(d, "clave_fred*"))):
                try:
                    with open(p, "r", encoding="utf-8-sig") as f:   # utf-8-sig quita el BOM de Notepad
                        v = f.read().strip().strip('"').strip("'").strip()
                    if v:
                        return v
                except Exception:
                    continue
        except Exception:
            continue
    return ""

def fetch_fred():
    """Devuelve (panel_para_mostrar, señales_para_el_regimen) o (None, None)."""
    key = _fred_key()
    if not key:
        return None, None
    series = {"DGS10": "Tipo 10A (%)", "T10Y2Y": "Pendiente 2s10s",
              "BAMLH0A0HYM2": "Diferencial HY (OAS)", "DFII10": "Tipo real 10A (%)"}
    out = {}
    raw = {}
    for sid, lab in series.items():
        try:
            url = ("https://api.stlouisfed.org/fred/series/observations"
                   f"?series_id={sid}&api_key={key}&file_type=json"
                   "&sort_order=desc&limit=70")
            r = requests.get(url, timeout=15).json()
            obs = [o for o in r.get("observations", []) if o["value"] not in (".", "")]
            if not obs:
                continue
            last = float(obs[0]["value"])
            prev = float(obs[min(13, len(obs) - 1)]["value"])
            out[lab] = {"last": round(last, 2), "chg": round(last - prev, 2)}
            raw[sid] = {"last": last, "chg": last - prev}
        except Exception:
            continue
    if not out:
        return None, None
    sig = {
        "dgs10_chg": raw.get("DGS10", {}).get("chg", 0),
        "curve_chg": raw.get("T10Y2Y", {}).get("chg", 0),
        "hy_chg": raw.get("BAMLH0A0HYM2", {}).get("chg", 0),
        "hy_last": raw.get("BAMLH0A0HYM2", {}).get("last", 0),
    }
    return out, sig

def fetch_macro():
    """Descarga macro de FRED (empleo, inflacion, PCE, blandos) y calcula nivel + direccion.
    Defensivo: sin key o si falla una serie, la salta. Devuelve dict {sid: {...}} o None."""
    key = _fred_key()
    if not key:
        return None
    def _obs(sid, limit=90):
        try:
            url = ("https://api.stlouisfed.org/fred/series/observations"
                   f"?series_id={sid}&api_key={key}&file_type=json&sort_order=desc&limit={limit}")
            r = requests.get(url, timeout=15).json()
            return [float(o["value"]) for o in r.get("observations", []) if o["value"] not in (".", "")]
        except Exception:
            return []
    def _yoy(v, per=12):
        return (v[0] / v[per] - 1.0) * 100 if len(v) > per and v[per] else None
    m = {}
    # INFLACION (indices -> YoY y direccion del YoY a 6 meses)
    for sid, lab in (("PCEPILFE", "PCE subyacente"), ("CPILFESL", "IPC subyacente")):
        v = _obs(sid)
        yoy = _yoy(v)
        yoy6 = _yoy(v[6:]) if len(v) > 18 else None
        if yoy is not None:
            m[sid] = {"lab": lab, "val": round(yoy, 2), "unit": "% i.a.",
                      "dir": round(yoy - yoy6, 2) if yoy6 is not None else 0.0, "kind": "hard", "goodup": False}
    # EMPLEO
    pay = _obs("PAYEMS")
    if len(pay) > 4:
        chg3 = (pay[0] - pay[3]) / 3.0
        m["PAYEMS"] = {"lab": "Nóminas (prom. 3m)", "val": round(chg3, 0), "unit": "k/mes",
                       "dir": round((pay[0] - pay[1]) - (pay[3] - pay[4]), 0), "kind": "hard", "goodup": True}
    un = _obs("UNRATE")
    if len(un) > 3:
        m["UNRATE"] = {"lab": "Paro", "val": round(un[0], 2), "unit": "%",
                       "dir": round(un[0] - un[3], 2), "kind": "hard", "goodup": False}
    cl = _obs("ICSA", limit=60)
    if len(cl) > 8:
        m4, p4 = sum(cl[0:4]) / 4.0, sum(cl[4:8]) / 4.0
        m["ICSA"] = {"lab": "Paro semanal (4s)", "val": round(m4 / 1000, 0), "unit": "k",
                     "dir": round((m4 - p4) / 1000, 1), "kind": "soft", "goodup": False}
    # CRECIMIENTO
    ip = _obs("INDPRO")
    yoy_ip = _yoy(ip)
    if yoy_ip is not None:
        yoy_ip6 = _yoy(ip[6:]) if len(ip) > 18 else None
        m["INDPRO"] = {"lab": "Prod. industrial", "val": round(yoy_ip, 2), "unit": "% i.a.",
                       "dir": round(yoy_ip - yoy_ip6, 2) if yoy_ip6 is not None else 0.0, "kind": "hard", "goodup": True}
    # BLANDOS (lideres)
    um = _obs("UMCSENT")
    if len(um) > 3:
        m["UMCSENT"] = {"lab": "Confianza consumidor", "val": round(um[0], 1), "unit": "",
                        "dir": round(um[0] - um[3], 1), "kind": "soft", "goodup": True}
    cu = _obs("T10Y2Y", limit=70)
    if len(cu) > 13:
        m["T10Y2Y"] = {"lab": "Curva 2s10s", "val": round(cu[0], 2), "unit": "pp",
                       "dir": round(cu[0] - cu[13], 2), "kind": "soft", "goodup": True}
    hy = _obs("BAMLH0A0HYM2", limit=70)
    if len(hy) > 13:
        m["HY"] = {"lab": "Spread HY (riesgo)", "val": round(hy[0], 2), "unit": "pp",
                   "dir": round(hy[0] - hy[13], 2), "kind": "soft", "goodup": False}
    return m or None

def compute_macro_regime(m, ism):
    """Reloj de inversion: cruza direccion de CRECIMIENTO x direccion de INFLACION -> cuadrante + playbook.
    Las probabilidades son GRUESAS (base-rate del regimen), nunca una prediccion."""
    if not m:
        return None
    # eje INFLACION
    infl_dir, n = 0.0, 0
    for sid in ("PCEPILFE", "CPILFESL"):
        if sid in m:
            infl_dir += m[sid]["dir"]; n += 1
    infl_dir = infl_dir / n if n else 0.0
    # banda muerta mas ancha (±0.20pp): solo "subiendo/bajando" si la senal es CLARA; evita que el regimen
    # baile entre sobrecalentamiento y goldilocks por rozar la frontera con cada dato/revision de FRED.
    infl_up = infl_dir > 0.20
    infl_down = infl_dir < -0.20
    infl_weak = not infl_up and not infl_down          # senal de inflacion ambigua / en transicion
    infl_lbl = "subiendo" if infl_up else ("bajando" if infl_down else "plana (en transición)")
    # eje CRECIMIENTO (compuesto blandos + hard; ISM pesa doble)
    g, gmax = 0, 0
    if ism is not None:
        gmax += 2; g += (2 if ism >= 53 else (1 if ism >= 50 else (-1 if ism >= 47 else -2)))
    if "INDPRO" in m:
        gmax += 1; g += (1 if (m["INDPRO"]["val"] > 0 and m["INDPRO"]["dir"] >= 0) else (-1 if (m["INDPRO"]["val"] < 0 or m["INDPRO"]["dir"] < -0.2) else 0))
    if "ICSA" in m:
        gmax += 1; g += (1 if m["ICSA"]["dir"] < 0 else (-1 if m["ICSA"]["dir"] > 5 else 0))
    if "UMCSENT" in m:
        gmax += 1; g += (1 if m["UMCSENT"]["dir"] > 0 else (-1 if m["UMCSENT"]["dir"] < -2 else 0))
    if "PAYEMS" in m:
        gmax += 1; g += (1 if m["PAYEMS"]["val"] > 100 else (-1 if m["PAYEMS"]["val"] < 50 else 0))
    if "T10Y2Y" in m:
        gmax += 1; g += (1 if m["T10Y2Y"]["dir"] > 0.05 else 0)
    grow_up = g > 0
    grow_lbl = "acelerando" if g > 0 else ("desacelerando" if g < 0 else "estable")
    # cuadrante del reloj de inversion
    if grow_up and not infl_up:
        quad, label = "recuperacion", "Recuperación / reflación temprana"
        favor, hurt = ["XLK", "XLY", "XLF", "IWM", "XLC", "SMH"], ["XLP", "XLU", "TLT", "GLD"]
    elif grow_up and infl_up:
        quad, label = "sobrecalentamiento", "Sobrecalentamiento"
        favor, hurt = ["XLE", "XLB", "XLF", "COPX", "GLD"], ["TLT", "XLK", "XLY"]
    elif (not grow_up) and infl_up:
        quad, label = "estanflacion", "Estanflación / shock de oferta"
        favor, hurt = ["XLE", "GLD", "XLP", "XLU", "GDX"], ["XLY", "IWM", "XLK", "SMH"]
    else:
        quad, label = "desinflacion", "Desinflación / desaceleración"
        favor, hurt = ["TLT", "XLU", "XLP", "XLV", "GLD"], ["XLE", "XLB", "IWM", "XLF"]
    # probabilidades GRUESAS (transparentes): cuanto mas clara la senal, mas peso al caso base
    conf = abs(g) / max(gmax, 1)
    base = 0.45 + 0.20 * conf
    rest = 1 - base
    bull, bear = (rest * 0.6, rest * 0.4) if g >= 0 else (rest * 0.4, rest * 0.6)
    pr = {"base": round(base * 100), "bull": round(bull * 100), "bear": round(bear * 100)}
    return {"quad": quad, "label": label, "favor": favor, "hurt": hurt,
            "grow_lbl": grow_lbl, "infl_lbl": infl_lbl, "grow_up": grow_up, "infl_up": infl_up,
            "g": g, "gmax": gmax, "conf": conf, "pr": pr, "infl_weak": infl_weak}

def notify(text):
    """Envia el resumen a Telegram y/o a un webhook (Discord/Slack). Devuelve True si envio algo."""
    sent = False
    tok = os.environ.get("TELEGRAM_TOKEN") or TELEGRAM_TOKEN
    chat = os.environ.get("TELEGRAM_CHAT_ID") or TELEGRAM_CHAT_ID
    if tok and chat:
        try:
            requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                          data={"chat_id": chat, "text": text}, timeout=15)
            sent = True
        except Exception:
            pass
    hook = os.environ.get("WEBHOOK_URL") or WEBHOOK_URL
    if hook:
        try:
            requests.post(hook, json={"content": text, "text": text}, timeout=15)
            sent = True
        except Exception:
            pass
    return sent

# ----------------------------------------------------------------------
# Analisis con IA (opcional)
# ----------------------------------------------------------------------
def state_summary(rrg, risk, regime, breadth, plan, flow):
    by_q = {"leading": [], "weakening": [], "improving": [], "lagging": []}
    for s, d in rrg.items():
        by_q[d["quad"]].append(s)
    divs = [f"{s} ({d['diverg']})" for s, d in (flow or {}).items() if d.get("diverg")]
    lines = [
        f"Regimen macro: {regime['label']}. Apetito de riesgo: {risk['label']} ({risk['score']:+}).",
        f"Amplitud: {breadth['leaders']}% con fuerza>indice, {breadth['uptrend']}% en tendencia.",
        f"LIDER: {', '.join(by_q['leading']) or '-'}.",
        f"DEBILITANDOSE: {', '.join(by_q['weakening']) or '-'}.",
        f"MEJORANDO: {', '.join(by_q['improving']) or '-'}.",
        f"REZAGADO: {', '.join(by_q['lagging']) or '-'}.",
    ]
    if divs:
        lines.append(f"Divergencias de flujo: {', '.join(divs)}.")
    if plan:
        lines.append(f"Caida actual del S&P desde maximos: {plan['dd']}%.")
    return "\n".join(lines)

def _cargar_key(constante, var_entorno, archivo):
    """Busca la key en 3 sitios: constante del codigo, variable de entorno, y un ARCHIVO de texto
    junto al script (la via sin tocar codigo). Si esta en un repo git, se auto-anade a .gitignore."""
    if constante:
        return constante.strip()
    v = os.environ.get(var_entorno, "").strip()
    if v:
        return v
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        ruta = os.path.join(base, archivo)
        if os.path.exists(ruta):
            with open(ruta, "r", encoding="utf-8") as fh:
                lineas = [l.strip() for l in fh.read().splitlines() if l.strip()]
            k = lineas[0] if lineas else ""
            if k:
                if os.path.isdir(os.path.join(base, ".git")):
                    gi = os.path.join(base, ".gitignore")
                    try:
                        cont = open(gi, "r", encoding="utf-8").read() if os.path.exists(gi) else ""
                        if archivo not in cont:
                            with open(gi, "a", encoding="utf-8") as fh:
                                fh.write(("" if (not cont or cont.endswith(chr(10))) else chr(10)) + archivo + chr(10))
                            print("  (proteccion) " + archivo + " anadido a .gitignore")
                    except Exception:
                        print("  AVISO: no subas " + archivo + " al repositorio")
                return k
    except Exception:
        pass
    return ""


def run_ia_auto(snap, fecha):
    """EJECUTA los prompts automaticos contra la API de Anthropic al construir el terminal.
    Devuelve {key: {"title","text","ok","modelo"}} o None si no hay API key. El maestro siempre
    (si IA_AUTO); los de IA_AUTO_EXTRA, ademas. Con IA_WEB_SEARCH la IA puede buscar 13F, VIX,
    earnings... (coste extra por busqueda). Errores legibles, nunca rompe el build."""
    if not IA_AUTO:
        return None
    if IA_PROVIDER == "openai_compat":
        key = _cargar_key(IA_COMPAT_KEY, "IA_COMPAT_KEY", "ia_key.txt")
    else:
        key = _cargar_key(ANTHROPIC_API_KEY, "ANTHROPIC_API_KEY", "anthropic_key.txt")
    if not key:
        print("  IA automatica: SIN key (crea ia_key.txt junto al script para activarla)")
        return None
    print("  IA automatica: key encontrada, consultando al proveedor ...")
    quiero = ["resumen"] + [k for k in (IA_AUTO_EXTRA or []) if k != "resumen"]
    pmap = {k: (t, p) for k, t, p in IA_PROMPTS}
    out = {}
    for k in quiero:
        if k not in pmap:
            continue
        title, prompt = pmap[k]
        _prompt_full = prompt + ia_data_block(snap, fecha)
        if IA_PROVIDER == "openai_compat":
            _modelo = IA_COMPAT_MODEL
            print(f"  IA automatica ({_modelo} via proveedor compatible): ejecutando '{k}' ...")
            try:
                r = requests.post(IA_COMPAT_BASE.rstrip("/") + "/chat/completions",
                                  headers={"Authorization": "Bearer " + key, "content-type": "application/json"},
                                  json={"model": _modelo, "max_tokens": int(IA_MAX_TOKENS),
                                        "messages": [{"role": "user", "content": _prompt_full}]},
                                  timeout=180)
                j = r.json()
                if r.status_code != 200:
                    err = (j.get("error") or {}).get("message", f"HTTP {r.status_code}")
                    out[k] = {"title": title, "text": "La API devolvió un error: " + str(err), "ok": False, "modelo": _modelo}
                    continue
                txt = ((j.get("choices") or [{}])[0].get("message") or {}).get("content", "").strip()
                _nota = chr(10) + chr(10) + "(Proveedor compatible sin búsqueda web: las referencias externas salen del conocimiento del modelo, no de fuentes en vivo.)" if txt else ""
                out[k] = {"title": title, "text": (txt + _nota) or "(respuesta vacía)", "ok": bool(txt), "modelo": _modelo}
            except Exception as e:
                out[k] = {"title": title, "text": "No se pudo conectar con el proveedor compatible: " + type(e).__name__ +
                          ". Revisa internet, la URL base y la key.", "ok": False, "modelo": _modelo}
            continue
        print(f"  IA automatica: ejecutando '{k}' ({IA_AUTO_MODEL}" + (", con busqueda web" if IA_WEB_SEARCH else "") + ") ...")
        body = {"model": IA_AUTO_MODEL, "max_tokens": int(IA_MAX_TOKENS),
                "messages": [{"role": "user", "content": _prompt_full}]}
        if IA_WEB_SEARCH:
            body["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}]
        try:
            r = requests.post("https://api.anthropic.com/v1/messages",
                              headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                       "content-type": "application/json"},
                              json=body, timeout=180)
            j = r.json()
            if r.status_code != 200:
                err = (j.get("error") or {}).get("message", f"HTTP {r.status_code}")
                out[k] = {"title": title, "text": f"La API devolvió un error: {err}", "ok": False, "modelo": IA_AUTO_MODEL}
                continue
            txt = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text").strip()
            out[k] = {"title": title, "text": txt or "(respuesta vacía)", "ok": bool(txt), "modelo": IA_AUTO_MODEL}
        except Exception as e:
            out[k] = {"title": title, "text": f"No se pudo conectar con la API: {type(e).__name__}. "
                      "Revisa internet y la key; el resto del terminal no se ve afectado.", "ok": False, "modelo": IA_AUTO_MODEL}
    return out or None


def ai_commentary(summary):
    key = _cargar_key(ANTHROPIC_API_KEY, "ANTHROPIC_API_KEY", "anthropic_key.txt")
    if not key:
        return None
    prompt = ("Eres analista de rotacion sectorial. Con estos datos de cierre (no en tiempo real), "
              "escribe un analisis breve en espanol (maximo 150 palabras): que esta rotando, que vigilar "
              "para entrar o proteger, y como encaja con la macro. Se concreto y prudente; no es asesoramiento.\n\n"
              + summary)
    try:
        r = requests.post("https://api.anthropic.com/v1/messages",
                          headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                   "content-type": "application/json"},
                          json={"model": AI_MODEL, "max_tokens": 500,
                                "messages": [{"role": "user", "content": prompt}]},
                          timeout=40)
        j = r.json()
        txt = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
        return txt.strip() or None
    except Exception as _dege:
        _deg("ai_commentary:4344", _dege)
        return None

# ----------------------------------------------------------------------
# Render del panel HTML (SVG + tablas, sin JS)
# ----------------------------------------------------------------------
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{--bg:#0A0E17;--bg2:#0F1521;--bg3:#131B2A;--line:#1E2A3D;--line2:#2A3A52;
--txt:#E6EDF6;--txt2:#93A4BC;--txt3:#5E708A;--accent:#5B8CFF;
background:var(--bg);color:var(--txt);font-family:ui-sans-serif,system-ui,'Segoe UI',Roboto,sans-serif;
line-height:1.45;-webkit-font-smoothing:antialiased;padding-bottom:40px}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-variant-numeric:tabular-nums}
header{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;
padding:14px 22px;border-bottom:1px solid var(--line);background:var(--bg2)}
.brand{display:flex;align-items:center;gap:11px}
.title{font-size:17px;font-weight:800;letter-spacing:4px}
.sub{font-size:10.5px;letter-spacing:2px;text-transform:uppercase;color:var(--txt3)}
.status{display:flex;gap:14px;flex-wrap:wrap;align-items:center;font-family:ui-monospace,monospace;font-size:11px;color:var(--txt2)}
.status b{color:var(--txt3);font-weight:500;font-size:9.5px;letter-spacing:1px;text-transform:uppercase;margin-right:5px}
.pill{font-size:10px;font-weight:700;letter-spacing:1px;padding:3px 9px;border-radius:4px;font-family:ui-monospace,monospace}
.RiskON{background:rgba(47,208,138,.14);color:#2FD08A}.RiskOFF{background:rgba(244,96,122,.14);color:#F4607A}
.Neutral{background:rgba(147,164,188,.12);color:var(--txt2)}
main{max-width:1280px;margin:0 auto;padding:16px;display:grid;grid-template-columns:1.55fr 1fr;gap:14px}
@media(max-width:900px){main{grid-template-columns:1fr}}
.panel{background:var(--bg2);border:1px solid var(--line);border-radius:10px;padding:14px 15px;margin-bottom:14px}
.panel h2{font-size:12.5px;font-weight:600;margin-bottom:10px}
.note{font-size:11.5px;color:var(--txt2);margin:6px 0 10px}
svg{width:100%;height:auto;display:block;background:var(--bg);border-radius:8px}
.legend{display:flex;gap:14px;flex-wrap:wrap;margin-top:10px;font-size:11px;color:var(--txt2)}
.legend i{width:9px;height:9px;border-radius:2px;display:inline-block;margin-right:5px}
.alerts{display:flex;flex-direction:column;gap:7px}
.alert{display:flex;gap:9px;background:var(--bg3);border:1px solid var(--line);border-left-width:3px;border-radius:7px;padding:8px 10px}
.a-warn{border-left-color:#F4B740}.a-in{border-left-color:#4CC2E0}.a-lead{border-left-color:#2FD08A}.a-down{border-left-color:#F4607A}
.atk{font-family:ui-monospace,monospace;font-weight:700;font-size:12px;min-width:42px}
.atx{font-size:11.5px;color:var(--txt2)}
table{width:100%;border-collapse:collapse;font-size:12px}
th{font-size:10px;text-transform:uppercase;letter-spacing:.6px;color:var(--txt3);text-align:left;padding:6px}
td{padding:7px 6px;border-top:1px solid var(--line);color:var(--txt2)}
td.r{text-align:right;font-family:ui-monospace,monospace}
.tk b{color:var(--txt);font-family:ui-monospace,monospace}.tk em{color:var(--txt3);font-style:normal;font-size:10px;display:block}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:5px}
.bar-row{display:grid;grid-template-columns:46px 1fr 44px;align-items:center;gap:9px;margin-bottom:6px}
.bar-lab{font-family:ui-monospace,monospace;font-size:12px;color:var(--txt)}
.bar-track{position:relative;height:16px;background:var(--bg3);border-radius:4px}
.bar-mid{position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--line2)}
.bar{position:absolute;top:2px;bottom:2px;border-radius:3px}
.bar-val{text-align:right;font-family:ui-monospace,monospace;font-size:11.5px}
.meter{margin-bottom:12px}.meter-top{display:flex;justify-content:space-between;font-size:11.5px;color:var(--txt2);margin-bottom:5px}
.meter-top b{font-family:ui-monospace,monospace}.meter-track{height:7px;background:var(--bg3);border-radius:4px;overflow:hidden}
.meter-fill{height:100%;border-radius:4px}
.bigrisk{font-size:22px;font-weight:800;letter-spacing:2px;text-align:center;padding:12px 0 6px;font-family:ui-monospace,monospace}
.tags{display:flex;flex-wrap:wrap;gap:5px;margin-top:5px}
.tag{font-family:ui-monospace,monospace;font-size:11px;padding:2px 7px;border-radius:4px;font-weight:600}
.tag.good{background:rgba(47,208,138,.12);color:#2FD08A}.tag.bad{background:rgba(244,96,122,.12);color:#F4607A}
.conv{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:10px}
@media(max-width:560px){.conv{grid-template-columns:1fr}}
.conv-box{border:1px solid var(--line);border-radius:8px;padding:11px;background:var(--bg3)}
.conv-box h3{font-size:11.5px;margin-bottom:5px}
.kv{display:flex;justify-content:space-between;font-size:12px;padding:5px 0;border-bottom:1px solid var(--line)}
.kv span{color:var(--txt3)}.kv b{color:var(--txt);font-family:ui-monospace,monospace;font-weight:500}
.full{grid-column:1/-1}
.summary{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:2px}
@media(max-width:700px){.summary{grid-template-columns:1fr 1fr}}
.scard{background:var(--bg2);border:1px solid var(--line);border-radius:10px;padding:11px 13px}
.scard .lab{font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--txt3);margin-bottom:6px}
.scard .big{font-size:17px;font-weight:800;font-family:ui-monospace,monospace;line-height:1.1}
.scard .sm{font-size:10.5px;color:var(--txt2);margin-top:4px}
td.spk{width:84px;padding-right:10px}
td.spk svg{display:block;opacity:.9}
td.ts2{font-size:10.5px;color:var(--txt3);white-space:nowrap}
.planwrap{display:grid;grid-template-columns:1.1fr 1fr;gap:16px}
@media(max-width:760px){.planwrap{grid-template-columns:1fr}}
.dd-now{background:var(--bg3);border:1px solid var(--line);border-radius:9px;padding:11px 13px;margin-bottom:10px}
.dd-now .lab{font-size:9.5px;text-transform:uppercase;letter-spacing:1px;color:var(--txt3)}
.dd-big{font-size:30px;font-weight:800;font-family:ui-monospace,monospace;line-height:1.1;margin:2px 0}
.dd-now .sm{font-size:11px;color:var(--txt2);font-family:ui-monospace,monospace}
.rung{display:grid;grid-template-columns:54px 1fr auto auto auto;gap:10px;align-items:center;
background:var(--bg3);border:1px solid var(--line);border-left:3px solid var(--line);border-radius:8px;padding:9px 11px;margin-bottom:7px}
.rk-thr{font-family:ui-monospace,monospace;font-weight:800;font-size:15px;color:var(--txt)}
.rk-lvl{font-family:ui-monospace,monospace;font-size:11.5px;color:var(--txt2)}
.rk-pct{font-size:11.5px;color:#5B8CFF;font-weight:600}
.rk-veh{font-family:ui-monospace,monospace;font-size:11px;color:#F4B740;background:rgba(244,183,64,.12);padding:1px 6px;border-radius:4px}
.rk-st{font-size:10.5px;font-family:ui-monospace,monospace;text-align:right}
@media(max-width:520px){.rung{grid-template-columns:46px 1fr auto;row-gap:4px}.rk-veh,.rk-st{grid-column:2/4}}
.planstats table{width:100%}
.planstats th{vertical-align:bottom;line-height:1.15}
.veh3{font-family:ui-monospace,monospace;font-size:10.5px;color:#F4B740;background:rgba(244,183,64,.12);padding:1px 6px;border-radius:4px}
svg circle{cursor:help}
td.tk{cursor:help}
.veh3.off{color:#5E708A;background:none}
.qgrid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
@media(max-width:560px){.qgrid{grid-template-columns:1fr}}
.qcell{background:var(--bg3);border:1px solid var(--line);border-radius:9px;padding:10px 11px;min-height:84px}
.qhead{font-family:ui-monospace,monospace;font-size:11px;font-weight:700;letter-spacing:1px;margin-bottom:8px}
.qhead span{color:var(--txt3);font-weight:400;letter-spacing:0;text-transform:none}
.qchips{display:flex;flex-wrap:wrap;gap:6px}
.qchip{border:1px solid var(--line);border-radius:6px;padding:3px 7px;font-size:11px;background:var(--bg2);cursor:help}
.qchip b{font-family:ui-monospace,monospace}.qchip i{color:var(--txt3);font-style:normal;font-size:9.5px;font-family:ui-monospace,monospace}
.qempty{color:var(--txt3);font-size:11px}
.viewtabs{display:flex;gap:6px;margin-bottom:10px}
.viewtab{font-size:11px;color:var(--txt3);background:var(--bg3);border:1px solid var(--line);border-radius:6px;padding:5px 12px;cursor:pointer}
.viewtab.active{color:#fff;background:#5B8CFF;border-color:#5B8CFF;font-weight:600}
.ai-box{background:linear-gradient(180deg,rgba(91,140,255,.07),rgba(91,140,255,0));border:1px solid rgba(91,140,255,.25);
border-radius:9px;padding:12px 14px;font-size:12.5px;color:var(--txt);line-height:1.55;white-space:pre-wrap}
.ai-btn{display:inline-flex;align-items:center;gap:7px;background:#5B8CFF;color:#fff;border:none;border-radius:8px;
padding:9px 14px;font-size:12.5px;font-weight:600;cursor:pointer;text-decoration:none}
.ai-btn.alt{background:var(--bg3);color:var(--txt2);border:1px solid var(--line)}
.hold-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px}
@media(max-width:600px){.hold-grid{grid-template-columns:1fr}}
.hold{display:flex;justify-content:space-between;align-items:center;gap:8px;background:var(--bg3);border:1px solid var(--line);
border-radius:7px;padding:7px 10px;font-size:11.5px}
.hold .h-sym{font-family:ui-monospace,monospace;font-weight:700;color:var(--txt)}
.hold .h-top{color:var(--txt2);font-family:ui-monospace,monospace;font-size:11px}
.hold a{color:#5B8CFF;text-decoration:none;font-size:10.5px}
.lrow{display:grid;grid-template-columns:150px 1fr;gap:12px;align-items:center;padding:8px 0;border-bottom:1px solid var(--line)}
@media(max-width:560px){.lrow{grid-template-columns:1fr;gap:4px}}
.lsec b{font-family:ui-monospace,monospace;color:var(--txt)}.lsec span{color:var(--txt3);font-size:10.5px}
.lchips{display:flex;flex-wrap:wrap;gap:6px}
.lchip{display:inline-flex;align-items:center;gap:5px;background:var(--bg3);border:1px solid var(--line);border-radius:7px;padding:3px 7px;font-size:11.5px}
.lchip b{font-family:ui-monospace,monospace;color:var(--txt)}
.rsbadge{font-family:ui-monospace,monospace;font-size:10px;border:1px solid;border-radius:4px;padding:0 4px}
.accel{font-family:ui-monospace,monospace;font-size:10px;color:#2FD08A;font-weight:700}
.accel.down{color:#F4607A}
.emrow{display:grid;grid-template-columns:64px 86px 60px 96px 1fr auto;gap:10px;align-items:center;padding:8px 0;border-bottom:1px solid var(--line);font-size:12px}
@media(max-width:600px){.emrow{grid-template-columns:1fr 1fr;gap:4px 10px}}
.em-sym{font-family:ui-monospace,monospace;font-weight:700;color:var(--txt)}
.em-sec{font-family:ui-monospace,monospace;color:var(--txt2);font-size:11px}
.em-rs{font-family:ui-monospace,monospace;color:var(--txt2)}
.em-drs{font-family:ui-monospace,monospace;font-weight:700}
.em-hi{font-family:ui-monospace,monospace;color:var(--txt3);font-size:11px}
.emtag{justify-self:end;font-size:9.5px;color:#0A0E17;background:#2FD08A;border-radius:4px;padding:1px 7px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}
.wkrow{display:grid;grid-template-columns:78px 1fr auto auto auto auto;gap:10px;align-items:center;padding:8px 0;border-bottom:1px solid var(--line);font-size:12px}
@media(max-width:620px){.wkrow{grid-template-columns:1fr 1fr;gap:4px 10px}}
.wk-sym{font-family:ui-monospace,monospace;font-weight:700;color:var(--txt)}
.wk-name{color:var(--txt2);font-size:11px}
.wk-eur{font-family:ui-monospace,monospace;font-weight:700;color:#5B8CFF}
.wk-desde{font-family:ui-monospace,monospace;font-size:11px;margin-left:8px;padding:1px 6px;border:1px solid #ffffff18;border-radius:5px}
.wk-x3{font-family:ui-monospace,monospace;font-size:10px;color:#F4B740;background:rgba(244,183,64,.12);padding:1px 6px;border-radius:4px}
.wk-stk{font-family:ui-monospace,monospace;font-size:10.5px;color:var(--txt3)}
.wk-new{justify-self:end;font-size:9.5px;color:#0A0E17;background:#4CC2E0;border-radius:4px;padding:1px 7px;font-weight:700;letter-spacing:.5px}
.wk-keep{justify-self:end;font-size:9.5px;color:var(--txt3);border:1px solid var(--line);border-radius:4px;padding:1px 7px}
.fgrid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
@media(max-width:680px){.fgrid{grid-template-columns:1fr}}
.fcol{background:var(--bg3);border:1px solid var(--line);border-radius:9px;padding:10px 12px}
.fhead{font-size:11px;font-weight:700;margin-bottom:8px;font-family:ui-monospace,monospace}
.fchips{display:flex;flex-wrap:wrap;gap:6px}
.fchip{display:inline-flex;align-items:center;gap:5px;border:1px solid var(--line);border-radius:6px;padding:3px 8px;font-size:11.5px;font-family:ui-monospace,monospace;font-weight:600;background:var(--bg2)}
.ring1{width:9px;height:9px;border-radius:50%;border:2px solid #2FD08A;display:inline-block;margin-right:2px}
.ring2{width:11px;height:11px;border-radius:50%;border:2px solid #F4607A;box-shadow:0 0 0 2px #F4607A;display:inline-block;margin-right:2px}
.hm{width:100%;border-collapse:separate;border-spacing:3px}
.hm-h{font-size:10px;color:var(--txt3);text-align:center;padding:4px 0;font-family:ui-monospace,monospace;text-transform:uppercase;letter-spacing:.5px;font-weight:600}
.hm-name{text-align:left;padding:6px 8px;font-size:12px;white-space:nowrap}
.hm-name b{font-family:ui-monospace,monospace}
.hm-name span{color:var(--txt3);font-size:11px}
.hm-c{text-align:center;font-family:ui-monospace,monospace;font-size:12px;font-weight:700;border-radius:5px;height:30px;width:18%}
.hm-turn{font-size:9.5px;color:#0A0E17;background:#4CC2E0;border-radius:4px;padding:1px 6px;font-weight:700;letter-spacing:.3px;margin-left:6px}
.sc{width:100%;border-collapse:separate;border-spacing:2px}
.sc-h{font-size:9.5px;color:var(--txt3);text-align:center;padding:4px 2px;font-family:ui-monospace,monospace;text-transform:uppercase;letter-spacing:.3px;font-weight:600}
.sc-name{text-align:left;padding:7px 8px;font-size:12px;white-space:nowrap;background:var(--bg3);border-radius:5px}
.sc-name b{font-family:ui-monospace,monospace}
.sc-name span{color:var(--txt3);font-size:11px}
.sc-c{text-align:center;font-size:14px;font-weight:700;background:var(--bg3);border-radius:5px}
.sc-tot{text-align:center;font-family:ui-monospace,monospace;font-weight:700;font-size:13px;background:var(--bg3);border-radius:5px}
.sc-act{text-align:center;font-size:11px;font-weight:700;background:var(--bg3);border-radius:5px;padding:0 6px}
.sc-acc{font-size:9px;color:#0A0E17;background:#F4B740;border-radius:4px;padding:1px 5px;font-weight:700;margin-left:6px}
.sc-warn{font-size:9px;color:#0A0E17;background:#F4607A;border-radius:4px;padding:1px 5px;font-weight:700;margin-left:6px}
.lbreadth{font-size:10px;border:1px solid;border-radius:5px;padding:1px 6px;margin-left:8px;font-weight:600}
.sc-grp,.rk-grp{background:#0E1521 !important;color:#5B8CFF;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;padding:8px 10px !important;text-align:left;border-top:2px solid #1C2740}
.fgwrap{display:flex;align-items:baseline;gap:14px;margin:2px 0 4px}
.fgnum{font-size:42px;font-weight:800;line-height:1}.fgnum span{font-size:15px;color:var(--txt3);font-weight:600}
.fgzone{font-size:17px;font-weight:700}
.fgbar{position:relative;height:10px;border-radius:6px;margin:8px 0 6px;background:linear-gradient(90deg,#F4607A,#F4824A,#F4B740,#7FC97F,#2FD08A)}
.fgmark{position:absolute;top:-3px;width:3px;height:16px;background:#fff;transform:translateX(-50%);border-radius:2px;box-shadow:0 0 3px #000}
.fgctx{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0}
.fgchip{font-size:11px;color:var(--txt3);border:1px solid #1C2740;border-radius:6px;padding:2px 7px}
.verdict{border:1px solid #2B3850;background:linear-gradient(180deg,rgba(91,140,255,.06),var(--bg2))}
.vrow{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;padding:7px 0;border-bottom:1px solid #131C2B;font-size:14px;color:#C7D3E3;line-height:1.5}
.vrow:last-of-type{border-bottom:none}
.vk{flex:0 0 auto;font-size:10px;font-weight:700;color:#0A0E17;border-radius:5px;padding:2px 9px;letter-spacing:.3px}
details.why{grid-column:1/-1;margin-bottom:14px}
details.why[open]{display:grid;grid-template-columns:1.55fr 1fr;gap:14px}
@media(max-width:900px){details.why[open]{grid-template-columns:1fr}}
details.why>summary{grid-column:1/-1;cursor:pointer;list-style:none;background:var(--bg2);border:1px solid var(--line);border-radius:10px;padding:13px 15px;font-size:14px;font-weight:600;color:var(--txt1);user-select:none}
details.why>summary::-webkit-details-marker{display:none}
details.why>summary::before{content:'▸ ';color:#5B8CFF}
details.why>summary span{color:var(--txt3);font-weight:400;font-size:12px}
details.why[open]>summary{color:#5B8CFF}
details.why[open]>summary::before{content:'▾ '}
.readbox{display:flex;gap:12px;align-items:flex-start;background:var(--bg3);border:1px solid var(--line);border-radius:10px;padding:14px}
.read-light{width:14px;height:14px;border-radius:50%;flex:0 0 auto;margin-top:3px;box-shadow:0 0 12px currentColor}
.read-txt{font-size:13px;color:var(--txt);margin-bottom:6px}
.read-stance{font-size:12.5px;font-weight:700}
.pb{width:100%;border-collapse:separate;border-spacing:2px;margin-top:4px}
.pb th{font-size:10px;color:var(--txt3);text-transform:uppercase;letter-spacing:.3px;padding:4px 8px;text-align:right}
.pb .pb-l{text-align:left}
.pb td{background:var(--bg3);padding:7px 8px;font-size:12px}
.pb-l{text-align:left;border-radius:5px 0 0 5px}
.pb-v{text-align:right;font-family:ui-monospace,monospace;font-weight:700}
.pb-n{text-align:right;color:var(--txt3);font-size:11px;border-radius:0 5px 5px 0}
.cand{background:var(--bg3);border:1px solid var(--line);border-radius:9px;padding:10px 12px;margin-bottom:8px}
.cand-h{display:flex;align-items:center;gap:8px;font-size:13px;margin-bottom:4px}
.cand-h b{font-family:ui-monospace,monospace}
.cand-h span{color:var(--txt3);font-size:11px}
.cand-sc{margin-left:auto;font-family:ui-monospace,monospace;font-weight:700}
.cand-r{font-size:12px;color:var(--txt2);margin-bottom:2px}
.cand-p{font-size:12px;color:var(--txt)}
.se{width:100%;border-collapse:separate;border-spacing:2px}
.scrollx{overflow-x:auto;-webkit-overflow-scrolling:touch;max-width:100%}
.se th{font-size:10px;color:var(--txt3);text-transform:uppercase;letter-spacing:.3px;padding:4px 8px;text-align:center}
.se .se-l{text-align:left}
.se td{background:var(--bg3);padding:7px 8px;font-size:12px}
.se-l{text-align:left;border-radius:5px 0 0 5px;white-space:nowrap}
.se-c{text-align:center}
.se-pup{font-family:ui-monospace,monospace;font-weight:700;font-size:13px;display:block}
.se-avg{font-family:ui-monospace,monospace;font-size:10px;display:block;margin-top:1px}
.se-hi td{background:#1A2233}
.se-now{font-size:9px;color:#0A0E17;background:#5B8CFF;border-radius:4px;padding:1px 6px;font-weight:700;margin-left:8px}
.se-next{font-size:9px;color:#0A0E17;background:#2FD08A;border-radius:4px;padding:1px 6px;font-weight:700;margin-left:8px}
.bar-cmf{font-family:ui-monospace,monospace;font-size:10px;margin-left:8px;min-width:62px;text-align:right}
@media(max-width:640px){.sc{min-width:600px}.sc-h{font-size:8px}.sc-act{font-size:9px}}
@media(max-width:600px){.hm-name span{display:none}.hm-c{font-size:11px}}
footer{font-size:10.5px;color:var(--txt3);text-align:center;padding:18px 20px;max-width:760px;margin:0 auto;line-height:1.6}
"""

def render_svg(rrg, flow=None, quality=None):
    flow = flow or {}
    W, H = 1040, 720
    mL, mR, mT, mB = 60, 66, 28, 54
    pw, ph = W - mL - mR, H - mT - mB
    maxdev = 4.0
    for d in rrg.values():
        maxdev = max(maxdev, abs(d["ratio"] - 100), abs(d["mom"] - 100))
        for r, m in d["tail"]:
            maxdev = max(maxdev, abs(r - 100), abs(m - 100))
    r = max(6, min(18, math.ceil(maxdev) + 2))
    lo, hi = 100 - r, 100 + r
    X = lambda v: mL + (v - lo) / (hi - lo) * pw
    Y = lambda v: mT + (1 - (v - lo) / (hi - lo)) * ph
    cx, cy = X(100), Y(100)
    qof = lambda rr, mm: ("Lider" if rr >= 100 and mm >= 100 else "Debilitandose" if rr >= 100
                          else "Mejorando" if mm >= 100 else "Rezagado")
    s = [f'<svg viewBox="0 0 {W} {H}">']
    quads = [(cx, mT, mL + pw - cx, cy - mT, "#2FD08A"),
             (cx, cy, mL + pw - cx, mT + ph - cy, "#F4B740"),
             (mL, cy, cx - mL, mT + ph - cy, "#F4607A"),
             (mL, mT, cx - mL, cy - mT, "#4CC2E0")]
    for x, y, w, h, c in quads:
        s.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{c}" opacity="0.06"/>')
    for i in range(9):
        vx = lo + (hi - lo) * i / 8
        s.append(f'<line x1="{X(vx):.1f}" y1="{mT}" x2="{X(vx):.1f}" y2="{mT+ph}" stroke="#1E2A3D"/>')
    for i in range(7):
        vy = lo + (hi - lo) * i / 6
        s.append(f'<line x1="{mL}" y1="{Y(vy):.1f}" x2="{mL+pw}" y2="{Y(vy):.1f}" stroke="#1E2A3D"/>')
    s.append(f'<line x1="{cx:.1f}" y1="{mT}" x2="{cx:.1f}" y2="{mT+ph}" stroke="#2A3A52" stroke-width="1.5"/>')
    s.append(f'<line x1="{mL}" y1="{cy:.1f}" x2="{mL+pw}" y2="{cy:.1f}" stroke="#2A3A52" stroke-width="1.5"/>')
    corners = [(mL+pw-8, mT+17, "LIDER", "end", "#2FD08A"),
               (mL+pw-8, mT+ph-8, "DEBILITANDOSE", "end", "#F4B740"),
               (mL+8, mT+ph-8, "REZAGADO", "start", "#F4607A"),
               (mL+8, mT+17, "MEJORANDO", "start", "#4CC2E0")]
    for x, y, t, a, c in corners:
        s.append(f'<text x="{x}" y="{y}" fill="{c}" font-size="13" font-family="ui-monospace,monospace" '
                 f'text-anchor="{a}" opacity="0.7" letter-spacing="1">{t}</text>')
    s.append(f'<text x="{mL+pw/2:.0f}" y="{H-14}" fill="#5E708A" font-size="11" text-anchor="middle" '
             f'font-family="ui-monospace,monospace">RS-Ratio - fuerza relativa -></text>')
    s.append(f'<text x="16" y="{mT+ph/2:.0f}" fill="#5E708A" font-size="11" text-anchor="middle" '
             f'font-family="ui-monospace,monospace" transform="rotate(-90 16 {mT+ph/2:.0f})">RS-Momentum - impulso -></text>')
    labels = []
    for sym, d in rrg.items():
        col = QUAD[d["quad"]][1]
        tail = d["tail"]
        tdates = d.get("tail_dates", [""] * len(tail))
        nm = NAMES.get(sym, (sym, sym, ""))[1]
        # estela: linea con degradado + un PUNTO por semana (con fecha al pasar el raton)
        for i in range(1, len(tail)):
            a, b = tail[i-1], tail[i]
            op = 0.10 + 0.6 * (i / max(1, len(tail)-1))
            s.append(f'<line x1="{X(a[0]):.1f}" y1="{Y(a[1]):.1f}" x2="{X(b[0]):.1f}" y2="{Y(b[1]):.1f}" '
                     f'stroke="{col}" stroke-width="1.6" stroke-opacity="{op:.2f}" stroke-linecap="round"/>')
        for i in range(len(tail) - 1):   # semanas anteriores (no la actual)
            rr, mm = tail[i]
            op = 0.25 + 0.5 * (i / max(1, len(tail)-1))
            wk = tdates[i] if i < len(tdates) else ""
            info = f"{sym} · semana {wk} · {qof(rr, mm)} (fuerza {rr:.0f}, impulso {mm:.0f})"
            s.append(f'<circle cx="{X(rr):.1f}" cy="{Y(mm):.1f}" r="3" fill="{col}" fill-opacity="{op:.2f}" '
                     f'stroke="#0A0E17" stroke-width="0.5"/>'
                     f'<circle cx="{X(rr):.1f}" cy="{Y(mm):.1f}" r="9" fill="transparent" class="tdot" '
                     f'data-t="{esc(info)}" style="cursor:pointer"><title>{esc(info)}</title></circle>')
        lx, ly = X(d["ratio"]), Y(d["mom"])
        labels.append((sym, lx, ly, col, nm, d, tail))
    # anillos de FLUJO (verde = entra dinero / acumulacion; doble rojo = cuidado, distribucion oculta)
    def _rad(sym):
        if quality is not None and sym in quality:
            q = max(-1.0, min(8.0, quality[sym]))
            return 4.0 + (q + 1.0) / 9.0 * 7.0
        return 6.5
    for sym, lx, ly, col, nm, d, tail in labels:
        f = flow.get(sym, {})
        dv = f.get("diverg")
        lab = f.get("label")
        rr = _rad(sym)
        if dv == "distribucion oculta":
            s.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="{rr+3:.1f}" fill="none" stroke="#F4607A" stroke-width="1.4"/>')
            s.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="{rr+5.5:.1f}" fill="none" stroke="#F4607A" stroke-width="1.4" stroke-opacity="0.55"/>')
        elif dv == "acumulacion oculta":
            s.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="{rr+3:.1f}" fill="none" stroke="#2FD08A" stroke-width="1.6"/>')
        elif lab == "Acumulacion" and f.get("cmf", 0) > 0:
            s.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="{rr+3:.1f}" fill="none" stroke="#2FD08A" stroke-width="1.1" stroke-opacity="0.45"/>')
        elif lab == "Distribucion" and f.get("cmf", 0) < 0:
            s.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="{rr+3:.1f}" fill="none" stroke="#F4607A" stroke-width="1.1" stroke-opacity="0.45"/>')
        # anillo DISCONTINUO del clima (ultimas 3 sesiones): 🟡 ambar = climax de subida (vela anomala que ya ve
        # todo el mundo, posible agotamiento) · 🟣 violeta = capitulacion (panico de un dia; el cazador vigila).
        # La opacidad baja con la antiguedad: hoy 1.0 · ayer 0.7 · hace 2d 0.45
        cl = f.get("clima")
        if cl:
            _op = {0: 1.0, 1: 0.7, 2: 0.45}.get(f.get("clima_hace") or 0, 0.45)
            _ccl = "#F4B740" if cl == "climax" else "#B980FF"
            s.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="{rr+8:.1f}" fill="none" stroke="{_ccl}" stroke-width="1.6" stroke-opacity="{_op}" stroke-dasharray="3.5,2.6"/>')
    # flecha de direccion + punto actual (en TODOS, brillante y encima)
    for sym, lx, ly, col, nm, d, tail in labels:
        if len(tail) >= 2:
            ax, ay = X(tail[-2][0]), Y(tail[-2][1])
            ang = math.atan2(ly - ay, lx - ax)
            if abs(lx - ax) > 0.3 or abs(ly - ay) > 0.3:
                tip = (lx + 13 * math.cos(ang), ly + 13 * math.sin(ang))
                b1 = (lx + 4 * math.cos(ang + 2.6), ly + 4 * math.sin(ang + 2.6))
                b2 = (lx + 4 * math.cos(ang - 2.6), ly + 4 * math.sin(ang - 2.6))
                s.append(f'<polygon points="{tip[0]:.1f},{tip[1]:.1f} {b1[0]:.1f},{b1[1]:.1f} {b2[0]:.1f},{b2[1]:.1f}" '
                         f'fill="{col}"/>')
        rel = d.get("rel4", 0)
        # precio de las ultimas 8 semanas, para ver si el precio acompana a la estela
        p8 = ""
        try:
            _s = df[sym].dropna()
            if len(_s) >= 9:
                _c = (float(_s.iloc[-1]) / float(_s.iloc[-9]) - 1) * 100
                _a = "↑ sube" if _c > 2 else "↓ baja" if _c < -2 else "→ plano"
                p8 = f" | precio 8s: {_a} {_c:+.1f}%"
        except Exception:
            pass
        f = flow.get(sym, {})
        fl = ""
        if f.get("diverg") == "distribucion oculta":
            fl = " | ⚠ distribucion oculta (cuidado)"
        elif f.get("diverg") == "acumulacion oculta":
            fl = " | entra dinero (acumulacion oculta)"
        else:
            _c = f.get("cmf")
            if _c is not None:
                _w = "entra dinero" if _c > 0.05 else "sale dinero" if _c < -0.05 else "plano"
                fl = f" | flujo: {_w} (CMF {_c:+.2f})"
        info = (f"{sym} · {nm} — {QUAD[d['quad']][0]} | fuerza {d['ratio']:.1f}, "
                f"impulso {d['mom']:.1f} | vs indice 4s {rel:+.1f}%{p8}{fl}")
        if quality is not None and sym in quality:
            rad = _rad(sym)
        else:
            rad = 6.5
        s.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="{rad:.1f}" fill="{col}" stroke="#0A0E17" stroke-width="1.8" '
                 f'class="tdot" data-t="{esc(info)}" style="cursor:pointer"><title>{esc(info)}</title></circle>')
    # etiquetas: columna a cada lado + linea guia desde la bola a su nombre (sin ambiguedad)
    GAP = 14
    rightballs = sorted([l for l in labels if l[1] >= cx], key=lambda p: p[2])   # bolas en mitad derecha -> nombre a la derecha
    leftballs = sorted([l for l in labels if l[1] < cx], key=lambda p: p[2])     # bolas en mitad izquierda -> nombre a la izquierda

    def place(group, side):
        if not group:
            return
        xs = [lx for _, lx, _, _, _, _, _ in group]
        if side == "right":
            colx = min(W - 6, max(xs) + 18); anchor = "start"
        else:
            colx = max(6, min(xs) - 18); anchor = "end"
        tys = [p[2] for p in group]                  # deseado = altura de su bola
        for i in range(1, len(tys)):                 # separar hacia abajo
            if tys[i] - tys[i-1] < GAP:
                tys[i] = tys[i-1] + GAP
        over = tys[-1] - (mT + ph - 4)               # si se sale por abajo, subir todo
        if over > 0:
            tys = [t - over for t in tys]
        if tys[0] < mT + 10:                          # si se sale por arriba, bajar todo
            sh = (mT + 10) - tys[0]
            tys = [t + sh for t in tys]
        anchorx = colx - 2 if side == "right" else colx + 2
        for (sym, lx, ly, col, nm, d, tail), ty in zip(group, tys):
            s.append(f'<line x1="{lx:.1f}" y1="{ly:.1f}" x2="{anchorx:.1f}" y2="{ty-3:.1f}" '
                     f'stroke="{col}" stroke-width="0.7" stroke-opacity="0.55"/>')
            info = f"{sym} · {nm}"
            s.append(f'<text x="{colx:.1f}" y="{ty:.1f}" fill="#E6EDF6" font-size="11.5" text-anchor="{anchor}" '
                     f'font-family="ui-monospace,monospace" font-weight="600" class="tdot" data-t="{esc(info)}" '
                     f'style="cursor:pointer"><title>{esc(info)}</title>{sym}</text>')
    place(rightballs, "right")
    place(leftballs, "left")
    s.append("</svg>")
    return "".join(s)

def quadrant_grid(rrg):
    """Vista alternativa: cuatro cajas con los ETFs de cada cuadrante (sin solapes)."""
    order = ["leading", "weakening", "improving", "lagging"]
    titles = {"leading": "LIDER", "weakening": "DEBILITANDOSE", "improving": "MEJORANDO", "lagging": "REZAGADO"}
    buckets = {q: [] for q in order}
    for sym, d in rrg.items():
        buckets[d["quad"]].append((sym, d["mom"], d["ratio"]))
    for q in buckets:
        buckets[q].sort(key=lambda x: -x[1])
    cells = ""
    for q in order:
        col = QUAD[q][1]
        chips = ""
        for sym, mom, ratio in buckets[q]:
            nm = NAMES.get(sym, (sym, sym, ""))[1]
            chips += (f"<span class='qchip' style='border-color:{col}33' title='{esc(sym)} · {esc(nm)}'>"
                      f"<b style='color:{col}'>{sym}</b> <i>{ratio:.0f}/{mom:.0f}</i></span>")
        if not chips:
            chips = "<span class='qempty'>—</span>"
        cells += (f"<div class='qcell' style='border-top:2px solid {col}'>"
                  f"<div class='qhead' style='color:{col}'>{titles[q]} <span>{QUAD[q][2]}</span></div>"
                  f"<div class='qchips'>{chips}</div></div>")
    return f"<div class='qgrid'>{cells}</div>"

def esc(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _pm(v):
    if v is None:
        return "n/d"
    return f"{'+' if v >= 0 else ''}{v}%"

def equity_svg(dates, eq_s, eq_b):
    W, H = 900, 250
    mL, mR, mT, mB = 50, 16, 16, 28
    pw, ph = W - mL - mR, H - mT - mB
    allv = eq_s + eq_b
    lo, hi = min(allv), max(allv)
    rng = (hi - lo) or 1e-9
    n = len(eq_s)
    X = lambda i: mL + pw * i / max(1, n - 1)
    Y = lambda v: mT + ph * (1 - (v - lo) / rng)
    def poly(arr, col, w):
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(arr))
        return f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round"/>'
    grid = []
    for g in range(5):
        v = lo + rng * g / 4
        y = Y(v)
        grid.append(f'<line x1="{mL}" y1="{y:.1f}" x2="{mL+pw}" y2="{y:.1f}" stroke="#1E2A3D"/>'
                    f'<text x="{mL-6}" y="{y+3:.1f}" fill="#5E708A" font-size="10" text-anchor="end" '
                    f'font-family="ui-monospace,monospace">{v:.2f}x</text>')
    return (f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto">'
            + "".join(grid) + poly(eq_b, "#93A4BC", 1.6) + poly(eq_s, "#5B8CFF", 2.2)
            + f'<text x="{mL+pw}" y="{mT+10}" fill="#5B8CFF" font-size="11" text-anchor="end" '
              f'font-family="ui-monospace,monospace">Estrategia</text>'
            + f'<text x="{mL+pw}" y="{mT+24}" fill="#93A4BC" font-size="11" text-anchor="end" '
              f'font-family="ui-monospace,monospace">Comprar y mantener {BENCH}</text>'
            + "</svg>")

def fresh_stocks(leaders, etf, n=2, max_hi=90):
    """Acciones de un ETF que ACELERAN (su RS de 3m sube) y NO estan en maximos (no extendidas).
    Devuelve hasta n, priorizando mayor aceleracion. Si ninguna pasa el tope, lo relaja para
    dar siempre 'las que mas aceleran y menos estiradas' (excluye las pegadas a maximos como MLI)."""
    if not leaders or etf not in leaders:
        return []
    rows = leaders[etf]
    def pick(mh, minrs):
        c = [r for r in rows if r.get("drs") is not None and r["drs"] > 0
             and r.get("hi", 100) < mh and r.get("rs", 0) >= minrs]
        c.sort(key=lambda r: -r["drs"])
        return c
    c = pick(max_hi, 45) or pick(95, 35) or pick(100, 30)
    return c[:n]


def compute_watchlist(tickers):
    """Para cada accion vigilada: descarga OHLCV, calcula FASE + FLUJO (OBV/CMF/distribucion) y un ESTADO
    que detecta cuando una hundida empieza a ACUMULAR (dinero entrando) antes de la siguiente subida."""
    if not tickers:
        return None
    try:
        data = yf.download(tickers, period="2y", interval="1d", progress=False,
                           group_by="ticker", auto_adjust=True, threads=True)
    except Exception:
        data = None
    daily, closes = {}, {}
    if data is not None:
        for t in tickers:
            try:
                d = data if len(tickers) == 1 else data[t]
                d = d.dropna(subset=["Close"])
                if len(d) >= 40:
                    daily[t] = d
                    closes[t] = d["Close"]
            except Exception:
                continue
    flow = compute_volume_flow(daily) if daily else {}
    out = []
    for t in tickers:
        if t not in closes:
            out.append({"sym": t, "name": WATCH_NAMES.get(t, t), "ok": False})
            continue
        s = closes[t].dropna()
        price = float(s.iloc[-1])
        win = s.iloc[-252:]
        mx, mn = float(win.max()), float(win.min())
        hi52 = round(price / mx * 100) if mx else 0           # % del maximo de 52s
        frm_lo = round((price / mn - 1) * 100) if mn else 0    # % por encima del minimo de 52s
        n3 = min(63, len(s) - 1)
        mom3 = round((price / float(s.iloc[-1 - n3]) - 1) * 100, 1)
        f = flow.get(t, {})
        ph = _phase(s, None)
        diverg = f.get("diverg")
        entrando = bool(f.get("obv_cross") or (diverg == "acumulacion oculta") or (f.get("cmf_pos") and f.get("obv_above")))
        if diverg == "distribucion oculta" or ph == "distrib":
            estado, ecol = "🟠 distribución — ojo, el dinero sale", "#F4B740"
        elif ph == "sube":
            estado, ecol = "🟢 subiendo — ya arrancó", "#2FD08A"
        elif entrando and ph in ("base", "lateral", "baja"):
            estado, ecol = "🟢 empezando a acumular — el dinero entra", "#2FD08A"
        elif ph == "baja":
            estado, ecol = "🔴 aún cayendo — cuchillo, no toques", "#F4607A"
        elif ph in ("base", "lateral"):
            estado, ecol = "🟦 en base, sin flujo — acumulando callado, espera", "#5AA9E6"
        else:
            estado, ecol = "⚪ sin señal clara", "#9FB0C8"
        out.append({"sym": t, "name": WATCH_NAMES.get(t, t), "ok": True, "price": price,
                    "phase": ph, "hi52": hi52, "frm_lo": frm_lo, "mom3": mom3,
                    "cmf": f.get("cmf"), "obv_above": f.get("obv_above"), "obv_cross": f.get("obv_cross"),
                    "diverg": diverg, "entrando": entrando, "estado": estado, "ecol": ecol})
    return out


CICLO_FASES = [
    ("recuperacion", "Recuperación", "Inicio de ciclo", "#2FD08A",
     ["XLF", "KRE", "XLY", "XRT", "XLI", "XLRE", "IWM", "XBI", "JETS"],
     "Sale de recesión: bajan tipos, curva empinada. Lideran financieras, consumo discrecional, industriales y small caps."),
    ("expansion", "Expansión", "Mitad de ciclo", "#4CC2E0",
     ["XLK", "SMH", "IGV", "XLI", "XLC", "CIBR", "SKYY"],
     "Crecimiento sólido y sostenido. Lideran tecnología, industriales y comunicaciones."),
    ("sobrecalentamiento", "Sobrecalentamiento", "Final de ciclo", "#F4B740",
     ["XLE", "XLB", "XOP", "COPX", "XME", "GLD", "XLP"],
     "Economía recalentada, inflación subiendo, la Fed sube tipos. Lideran energía, materiales y materias primas."),
    ("recesion", "Recesión", "Contracción", "#F4607A",
     ["XLU", "XLP", "XLV", "TLT", "GLD"],
     "Contracción. Refugio en defensivos: utilities, consumo básico, salud y bonos."),
]


def compute_cycle_phase(rrg, scores):
    """Deduce en que fase del ciclo economico estamos segun que sectores tienen el dinero (Lider/Mejorando en el RRG).
    Mapa orientativo basado en el modelo de rotacion sectorial (Fidelity/Stovall), no una prediccion."""
    fases = []
    for key, lbl, sub, col, secs, desc in CICLO_FASES:
        lit, tot = [], 0
        for s in secs:
            d = rrg.get(s)
            if d is None:
                continue
            tot += 1
            if d.get("quad") in ("leading", "improving"):
                lit.append(s)
        ratio = (len(lit) / tot) if tot else 0.0
        fases.append({"key": key, "lbl": lbl, "sub": sub, "col": col, "desc": desc,
                      "secs": secs, "lit": lit, "ratio": ratio, "n": len(lit), "tot": tot})
    cur = max(fases, key=lambda x: (x["ratio"], x["n"])) if fases else None
    return {"fases": fases, "actual": cur}


def cycle_clock_html(cyc):
    """Dibuja un reloj del ciclo economico (4 cuadrantes) con la aguja en la fase actual."""
    import math
    if not cyc or not cyc.get("actual"):
        return ""
    fases, cur = cyc["fases"], cyc["actual"]
    by_key = {f["key"]: f for f in fases}
    order = ["recuperacion", "expansion", "sobrecalentamiento", "recesion"]
    cx, cy, R = 150, 150, 95
    def pt(r, ang):
        a = math.radians(ang)
        return (cx + r * math.sin(a), cy - r * math.cos(a))
    wedges, labels = "", ""
    cur_idx = order.index(cur["key"]) if cur["key"] in order else 0
    for i, key in enumerate(order):
        f = by_key[key]
        active = (key == cur["key"])
        x0, y0 = pt(R, i * 90)
        x1, y1 = pt(R, i * 90 + 90)
        fill = f["col"] if active else f["col"] + "26"
        wedges += (f"<path d='M{cx},{cy} L{x0:.1f},{y0:.1f} A{R},{R} 0 0 1 {x1:.1f},{y1:.1f} Z' "
                   f"fill='{fill}' stroke='#0b0f17' stroke-width='2'/>")
        lx, ly = pt(R + 24, i * 90 + 45)
        labels += (f"<text x='{lx:.0f}' y='{ly:.0f}' fill='{f['col'] if active else '#9FB0C8'}' font-size='11' "
                   f"font-weight='{700 if active else 500}' text-anchor='middle'>{f['lbl']}</text>"
                   f"<text x='{lx:.0f}' y='{ly+13:.0f}' fill='#5E708A' font-size='8.5' text-anchor='middle'>{f['n']}/{f['tot']} con dinero</text>")
    nx, ny = pt(R - 16, cur_idx * 90 + 45)
    needle = (f"<line x1='{cx}' y1='{cy}' x2='{nx:.1f}' y2='{ny:.1f}' stroke='{cur['col']}' stroke-width='3.5' stroke-linecap='round'/>"
              f"<circle cx='{cx}' cy='{cy}' r='6' fill='{cur['col']}'/>")
    return ("<svg viewBox='0 0 300 300' style='width:100%;max-width:280px;display:block;margin:4px auto 0'>"
            + wedges + needle + labels + "</svg>")


def compute_suelo(df, rrg, scores, flow, meanrev):
    """DURMIENTES: sectores machacados y OLVIDADOS (el silencio pesa doble) cuyo impulso empieza
    a girar mientras el precio apenas se ha movido — la anticipacion de la subida, tu caso China.
    Ingredientes 0-10: castigo + SILENCIO (volumen bajisimo, nadie habla de el) + semanas dormido
    + estructura 0/3 + GIRO (verticalidad del impulso) + precio aun quieto + flujo despertando.
    OJO: condiciones de suelo, no el suelo — y sin flujo que deje de sangrar, no hay trato."""
    if not rrg or not flow:
        return None
    _n3 = {}
    for r in (scores or []):
        _n3[r["sym"]] = sum(1 for _, v in r["parts"][:3] if v)
    rows = []
    for s, d in rrg.items():
        if s == BENCH or s in SINTETICOS:
            continue
        if not (d["quad"] == "lagging" or (d["ratio"] <= 97.5 and d["mom"] <= 101)):
            continue
        pts, det = 0, []
        # --- 1) CASTIGO (max 3) ---
        hi52 = None
        if s in df.columns:
            ser = df[s].dropna()
            if len(ser) >= 20:
                hi52 = float(ser.iloc[-1] / ser.iloc[-min(52, len(ser)):].max() * 100)
        if hi52 is not None:
            if hi52 <= 70:
                pts += 2; det.append(f"−{100 - hi52:.0f}% de su máx 52s (paliza)")
            elif hi52 <= 82:
                pts += 1; det.append(f"−{100 - hi52:.0f}% de su máx 52s")
        mg = ((meanrev or {}).get(s) or {}).get("margen")
        if mg is not None and mg >= 12:
            pts += 1; det.append(f"{mg:.0f} pts bajo su media histórica")
        # --- 2) SILENCIO (max 4, POTENCIADO: el ingrediente que pediste subir) ---
        f = flow.get(s, {}) or {}
        vr = f.get("vol_rel5", f.get("vol_rel"))
        sil = 0
        if vr is not None:
            if vr < 0.80:
                sil = 3; det.append(f"volumen {vr:.2f}× — nadie habla de él")
            elif vr < 0.95:
                sil = 2; det.append(f"volumen {vr:.2f}× (poca atención)")
            elif vr < 1.10:
                sil = 1; det.append(f"volumen {vr:.2f}×")
        pts += sil
        wk_lag = 0
        for rr, mm in zip(reversed(d.get("ratio_series") or []), reversed(d.get("mom_series") or [])):
            if rr is None or mm is None or rr != rr or mm != mm:
                break
            if quad_of(rr, mm) == "lagging":
                wk_lag += 1
            else:
                break
        if wk_lag >= 8:
            pts += 1; det.append(f"{wk_lag} semanas dormido en Rezagado")
        # --- 3) ESTRUCTURA 0/3 (max 2) ---
        n3 = _n3.get(s)
        if n3 == 0:
            pts += 2; det.append("0/3 estructurales (64-65% hist. a 4 sem)")
        elif n3 == 1:
            pts += 1; det.append("1/3 estructurales")
        # --- 4) GIRO: la estela se pone vertical (max 3) ---
        tail = d.get("tail") or []
        dmom, vert = None, None
        if len(tail) >= 4:
            r_now, m_now = tail[-1]
            r_prev, m_prev = tail[-4]
            dmom = m_now - m_prev
            vert = dmom / max(0.6, abs(r_now - r_prev)) if dmom is not None else None
            if dmom >= 1.5 and (vert or 0) >= 1.8:
                pts += 2; det.append(f"GIRO VERTICAL {vert:.1f}× (impulso +{dmom:.1f} en 3s)")
            elif dmom >= 1.5:
                pts += 1; det.append(f"impulso girando (+{dmom:.1f} en 3s)")
        # --- 5) PRECIO AUN QUIETO: gira el impulso pero el precio apenas se ha movido (tu China) ---
        quieto = None
        if s in df.columns:
            ser = df[s].dropna()
            if len(ser) >= 5:
                quieto = float(ser.iloc[-1] / ser.iloc[-5] - 1) * 100
                if dmom is not None and dmom >= 1.5 and abs(quieto) <= 2.5:
                    pts += 1; det.append(f"precio aún quieto ({quieto:+.1f}% en 4s): anticipación")
        # --- 6) FLUJO: deja de sangrar o ya entra (max 2) ---
        cmf = f.get("cmf")
        if cmf is not None:
            if cmf > 0.05:
                pts += 2; det.append("CMF>+0.05: el dinero ya ENTRA")
            elif cmf >= -0.05:
                pts += 1; det.append("CMF plano: dejó de salir")
        # --- 7) PATRÓN PRE-DESPERTAR (la base del sistema: el suelo de oro/BTC/mineras) — 4 huellas
        #     de acumulación institucional ANTES del giro visible: divergencia CMF positiva, OBV con
        #     mínimos crecientes, compresión de volatilidad (muelle cargado) y base de mínimos
        #     crecientes en el precio. 3+ de 4 con el precio aún quieto = el patrón casi completo. ---
        pre, pdet = 0, []
        if f.get("diverg") == "acumulacion oculta":
            pre += 1; pdet.append("precio baja pero el dinero ENTRA (acumulación oculta)")
        osp = [x for x in (f.get("obv_spark") or []) if x is not None and x == x]
        if len(osp) >= 24:
            _t = len(osp) // 3
            if min(osp[-_t:]) > min(osp[:_t]):
                pre += 1; pdet.append("OBV con mínimos crecientes (compran las caídas)")
        if s in df.columns:
            _ser = df[s].dropna()
            _ret = _ser.pct_change().dropna()
            if len(_ret) >= 40:
                _v8 = _ret.rolling(8).std().dropna()
                if len(_v8) >= 20 and float((_v8 <= _v8.iloc[-1]).mean()) <= 0.30:
                    pre += 1; pdet.append("volatilidad comprimida: muelle cargado")
            if len(_ser) >= 16:
                _mn = float(_ser.iloc[-4:].min()); _m8 = float(_ser.iloc[-12:-8].min()); _m12 = float(_ser.iloc[-16:-12].min())
                if _mn > _m8 and _mn > _m12:
                    pre += 1; pdet.append("mínimos crecientes: base construyéndose")
        if pre >= 3:
            pts += 1                     # patrón casi completo: suma al score (el tope /10 se mantiene)
        det.extend(pdet)
        sangra = (cmf is not None and cmf < -0.05)
        despertando = bool((dmom or 0) >= 1.5 and not sangra and pts >= 6)
        # FASE del ciclo del durmiente — la secuencia que buscamos replicar de oro/BTC/mineras:
        # DORMIDO → ACUMULACIÓN (entra dinero en silencio) → PRE-DESPERTAR (3-4 huellas, precio aún
        # quieto: la ventana de entrada temprana) → DESPERTANDO (giro vertical: la ventana se cierra).
        # SANGRA anula todo: sin flujo que deje de salir, no hay trato.
        if sangra:
            fase = "SANGRA"
        elif despertando:
            fase = "DESPERTANDO"
        elif pre >= 3:
            fase = "PRE-DESPERTAR"
        elif pre >= 2 or (cmf is not None and cmf > 0.05):
            fase = "ACUMULACION"
        else:
            fase = "DORMIDO"
        rows.append({"sym": s, "pts": min(pts, 10), "det": det, "hi52": hi52, "vr": vr, "sil": sil,
                     "wk_lag": wk_lag, "n3": n3, "cmf": cmf, "dmom": dmom,
                     "vert": (round(vert, 1) if vert is not None else None),
                     "quieto": (round(quieto, 1) if quieto is not None else None),
                     "sangra": sangra, "despertando": despertando, "pre": pre, "fase": fase})
    rows.sort(key=lambda r: (-int(r["despertando"]), -int(r["fase"] == "PRE-DESPERTAR"), -r["pre"], -r["pts"],
                             (r["hi52"] if r["hi52"] is not None else 999)))
    return [r for r in rows if r["pts"] >= 5 or r["pre"] >= 3][:14] or None


DESPERTARES_FILE = os.path.join(SEGUIMIENTO_DIR, "despertares.json")
DESPERTARES_BAK = os.path.join(SEGUIMIENTO_DIR, "despertares.bak.json")


def _sello_macro(df, rrg, flow, cascada=None):
    """Foto del CONTEXTO MACRO en el momento de abrir una ficha. Se guarda con la ficha para que,
    dentro de unos meses, el libro pueda responder solo: "los despertares de mineras funcionaron el
    X% con el dolar cayendo y el Y% con el dolar subiendo". Sin esto, esa pregunta no se puede
    responder nunca — y es justo la que decide si el semaforo macro aporta algo o es ruido."""
    m = {}
    try:
        # DOLAR (UUP): viento en contra de materias primas y emergentes cuando sube
        if rrg and "UUP" in rrg:
            d = rrg["UUP"]
            sube = d["quad"] in ("leading", "improving")
            m["usd"] = "sube" if sube else "baja"
            m["usd_ratio"] = round(float(d["ratio"]), 1)
        cu = (flow or {}).get("UUP", {}).get("cmf")
        if cu is not None:
            m["usd_cmf"] = cu
    except Exception:
        pass
    try:
        # CHINA (FXI/KWEB): comprador marginal de cobre y metales
        qs, cs = [], []
        for s in ("FXI", "KWEB"):
            if rrg and s in rrg:
                qs.append(rrg[s]["quad"] in ("leading", "improving"))
            c = (flow or {}).get(s, {}).get("cmf")
            if c is not None:
                cs.append(c)
        if qs:
            m["china"] = "fuerte" if sum(qs) >= max(1, len(qs) - 0) else ("mixta" if any(qs) else "floja")
        if cs:
            m["china_cmf"] = round(sum(cs) / len(cs), 3)
    except Exception:
        pass
    try:
        if cascada and cascada.get("lider"):
            m["eslabon"] = cascada["lider"]
            m["cascada"] = cascada.get("sentido")
    except Exception:
        pass
    return m or None



# ======================================================================
# LIBRO DE DESPERTARES — APUESTAS INDEPENDIENTES  (v4.5)
#
# EL PROBLEMA QUE RESUELVE, con el ejemplo real que lo destapo:
#   En agosto de 2026 el libro tenia 9 despertares y una media de +8.1%.
#   Parece una muestra de 9. No lo es: SIL, GDX, SLV, GLD y XME son CINCO
#   FORMAS DE LA MISMA APUESTA (metales preciosos y mineras). Si el oro se
#   gira, caen los cinco a la vez. La muestra real eran ~5 apuestas, y una
#   sola de ellas se llevaba casi todo el resultado.
#
#   Contar filas en vez de apuestas infla la N, estrecha el intervalo de
#   Wilson y te hace creer que sabes algo que todavia no sabes. Con vistas a
#   VENDER esto, es la diferencia entre un track record honesto y uno que
#   se cae en cuanto alguien lo mire de cerca.
#
# QUE HACE: agrupa los despertares cerrados por FAMILIA, calcula el resultado
# de cada familia (media de sus miembros, porque se mueven juntos) y recalcula
# Wilson sobre el numero de FAMILIAS, no de filas. El intervalo sale mucho mas
# ancho. Ese ancho es la verdad.
# ======================================================================
FAMILIAS = {
    "metales preciosos": ["GLD", "SLV", "GDX", "SIL", "XME"],
    "cobre / industrial": ["COPX", "XLB", "MOO"],
    "energia nuclear":    ["URA"],
    "energia limpia":     ["TAN", "LIT", "ICLN", "FAN", "HYDR", "DRIV"],
    "software / nube":    ["IGV", "SKYY", "CIBR", "MAGS", "XLK"],
    "chips":              ["SMH", "SOXX"],
    "memoria / HBM":      ["DRAM"],
    "almacenamiento":     ["S-ALMACEN", "WDC", "STX", "SNDK"],
    "equipos semi":       ["CE-EQUIPOS", "ASML", "LRCX", "AMAT", "KLAC"],
    "neocloud / GPU":     ["NCLD"],
    "biotech / salud":    ["XBI", "XLV"],
    "espacio / defensa":  ["UFO", "ARKX", "ITA"],
    "innovacion / ARK":   ["ARKK", "ARKF", "BOTZ", "QTUM"],
    "cripto":             ["IBIT"],
    "china":              ["KWEB", "FXI"],
    "emergentes":         ["EWZ", "INDA", "EEM", "EWY"],
    "petroleo":           ["XLE", "XOP", "OIH"],
}
_FAM_DE = {t: f for f, lst in FAMILIAS.items() for t in lst}


def familia_de(sym):
    return _FAM_DE.get(sym) or EXPLOSIVO_TIPO.get(sym) or GRUPO.get(sym) or "otros"


def despertares_por_familia(cerradas):
    """Convierte una lista de despertares cerrados en APUESTAS independientes.
       Devuelve None si no hay nada cerrado todavia (no se inventa un resumen)."""
    try:
        if not cerradas:
            return None
        fams = {}
        for c in cerradas:
            f = familia_de(c.get("sym", ""))
            fams.setdefault(f, []).append(c)
        filas = []
        for f, lst in fams.items():
            rets = [c.get("ret") for c in lst if c.get("ret") is not None]
            if not rets:
                continue
            media = sum(rets) / len(rets)
            filas.append({"familia": f, "n_filas": len(lst),
                          "syms": sorted({c.get("sym", "") for c in lst}),
                          "ret": round(media, 1), "gana": media > 0})
        if not filas:
            return None
        filas.sort(key=lambda r: -r["ret"])
        n_fam = len(filas)
        n_filas = sum(r["n_filas"] for r in filas)
        gan = sum(1 for r in filas if r["gana"])
        p = gan / n_fam
        z = 1.96
        d = 1 + z * z / n_fam
        ctr = (p + z * z / (2 * n_fam)) / d
        rad = z * math.sqrt(max(0.0, p * (1 - p) / n_fam + z * z / (4 * n_fam * n_fam))) / d
        # concentracion: cuanto del resultado total se lo lleva la mejor familia
        tot = sum(abs(r["ret"]) for r in filas) or 1.0
        conc = round(100 * abs(filas[0]["ret"]) / tot)
        return {"filas": filas, "n_familias": n_fam, "n_filas": n_filas,
                "gan": gan, "p": int(round(100 * p)),
                "lo": int(round(100 * max(0.0, ctr - rad))),
                "hi": int(round(100 * min(1.0, ctr + rad))),
                "avg": round(sum(r["ret"] for r in filas) / n_fam, 1),
                "concentracion": conc, "top": filas[0]["familia"],
                "maduro": n_fam >= 12}
    except Exception as _dege:
        _deg("despertares_por_familia", _dege)
        return None


def update_despertares(suelo, daily, close_date, bench="SPY", macro=None):
    """LIBRO DE DESPERTARES — el registro de anticipación, fechado y falsable.

    Idea: cualquiera dice "compra uranio". Lo que nadie publica es "el dia X mi sistema marco URA
    con ESTAS huellas y ESTE nivel de invalidacion; aqui esta el resultado a 4 semanas, incluidos
    los fallos". Eso es lo unico que hace creible (y monetizable) el sistema.

    Se persiste SOLO la ficha (fecha, huellas, precio y nivel de invalidacion). El resultado se
    RECALCULA en cada build desde los precios reales: asi nunca hay un numero guardado que pueda
    quedar desfasado o maquillado. Una ficha por despertar (no se re-registra el mismo simbolo
    mientras siga viva), y se evalua sola a las 4 semanas gane o pierda.

    Devuelve {"activas": [...], "cadena": [...], "libro": {...}} o None."""
    if suelo is None and not os.path.exists(DESPERTARES_FILE):
        return None
    suelo = suelo or []
    os.makedirs(SEGUIMIENTO_DIR, exist_ok=True)
    recs = []
    for _f in (DESPERTARES_FILE, DESPERTARES_BAK):
        if os.path.exists(_f):
            try:
                with open(_f, "r", encoding="utf-8") as fh:
                    recs = json.load(fh)
                break
            except Exception:
                continue
    hoy = str(close_date)

    def _cierre(sym):
        d = (daily or {}).get(sym)
        if d is None or "Close" not in d.columns:
            return None
        s = d["Close"].dropna()
        return s if len(s) else None

    # --- 1) REGISTRAR las fichas nuevas de este cierre -------------------------------------
    # ANTI-DUPLICADO: no se abre ficha nueva si ese simbolo ya tuvo una en las ultimas 8 semanas
    # (viva o ya madurada). Sin esta ventana, al madurar la ficha el simbolo volvia a estar "libre"
    # y el sistema se auto-registraba otra vez cada build: el libro se llenaba de clones.
    FASES_FICHA = ("DESPERTANDO", "PRE-DESPERTAR")
    try:
        _corte = str((pd.Timestamp(hoy) - pd.Timedelta(days=56)).date())
    except Exception:
        _corte = ""
    vetados = {r["sym"] for r in recs if (not r.get("cerrada")) or (r.get("date") or "") >= _corte}
    for r in suelo:
        if r.get("fase") not in FASES_FICHA or r.get("sangra"):
            continue
        s = r["sym"]
        if s in vetados:                    # ficha viva o demasiado reciente: no se duplica
            continue
        px = _cierre(s)
        if px is None or len(px) < 30:
            continue
        px0 = float(px.iloc[-1])
        # NIVEL DE INVALIDACION: el minimo de las ultimas 20 sesiones CON UN 3% DE MARGEN. Sin ese
        # margen el nivel queda pegado al minimo (un durmiente cotiza cerca de sus minimos por
        # definicion) y cualquier ruido lo rompia: fichas que acababan +11% salian "invalidadas".
        # No es un stop de trading: es la condicion que FALSA la tesis, declarada antes del resultado.
        inval = round(float(px.iloc[-20:].min()) * 0.97, 2)
        recs.append({"date": hoy, "sym": s, "fase": r.get("fase"),
                     "pts": r.get("pts"), "pre": r.get("pre"),
                     "caida": (round(r["hi52"] - 100, 1) if r.get("hi52") is not None else None),
                     "cmf": r.get("cmf"), "sil": r.get("sil"), "vr": r.get("vr"),
                     "huellas": [h for h in (r.get("det") or [])][:4],
                     "px0": round(px0, 2), "inval": inval, "cerrada": False,
                     "macro": macro})
        vetados.add(s)
    # limite de tamano: 200 fichas mas recientes
    if len(recs) > 200:
        recs = sorted(recs, key=lambda r: r.get("date", ""))[-200:]

    # --- 2) EVALUAR (recalculado siempre desde precios reales) -----------------------------
    bpx = _cierre(bench)
    activas, cerradas = [], []
    for r in recs:
        px = _cierre(r["sym"])
        if px is None:
            continue
        try:
            f0 = pd.Timestamp(r["date"])
            post = px[px.index >= f0]
            if not len(post):
                continue
            n_ses = len(post) - 1
            px_now = float(post.iloc[-1])
            base = float(post.iloc[0])
            ret = (px_now / base - 1) * 100
            # ¿toco el nivel de invalidacion en algun momento?
            roto = bool(r.get("inval") and float(post.min()) <= float(r["inval"]))
            # rendimiento del indice en la MISMA ventana (misma pregunta, misma fecha)
            ret_b = None
            if bpx is not None:
                bp = bpx[bpx.index >= f0]
                if len(bp) > 1:
                    ret_b = (float(bp.iloc[-1]) / float(bp.iloc[0]) - 1) * 100
            # MADURA a las 4 semanas (20 sesiones): a partir de ahi el resultado queda fijado
            madura = n_ses >= 20
            if madura:
                fin = post.iloc[:21]
                ret4 = (float(fin.iloc[-1]) / base - 1) * 100
                ret4_b = None
                if bpx is not None:
                    bp = bpx[bpx.index >= f0].iloc[:21]
                    if len(bp) > 1:
                        ret4_b = (float(bp.iloc[-1]) / float(bp.iloc[0]) - 1) * 100
                roto4 = bool(r.get("inval") and float(fin.min()) <= float(r["inval"]))
                r["cerrada"] = True
                cerradas.append({**r, "ret": round(ret4, 1), "ret_b": (round(ret4_b, 1) if ret4_b is not None else None),
                                 "vs": (round(ret4 - ret4_b, 1) if ret4_b is not None else None),
                                 "roto": roto4, "gana": ret4 > 0, "n_ses": n_ses,
                                 "ret_hoy": round(ret, 1)})
            else:
                r["cerrada"] = False
                # ---- GESTIÓN DE LA POSICIÓN VIVA: el problema de "no devolver lo ganado pero no
                #      salir demasiado pronto". Se resuelve con un trailing ANCLADO AL MÁXIMO y
                #      medido en volatilidad del propio activo (chandelier exit):
                #        stop = máximo cierre desde la ficha − 3 × ATR(14)
                #      En un activo nervioso (mineras, IBIT) el ATR es grande → el stop va lejos y NO
                #      te echa en el primer susto. En uno tranquilo se ciñe. Un stop de "% fijo" hace
                #      justo lo contrario: te saca de lo volátil y deja correr las pérdidas de lo lento.
                gestion = None
                try:
                    dd_ = (daily or {}).get(r["sym"])
                    px_max = float(post.max())
                    g_pico = (px_max / base - 1) * 100
                    g_hoy = ret
                    atr = None
                    if dd_ is not None and {"High", "Low", "Close"}.issubset(dd_.columns):
                        w = dd_[dd_.index >= f0]
                        if len(w) >= 5:
                            hl = (w["High"] - w["Low"]).abs()
                            hc = (w["High"] - w["Close"].shift()).abs()
                            lc = (w["Low"] - w["Close"].shift()).abs()
                            tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
                            _a = float(tr.rolling(min(14, len(tr))).mean().iloc[-1])
                            atr = _a if _a > 0 else None
                    if atr is None:      # sin High/Low usable: ATR aproximado por desviación diaria
                        rr = post.pct_change().dropna()
                        if len(rr) >= 5:
                            atr = float(rr.std() * px_now * 1.4) or None
                    stop = round(px_max - 3 * atr, 2) if atr else None
                    margen = ((px_now / stop - 1) * 100) if stop and stop > 0 else None
                    # DEVOLUCIÓN: cuánto del beneficio máximo se ha ido ya. Es la métrica honesta de
                    # "estoy devolviendo lo ganado", y solo tiene sentido si llegó a haber ganancia.
                    devol = None
                    if g_pico > 1.0:
                        devol = round(100 * max(0.0, (g_pico - g_hoy)) / g_pico, 0)
                    if stop and px_now <= stop:
                        est, ecol = "TRAILING TOCADO — el sistema dice cerrar", "malo"
                    elif devol is not None and devol >= 50:
                        est, ecol = f"ya has devuelto el {devol:.0f}% de lo ganado — vigila de cerca", "aviso"
                    elif margen is not None and margen < 3:
                        est, ecol = "el trailing te pisa los talones", "aviso"
                    else:
                        est, ecol = "aguantar: la tendencia todavía paga", "bueno"
                    gestion = {"px_now": round(px_now, 2), "px_max": round(px_max, 2),
                               "g_pico": round(g_pico, 1), "g_hoy": round(g_hoy, 1),
                               "devol": devol, "atr": (round(atr, 2) if atr else None),
                               "stop": stop, "margen": (round(margen, 1) if margen is not None else None),
                               "estado": est, "nivel": ecol}
                except Exception:
                    gestion = None
                activas.append({**r, "ret": round(ret, 1), "ret_b": (round(ret_b, 1) if ret_b is not None else None),
                                "vs": (round(ret - ret_b, 1) if ret_b is not None else None),
                                "roto": roto, "n_ses": n_ses, "gestion": gestion,
                                "faltan": max(0, 20 - n_ses)})
        except Exception:
            continue
    try:
        with open(DESPERTARES_FILE, "w", encoding="utf-8") as fh:
            json.dump(recs, fh, ensure_ascii=False, indent=0)
        with open(DESPERTARES_BAK, "w", encoding="utf-8") as fh:
            json.dump(recs, fh, ensure_ascii=False, indent=0)
    except Exception:
        pass

    # --- 3) EL LIBRO: tasa base fuera de muestra, con los fallos dentro ---------------------
    libro = None
    n = len(cerradas)
    if n:
        gan = sum(1 for c in cerradas if c["gana"])
        p = gan / n
        zz = 1.96
        den = 1 + zz * zz / n
        ctr = (p + zz * zz / (2 * n)) / den
        rad = zz * math.sqrt(p * (1 - p) / n + zz * zz / (4 * n * n)) / den
        med = sorted(c["ret"] for c in cerradas)
        vs_ok = [c["vs"] for c in cerradas if c.get("vs") is not None]
        # DESGLOSE POR FASE: la pregunta central de tu tesis — ¿entrar en el giro (DESPERTANDO) rinde
        # mas que entrar antes (PRE-DESPERTAR)? Con el libro se puede RESPONDER en vez de opinar.
        porfase = {}
        for f in ("DESPERTANDO", "PRE-DESPERTAR"):
            sub = [c for c in cerradas if c.get("fase") == f]
            if sub:
                porfase[f] = {"n": len(sub),
                              "gan": sum(1 for c in sub if c["gana"]),
                              "p": int(round(100 * sum(1 for c in sub if c["gana"]) / len(sub))),
                              "avg": round(sum(c["ret"] for c in sub) / len(sub), 1)}
        # DESGLOSE POR DOLAR: ¿de verdad los despertares (sobre todo de mineras) funcionan mejor con
        # el dolar cayendo? Con el sello macro guardado en cada ficha, esto se RESPONDE en vez de
        # suponerse. Es la unica forma de saber si el semaforo macro aporta o es ruido.
        pordolar = {}
        for est in ("baja", "sube"):
            sub = [c for c in cerradas if (c.get("macro") or {}).get("usd") == est]
            if sub:
                pordolar[est] = {"n": len(sub),
                                 "gan": sum(1 for c in sub if c["gana"]),
                                 "p": int(round(100 * sum(1 for c in sub if c["gana"]) / len(sub))),
                                 "avg": round(sum(c["ret"] for c in sub) / len(sub), 1)}
        libro = {"n": n, "gan": gan, "p": int(round(100 * p)),
                 "lo": int(round(100 * (ctr - rad))), "hi": int(round(100 * (ctr + rad))),
                 "avg": round(sum(c["ret"] for c in cerradas) / n, 1),
                 "med": round(med[n // 2], 1),
                 "avg_vs": (round(sum(vs_ok) / len(vs_ok), 1) if vs_ok else None),
                 "rotas": sum(1 for c in cerradas if c.get("roto")),
                 "porfase": porfase, "pordolar": pordolar,
                 "maduro": n >= 20}
    # DESPERTANDO primero: es la fase del giro, la que Pedro quiere cazar. Luego por patron y fecha.
    activas.sort(key=lambda r: (0 if r.get("fase") == "DESPERTANDO" else 1,
                                -(r.get("pts") or 0), r.get("date") or ""))
    cerradas.sort(key=lambda r: (r.get("date") or ""), reverse=True)
    return {"activas": activas, "cadena": cerradas[:24], "libro": libro,
            "familias": despertares_por_familia(cerradas),
            "total": len(recs)}


def compute_giro_intradia(daily, rrg=None):
    """Huella del GIRO INTRADIA en la ultima vela diaria: gap de apertura fuerte que la sesion
    revierte. Gap arriba + cierre en el tercio bajo del rango = abrieron comprando y cerraron
    VENDIENDO (distribuyen aprovechando la liquidez del gap). Gap abajo + cierre arriba = compraron
    el miedo. Con velas diarias el aviso llega AL CIERRE, no en vivo: sirve para leer la manana
    siguiente, no para operar la sesion."""
    rows = []
    for sym, d in (daily or {}).items():
        try:
            if not {"Open", "High", "Low", "Close"}.issubset(d.columns):
                continue
            dd = d.dropna(subset=["Open", "High", "Low", "Close"])
            if len(dd) < 21:
                continue
            o, h, l, c = (float(dd["Open"].iloc[-1]), float(dd["High"].iloc[-1]),
                          float(dd["Low"].iloc[-1]), float(dd["Close"].iloc[-1]))
            pc = float(dd["Close"].iloc[-2])
            if min(o, h, l, c, pc) <= 0 or h <= l:
                continue
            gap = (o / pc - 1) * 100
            intra = (c / o - 1) * 100
            pos = (c - l) / (h - l)          # 0 = cierra en minimos · 1 = cierra en maximos
            vol_rel = None
            if "Volume" in dd.columns:
                v = dd["Volume"].astype(float)
                m = v.iloc[-21:-1].mean()
                if m and m > 0:
                    vol_rel = float(v.iloc[-1] / m)
            sig = None
            if gap >= 1.2 and (pos <= 0.35 or intra <= -1.0):
                sig = "bajista"              # vendieron la subida
            elif gap <= -1.2 and pos >= 0.65:
                sig = "alcista"              # compraron el miedo
            if sig:
                rows.append({"sym": sym, "sig": sig, "gap": round(gap, 1), "intra": round(intra, 1),
                             "pos": int(round(pos * 100)), "vol_rel": (round(vol_rel, 2) if vol_rel else None),
                             "fecha": str(dd.index[-1].date()),
                             "quad": ((rrg or {}).get(sym) or {}).get("quad")})
        except Exception:
            continue
    if not rows:
        return None
    rows.sort(key=lambda r: -abs(r["gap"]))
    # el patron de Pedro: venden lo CALIENTE (Lider/Debilitandose) y compran lo FRIO (Rezagado/Mejorando) el mismo dia
    rot_flag = (any(r["sig"] == "bajista" and r["quad"] in ("leading", "weakening") for r in rows)
                and any(r["sig"] == "alcista" and r["quad"] in ("lagging", "improving") for r in rows))
    return {"rows": rows[:10], "rotacion": rot_flag, "fecha": rows[0]["fecha"]}


def update_centinela_ledger(estado, close_date):
    """Historial del estado del CENTINELA por fecha de cierre (idempotente: re-ejecutar el mismo dia
    sobreescribe, no duplica). Sirve para la regla de confirmacion (un dia es ruido; el mismo estado
    en 2+ cierres consecutivos es regimen) y para pintar la linea de tiempo de cambios."""
    recs = []
    try:
        os.makedirs(SEGUIMIENTO_DIR, exist_ok=True)
        if os.path.exists(CENTINELA_FILE):
            with open(CENTINELA_FILE, "r", encoding="utf-8") as fh:
                recs = json.load(fh)
    except Exception as _dege:
        _deg("update_centinela_ledger:5413", _dege)
        recs = []
    d = str(close_date)
    recs = [r for r in recs if r.get("date") != d]
    recs.append({"date": d, "estado": estado})
    recs = sorted(recs, key=lambda r: r["date"])[-90:]
    try:
        with open(CENTINELA_FILE, "w", encoding="utf-8") as fh:
            json.dump(recs, fh, ensure_ascii=False, indent=0)
    except Exception:
        pass
    return recs


def compute_centinela(df, rrg, flow, suelo, dix=None, plan=None):
    """CENTINELA — el reloj de regimen que une todo el terminal en UNA decision operable.
    La tesis: el dinero se gana entrando pronto en ALTA BETA tras el suelo; los DEFENSIVOS se mueven
    tan poco que rotar hacia ellos no compensa con capital pequeno — son TERMOMETRO, no destino.
    Motor: spread = ratio RRG medio de (S-EXPLOSIVO, S-DUROS) menos (S-DEFENSA, S-REFUGIO), con su
    persistencia semanal (la regla de siempre: un dato es ruido, la racha es patron). Confirmadores:
    CMF agregado de los explosivos, credito (S-CREDITO), amplitud (S-AMPLITUD), durmientes en
    PRE-DESPERTAR/DESPERTANDO y DIX (dark pools) si esta disponible.
    Estados del ciclo: RISK-ON -> DISTRIBUCION (aviso) -> LIQUIDEZ -> ACECHO -> REENTRADA -> RISK-ON."""
    if not rrg:
        return None
    EXP, DEF = ["S-EXPLOSIVO", "S-DUROS"], ["S-DEFENSA", "S-REFUGIO"]
    exp_ok = [s for s in EXP if s in rrg]
    def_ok = [s for s in DEF if s in rrg]
    if not exp_ok or not def_ok:
        return None
    # --- serie del spread (semanal, alineada al indice del df) ---
    def _serie(keys):
        cols = []
        for k in keys:
            vals = rrg[k].get("ratio_series") or []
            cols.append(pd.Series([v if (v is not None and v == v) else float("nan") for v in vals]))
        return pd.concat(cols, axis=1).mean(axis=1) if cols else None
    se, sd = _serie(exp_ok), _serie(def_ok)
    spread_s = (se - sd).dropna()
    if len(spread_s) < 5:
        return None
    spread = float(spread_s.iloc[-1])
    d3 = float(spread_s.iloc[-1] - spread_s.iloc[-4]) if len(spread_s) >= 4 else 0.0
    # persistencia: semanas seguidas con el spread al mismo lado del cero, y semanas seguidas cayendo
    lado = 0
    for v in reversed(list(spread_s)):
        if (v > 0) == (spread > 0) and v != 0:
            lado += 1
        else:
            break
    cayendo = 0
    difs = spread_s.diff().dropna()
    for v in reversed(list(difs)):
        if v < 0:
            cayendo += 1
        else:
            break
    # --- confirmadores ---
    _cmfs = [flow[s]["cmf"] for s in SECTORES_EXPLOSIVOS if s in (flow or {}) and flow[s].get("cmf") is not None]
    cmf_beta = round(float(sum(_cmfs) / len(_cmfs)), 3) if _cmfs else None
    beta_pos = int(round(100 * sum(1 for c in _cmfs if c > 0) / len(_cmfs))) if _cmfs else None
    _q = lambda k: (rrg.get(k) or {}).get("quad")
    def_lidera = any(_q(k) in ("leading", "improving") for k in def_ok)
    exp_lidera = any(_q(k) == "leading" for k in exp_ok)
    credito_ok = _q("S-CREDITO") in ("leading", "improving") if "S-CREDITO" in rrg else None
    # el pulso de credito de verdad: HYG/TLT subiendo = apetito por riesgo intacto
    hyg_tlt = None
    if "HYG" in df.columns and "TLT" in df.columns:
        _r = (df["HYG"] / df["TLT"]).dropna()
        if len(_r) >= 5:
            hyg_tlt = round(float(_r.iloc[-1] / _r.iloc[-5] - 1) * 100, 1)
    amplitud_ok = _q("S-AMPLITUD") in ("leading", "improving") if "S-AMPLITUD" in rrg else None
    # durmientes explosivos por fase (el radar de anticipacion alimenta al reloj)
    _expl = [r for r in (suelo or []) if r["sym"] in SECTORES_EXPLOSIVOS]
    acecho_syms = [r["sym"] for r in _expl if r.get("fase") in ("PRE-DESPERTAR", "ACUMULACION")]
    despierta_syms = [r["sym"] for r in _expl if r.get("fase") == "DESPERTANDO"]
    dix_fuerte = bool(dix and dix.get("m5") is not None and dix["m5"] >= 45.5)
    dd_now = (plan or {}).get("dd")
    # --- maquina de estados (de arriba abajo: gana la primera que se cumple) ---
    if spread < 0 and despierta_syms and d3 > 0 and (cmf_beta is None or cmf_beta > -0.02):
        estado, col = "REENTRADA", "#2FD08A"
        que = ("El dinero VUELVE a la alta beta desde el suelo: durmientes explosivos DESPERTANDO ("
               + ", ".join(despierta_syms[:4]) + ") con el spread girando al alza. La ventana de entrada "
               "temprana que persigue todo el sistema. Desplegar liquidez POR TRAMOS en los que despiertan, "
               "solo con el cierre del viernes y flujo que no salga.")
        inval = ("Se invalida si el spread vuelve a caer 2 semanas seguidas, si el CMF agregado de los "
                 "explosivos vuelve a negativo claro (<−0.05) o si los que despertaban recaen a SANGRA.")
    elif spread >= CENTINELA_SPREAD_ON and d3 >= CENTINELA_CAIDA_3S and (beta_pos is None or beta_pos >= 45):
        estado, col = "RISK-ON", "#2FD08A"
        que = ("La alta beta lidera y el flujo acompaña: es el régimen de estar INVERTIDO en los líderes "
               "explosivos (los defensivos ni mirarlos). Gestionar posiciones con el ritmo semanal de siempre.")
        inval = (f"Se invalida si el spread cae más de {abs(CENTINELA_CAIDA_3S):.1f} pts en 3 semanas o si los "
                 "defensivos entran en Mejorando mientras el CMF de la beta alta se gira a negativo → pasar a DISTRIBUCIÓN.")
    elif spread >= 0 and (d3 <= CENTINELA_CAIDA_3S or (def_lidera and (cmf_beta or 0) < 0) or cayendo >= 2):
        estado, col = "DISTRIBUCION", "#F4B740"
        que = ("AVISO: la alta beta aún manda pero pierde fuelle" + (" y los defensivos mejoran" if def_lidera else "")
               + ((" con el dinero saliendo de los explosivos (CMF %.2f)" % cmf_beta) if (cmf_beta or 0) < 0 else "")
               + ". NO abrir posiciones nuevas de beta alta; subir stops; preparar la salida a LIQUIDEZ. "
               "Recuerda: los defensivos son el termómetro, NO el destino — con capital pequeño, rotar a lo que no se mueve no compensa.")
        inval = "Se invalida (vuelta a RISK-ON) si el spread recupera y el CMF agregado vuelve a positivo dos viernes seguidos."
    elif spread <= CENTINELA_SPREAD_OFF and lado >= 2:
        if len(acecho_syms) >= 2 or (dix_fuerte and (dd_now is None or dd_now <= -3)):
            estado, col = "ACECHO", "#4CC2E0"
            que = ("Régimen defensivo confirmado PERO el suelo se está armando en silencio: "
                   + (f"{len(acecho_syms)} explosivo(s) en acumulación/pre-despertar ({', '.join(acecho_syms[:5])})" if acecho_syms else "")
                   + (" y el DIX marca acumulación oculta institucional" if dix_fuerte else "")
                   + ". Liquidez INTACTA pero lista: watchlist armada, tamaños calculados (mesas de póker), "
                   "escalones del plan de caídas a mano. Se dispara la entrada cuando alguno pase a DESPERTANDO.")
            inval = "Se degrada a LIQUIDEZ si las huellas de acumulación desaparecen (vuelven a SANGRA) o el DIX cae por debajo de 43."
        else:
            estado, col = "LIQUIDEZ", "#F4607A"
            que = ("Liderazgo defensivo confirmado y sin huellas de suelo en la alta beta: el sitio es la LIQUIDEZ, "
                   "no los defensivos (se mueven poco y con capital pequeño la rotación se come el beneficio). "
                   "Cobrar el escalón del plan de caídas si toca y ESPERAR: la paciencia también es una posición.")
            inval = ("Se pasa a ACECHO cuando 2+ explosivos muestren el patrón pre-despertar (o el DIX supere 45.5 en caída), "
                     "y a REENTRADA cuando alguno DESPIERTE con el spread girando.")
    else:
        estado, col = "TRANSICION", "#9FB0C8"
        que = ("Zona gris: ni la alta beta ni los defensivos mandan con claridad. Sin cambios: mantener lo que funciona, "
               "no perseguir nada nuevo, y dejar que el viernes decida. El sistema está diseñado para NO operar aquí.")
        inval = f"Sale de la zona gris cuando el spread supere {CENTINELA_SPREAD_ON:+.1f} (RISK-ON) o caiga bajo {CENTINELA_SPREAD_OFF:+.1f} dos semanas (LIQUIDEZ)."
    # --- persistencia entre sesiones: confirmacion a 2 cierres ---
    hist = update_centinela_ledger(estado, str(df.index[-1].date()))
    prev = hist[-2]["estado"] if len(hist) >= 2 else None
    confirmado = bool(prev == estado)
    cambios = []
    _last = None
    for r in hist:
        if r["estado"] != _last:
            cambios.append(r)
            _last = r["estado"]
    return {"estado": estado, "col": col, "que": que, "inval": inval, "confirmado": confirmado, "prev": prev,
            "spread": round(spread, 2), "d3": round(d3, 2), "lado": lado, "cayendo": cayendo,
            "spread_spark": [float(x) for x in spread_s.iloc[-26:]],
            "cmf_beta": cmf_beta, "beta_pos": beta_pos, "def_lidera": def_lidera, "exp_lidera": exp_lidera,
            "credito_ok": credito_ok, "hyg_tlt": hyg_tlt, "amplitud_ok": amplitud_ok,
            "acecho": acecho_syms, "despierta": despierta_syms, "dix_fuerte": dix_fuerte,
            "cambios": cambios[-8:], "quads": {k: _q(k) for k in exp_ok + def_ok + ["S-CREDITO", "S-AMPLITUD"] if k in rrg}}


def compute_momento(df, rrg, flow, suelo=None, graduados=None, look=13, skip=1, corto=4, hist=10):
    """📐 CUADRO DEL FACTOR MOMENTO: nivel (X) contra aceleracion (Y).

    Existe para tapar un agujero real del RRG. El impulso del RRG es un z-score sobre
    ventana movil, y por eso SE ADELANTA al precio: cuando el sector deja de caer el
    indicador ya cruza al alza aunque el precio siga plano. Cuando el precio arranca de
    verdad, el cruce lleva ya 5-8 semanas y compute_graduados (ventana de 4) ya lo ha
    soltado; compute_suelo tampoco lo recoge porque su impulso pasa de 101. Resultado:
    un sector que sube se queda en tierra de nadie, visible en el grafico y en ningun
    panel de deteccion. Asi se esfumaron KWEB y FXI.

    El momento en crudo no lleva z-score: no se adelanta ni se retrasa, SIGUE al precio.
      X = momento 12-1: rentabilidad de t-13 a t-1. Se salta la ultima semana porque
          el corto plazo suele rebotar en contra (Jegadeesh-Titman).
      Y = aceleracion: ritmo semanal de las ultimas 4 frente al ritmo medio de las 12.
    Ambos ejes son RANKING entre sectores (percentil), no valor absoluto: lo que importa
    es quien lo hace mejor que el resto, no cuanto sube en abstracto.

    Cuatro cajas:
      EN MARCHA (alto y acelerando) · MADURO (alto y frenando)
      GIRANDO   (bajo y acelerando) · CAYENDO (bajo y frenando)

    OJO con la jerarquia: esto es PRECIO, no flujo. El cuadro PROPONE; el CMF y el cierre
    del viernes siguen siendo los que CONFIRMAN. Y el factor momento se desploma en los
    giros de regimen: con CENTINELA en DISTRIBUCION o LIQUIDEZ hay que apagarlo.
    """
    syms = [s for s in df.columns if s != BENCH and s not in SINTETICOS]
    n_nec = look + hist + 2
    if len(df) < n_nec or len(syms) < 8:
        return None

    def _cajas_en(t):
        """Las cuatro cajas tal como se veian en la semana t (t=0 es la ultima)."""
        m12, m4 = {}, {}
        for s in syms:
            ser = df[s]
            a, b = ser.iloc[t - look], ser.iloc[t - skip]
            c = ser.iloc[t - corto]
            if a > 0 and c > 0 and b == b and a == a and c == c:
                m12[s] = (b / a - 1) * 100
                m4[s] = (ser.iloc[t] / c - 1) * 100
        comunes = [s for s in m12 if s in m4]
        if len(comunes) < 8:
            return None, None, None
        ace = {s: (m4[s] / corto) - (m12[s] / (look - skip)) for s in comunes}
        def _pct(d):
            o = sorted(d, key=lambda s: -d[s])
            return {s: 1 - i / (len(o) - 1) for i, s in enumerate(o)}
        pm, pa = _pct({s: m12[s] for s in comunes}), _pct(ace)
        caja = {}
        for s in comunes:
            alto, acel = pm[s] >= 0.5, pa[s] >= 0.5
            caja[s] = ("EN MARCHA" if (alto and acel) else "MADURO" if alto
                       else "GIRANDO" if acel else "CAYENDO")
        return caja, {"m12": m12, "m4": m4, "ace": ace}, {"pm": pm, "pa": pa}

    T = len(df) - 1
    caja_hoy, vals, pcts = _cajas_en(T)
    if not caja_hoy:
        return None
    # persistencia: cuantas semanas seguidas lleva en la misma caja.
    # Una semana es ruido; tres seguidas ya es un patron.
    previas = []
    for k in range(1, hist + 1):
        c, _, _ = _cajas_en(T - k)
        previas.append(c or {})

    ya_visto = set()
    for r in (suelo or []):
        ya_visto.add(r.get("sym"))
    for r in (graduados or []):
        ya_visto.add(r.get("sym"))

    rows = []
    for s, cj in caja_hoy.items():
        sem = 1
        for c in previas:
            if c.get(s) == cj:
                sem += 1
            else:
                break
        ser = df[s].dropna()
        sma40 = float(ser.rolling(40).mean().iloc[-1]) if len(ser) >= 40 else None
        ext = ((float(ser.iloc[-1]) / sma40 - 1) * 100) if (sma40 and sma40 > 0) else None
        f = (flow or {}).get(s, {}) or {}
        cmf = f.get("cmf")
        mejora = bool(f.get("cmf_mejora"))
        aext = bool(f.get("acum_ext"))
        flujo_ok = bool((cmf is not None and cmf > 0) or mejora or aext)
        quad = (rrg.get(s, {}) or {}).get("quad")

        if cj == "EN MARCHA":
            if ext is not None and ext > 12:
                ver, vcol = "🔴 corriendo pero ya extendido — no perseguir, esperar retroceso", "#F4607A"
            elif cmf is not None and cmf > 0:
                ver, vcol = "🟢 precio y flujo de acuerdo — posición con el cierre del viernes", "#2FD08A"
            elif flujo_ok:
                ver, vcol = "🟡 precio manda, flujo girando — manga pequeña", "#F4B740"
            else:
                ver, vcol = "⚪ sube sin flujo detrás — el precio propone, el CMF no confirma", "#9FB0C8"
        elif cj == "GIRANDO":
            if flujo_ok:
                ver, vcol = "🟢 aviso temprano: aún flojo pero acelerando CON flujo — vigilar de cerca", "#2FD08A"
            else:
                ver, vcol = "⚪ aviso temprano: acelera sin flujo aún — solo mirar, no tocar", "#9FB0C8"
        elif cj == "MADURO":
            ver, vcol = "🟠 fuerte pero perdiendo ritmo — gestionar lo abierto, no abrir nuevo", "#F4B740"
        else:
            ver, vcol = "🔴 débil y frenando — fuera del radar", "#F4607A"

        rows.append({
            "sym": s, "caja": cj, "sem": sem,
            "m12": round(float(vals["m12"][s]), 1), "m4": round(float(vals["m4"][s]), 1),
            "ace": round(float(vals["ace"][s]), 2),
            "pm": int(round(pcts["pm"][s] * 100)), "pa": int(round(pcts["pa"][s] * 100)),
            "ext": (round(float(ext), 1) if ext is not None else None),
            "cmf": (float(cmf) if cmf is not None else None), "mejora": mejora, "aext": aext, "quad": quad,
            # el limbo: corre y no sale en ningun otro panel de deteccion
            "huerfano": bool(cj == "EN MARCHA" and sem >= 2 and s not in ya_visto),
            "ver": ver, "vcol": vcol,
        })

    orden = {"EN MARCHA": 0, "GIRANDO": 1, "MADURO": 2, "CAYENDO": 3}
    rows.sort(key=lambda r: (orden[r["caja"]], -r["pm"]))
    por_caja = {c: [r for r in rows if r["caja"] == c] for c in orden}
    return {"rows": rows, "cajas": por_caja,
            "huerfanos": [r for r in rows if r["huerfano"]],
            "n": len(rows), "look": look, "corto": corto}


def compute_graduados(df, rrg, flow, max_sem=4, cueva_ventana=12, cueva_min=5):
    """🌅 RECIEN DESPERTADOS (graduados de la cueva): los que ERAN durmientes — semanas rezagados y
    castigados — y cuyo impulso RRG cruzo al alza hace <= max_sem semanas y se ha MANTENIDO arriba.
    Es la fase que faltaba: en el radar de durmientes desaparecen justo cuando se ponen interesantes
    (KWEB y FXI se esfumaron asi entre paneles); aqui se les sigue mientras la entrada aun no este
    extendida, con la regla de tramos: manga pequena si el flujo esta girando, posicion completa solo
    con CMF > 0 y siempre con el cierre del viernes."""
    rows = []
    for s in rrg:
        if s == BENCH or s in SINTETICOS:
            continue
        try:
            ser = df[s].dropna() if s in df.columns else None
            if ser is None or len(ser) < 30:
                continue
            rs = rrg[s].get("ratio_series") or []
            ms = rrg[s].get("mom_series") or []
            pares = [(r, m) for r, m in zip(rs, ms) if r is not None and m is not None and r == r and m == m]
            if len(pares) < cueva_ventana + max_sem + 2:
                continue
            momv = [m for _, m in pares]
            # cruce: ultimo indice k donde el impulso paso de <=101 a >101 Y sigue >101 hasta hoy (continuo)
            k = None
            for i in range(len(momv) - 1, 0, -1):
                if momv[i] <= 101:
                    break
                if momv[i - 1] <= 101:
                    k = i
                    break
            if k is None:
                continue
            sem_desp = len(momv) - 1 - k          # 0 = cruzo esta semana
            if sem_desp > max_sem:
                continue
            # la cueva: en las cueva_ventana semanas ANTES del cruce, >= cueva_min con fuerza rezagada.
            # Umbral 98.5/102: una base plana justo antes del giro normaliza el z-ratio hacia 100 y con
            # 97.5 estricto se escapaban los suelos someros (el castigo >=8% y el cruce siguen filtrando).
            prev = pares[max(0, k - cueva_ventana):k]
            if sum(1 for r, m in prev if r <= 98.5 and m <= 102.0) < cueva_min:
                continue
            # castigo en el cruce: al menos -8% vs su maximo de 52 semanas en aquel momento
            idx_cross = len(ser) - 1 - sem_desp
            if idx_cross < 5:
                continue
            px_cross = float(ser.iloc[idx_cross])
            max52 = float(ser.iloc[max(0, idx_cross - 51):idx_cross + 1].max())
            dd_cross = (px_cross / max52 - 1) * 100 if max52 > 0 else 0.0
            if dd_cross > -8.0:
                continue
            last = float(ser.iloc[-1])
            pct_desde = (last / px_cross - 1) * 100
            sma40 = float(ser.rolling(40).mean().iloc[-1]) if len(ser) >= 40 else None
            ext = ((last / sma40 - 1) * 100) if (sma40 and sma40 > 0) else None
            f = (flow or {}).get(s, {}) or {}
            cmf = f.get("cmf"); mejora = bool(f.get("cmf_mejora")); aext = bool(f.get("acum_ext"))
            flujo_ok = bool((cmf is not None and cmf > 0) or mejora or aext)
            if ext is not None and ext > 12:
                ver, vcol = "🔴 ya extendido — esperar retroceso a la media, no perseguir", "#F4607A"
            elif flujo_ok and (ext is None or ext <= 6):
                _det = ("CMF>0" if (cmf is not None and cmf > 0)
                        else ("CMF mejorando 3 tramos" if mejora else "acumulación extranjera 🌏"))
                _tam = "posición" if (cmf is not None and cmf > 0) else "manga pequeña"
                ver, vcol = f"🟢 sin extender y flujo girando ({_det}) — {_tam} con el cierre del viernes", "#2FD08A"
            elif flujo_ok:
                ver, vcol = "🟡 a medio extender con flujo girando — solo manga pequeña y stop en el cruce", "#F4B740"
            else:
                ver, vcol = "⚪ despierto pero sin flujo — vigilar el viernes, no adelantarse", "#9FB0C8"
            rows.append({"sym": s, "sem": sem_desp, "pct": round(pct_desde, 1),
                         "ext": (round(ext, 1) if ext is not None else None), "dd_cross": round(dd_cross, 0),
                         "cmf": cmf, "mejora": mejora, "aext": aext, "noct": f.get("noct20"),
                         "ver": ver, "vcol": vcol, "expl": s in SECTORES_EXPLOSIVOS})
        except Exception:
            continue
    rows.sort(key=lambda r: (r["sem"], -(r["pct"] or 0)))
    return rows[:10]


def compute_cockpit_beta(df, rrg, flow, suelo=None, graduados=None, desks=None, giro=None):
    """💥 COCKPIT ALTA BETA: la tabla que fusiona TODO lo que el terminal sabe de los sectores explosivos
    en UNA fila por sector, ordenada por cercania a la ignicion. La tesis: con poco capital, el dinero
    esta en entrar ABAJO en alta beta cuando despierta — no en rotar defensivos que no se mueven.
    Fusiona: suelo (pts/10) + patron pre-despertar (0/4) + capitulacion + silencio + flujo (CMF, mejora
    por tramos, 🌏 nocturno) + giro vertical + graduacion + la mesa de poker (prob. del cubo historico).
    El score de ANTICIPACION (0-100) pondera todo eso; es un ranking interno, NO una probabilidad."""
    smap = {r["sym"]: r for r in (suelo or [])}
    gmap = {g["sym"]: g for g in (graduados or [])}
    dmap = {}
    for dk in (desks or []):
        if dk and dk.get("sym"):
            dmap[dk["sym"]] = dk
    girom = {}
    for row in ((giro or {}).get("rows") or []):
        girom[row.get("sym")] = row
    FASE_ORDEN = {"PRE-DESPERTAR": 0, "DESPERTANDO": 1, "GRADUADO": 2, "ACUMULACION": 3,
                  "CAPITULACION": 4, "CASTIGADO": 5, "DORMIDO": 6, "SANGRA": 7, "EN MARCHA": 8, "NEUTRO": 9}
    rows = []
    for s in SECTORES_EXPLOSIVOS:
        if s in ("LABU", "TNA") or s not in rrg or s not in df.columns:
            continue          # los x3 no se analizan: son vehiculo, no sector
        try:
            ser = df[s].dropna()
            if len(ser) < 20:
                continue
            last = float(ser.iloc[-1])
            max52 = float(ser.iloc[-min(52, len(ser)):].max())
            dd52 = round((last / max52 - 1) * 100, 0) if max52 > 0 else 0.0
            quad = rrg[s].get("quad"); mom = rrg[s].get("mom", 100)
            f = (flow or {}).get(s, {}) or {}
            cmf = f.get("cmf"); mejora = bool(f.get("cmf_mejora")); aext = bool(f.get("acum_ext"))
            capit = bool(f.get("clima") == "capitulacion" and (f.get("clima_hace") or 0) <= 2)
            su, gr, dk = smap.get(s), gmap.get(s), dmap.get(s)
            # ---- FASE del pipeline ----
            if gr:
                fase = "GRADUADO"
            elif su:
                fase = su["fase"] if su["fase"] != "DORMIDO" else "DORMIDO"
            elif capit:
                fase = "CAPITULACION"
            elif quad in ("leading", "improving") and mom > 101:
                fase = "EN MARCHA"
            elif dd52 <= -15 and cmf is not None and cmf < -0.10:
                fase = "SANGRA"
            elif dd52 <= -12:
                fase = "CASTIGADO"
            else:
                fase = "NEUTRO"
            # ---- score de anticipacion 0-100 ----
            sc = 0
            if su:
                sc += min(40, int(su.get("pts", 0)) * 4)
                sc += min(28, int(su.get("pre", 0)) * 7)
                if su.get("despertando"):
                    sc += 6
                if su.get("sangra"):
                    sc -= 15
            if capit:
                sc += 8
            if mejora:
                sc += 8
            if cmf is not None and cmf > 0:
                sc += 6
            if aext:
                sc += 8
            if s in girom and girom[s].get("sig") == "alcista":
                sc += 6
            if gr:
                sc += 10
                if gr.get("ext") is not None and gr["ext"] > 12:
                    sc -= 12
            desk_prob = None
            if dk:
                _now = next((t for t in (dk.get("tbl") or []) if t.get("now")), None)
                desk_prob = (_now or {}).get("p")
                if (desk_prob or 0) >= 60:
                    sc += 8
                if (dk.get("pts") or 0) >= 6:
                    sc += 6
            sc = max(0, min(100, sc))
            # ---- accion por fase (regla de tramos) ----
            if fase == "PRE-DESPERTAR":
                acc, acol = "liquidez lista: si el viernes confirma con flujo, manga en el giro", "#4CC2E0"
            elif fase == "DESPERTANDO":
                acc, acol = "despierta: manga con el cierre del viernes si el flujo dejo de salir", "#2FD08A"
            elif fase == "GRADUADO":
                acc, acol = (gr or {}).get("ver", "seguir el veredicto del panel de graduados"), (gr or {}).get("vcol", "#2FD08A")
            elif fase == "ACUMULACION":
                acc, acol = "el dinero entra callado: vigilar el paso a pre-despertar", "#7BD88F"
            elif fase == "CAPITULACION":
                acc, acol = "panico de un dia: empieza la vigilancia — sin flujo no hay trato", "#B980FF"
            elif fase == "CASTIGADO":
                acc, acol = "castigado pero sin patron todavia: paciencia", "#9FB0C8"
            elif fase == "SANGRA":
                acc, acol = "ni tocar: el dinero sigue saliendo, da igual lo barato", "#F4607A"
            elif fase == "EN MARCHA":
                acc, acol = "ya en marcha: esto es del gestor de salidas, no del cazador", "#8FA3C0"
            else:
                acc, acol = "sin señal: fuera del radar esta semana", "#5E708A"
            rows.append({"sym": s, "tipo": EXPLOSIVO_TIPO.get(s, ""), "fase": fase, "sc": sc,
                         "dd52": dd52, "cmf": cmf, "mejora": mejora, "aext": aext, "noct": f.get("noct20"),
                         "capit": capit, "pre": (su or {}).get("pre", 0), "pts": (su or {}).get("pts"),
                         "desk_prob": desk_prob, "desk_id": (dk or {}).get("id"),
                         "gr_sem": (gr or {}).get("sem"), "acc": acc, "acol": acol,
                         "orden": FASE_ORDEN.get(fase, 9)})
        except Exception as _dege:
            _deg("compute_cockpit_beta:5866", _dege)
            continue
    rows.sort(key=lambda r: (r["orden"], -r["sc"]))
    return rows or None


def compute_gestor_salidas(syms, df, daily, rrg, flow, centinela=None):
    """🧭 GESTOR DE SALIDAS — gestion de posiciones estilo gestor de fondo: detectar cuando SUBE de
    verdad la probabilidad de que el tramo alcista este agotandose, sin vender solo porque "ya subio
    mucho". Cuatro pilares computables cada dia con los datos descargados:
      1) TENDENCIA: perdida de minimos crecientes, ruptura de SMA20/SMA50 diarias, cierre bajo soporte.
      2) FUERZA: divergencia bajista de RSI, MACD deteriorandose, perdida de fuerza relativa vs S&P.
      3) VOLUMEN: distribucion (CMF), dias de caida con volumen alto, rachas de venta.
      4) CONTEXTO: cuadrante RRG del propio sector + regimen del CENTINELA.
    El 5º pilar (noticias, valoracion, resultados) NO es computable aqui: ese lo pones tu o el prompt IA.
    El "score de deterioro" 0-100 se muestra como probabilidad ORIENTATIVA de techo (no esta calibrada).
    Filosofia: capturar el movimiento grande > acertar el maximo exacto — solo se penaliza la EVIDENCIA
    objetiva de deterioro, nunca la extension al alza por si sola."""
    out = []
    for s in syms or []:
        try:
            d = daily.get(s)
            if d is None or "Close" not in d.columns or len(d.dropna(subset=["Close"])) < 60:
                continue
            dd = d.dropna(subset=["Close"]).copy()
            c = dd["Close"].astype(float)
            vol = dd["Volume"].astype(float) if "Volume" in dd.columns else None
            px = float(c.iloc[-1])
            sma20 = float(c.rolling(20).mean().iloc[-1])
            sma50 = float(c.rolling(50).mean().iloc[-1])
            razones, pts = [], 0
            # 1) TENDENCIA
            m_rec = float(c.iloc[-10:].min()); m_prev = float(c.iloc[-25:-10].min())
            if m_rec < m_prev * 0.998:
                pts += 12; razones.append((12, "perdió los mínimos crecientes (estructura rota)"))
            if px < sma20:
                pts += 10; razones.append((10, "cierra bajo su media de 20 sesiones"))
            if px < sma50:
                pts += 14; razones.append((14, "cierra bajo su media de 50 sesiones"))
            sop = float(c.iloc[-21:-1].min())
            if px < sop:
                pts += 10; razones.append((10, "rompió el soporte de las últimas 20 sesiones"))
            # 2) FUERZA
            delta = c.diff()
            up = delta.clip(lower=0).rolling(14).mean(); dn = (-delta.clip(upper=0)).rolling(14).mean()
            rs14 = up / dn.replace(0, float("nan"))
            rsi = 100 - 100 / (1 + rs14)
            try:
                h1 = float(c.iloc[-15:].max()); h0 = float(c.iloc[-40:-15].max())
                r1 = float(rsi.iloc[-15:].max()); r0 = float(rsi.iloc[-40:-15].max())
                if h1 > h0 and r1 < r0 - 1:
                    pts += 10; razones.append((10, "divergencia bajista de RSI (precio hace máximo, la fuerza no)"))
            except Exception:
                pass
            ema12 = c.ewm(span=12).mean(); ema26 = c.ewm(span=26).mean()
            macd = ema12 - ema26; sig = macd.ewm(span=9).mean(); hist = (macd - sig).dropna()
            if len(hist) >= 6 and float(hist.iloc[-1]) < 0 and float(hist.iloc[-1]) < float(hist.iloc[-5]):
                pts += 6; razones.append((6, "MACD por debajo de señal y empeorando"))
            _rs = [x for x in (rrg.get(s, {}) or {}).get("ratio_series", []) if x is not None and x == x]
            if len(_rs) >= 4 and _rs[-1] < _rs[-2] < _rs[-3]:
                pts += 8; razones.append((8, "pierde fuerza relativa vs S&P dos semanas seguidas"))
            _ms = [x for x in (rrg.get(s, {}) or {}).get("mom_series", []) if x is not None and x == x]
            if len(_ms) >= 3 and _ms[-1] < _ms[-2] and _ms[-1] < 100:
                pts += 4; razones.append((4, "impulso RRG cayendo y por debajo de 100"))
            # 3) VOLUMEN
            f = (flow or {}).get(s, {}) or {}
            cmf = f.get("cmf")
            if f.get("diverg") == "distribucion oculta":
                pts += 10; razones.append((10, "DISTRIBUCIÓN OCULTA: el precio aguanta pero el dinero sale"))
            elif cmf is not None and cmf < -0.05:
                pts += 8; razones.append((8, f"el dinero sale (CMF {cmf:+.2f})"))
            if vol is not None and len(vol) >= 30:
                v20 = vol.rolling(20).mean()
                ndist = int(((c.pct_change() < -0.003) & (vol > v20 * 1.3)).iloc[-10:].sum())
                if ndist >= 3:
                    pts += 8; razones.append((8, f"{ndist} días de venta con volumen alto en 10 sesiones (distribución institucional)"))
            rets = c.pct_change().iloc[-4:]
            if len(rets) >= 3 and int((rets < -0.008).sum()) >= 3:
                pts += 4; razones.append((4, "racha de 3+ sesiones de venta fuerte"))
            # 4) CONTEXTO
            quad = (rrg.get(s, {}) or {}).get("quad")
            if quad == "weakening":
                pts += 6; razones.append((6, "su sector se debilita en el RRG (deja de liderar)"))
            elif quad == "lagging":
                pts += 10; razones.append((10, "su sector ya es rezagado en el RRG"))
            _est = (centinela or {}).get("estado")
            if _est == "DISTRIBUCION":
                pts += 5; razones.append((5, "el CENTINELA está en DISTRIBUCIÓN: el mercado rota a defensivos"))
            elif _est in ("LIQUIDEZ", "ACECHO"):
                pts += 8; razones.append((8, "el CENTINELA está en riesgo-OFF: contexto en contra"))
            # 🌏 atenuante: acumulacion extranjera contradice la lectura de venta del CMF
            if f.get("acum_ext"):
                pts = max(0, pts - 8)
                razones.append((-8, f"🌏 atenuante: flujo nocturno {f.get('noct20', 0):+.1f}% — la compra ocurre en su bolsa local y el CMF la infravalora"))
            pts = max(0, min(100, pts))
            p_techo = pts
            p_cont = 100 - pts
            if p_techo < 25:
                est, ecol = "🟢 MANTENER", "#2FD08A"
            elif p_techo < 45:
                est, ecol = "🟡 MANTENER + SUBIR STOP", "#F4B740"
            elif p_techo < 70:
                est, ecol = "🟠 REDUCIR 25–50%", "#FF8C42"
            else:
                est, ecol = "🔴 SALIR", "#F4607A"
            # stop: el nivel mas alto que quede POR DEBAJO del precio (minimo de 10 sesiones o SMA50)
            _cands = [x for x in (m_rec, sma50) if x < px]
            stop = round(max(_cands) if _cands else float(c.iloc[-5:].min()) * 0.99, 2)
            # recompra si corrige: SMA50 diaria (tendencia probandose de nuevo) o el soporte previo
            recompra = round(sma50 if px > sma50 else sop, 2)
            razones.sort(key=lambda x: -abs(x[0]))
            out.append({"sym": s, "est": est, "ecol": ecol, "p_techo": p_techo, "p_cont": p_cont,
                        "stop": stop, "recompra": recompra, "px": round(px, 2),
                        "razones": [r for _, r in razones[:3]] or ["sin evidencias de deterioro: la tendencia sigue sana"]})
        except Exception:
            continue
    out.sort(key=lambda r: -r["p_techo"])
    return out or None


def compute_rebote_desk(df, daily, rrg, flow, scores, leaders, giro=None, prefs=("SMH", "SOXX"), lead_keys=None, desk_id=None):
    """Mesa de poker GENÉRICA de un tema explosivo (semis, materiales, espacio...): la 'mano' actual
    (estado), la 'mesa' (probabilidades HISTORICAS de rebote a 4 semanas condicionadas a la
    profundidad de la caida, con intervalo de confianza Wilson 95%) y el 'bote' (EV y tamano
    fraccional). Todo calculado sobre la serie real del propio ETF — sin numeros inventados.
    prefs = ETFs candidatos por orden de preferencia; lead_keys = de que ETF tomar el desglose
    de acciones para el washout si el elegido no tiene el suyo propio."""
    sym = next((p for p in prefs if p in df.columns), None)
    if not sym:
        return None
    w = df[sym].dropna()
    # si la serie diaria tiene mas historia, la resampleamos a semanal para engordar la muestra
    try:
        dser = (daily or {}).get(sym)
        if dser is not None and "Close" in dser.columns:
            wl = dser["Close"].dropna().resample("W-FRI").last().dropna()
            if len(wl) > len(w):
                w = wl
    except Exception as _dege:
        _deg("compute_rebote_desk:6004", _dege)
        pass
    if len(w) < 30:
        return None
    # --- LA MANO: estado actual ---
    hi52 = float(w.iloc[-1] / w.iloc[-min(52, len(w)):].max() * 100)
    dd52 = hi52 - 100.0                                   # caida desde maximos (negativa)
    r4 = w.pct_change(4).dropna()
    z4 = float((r4.iloc[-1] - r4.mean()) / (r4.std() or 1.0)) if len(r4) > 10 else 0.0
    ma40 = w.rolling(40, min_periods=20).mean()
    vs40 = float(w.iloc[-1] / ma40.iloc[-1] - 1) * 100 if ma40.iloc[-1] == ma40.iloc[-1] else None
    chg = w.pct_change().dropna()
    streak = 0
    for v in reversed(list(chg)):
        if v < 0:
            streak += 1
        else:
            break
    d = rrg.get(sym, {}) or {}
    f = (flow or {}).get(sym, {}) or {}
    sc = next((r for r in (scores or []) if r["sym"] == sym), {}) or {}
    lead = (leaders or {}).get(sym) or []
    if not lead:
        for lk in (lead_keys or []):
            lead = (leaders or {}).get(lk) or []
            if lead:
                break
    wash = None
    if lead:
        wash = int(round(100 * sum(1 for r in lead if r.get("phase") == "baja" or (r.get("rs") or 99) < 30) / len(lead)))
    g = None
    for row in ((giro or {}).get("rows") or []):
        if row["sym"] in prefs:
            g = row
            break
    # --- LA MESA: prob. historica de estar mas arriba 4 semanas despues, por cubo de caida ---
    hi52s = w / w.rolling(52, min_periods=20).max() * 100
    fwd4 = (w.shift(-4) / w - 1)
    def _wilson(p, n, zz=1.96):
        den = 1 + zz * zz / n
        ctr = (p + zz * zz / (2 * n)) / den
        rad = zz * math.sqrt(p * (1 - p) / n + zz * zz / (4 * n * n)) / den
        return int(round(100 * (ctr - rad))), int(round(100 * (ctr + rad)))
    tbl = []
    for lo, hiB, lbl in [(0, 5, "0–5%"), (5, 10, "5–10%"), (10, 15, "10–15%"), (15, 25, "15–25%"), (25, 100, ">25%")]:
        caida = 100 - hi52s
        mask = (caida >= lo) & (caida < hiB) & fwd4.notna()
        n = int(mask.sum())
        if n >= 3:
            p = float((fwd4[mask] > 0).mean())
            wlo, whi = _wilson(p, n)
            tbl.append({"lbl": lbl, "n": n, "p": int(round(100 * p)), "lo": wlo, "hi": whi,
                        "avg": round(float(fwd4[mask].mean()) * 100, 1),
                        "now": (lo <= -dd52 < hiB)})
    # sobreventa estadistica: retorno 4s por debajo de -1.5 desviaciones
    zview = None
    if len(r4) > 20:
        zmask = r4 <= (r4.mean() - 1.5 * r4.std())
        zf = fwd4.reindex(r4[zmask].index).dropna()
        if len(zf) >= 3:
            p = float((zf > 0).mean())
            wlo, whi = _wilson(p, len(zf))
            zview = {"n": len(zf), "p": int(round(100 * p)), "lo": wlo, "hi": whi,
                     "avg": round(float(zf.mean()) * 100, 1), "now": z4 <= -1.5}
    # --- REBOTE SCORE 0-10: los ingredientes del rebote salvaje ---
    pts, det = 0, []
    if dd52 <= -15:
        pts += 2; det.append(f"caída {dd52:.0f}% desde máximos")
    elif dd52 <= -8:
        pts += 1; det.append(f"caída {dd52:.0f}%")
    if z4 <= -1.5:
        pts += 2; det.append(f"sobreventa z={z4:.1f}")
    elif z4 <= -1.0:
        pts += 1; det.append(f"z={z4:.1f}")
    if streak >= 3:
        pts += 1; det.append(f"{streak} semanas rojas seguidas")
    cmf = f.get("cmf")
    if cmf is not None:
        if cmf > 0.05:
            pts += 2; det.append("CMF: el dinero ya entra")
        elif cmf >= -0.05:
            pts += 1; det.append("CMF plano: dejó de salir")
    if g and g.get("sig") == "alcista":
        pts += 2; det.append(f"giro intradía: compraron el miedo ({g.get('fecha', '')})")
    if wash is not None and wash >= 50:
        pts += 1; det.append(f"washout: {wash}% de componentes rotos")
    tail = d.get("tail") or []
    if len(tail) >= 4 and (tail[-1][1] - tail[-4][1]) >= 1.5:
        pts += 1; det.append("impulso RRG girando al alza")
    pts = min(pts, 10)
    # EV y tamano con el cubo actual
    ev = None
    cur = next((t for t in tbl if t["now"]), None)
    if cur and cur["n"] >= 10:
        ev = {"p": cur["p"], "avg": cur["avg"], "n": cur["n"],
              "kelly4": max(0.0, round((cur["p"] / 100 - (1 - cur["p"] / 100)) * 25, 1))}  # ~Kelly/4 con payoff 1:1, tope abajo
    return {"sym": sym, "id": desk_id, "dd52": round(dd52, 1), "z4": round(z4, 2), "vs40": (round(vs40, 1) if vs40 is not None else None),
            "streak": streak, "quad": d.get("quad"), "score": sc.get("score"), "cmf": cmf,
            "distrib": sc.get("distrib"), "wash": wash, "giro": g, "tbl": tbl, "zview": zview,
            "pts": pts, "det": det, "ev": ev, "n_hist": len(w)}


def compute_analogos_flujo(daily, sym_precio, sym_flujo=None, n_sesiones=2, horizontes=(1, 5, 10, 21, 30)):
    """DETECTOR DE ANÁLOGOS (contexto, NO señal de trading).

    Busca en el histórico DIARIO las veces que se repitió la condición:
        el ETF cae  Y  el dinero sale (CMF de su hermano de flujo negativo)  N sesiones SEGUIDAS
    y mide qué hizo el precio después a T+1/T+5/T+10/T+21/T+30.

    Honestidad de origen: la idea viene de una tabla que mide el "sell skew" del MINORISTA (flujo de
    ordenes de pago que este terminal NO tiene). Aqui se usa el CMF como proxy de flujo: NO es lo
    mismo — el CMF dice "sale dinero", no "vendio el minorista". Se etiqueta como frecuencia
    historica con N visible e IC de Wilson, nunca como probabilidad ni prediccion."""
    d = (daily or {}).get(sym_precio)
    if d is None or "Close" not in d.columns or len(d) < 120:
        return None
    df_f = (daily or {}).get(sym_flujo or sym_precio)
    if df_f is None or not {"High", "Low", "Close", "Volume"}.issubset(df_f.columns) or len(df_f) < 60:
        return None
    px = d["Close"].dropna()
    # CMF diario de 20 sesiones sobre el simbolo de flujo (mismo calculo que el resto del terminal)
    hi, lo, cl, vo = df_f["High"], df_f["Low"], df_f["Close"], df_f["Volume"].astype(float)
    rng = (hi - lo).replace(0, np.nan)
    mfv = ((((cl - lo) - (hi - cl)) / rng).fillna(0)) * vo
    cmf = (mfv.rolling(20).sum() / vo.rolling(20).sum()).reindex(px.index).ffill(limit=3)
    baja = px.pct_change() < 0
    cond = baja & (cmf < 0)
    # racha de N sesiones consecutivas cumpliendo la condicion; se marca el ULTIMO dia de la racha
    racha = cond.astype(int).groupby((~cond).cumsum()).cumsum()
    disparo = (racha == n_sesiones)          # exactamente al alcanzar N (no cuenta cada dia extra)
    idxs = list(np.where(disparo.values)[0])
    if len(idxs) < 4:
        return None
    def _wil(p, n, zz=1.96):
        den = 1 + zz * zz / n
        ctr = (p + zz * zz / (2 * n)) / den
        rad = zz * math.sqrt(p * (1 - p) / n + zz * zz / (4 * n * n)) / den
        return int(round(100 * (ctr - rad))), int(round(100 * (ctr + rad)))
    filas = []
    v = px.values
    for h in horizontes:
        rets = [(v[i + h] / v[i] - 1) for i in idxs if i + h < len(v)]
        n = len(rets)
        if n < 4:
            continue
        p = sum(1 for r in rets if r > 0) / n
        wlo, whi = _wil(p, n)
        filas.append({"h": h, "n": n, "p": int(round(100 * p)), "lo": wlo, "hi": whi,
                      "avg": round(100 * float(np.mean(rets)), 1),
                      "med": round(100 * float(np.median(rets)), 1)})
    if not filas:
        return None
    # ¿la condicion esta ACTIVA ahora mismo? (racha >= N en la ultima sesion)
    activa = bool(racha.iloc[-1] >= n_sesiones)
    ultima = None
    if idxs:
        try:
            ultima = str(px.index[idxs[-1]].date())
        except Exception:
            ultima = None
    return {"sym": sym_precio, "flujo": (sym_flujo or sym_precio), "n_ses": n_sesiones,
            "casos": len(idxs), "filas": filas, "activa": activa, "ultima": ultima,
            "cmf_hoy": (round(float(cmf.iloc[-1]), 3) if pd.notna(cmf.iloc[-1]) else None),
            "racha_hoy": int(racha.iloc[-1])}


def compute_cascada(df, rrg, flow=None):
    """MAPA DE LA CASCADA DEL CAPEX DE IA — ¿en qué eslabón está el dinero hoy?

    Un euro de capex no llega a todos a la vez: paga primero el chip (C1), luego la obra (C2), la
    electricidad (C3) y al final la materia prima (C4). Este panel mide la fuerza relativa y el flujo
    de cada eslabón para VER la rotación en vez de suponerla.

    Contexto, NO señal: los eslabones son sintéticos de solo lectura. La ejecución la sigue mandando
    el flujo del viernes sobre los ETFs concretos."""
    esl = sorted([(k, v) for k, v in SINTETICOS.items() if v.get("grupo") == "cascada"],
                 key=lambda kv: kv[1].get("orden", 99))
    if not esl or rrg is None:
        return None
    flow = flow or {}
    filas = []
    for key, cfg in esl:
        d = rrg.get(key)
        if d is None or key not in df.columns:
            continue
        s = df[key].dropna()
        if len(s) < 13:
            continue
        def _r(n):
            return (float(s.iloc[-1] / s.iloc[-1 - n] - 1) * 100) if len(s) > n else None
        miembros = [m for m in cfg["members"] if m in df.columns]
        cmfs = [flow[m]["cmf"] for m in miembros if flow.get(m, {}).get("cmf") is not None]
        filas.append({
            "key": key, "orden": cfg.get("orden", 99), "corto": cfg.get("corto", key),
            "desc": cfg.get("desc", ""), "miembros": miembros,
            "quad": d["quad"], "ratio": round(d["ratio"], 1), "mom": round(d["mom"], 1),
            "dmom": round(d["dmom"], 2),
            "r1": _r(1), "r4": _r(4), "r12": _r(12),
            "cmf": (round(sum(cmfs) / len(cmfs), 3) if cmfs else None),
            "n_cmf": len(cmfs),
        })
    if len(filas) < 2:
        return None
    # ¿QUIEN LIDERA? por fuerza relativa (ratio RRG)
    lider = max(filas, key=lambda f: f["ratio"])
    # ¿EL DINERO BAJA POR LA CADENA? Solo se comparan los eslabones del DESCENSO (1-4): C0 (quien paga)
    # y C5 (quien devuelve) no forman parte de la bajada, son los dos extremos del circulo.
    # v4.7: "orden" puede ser decimal (CE-EQUIPOS = 1.5), asi que se filtra por RANGO.
    # Con la lista de enteros de antes, el eslabon de equipos se caia del calculo sin avisar.
    alto = [f["dmom"] for f in filas if 1 <= f["orden"] <= 2]
    bajo = [f["dmom"] for f in filas if 3 <= f["orden"] <= 4]
    spread = None
    sentido = "sin sentido claro"
    if alto and bajo:
        spread = round(sum(bajo) / len(bajo) - sum(alto) / len(alto), 2)
        if spread > 0.5:
            sentido = "el dinero BAJA por la cadena (rota hacia energía y materia prima)"
        elif spread < -0.5:
            sentido = "el dinero SUBE hacia el principio (vuelve a chips)"
    # --- ¿SE CIERRA EL CIRCULO? Lo que casi nadie mira: el capex solo se sostiene si quien lo paga
    #     (C0) acaba ingresando por el servicio vendido (C5). Si la CADENA vuela pero el RETORNO se
    #     queda atras, el gasto no se esta monetizando — es el aviso temprano de recorte de capex,
    #     y ahi lo que mas cae es el final de la cadena, que es justo donde esta la beta.
    circulo = None
    f0 = next((f for f in filas if f["orden"] == 0), None)
    f5 = next((f for f in filas if f["orden"] == 5), None)
    cadena = [f for f in filas if 1 <= f["orden"] <= 4]
    if f5 and cadena:
        fuerza_cadena = sum(f["ratio"] for f in cadena) / len(cadena)
        gap = round(f5["ratio"] - fuerza_cadena, 1)
        if gap < -2.0:
            estado = "ROTO: la cadena vuela pero el retorno (software/nube) se queda atrás — el capex no se está monetizando"
            nivel = "malo"
        elif gap > 2.0:
            estado = "el retorno tira MÁS que la cadena: lo que se gastó se está cobrando"
            nivel = "bueno"
        else:
            estado = "cadena y retorno van en línea: circuito equilibrado"
            nivel = "neutro"
        circulo = {"gap": gap, "estado": estado, "nivel": nivel,
                   "retorno": round(f5["ratio"], 1), "cadena": round(fuerza_cadena, 1),
                   "paga": (round(f0["ratio"], 1) if f0 else None)}
    return {"filas": filas, "lider": lider["key"], "lider_corto": lider["corto"],
            "spread": spread, "sentido": sentido, "circulo": circulo}


def compute_attention_radar(rrg, flow):
    """Cruza tendencia (RRG) con volumen relativo (proxy de atencion del MERCADO, no de prensa, pero capta
    la misma idea de forma fiable) para separar lo que sube EN SILENCIO (volumen normal = joya escondida) de
    lo que sube CON RUIDO (volumen disparado = masificado, posible techo)."""
    if not rrg or not flow:
        return None
    rows = []
    for s, d in rrg.items():
        if s == BENCH:
            continue
        f = flow.get(s)
        if not f:
            continue
        quad = d.get("quad")
        vr = f.get("vol_rel5", f.get("vol_rel"))
        cmf = f.get("cmf")
        rising = quad in ("leading", "improving")
        money_in = (cmf is not None and cmf > 0) or f.get("obv_above")
        if vr is None:
            ruido = "n/d"
        elif vr < 1.1:
            ruido = "🤫 bajo"
        elif vr > 1.5:
            ruido = "📢 alto"
        else:
            ruido = "normal"
        if rising and money_in:
            if vr is not None and vr < 1.15:
                vd, vcol, rank = "🤫 Joya escondida — sube sin ruido", "#2FD08A", 0
            elif vr is not None and vr > 1.5:
                vd, vcol, rank = "📢 Masificado — sube con ruido", "#F4B740", 2
            else:
                vd, vcol, rank = "🟢 Subiendo (ruido normal)", "#7FD8A0", 1
        elif quad in ("weakening", "lagging") and (cmf is not None and cmf < 0):
            vd, vcol, rank = "🩸 Cayendo / sale dinero", "#F4607A", 4
        else:
            vd, vcol, rank = "😴 Dormido / lateral", "#9FB0C8", 3
        rows.append({"sym": s, "quad": quad, "vol_rel": vr, "cmf": cmf,
                     "ruido": ruido, "vd": vd, "vcol": vcol, "rank": rank})
    rows.sort(key=lambda r: (r["rank"], (r["vol_rel"] if r["vol_rel"] is not None else 99)))
    return rows


def clima_dia(hace):
    """Etiqueta del día de la vela anómala: 0=hoy, 1=ayer, 2+ = hace Nd."""
    try:
        h = int(hace)
        return "hoy" if h == 0 else "ayer" if h == 1 else f"hace {h}d"
    except Exception:
        return ""


def dix_gauge(dix, w=250):
    """Termómetro del DIX en HTML puro (sin SVG: en el PDF los SVG se deforman). Escala fija 38-50%
    con las zonas que importan: rojo <41 (compra dark pool débil) · gris 41-43.5 (neutro) ·
    verde pálido 43.5-45.5 (normal-alta) · verde >=45.5 (acumulación oculta institucional).
    La barra gruesa de color = MEDIA 5d (la que manda); la línea fina blanca = el dato de HOY."""
    try:
        lo, hi = 38.0, 50.0
        pos = lambda v: max(0.0, min(99.2, (float(v) - lo) / (hi - lo) * 100.0))
        zonas = [(38.0, 41.0, "rgba(244,96,122,.22)"), (41.0, 43.5, "rgba(94,112,138,.18)"),
                 (43.5, 45.5, "rgba(127,216,160,.20)"), (45.5, 50.0, "rgba(47,208,138,.30)")]
        segs = "".join(f"<span style='display:block;position:absolute;left:{pos(a):.1f}%;width:{(pos(b) - pos(a)):.1f}%;top:0;bottom:0;background:{c}'></span>"
                       for a, b, c in zonas)
        ticks = "".join(f"<span style='display:block;position:absolute;left:{pos(v):.1f}%;top:0;bottom:0;width:1px;background:#2A3A52'></span>"
                        for v in (41.0, 43.5, 45.5))
        scol = dix.get("scol", "#9FB0C8")
        barra = (f"<span style='display:block;position:absolute;left:{pos(dix['last']):.1f}%;top:-2px;bottom:-2px;width:1.5px;background:#DCE6F5;opacity:.85' title='hoy: {dix['last']}%'></span>"
                 f"<span style='display:block;position:absolute;left:calc({pos(dix['m5']):.1f}% - 2px);top:-3px;bottom:-3px;width:5px;border-radius:2px;background:{scol};box-shadow:0 0 7px {scol}AA' title='media 5d: {dix['m5']}%'></span>")
        labs = "".join(f"<span style='position:absolute;left:{pos(v):.1f}%;transform:translateX(-50%)'>{t}</span>"
                       for v, t in ((41.0, "41"), (43.5, "43.5"), (45.5, "45.5")))
        return (f"<span style='display:inline-block;vertical-align:middle;width:{w}px;margin:0 10px 0 6px'>"
                f"<span style='display:block;position:relative;height:13px;border:1px solid #2A3A52;border-radius:7px;background:#0B1220;overflow:visible'>{segs}{ticks}{barra}</span>"
                f"<span style='display:block;position:relative;height:11px;font-size:8px;color:#5E708A'>{labs}"
                f"<span style='position:absolute;right:0'>zona 🌑≥45.5</span></span></span>")
    except Exception:
        return ""


def _spark(vals, w=70, h=20, color=None, sw=1.4):
    """Mini-linea (sparkline) auto-escalada. Si color es None, verde si termina arriba, rojo si abajo."""
    vals = [float(v) for v in vals if v is not None and v == v]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    n = len(vals)
    pts = " ".join(f"{(i/(n-1))*(w-2)+1:.1f},{h-1-((v-lo)/rng)*(h-2):.1f}" for i, v in enumerate(vals))
    c = color if color else ("#2FD08A" if vals[-1] >= vals[0] else "#F4607A")
    dot = f'<circle cx="{w-1:.1f}" cy="{h-1-((vals[-1]-lo)/rng)*(h-2):.1f}" r="1.6" fill="{c}"/>'
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" style="vertical-align:middle">'
            f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="{sw}"/>{dot}</svg>')


def build_html(df, rrg, alerts, breadth, risk, regime, buy, avoid, sources, fred, flow=None, bt=None,
               dd=None, dd_meta=None, plan=None, fx=None, long_src="", ai_text=None, leaders=None, leaders_n=0, bt2=None, heatmap=None, scores=None, probs=None, season=None, early=None, sector_breadth=None, meanrev=None, nq_close=None, fg_idx=None, spy_flow=None, watch=None, giro=None, desks=None, dix=None, suelo_pre=None, centinela=None, graduados=None, daily=None, ia_auto=None, tau=None, analogos=None, es_fut=None, options=None, despertares=None, cascada=None, momento=None, cobertura=None, mcc=None):
    rank = {"leading": 0, "weakening": 1, "improving": 2, "lagging": 3}
    ranked = sorted(rrg.items(), key=lambda kv: (rank[kv[1]["quad"]], -kv[1]["mom"]))
    last_date = df.index[-1].date()
    _dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    _mes = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    last_lbl = f"{_dias[last_date.weekday()]} {last_date.day} {_mes[last_date.month-1]}"
    stale_days = (dt.date.today() - last_date).days
    # ¿el ultimo dato es de MEDIA SEMANA? (el sistema decide con el cierre del VIERNES; lo demas es observacion)
    _hoy_wd = dt.date.today().weekday()   # 0=lun ... 4=vie
    media_semana = _hoy_wd < 4            # lun-jue = todavia no ha cerrado la semana
    src_summary = ", ".join(sorted(set(v for v in sources.values() if v not in ("—",))))

    # ranking enriquecido (sparkline RS + rendimiento relativo 4 semanas)
    def spark_svg(vals, color):
        if not vals or len(vals) < 2:
            return ""
        w, h = 78, 22
        lo, hi = min(vals), max(vals)
        rng = (hi - lo) or 1e-9
        pts = " ".join(f"{w*i/(len(vals)-1):.1f},{h-2-(h-4)*(v-lo)/rng:.1f}" for i, v in enumerate(vals))
        return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
                f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.5" '
                f'stroke-linejoin="round" stroke-linecap="round"/></svg>')

    def _rk_row(sym, d):
        c = QUAD[d["quad"]][1]
        rcol = "#2FD08A" if d["rel4"] >= 0 else "#F4607A"
        rarrow = "+" if d["rel4"] >= 0 else ""
        veh = LEV3X.get(sym, "—")
        veh_html = f"<span class='veh3'>{veh}</span>" if veh and veh != "—" else "<span class='veh3 off'>—</span>"
        return (
            f'<tr><td class="tk" title="{esc(sym)} · {esc(NAMES.get(sym,("","",""))[1])}"><b>{sym}</b><em>{esc(NAMES.get(sym,("","",""))[1])}</em></td>'
            f'<td><span class="dot" style="background:{c}"></span>{QUAD[d["quad"]][0]}</td>'
            f'<td class="r">{d["ratio"]:.1f}</td><td class="r">{d["mom"]:.1f}</td>'
            f'<td class="r" style="color:{rcol}">{rarrow}{d["rel4"]:.1f}%</td>'
            f'<td>{veh_html}</td>'
            f'<td class="spk">{spark_svg(d["spark"], c)}</td></tr>')
    rows = []
    for g in GRUPO_ORDEN:
        grp = [(sym, d) for sym, d in ranked if GRUPO.get(sym) == g]
        if not grp:
            continue
        rows.append(f'<tr><td class="rk-grp" colspan="7">{GRUPO_NOMBRE.get(g, g)}</td></tr>')
        for sym, d in grp:
            rows.append(_rk_row(sym, d))
    table = ('<table><tr><th>Activo</th><th>Cuadrante</th><th class="r">Fuerza</th>'
             '<th class="r">Impulso</th><th class="r">vs idx 4s</th><th>x3</th><th>Tendencia RS</th></tr>'
             + "".join(rows) + "</table>")

    # alertas
    if alerts:
        al = "".join(f'<div class="alert a-{k}"><span class="atk">{s}</span><span class="atx">{esc(t)}</span></div>'
                     for s, k, t in alerts)
    else:
        al = '<div class="note">Sin giros relevantes en la ultima lectura. El liderazgo se mantiene estable.</div>'

    # barras de impulso
    mom_sorted = sorted(rrg.items(), key=lambda kv: -kv[1]["mom"])
    maxabs = max([6.0] + [abs(d["mom"] - 100) for _, d in mom_sorted])
    bars = []
    for sym, d in mom_sorted:
        v = d["mom"] - 100
        pct = abs(v) / maxabs * 50
        c = QUAD[d["quad"]][1]
        left = 50 if v >= 0 else 50 - pct
        bars.append(f'<div class="bar-row"><span class="bar-lab">{sym}</span>'
                    f'<div class="bar-track"><div class="bar-mid"></div>'
                    f'<div class="bar" style="background:{c};width:{pct:.1f}%;left:{left:.1f}%"></div></div>'
                    f'<span class="bar-val" style="color:{c}">{d["mom"]:.1f}</span></div>')

    def meter(label, val, good=50):
        col = "#2FD08A" if val >= good else "#F4B740" if val >= good - 15 else "#F4607A"
        return (f'<div class="meter"><div class="meter-top"><span>{label}</span><b style="color:{col}">{val}%</b></div>'
                f'<div class="meter-track"><div class="meter-fill" style="width:{val}%;background:{col}"></div></div></div>')

    # macro
    sig_rows = "".join(f'<div class="kv"><span>{esc(k)}</span><b>{("+" if (v is not None and v>=0) else "")}{v if v is not None else "n/d"}{"%" if k!="Apetito riesgo" and v is not None else ""}</b></div>'
                       for k, v in regime["sig"].items())
    favor = "".join(f'<span class="tag good">{s}</span>' for s in regime["favor"])
    hurt = "".join(f'<span class="tag bad">{s}</span>' for s in regime["hurt"])
    buy_t = "".join(f'<span class="tag good">{s}</span>' for s in buy) or '<em style="color:#5E708A">Ninguno ahora.</em>'
    avoid_t = "".join(f'<span class="tag bad">{s}</span>' for s in avoid) or '<em style="color:#5E708A">Ninguno ahora.</em>'

    fred_html = ""
    if fred:
        fr = "".join(f'<div class="kv"><span>{esc(k)}</span><b>{v["last"]} ({"+" if v["chg"]>=0 else ""}{v["chg"]} 13s)</b></div>'
                     for k, v in fred.items())
        fred_html = f'<div class="panel"><h2>Macro FRED (13 semanas)</h2>{fr}</div>'

    risk_cls = risk["label"].replace("-", "")

    html = []
    html.append("<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>")
    html.append("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    html.append("<title>Rotacion - Smart-Money Flow Terminal</title>")
    html.append("<meta name='theme-color' content='#0A0E17'>")
    html.append("<link rel='manifest' href='manifest.webmanifest'>")
    html.append("<meta name='apple-mobile-web-app-capable' content='yes'>")
    html.append("<meta name='mobile-web-app-capable' content='yes'>")
    html.append("<meta name='apple-mobile-web-app-status-bar-style' content='black-translucent'>")
    html.append("<meta name='apple-mobile-web-app-title' content='Rotacion'>")
    html.append("<link rel='apple-touch-icon' href='icons/apple-touch-icon.png'>")
    html.append("<link rel='icon' href='icons/icon-192.png'>")
    html.append("<style>" + CSS + "</style></head><body>")
    html.append(
        "<header><div class='brand'><div><div class='title'>ROTACION</div>"
        "<div class='sub'>Smart-Money Flow Terminal</div></div></div>"
        f"<div class='status'><span class='pill RiskON' style='background:rgba(47,208,138,.12);color:#2FD08A'>DATOS REALES</span>"
        f"<span><b>Fuente</b>{esc(src_summary)}</span>"
        f"<span><b>Referencia</b>{BENCH}</span>"
        f"<span><b>Activos</b>{len(rrg)}</span>"
        f"<span><b>Ult. cierre</b>{last_lbl}</span>"
        + (f"<span class='pill' style='background:rgba(244,183,64,.15);color:#F4B740'>⚠ datos {stale_days}d atrás</span>" if stale_days >= 5 else "")
        + f"<span class='pill {risk_cls}'>{risk['label']}</span></div></header>")

    html.append("<main>")
    html.append(
        "<div class='viewtabs' style='grid-column:1/-1;position:sticky;top:0;z-index:60;background:var(--bg);padding:8px 0 6px;margin:-4px 0 6px;border-bottom:1px solid var(--line)'>"
        "<button class='viewtab mainview active' onclick=\"mainView('ctx',this)\" style='font-size:13px;padding:7px 16px'>📊 Contexto</button>"
        "<button class='viewtab mainview' onclick=\"mainView('op',this)\" style='font-size:13px;padding:7px 16px'>🎯 Operativa</button>"
        "<button class='viewtab mainview' onclick=\"mainView('vig',this)\" style='font-size:13px;padding:7px 16px'>📋 Vigilancia</button>"
        "<button class='viewtab mainview' onclick=\"mainView('bbg',this)\" style='font-size:13px;padding:7px 16px;border-color:#FFB00055;color:#FFB000'>🖥️ PRO</button>"
        "<button class='viewtab mainview' onclick=\"mainView('rds',this)\" style='font-size:13px;padding:7px 16px;border-color:#4CC2E055;color:#4CC2E0'>📣 Redes</button>"
        "<button class='viewtab mainview' onclick=\"mainView('cl',this)\" style='font-size:13px;padding:7px 16px'>🤖 Modo Claude</button>"
        "<button class='viewtab mainview' onclick=\"mainView('vd',this)\" style='font-size:13px;padding:7px 16px;border-color:#4CC2E055;color:#4CC2E0'>⚖️ Veredicto</button>"
        "<button class='viewtab mainview' onclick=\"mainView('news',this)\" style='font-size:13px;padding:7px 16px;border-color:#2FD08A55;color:#2FD08A'>📰 News</button>"
        "<span style='flex:1'></span>"
        "<button class='viewtab' onclick='descargarPDF()' title='Resumen semanal en PDF (imprimible / para Substack)' style='font-size:12px;padding:7px 12px;border-color:#5B8CFF55;color:#5B8CFF'>📄 Resumen PDF</button>"
        "<button class='viewtab' onclick='descargarJPG()' title='Resumen semanal en JPG (para X / Telegram; necesita internet)' style='font-size:12px;padding:7px 12px;border-color:#5B8CFF33'>🖼 JPG</button>"
        "</div>"
        "<div id='vista-ctx' style='display:contents'>")

    # ---- barra-resumen de rotacion ----
    entering = [s for s, d in rrg.items() if d["quad"] == "improving"]
    leaving = [s for s, d in rrg.items() if d["quad"] == "weakening"]
    leadnow = [s for s, d in rrg.items() if d["quad"] == "leading"]
    flow_col = "#2FD08A" if risk["score"] > 1.5 else "#F4607A" if risk["score"] < -1.5 else "#93A4BC"
    def scard(lab, big, big_col, sm):
        return (f"<div class='scard'><div class='lab'>{lab}</div>"
                f"<div class='big' style='color:{big_col}'>{big}</div><div class='sm'>{sm}</div></div>")
    html.append("<div class='summary full'>"
                + scard("Sesgo de flujo", risk["label"], flow_col, f"{'+' if risk['score']>=0 else ''}{risk['score']} ciclicos vs defensivos")
                + scard("Entrando a liderazgo", str(len(entering)), "#4CC2E0", (", ".join(entering[:4]) or "—"))
                + scard("Perdiendo liderazgo", str(len(leaving)), "#F4B740", (", ".join(leaving[:4]) or "—"))
                + scard("Regimen macro", regime["label"].split(" / ")[0], "#5B8CFF", f"{len(leadnow)} sectores liderando")
                + "</div>")
    verdict_pos = len(html)                       # aqui se insertara el "Veredicto de hoy" (se construye mas abajo)
    # ---- COBERTURA EUR/USD: en la PRIMERA PANTALLA (antes estaba enterrada en el desplegable "El
    #      porqué"). Operas en euros activos en dólares: la divisa te come o te regala rentabilidad
    #      sin que hagas nada, así que la lectura tiene que estar a la vista, no a tres clics. ----
    if fx:
        _eu_fuerte = fx["strong"]
        _fxcol = "#F4607A" if _eu_fuerte else "#2FD08A"
        _fxtrend = "Euro fuerte / dólar débil" if _eu_fuerte else "Dólar fuerte / euro débil"
        if _eu_fuerte and fx["pos"] > 60:
            _hedge = ("Euro fuerte y caro (cerca de máximos de 52s): es cuando <b>más conviene cubrir</b> tus "
                      "activos en dólares. Usa ETFs con clase <b>EUR hedged</b> o reduce exposición neta al dólar.")
            _hcol = "#F4607A"; _hlab = "Cobertura: ALTA prioridad"
        elif _eu_fuerte:
            _hedge = ("El euro sube pero no está caro: cobertura <b>moderada</b>. Puedes cubrir una parte e ir "
                      "ajustando si rompe la media de 200 al alza con fuerza.")
            _hcol = "#F4B740"; _hlab = "Cobertura: media"
        else:
            _hedge = ("Dólar fuerte: te da <b>viento a favor</b> al convertir a euros, así que cubrir es poco "
                      "urgente. Vigila un giro del euro (cruce de la media de 50 sobre la de 200).")
            _hcol = "#2FD08A"; _hlab = "Cobertura: baja prioridad"
        _sp = fx["spark"]
        _fx_spark = ""
        if len(_sp) > 2:
            _lo, _hi = min(_sp), max(_sp); _rg = (_hi - _lo) or 1e-9
            _pts = " ".join(f"{200*i/(len(_sp)-1):.1f},{34-2-(34-4)*(v-_lo)/_rg:.1f}" for i, v in enumerate(_sp))
            _fx_spark = (f"<svg width='100%' height='34' viewBox='0 0 200 34' preserveAspectRatio='none'>"
                         f"<polyline points='{_pts}' fill='none' stroke='{_fxcol}' stroke-width='1.5'/></svg>")
        html.append("<div class='panel full'><h2>💱 Cobertura EUR/USD — la divisa que te come (o te regala) rentabilidad</h2>"
                    f"<div style='background:{_hcol}18;border:1px solid {_hcol}55;border-radius:7px;padding:8px 11px;margin-bottom:8px'>"
                    f"<b style='color:{_hcol};font-size:13px'>{_hlab}</b>"
                    f"<div style='font-size:11.5px;color:#B9C6D8;margin-top:3px'>{_hedge}</div></div>"
                    + _fx_spark +
                    "<div style='display:flex;flex-wrap:wrap;gap:6px 20px;font-size:11.5px;margin-top:4px'>"
                    f"<span>EUR/USD <b style='color:{_fxcol};font-size:13px'>{fx['last']}</b></span>"
                    f"<span style='color:#8FA3C0'>medias 50/200 <b style='color:#CDE3FF'>{fx['ma50']} / {fx['ma200']}</b></span>"
                    f"<span style='color:#8FA3C0'>cruce <b style='color:#CDE3FF'>{fx['cross']}</b></span>"
                    f"<span style='color:#8FA3C0'>1m/3m/6m <b style='color:#CDE3FF'>{_pm(fx['roc1m'])} / {_pm(fx['roc3m'])} / {_pm(fx['roc6m'])}</b></span>"
                    f"<span style='color:#8FA3C0'>rango 52s <b style='color:#CDE3FF'>{fx['lo52']}–{fx['hi52']} ({fx['pos']}%)</b></span>"
                    f"<span style='color:#8FA3C0'>tendencia <b style='color:{_fxcol}'>{_fxtrend}</b></span></div>"
                    "<div class='note' style='color:#5E708A;margin-top:7px'>La dirección del cambio no se puede predecir; esto es la "
                    "lectura técnica actual y su implicación para tu cartera en dólares, no una previsión. No es asesoramiento.</div></div>")
    # ---- MAPA DE LA CASCADA DEL CAPEX DE IA ----
    if cascada and cascada.get("filas"):
        _cAMB, _cGRN, _cRED, _cGRY, _cCYN = "#FFB000", "#00E676", "#FF5252", "#8A96A8", "#4CC2E0"
        _cf = cascada["filas"]
        _maxabs = max([abs(f["r4"]) for f in _cf if f["r4"] is not None] or [1]) or 1
        _rows = ""
        for f in _cf:
            _ql, _qc = QUAD.get(f["quad"], (f["quad"], "#888"))[0], QUAD.get(f["quad"], ("", "#888"))[1]
            _es_lider = (f["key"] == cascada["lider"])
            _cmfc = _cGRY if f["cmf"] is None else (_cGRN if f["cmf"] > 0.05 else _cRED if f["cmf"] < -0.05 else _cGRY)
            _cmft = "n/d" if f["cmf"] is None else f"{f['cmf']:+.2f}"
            _w = int(round(100 * abs(f["r4"] or 0) / _maxabs))
            _bc = _cGRN if (f["r4"] or 0) >= 0 else _cRED
            _bar = (f"<div style='background:#0C1220;border-radius:3px;height:7px;width:100%;overflow:hidden'>"
                    f"<div style='background:{_bc};height:7px;width:{_w}%'></div></div>")
            _rows += (f"<tr style='{'background:#12203A' if _es_lider else ''}'>"
                      f"<td style='padding:5px 6px'><b style='color:{_cCYN};font-size:12px'>{f['orden']}. {esc(f['corto'])}</b>"
                      + ("<span style='color:#F4B740;font-size:9px;margin-left:5px'>◄ LIDERA</span>" if _es_lider else "")
                      + f"<div style='font-size:10px;color:#7A8AA3;margin-top:1px'>{esc(', '.join(f['miembros']))}</div></td>"
                      f"<td style='color:{_qc};font-size:11px'>{_ql}</td>"
                      f"<td class='r' style='font-size:11px'>{f['ratio']}</td>"
                      f"<td class='r' style='font-size:11px;color:{_cGRN if f['dmom'] > 0 else _cRED}'>{f['dmom']:+.2f}</td>"
                      f"<td class='r' style='font-size:11px'>{('%+.1f%%' % f['r4']) if f['r4'] is not None else '—'}</td>"
                      f"<td style='width:22%'>{_bar}</td>"
                      f"<td class='r' style='color:{_cmfc};font-size:11px'>{_cmft}</td></tr>")
        _sp = cascada.get("spread")
        _spc = _cGRN if (_sp or 0) > 0.5 else (_cAMB if (_sp or 0) > -0.5 else "#8FA3C0")
        _cir = cascada.get("circulo")
        _cirhtml = ""
        if _cir:
            _cc = {"bueno": _cGRN, "malo": _cRED, "neutro": "#8FA3C0"}.get(_cir["nivel"], "#8FA3C0")
            _cirhtml = (f"<div style='background:{_cc}18;border:1px solid {_cc}55;border-radius:7px;padding:7px 10px;margin:7px 0;font-size:12px'>"
                        f"⭕ <b>El círculo:</b> <span style='color:{_cc}'>{esc(_cir['estado'])}</span>"
                        f"<div style='font-size:10.5px;color:#7A8AA3;margin-top:3px'>fuerza del retorno (C5) {_cir['retorno']} vs "
                        f"media de la cadena (C1–C4) {_cir['cadena']} → diferencia <b style='color:{_cc}'>{_cir['gap']:+.1f}</b>"
                        + (f" · quien paga (C0) {_cir['paga']}" if _cir.get("paga") is not None else "") + "</div></div>")
        html.append("<div class='panel full'><h2>🔗 Cascada del capex de IA — ¿en qué eslabón está el dinero?</h2>"
                    "<div class='note'>Un euro de capex de un hiperescalador <b>no llega a todos a la vez</b>: primero paga el chip, "
                    "luego la obra y la red, luego la electricidad, y al final la materia prima. Y el <b>círculo se cierra</b> con quien lo paga (C0, los hiperescaladores) y quien tiene que devolverlo en ingresos (C5, nube y software). Aquí ves por qué eslabón va el dinero "
                    "<b>hoy</b> y hacia dónde se mueve, en vez de suponerlo. Todo el mundo dice «infraestructura»; lo interesante es "
                    "que la <b>beta de verdad está al final de la cadena</b> (las mineras multiplican porque su coste no sube cuando "
                    "sube el metal: apalancamiento operativo).</div>"
                    f"<div style='background:{_spc}18;border:1px solid {_spc}55;border-radius:7px;padding:7px 10px;margin:7px 0;font-size:12px'>"
                    f"Lidera ahora: <b style='color:{_cCYN}'>{esc(cascada['lider_corto'])}</b> · "
                    f"<b style='color:{_spc}'>{esc(cascada['sentido'])}</b>"
                    + (f" <span style='color:#7A8AA3;font-size:10px'>(impulso abajo − arriba: {_sp:+.2f})</span>" if _sp is not None else "")
                    + "</div>" + _cirhtml +
                    "<div class='scrollx'><table style='width:100%;font-size:11.5px;min-width:520px'>"
                    "<tr style='color:#777;font-size:10px'><td>ESLABÓN</td><td>CUADRANTE</td><td class='r'>FUERZA</td>"
                    "<td class='r'>Δ IMPULSO</td><td class='r'>4 SEM</td><td>·</td><td class='r'>FLUJO</td></tr>"
                    + _rows + "</table></div>"
                    "<div style='font-size:10px;color:#666;margin-top:7px'>⚠ Esto es <b>contexto, no señal</b>: los eslabones son "
                    "cestas de solo lectura (no entran en scoring ni cartera). La cascada <b>no es limpia ni ordenada</b> — los eslabones "
                    "se solapan y a veces van al revés; y si el capex se recorta, lo que más cae es justo el final de la cadena, que es "
                    "donde está la beta. Falta el eslabón de <b>equipos</b> (ASML/LRCX/AMAT): no hay ETF de equipos semi en tu universo "
                    "UCITS, habría que montarlo con acciones sueltas como el sintético de FIW. No es asesoramiento.</div></div>")
    # ---- RELOJ DEL CICLO ECONOMICO ----
    try:
        cyc = compute_cycle_phase(rrg, scores or [])
        cur = cyc.get("actual")
        if cur:
            lit_txt = ", ".join(cur["lit"]) if cur["lit"] else "—"
            html.append("<div class='panel full'><h2>🕒 Reloj del ciclo económico — ¿en qué punto estamos?</h2>"
                        "<div class='note'>Dónde está el dinero hoy, traducido al ciclo económico (modelo de rotación sectorial de Fidelity/Stovall). "
                        "La aguja marca la fase cuyos sectores están <b>recibiendo dinero ahora</b> (en Líder o Mejorando). El ciclo gira en el sentido del reloj: "
                        "Recuperación → Expansión → Sobrecalentamiento → Recesión → y vuelta a empezar.</div>"
                        + cycle_clock_html(cyc)
                        + f"<div style='text-align:center;margin-top:6px'><b style='color:{cur['col']};font-size:15px'>{cur['lbl']}</b> "
                          f"<span style='color:#9FB0C8'>· {cur['sub']}</span></div>"
                        + f"<div class='note' style='margin-top:8px'>{cur['desc']}<br>"
                          f"<b>Con dinero entrando ahora ({cur['n']}/{cur['tot']}):</b> <span style='color:{cur['col']}'>{lit_txt}</span></div>"
                        "<div class='note' style='margin-top:8px;color:#5E708A'>⚠ Los ciclos son <b>lentos</b> (cada fase dura 1-4 años) y en tiempo real son <b>confusos</b> — "
                        "distinguir mitad de ciclo de final de ciclo es justo donde más se equivoca todo el mundo. Es un <b>mapa orientativo, no una predicción</b>, "
                        "y va con la rotación del mercado, no con el calendario. El flujo manda. No es asesoramiento.</div></div>")
    except Exception:
        pass
    # ---- RADAR DE ATENCION (ruido vs silencio) ----
    try:
        radar = compute_attention_radar(rrg, flow)
        if radar:
            gems = [r for r in radar if r["rank"] == 0]
            shown = [r for r in radar if r["rank"] <= 2][:14]
            rrows = ""
            for r in shown:
                nm = NAMES.get(r["sym"], (r["sym"], r["sym"], ""))[1]
                vr = r["vol_rel"]
                vrtxt = (f"{vr:.2f}×" if vr is not None else "n/d")
                cuad = QUAD.get(r["quad"], (r["quad"], ""))[0]
                # insignia del clima del dia: 🟡 climax (vela anomala al alza, ya lo ve todo el mundo) · 🟣 capitulacion
                _fcl = (flow.get(r["sym"], {}) or {})
                _r1v, _zdv = _fcl.get("ret1d") or 0, _fcl.get("zday") or 0
                _diav = clima_dia(_fcl.get("clima_hace") or 0)
                clbadge = ""
                if _fcl.get("clima") == "climax":
                    clbadge = (f" <span style='color:#F4B740;font-size:9px;border:1px dashed #F4B74088;border-radius:8px;padding:0 5px;white-space:nowrap' "
                               f"title='CLÍMAX {_diav}: {_r1v:+.1f}% en un día (z {_zdv:+.1f}) — la vela que ya ve todo el mundo; posible agotamiento'>🟡 clímax {_diav}</span>")
                elif _fcl.get("clima") == "capitulacion":
                    clbadge = (f" <span style='color:#B980FF;font-size:9px;border:1px dashed #B980FF88;border-radius:8px;padding:0 5px;white-space:nowrap' "
                               f"title='CAPITULACIÓN {_diav}: {_r1v:+.1f}% en un día (z {_zdv:+.1f}) — pánico de un día; vigilar suelo si el flujo frena'>🟣 capitulación {_diav}</span>")
                if _fcl.get("acum_ext"):
                    _nvr = _fcl.get("noct20") or 0
                    clbadge += (f" <span style='color:#4CC2E0;font-size:9px;border:1px dashed #4CC2E088;border-radius:8px;padding:0 5px;white-space:nowrap' "
                                f"title='ACUMULACIÓN EXTRANJERA: gap nocturno {_nvr:+.1f}% en 20 sesiones con CMF≤0 — la compra ocurre en su bolsa local; el CMF americano no la ve'>🌏 {_nvr:+.1f}%</span>")
                rrows += (f"<tr><td class='se-l'><b>{r['sym']}</b> <span style='color:var(--txt3);font-size:11px'>{esc(nm)}</span>{clbadge}</td>"
                          f"<td class='r' style='font-size:11px'>{esc(cuad)}</td>"
                          f"<td class='r' style='white-space:nowrap'>{esc(r['ruido'])} <span style='color:#5E708A;font-size:10px'>{vrtxt}</span></td>"
                          f"<td class='r' style='color:{r['vcol']};white-space:nowrap;font-size:11px'>{esc(r['vd'])}</td></tr>")
            gem_line = ", ".join(f"<b>{r['sym']}</b>" for r in gems) if gems else "ninguna clara hoy"
            html.append("<div class='panel full'><h2>📡 Radar de atención — ¿quién sube en silencio?</h2>"
                        "<div class='note'>Tu idea: lo que sube <b>sin ruido</b> suele ser mejor que lo que está en boca de todos (semis, «picos y palas»…). "
                        "Cruzo la <b>tendencia</b> (RRG) con el <b>volumen relativo</b> (volumen medio de 5 sesiones vs su media de 20) como medida de atención. "
                        "Sube con volumen <b>normal/bajo</b> = aún no se ha enterado nadie (🤫 joya escondida). Sube con volumen <b>disparado</b> = ya está la masa dentro (📢 masificado, ojo al techo).</div>"
                        + (f"<div class='note' style='margin-top:6px;color:#2FD08A'>🤫 <b>Subiendo en silencio ahora:</b> {gem_line}</div>")
                        + "<div class='scrollx'><table class='se'><tr><th class='se-l'>sector / tema</th><th class='r'>cuadrante</th><th class='r'>ruido (vol.)</th><th class='r'>veredicto</th></tr>"
                        + rrows + "</table></div>"
                        "<div class='note' style='margin-top:8px;color:#5E708A'>⚠ El volumen es proxy de atención del <b>mercado</b>, no de la prensa — casi siempre coinciden, pero no es idéntico. "
                        "Y poco volumen no garantiza subida: dice que aún no está masificado, no que vaya a subir. Cruza con su flujo y su gráfico. No es asesoramiento.</div></div>")
    except Exception:
        pass
    # ---- 🛰️ CENTINELA: el reloj de régimen que une sintéticos + flujo + durmientes + DIX ----
    if centinela:
        try:
            cn = centinela
            _fases = ["RISK-ON", "DISTRIBUCION", "LIQUIDEZ", "ACECHO", "REENTRADA"]
            _fcol = {"RISK-ON": "#2FD08A", "DISTRIBUCION": "#F4B740", "LIQUIDEZ": "#F4607A",
                     "ACECHO": "#4CC2E0", "REENTRADA": "#2FD08A", "TRANSICION": "#9FB0C8"}
            _flbl = {"DISTRIBUCION": "DISTRIBUCIÓN", "TRANSICION": "TRANSICIÓN"}
            tira = "<div style='display:flex;gap:6px;flex-wrap:wrap;margin:10px 0'>"
            for fph in _fases:
                _on = (fph == cn["estado"])
                _c = _fcol[fph]
                tira += (f"<div style='flex:1;min-width:90px;text-align:center;padding:7px 4px;border-radius:7px;"
                         f"border:1px solid {_c}{'' if _on else '33'};"
                         + (f"background:{_c}22;color:{_c};font-weight:700;box-shadow:0 0 12px {_c}44" if _on else "color:#5E708A;background:transparent")
                         + f";font-size:11px'>{_flbl.get(fph, fph)}</div>")
            tira += "</div>"
            if cn["estado"] == "TRANSICION":
                tira += "<div style='font-size:11px;color:#9FB0C8;margin:-4px 0 8px'>⚪ Ahora mismo: <b>TRANSICIÓN</b> — fuera de las 5 fases del ciclo, zona gris.</div>"
            conf_badge = ("<span style='color:#2FD08A;font-size:11px;border:1px solid #2FD08A55;border-radius:5px;padding:2px 7px'>✓ CONFIRMADO (2+ cierres)</span>"
                          if cn["confirmado"] else
                          f"<span style='color:#F4B740;font-size:11px;border:1px solid #F4B74055;border-radius:5px;padding:2px 7px'>⧗ NUEVO — un cierre es ruido, confirma el próximo viernes</span>")
            _sc = "#2FD08A" if cn["spread"] > 0 else "#F4607A"
            gauge = (f"<div style='display:flex;gap:18px;flex-wrap:wrap;align-items:center;margin:6px 0'>"
                     f"<div><span style='color:#8FA3C0;font-size:11px'>SPREAD alta beta − defensivos</span> "
                     f"<b style='color:{_sc};font-size:17px'>{cn['spread']:+.2f}</b> "
                     f"<span style='color:#5E708A;font-size:10px'>pts RRG</span> {_spark(cn['spread_spark'], w=110, h=22)}</div>"
                     f"<div style='font-size:11px;color:#8FA3C0'>Δ3 semanas <b style='color:{('#2FD08A' if cn['d3'] >= 0 else '#F4607A')}'>{cn['d3']:+.2f}</b>"
                     f" · {cn['lado']} sem al mismo lado" + (f" · {cn['cayendo']} cayendo" if cn['cayendo'] >= 2 else "") + "</div></div>")
            _qs2 = {"leading": ("Líder", "#2FD08A"), "improving": ("Mejorando", "#4CC2E0"),
                    "weakening": ("Debilitándose", "#F4B740"), "lagging": ("Rezagado", "#F4607A")}
            confs = "<div style='display:flex;gap:7px;flex-wrap:wrap;margin:8px 0'>"
            for k in ("S-EXPLOSIVO", "S-DUROS", "S-DEFENSA", "S-REFUGIO", "S-CREDITO", "S-AMPLITUD"):
                qv = (cn.get("quads") or {}).get(k)
                if not qv:
                    continue
                _t, _c = _qs2.get(qv, ("—", "#5E708A"))
                confs += (f"<span style='font-size:10.5px;border:1px solid #1E2A3D;border-radius:6px;padding:3px 8px;background:rgba(255,255,255,.02)'>"
                          f"<b style='color:#DCE6F5'>{k.replace('S-', '')}</b> <span style='color:{_c}'>{_t}</span></span>")
            if cn.get("cmf_beta") is not None:
                _cc = "#2FD08A" if cn["cmf_beta"] > 0 else "#F4607A"
                confs += (f"<span style='font-size:10.5px;border:1px solid #1E2A3D;border-radius:6px;padding:3px 8px'>"
                          f"<b style='color:#DCE6F5'>CMF explosivos</b> <span style='color:{_cc}'>{cn['cmf_beta']:+.2f}</span>"
                          + (f" <span style='color:#5E708A'>({cn['beta_pos']}% en +)</span>" if cn.get("beta_pos") is not None else "") + "</span>")
            if cn.get("hyg_tlt") is not None:
                _hc = "#2FD08A" if cn["hyg_tlt"] > 0 else "#F4607A"
                confs += (f"<span style='font-size:10.5px;border:1px solid #1E2A3D;border-radius:6px;padding:3px 8px' "
                          f"title='HYG/TLT subiendo = apetito por el riesgo intacto; cayendo = el crédito huye antes que la bolsa'>"
                          f"<b style='color:#DCE6F5'>HYG/TLT 4s</b> <span style='color:{_hc}'>{cn['hyg_tlt']:+.1f}%</span></span>")
            confs += "</div>"
            dixh = ""
            if dix:
                _gexs = ""
                if dix.get("gex") is not None:
                    _gc = "#F4B740" if dix["gex"] < 0 else "#9FB0C8"
                    _gt = "dealers amplifican (gasolina para el giro)" if dix["gex"] < 0 else "dealers amortiguan"
                    _gexs = f" · GEX <b style='color:{_gc}'>{dix['gex']:,.0f}</b> <span style='color:#5E708A'>({_gt})</span>".replace(",", ".")
                dixh = (f"<div style='margin:8px 0;padding:8px 10px;background:rgba(76,194,224,.05);border:1px solid #4CC2E033;border-radius:8px;font-size:11.5px'>"
                        f"<b style='color:#4CC2E0'>🌑 DARK POOLS (DIX)</b> · hoy <b style='color:{dix['scol']}'>{dix['last']}%</b>"
                        f" · media 5d <b style='color:{dix['scol']}'>{dix['m5']}%</b>"
                        f" <span style='color:#5E708A'>(percentil {dix['pct']} del año)</span>{dix_gauge(dix)}"
                        f"→ <span style='color:{dix['scol']}'>{esc(dix['senal'])}</span>{_gexs}"
                        f"<div style='color:#5E708A;font-size:10px;margin-top:3px'>Compra institucional en mercados oscuros sobre el S&amp;P (dato de MERCADO, no por sector; 1 día de retraso, fuente SqueezeMetrics). "
                        f"En el termómetro: la <b>barra gruesa de color</b> es la media 5d (la que manda), la línea fina blanca es el dato de hoy. "
                        f"DIX ≥45.5 en plena caída = acumulación oculta a escala de índice: el mismo patrón del durmiente pero del mercado entero. Cotéjalo, no lo obedezcas: <b>el flujo del terminal manda</b>; si discrepan, se señala la divergencia.</div></div>")
            elif DIX_ON:
                dixh = "<div style='font-size:10px;color:#5E708A;margin:6px 0'>🌑 DIX (dark pools): sin respuesta de SqueezeMetrics en esta ejecución — el reloj funciona igual sin él.</div>"
            timeline = ""
            if cn.get("cambios"):
                _tl = " → ".join(f"<span style='color:{_fcol.get(c['estado'], '#9FB0C8')}'>{_flbl.get(c['estado'], c['estado'])}</span> <span style='color:#5E708A;font-size:9px'>{c['date'][5:]}</span>"
                                 for c in cn["cambios"])
                timeline = f"<div style='font-size:10.5px;color:#8FA3C0;margin-top:8px'>Historial de régimen: {_tl} <span style='color:#5E708A'>(guardado en <code>centinela_estado.json</code>)</span></div>"
            html.append("<div class='panel full'><h2>🛰️ CENTINELA — el reloj de régimen: dónde está el dinero y qué toca hacer</h2>"
                        f"<div style='display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:2px'>"
                        f"<span style='font-size:22px;font-weight:800;color:{cn['col']};letter-spacing:1px'>{_flbl.get(cn['estado'], cn['estado'])}</span>{conf_badge}</div>"
                        + tira + gauge + confs
                        + f"<div style='margin:8px 0;padding:10px 12px;background:rgba(255,255,255,.03);border-left:3px solid {cn['col']};border-radius:0 8px 8px 0;font-size:12.5px;color:#DCE6F5'><b style='color:{cn['col']}'>QUÉ HACER:</b> {cn['que']}</div>"
                        + f"<div style='font-size:11px;color:#F4B740'>⚠ INVALIDACIÓN: {cn['inval']}</div>"
                        + dixh + timeline +
                        "<div class='note' style='margin-top:8px'>El ciclo completo que opera el sistema: <b style='color:#2FD08A'>RISK-ON</b> (invertido en alta beta) → "
                        "<b style='color:#F4B740'>DISTRIBUCIÓN</b> (los defensivos mejoran = aviso: stops arriba, nada nuevo) → "
                        "<b style='color:#F4607A'>LIQUIDEZ</b> (liderazgo defensivo = a caja; los defensivos son <b>termómetro, no destino</b>: se mueven tan poco que con capital pequeño rotar hacia ellos no compensa) → "
                        "<b style='color:#4CC2E0'>ACECHO</b> (en caja, vigilando los pre-despertares de los 💥 explosivos y el DIX) → "
                        "<b style='color:#2FD08A'>REENTRADA</b> (despiertan: desplegar por tramos, desde abajo). "
                        "Todo con la regla de siempre: se observa entre semana, se <b>ejecuta con el cierre del viernes</b>, y un cierre no confirma — dos sí. No es asesoramiento.</div></div>")
        except Exception:
            pass
    # ---- 💥 COCKPIT ALTA BETA: la fusion — una fila por sector explosivo, ordenada por cercania a la ignicion ----
    try:
        _ckp = compute_cockpit_beta(df, rrg, flow, suelo=suelo_pre, graduados=graduados, desks=desks, giro=giro)
        if _ckp:
            FASE_TXT = {"PRE-DESPERTAR": ("🌱 PRE-DESPERTAR", "#4CC2E0"), "DESPERTANDO": ("🌅 DESPERTANDO", "#2FD08A"),
                        "GRADUADO": ("🎓 GRADUADO", "#7BD88F"), "ACUMULACION": ("🧲 ACUMULACIÓN", "#7BD88F"),
                        "CAPITULACION": ("🟣 CAPITULACIÓN", "#B980FF"), "CASTIGADO": ("⛏ CASTIGADO", "#9FB0C8"),
                        "DORMIDO": ("😴 DORMIDO", "#8FA3C0"), "SANGRA": ("🩸 SANGRA", "#F4607A"),
                        "EN MARCHA": ("🏃 EN MARCHA", "#8FA3C0"), "NEUTRO": ("· neutro", "#5E708A")}
            kfilas = ""
            for r in _ckp:
                ft, fc = FASE_TXT.get(r["fase"], (r["fase"], "#9FB0C8"))
                _scw = max(3, int(r["sc"]))
                _sccol = "#2FD08A" if r["sc"] >= 60 else "#F4B740" if r["sc"] >= 35 else "#5E708A"
                _scbar = (f"<span style='display:inline-block;vertical-align:middle;width:56px;height:7px;background:#141E30;border-radius:4px;overflow:hidden;margin-right:5px'>"
                          f"<span style='display:block;width:{_scw}%;height:100%;background:{_sccol}'></span></span>"
                          f"<b style='color:{_sccol}'>{r['sc']}</b>")
                _fl = (f"{r['cmf']:+.2f}" if r.get("cmf") is not None else "n/d")
                if r.get("mejora"):
                    _fl += " <span style='color:#7BD88F' title='CMF mejorando 3 tramos: dejó de empeorar'>↗3t</span>"
                if r.get("aext"):
                    _nv = r.get("noct") or 0
                    _fl += f" <span style='color:#4CC2E0' title='acumulación extranjera: gap nocturno {_nv:+.1f}% en 20 sesiones'>🌏</span>"
                _pt = ("●" * int(r.get("pre") or 0) + "○" * (4 - int(r.get("pre") or 0)))
                _mesa = (f"<span title='probabilidad histórica del cubo actual en su mesa de póker (PRO)'>{r['desk_prob']}%</span>" if r.get("desk_prob") is not None else "—")
                kfilas += (f"<tr><td class='se-l'><b>{r['sym']}</b> <span style='color:#FF8C42;font-size:9px'>{esc(r['tipo'])}</span></td>"
                           f"<td class='se-l' style='color:{fc};font-weight:700;font-size:11px;white-space:nowrap'>{ft}</td>"
                           f"<td class='r' style='white-space:nowrap'>{_scbar}</td>"
                           f"<td class='r'>{r['dd52']:+.0f}%</td>"
                           f"<td class='r' style='font-size:11px;white-space:nowrap'>{_fl}</td>"
                           f"<td class='r' style='color:#4CC2E0;letter-spacing:1px'>{_pt}</td>"
                           f"<td class='r'>{_mesa}</td>"
                           f"<td class='se-l' style='color:{r['acol']};font-size:11px'>{esc(r['acc'])}</td></tr>")
            html.append("<div class='panel full'><h2>💥 COCKPIT ALTA BETA — el pipeline del cazador, todo fusionado</h2>"
                        "<div class='note' style='margin-bottom:6px'>Tu tesis hecha tabla: <b>con poco capital, el dinero está en entrar ABAJO en alta beta</b> — no en rotar defensivos que no se mueven. "
                        "Una fila por sector explosivo (chips, biotech, ARKK, China, metales/mineras, uranio, solar, litio, petróleo E&P, espacio, bitcoin…) fusionando TODO lo que el terminal sabe: "
                        "suelo, patrón pre-despertar (●●●○), capitulación, flujo (CMF, mejora por tramos ↗3t, 🌏 nocturno), giro, graduación y la probabilidad del cubo de su mesa de póker. "
                        "Ordenada por <b>cercanía a la ignición</b>: arriba lo que está a punto, abajo lo que sangra o ya corre. El score de ANTICIPACIÓN (0-100) es un <b>ranking interno, no una probabilidad</b>. "
                        "La ejecución no cambia: se observa entre semana, se dispara con el <b>cierre del viernes</b> y con flujo que al menos haya dejado de salir. No es asesoramiento.</div>"
                        "<table class='sectbl'><tr><th class='se-l'>SECTOR</th><th class='se-l'>FASE</th><th class='r'>ANTICIPACIÓN</th>"
                        "<th class='r'>VS MÁX 52S</th><th class='r'>FLUJO</th><th class='r' title='huellas del patrón oro/BTC/mineras (0-4)'>PATRÓN</th>"
                        "<th class='r' title='probabilidad histórica del cubo actual en su mesa de póker (pestaña PRO)'>MESA</th><th class='se-l'>QUÉ TOCA</th></tr>"
                        + kfilas + "</table></div>")
    except Exception:
        pass
    # ---- 😴 DURMIENTES: suelo + silencio + giro + contraria 0/3, TODO EN UN PANEL ----
    suelo = suelo_pre
    contra_sigs, contra_led = [], None
    if suelo is None:
        try:
            suelo = compute_suelo(df, rrg, scores, flow, meanrev)
        except Exception:
            suelo = None
    if CONTRARIAN_ON:
        try:
            contra_sigs = compute_contrarian(rrg, scores, flow)
            _px = {k: float(v) for k, v in df.iloc[-1].to_dict().items() if v == v}
            contra_led = update_contrarian_ledger(contra_sigs, _px, str(df.index[-1].date()), df)
        except Exception:
            contra_sigs, contra_led = [], None
    try:
        stats = (contra_led or {}).get("stats")
        if stats and stats["n"] >= 20 and stats.get("kelly4") is not None:
            size_pct = min(stats["kelly4"], 3.0)
            size_src = f"¼ de Kelly empírico con tus {stats['n']} señales fuera-de-muestra"
        else:
            size_pct = CONTRARIAN_SIZE_PCT
            size_src = "tamaño de prueba fijo hasta acumular ≥20 señales fuera-de-muestra"
        if suelo:
            _c_act = {c["sym"] for c in (contra_sigs or [])}
            sfilas = ""
            for r in suelo:
                nm = NAMES.get(r["sym"], (r["sym"], r["sym"], ""))[1]
                _fase = r.get("fase") or ""
                if r["sangra"]:
                    verd, vcol = "⚠ aún sangra — sin prisa", "#F4607A"
                elif r["despertando"] and r["sil"] >= 2:
                    verd, vcol = "🌅 DESPERTANDO EN SILENCIO", "#2FD08A"
                elif r["despertando"]:
                    verd, vcol = "🌅 despertando", "#2FD08A"
                elif _fase == "PRE-DESPERTAR":
                    verd, vcol = "🌱 PRE-DESPERTAR — patrón oro/BTC", "#4CC2E0"
                elif _fase == "ACUMULACION":
                    verd, vcol = "🧲 acumulando en silencio", "#7FD8A0"
                elif r["pts"] >= 8:
                    verd, vcol = "suelo armado — falta el giro", "#F4B740"
                else:
                    verd, vcol = "dormido — vigilar", "#9FB0C8"
                scol = "#2FD08A" if r["pts"] >= 8 else "#F4B740" if r["pts"] >= 6 else "#9FB0C8"
                cbadge = (" <span style='color:#7BD88F;font-size:10px;border:1px solid #7BD88F55;border-radius:4px;padding:1px 4px' "
                          "title='dispara HOY la señal contraria 0/3: tamaño de manga abajo'>0/3 ACTIVA</span>"
                          if r["sym"] in _c_act else "")
                hia = f"−{100 - r['hi52']:.0f}%" if r["hi52"] is not None else "—"
                _silc = "#2FD08A" if r["sil"] >= 3 else "#F4B740" if r["sil"] == 2 else "#9FB0C8"
                sila = (f"<span style='color:{_silc}'>{'🤫' * max(r['sil'], 0)}</span> {r['vr']:.2f}×" if r["vr"] is not None else "—")
                gira = (f"<b style='color:#7BD88F'>{r['vert']:.1f}×</b>" if (r.get("vert") and r["dmom"] and r["dmom"] >= 1.5)
                        else (f"{r['dmom']:+.1f}" if r.get("dmom") is not None else "—"))
                qta = (f"{r['quieto']:+.1f}%" if r.get("quieto") is not None else "—")
                fla = ("<span style='color:#2FD08A'>entra</span>" if (r["cmf"] or 0) > 0.05 else
                       "<span style='color:#F4607A'>sale</span>" if (r["cmf"] or 0) < -0.05 else
                       "<span style='color:#9FB0C8'>plano</span>") if r["cmf"] is not None else "—"
                n3a = ("<b style='color:#7BD88F'>0/3</b>" if r["n3"] == 0 else f"{r['n3']}/3" if r["n3"] is not None else "—")
                # patrón PRE-DESPERTAR: cuántas de las 4 huellas de acumulación están presentes
                _pre = r.get("pre") or 0
                _prc = "#4CC2E0" if _pre >= 3 else "#7FD8A0" if _pre == 2 else "#5E708A"
                prea = (f"<span style='color:{_prc};letter-spacing:1px' title='Huellas del patrón que clavó oro/BTC/mineras: "
                        f"divergencia CMF positiva · OBV con mínimos crecientes · volatilidad comprimida · base de mínimos crecientes'>"
                        + "●" * _pre + "○" * (4 - _pre) + "</span>")
                # marca de sector EXPLOSIVO: los que al rebotar se mueven mas (donde tener liquidez lista)
                expl = ""
                if r["sym"] in SECTORES_EXPLOSIVOS:
                    _et = EXPLOSIVO_TIPO.get(r["sym"], "")
                    expl = (f" <span style='color:#FF8C42;font-size:9px;border:1px solid #FF8C4255;border-radius:3px;padding:0 4px;white-space:nowrap' "
                            f"title='Sector de beta alta: cuando rebota, se mueve mucho más que el mercado. Aquí es donde conviene tener liquidez preparada para entrar en el giro.'>💥 {esc(_et)}</span>")
                # insignia del clima: 🟣 capitulacion (panico de un dia = empieza la vigilancia del suelo) · 🟡 climax
                _fcd = (flow.get(r["sym"], {}) or {})
                _r1d, _zdd = _fcd.get("ret1d") or 0, _fcd.get("zday") or 0
                _diad = clima_dia(_fcd.get("clima_hace") or 0)
                if _fcd.get("clima") == "capitulacion":
                    expl += (f" <span style='color:#B980FF;font-size:9px;border:1px dashed #B980FF88;border-radius:8px;padding:0 5px;white-space:nowrap' "
                             f"title='CAPITULACIÓN ({_diad}): {_r1d:+.1f}% en un día (z {_zdd:+.1f}). El pánico de un día es donde la gente se olvida del ETF — a menudo cerca del suelo, pero solo cuenta cuando el flujo deje de salir.'>🟣</span>")
                elif _fcd.get("clima") == "climax":
                    expl += (f" <span style='color:#F4B740;font-size:9px;border:1px dashed #F4B74088;border-radius:8px;padding:0 5px;white-space:nowrap' "
                             f"title='CLÍMAX ({_diad}): {_r1d:+.1f}% en un día (z {_zdd:+.1f}). Ojo: si despierta con una vela que ve todo el mundo, no persigas — espera el cierre del viernes.'>🟡</span>")
                if _fcd.get("acum_ext"):
                    _nvd = _fcd.get("noct20") or 0
                    expl += (f" <span style='color:#4CC2E0;font-size:9px;border:1px dashed #4CC2E088;border-radius:8px;padding:0 5px;white-space:nowrap' "
                             f"title='ACUMULACIÓN EXTRANJERA: gap nocturno {_nvd:+.1f}% en 20 sesiones con CMF≤0 — aquí el «sangra» del CMF es poco fiable: la compra ocurre en su bolsa local'>🌏 {_nvd:+.1f}%</span>")
                sfilas += (f"<tr><td class='se-l'><b>{r['sym']}</b> <span style='color:var(--txt3);font-size:11px'>{esc(nm)}</span>{cbadge}{expl}</td>"
                           f"<td class='r'><b style='color:{scol};font-size:14px'>{r['pts']}</b><span style='color:#5E708A;font-size:10px'>/10</span></td>"
                           f"<td class='r'>{hia}</td>"
                           f"<td class='r' style='white-space:nowrap'>{sila}</td>"
                           f"<td class='r'>{r['wk_lag'] or '—'}</td>"
                           f"<td class='r'>{n3a}</td>"
                           f"<td class='r'>{prea}</td>"
                           f"<td class='r'>{gira}</td>"
                           f"<td class='r' style='color:#9FB0C8'>{qta}</td>"
                           f"<td class='r' style='font-size:11px'>{fla}</td>"
                           f"<td class='r' style='color:{vcol};font-size:11px;white-space:nowrap'>{verd}</td></tr>")
            crows = ""
            for s2 in (contra_sigs or []):
                _fm = (flow or {}).get(s2["sym"], {}) or {}
                _fmt = (f"{_fm['cmf']:+.2f}" if _fm.get("cmf") is not None else "n/d")
                if _fm.get("cmf_mejora"):
                    _fmt += " <span style='color:#7BD88F' title='CMF mejorando 3 tramos — regla de tramos: justifica manga pequeña; posición completa solo con CMF>0'>↗3t</span>"
                elif _fm.get("cmf") is not None and _fm["cmf"] > 0:
                    _fmt += " <span style='color:#2FD08A'>✓</span>"
                crows += (f"<tr><td class='se-l'><b>{s2['sym']}</b> <span style='color:var(--txt3);font-size:11px'>{esc(NAMES.get(s2['sym'], (s2['sym'], s2['sym'], ''))[1])}</span></td>"
                          f"<td class='r' style='color:#7BD88F;font-weight:700'>{s2['n3']}/3</td>"
                          f"<td class='r'>{s2['vert']:.1f}×</td>"
                          f"<td class='r' style='font-size:11px;white-space:nowrap'>{_fmt}</td>"
                          f"<td class='r' style='color:#5B8CFF;font-weight:700'>{size_pct:.1f}%</td></tr>")
            if stats:
                oos = (f"<b style='color:{'#2FD08A' if stats['winrate'] >= 55 else '#F4B740'}'>{stats['winrate']}% de acierto</b> "
                       f"en <b>{stats['n']}</b> señales fuera-de-muestra · media {stats['avg']:+.2f}% a {CONTRARIAN_HORIZON_W} sem")
            else:
                oos = f"aún sin señales maduras — cada una se evalúa sola a las {CONTRARIAN_HORIZON_W} semanas"
            # resumen del MODO CAZADOR DE SUELOS EXPLOSIVOS: cuantos de alta beta estan en zona de suelo
            _expl_suelo = [r for r in suelo if r["sym"] in SECTORES_EXPLOSIVOS]
            _expl_despierta = [r for r in _expl_suelo if r.get("despertando") and not r["sangra"]]
            _expl_pre = [r for r in _expl_suelo if r.get("fase") == "PRE-DESPERTAR"]
            _expl_sangra = [r for r in _expl_suelo if r["sangra"]]
            cazador = ""
            if _expl_suelo:
                if _expl_despierta:
                    _lst = ", ".join(f"<b style='color:#2FD08A'>{r['sym']}</b> ({EXPLOSIVO_TIPO.get(r['sym'],'')})" for r in _expl_despierta[:5])
                    cazador = (f"<div style='margin-bottom:12px;padding:10px 12px;background:rgba(47,208,138,.08);border:1px solid #2FD08A44;border-radius:8px'>"
                               f"<div style='font-size:12px;color:#2FD08A;font-weight:700;margin-bottom:4px'>🎯 CAZADOR DE SUELOS — {len(_expl_despierta)} sector(es) explosivo(s) DESPERTANDO</div>"
                               f"<div style='font-size:12px;color:#DCE6F5'>{_lst}</div>"
                               "<div style='font-size:10.5px;color:#8FA3C0;margin-top:5px'>Estos son de <b>beta alta</b> (rebotan fuerte) y están dejando de sangrar tras la caída. "
                               "Es la señal para <b>tener la liquidez lista</b> y, si el viernes lo confirma con flujo, entrar en el giro buscando el suelo. "
                               "No persigas: espera el cierre.</div></div>")
                elif _expl_pre:
                    _lst = ", ".join(f"<b style='color:#4CC2E0'>{r['sym']}</b> ({EXPLOSIVO_TIPO.get(r['sym'],'')} · {r.get('pre',0)}/4)" for r in _expl_pre[:5])
                    cazador = (f"<div style='margin-bottom:12px;padding:10px 12px;background:rgba(76,194,224,.07);border:1px solid #4CC2E044;border-radius:8px'>"
                               f"<div style='font-size:12px;color:#4CC2E0;font-weight:700;margin-bottom:4px'>🎯 CAZADOR DE SUELOS — {len(_expl_pre)} explosivo(s) en 🌱 PRE-DESPERTAR</div>"
                               f"<div style='font-size:12px;color:#DCE6F5'>{_lst}</div>"
                               "<div style='font-size:10.5px;color:#8FA3C0;margin-top:5px'>El patrón oro/BTC/mineras casi completo con el <b>precio aún quieto</b>: la ventana de anticipación. "
                               "Prepara la lista y los tamaños (mesas de póker); la entrada se dispara cuando el giro vertical lo pase a 🌅 con el cierre del viernes.</div></div>")
                elif _expl_sangra:
                    _lst = ", ".join(f"{r['sym']}" for r in _expl_sangra[:6])
                    cazador = (f"<div style='margin-bottom:12px;padding:10px 12px;background:rgba(244,96,122,.06);border:1px solid #F4607A33;border-radius:8px'>"
                               f"<div style='font-size:12px;color:#F4B740;font-weight:700;margin-bottom:4px'>🎯 CAZADOR DE SUELOS — {len(_expl_sangra)} explosivo(s) cayendo, AÚN SANGRAN</div>"
                               f"<div style='font-size:11.5px;color:#9FB0C8'>{_lst} — castigados pero el dinero todavía sale. <b>Liquidez quieta, sin prisa.</b> "
                               "El suelo se caza cuando el flujo deja de salir, no cuando el precio está barato.</div></div>")

            _tau_tag = ""
            if tau and tau.get("activa"):
                _tau_tag = (f"<div style='margin-bottom:6px;padding:5px 9px;background:rgba(244,183,64,.10);border:1px solid #F4B74055;"
                            f"border-radius:6px;font-size:11px;color:#F4B740'>📅 VENTANA τ ACTIVA hasta {tau['win_fin']}: señal de suelo aquí = "
                            f"reconfirmar tras la ventana (la caída puede ser venta forzada de fin de mes, no convicción).</div>")
            elif tau and tau.get("rebote"):
                _tau_tag = (f"<div style='margin-bottom:6px;padding:5px 9px;background:rgba(47,208,138,.10);border:1px solid #2FD08A55;"
                            f"border-radius:6px;font-size:11px;color:#2FD08A'>📅 ZONA REBOTE τ hasta {tau['reb_fin']}: la mejor franja del mes "
                            f"para un giro confirmado de suelo — la venta forzada terminó.</div>")
            html.append("<div class='panel full'><h2>😴 DURMIENTES — suelo + silencio + giro, el radar de anticipación</h2>" + _tau_tag
                        + cazador +
                        "<div class='note'>La <b>base del sistema</b>: replicar el patrón que clavó el suelo de oro, Bitcoin y mineras. La secuencia completa es "
                        "<b>DORMIDO → 🧲 ACUMULACIÓN → 🌱 PRE-DESPERTAR → 🌅 DESPERTANDO</b>, y el dinero grande se gana entrando en el PRE-DESPERTAR, "
                        "no persiguiendo el despertar. La columna <b>patrón</b> (●●●●) cuenta las 4 huellas de acumulación institucional: "
                        "divergencia CMF positiva (precio baja, dinero entra) · OBV con mínimos crecientes (compran las caídas) · volatilidad comprimida (muelle cargado) · base de mínimos crecientes. "
                        "3-4 huellas con el precio aún quieto y 🤫 silencio = la ventana de anticipación; cuando pase a 🌅 y llegue el volumen, ya será tarde para entrar barato. "
                        "La marca <span style='color:#FF8C42'>💥</span> señala los sectores <b>explosivos</b> (beta alta): donde el rebote es más salvaje y conviene tener liquidez lista. "
                        "El veredicto manda y <b>⚠ aún sangra</b> = ni tocar, da igual lo barato y lo bonito que esté el patrón.</div>"
                        "<div class='scrollx'><table class='se'><tr><th class='se-l'>sector / tema</th><th class='r'>😴</th>"
                        "<th class='r'>vs máx 52s</th><th class='r'>silencio</th><th class='r'>sem. dorm.</th>"
                        "<th class='r'>estruct.</th><th class='r'>patrón</th><th class='r'>giro</th><th class='r'>precio 4s</th><th class='r'>flujo</th><th class='r'>veredicto</th></tr>"
                        + sfilas + "</table></div>"
                        + ("<div style='margin-top:10px;padding:8px 10px;background:rgba(123,216,143,.06);border:1px solid #7BD88F33;border-radius:8px'>"
                           "<span style='font-size:11px;color:#7BD88F;font-weight:700'>SEÑAL CONTRARIA 0/3 DE ESTA SEMANA</span> "
                           "<span style='color:#8FA3C0;font-size:11px'>(la manga aparte: tamaño pequeño, nunca apalancados, se registra y se evalúa sola a 4 semanas)</span>"
                           "<table class='se' style='margin-top:6px'><tr><th class='se-l'>señal</th><th class='r'>estruct.</th><th class='r'>verticalidad</th><th class='r' title='regla de tramos: CMF mejorando 3 tramos = manga pequeña; CMF>0 = posición'>flujo</th><th class='r'>tamaño</th></tr>"
                           + crows + "</table></div>" if crows else
                           "<div class='note' style='margin-top:8px;color:#5E708A'>Sin señal contraria 0/3 válida esta semana — la paciencia también es una posición.</div>")
                        + f"<div class='note' style='margin-top:8px'><b>Ledger fuera-de-muestra</b>: {oos}. Tamaño: {size_src}. "
                        f"Guardado en <code>senales_contrarias.json</code>. Regla de siempre: esto <b>observa</b> entre semana y se <b>ejecuta</b> con el cierre del viernes, "
                        "con flujo que como mínimo haya dejado de salir. El flujo confirma, no predice — también aquí. No es asesoramiento.</div></div>")
    except Exception:
        pass
    # ---- 🌅 RECIEN DESPERTADOS: la fase que faltaba entre el durmiente y el scoring ----
    try:
        if graduados:
            grows = ""
            for g in graduados:
                _gb = ""
                if g.get("expl"):
                    _gb += (f" <span style='color:#FF8C42;font-size:9px;border:1px solid #FF8C4255;border-radius:3px;padding:0 4px'>💥 {esc(EXPLOSIVO_TIPO.get(g['sym'], ''))}</span>")
                if g.get("aext"):
                    _nv = g.get("noct") or 0
                    _gb += (f" <span style='color:#4CC2E0;font-size:9px;border:1px dashed #4CC2E088;border-radius:8px;padding:0 5px;white-space:nowrap' "
                            f"title='ACUMULACIÓN EXTRANJERA: gap nocturno {_nv:+.1f}% en 20 sesiones con CMF<=0 — la compra ocurre en su bolsa local, el CMF americano no la ve'>🌏 {_nv:+.1f}% noct.</span>")
                _cmftx = (f"{g['cmf']:+.2f}" if g.get("cmf") is not None else "n/d") + (" ↗3t" if g.get("mejora") else "")
                _extx = (f"{g['ext']:+.1f}%" if g.get("ext") is not None else "n/d")
                grows += (f"<tr><td class='se-l'><b>{g['sym']}</b> <span style='color:var(--txt3);font-size:11px'>{esc(NAMES.get(g['sym'], (g['sym'], g['sym']))[1])}</span>{_gb}</td>"
                          f"<td class='r'>{('esta semana' if g['sem'] == 0 else ('hace 1 sem' if g['sem'] == 1 else 'hace %d sem' % g['sem']))}</td>"
                          f"<td class='r' style='color:{('#2FD08A' if (g['pct'] or 0) >= 0 else '#F4607A')}'>{g['pct']:+.1f}%</td>"
                          f"<td class='r'>{g['dd_cross']:+.0f}%</td>"
                          f"<td class='r'>{_extx}</td>"
                          f"<td class='r'>{_cmftx}</td>"
                          f"<td class='se-l' style='color:{g['vcol']};font-size:11px'>{esc(g['ver'])}</td></tr>")
            html.append("<div class='panel full'><h2>🌅 Recién despertados — graduados de la cueva</h2>"
                        "<div class='note' style='margin-bottom:6px'>La fase que faltaba: cuando un durmiente cruza su impulso al alza, <b>desaparece del radar de arriba justo cuando "
                        "se pone interesante</b> (así se esfumaron KWEB y FXI entre paneles). Aquí se sigue a los que ERAN durmientes — semanas rezagados y con castigo ≥8% — y despertaron "
                        "hace ≤4 semanas: cuánto llevan desde el cruce, si la entrada sigue <b>sin extender</b> (precio vs su media de 40s) y qué dice el flujo, incluida la 🌏 <b>acumulación "
                        "extranjera</b> (gap nocturno acumulado: en internacionales la compra ocurre en su bolsa y el CMF americano no la ve — el punto ciego que ocultó a China). "
                        "<b>Regla de tramos:</b> flujo girando (CMF mejorando 3 tramos o acum. extranjera) = manga pequeña · CMF&gt;0 = posición · siempre con el cierre del viernes.</div>"
                        "<table class='sectbl'><tr><th class='se-l'>SECTOR / TEMA</th><th class='r'>DESPERTÓ</th><th class='r'>DESDE CRUCE</th>"
                        "<th class='r' title='castigo vs máximo de 52 semanas en el momento del cruce'>CASTIGO AL CRUZAR</th>"
                        "<th class='r' title='precio vs su media de 40 semanas: la extensión. Poco extendido = todavía no llegas tarde'>EXTENSIÓN</th>"
                        "<th class='r'>CMF</th><th class='se-l'>VEREDICTO</th></tr>" + grows + "</table>"
                        "<div class='note' style='margin-top:6px'>No es asesoramiento.</div></div>")
    except Exception:
        pass
    # ---- PANEL DE COBERTURA (skew de opciones: quien paga por protegerse) ----
    try:
        if cobertura and cobertura.get("cestas"):
            _cfil = [c for c in cobertura["cestas"] if c["miembros"] or c["rank"] is not None]
            _cards = ""
            for c in _cfil:
                _vs = ""
                if c.get("vs_mercado") is not None:
                    _vcol = "#F4607A" if c["vs_mercado"] >= 15 else ("#2FD08A" if c["vs_mercado"] <= -15 else "var(--txt3)")
                    _vs = (f"<div style='font-size:11px;color:{_vcol};margin-top:2px'>"
                           f"{'+' if c['vs_mercado'] > 0 else ''}{c['vs_mercado']} pts vs el mercado entero</div>")
                _chips = ""
                for m in c["miembros"]:
                    _mk = ("<span style='color:var(--txt3)'>s/n</span>" if m["rank"] is None
                           else f"<b style='color:{('#F4607A' if m['rank'] >= 75 else '#2FD08A' if m['rank'] <= 25 else 'var(--txt1)')}'>{m['rank']}</b>")
                    _px = " <span title='ETF ilíquido: leído con acciones proxy' style='color:#F4B740'>~</span>" if (m["proxy"] or m["iliquido"]) else ""
                    _chips += (f"<span style='display:inline-block;margin:2px 4px 2px 0;padding:2px 6px;"
                               f"border:1px solid var(--line);border-radius:4px;font-size:11px'>"
                               f"{esc(m['sym'])}{_px} {_mk}</span>")
                _bar = ""
                if c["rank"] is not None:
                    _bar = ("<div style='height:5px;background:var(--ink3);border-radius:3px;margin:6px 0 4px'>"
                            f"<div style='height:5px;width:{max(2, min(100, c['rank']))}%;background:{c['col']};border-radius:3px'></div></div>")
                _cards += (f"<div style='border:1px solid {c['col']}55;border-left:3px solid {c['col']};"
                           f"border-radius:6px;padding:9px 11px;margin-bottom:7px'>"
                           f"<div style='display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap'>"
                           f"<span style='font-size:13px;font-weight:700'>{esc(c['titulo'])}</span>"
                           f"<span style='font-size:12px;font-weight:700;color:{c['col']}'>{esc(c['estado'])}</span></div>"
                           + _bar + _vs
                           + f"<div style='font-size:11px;color:var(--txt2);margin:4px 0'>{esc(c['lectura'])}</div>"
                           + _chips
                           + (f"<div style='font-size:10px;color:var(--txt3);margin-top:4px'>n={c['n_min']} lecturas guardadas</div>" if c["n_min"] else "")
                           + "</div>")
            _av = ""
            if not cobertura.get("listo"):
                _av = ("<div class='note' style='margin:6px 0;padding:6px 8px;border-left:3px solid #F4B740'>"
                       "&#9888; <b>El panel aún se está llenando.</b> El skew solo informa comparado con su propia historia, "
                       f"y hacen falta {cobertura.get('min_hist', 8)} lecturas guardadas. Se añade una por ejecución: "
                       "publica cada viernes y en unas semanas empieza a hablar. Hasta entonces no te fíes de los números.</div>")
            html.append("<div class='panel full'><h2>&#128737; Cobertura — ¿quién está pagando por protegerse?</h2>"
                        "<div class='note' style='margin-bottom:6px'>Mide el <b>skew</b>: lo que cuesta el seguro de caída frente al billete de lotería de subida "
                        "(volatilidad implícita del put 5% por debajo menos la del call 5% por encima). Cuando los grandes se cubren, pagan más por los puts y ese hueco se ensancha."
                        "<br><b>Todo son percentiles contra su propia historia, no valores brutos</b>, porque el seguro de caída SIEMPRE cuesta más que el de subida: el número absoluto no dice nada. "
                        "Percentil alto = se protegen más de lo que acostumbran. Percentil bajo = complacencia, nadie ve riesgo."
                        "<br><b>Lo que de verdad vale es la divergencia</b>: precio subiendo y cobertura encareciéndose a la vez = alguien compra el rebote y lo asegura. Es la distribución oculta, pero en opciones.</div>"
                        + _av + _cards
                        + "<div class='note' style='margin-top:6px'>&#9888; <b>Esto NO son flujos institucionales.</b> El order flow real no es público y los 13F llegan con ~3,5 meses de retraso. "
                          "El skew mide lo que se <b>paga</b> por protegerse, no quién compra. Es un proxy y hay que tratarlo como tal: el flujo del terminal (CMF) sigue mandando. "
                          "La marca ~ señala ETFs ilíquidos leídos con acciones proxy. Frecuencia y contexto, no predicción. No es asesoramiento.</div></div>")
    except Exception:
        pass
    # ---- CUADRO DEL FACTOR MOMENTO (tapa el limbo del RRG) ----
    try:
        if momento and momento.get("rows"):
            _MC = {"EN MARCHA": "#2FD08A", "GIRANDO": "#F4B740",
                   "MADURO": "#9FB0C8", "CAYENDO": "#F4607A"}
            _MD = {"EN MARCHA": "sube y acelera", "GIRANDO": "aun flojo pero acelerando",
                   "MADURO": "fuerte pero frenando", "CAYENDO": "debil y frenando"}
            def _mcelda(cj):
                v = momento["cajas"].get(cj, [])
                col = _MC[cj]
                # fuera de la f-string a proposito: un backslash dentro de {..} rompe en Python 3.11
                _vacio = "<span style='font-size:11px;color:var(--txt3)'>vacio</span>"
                chips = ""
                for r in v[:9]:
                    _h = " <span title='corre y no sale en ningun otro panel'>&#9679;</span>" if r["huerfano"] else ""
                    chips += (f"<span style='display:inline-block;margin:2px 4px 2px 0;padding:2px 6px;"
                              f"border:1px solid {col}44;border-radius:4px;font-size:11px;color:var(--txt1)'>"
                              f"<b>{esc(r['sym'])}</b> <span style='color:var(--txt3)'>{r['sem']}s</span>{_h}</span>")
                if len(v) > 9:
                    chips += f"<span style='font-size:11px;color:var(--txt3)'>+{len(v)-9} mas</span>"
                return (f"<div style='border:1px solid {col}55;border-left:3px solid {col};border-radius:6px;"
                        f"padding:8px 10px;min-height:82px'>"
                        f"<div style='font-size:12px;font-weight:700;color:{col}'>{cj} "
                        f"<span style='color:var(--txt3);font-weight:400'>({len(v)})</span></div>"
                        f"<div style='font-size:10px;color:var(--txt3);margin-bottom:5px'>{_MD[cj]}</div>"
                        f"{chips or _vacio}</div>")
            _grid = ("<div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:8px 0'>"
                     + _mcelda("EN MARCHA") + _mcelda("MADURO")
                     + _mcelda("GIRANDO") + _mcelda("CAYENDO") + "</div>")
            _mrows = ""
            for r in momento["cajas"]["EN MARCHA"] + momento["cajas"]["GIRANDO"]:
                _cm = ("<span style='color:var(--txt3)'>s/d</span>" if r["cmf"] is None
                       else f"<span style='color:{('#2FD08A' if r['cmf'] > 0 else '#F4607A')}'>{r['cmf']:+.2f}</span>")
                _ex = "<span style='color:var(--txt3)'>s/d</span>" if r["ext"] is None else (
                      f"<span style='color:{('#F4607A' if r['ext'] > 12 else '#F4B740' if r['ext'] > 6 else '#2FD08A')}'>{r['ext']:+.1f}%</span>")
                _hb = (" <span style='background:#F4B74022;color:#F4B740;font-size:9px;padding:1px 4px;"
                       "border-radius:3px' title='no aparece en durmientes ni en graduados'>SE ESCAPABA</span>") if r["huerfano"] else ""
                _mrows += (f"<tr><td class='se-l'><b>{esc(r['sym'])}</b> "
                           f"<span style='color:var(--txt3);font-size:11px'>{esc(NAMES.get(r['sym'], (r['sym'], r['sym']))[1])}</span>{_hb}</td>"
                           f"<td class='r' style='color:{_MC[r['caja']]};font-size:11px'>{r['caja']}</td>"
                           f"<td class='r'>{r['sem']} sem</td>"
                           f"<td class='r'>{r['m12']:+.1f}%</td>"
                           f"<td class='r'>{r['pm']} / {r['pa']}</td>"
                           f"<td class='r'>{_ex}</td><td class='r'>{_cm}</td>"
                           f"<td class='se-l' style='color:{r['vcol']};font-size:11px'>{esc(r['ver'])}</td></tr>")
            _apagado = ""
            if centinela and centinela.get("estado") in ("DISTRIBUCION", "DISTRIBUCIÓN", "LIQUIDEZ"):
                _apagado = ("<div class='note' style='margin:6px 0;padding:6px 8px;border-left:3px solid #F4607A'>"
                            "&#9888; <b>CENTINELA en " + esc(str(centinela.get("estado"))) + "</b>: el factor momento se desploma "
                            "justo en los giros de regimen. Este cuadro queda en <b>solo lectura</b> — nada de abrir por momento.</div>")
            html.append("<div class='panel full'><h2>&#128208; Cuadro del factor momento</h2>"
                        "<div class='note' style='margin-bottom:6px'>Tapa un agujero real: el impulso del RRG es un z-score y <b>se adelanta al precio</b> "
                        "(cruza durante la base plana), asi que cuando el precio arranca de verdad ya han pasado 5-8 semanas y los graduados (ventana de 4) lo han soltado, "
                        "mientras los durmientes tampoco lo recogen. Un sector que sube se queda en tierra de nadie: asi se esfumaron KWEB y FXI. "
                        "El momento en crudo no lleva z-score, <b>sigue al precio</b>. Eje horizontal: momento 12-1 (rentabilidad de 12 semanas saltandose la ultima, "
                        "porque el corto plazo suele rebotar en contra). Eje vertical: aceleracion (ritmo de 4 semanas contra el ritmo medio de 12). "
                        "Los dos son <b>ranking entre sectores</b>, no valor absoluto. El punto &#9679; marca los que corren y no salen en ningun otro panel."
                        "<br><b>Jerarquia:</b> esto es precio, no flujo. El cuadro <b>propone</b>; el CMF y el cierre del viernes <b>confirman</b>.</div>"
                        + _apagado + _grid
                        + ("<table class='sectbl'><tr><th class='se-l'>SECTOR / TEMA</th><th class='r'>CAJA</th><th class='r'>LLEVA</th>"
                           "<th class='r' title='rentabilidad de t-13 a t-1'>MOMENTO 12-1</th>"
                           "<th class='r' title='percentil de momento / percentil de aceleracion'>PCTL M / A</th>"
                           "<th class='r' title='precio vs su media de 40 semanas'>EXTENSION</th>"
                           "<th class='r'>CMF</th><th class='se-l'>VEREDICTO</th></tr>" + _mrows + "</table>" if _mrows else "")
                        + "<div class='note' style='margin-top:6px'>Frecuencia y ranking, no prediccion. No es asesoramiento.</div></div>")
    except Exception:
        pass
    # ---- PLAN DE LIQUIDEZ + CAIDAS DEL S&P 500 (fusionado) ----
    if plan or dd:
        left = ""
        if plan:
            ddc = "#F4607A" if plan["dd"] <= -5 else "#F4B740" if plan["dd"] <= -2 else "#2FD08A"
            idx_name = "S&amp;P 500" if "SP" in long_src.upper() or long_src in ("^SPX", "^GSPC") else long_src or "S&amp;P 500"
            rungs_html = ""
            for r in plan["rungs"]:
                veh = LEV3X.get("QQQ", "TQQQ")
                stt = ("<span style='color:#2FD08A'>ALCANZADA</span>" if r["hit"]
                       else f"<span style='color:#5E708A'>faltan {(r['thr'] + plan['dd']):.1f}%</span>")
                bcol = "#2FD08A" if r["hit"] else "#1E2A3D"
                rungs_html += (f"<div class='rung' style='border-left-color:{bcol}'>"
                               f"<span class='rk-thr'>−{r['thr']}%</span>"
                               f"<span class='rk-lvl'>{idx_name} ≤ {r['level']}</span>"
                               f"<span class='rk-pct'>desplegar {r['pct']}%</span>"
                               f"<span class='rk-veh'>{veh}</span>"
                               f"<span class='rk-st'>{stt}</span></div>")
            _aviso_stale = ""
            if plan.get("stale", 0) >= 1:
                _aviso_stale = (f"<div style='margin:6px 0;padding:6px 9px;background:rgba(244,183,64,.12);border:1px solid #F4B74066;"
                                f"border-radius:6px;font-size:11px;color:#F4B740'>⚠ El último dato es del <b>{plan.get('fecha','?')}</b> "
                                f"(falta{'n' if plan['stale'] > 1 else ''} {plan['stale']} sesión(es)): la caída real puede ser MAYOR de la que ves aquí.</div>")
            _es_line = ""
            if es_fut:
                try:
                    # el ES cotiza en PUNTOS DE INDICE (~7500); si la serie de referencia es SPY (~750),
                    # se reescala por la potencia de 10 mas cercana antes de comparar (el +888% de la v1 era esto)
                    _fac = 10 ** round(math.log10(max(es_fut["last"], 1e-9) / max(plan["last"], 1e-9)))
                    _es_adj = es_fut["last"] / _fac
                    _es_dd = (_es_adj / plan["peak"] - 1) * 100
                    if abs(_es_dd) < 15:                      # sanidad: si aun asi sale absurdo, no se muestra
                        _es_esc = f" (≈{_es_adj:.1f} en escala {esc(long_src)})" if _fac != 1 else ""
                        _es_line = (f"<div class='sm' style='margin-top:3px'>Futuro ES (casi 24h): <b>{es_fut['last']}</b>{_es_esc} "
                                    f"({_es_dd:+.1f}% vs ATH) · {es_fut['ts']} <span style='color:#5E708A'>— la referencia más fresca; "
                                    f"el contado siempre va por detrás</span></div>")
                except Exception:
                    pass
            left = (f"<div class='dd-now'><div class='lab'>Caida actual del {idx_name} desde su MAXIMO INTRADIA</div>"
                    f"<div class='dd-big' style='color:{ddc}'>{plan['dd']:.1f}%</div>"
                    f"<div class='sm'>ATH intradía <b>{plan['peak']}</b> · último cierre <b>{plan['last']}</b> ({plan.get('fecha','?')}) · fuente {long_src}"
                    f"<span style='color:#5E708A'> · vs máx. de cierres: {plan.get('dd_close', plan['dd']):+.1f}%</span></div>"
                    + _es_line + _aviso_stale + "</div>"
                    + rungs_html)
        right = ""
        if dd:
            rows = ""
            for t in DD_THRESHOLDS:
                e = dd[t]
                ytdcol = "#F4B740" if e["ytd"] > 0 else "#5E708A"
                restcol = "#2FD08A" if e["rest"] >= 50 else "#F4B740" if e["rest"] >= 20 else "#9FB0C8"
                rows += (f"<tr><td class='r' style='color:#E6EDF6'>−{t:g}%</td>"
                         f"<td class='r'>{e['avg20']}</td><td class='r'>{e['avgfull']}</td>"
                         f"<td class='r' style='color:#5B8CFF'>{e['probfull']}%</td>"
                         f"<td class='r' style='color:{restcol}'>{e['rest']}%</td>"
                         f"<td class='r' style='color:{ytdcol}'>{e['ytd']}</td></tr>")
            meta = dd_meta or {}
            right = ("<table><tr><th>Caida</th><th class='r'>media/año<br>20a</th>"
                     "<th class='r'>media/año<br>histórico</th><th class='r'>prob. en<br>un año</th>"
                     "<th class='r'>prob. resto<br>del año</th>"
                     "<th class='r'>ya este<br>año</th></tr>" + rows + "</table>"
                     f"<div class='note' style='margin-top:6px'>Histórico {meta.get('start','?')}–{meta.get('end','?')} "
                     f"({long_src}, <b>{meta.get('basis','cierre')}</b>). «Prob. en un año» = % de años con al menos una caída de ese tamaño. "
                     "«Prob. resto del año» = % de años en que ocurrió una caída así <b>entre la fecha de hoy y fin de año</b>. "
                     "«Media/año» = nº de caídas de ese tamaño por año (un evento se cierra al recuperar la mitad). "
                     + ("<b>Intradía</b>: cuenta cuando el índice <b>tocó</b> ese nivel en algún momento del día (ahí suele haber compras y rebote), aunque cerrara más arriba."
                        if meta.get('basis') == 'intradía' else
                        "Medido sobre precios de <b>cierre</b>.")
                     + " <b>Método:</b> caída desde el <b>pico de las últimas 52 semanas</b> (pico reciente, como una corrección normal). "
                       "Los cubos grandes (<b>−10%</b> y <b>−20%</b>) saltan a partir de <b>−9.5%</b> y <b>−19.5%</b>: el SPY solo "
                       "registra su sesión de contado, pero el futuro/CFD del S&amp;P cotiza casi 24h, así que una caída que tocó el −10% "
                       "de madrugada puede quedar en ~−9.5% en el dato del SPY. Ese medio punto capta ese hueco nocturno. "
                       "Consenso de mercado: un <b>−10%</b> ocurre ≈<b>1 vez/año</b>, un <b>−5%</b> ≈<b>3 veces/año</b> y un <b>−20%</b> "
                       "≈<b>1 vez cada 5-6 años</b> (13 desde 1950). Son frecuencias históricas, no predicción.</div>")
        html.append("<div class='panel full'><h2>Plan de liquidez y caídas del S&amp;P 500</h2>"
                    "<div class='note'>Guía de entrada escalonada según la caída del S&amp;P desde máximos, junto a la "
                    "frecuencia histórica de caídas. Los porcentajes de despliegue se editan arriba del archivo (CASH_PLAN).</div>"
                    "<div class='planwrap'><div class='planladder'>" + left + "</div>"
                    "<div class='planstats'>" + right + "</div></div>"
                    "<div class='note' style='margin-top:8px;color:#F4607A'>⚠ Los productos apalancados x3 (TQQQ y similares) se reajustan "
                    "a diario, sufren desgaste por volatilidad y pueden caer mucho más que el índice (TQQQ perdió ~80% en 2022). "
                    "No son para mantener en mercados laterales. El mercado puede seguir cayendo más allá del −20%. No es asesoramiento.</div></div>")

    # ---- LECTURA DEL MERCADO Y PROBABILIDADES (fusion de todo) ----
    # defaults incondicionales: el veredicto (stance/light/bull) SIEMPRE debe poder pintarse,
    # aunque scores o probs falten en un build degradado.
    try:
        _spyd = df[BENCH].dropna()
        bull = bool(_spyd.iloc[-1] > _spyd.rolling(min(40, len(_spyd)), min_periods=10).mean().iloc[-1])
    except Exception:
        bull = True
    if bull:
        light, stance = "#F4B740", "ÁMBAR — mercado alcista, sin datos de puntuación suficientes esta semana."
    else:
        light, stance = "#F4607A", "ROJO — el S&P está por debajo de su media de 40 semanas: prudencia."
    if scores and probs:
        spy = df[BENCH]
        bull = bool(spy.iloc[-1] > spy.rolling(min(40, len(spy))).mean().iloc[-1])
        st = probs["stats"]; fwd = probs["fwd"]
        lite = lambda r: sum(1 for _, v in r["parts"][:3] if v)
        buy = [r for r in scores if r["score"] >= 4]
        n_buy = len(buy)
        if not bull:
            light, stance = "#F4607A", "ROJO — el S&P está por debajo de su media de 40 semanas: el filtro de tendencia recomienda prudencia (liquidez o defensivos)."
        elif n_buy >= 5:
            light, stance = "#2FD08A", "VERDE — mercado alcista y varias oportunidades de alta puntuación: entorno favorable para invertir, siendo selectivo."
        elif n_buy >= 2:
            light, stance = "#F4B740", "ÁMBAR-VERDE — mercado alcista pero selectivo: hay oportunidades, aunque pocas y concentradas."
        else:
            light, stance = "#F4B740", "ÁMBAR — mercado alcista pero sin señales fuertes claras esta semana: mejor paciencia."
        read = (f"Régimen <b>{esc(regime['label'])}</b>, apetito de riesgo <b>{esc(risk['label'])}</b>, "
                f"tendencia del mercado <b>{'alcista' if bull else 'bajista'}</b>. "
                f"<b>{n_buy}</b> ETF con puntuación de compra (4–5/5) esta semana.")
        # tabla de probabilidades base (historica)
        prob_rows = ""
        for sc in [3, 2, 1, 0]:
            d = st.get(sc, {})
            if d.get("pup") is None:
                continue
            pcol = "#2FD08A" if d["pup"] >= 60 else "#F4B740" if d["pup"] >= 50 else "#F4607A"
            acol = "#2FD08A" if d["avg"] >= 0 else "#F4607A"
            prob_rows += (f"<tr><td class='pb-l'><b>{sc}/3</b> señales estructurales</td>"
                          f"<td class='pb-v' style='color:{pcol}'>{d['pup']}%</td>"
                          f"<td class='pb-v' style='color:{acol}'>{d['avg']:+.1f}%</td>"
                          f"<td class='pb-n'>{d['n']} casos</td></tr>")
        # candidatos listos con motivos + probabilidad
        cand = ""
        for r in buy[:8]:
            ls = lite(r); bd = st.get(ls, {})
            reasons = ", ".join(name for name, v in r["parts"] if v)
            prob_txt = (f"<b style='color:{'#2FD08A' if bd['pup']>=55 else '#F4B740'}'>{bd['pup']}%</b> histórico de subir en {fwd} sem (media {bd['avg']:+.1f}%)"
                        if bd.get("pup") is not None else "—")
            nm = NAMES.get(r["sym"], (r["sym"], r["sym"], ""))[1]
            acc = " <span class='sc-acc'>⚡</span>" if r["obv_cross"] else ""
            cand += (f"<div class='cand'><div class='cand-h'><b>{r['sym']}</b> <span>{esc(nm)}</span>"
                     f"<span class='cand-sc' style='color:{'#2FD08A' if r['score']>=4 else '#F4B740'}'>{r['score']}/5</span>{acc}</div>"
                     f"<div class='cand-r'>Listo para la semana que viene porque: {esc(reasons)}.</div>"
                     f"<div class='cand-p'>Probabilidad: {prob_txt}.</div></div>")
        # ---- FEAR & GREED de CNN (sentimiento contrario) ----
        if fg_idx:
            sc = fg_idx["score"]
            if sc < 25:
                zona, col = "Miedo extremo", "#F4607A"
            elif sc < 45:
                zona, col = "Miedo", "#F4824A"
            elif sc <= 55:
                zona, col = "Neutral", "#F4B740"
            elif sc <= 74:
                zona, col = "Codicia", "#7FC97F"
            else:
                zona, col = "Codicia extrema", "#2FD08A"
            if sc >= 75:
                lect = "Sentimiento eufórico — históricamente <b>peor</b> momento para añadir riesgo. Encaja con tu pólvora seca: cautela."
            elif sc < 25:
                lect = "Pánico — históricamente de las <b>mejores</b> ventanas de entrada (pero no es señal de timing: puede caer más). Es cuando tu plan de liquidez entra en juego."
            else:
                lect = "Sentimiento intermedio, sin extremo contrario claro."
            def _fgchip(lbl, v):
                return f"<span class='fgchip'>{lbl}: <b>{v if v is not None else '—'}</b></span>"
            html.append("<div class='panel full'><h2>Fear &amp; Greed (CNN)</h2>"
                        f"<div class='fgwrap'><div class='fgnum' style='color:{col}'>{sc}<span>/100</span></div>"
                        f"<div class='fgzone' style='color:{col}'>{esc(zona)}</div></div>"
                        f"<div class='fgbar'><div class='fgmark' style='left:{sc}%'></div></div>"
                        f"<div class='fgctx'>{_fgchip('ayer', fg_idx['prev'])}{_fgchip('hace 1 sem', fg_idx['week'])}"
                        f"{_fgchip('hace 1 mes', fg_idx['month'])}{_fgchip('hace 1 año', fg_idx['year'])}</div>"
                        f"<div class='note'>{lect} Es un indicador <b>contrario</b>: mide la emoción del mercado "
                        "(0 = pánico, 100 = euforia), no su dirección. Fuente: CNN. No es asesoramiento.</div></div>")
        else:
            html.append("<div class='panel full'><h2>Fear &amp; Greed (CNN)</h2>"
                        "<div class='note'>⚠ <b>F&amp;G no disponible</b> ahora mismo: CNN no ha devuelto el dato "
                        "(puede ser un fallo temporal de su servidor o de red). El resto del panel no se ve afectado; "
                        "vuelve a ejecutar más tarde y reaparecerá. No es asesoramiento.</div></div>")

        # ===== TERMOMETRO DEL MERCADO — SPY (entra o sale dinero) =====
        try:
            if spy_flow:
                sf = spy_flow
                spy = df[BENCH].dropna()
                sma40 = spy.rolling(40).mean()
                trend_up = bool(spy.iloc[-1] > sma40.iloc[-1]) if sma40.notna().any() else None
                mom3 = ((spy.iloc[-1] / spy.iloc[-14] - 1) * 100) if len(spy) > 14 else None
                obv_ok = bool(sf.get("obv_above")); cmf = sf.get("cmf", 0.0) or 0.0
                cmf_pos = bool(sf.get("cmf_pos")); diverg = bool(sf.get("diverg"))
                if diverg:
                    verd, vcol = "⚠ Distribución oculta: el precio sube pero el dinero SALE", "#F4607A"
                elif obv_ok and cmf_pos:
                    verd, vcol = "Dinero ENTRANDO en el mercado (acumulación)", "#2FD08A"
                elif (not obv_ok) and cmf < 0:
                    verd, vcol = "Dinero SALIENDO del mercado (distribución)", "#F4607A"
                else:
                    verd, vcol = "Flujo mixto / sin señal clara", "#F4B740"
                def _yn(b, t, f):
                    return (f"<b style='color:#2FD08A'>{t}</b>" if b else f"<b style='color:#F4607A'>{f}</b>")
                obv_txt = _yn(obv_ok, "por encima de su media (acumula)", "por debajo (distribuye)")
                cmf_col = "#2FD08A" if cmf > 0 else "#F4607A"
                cmf_txt = f"<span style='color:{cmf_col}'>{cmf:+.3f} ({'compra' if cmf > 0 else 'venta'})</span>"
                div_txt = "⚠ <b style='color:#F4607A'>sí</b>" if diverg else "<span style='color:#2FD08A'>no</span>"
                rows = (f"<tr><td class='se-l'>OBV (volumen acumulado)</td><td class='r'>{obv_txt}</td></tr>"
                        f"<tr><td class='se-l'>CMF (dinero neto, Chaikin)</td><td class='r'>{cmf_txt}</td></tr>"
                        f"<tr><td class='se-l'>Distribución oculta</td><td class='r'>{div_txt}</td></tr>")
                if trend_up is not None:
                    rows += f"<tr><td class='se-l'>Tendencia (precio vs media 40s)</td><td class='r'>{_yn(trend_up, 'alcista', 'bajista')}</td></tr>"
                if mom3 is not None:
                    mcol = "#2FD08A" if mom3 > 0 else "#F4607A"
                    rows += f"<tr><td class='se-l'>Momentum 3 meses</td><td class='r' style='color:{mcol}'>{mom3:+.1f}%</td></tr>"
                if sf.get("vol_break"):
                    rows += "<tr><td class='se-l'>Volumen</td><td class='r' style='color:#2FD08A'>ruptura al alza con volumen</td></tr>"
                html.append(
                    "<div class='panel full'><h2>Termómetro del mercado — ¿entra o sale dinero del SPY?</h2>"
                    f"<div class='readbox' style='border-color:{vcol}55'><div class='read-light' style='background:{vcol}'></div>"
                    f"<div><div class='read-txt'>{verd}</div><div class='read-stance' style='color:{vcol}'>SPY = el mercado entero (el centro del RRG)</div></div></div>"
                    "<div class='scrollx' style='margin-top:10px'><table class='se'><tr><th class='se-l'>señal</th><th class='r'>lectura</th></tr>"
                    + rows + "</table></div>"
                    "<div class='note' style='margin-top:8px'>Es el <b>flujo absoluto del propio SPY</b> (no relativo): la <b>marea</b> del mercado entero. "
                    "Como SPY es el centro del RRG, su dinero no se ve ahí, por eso va aquí. "
                    "<b>Distribución oculta</b> (el precio sube pero OBV/CMF caen) es el aviso más útil: el mercado sube pero el dinero se va. No es asesoramiento.</div></div>")
        except Exception:
            pass

        # ===== CORTO TÁCTICO — SEMICONDUCTORES (SOXS −3x) — separado y marcado en rojo =====
        try:
            smhf = (flow or {}).get("SMH")
            if smhf is not None and "SMH" in df.columns:
                smh = df["SMH"].dropna()
                sma40 = smh.rolling(40).mean()
                below = bool(smh.iloc[-1] < sma40.iloc[-1]) if sma40.notna().any() else None
                mom3 = ((smh.iloc[-1] / smh.iloc[-14] - 1) * 100) if len(smh) > 14 else None
                obv_ok = bool(smhf.get("obv_above")); cmf = smhf.get("cmf", 0.0) or 0.0
                diverg = bool(smhf.get("diverg"))
                if diverg:
                    verd = "🟢 Setup de corto temprano: el precio aún arriba pero el dinero SALE (distribución oculta). La entrada de corto más limpia — si te pones, es ahora, no cuando ya cae."
                    vcol = "#F4607A"
                elif below and mom3 is not None and mom3 < -8:
                    verd = "🟠 Ya cayendo fuerte: llegas TARDE. Ponerte corto aquí con un 3x inverso es perseguir, con riesgo de rebote violento que destroza el SOXS."
                    vcol = "#F4B740"
                elif obv_ok and cmf > 0:
                    verd = "⛔ NO te pongas corto: el dinero sigue ENTRANDO en semis. Un corto aquí rema contra corriente."
                    vcol = "#2FD08A"
                else:
                    verd = "⚪ Sin señal clara de corto. Espera a que el flujo confirme salida de dinero (distribución oculta)."
                    vcol = "#9FB0C8"
                def _yns(b, t, f):
                    return (f"<b style='color:#2FD08A'>{t}</b>" if b else f"<b style='color:#F4607A'>{f}</b>")
                div_txt = "⚠ <b style='color:#F4607A'>sí — setup de corto</b>" if diverg else "<span style='color:#2FD08A'>no</span>"
                rows = (f"<tr><td class='se-l'>OBV (volumen acumulado)</td><td class='r'>{_yns(obv_ok, 'arriba (entra dinero)', 'abajo (sale dinero)')}</td></tr>"
                        f"<tr><td class='se-l'>CMF (dinero neto)</td><td class='r' style='color:{'#2FD08A' if cmf > 0 else '#F4607A'}'>{cmf:+.3f}</td></tr>"
                        f"<tr><td class='se-l'>Distribución oculta (precio↑ dinero↓)</td><td class='r'>{div_txt}</td></tr>")
                if below is not None:
                    rows += f"<tr><td class='se-l'>Precio vs media 40s</td><td class='r'>{_yns(not below, 'por encima', 'por debajo (ya débil)')}</td></tr>"
                if mom3 is not None:
                    rows += f"<tr><td class='se-l'>Momentum 3 meses</td><td class='r' style='color:{'#2FD08A' if mom3 > 0 else '#F4607A'}'>{mom3:+.1f}%</td></tr>"
                html.append(
                    "<div class='panel full' style='border:1px solid #F4607A55'><h2>🔻 Corto táctico — semiconductores (SOXS −3x)</h2>"
                    "<div class='note' style='color:#F4B740'><b>Avanzado y peligroso.</b> Lee el flujo de los semis (SMH) y lo traduce al lado corto. El instrumento sería <b>SOXS</b> (Direxion −3x diario, el más volátil).</div>"
                    f"<div class='readbox' style='border-color:{vcol}55;margin-top:8px'><div class='read-light' style='background:{vcol}'></div>"
                    f"<div><div class='read-txt'>{verd}</div><div class='read-stance' style='color:{vcol}'>¿está saliendo dinero de los semis?</div></div></div>"
                    "<div class='scrollx' style='margin-top:10px'><table class='se'><tr><th class='se-l'>señal (sobre SMH)</th><th class='r'>lectura</th></tr>"
                    + rows + "</table></div>"
                    "<div class='note' style='margin-top:10px;color:#F4607A'><b>Reglas de supervivencia:</b> "
                    "① corto SOLO con <b>distribución oculta</b> (dinero saliendo y precio aún arriba), nunca solo porque \"esté extendido\". "
                    "② SOXS −3x tiene <b>decay diario brutal</b>: es de <b>días, no semanas</b>. "
                    "③ Si ya cae en vertical, <b>llegas tarde</b> y el rebote te revienta. "
                    "④ Stop duro, tamaño mínimo. Esto es <b>predecir un techo</b>, lo contrario a tu sistema. No es asesoramiento.</div></div>")
        except Exception:
            pass

        html.append("<div class='panel full'><h2>Lectura del mercado y probabilidades</h2>"
                    f"<div class='readbox' style='border-color:{light}55'><div class='read-light' style='background:{light}'></div>"
                    f"<div><div class='read-txt'>{read}</div><div class='read-stance' style='color:{light}'>{stance}</div></div></div>"
                    "<div class='note' style='margin-top:12px'><b>Probabilidades históricas</b> (base, no predicción): de todas las veces que un ETF "
                    "cumplía N de las 3 señales estructurales (<b>precio &gt; media 40s</b>, <b>RS subiendo</b>, <b>gana dinero a 3m</b>), "
                    f"qué % de veces estaba más arriba <b>{fwd} semanas después</b> y cuánto de media. Calculado sobre {probs['weeks']} semanas de tu propio histórico.</div>"
                    f"<table class='pb'><tr><th class='pb-l'></th><th class='pb-v'>prob. subir</th><th class='pb-v'>media {fwd}s</th><th class='pb-n'>muestra</th></tr>{prob_rows}</table>"
                    + (f"<div class='note' style='margin:12px 0 6px'><b>Listos para invertir la semana que viene</b> (puntuación 4–5/5), con el porqué y su probabilidad histórica:</div>{cand}" if cand else "")
                    + "<div class='note' style='margin-top:10px;color:#F4B740'>⚠ Son <b>frecuencias históricas sobre una muestra corta</b> (~"
                    f"{probs['weeks']} semanas), no una predicción. Como el póker: tener buena mano sube las probabilidades, no garantiza ganar la mano. No es asesoramiento.</div></div>")

    # ---- ESTACIONALIDAD (media-quincena: S&P, Nasdaq, Russell) ----
    if season:
        idx_names = list(season.keys())
        base_rows = season[idx_names[0]]["rows"]
        def se_cell(st, invert=False):
            # invert=True para el VIX: ahi "subir" es MIEDO subiendo, o sea malo para bolsa. Sin esta
            # inversion el panel pintaria de verde una quincena en la que historicamente se dispara
            # la volatilidad — justo al reves de lo que significa.
            if not st or st.get("pup") is None:
                return "<td class='se-c' style='color:#3A4658'>—</td>"
            p = st["pup"]
            if invert:
                pcol = "#F4607A" if p >= 60 else "#F4B740" if p >= 50 else "#2FD08A"
                acol = "#9FB0C8" if st["avg"] is None else ("#F49AAC" if st["avg"] >= 0 else "#7FE0B0")
            else:
                pcol = "#2FD08A" if p >= 60 else "#F4B740" if p >= 50 else "#F4607A"
                acol = "#9FB0C8" if st["avg"] is None else ("#7FE0B0" if st["avg"] >= 0 else "#F49AAC")
            return (f"<td class='se-c'><span class='se-pup' style='color:{pcol}'>{p}%</span>"
                    f"<span class='se-avg' style='color:{acol}'>{st['avg']:+.2f}%</span></td>")
        _es_vix = {n: ("VIX" in n.upper()) for n in idx_names}
        head = "".join(f"<th class='se-c'>{esc(n)}</th>" for n in idx_names)
        body = ""
        for i, base in enumerate(base_rows):
            tag = "<span class='se-now'>ahora</span>" if i == 0 else ("<span class='se-next'>próxima</span>" if i == 1 else "")
            cells = "".join(se_cell(season[n]["rows"][i] if i < len(season[n]["rows"]) else None, invert=_es_vix[n]) for n in idx_names)
            rowcls = " class='se-hi'" if i <= 1 else ""
            body += f"<tr{rowcls}><td class='se-l'>{base['label']}{tag}</td>{cells}</tr>"
        yrs = " · ".join(f"{n} {season[n]['years']}a" for n in idx_names)
        _vix_on = any(_es_vix.values())
        html.append("<div class='panel full'><h2>Estacionalidad por media-quincena (S&amp;P · Nasdaq · Russell · Dow"
                    + (" · VIX" if _vix_on else "") + ")</h2>"
                    "<div class='note'>De cada media-quincena (1ª mitad = días 1–15, 2ª = 16–fin), <b>% de años que cerró en positivo</b> "
                    "y <b>retorno medio</b>. <b style='color:#2FD08A'>Verde</b> = quincena históricamente alcista; "
                    "<b style='color:#F4607A'>rojo</b> = floja. Es un <b>viento de fondo</b> probabilístico, no una señal de entrada. "
                    f"Histórico: {yrs}.</div>"
                    + ("<div class='note' style='color:#F4B740'>⚠ La columna <b>VIX (miedo)</b> se lee AL REVÉS: ahí el % es el de años en que "
                       "el VIX <b>subió</b>, y que suba el miedo suele ser malo para la bolsa. Por eso sus colores van invertidos: "
                       "<b style='color:#2FD08A'>verde = el miedo baja</b> (mercado tranquilo), <b style='color:#F4607A'>rojo = el miedo sube</b>. "
                       "El patrón clásico del VIX es suelo en julio y pico en octubre — si la quincena que viene es roja en el VIX, "
                       "es un aviso de que suele venir más volatilidad, no de que el mercado vaya a caer sí o sí.</div>" if _vix_on else "")
                    + f"<table class='se'><tr><th class='se-l'></th>{head}</tr>{body}</table>"
                    "<div class='note' style='margin-top:8px'>El Russell (small caps) y el Nasdaq suelen tener su patrón propio "
                    "(p. ej. fuerza de fin de año en small caps). Por eso conviene mirar el índice del activo que vas a tocar. "
                    "No es asesoramiento.</div></div>")

    # ---- PUNTUACION (SCORING): el entregable de 5 minutos ----
    # historico para "% desde que entro" (racha continua; reinicia si sale y vuelve) — disponible para scoring Y cartera
    try:
        _recs_e = json.load(open(TRACK_FILE, encoding="utf-8")) if os.path.exists(TRACK_FILE) else []
    except Exception as _dege:
        _deg("build_html:7434", _dege)
        _recs_e = []
    try:
        _cur_week = semana_trading(df.index[-1].date())
    except Exception:
        _cur_week = ""
    def _entrada_html(sym, key, in_now):
        try:
            cur_px = float(df[sym].dropna().iloc[-1])
        except Exception:
            return "<span style='color:var(--txt3)'>—</span>"
        res = pct_desde_entrada(_recs_e, sym, key, _cur_week, in_now, cur_px, df)
        if res is None:
            return "<span style='color:var(--txt3)'>—</span>"
        p, wk = res
        col = "#2FD08A" if p >= 0 else "#F4607A"
        return f"<span style='color:{col}'>{p:+.1f}%</span> <span style='color:var(--txt3);font-size:10px'>{wk}s</span>"

    if scores:
        _marked = {r["sym"] for r in scores if r["score"] >= 4}      # "marcado" = señal de compra (>=4/5)
        def sc_col(sc):
            return "#2FD08A" if sc >= 4 else "#F4B740" if sc == 3 else "#F4607A"
        def sc_act(sc):
            return ("comprar" if sc >= 4 else "vigilar" if sc == 3 else "evitar / vender")
        labels = [p[0] for p in scores[0]["parts"]]
        head = "".join(f"<th class='sc-h'>{l}</th>" for l in labels)
        body = ""
        ncols = 1 + len(labels) + 4
        def _sc_row(r):
            cells = ""
            for _, v in r["parts"]:
                cells += (f"<td class='sc-c' style='color:{'#2FD08A' if v else '#5E708A'}'>{'✓' if v else '·'}</td>")
            nm = NAMES.get(r["sym"], (r["sym"], r["sym"], ""))[1]
            cross = "<span class='sc-acc' title='OBV cruzó su media esta semana: presión compradora acelerando'>⚡ acelera</span>" if r["obv_cross"] else ""
            warn = "<span class='sc-warn' title='precio sube pero el dinero sale: distribución oculta'>⚠ distribución</span>" if r.get("distrib") else ""
            col = sc_col(r["score"])
            wk = ""
            try:
                _s = df[r["sym"]].dropna()
                if len(_s) >= 2:
                    _w = (float(_s.iloc[-1]) / float(_s.iloc[-2]) - 1) * 100
                    wk = f"<span style='color:{'#2FD08A' if _w >= 0 else '#F4607A'}'>{_w:+.1f}%</span>"
            except Exception:
                pass
            desde = _entrada_html(r["sym"], "marked", r["score"] >= 4)
            return (f"<tr><td class='sc-name'><b>{r['sym']}</b> <span>{esc(nm)}</span>{cross}{warn}</td>{cells}"
                    f"<td class='sc-c'>{wk}</td>"
                    f"<td class='sc-c'>{desde}</td>"
                    f"<td class='sc-tot' style='color:{col}'>{r['score']}/5</td>"
                    f"<td class='sc-act' style='color:{col}'>{sc_act(r['score'])}</td></tr>")
        for g in GRUPO_ORDEN:
            grp_rows = [r for r in scores if GRUPO.get(r["sym"]) == g]
            if not grp_rows:
                continue
            body += f"<tr><td class='sc-grp' colspan='{ncols}'>{GRUPO_NOMBRE.get(g, g)}</td></tr>"
            for r in grp_rows:
                body += _sc_row(r)
        html.append("<div class='panel full'><h2>Puntuación (scoring) — decide en 5 minutos</h2>"
                    "<div class='note'>Cada ETF suma 1 punto por: <b>precio &gt; su media de 40 semanas</b>, "
                    "<b>RS subiendo</b> (vs S&P), <b>momentum absoluto 3m &gt; 0</b> (gana dinero de verdad), "
                    "<b>OBV por encima de su media</b> y <b>CMF &gt; 0</b> (entra dinero). Ordenado de mayor a menor. "
                    "Regla simple: entra en los <b>4–5/5</b>, vende los que bajen a <b>≤2/5</b>. "
                    "El <b>⚡ acelera</b> marca que el OBV acaba de cruzar su media (entrada temprana). No es asesoramiento.</div>"
                    f"<div class='scrollx'><table class='sc'><tr><th class='sc-name'></th>{head}<th class='sc-h'>sem. curso</th><th class='sc-h'>desde entrada</th><th class='sc-h'>total</th><th class='sc-h'>acción</th></tr>{body}</table></div></div>")

    # ---- CARTERA DE LA SEMANA (Lider + Mejorando + momentum absoluto positivo) ----
    _ord = {"leading": 0, "improving": 1}
    def _cart_key(sd):
        # Líder primero (si el flag está activo), luego por impulso; si no, solo impulso
        if CARTERA_LIDER_PRIMERO:
            return (_ord.get(sd[1]["quad"], 9), -(sd[1]["mom"] or 0))
        return (-(sd[1]["mom"] or 0),)
    _cart_universe = set(SECTORS + THEMATIC + EXTRA)   # la cartera rota sectores/tematicos, no satelites (IWM, TLT, GLD, UUP, HYG)
    chosen_all = [(s, d) for s, d in rrg.items() if d["quad"] in ("leading", "improving") and s in _cart_universe]

    def _abs_mom_sym(sym):
        # momentum absoluto 3m (13 semanas) calculado directamente del precio (vale para satelites)
        if sym not in df.columns:
            return None
        s = df[sym].dropna()
        if len(s) < 14:
            return None
        n = min(13, len(s) - 1)
        return float(s.iloc[-1] / s.iloc[-1 - n] - 1)

    excluded_dm = []
    if CARTERA_DUAL_MOMENTUM:
        keep = []
        for s, d in chosen_all:
            am = _abs_mom_sym(s)
            if am is None or am > 0:        # si no se puede medir, NO se excluye por esto
                keep.append((s, d))
            else:
                excluded_dm.append(s)
        chosen = keep
    else:
        chosen = chosen_all
    # alinear con el scoring: fuera lo que el scoring suspende (< CARTERA_SCORE_MIN) y SIEMPRE la distribución oculta
    excluded_sc, excluded_di, excluded_fl = [], [], []
    if scores:
        sc_map = {r["sym"]: r["score"] for r in scores}
        distrib_set = {r["sym"] for r in scores if r.get("distrib")}
        keep = []
        for s, d in chosen:
            _cmf = (flow or {}).get(s, {}).get("cmf")
            if s in distrib_set:                         # distribución oculta: el dinero sale -> nunca entra (arregla la paradoja ITB)
                excluded_di.append(s)
            elif CARTERA_SCORE_MIN and sc_map.get(s, 0) < CARTERA_SCORE_MIN:
                excluded_sc.append(s)
            elif CARTERA_EXIGE_FLUJO and _cmf is not None and _cmf < -0.05:   # solo si el dinero SALE de verdad (mismo umbral que todo el panel: plano = -0.05..+0.05 no expulsa)
                excluded_fl.append(s)
            else:
                keep.append((s, d))
        chosen = keep
    below_trend = {r["sym"] for r in scores if r.get("above_sma") is False} if scores else set()   # bajo su propia media 40s: se etiqueta, no se expulsa
    chosen.sort(key=_cart_key)
    # set de símbolos que SÍ entran en la cartera de la semana (top-N), para cruzar con la pantalla Operativa
    _cart_sorted = sorted(chosen, key=_cart_key)
    cartera_syms = {s for s, _ in (_cart_sorted[:MAX_POSICIONES] if MAX_POSICIONES else _cart_sorted)}
    # === FUENTE UNICA DE VERDAD ===
    # CARTERA_FINAL = la unica lista que se opera (todos los filtros + tope de posiciones, universo "Todos").
    # TODOS los paneles (veredicto, mesa, track record, candidato, redes, Modo Claude) leen de aqui.
    CARTERA_FINAL = [s for s, _ in (_cart_sorted[:MAX_POSICIONES] if MAX_POSICIONES else _cart_sorted)]

    def _prev_quad(d):
        rs = d.get("ratio_series") or []
        ms = d.get("mom_series") or []
        if len(rs) >= 2 and rs[-2] is not None and ms[-2] is not None and rs[-2] == rs[-2] and ms[-2] == ms[-2]:
            return quad_of(rs[-2], ms[-2])
        return None

    n_wk = len(chosen)
    if n_wk:
        # estado del mercado para el filtro de tendencia
        spy_w = df[BENCH]
        spy_ma = float(spy_w.rolling(min(TREND_MA_WEEKS, len(spy_w)), min_periods=5).mean().iloc[-1])
        bull = spy_w.iloc[-1] >= spy_ma
        wvol = {s: df[s].pct_change().rolling(13, min_periods=4).std().iloc[-1] for s in rrg}

        def _weights(syms):
            w = {}
            for s in syms:
                if PESO == "volatilidad":
                    v = wvol.get(s)
                    w[s] = 1.0 / (v if v and v == v and v > 1e-6 else 0.02)
                elif PESO == "impulso":
                    w[s] = max(0.1, (rrg[s]["mom"] or 100) - 99)
                else:
                    w[s] = 1.0
            tot = sum(w.values()) or 1.0
            return {s: w[s] / tot for s in syms}

        def _cartera_block(keep):
            sel = [(s, d) for s, d in chosen if keep(s)]
            sel.sort(key=_cart_key)
            if MAX_POSICIONES and len(sel) > MAX_POSICIONES:
                sel = sel[:MAX_POSICIONES]
            n = len(sel)
            if not n:
                return "<div class='note'>Nada en Líder/Mejorando esta semana.</div>"
            w = _weights([s for s, _ in sel])
            # regla anti-anomalia: tope de peso por posicion; el resto se declara LIQUIDEZ.
            _capped = {s: min(w[s] * 100, CARTERA_PESO_MAX) for s, _ in sel}
            _liquidez = max(0.0, 100.0 - sum(_capped.values()))
            rows = ""
            for s, d in sel:
                col = QUAD[d["quad"]][1]
                nm = NAMES.get(s, (s, s, ""))[1]
                pct = _capped[s]
                veh = LEV3X.get(s, "—")
                veh_h = f"<span class='wk-x3'>x3 {veh}</span>" if veh and veh != "—" else ""
                top = TOP_HOLDING.get(s, "")
                fs = fresh_stocks(leaders, s)
                if fs:
                    stk = ", ".join((PHASE_INFO.get(r.get("phase"), ("",))[0] + " " + r["sym"] + f" ↑{r['drs']}").strip() for r in fs)
                    top_h = f"<span class='wk-stk' title='acelerando y no en máximos (no extendidas)'>acciones: {esc(stk)}</span>"
                else:
                    top_h = f"<span class='wk-stk' title='accion lider (orientativo)'>lider: {esc(top)}</span>" if top else ""
                isnew = _prev_quad(d) not in ("leading", "improving")
                tag = "<span class='wk-new'>NUEVO</span>" if isnew else "<span class='wk-keep'>mantener</span>"
                trend_warn = ("<span style='font-size:9.5px;color:#5AA9E6;border:1px solid #5AA9E555;border-radius:4px;padding:1px 5px;margin-left:4px;white-space:nowrap' title='rebote por debajo de su media de 40 semanas — mira el gráfico antes de entrar'>⚠ bajo tendencia, mira el gráfico</span>"
                              if (CARTERA_AVISA_TENDENCIA and s in below_trend) else "")
                desde_h = f"<span class='wk-desde' title='rentabilidad del ETF desde que entró en la cartera (se reinicia si sale y vuelve)'>{_entrada_html(s, 'basket', True)}</span>"
                # AVISO DE COHERENCIA: el tema dominante de este ETF, ¿está saliendo en el mercado US?
                coh_warn = ""
                _coh = COHERENCIA_TEMA.get(s)
                if _coh and s not in _coh[1]:            # no compararse consigo mismo
                    tema, espejos = _coh
                    _malos = [e for e in espejos if e in rrg and rrg[e]["quad"] in ("weakening", "lagging")]
                    if _malos and len(_malos) == len([e for e in espejos if e in rrg]):
                        coh_warn = (f"<span style='font-size:9.5px;color:#F4B740;border:1px solid #F4B74055;border-radius:4px;padding:1px 5px;margin-left:4px;white-space:nowrap' "
                                    f"title='Sube como bloque, pero su tema dominante ({tema}) está debilitándose en EE.UU. ({', '.join(_malos)}). "
                                    f"Puede ser fuerza sana (rota hacia value) o entrada por la puerta de atrás de un tema que el sistema rechaza. Mira su composición.'>"
                                    f"⚠ {esc(tema)} flojo en US</span>")
                rows += (f"<div class='wkrow'><span class='wk-sym'><span class='dot' style='background:{col}'></span>{s}</span>"
                         f"<span class='wk-name'>{esc(nm)} · {QUAD[d['quad']][0]}</span>"
                         f"<span class='wk-eur'>{pct:.0f}%</span>{desde_h}{veh_h}{top_h}{trend_warn}{coh_warn}{tag}</div>")
            if _liquidez >= 1:
                rows += (f"<div class='wkrow' style='border-top:1px dashed #2A3A55'><span class='wk-sym'><span class='dot' style='background:#5E708A'></span>💤</span>"
                         f"<span class='wk-name'>LIQUIDEZ — sin señal suficiente donde ponerla</span>"
                         f"<span class='wk-eur' style='color:#9FB0C8'>{_liquidez:.0f}%</span>"
                         f"<span class='wk-stk' title='regla anti-anomalía: cuando los filtros dejan pocas posiciones (como esta semana el flujo), ninguna se lleva más del "
                         f"{CARTERA_PESO_MAX}% — el resto espera en liquidez a que haya más señales. Editable en CARTERA_PESO_MAX.'>"
                         "quedarse fuera también es una posición</span></div>")
            ex = [s for s, d in rrg.items() if keep(s) and d["quad"] not in ("leading", "improving") and _prev_quad(d) in ("leading", "improving")]
            ex_h = (f"<div class='note' style='margin-top:10px;color:#F4607A'><b>Salen esta semana (vender):</b> {', '.join(ex)}</div>" if ex else "")
            pesotxt = {"volatilidad": "ponderado por volatilidad inversa", "impulso": "ponderado por impulso", "igual": "a partes iguales"}[PESO]
            head = (f"<div class='note' style='margin-bottom:8px;color:#2FD08A'>"
                    f"<b>👉 Aquí repartes tu dinero:</b> estas <b>{n}</b> posiciones son la cartera de esta semana, con el <b>% de tu capital</b> que va en cada una "
                    f"(tope {MAX_POSICIONES or '∞'} posiciones, {pesotxt}). "
                    f"<b>acciones:</b> = qué comprar si el ETF no se vende en España o quieres apalancar.</div>")
            return head + rows + ex_h

        bull_banner = ("<div class='note' style='margin-bottom:10px;padding:8px 12px;border-radius:8px;background:rgba(47,208,138,.1);color:#2FD08A'>"
                       "✓ <b>Mercado alcista</b> (S&P por encima de su media de 40 semanas): la estrategia invierte.</div>"
                       if bull else
                       "<div class='note' style='margin-bottom:10px;padding:8px 12px;border-radius:8px;background:rgba(244,96,122,.12);color:#F4607A'>"
                       "⚠ <b>Mercado bajista</b> (S&P por debajo de su media de 40 semanas): el filtro de tendencia recomienda "
                       "<b>liquidez / defensivo</b>. Las posiciones de abajo son orientativas; el backtest estaría en liquidez.</div>")

        sec_html = _cartera_block(lambda s: s in SECTORS)
        all_html = _cartera_block(lambda s: True)
        dm_note = ""
        if excluded_dm:
            dm_note = ("<div class='note' style='margin-top:8px;color:#F4B740'>⚠ <b>Excluidos por momentum absoluto negativo</b> "
                       "(suben respecto al S&P pero <b>pierden dinero</b> en términos absolutos, así que no se entra): "
                       + ", ".join(excluded_dm) + ".</div>")
        if excluded_di:
            dm_note += ("<div class='note' style='margin-top:8px;color:#F4607A'>⚠ <b>Excluidos por distribución oculta</b> "
                        "(el precio sube pero el dinero sale; no se entra aunque roten al alza): " + ", ".join(excluded_di) + ".</div>")
        if excluded_fl:
            dm_note += ("<div class='note' style='margin-top:8px;color:#F4B740'>⚠ <b>Excluidos por flujo negativo</b> (CMF &lt; -0.05, el dinero sale de verdad; el flujo plano no expulsa: "
                        "la cartera exige el mismo flujo que Operativa; editable en CARTERA_EXIGE_FLUJO): " + ", ".join(excluded_fl) + ".</div>")
        if excluded_sc:
            dm_note += ("<div class='note' style='margin-top:8px;color:#F4B740'>⚠ <b>Excluidos por puntuación &lt; "
                        f"{CARTERA_SCORE_MIN}/5</b> (el scoring los marca como «evitar», para que cartera y scoring no se contradigan): "
                        + ", ".join(excluded_sc) + ".</div>")
        html.append("<div class='panel full'><h2>Cartera de la semana (rotación)</h2>"
                    + bull_banner +
                    "<div class='note'>Reparto del <b>% de tu capital</b> entre lo más fuerte en "
                    "<b>Líder o Mejorando</b>, con las optimizaciones activas: <b>filtro de tendencia</b> (solo invierte en "
                    f"mercado alcista), <b>doble momentum</b> (exige también que gane dinero en absoluto), <b>tope de {MAX_POSICIONES or '∞'} posiciones</b> por impulso "
                    "y <b>peso por volatilidad</b>. <b>Solo sectores</b> = menos comisiones; "
                    "<b>Todos</b> incluye temáticos. Los % suman 100 y los aplicas a tu propio capital.</div>"
                    + dm_note +
                    "<div class='viewtabs'>"
                    "<button class='viewtab cartab active' onclick=\"carView('all',this)\">Todos (la cartera que se opera)</button>"
                    "<button class='viewtab cartab' onclick=\"carView('sec',this)\">Solo sectores</button>"
                    "</div>"
                    "<div id='car-all'>" + all_html + "</div>"
                    "<div id='car-sec' style='display:none'>" + sec_html + "</div>"
                    "<script>function carView(v,b){document.getElementById('car-sec').style.display=(v=='sec')?'block':'none';"
                    "document.getElementById('car-all').style.display=(v=='all')?'block':'none';"
                    "document.querySelectorAll('.cartab').forEach(function(x){x.classList.remove('active')});b.classList.add('active');}</script>"
                    "<div class='note' style='margin-top:10px'>Rutina: <b>decides en el cierre del viernes y ejecutas el lunes</b>; "
                    "aguantas la semana y solo tocas lo que cambia (NUEVO / salen). No es asesoramiento.</div></div>")

    # ---- 🧭 GESTOR DE SALIDAS: gestion de posiciones estilo gestor de fondo, sobre la CARTERA_FINAL ----
    try:
        _gsal = compute_gestor_salidas(CARTERA_FINAL, df, daily or {}, rrg, flow, centinela=centinela) if daily else None
        if _gsal:
            gfilas = ""
            for g in _gsal:
                _raz = "<br>".join(f"<span style='color:#8FA3C0'>{i+1}.</span> {esc(rz)}" for i, rz in enumerate(g["razones"]))
                _ptc = "#F4607A" if g["p_techo"] >= 60 else "#F4B740" if g["p_techo"] >= 35 else "#2FD08A"
                gfilas += (f"<tr><td class='se-l'><b>{g['sym']}</b> <span style='color:var(--txt3);font-size:11px'>{esc(NAMES.get(g['sym'], (g['sym'], g['sym']))[1])}</span></td>"
                           f"<td class='se-l' style='color:{g['ecol']};font-weight:700;white-space:nowrap'>{g['est']}</td>"
                           f"<td class='r' style='color:{_ptc};font-weight:700'>{g['p_techo']}%</td>"
                           f"<td class='r' style='color:#8FA3C0'>{g['p_cont']}%</td>"
                           f"<td class='r' style='white-space:nowrap'>{g['stop']}</td>"
                           f"<td class='r' style='white-space:nowrap'>{g['recompra']}</td>"
                           f"<td class='se-l' style='font-size:10.5px;line-height:1.5'>{_raz}</td></tr>")
            html.append("<div class='panel full'><h2>🧭 Gestor de salidas — ¿el tramo alcista se está agotando?</h2>"
                        "<div class='note' style='margin-bottom:6px'>Gestión de posiciones estilo gestor de fondo sobre la cartera del sistema: cada día se auditan <b>cuatro pilares computables</b> — "
                        "tendencia (mínimos crecientes, SMA20/50 diarias, soportes), fuerza (divergencia de RSI, MACD, fuerza relativa vs S&amp;P), volumen (distribución institucional, días de venta con "
                        "volumen) y contexto (cuadrante RRG + régimen del CENTINELA). El 5º pilar (noticias, valoración, resultados) <b>no es computable aquí: ese lo pones tú</b> o el prompt de IA. "
                        "Regla de la casa: <b>no se vende porque «ya subió mucho»</b> — la extensión al alza no suma ni un punto; solo puntúa la evidencia objetiva de deterioro. El objetivo es capturar el "
                        "movimiento grande, no acertar el máximo exacto. Los % son un <b>score de deterioro en escala 0-100, no probabilidades calibradas</b>. En internacionales, la 🌏 acumulación "
                        "extranjera actúa de atenuante (el CMF americano infravalora su compra). Ejemplo vivo: tu entrada en EWJ del viernes se audita aquí cada día. No es asesoramiento.</div>"
                        "<table class='sectbl'><tr><th class='se-l'>POSICIÓN</th><th class='se-l'>ESTADO</th>"
                        "<th class='r' title='score de deterioro 0-100 mostrado como probabilidad ORIENTATIVA de que el techo ya esté formado'>P. TECHO</th>"
                        "<th class='r' title='100 menos el deterioro: orientativa de continuación'>P. SIGUE</th>"
                        "<th class='r' title='el nivel más alto que queda POR DEBAJO del precio: mínimo de 10 sesiones o SMA50 diaria'>STOP</th>"
                        "<th class='r' title='zona orientativa de recompra si corrige: SMA50 diaria o el soporte previo'>RECOMPRA</th>"
                        "<th class='se-l'>LAS 3 RAZONES QUE MÁS PESAN</th></tr>" + gfilas + "</table></div>")
    except Exception:
        pass

    # ---- CANDIDATO DE LA SEMANA (el sistema elige la accion; tu solo ejecutas o no) ----
    candidato = None
    try:
        candidato = compute_candidato(CARTERA_FINAL, leaders, flow, scores, rrg)
    except Exception:
        candidato = None
    if candidato:
        top = candidato["top"]
        st = top["stock"]
        pe, pl, pc = PHASE_INFO.get(st.get("phase"), ("", "—", "#9FB0C8"))
        crows = ""
        for c in candidato["per"]:
            s2 = c["stock"]
            pe2, pl2, pc2 = PHASE_INFO.get(s2.get("phase"), ("", "—", "#9FB0C8"))
            mark = " 🏆" if c is top else ""
            cmf_t = ("<span style='color:#2FD08A'>entra</span>" if (c["cmf"] or 0) > 0.05 else
                     "<span style='color:#F4607A'>sale</span>" if (c["cmf"] or 0) < -0.05 else
                     "<span style='color:#9FB0C8'>plano</span>") if c["cmf"] is not None else "—"
            crows += (f"<tr><td class='se-l'><b>{c['etf']}</b> <span style='color:var(--txt3);font-size:11px'>{esc(NAMES.get(c['etf'], (c['etf'], c['etf'], ''))[1])}</span></td>"
                      f"<td class='se-l'><b style='color:#5B8CFF'>{s2['sym']}</b>{mark}</td>"
                      f"<td class='r' style='font-weight:700'>{s2['rs']}</td>"
                      f"<td class='r' style='color:#7BD88F'>{(s2.get('drs') if s2.get('drs') is not None else 0):+d}</td>"
                      f"<td class='r'>{s2['hi']}%</td>"
                      f"<td class='r' style='color:{pc2};font-size:11px;white-space:nowrap'>{pe2} {pl2}</td>"
                      f"<td class='r' style='font-size:11px'>{cmf_t}</td>"
                      f"<td class='r' style='font-weight:700'>{c['tot']:.0f}</td></tr>")
        html.append("<div class='panel full'><h2>🏆 Candidato de la semana — lo elige el sistema, no tú</h2>"
                    f"<div class='note'>De los ETFs que están <b>esta semana en la cartera</b>, el sistema analiza sus acciones y elige "
                    "<b>una candidata por sector</b> con un criterio fijo (percentil de fuerza + aceleración 3m + fase + no extendida + salud del ETF padre) "
                    "y <b>una ganadora absoluta</b>. Sin discreción: mismas reglas cada semana, para quitarle la decisión al impulso del momento.</div>"
                    f"<div style='margin:10px 0;padding:12px 14px;background:rgba(91,140,255,.08);border:1px solid #5B8CFF44;border-radius:9px'>"
                    f"<span style='font-size:11px;color:#9FB0C8'>ELECCIÓN DE ESTA SEMANA</span><br>"
                    f"<b style='font-size:19px;color:#5B8CFF'>{st['sym']}</b> "
                    f"<span style='color:#9FB0C8'>(vía {top['etf']})</span> · "
                    f"<span style='color:{pc}'>{pe} {pl}</span><br>"
                    f"<span style='font-size:12px;color:var(--txt2)'>{esc(top['why'])}</span></div>"
                    "<div class='scrollx'><table class='se'><tr><th class='se-l'>ETF en cartera</th><th class='se-l'>candidata</th>"
                    "<th class='r'>RS</th><th class='r'>acel. 3m</th><th class='r'>% máx 52s</th><th class='r'>fase</th>"
                    "<th class='r'>flujo ETF</th><th class='r'>puntos</th></tr>" + crows + "</table></div>"
                    "<div class='note' style='margin-top:8px'>Disciplina: la candidata se decide con el <b>cierre confirmado del viernes</b> y se ejecuta el lunes, "
                    "como el resto del sistema. Si la semana siguiente su ETF sale de la cartera, la candidata sale con él. "
                    "Solo hay acciones para los ETFs con desglose (sectores, semis, software, agua, biotech, banca regional, viajes, vivienda, defensa). No es asesoramiento.</div></div>")

    # ---- SEGUIMIENTO SEMANAL DEL SISTEMA (track record real, semana a semana + acumulado) ----
    basket = list(CARTERA_FINAL)          # la MISMA lista que la Cartera de la semana (todos los filtros + tope)
    tperf = None
    if basket:
        try:
            px_now = {k: float(v) for k, v in df.iloc[-1].to_dict().items() if v == v}
            px_now["SPY"] = float(df[BENCH].iloc[-1])
            if "IWM" in df.columns:
                px_now["IWM"] = float(df["IWM"].iloc[-1])
            if nq_close is not None and len(nq_close):
                px_now["QQQ"] = float(nq_close.iloc[-1])
            _marked_now = [r["sym"] for r in (scores or []) if r["score"] >= 4]
            recs = update_track_record(basket, px_now, str(df.index[-1].date()), marked=_marked_now)
            tperf = compute_track_perf(recs)
        except Exception:
            tperf = None
    if tperf:
        def _pct(x):
            return f"{x*100:+.1f}%"
        def _cc(x):
            return "#2FD08A" if x >= 0 else "#F4607A"
        bn = ("SPY", "QQQ", "IWM")
        cum = tperf["cum"]
        has_ew = "ew" in cum and any(w.get("ew") is not None for w in tperf["weeks"])
        rows = ""
        for w in tperf["weeks"][-10:]:
            beat = w["sys"] - w["bench"].get("SPY", 0.0)
            bcells = ""
            for b in bn:
                rb = w["bench"].get(b)
                bcells += (f"<td class='r' style='color:{_cc(rb)}'>{_pct(rb)}</td>" if rb is not None else "<td class='r' style='color:#5E708A'>—</td>")
            ew = w.get("ew")
            ewcell = (f"<td class='r' style='color:{_cc(ew)}'>{_pct(ew)}</td>" if ew is not None else "<td class='r' style='color:#5E708A'>—</td>") if has_ew else ""
            rows += (f"<tr><td class='se-l'>{w['week']}</td>"
                     f"<td class='r' style='color:{_cc(w['sys'])};font-weight:700'>{_pct(w['sys'])}</td>{ewcell}{bcells}"
                     f"<td class='r' style='color:{_cc(beat)}'>{_pct(beat)}</td></tr>")
        cumcells = "".join(f"<td class='r' style='color:{_cc(cum.get(b,0))};font-weight:700'>{_pct(cum.get(b,0))}</td>" for b in bn)
        ewcum = cum.get("ew", 0.0)
        ewcumcell = (f"<td class='r' style='color:{_cc(ewcum)};font-weight:700'>{_pct(ewcum)}</td>") if has_ew else ""
        beat_cum = cum["sys"] - cum.get("SPY", 0.0)
        beat_ew = cum["sys"] - ewcum
        cumrow = (f"<tr style='border-top:2px solid #1C2740'><td class='se-l'><b>ACUMULADO ({tperf['n']} sem)</b></td>"
                  f"<td class='r' style='color:{_cc(cum['sys'])};font-weight:800'>{_pct(cum['sys'])}</td>{ewcumcell}{cumcells}"
                  f"<td class='r' style='color:{_cc(beat_cum)};font-weight:700'>{_pct(beat_cum)}</td></tr>")
        ewth = "<th class='r'>sect.EW</th>" if has_ew else ""
        verdict = (f"bate al S&P por {_pct(beat_cum)}" if beat_cum >= 0 else f"por debajo del S&P ({_pct(beat_cum)})")
        ewphrase = ""
        if has_ew:
            ewverd = (f"<b style='color:#2FD08A'>bate por {_pct(beat_ew)}</b>" if beat_ew >= 0
                      else f"<b style='color:#F4607A'>pierde por {_pct(beat_ew)}</b>")
            ewphrase = (f" · vs <b>sectores equiponderados</b> {_pct(ewcum)}: la <b>selección</b> {ewverd} "
                        "a tener los 11 sectores por igual")
        head = (f"Desde que registras ({tperf['n']} semanas): <b style='color:{_cc(cum['sys'])}'>sistema {_pct(cum['sys'])}</b> · "
                f"SPY {_pct(cum.get('SPY',0))} · QQQ {_pct(cum['QQQ']) if 'QQQ' in cum else '—'} · IWM {_pct(cum['IWM']) if 'IWM' in cum else '—'} → "
                f"<b style='color:{_cc(beat_cum)}'>{verdict}</b>{ewphrase}")
        pend = tperf["pending"]
        # ---- GRAFICO DOSIER: curva acumulada sistema vs SPY (incluye entradas Y salidas: la cadena real) ----
        graf = ""
        try:
            wks = tperf["weeks"]
            if len(wks) >= 2:
                serie_sys = [0.0] + [w["cum_sys"] * 100 for w in wks]
                serie_spy = [0.0] + [w.get("cum_SPY", 0) * 100 for w in wks]
                labels = ["inicio"] + [w["week"].split("-W")[-1] + "'" for w in wks]
                W, H, ML, MT, MB, MR = 720, 300, 46, 24, 46, 16
                lo = min(min(serie_sys), min(serie_spy), 0) - 1
                hi = max(max(serie_sys), max(serie_spy), 0) + 1
                rng = (hi - lo) or 1
                def X(i): return ML + i * (W - ML - MR) / (len(serie_sys) - 1)
                def Y(v): return MT + (hi - v) / rng * (H - MT - MB)
                def path(serie): return "M" + " L".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(serie))
                area_sys = path(serie_sys) + f" L{X(len(serie_sys)-1):.1f},{Y(lo):.1f} L{X(0):.1f},{Y(lo):.1f} Z"
                y0 = Y(0)
                # rejilla horizontal
                grid = ""
                for gv in range(int(lo), int(hi) + 1):
                    if gv % max(1, int(rng / 5)) == 0:
                        gy = Y(gv)
                        grid += f"<line x1='{ML}' y1='{gy:.1f}' x2='{W-MR}' y2='{gy:.1f}' stroke='#1C2740' stroke-width='1'/>"
                        grid += f"<text x='{ML-6}' y='{gy+3:.1f}' fill='#5E708A' font-size='9' text-anchor='end'>{gv:+d}%</text>"
                # etiquetas X (cada ~2)
                xlabels = ""
                step = max(1, len(labels) // 8)
                for i in range(0, len(labels), step):
                    xlabels += f"<text x='{X(i):.1f}' y='{H-MB+16:.1f}' fill='#5E708A' font-size='9' text-anchor='middle'>{esc(labels[i])}</text>"
                _fsys, _fspy = serie_sys[-1], serie_spy[-1]
                _csys = "#2FD08A" if _fsys >= _fspy else "#F4607A"
                graf = (f"<div style='background:#0A0E17;border:1px solid #1C2740;border-radius:10px;padding:14px 10px 6px;margin:10px 0'>"
                        f"<svg viewBox='0 0 {W} {H}' style='width:100%;height:auto;font-family:system-ui'>"
                        f"<defs><linearGradient id='gsys' x1='0' y1='0' x2='0' y2='1'>"
                        f"<stop offset='0%' stop-color='{_csys}' stop-opacity='0.28'/><stop offset='100%' stop-color='{_csys}' stop-opacity='0'/></linearGradient></defs>"
                        + grid +
                        f"<line x1='{ML}' y1='{y0:.1f}' x2='{W-MR}' y2='{y0:.1f}' stroke='#3A4A63' stroke-width='1' stroke-dasharray='3,3'/>"
                        f"<path d='{area_sys}' fill='url(#gsys)'/>"
                        f"<path d='{path(serie_spy)}' fill='none' stroke='#8FA3C0' stroke-width='2' stroke-dasharray='5,4'/>"
                        f"<path d='{path(serie_sys)}' fill='none' stroke='{_csys}' stroke-width='2.5'/>"
                        f"<circle cx='{X(len(serie_sys)-1):.1f}' cy='{Y(_fsys):.1f}' r='4' fill='{_csys}'/>"
                        f"<circle cx='{X(len(serie_spy)-1):.1f}' cy='{Y(_fspy):.1f}' r='3.5' fill='#8FA3C0'/>"
                        f"<text x='{W-MR-2:.1f}' y='{Y(_fsys)-8:.1f}' fill='{_csys}' font-size='12' font-weight='700' text-anchor='end'>Sistema {_fsys:+.1f}%</text>"
                        f"<text x='{W-MR-2:.1f}' y='{Y(_fspy)+14:.1f}' fill='#8FA3C0' font-size='11' text-anchor='end'>S&amp;P 500 {_fspy:+.1f}%</text>"
                        + xlabels +
                        "</svg>"
                        "<div style='display:flex;gap:18px;justify-content:center;font-size:11px;color:#9FB0C8;padding:4px 0 2px'>"
                        f"<span><span style='display:inline-block;width:14px;height:3px;background:{_csys};vertical-align:middle'></span> Cartera del sistema (rota cada semana)</span>"
                        "<span><span style='display:inline-block;width:14px;height:2px;background:#8FA3C0;vertical-align:middle'></span> S&amp;P 500 (comprar y mantener)</span>"
                        "</div></div>")
        except Exception:
            graf = ""
        html.append("<div class='panel full'><h2>📈 Track record del sistema — rendimiento acumulado verificable</h2>"
                    f"<div class='note'>{head}</div>"
                    + graf +
                    "<div class='note' style='margin:6px 0'>Esta curva es la <b>cadena real</b>: cada semana la cartera se recompone y se encadena su rendimiento — "
                    "incluye <b>las posiciones que entraron Y las que salieron</b>, ganaran o perdieran. Es lo que de verdad habría hecho tu dinero siguiendo el sistema, "
                    "no una selección de aciertos. Por eso puede diferir de la tabla de posiciones actuales de la pestaña Redes.</div>"
                    "<div class='scrollx'><table class='se'><tr><th class='se-l'>semana</th><th class='r'>sistema</th>"
                    + ewth + "<th class='r'>SPY</th><th class='r'>QQQ</th><th class='r'>IWM</th><th class='r'>vs S&amp;P</th></tr>"
                    + rows + cumrow + "</table></div>"
                    f"<div class='note' style='margin-top:8px'>La <b>cesta del sistema</b> = las posiciones de la <b>Cartera de la semana</b> (equiponderadas), rotada cada semana. "
                    "<b>sect.EW</b> = los <b>11 sectores SPDR equiponderados</b> (sin rotar): es la referencia honesta de si tu <b>selección</b> aporta algo o si te bastaría con tenerlos todos por igual. "
                    f"En curso ({esc(pend['week'])}): <b>{esc(', '.join(pend['basket']) or '—')}</b> — su resultado se medirá en el próximo registro. "
                    "<b>Paper-track honesto</b>: sin comisiones, impuestos ni slippage; se construye solo si ejecutas la herramienta cada semana. No es asesoramiento.</div></div>")
    elif basket:
        html.append("<div class='panel full'><h2>📈 Track record del sistema — rendimiento acumulado verificable</h2>"
                    f"<div class='note'>Acabo de registrar la cesta de esta semana (<b>{esc(', '.join(basket))}</b>). "
                    "El seguimiento se construye <b>ejecutando la herramienta cada semana</b>: la próxima vez compararé esta cesta con <b>SPY / QQQ / IWM</b> "
                    "y verás, semana a semana y en acumulado, si el sistema bate al mercado. No es asesoramiento.</div></div>")

    # ---- SINTETIZAR FIW: acciones de agua ordenadas por fuerza relativa (para España, donde no se compra el ETF) ----
    if leaders and leaders.get("FIW"):
        _wn = {"ROP":"Roper","FERG":"Ferguson","MLI":"Mueller Ind.","AWK":"American Water","WAT":"Waters",
               "XYL":"Xylem","VLTO":"Veralto","ECL":"Ecolab","IEX":"IDEX","PNR":"Pentair","A":"Agilent",
               "IDXX":"IDEXX Labs","J":"Jacobs","MAS":"Masco","STN":"Stantec","ACM":"AECOM","FELE":"Franklin Electric",
               "WMS":"Adv. Drainage","WTS":"Watts Water","MWA":"Mueller Water","TTEK":"Tetra Tech","ZWS":"Zurn Elkay",
               "CNM":"Core & Main","BMI":"Badger Meter","ITRI":"Itron"}
        wrows = ""
        for r in leaders["FIW"]:
            acc = "—"
            if r["drs"] is not None:
                if r["drs"] >= 8:
                    acc = f"<span style='color:#2FD08A'>⚡ +{r['drs']}</span>"
                elif r["drs"] <= -8:
                    acc = f"<span style='color:#F4607A'>▼ {r['drs']}</span>"
                else:
                    acc = f"<span style='color:var(--txt3)'>{r['drs']:+d}</span>"
            rscol = "#2FD08A" if r["rs"] >= 70 else ("#F4B740" if r["rs"] >= 40 else "#9FB0C8")
            hicol = "#2FD08A" if r["hi"] >= 90 else ("#F4B740" if r["hi"] >= 75 else "#9FB0C8")
            cfd = (" <span class='lchip' style='background:#13351F;border-color:#2FD08A55;color:#2FD08A;font-size:10px;padding:1px 5px'>CFD XTB</span>"
                   if r["sym"] in XTB_CFD_AGUA else "")
            ph = r.get("phase"); pe, pl, pc = PHASE_INFO.get(ph, ("", "—", "#9FB0C8"))
            wrows += (f"<tr><td class='se-l'><b>{r['sym']}</b> <span style='color:var(--txt3);font-size:11px'>{esc(_wn.get(r['sym'],''))}</span>{cfd}</td>"
                      f"<td class='r' style='color:{rscol};font-weight:700'>{r['rs']}</td>"
                      f"<td class='r' style='color:{hicol}'>{r['hi']}%</td>"
                      f"<td class='r'>{acc}</td>"
                      f"<td class='r' style='color:{pc};font-size:11px;white-space:nowrap'>{pe} {pl}</td></tr>")
        topn = [r["sym"] for r in leaders["FIW"][:6]]
        html.append("<div class='panel full'><h2>Sintetiza FIW: agua por fuerza relativa</h2>"
                    "<div class='note'>El ETF FIW no se compra en España, pero <b>sus acciones US sí</b> (XTB/DEGIRO; lo que la UE bloquea es el ETF, no la acción). "
                    "Aquí van las empresas del fondo <b>ordenadas por percentil de fuerza relativa frente a todo el mercado</b> (no por tamaño): "
                    "<b>percentil</b> 1–99 (99 = de las más fuertes del mercado), <b>% máx 52s</b> (cerca de 100 = en máximos), "
                    "<b>acel. 3m</b> = cuánto ha subido su percentil en 3 meses (⚡ acelerando, ▼ perdiendo fuerza). "
                    f"Para sintetizar el ETF quedándote con lo mejor, una vía es las de mayor percentil — ahora mismo: <b>{esc(', '.join(topn))}</b>. "
                    "Equipondéralas y revisa cada semana: rota la que caiga de percentil. Ojo: 5–8 acciones es <b>más concentrado</b> que las 39 del ETF, "
                    "así que más riesgo idiosincrático; cuantas más metas, más te pareces al fondo. "
                    "La etiqueta <span style='color:#2FD08A'>CFD XTB</span> marca las que creo disponibles como CFD en XTB (para apalancar agua, que no tiene ETF x3); "
                    "<b>es una lista de partida que debes verificar</b> en el buscador de XTB, porque su catálogo cambia y no puedo comprobarlo en vivo. No es asesoramiento.</div>"
                    "<div class='note' style='margin-top:6px'><b>Fase</b> (modelo de 4 fases): "
                    "🟦 base/acumulación (lateral abajo, dinero entrando callado, antes de arrancar) · 🟢 subiendo (tendencia sana, aquí quieres estar) · "
                    "🟠 distribución (lateral pegada a máximos, techo formándose y el dinero saliendo — <b>la trampa de MLI</b>) · 🔴 cayendo · ⚪ lateral medio sin sesgo claro. "
                    "Se calcula con la media de 30 semanas, dónde está en su rango de 52s y si su fuerza acelera. Es un <b>mapa de probabilidad, no una predicción</b>: una base puede romper para arriba o para abajo; el flujo inclina la balanza, no la garantiza.</div>"
                    "<div class='scrollx'><table class='se'><tr><th class='se-l'>empresa</th><th class='r'>percentil RS</th>"
                    "<th class='r'>% máx 52s</th><th class='r'>acel. 3m</th><th class='r'>fase</th></tr>" + wrows + "</table></div></div>")

    # ---- PLAN DE ROTACION DE MI CARTERA (compara tu cartera real con las señales) ----
    mi_plan = compute_mi_cartera_plan(MI_CARTERA, rrg, scores, flow, chosen, df)
    if mi_plan:
        mrows = ""
        _n_trampa = 0
        for r in mi_plan["rows"]:
            est = (f"{r.get('quad','—')}" + (f" · {r['sc']}/5" if r.get("sc") is not None else "")) if r["base"] else "—"
            eur = f"{r['eur']:,.0f} €" if isinstance(r["eur"], (int, float)) else esc(str(r["eur"]))
            _dd = r.get("dd_pos")
            ddcell = (f"<span style='color:{'#F4607A' if _dd <= -10 else '#F4B740' if _dd <= -3 else '#9FB0C8'}'>{_dd:.0f}%</span>" if _dd is not None else "—")
            motivo = esc(r["why"])
            if r.get("corte"):
                _tipo, _ccol, _ctxt = r["corte"]
                if _tipo == "trampa":
                    _n_trampa += 1
                motivo += f"<br><span style='color:{_ccol};font-size:10.5px'>{esc(_ctxt)}</span>"
            mrows += (f"<tr><td class='se-l'><b>{esc(r['tk'])}</b>{esc(r.get('via',''))}</td>"
                      f"<td class='r' style='color:#9FB0C8'>{esc(r['broker'])}</td>"
                      f"<td class='r'>{eur}</td><td class='r'>{ddcell}</td><td class='r' style='color:#9FB0C8;font-size:11px'>{esc(est)}</td>"
                      f"<td class='r'><b style='color:{r['col']}'>{esc(r['act'])}</b></td>"
                      f"<td class='se-l' style='font-size:11px;color:var(--txt2)'>{motivo}</td></tr>")
        rot = ""
        if mi_plan["rotar_hacia"]:
            chips = " ".join(f"<span class='lchip'><b>{r['sym']}</b> <span style='color:var(--txt3)'>{r['quad']}"
                             + (f" {r['sc']}/5" if r["sc"] is not None else "") + "</span></span>" for r in mi_plan["rotar_hacia"])
            rot = (f"<div style='margin-top:10px'><b style='color:#5B8CFF'>ROTAR HACIA</b> "
                   "<span class='note' style='display:inline'>(recomendadas que aún no tienes):</span><div class='lchips' style='margin-top:6px'>" + chips + "</div></div>")
        html.append("<div class='panel full'><h2>🩺 Plan de rotación de mi cartera — cortar o aguantar</h2>"
                    f"<div class='note'>Compara <b>tus posiciones reales</b> (editables arriba del archivo en <code>MI_CARTERA</code>) con las señales de hoy. "
                    f"Total declarado: <b>{mi_plan['total']:,.0f} €</b> · mantener {mi_plan['n_mantener']} · vender/rotar {mi_plan['n_vender']}"
                    + (f" · <b style='color:#F4607A'>{_n_trampa} en trampa de esperanza</b>" if _n_trampa else "") + ". "
                    "La columna <b>caída</b> es cuánto ha bajado desde su máximo de 52s. El motivo te dice si el sistema ordena <b>CORTAR</b> "
                    "(cae y el dinero sigue saliendo) o si hay <b>base para aguantar con stop</b> (el flujo ya frenó). "
                    "Las acciones y apalancados se evalúan por su ETF de referencia (vía …).</div>"
                    "<div class='scrollx'><table class='se'><tr><th class='se-l'></th><th class='r'>broker</th><th class='r'>importe</th>"
                    "<th class='r'>caída</th><th class='r'>estado</th><th class='r'>acción</th><th class='se-l'>motivo</th></tr>"
                    + mrows + "</table></div>" + rot +
                    "<div class='note' style='margin-top:10px;color:#F4B740'>⚠ La <b>trampa de esperanza</b>: mantener algo que cae «a ver si recupera» mientras el dinero sigue saliendo "
                    "es cómo una pérdida pequeña se hace grande. El sistema no siente apego: si el flujo confirma la salida, corta. "
                    "Esto aplica a tu <b>parte de rotación</b>, no a la liquidez de reserva. Rotar mucho genera comisiones y plusvalías que tributan. No es asesoramiento.</div></div>")

    # ---- APALANCAMIENTO CONSOLIDADO (XTB + Robinhood + DEGIRO) + STRESS-TEST ----
    apal = None
    try:
        apal = compute_apalancamiento(MI_CARTERA, BROKER_INFO)
    except Exception:
        apal = None
    if apal:
        _e = lambda v: f"{v:,.0f} €".replace(",", ".")
        brows = ""
        for b in apal["brokers"]:
            esc5, esc10, esc20 = (b["esc"].get(dd) for dd in STRESS_DD)
            def _cell(e):
                if not e:
                    return "<td class='r'>—</td>"
                col = "#F4607A" if e["estado"] in ("STOP-OUT", "margin call", "cuenta a cero") else "#F4B740" if e["estado"] != "ok" else "#9FB0C8"
                niv = f" · nivel {e['nivel_after']:.0f}%" if e["nivel_after"] is not None else ""
                tag = f"<br><b style='color:{col};font-size:10px'>{e['estado'].upper()}</b>" if e["estado"] != "ok" else ""
                return (f"<td class='r' style='white-space:nowrap'><span style='color:#F4607A'>{e['loss']:+,.0f} €</span> "
                        f"<span style='color:#5E708A;font-size:10px'>({e['pct']:.0f}%{niv})</span>{tag}</td>").replace(",", ".")
            lev_col = "#F4607A" if b["lev_ef"] >= 2.5 else "#F4B740" if b["lev_ef"] >= 1.5 else "#2FD08A"
            extra = ""
            info = b.get("info") or {}
            if info.get("nivel_margen") is not None:
                mcol = "#F4607A" if info["nivel_margen"] < 120 else "#F4B740" if info["nivel_margen"] < 200 else "#2FD08A"
                extra = f"<br><span style='color:{mcol};font-size:10px'>nivel margen HOY: {info['nivel_margen']:.0f}% · libre {info.get('margen_libre', 0):.0f} €</span>"
            brows += (f"<tr><td class='se-l'><b>{esc(b['broker'])}</b>{extra}</td>"
                      f"<td class='r'>{_e(b['equity'])}</td>"
                      f"<td class='r'>{_e(b['expo'])}</td>"
                      f"<td class='r' style='color:{lev_col};font-weight:700'>{b['lev_ef']:.2f}×</td>"
                      + _cell(esc5) + _cell(esc10) + _cell(esc20) + "</tr>")
        tcol = "#F4607A" if apal["lev_ef"] >= 2 else "#F4B740" if apal["lev_ef"] >= 1.4 else "#2FD08A"
        trow = (f"<tr style='border-top:2px solid #1C2740'><td class='se-l'><b>TOTAL</b></td>"
                f"<td class='r'><b>{_e(apal['tot_eur'])}</b></td>"
                f"<td class='r'><b>{_e(apal['tot_expo'])}</b></td>"
                f"<td class='r' style='color:{tcol};font-weight:800'>{apal['lev_ef']:.2f}×</td>"
                + "".join(f"<td class='r' style='color:#F4607A;font-weight:700'>{apal['tot_stress'][dd]:+,.0f} €</td>".replace(",", ".") for dd in STRESS_DD)
                + "</tr>")
        xtb_i = (BROKER_INFO or {}).get("XTB", {})
        warn_xtb = ""
        if xtb_i.get("nivel_margen") is not None and xtb_i["nivel_margen"] < 120:
            warn_xtb = (f"<div class='note' style='margin-top:8px;color:#F4607A'>🚨 <b>XTB en zona crítica</b>: nivel de margen "
                        f"{xtb_i['nivel_margen']:.1f}% y solo {xtb_i.get('margen_libre', 0):.0f} € libres. Sin colchón, una caída moderada "
                        "activa cierres forzosos <b>en el peor momento</b> (justo cuando tu plan de liquidez diría comprar). "
                        "Prioridad antes que cualquier rotación: liberar margen (reducir posiciones CFD) o aportar garantías.</div>")
        html.append("<div class='panel full'><h2>⚖️ Apalancamiento consolidado — los 3 brokers juntos</h2>"
                    "<div class='note'>Lo que ningún broker te enseña: tu <b>exposición real total</b> (importe × apalancamiento) y qué le pasaría "
                    "al equity de cada cuenta si el S&amp;P cae <b>−5% / −10% / −20%</b> (con beta aproximada por tipo de activo: "
                    "cripto ~1.8×, plata ~0.8×, bonos ~−0.2×, resto ~1×). Es un choque de <b>1 día</b>: en una caída de varios días con "
                    "volatilidad, los productos de <b>reset diario</b> (3x/5x) pierden <b>más</b> por el decay — este cuadro es el suelo optimista.</div>"
                    "<div class='scrollx'><table class='se'><tr><th class='se-l'>broker</th><th class='r'>equity</th>"
                    "<th class='r'>exposición</th><th class='r'>apalanc. efectivo</th>"
                    + "".join(f"<th class='r'>S&amp;P {dd}%</th>" for dd in STRESS_DD)
                    + "</tr>" + brows + trow + "</table></div>"
                    + warn_xtb +
                    "<div class='note' style='margin-top:8px'>Regla que hemos hablado: si quieres usar margen de IBKR (tu 10% de pólvora), "
                    "este cuadro tiene que seguir en verde <b>en el escenario −20%</b> DESPUÉS de añadirlo. Margen sobre productos ya apalancados "
                    "= apalancamiento al cuadrado. Los importes de posición se editan arriba en <code>MI_CARTERA</code> y los datos de margen en "
                    "<code>BROKER_INFO</code>. No es asesoramiento.</div></div>")

    # ---- VEREDICTO DE HOY (resumen de un vistazo, se inserta arriba) ----
    sem_short = stance.split("—")[0].strip() or "—"
    reg_short = regime["label"].split(" / ")[0]
    mkt = "alcista" if bull else "bajista"
    top_pos = list(CARTERA_FINAL)          # identica a la Cartera de la semana: una sola verdad
    if not bull:
        cartera_txt = "liquidez — el filtro de tendencia no invierte en mercado bajista"
    elif top_pos:
        cartera_txt = ", ".join(top_pos)
    else:
        cartera_txt = "nada claro — mantener liquidez"
    breadth_pct = round(100 * sum(1 for s in rrg if rrg[s]["ratio"] >= 100) / max(1, len(rrg)))
    if not bull:
        ojo = "el S&P está por debajo de su media de 40s: prioriza <b>liquidez / defensivo</b>."
    elif excluded_di:
        ojo = f"<b>distribución oculta</b> (el dinero sale) en {', '.join(excluded_di)} — no te fíes de su subida."
    elif leaving:
        ojo = f"perdiendo liderazgo: <b>{', '.join(leaving[:4])}</b> (recoger / no añadir)."
    elif breadth_pct < 40:
        ojo = f"amplitud estrecha ({breadth_pct}%): la subida la sostienen pocos sectores, sé selectivo."
    else:
        ojo = "sin alertas mayores; sigue el plan."
    liq = ""
    if plan:
        nxt = next((r for r in plan["rungs"] if not r["hit"]), None)
        if nxt:
            liq = f"S&P {plan['dd']:.1f}% de máximos · próximo escalón −{nxt['thr']}% (faltan {(nxt['thr'] + plan['dd']):.1f}%)."
    verdict_html = (
        "<div class='panel full verdict'><h2>Veredicto de hoy</h2>"
        + ("<div style='margin:0 0 10px 0;padding:9px 12px;background:rgba(244,183,64,.12);border:1px solid #F4B74066;border-radius:8px;font-size:12.5px;color:#F4B740'>"
           "⚠ <b>Cierre de media semana</b> — el sistema decide con el <b>cierre del VIERNES</b>. Hoy es solo <b>observación</b>: mira los giros y prepárate, "
           "pero <b>no ejecutes rotaciones</b> hasta el viernes. El track record de la semana quedó congelado en su primer registro; esta ejecución no lo altera.</div>"
           if media_semana else "")
        + f"<div class='vrow'><span class='vk' style='background:{light}'>¿Invierto?</span>"
        f"<span><b style='color:{light}'>{esc(sem_short)}</b> · {esc(reg_short)}, {esc(risk['label'])}, mercado {mkt}</span></div>"
        f"<div class='vrow'><span class='vk' style='background:#5B8CFF'>Compra</span><span>{esc(cartera_txt)}</span></div>"
        f"<div class='vrow'><span class='vk' style='background:#F4B740'>Ojo</span><span>{ojo}</span></div>"
        + (f"<div class='vrow'><span class='vk' style='background:#93A4BC'>Liquidez</span><span>{liq}</span></div>" if liq else "")
        + "<div class='note' style='margin-top:6px'>Resumen de un vistazo. Debajo tienes la decisión completa (scoring, cartera, entrada temprana) "
          "y, plegado, todo el detalle (RRG, flujo, rankings). No es asesoramiento.</div></div>")

    # ---- ANALISIS IA (opcional) + boton para analizar con IA ----
    snap = state_summary(rrg, risk, regime, breadth, plan, flow)
    snap_js = (snap.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
                   .replace("`", "'").replace("\n", "\\n"))
    ai_inner = ""
    if ai_text:
        ai_inner = f"<div class='ai-box'>{esc(ai_text)}</div>"
    else:
        ai_inner = ("<div class='note'>Este panel calcula los datos (no es IA en tiempo real). Pulsa para que una IA "
                    "te analice la foto de hoy: copia el resumen y lo pegas en Claude/ChatGPT, o abre Claude directamente.</div>")
    html.append("<div class='panel full'><h2>Análisis con IA</h2>" + ai_inner +
                "<div style='margin-top:10px;display:flex;gap:8px;flex-wrap:wrap'>"
                f"<button class='ai-btn' onclick=\"navigator.clipboard.writeText('Analiza esta rotacion sectorial (datos de cierre):\\n\\n{snap_js}'); this.textContent='Copiado, pegalo en tu IA';\">Copiar resumen para IA</button>"
                "<a class='ai-btn alt' href='https://claude.ai/new' target='_blank' rel='noopener'>Abrir Claude</a>"
                "</div></div>")

    # ---- TIRA RESUMEN (flujo + alertas) justo encima del RRG ----
    entra, sale, cuida = [], [], []
    climax_l, capit_l, noct_l = [], [], []
    for sym, fdat in (flow or {}).items():
        dv = fdat.get("diverg"); lab = fdat.get("label")
        if dv == "acumulacion oculta":
            entra.append((sym, True))
        elif lab == "Acumulacion":
            entra.append((sym, False))
        if dv == "distribucion oculta":
            cuida.append(sym)
        elif lab == "Distribucion":
            sale.append(sym)
        if fdat.get("acum_ext"):
            noct_l.append((sym, fdat.get("noct20"), fdat.get("cmf")))
        if fdat.get("clima") == "climax":
            climax_l.append((sym, fdat.get("ret1d"), fdat.get("zday"), fdat.get("clima_hace"), fdat.get("clima_vol")))
        elif fdat.get("clima") == "capitulacion":
            capit_l.append((sym, fdat.get("ret1d"), fdat.get("zday"), fdat.get("clima_hace"), fdat.get("clima_vol")))
    noct_l.sort(key=lambda x: -(x[1] or 0))
    climax_l.sort(key=lambda x: ((x[3] if x[3] is not None else 9), -(abs(x[2]) if x[2] is not None else 0)))
    capit_l.sort(key=lambda x: ((x[3] if x[3] is not None else 9), -(abs(x[2]) if x[2] is not None else 0)))
    def fchips(items, col, ring=0):
        out = ""
        for it in items:
            sym = it[0] if isinstance(it, tuple) else it
            strong = it[1] if isinstance(it, tuple) else False
            mark = ""
            if ring == 2:   # doble circulo rojo
                mark = "<span class='ring2'></span>"
            elif strong:
                mark = "<span class='ring1'></span>"
            out += f"<span class='fchip' style='border-color:{col}55;color:{col}'>{mark}{sym}</span>"
        return out or "<span class='qempty'>—</span>"
    alert_chips = ""
    for sym, kind, txt in (alerts or [])[:8]:
        acol = {"warn": "#F4B740", "in": "#2FD08A", "lead": "#5B8CFF", "down": "#F4607A"}.get(kind, "#93A4BC")
        alert_chips += f"<span class='fchip' style='border-color:{acol}55;color:{acol}' title='{esc(txt)}'>{sym}</span>"
    def climachips(items, col):
        out = ""
        for sym, r1, zd, hc, cv in items[:8]:
            _dia = clima_dia(hc)
            _volt = f", volumen {cv}×" if (cv is not None and cv >= CLIMA_VOL_FUERTE) else ""
            tt = f"{sym}: {r1:+.1f}% {_dia} (z {zd:+.1f} sobre su volatilidad típica{_volt})" if r1 is not None else sym
            out += (f"<span class='fchip' style='border-color:{col}66;color:{col}' title='{esc(tt)}'>"
                    f"<span style='display:inline-block;width:8px;height:8px;border-radius:50%;border:2px dashed {col};margin-right:3px;vertical-align:-1px'></span>"
                    f"{sym} <span style='opacity:.75;font-size:9px'>{(f'{r1:+.0f}% {_dia}' if r1 is not None else '')}</span></span>")
        return out or "<span class='qempty'>—</span>"
    def noctchips(items):
        out = ""
        for sym, nv, cm in items[:8]:
            _cmv = f"{cm:+.2f}" if cm is not None else "n/d"
            tt = f"{sym}: gap nocturno {nv:+.1f}% en 20 sesiones con CMF {_cmv} — la compra ocurre en su bolsa local (Asia/Europa); el CMF americano no la ve. El punto ciego que ocultó a China, ya vigilado."
            out += (f"<span class='fchip' style='border-color:#4CC2E066;color:#4CC2E0' title='{esc(tt)}'>🌏 {sym} "
                    f"<span style='opacity:.75;font-size:9px'>{nv:+.1f}%</span></span>")
        return out or "<span class='qempty'>—</span>"
    html.append("<div class='panel full'><h2>Resumen visual: flujo y rotación</h2>"
                "<div class='fgrid'>"
                "<div class='fcol'><div class='fhead' style='color:#2FD08A'>● Entra dinero (acumulación)</div>"
                f"<div class='fchips'>{fchips(entra, '#2FD08A')}</div></div>"
                "<div class='fcol'><div class='fhead' style='color:#F4607A'>◎ Cuidado: distribución oculta</div>"
                f"<div class='fchips'>{fchips(cuida, '#F4607A', ring=2)}</div></div>"
                "<div class='fcol'><div class='fhead' style='color:#F4B740'>🟡 Clímax de subida (ojo)</div>"
                f"<div class='fchips'>{climachips(climax_l, '#F4B740')}</div></div>"
                "<div class='fcol'><div class='fhead' style='color:#B980FF'>🟣 Capitulación (vigilar suelo)</div>"
                f"<div class='fchips'>{climachips(capit_l, '#B980FF')}</div></div>"
                "<div class='fcol'><div class='fhead' style='color:#4CC2E0'>🌏 Acum. extranjera (nocturno)</div>"
                f"<div class='fchips'>{noctchips(noct_l)}</div></div>"
                "<div class='fcol'><div class='fhead' style='color:#F4B740'>Alertas de rotación</div>"
                f"<div class='fchips'>{alert_chips or '<span class=qempty>sin giros</span>'}</div></div>"
                "</div>"
                "<div class='note' style='margin-top:8px'>El <b>◎ doble círculo rojo</b> marca distribución oculta (precio sube, dinero sale: cuidado). "
                "<b style='color:#F4B740'>🟡 Clímax</b> = vela anómala al alza en las <b>últimas 3 sesiones</b> (≥2.2× la volatilidad diaria típica del propio ETF): tu regla — si algo sube 1-1.5% al día "
                "y de repente hace +3-4% y sale en todos lados, suele ser <b>agotamiento, no fuerza</b>: ojo con comprar ahí. Si además vino con volumen fuerte, se anota (más fiable). "
                "<b style='color:#B980FF'>🟣 Capitulación</b> = lo mismo al revés: pánico de un día, la gente «se olvida» del ETF — el cazador de suelos <b>empieza a vigilar</b> "
                "(vigilar, no comprar: falta que el flujo deje de salir). Un día es un aviso; el WIRE TIMELINE (PRO) cuenta si se repite. "
                "Todos estos avisos salen dibujados <b>dentro del RRG</b>: anillo verde = entra dinero, doble anillo rojo = cuidado, "
                "anillo discontinuo ámbar/violeta = clímax/capitulación (más tenue = más días atrás). "
                "<b style='color:#4CC2E0'>🌏 Acum. extranjera</b> = internacionales cuyo gap nocturno acumulado (20 sesiones) es claramente positivo con CMF≤0: "
                "la compra ocurre en su bolsa local y el CMF americano no la ve — el punto ciego que ocultó la subida de China, ahora vigilado.</div></div>")

    # ---- RRG con selector por grupo (Todos / Sectores / Subsectores / Internacional) ----
    # calidad global de cada ETF: alimenta el TAMAÑO de la bola (mas verde en todo -> mas grande)
    quality = {}
    sc_q = {r["sym"]: r for r in scores} if scores else {}
    for s in rrg:
        base = sc_q.get(s, {}).get("score")
        q = 2.5 if base is None else float(base)              # satelites sin score -> neutro
        f = flow.get(s, {}) if flow else {}
        if f.get("diverg") == "distribucion oculta":
            q -= 1.5
        elif f.get("obv_above") and f.get("cmf_pos"):
            q += 1.5
        if sector_breadth and s in sector_breadth:
            bp = sector_breadth[s]["pct"]
            q += 1.0 if bp >= 60 else (-1.0 if bp < 40 else 0.0)
        if f.get("vol_break"):
            q += 0.7
        quality[s] = q
    rrg_g = {g: {s: d for s, d in rrg.items() if GRUPO.get(s) == g} for g in GRUPO_ORDEN}
    _rrgt = "<button class='viewtab rrgtab active' onclick=\"rrgView('all',this)\">Todos</button>"
    for _g in GRUPO_ORDEN:
        _rrgt += "<button class='viewtab rrgtab' onclick=\"rrgView('" + _g + "',this)\">" + GRUPO_NOMBRE.get(_g, _g) + "</button>"
    _rrgd = "<div id='rrg-all' style='max-width:1040px;margin:0 auto;display:block'>" + render_svg(rrg, flow, quality) + "</div>"
    for _g in GRUPO_ORDEN:
        _rrgd += "<div id='rrg-" + _g + "' style='max-width:1040px;margin:0 auto;display:none'>" + render_svg(rrg_g[_g], flow, quality) + "</div>"
    _rrgk = "['all'," + ",".join("'" + _g + "'" for _g in GRUPO_ORDEN) + "]"
    html.append("<div class='panel full'><h2>Grafico de rotacion relativa (RRG)</h2>"
                "<div class='note'>Cada punto pequeño de la estela es una <b>semana</b> (pasa el ratón o toca para la fecha). "
                "La <b>flecha</b> marca hacia dónde se mueve. El <b>tamaño de la bola</b> = calidad global de la señal "
                "(scoring + flujo + amplitud + volumen): más grande = mejor en todo. Anillo <b style='color:#2FD08A'>verde</b> = entra dinero; "
                "<b style='color:#F4607A'>doble rojo</b> = distribución oculta (cuidado) · anillo discontinuo <b style='color:#F4B740'>ámbar</b> = 🟡 clímax de subida en las últimas 3 sesiones (vela anómala que ya ve todo el mundo: posible agotamiento) · "
                "discontinuo <b style='color:#B980FF'>violeta</b> = 🟣 capitulación reciente (pánico de un día: vigilar suelo). Usa el selector para ver cada grupo a tamaño completo.</div>"
                "<div class='viewtabs'>"
                + _rrgt +
                "</div>"
                + _rrgd +
                "<script>function rrgView(v,b){" + _rrgk + ".forEach(function(g){"
                "document.getElementById('rrg-'+g).style.display=(g==v)?'block':'none';});"
                "document.querySelectorAll('.rrgtab').forEach(function(x){x.classList.remove('active')});b.classList.add('active');}</script>"
                "<div id='rrgtip' style='position:fixed;display:none;z-index:9999;background:#0F1623;color:#E6EDF6;"
                "border:1px solid #2B3850;border-radius:7px;padding:6px 9px;font-size:12px;max-width:240px;"
                "box-shadow:0 6px 20px rgba(0,0,0,.5);pointer-events:none'></div>"
                "<script>(function(){var tip=document.getElementById('rrgtip');"
                "function show(x,y,t){tip.textContent=t;tip.style.display='block';"
                "var L=Math.min(x+12,window.innerWidth-tip.offsetWidth-8);tip.style.left=Math.max(6,L)+'px';"
                "tip.style.top=Math.min(y+12,window.innerHeight-tip.offsetHeight-8)+'px';}"
                "function hide(){tip.style.display='none';}"
                "document.addEventListener('click',function(e){var d=e.target.closest('.tdot');"
                "if(d){show(e.clientX,e.clientY,d.getAttribute('data-t'));e.stopPropagation();}else hide();},true);"
                "document.querySelectorAll('.tdot').forEach(function(d){"
                "d.addEventListener('mouseenter',function(e){show(e.clientX,e.clientY,d.getAttribute('data-t'));});"
                "d.addEventListener('mouseleave',hide);});})();</script>"
                "<div class='legend' style='justify-content:center'>" +
                "".join(f"<span><i style='background:{QUAD[q][1]}'></i>{QUAD[q][0]}</span>" for q in QUAD) +
                "</div></div>")
    # ---- GRAFICO INTERACTIVO (TradingView, gratuito via widget; requiere internet) ----
    try:
        _tv_syms = sorted(rrg.keys())
        _tv_opts = "".join(f"<option value='{s}'{' selected' if s == 'XBI' else ''}>{s} · {esc(NAMES.get(s, (s, s, ''))[1])}</option>" for s in _tv_syms)
        html.append(
            "<div class='panel full'><h2>📺 Gráfico interactivo (TradingView)</h2>"
            "<div class='note'>Gráfico profesional en velas <b>semanales</b> del ETF que elijas (zoom, indicadores, dibujar). "
            "Necesita internet. Si en este mismo navegador tienes abierta tu sesión de TradingView de pago, tus preferencias extra aparecen solas. No es asesoramiento.</div>"
            f"<select id='tvsel' style='margin:6px 0;padding:7px 10px;background:#0E1626;color:#E8EEF9;border:1px solid #ffffff22;border-radius:6px;font-size:13px'>{_tv_opts}</select>"
            "<div id='tvwrap' style='height:470px;border-radius:8px;overflow:hidden'></div>"
            "<script src='https://s3.tradingview.com/tv.js'></script>"
            "<script>function tvload(s){var w=document.getElementById('tvwrap');w.innerHTML='';"
            "try{new TradingView.widget({container_id:'tvwrap',symbol:s,interval:'W',autosize:true,theme:'dark',style:'1',locale:'es',hide_side_toolbar:false,allow_symbol_change:true});}"
            "catch(e){w.innerHTML='<div style=\\'color:#9FB0C8;padding:20px\\'>Sin conexión con TradingView (requiere internet).</div>';}}"
            "var _tvs=document.getElementById('tvsel');_tvs.addEventListener('change',function(){tvload(this.value)});tvload(_tvs.value);</script>"
            "</div>")
    except Exception:
        pass
    # ---- INDICADOR PINE v6 (para pegar en TradingView): el MISMO flujo del terminal, en grafico profesional ----
    try:
        html.append(
            "<div class='panel full'><h2>📟 Tu flujo en TradingView (indicador Pine v6)</h2>"
            "<div class='note'>El <b>mismo CMF y la misma distribución oculta</b> que calcula este terminal (umbral ±0.05), como indicador "
            "para TradingView: se ve en una <b>ventana bajo el gráfico</b> de arriba y así comparas el flujo con las velas profesionales. "
            "Cómo instalarlo: en TradingView abre el <b>Editor Pine</b> (pestaña inferior) → borra lo que haya → pega este código → "
            "<b>Añadir al gráfico</b> → guárdalo como «Flujo PeVR» y te aparecerá en tus indicadores para siempre. "
            "Ponlo en velas <b>semanales</b> para que cuente la misma historia que el terminal.</div>"
            "<button class='viewtab' onclick=\"var t=document.getElementById('pinesrc').innerText;navigator.clipboard.writeText(t).then(function(){alert('Código Pine copiado. Pégalo en el Editor Pine de TradingView.')});\" "
            "style='margin:6px 0;font-size:12px;border-color:#5B8CFF55;color:#5B8CFF'>📋 Copiar código Pine</button>"
            "<details><summary style='cursor:pointer;color:#9FB0C8;font-size:12px'>Ver el código</summary>"
            "<pre id='pinesrc' style='background:#0E1626;border:1px solid #ffffff18;border-radius:8px;padding:12px;font-size:11px;overflow-x:auto;color:#CDE3FF'>"
            + esc(PINE_SCRIPT) +
            "</pre></details>"
            "<div class='note' style='margin-top:6px;color:#5E708A'>El triángulo naranja marca la <b>distribución oculta</b> (precio sube en 13 velas "
            "pero el dinero sale) — la misma señal que aquí excluye a un ETF de la cartera. Incluye alerta configurable en TradingView "
            "(botón de alertas → condición «Flujo PeVR: Distribución oculta»).</div></div>")
    except Exception:
        pass
    # ---- ZONA DE ENTRADA TEMPRANA (giro al alza, aún sin extender) ----
    if early:
        def _emerging_stock(sym):
            if not leaders or sym not in leaders:
                return None
            rows = leaders[sym]
            em = [r for r in rows if r.get("drs") is not None and r["drs"] >= 10 and 45 <= r["rs"] <= 92]
            if em:
                return max(em, key=lambda r: r["drs"])
            acc = [r for r in rows if r.get("drs") is not None and r["drs"] >= 5 and r["rs"] <= 92]
            return max(acc, key=lambda r: r["drs"]) if acc else None
        erows = ""
        for r in early[:8]:
            nm = NAMES.get(r["sym"], (r["sym"], r["sym"], ""))[1]
            qn = QUAD.get(r["quad"], (r["quad"], "#888"))[0]
            extcol = "#2FD08A" if r["ext"] <= 2 else "#F4B740"
            st = _emerging_stock(r["sym"])
            stock = (f"<b>{st['sym']}</b> <span style='color:#7BD88F'>RS {st['rs']} ↑{st['drs']}</span>"
                     if st else "<span style='color:#5E708A'>—</span>")
            fl = flow.get(r["sym"], {})
            if fl.get("diverg") == "distribucion oculta":
                conf = "<span style='color:#F4607A'>⚠ sale dinero</span>"
            elif fl.get("obv_above") and fl.get("cmf_pos"):
                conf = "<span style='color:#2FD08A'>✓ flujo confirma</span>"
            elif fl.get("obv_above") or fl.get("cmf_pos"):
                conf = "<span style='color:#F4B740'>~ parcial</span>"
            else:
                conf = "<span style='color:#5E708A'>— sin flujo</span>"
            vert = ("<span style='color:#7BD88F;font-weight:700' title='giro VERTICAL: impulso acelerando fuerte (>=3) con fuerza aun baja — tu patron de arranque de varias semanas'>🚀</span> "
                    if (r["accel"] >= 3 and r["ratio"] <= 97) else "")
            erows += (f"<tr><td class='se-l'>{vert}<b>{r['sym']}</b> <span style='color:var(--txt3);font-size:11px'>{esc(nm)}</span></td>"
                      f"<td class='r' style='color:#9FB0C8'>{qn}</td>"
                      f"<td class='r'>{r['ratio']:.0f}</td><td class='r' style='color:#5B8CFF'>{r['mom']:.0f}</td>"
                      f"<td class='r' style='color:#2FD08A'>+{r['accel']:.1f}</td>"
                      f"<td class='r' style='color:{extcol}'>{r['ext']:+.1f}%</td>"
                      f"<td class='r' style='font-size:11px'>{conf}</td>"
                      f"<td class='se-l'>{stock}</td></tr>")
        if erows:
            html.append("<div class='panel full'><h2>Zona de entrada temprana — giro al alza, aún sin extender</h2>"
                        "<div class='note'>Lo contrario de comprar caro: ETFs cuyo <b>impulso acaba de girarse al alza</b> "
                        "(aceleración positiva) pero que <b>todavía tienen fuerza baja y precio poco estirado</b> sobre su media. "
                        "Es la zona de abajo-izquierda del RRG que empieza a curvarse: <b>el principio del movimiento</b>, antes de que sea "
                        "un líder caro. <b>Aceleración</b> = subida del impulso en 4 semanas; <b>extensión</b> = cuánto está el precio por encima de su media de 40s. "
                        "<b>Flujo</b>: <span style='color:#2FD08A'>✓ confirma</span> = entra dinero (OBV&gt;media y CMF&gt;0) → señal más fiable; "
                        "<span style='color:#F4607A'>⚠ sale dinero</span> = distribución oculta, desconfía. La <b>acción emergente</b> es el nombre del sector que "
                        "más acelera y aún no está agotado. Más especulativo que el scoring. No es asesoramiento.</div>"
                        "<div class='scrollx'><table class='se'><tr><th class='se-l'></th><th class='r'>cuadrante</th><th class='r'>fuerza</th>"
                        "<th class='r'>impulso</th><th class='r'>acelera</th><th class='r'>extensión</th><th class='r'>flujo</th><th class='se-l'>acción emergente</th></tr>"
                        + erows + "</table></div></div>")

    # (radar de giro vertical absorbido por el panel 😴 DURMIENTES de arriba)

    # (señal contraria 0/3 absorbida por el panel 😴 DURMIENTES; contra_sigs/contra_led ya calculados alli)
    # ---- Vista alternativa: mapa de cuadrantes (sin solapes) ----
    html.append("<details class='why'><summary>El porqué — mapas, flujo, rankings, backtests y diagnóstico <span>(toca para abrir)</span></summary>")
    # ---- MARGEN VS SU MEDIA HISTORICA (contexto de extension, no senal) ----
    if meanrev:
        mvrows = sorted((kv for kv in meanrev.items() if kv[1].get("ytd") is not None),
                        key=lambda kv: -(kv[1]["margen"] if kv[1]["margen"] is not None else -999))
        mrows = ""
        for sym, m in mvrows:
            nm = NAMES.get(sym, (sym, sym, ""))[1]
            mg = m["margen"]
            if m["ytd"] < -10:
                lec, col = "rezagado / débil", "#9FB0C8"
            elif mg >= 5:
                lec, col = "le queda recorrido", "#2FD08A"
            elif mg >= -5:
                lec, col = "en su media (estirado)", "#F4B740"
            else:
                lec, col = "por encima de su media", "#F4607A"
            q = rrg.get(sym, {})
            turning = q.get("quad") in ("leading", "improving") and q.get("mom", 0) > 100
            combo = " <span style='color:#2FD08A;font-size:11px'>⬆ sitio + girando</span>" if (mg >= 3 and turning) else ""
            ytdcol = "#2FD08A" if m["ytd"] >= 0 else "#F4607A"
            mrows += (f"<tr><td class='se-l'><b>{sym}</b> <span style='color:var(--txt3);font-size:11px'>{esc(nm)}</span>{combo}</td>"
                      f"<td class='r' style='color:#9FB0C8'>{m['cagr']:+.1f}%</td>"
                      f"<td class='r' style='color:{ytdcol}'>{m['ytd']:+.1f}%</td>"
                      f"<td class='r' style='color:{col}'><b>{mg:+.1f}</b></td>"
                      f"<td class='se-l' style='font-size:11px;color:{col}'>{lec}</td></tr>")
        if mrows:
            html.append("<div class='panel full'><h2>Margen vs su media histórica</h2>"
                        "<div class='note'>Rentabilidad media anual de cada ETF (CAGR ~10 años) frente a lo que <b>lleva en el año</b> (YTD). "
                        "El <b>margen</b> = media − YTD: <span style='color:#2FD08A'>positivo</span> = va por debajo de su ritmo habitual (le queda sitio); "
                        "<span style='color:#F4607A'>negativo</span> = ya por encima (estirado). <b>Es contexto, no señal</b>: estar por debajo de la media "
                        "<b>no garantiza</b> subir — un sector puede seguir barato años. Solo es potente combinado con el RRG: "
                        "<b style='color:#2FD08A'>⬆ sitio + girando</b> marca los que están por debajo de su media <b>Y</b> rotando al alza — "
                        "esa es la combinación que de verdad interesa. Ordenado por margen (más sitio arriba). No es asesoramiento.</div>"
                        "<div class='scrollx'><table class='se'><tr><th class='se-l'></th><th class='r'>media anual</th><th class='r'>este año</th>"
                        "<th class='r'>margen</th><th class='se-l'>lectura</th></tr>" + mrows + "</table></div></div>")
    if heatmap and heatmap["rows"]:
        hcols = "".join(f"<th class='hm-h'>{c}</th>" for c in heatmap["cols"])
        hrows = ""
        for r in heatmap["rows"]:
            nm = NAMES.get(r["sym"], (r["sym"], r["sym"], ""))[1]
            turn = "<span class='hm-turn' title='rotacion temprana'>↗ girando</span>" if r["turning"] else ""
            cells = ""
            for v in r["vals"]:
                txt = "—" if v is None else f"{v:+.1f}"
                cells += f"<td class='hm-c' style='{heatmap_color(v)}'>{txt}</td>"
            hrows += (f"<tr><td class='hm-name'><b>{r['sym']}</b> <span>{esc(nm)}</span>{turn}</td>{cells}</tr>")
        html.append("<div class='panel full'><h2>Mapa de calor: fuerza relativa por plazo</h2>"
                    "<div class='note'>Rendimiento de cada ETF <b>menos el del S&P 500</b> en cada plazo. "
                    "<b style='color:#2FD08A'>Verde</b> = bate al mercado; <b style='color:#F4607A'>rojo</b> = lo hace peor. "
                    "La señal de <b>rotación temprana</b> es una fila <b>roja a 3–6 meses</b> que se pone <b>verde a 1 semana/1 mes</b> "
                    "(marcada con <b>↗ girando</b>): un sector castigado que empieza a despertar.</div>"
                    f"<table class='hm'><tr><th class='hm-name'></th>{hcols}</tr>{hrows}</table></div>")

    # ---- Vista de cuadrantes ----
    html.append("<div class='panel full'><h2>Mapa de cuadrantes (vista alternativa)</h2>"
                "<div class='note'>La misma información sin puntos que se solapan: cada caja lista los ETFs de ese cuadrante, "
                "ordenados por impulso. El número es fuerza/impulso (100 = igual que el índice).</div>"
                + quadrant_grid(rrg) + "</div>")

    # columna izquierda
    html.append("<div>")
    html.append("<div class='panel'><h2>Impulso relativo (RS-Momentum)</h2>"
                "<div class='note'>A la derecha = gana impulso vs indice. A la izquierda = lo pierde. "
                "Aqui aparece pronto el giro antes de que el precio lo confirme.</div>" + "".join(bars) + "</div>")
    html.append("</div>")
    # columna derecha
    html.append("<div>")
    html.append("<div class='panel'><h2>Alertas de rotacion</h2><div class='alerts'>" + al + "</div></div>")
    html.append("<div class='panel'><h2>Amplitud y riesgo</h2>" +
                meter("Sectores con fuerza &gt; indice", breadth["leaders"]) +
                meter("Sectores en tendencia alcista", breadth["uptrend"]) +
                f"<div class='bigrisk {risk_cls}'>{risk['label']}</div>"
                f"<div class='note'>Ciclicos/sensibles vs defensivos: {'+' if risk['score']>=0 else ''}{risk['score']} puntos.</div></div>")
    # panel de flujo de dinero por volumen
    if flow:
        fl_sorted = sorted(flow.items(), key=lambda kv: kv[1]["flow"], reverse=True)
        divs = [(s, d) for s, d in flow.items() if d["diverg"]]
        flow_rows = []
        for s, d in fl_sorted:
            col = "#2FD08A" if d["label"] == "Acumulacion" else "#F4607A" if d["label"] == "Distribucion" else "#93A4BC"
            mag = min(abs(d["flow"]) / 3.0, 1.0) * 50
            left = 50 if d["flow"] >= 0 else 50 - mag
            cmf = d.get("cmf")
            ccol = "#93A4BC" if cmf is None else ("#2FD08A" if cmf > 0 else "#F4607A" if cmf < 0 else "#93A4BC")
            _cmf_txt = "CMF n/d" if cmf is None else f"CMF {cmf:+.2f}"
            cross = " <span class='sc-acc' title='OBV cruzó su media: presión compradora acelerando'>⚡</span>" if d.get("obv_cross") else ""
            vr = d.get("vol_rel", 1.0)
            vcol = "#2FD08A" if d.get("vol_break") else ("#F4B740" if vr >= 1.0 else "#5E708A")
            brk = " 🔼" if d.get("vol_break") else ""
            vol_h = f"<span class='bar-cmf' style='color:{vcol}' title='Volumen de hoy vs media de 20 sesiones (≥1.3x con precio al alza = ruptura con volumen)'>×{vr:.1f} vol{brk}</span>"
            flow_rows.append(f"<div class='bar-row'><span class='bar-lab'>{s}{cross}</span>"
                             f"<div class='bar-track'><div class='bar-mid'></div>"
                             f"<div class='bar' style='background:{col};width:{mag:.0f}%;left:{left:.0f}%'></div></div>"
                             f"<span class='bar-val' style='color:{col}'>{d['flow']:+.1f}</span>"
                             f"<span class='bar-cmf' style='color:{ccol}' title='Chaikin Money Flow'>{_cmf_txt}</span>"
                             f"{vol_h}</div>")
        div_html = ""
        if divs:
            items = []
            for s, d in divs:
                kind = "warn" if d["diverg"] == "distribucion oculta" else "in"
                txt = ("Precio sube pero sale dinero (distribucion oculta): cuidado."
                       if d["diverg"] == "distribucion oculta"
                       else "Precio flojo pero entra dinero (acumulacion oculta): vigilar.")
                items.append(f"<div class='alert a-{kind}'><span class='atk'>{s}</span><span class='atx'>{txt}</span></div>")
            div_html = "<div class='alerts' style='margin-bottom:10px'>" + "".join(items) + "</div>"
        html.append("<div class='panel'><h2>Flujo de dinero (volumen)</h2>"
                    "<div class='note'>Acumulacion/Distribucion por volumen (OBV + A/D + <b>CMF</b>). Verde = entra dinero, rojo = sale. "
                    "El <b>CMF</b> (−1 a +1) es la presión compradora reciente; <b>⚡</b> = el OBV cruzó al alza su media (acelera). "
                    "El <b>×N vol</b> es el volumen de hoy frente a su media de 20 sesiones; <b>🔼</b> = ruptura al alza con volumen (≥1.3×). "
                    "Las <b>divergencias</b> (precio y dinero en sentidos opuestos) avisan antes que el precio.</div>"
                    + div_html + "".join(flow_rows) + "</div>")
    # (el panel de cobertura EUR/USD se movió arriba, a la primera pantalla)
    html.append("</div>")
    # fila completa: ranking enriquecido
    html.append("<div class='panel full'><h2>Ranking por cuadrante</h2>" + table + "</div>")
    # fila completa: backtest
    if bt:
        delta = bt["tot_s"] - bt["tot_b"]
        dcol = "#2FD08A" if delta >= 0 else "#F4607A"
        opt = []
        if TREND_FILTER: opt.append("filtro de tendencia (200d)")
        if MAX_POSICIONES: opt.append(f"tope {MAX_POSICIONES} posic.")
        opt.append({"volatilidad": "peso por volatilidad", "impulso": "peso por impulso", "igual": "peso igual"}[PESO])
        if BUFFER: opt.append(f"histeresis ±{BUFFER:g}")
        html.append("<div class='panel full'><h2>Backtest A — salir al debilitarse</h2>"
                    "<div class='note'>Estrategia <b>causal</b> (no mira el futuro): mantiene los activos en <b>Líder o Mejorando</b> "
                    "y <b>vende al pasar a Debilitándose</b>. Optimizaciones activas: <b>" + ", ".join(opt) + "</b>. "
                    f"Sobre {bt['weeks']} semanas (en mercado el {bt.get('exposure', 100)}% del tiempo).</div>"
                    + equity_svg(bt["dates"], bt["eq_s"], bt["eq_b"]) +
                    "<div class='summary' style='margin-top:12px'>"
                    + scard("Rentab. estrategia", f"{bt['tot_s']:+.1f}%", "#5B8CFF", "periodo completo")
                    + scard(f"Rentab. {BENCH}", f"{bt['tot_b']:+.1f}%", "#93A4BC", "comprar y mantener")
                    + scard("Diferencia", f"{delta:+.1f}%", dcol, "estrategia vs indice")
                    + scard("Caida maxima", f"{bt['mdd_s']:.0f}% / {bt['mdd_b']:.0f}%", "#F4B740", "estrategia / indice")
                    + "</div>"
                    "<div class='note' style='margin-top:8px'>El filtro de tendencia busca <b>bajar la caída máxima</b> (te saca en "
                    "mercados bajistas), no tanto subir la rentabilidad. Historia corta; sin comisiones ni impuestos. No es asesoramiento.</div></div>")
    if bt2:
        delta2 = bt2["tot_s"] - bt2["tot_b"]
        dcol2 = "#2FD08A" if delta2 >= 0 else "#F4607A"
        diff_ab = bt2["tot_s"] - (bt["tot_s"] if bt else 0)
        html.append("<div class='panel full'><h2>Backtest B — aguantar hasta rezagado</h2>"
                    "<div class='note'>Igual que la A pero <b>más paciente</b>: mantiene también los que están en <b>Debilitándose</b> "
                    "y <b>solo vende cuando caen a Rezagado</b> (la salida tardía «Debilitándose → Rezagado»). "
                    f"Sobre {bt2['weeks']} semanas.</div>"
                    + equity_svg(bt2["dates"], bt2["eq_s"], bt2["eq_b"]) +
                    "<div class='summary' style='margin-top:12px'>"
                    + scard("Rentab. estrategia", f"{bt2['tot_s']:+.1f}%", "#5B8CFF", "periodo completo")
                    + scard(f"Rentab. {BENCH}", f"{bt2['tot_b']:+.1f}%", "#93A4BC", "comprar y mantener")
                    + scard("Diferencia", f"{delta2:+.1f}%", dcol2, "estrategia vs indice")
                    + scard("B vs A", f"{diff_ab:+.1f}%", "#2FD08A" if diff_ab >= 0 else "#F4607A", "aguantar vs salir antes")
                    + "</div>"
                    "<div class='note' style='margin-top:8px'>Compara salir pronto (A) con aguantar (B): si <b>B &gt; A</b>, salir al primer "
                    "síntoma te cuesta dinero (sales demasiado pronto); si <b>A &gt; B</b>, cortar rápido protege. Historia corta, no es asesoramiento.</div></div>")
    # fila completa: empresa lider de cada ETF (por si no hay apalancado, entrar en la accion)
    rank_pri = {"leading": 0, "weakening": 1, "improving": 2, "lagging": 3}
    hold_syms = sorted([s for s in rrg if s in TOP_HOLDING],
                       key=lambda s: (rank_pri.get(rrg[s]["quad"], 9), -rrg[s]["mom"]))
    holds = ""
    for s in hold_syms:
        col = QUAD[rrg[s]["quad"]][1]
        holds += (f"<div class='hold'><span class='h-sym'><span class='dot' style='background:{col}'></span>{s}</span>"
                  f"<span class='h-top'>{esc(TOP_HOLDING[s])}</span>"
                  f"<a href='https://stockanalysis.com/etf/{s}/holdings/' target='_blank' rel='noopener'>ver</a></div>")
    html.append("<div class='panel full'><h2>Empresa líder de cada ETF</h2>"
                "<div class='note'>Por si no encuentras el ETF apalancado: la mayor posición de cada ETF (orientativo, "
                "puede cambiar). Pulsa «ver» para la lista actualizada de cada uno. Ordenado por cuadrante e impulso.</div>"
                "<div class='hold-grid'>" + holds + "</div></div>")
    # fila completa: acciones lideres por sector (RS Rating)
    if leaders:
        def rs_col(v):
            return "#2FD08A" if v >= 95 else "#7BD88F" if v >= 90 else "#F4B740" if v >= 80 else "#93A4BC" if v >= 60 else "#5E708A"
        lead_order = sorted(leaders.keys(),
                            key=lambda sec: (rank_pri.get(rrg.get(sec, {}).get("quad"), 9),
                                             -(rrg.get(sec, {}).get("mom", 0))))
        lrows = ""
        for sec in lead_order:
            q = rrg.get(sec, {}).get("quad")
            qchip = (f"<span class='dot' style='background:{QUAD[q][1]}'></span>" if q else "")
            chips = ""
            for r in leaders[sec][:LEADERS_TOP_N]:
                c = rs_col(r["rs"])
                star = " ★" if r["rs"] >= 99 else ""
                drs = r.get("drs")
                acc = ""
                if drs is not None and drs >= 6:
                    acc = f"<span class='accel'>↑{drs}</span>"
                elif drs is not None and drs <= -6:
                    acc = f"<span class='accel down'>↓{abs(drs)}</span>"
                chips += (f"<span class='lchip'><b>{r['sym']}</b>"
                          f"<span class='rsbadge' style='color:{c};border-color:{c}55'>RS {r['rs']}{star}</span>{acc}</span>")
            secname = NAMES.get(sec, (sec, sec, ""))[1]
            br = (sector_breadth or {}).get(sec)
            br_h = ""
            if br:
                bp = br["pct"]
                bc = "#2FD08A" if bp >= 60 else "#F4B740" if bp >= 40 else "#F4607A"
                btitle = ("amplitud amplia: la fuerza del sector está repartida" if bp >= 60 else
                          "amplitud media" if bp >= 40 else "ojo: falso liderazgo, suben pocas (2-3 megacaps)")
                br_h = f"<span class='lbreadth' style='color:{bc};border-color:{bc}55' title='{btitle}'>{bp}% &gt;media50</span>"
            lrows += (f"<div class='lrow'><div class='lsec'>{qchip}<b>{sec}</b> <span>{esc(secname)}</span>{br_h}</div>"
                      f"<div class='lchips'>{chips}</div></div>")
        html.append("<div class='panel full'><h2>Acciones líderes por sector (fuerza relativa)</h2>"
                    f"<div class='note'>RS Rating estilo IBD (1–99): percentil de fuerza calculado sobre las <b>{leaders_n} acciones seguidas</b> "
                    "(cuanto mayor el universo, más se acerca al percentil real del mercado; amplía la lista en SECTOR_STOCKS). "
                    "Las de <b>RS 90+</b> (verde) son las líderes; <b>★</b> = RS 99. El <b>↑N</b> es cuánto ha subido de percentil en 3 meses "
                    "(aceleración). El <b>% &gt;media50</b> de cada sector es su <b>amplitud real</b>: qué % de sus acciones están sobre su media de 50 sesiones "
                    "(<span style='color:#2FD08A'>verde &ge;60%</span> = subida repartida; <span style='color:#F4607A'>rojo &lt;40%</span> = <b>falso liderazgo</b>, tiran 2-3 megacaps). "
                    "Sectores ordenados por su cuadrante. Aproximación del rating, no asesoramiento.</div>"
                    + lrows + "</div>")

        # ---- ACCIONES EMERGENTES: RS acelerando en sectores donde entra dinero ----
        entering = [sec for sec in leaders if rrg.get(sec, {}).get("quad") in ("improving", "leading")]
        cands = []
        for sec in entering:
            for r in leaders[sec]:
                if r.get("drs") is not None:
                    cands.append((sec, r))
        # quitar duplicados (una accion puede estar en SMH e XLK): nos quedamos con el mayor drs
        best = {}
        for sec, r in cands:
            k = r["sym"]
            if k not in best or r["drs"] > best[k][1]["drs"]:
                best[k] = (sec, r)
        ranked = sorted(best.values(), key=lambda x: -x[1]["drs"])[:14]
        if ranked:
            erows = ""
            for sec, r in ranked:
                sweet = (r["drs"] >= 10 and 45 <= r["rs"] <= 92)
                dcol = "#2FD08A" if r["drs"] >= 10 else "#7BD88F" if r["drs"] >= 5 else "#93A4BC"
                qcol = QUAD[rrg.get(sec, {}).get("quad", "improving")][1]
                tag = "<span class='emtag'>emergente</span>" if sweet else ""
                erows += (f"<div class='emrow'><span class='em-sym'>{r['sym']}</span>"
                          f"<span class='em-sec' title='{esc(NAMES.get(sec,(sec,sec,''))[1])}'>"
                          f"<span class='dot' style='background:{qcol}'></span>{sec}</span>"
                          f"<span class='em-rs'>RS {r['rs']}</span>"
                          f"<span class='em-drs' style='color:{dcol}'>↑{r['drs']} en 3m</span>"
                          f"<span class='em-hi'>{r['hi']}% del máx.</span>{tag}</div>")
            html.append("<div class='panel full'><h2>Acciones emergentes (RS acelerando)</h2>"
                        "<div class='note'>Acciones cuyo <b>percentil RS sube más rápido</b> (últimos 3 meses), y solo en sectores que "
                        "están <b>entrando o liderando</b> en el RRG (donde fluye el dinero). La idea: pillarlas <b>mientras escalan</b>, "
                        "antes de que estén en RS 95+ y ya muy estiradas. <b>«emergente»</b> = sube fuerte (≥10) pero aún no está agotada "
                        "(RS 45–92). El «% del máx.» es lo cerca que está de su máximo de 52 semanas. No es asesoramiento.</div>"
                        + erows + "</div>")
    # fila completa: macro
    html.append("<div class='panel full'><h2>Regimen macro automatico: " + esc(regime["label"]) + "</h2>"
                "<div class='note'>Lectura orientativa deducida del propio mercado (bonos, credito, oro, dolar y apetito de riesgo).</div>"
                "<div class='conv'>"
                "<div><div class='kv'><span><b>Senales (variacion 13 semanas)</b></span><b></b></div>" + sig_rows + "</div>"
                "<div><div style='margin-bottom:10px'><h3 style='color:#2FD08A;font-size:11px'>Favorece</h3><div class='tags'>" + favor + "</div></div>"
                "<div><h3 style='color:#F4607A;font-size:11px'>Penaliza</h3><div class='tags'>" + hurt + "</div></div></div>"
                "</div>"
                "<div class='conv'>"
                "<div class='conv-box'><h3 style='color:#2FD08A'>Alta conviccion alcista</h3>"
                "<div class='note' style='margin:0 0 6px'>Regimen a favor + rotacion entrando/liderando:</div>"
                "<div class='tags'>" + buy_t + "</div></div>"
                "<div class='conv-box'><h3 style='color:#F4607A'>Evitar / reducir confirmado</h3>"
                "<div class='note' style='margin:0 0 6px'>Regimen en contra + rotacion saliendo/rezagada:</div>"
                "<div class='tags'>" + avoid_t + "</div></div>"
                "</div></div>")
    if fred_html:
        html.append("<div class='full'>" + fred_html + "</div>")
    html.append("</details>")
    html.insert(verdict_pos, verdict_html)
    # ===== PREVISION MACRO (reloj de inversion) — al final del todo =====
    try:
        _macro = fetch_macro()
        _mr = compute_macro_regime(_macro, ISM_MANUAL)
        if _macro and _mr:
            def _ar(it):
                d = it["dir"]; gu = it.get("goodup", True)
                if d > 0:
                    return "▲", ("#2FD08A" if gu else "#F4607A")
                if d < 0:
                    return "▼", ("#F4607A" if gu else "#2FD08A")
                return "▬", "#9FB0C8"
            def _rows(kind):
                r = ""
                for k, v in _macro.items():
                    if v["kind"] != kind:
                        continue
                    a, c = _ar(v)
                    r += (f"<tr><td class='se-l'>{esc(v['lab'])}</td>"
                          f"<td class='r'>{v['val']:g}{(' ' + v['unit']) if v['unit'] else ''}</td>"
                          f"<td class='r' style='color:{c}'>{a} {v['dir']:+g}</td></tr>")
                return r
            ism_row = (f"<tr><td class='se-l'>ISM manufacturas <span style='color:#5E708A;font-size:10px'>(manual)</span></td>"
                       f"<td class='r'>{ISM_MANUAL:g}</td>"
                       f"<td class='r' style='color:{'#2FD08A' if ISM_MANUAL >= 50 else '#F4607A'}'>{'expansión' if ISM_MANUAL >= 50 else 'contracción'}</td></tr>")
            conf_list, wait_list = [], []
            for s in _mr["favor"]:
                q = (rrg.get(s, {}) or {}).get("quad")
                (conf_list if q in ("leading", "improving") else wait_list).append(s)
            qcol = {"recuperacion": "#2FD08A", "sobrecalentamiento": "#F4B740",
                    "estanflacion": "#F4607A", "desinflacion": "#5AA9E6"}.get(_mr["quad"], "#9FB0C8")
            pr = _mr["pr"]
            esc_base = f"sigue <b>{_mr['label']}</b> → favorece {', '.join(_mr['favor'][:5])}"
            html.append(
                "<div class='panel full'><h2>Previsión macro — reloj de inversión</h2>"
                "<div class='note'>Cruzo la <b>dirección del crecimiento</b> (datos blandos, que se adelantan) con la <b>dirección de la inflación</b> "
                "(PCE/IPC subyacente) para situar el régimen, y miro dónde está entrando el dinero en tu propio panel. "
                "<b>Es un mapa de probabilidades por régimen, no una predicción.</b></div>"
                "<div class='scrollx'><table class='se'><tr><th class='se-l'>indicador</th><th class='r'>nivel</th><th class='r'>tendencia</th></tr>"
                "<tr><td colspan='3' style='color:#5E708A;font-size:11px;padding-top:6px'>DUROS (retrasados)</td></tr>"
                + _rows("hard") +
                "<tr><td colspan='3' style='color:#5E708A;font-size:11px;padding-top:6px'>BLANDOS (líderes)</td></tr>"
                + ism_row + _rows("soft") +
                "</table></div>"
                f"<div style='margin-top:12px;padding:10px;border:1px solid {qcol}55;border-radius:8px;background:{qcol}11'>"
                f"Crecimiento <b>{_mr['grow_lbl']}</b> · inflación <b>{_mr['infl_lbl']}</b> → "
                f"<b style='color:{qcol}'>{_mr['label']}</b>"
                + ("<br><span style='color:#F4B740;font-size:11px'>⚠ inflación plana, en la frontera entre regímenes — poca convicción, puede cambiar con el próximo dato</span>" if _mr.get("infl_weak") else "")
                + "<br>"
                f"<span style='color:#9FB0C8'>Playbook histórico:</span> a favor <b style='color:#2FD08A'>{', '.join(_mr['favor'])}</b> · "
                f"en contra <b style='color:#F4607A'>{', '.join(_mr['hurt'])}</b></div>"
                "<div class='note' style='margin-top:10px'><b>¿El dinero lo confirma?</b> "
                + (f"Ya en Líder/Mejorando: <b style='color:#2FD08A'>{', '.join(conf_list)}</b>. " if conf_list else "Aún ninguno de los favorecidos está en Líder/Mejorando. ")
                + (f"Aún no confirman: <span style='color:#9FB0C8'>{', '.join(wait_list)}</span>. " if wait_list else "")
                + "Actúa donde el régimen <b>y</b> el flujo coinciden.</div>"
                "<div class='scrollx' style='margin-top:10px'><table class='se'><tr><th class='se-l'>escenario</th><th class='r'>prob.*</th><th class='se-l'>implicación</th></tr>"
                f"<tr><td class='se-l'>Base</td><td class='r' style='font-weight:700'>~{pr['base']}%</td><td class='se-l'>{esc_base}</td></tr>"
                f"<tr><td class='se-l'>Alcista</td><td class='r'>~{pr['bull']}%</td><td class='se-l'>crecimiento reacelera con inflación contenida → giro a cíclicos/tech (XLK, XLY, XLF, IWM)</td></tr>"
                f"<tr><td class='se-l'>Bajista</td><td class='r'>~{pr['bear']}%</td><td class='se-l'>susto de crecimiento o inflación que reacelera → defensa (XLP, XLU, XLV, TLT, GLD)</td></tr>"
                "</table></div>"
                "<div class='note' style='margin-top:8px'><b>Línea de tiempo — qué dato rompe el empate:</b> "
                "el <b>PCE subyacente</b> (fin de mes) marca el eje inflación; las <b>nóminas</b> (1er viernes), el <b>ISM</b> (1er día hábil) y el <b>IPC</b> (mitad de mes) marcan el crecimiento. "
                "Cada build lo recalcula con el dato fresco.</div>"
                f"<div class='note' style='margin-top:8px;color:#5E708A'>*Probabilidades gruesas derivadas de la fuerza de la señal (claridad {round(_mr['conf'] * 100)}%), "
                "no de un modelo predictivo. La previsión macro es de poca pericia hasta para los bancos: úsala como marco, no como certeza. "
                "El <b>flujo manda</b>. No es asesoramiento.</div></div>")
        elif _macro is None:
            _k = _fred_key()
            if not _k:
                _diag = ("No encuentro la key. En el <b>PC</b>: pon <b>clave_fred.txt</b> (con la key dentro) en la misma carpeta "
                         "desde la que lanzas <code>python rotacion.py</code> y re-ejecuta. En <b>GitHub</b>: ponla en Secrets "
                         "(Settings → Secrets and variables → Actions → <b>FRED_API_KEY</b>).")
            else:
                _diag = (f"Key detectada (<b>{len(_k)} caracteres</b>) pero FRED no devolvió datos. Casi seguro es internet/firewall al "
                         "ejecutar o una key inválida. Pruébala en el navegador: "
                         "<code>https://api.stlouisfed.org/fred/series/observations?series_id=UNRATE&amp;api_key=TU_KEY&amp;file_type=json&amp;limit=1</code> "
                         "— si te devuelve JSON, la key va bien.")
            html.append("<div class='panel full'><h2>Previsión macro — reloj de inversión</h2>"
                        f"<div class='note'>⚙ {_diag}</div></div>")
    except Exception:
        pass
    # ===== V3 — VISTA OPERATIVA (cerrar Contexto, abrir Operativa) =====
    html.append("</div><div id='vista-op' style='display:none'>")

    # ===== SISTEMA DE DECISION (rediseño Operativa): menos es mas — decidir en 10 segundos =====
    try:
        _mi_syms = {t[0] for t in MI_CARTERA} if MI_CARTERA else set()
        _fichas = compute_fichas(df, daily or {}, rrg, flow or {}, scores, suelo_pre, centinela, plan,
                                 CARTERA_FINAL, _mi_syms, analogos=analogos, tau=tau, desks=desks, options=options)
        # --- cabecera de contexto: mercado + analogos + tau, todo en una franja ---
        ctx = []
        if centinela:
            ctx.append(f"<span style='color:{centinela['col']};font-weight:800'>{centinela['estado']}</span>")
        if plan:
            _dc = "#F4607A" if plan["dd"] <= -5 else "#F4B740" if plan["dd"] <= -2 else "#2FD08A"
            ctx.append(f"S&P vs ATH <b style='color:{_dc}'>{plan['dd']:+.1f}%</b>")
        if analogos:
            _a3 = analogos["m3"]
            ctx.append(f"análogos desde {analogos['desde']}: a 3 meses <b style='color:#5B8CFF'>{_a3['pos']}%</b> positivos "
                       f"<span style='color:#5E708A'>(IC95 {_a3['lo']}–{_a3['hi']}, mediana {_a3['med']:+.1f}%, n={_a3['n']})</span>")
        if tau:
            ctx.append(f"ciclo τ: <b style='color:{tau['col']}'>{tau['estado']}</b>")
        # DIVERGENCIA entre relojes: el sesgo de flujo (spread RRG ciclicos-defensivos) y el Centinela
        # (flujo+amplitud+credito) pueden discrepar. Regla de la casa: se SEÑALA, no se reconcilia.
        try:
            _rl = (risk or {}).get("label", "")
            _ce = (centinela or {}).get("estado", "")
            if _rl == "Risk-ON" and _ce in ("DISTRIBUCION", "LIQUIDEZ"):
                ctx.append("<span style='color:#F4B740'>⚠ divergencia de relojes: sesgo de flujo <b>Risk-ON</b> pero Centinela en <b>" + _ce +
                           "</b> — el precio aún manda pero el dinero se recoloca; señal mixta, prudencia con tamaño</span>")
            elif _rl == "Risk-OFF" and _ce == "RISK-ON":
                ctx.append("<span style='color:#F4B740'>⚠ divergencia de relojes: sesgo Risk-OFF con Centinela RISK-ON — señal mixta</span>")
        except Exception:
            pass
        _lideres_t = [ff["sym"] for ff in (_fichas or []) if ff.get("lider_temp")][:5]
        # --- CONFLUENCIA DE REBOTE: ideas tacticas rapidas (SEPARADAS de la cartera de rotacion) ---
        # Candados: (1) etiqueta tactica explicita; (2) vehiculo CONTADO por defecto, apalancado solo
        # como mencion con stop; (3) si el Centinela esta en DISTRIBUCION CONFIRMADA, el bloque se
        # bloquea entero: comprar rebote apalancado en distribucion es la trampa clasica.
        _confl_html = ""
        try:
            _dist_conf = bool(centinela and centinela.get("estado") == "DISTRIBUCION" and centinela.get("confirmado"))
            _ideas = []
            _poker_hi = {d["sym"]: d for d in (desks or []) if d and d.get("pts", 0) >= 7}
            for _sym, _dk in _poker_hi.items():
                _fk = (flow or {}).get(_sym, {})
                _flujo_gira = bool(_fk.get("cmf_mejora") or (_fk.get("cmf") is not None and _fk["cmf"] > -0.05))
                if _flujo_gira:
                    _cfgd = next((c for c in DESKS_POKER if c["id"] == _dk.get("id")), {})
                    _ideas.append({"tit": f"{_sym} rebote {_dk['pts']}/10",
                                   "det": " · ".join(_dk.get("det", [])[:3]),
                                   "veh": f"{_sym} en CONTADO, tamaño ¼-Kelly del desk",
                                   "lev": _cfgd.get("veh", "")})
            # la confluencia que pediste: XLK con flujo girando + SEMIS >= 7 -> rebote Nasdaq
            _dk_semis = next((d for d in (desks or []) if d and d.get("id") == "SEMIS"), None)
            _fx_xlk = (flow or {}).get("XLK", {})
            _xlk_gira = bool(_fx_xlk.get("cmf_mejora") or (_fx_xlk.get("cmf") is not None and _fx_xlk["cmf"] > 0))
            _xlk_no_div = _fx_xlk.get("diverg") != "distribucion oculta"
            if _dk_semis and _dk_semis.get("pts", 0) >= 7 and _xlk_gira and _xlk_no_div:
                _ideas.insert(0, {"tit": f"NASDAQ rebote por confluencia (XLK flujo girando + semis {_dk_semis['pts']}/10)",
                                  "det": "primer giro de flujo en XLK con semis en zona de rebote estadístico",
                                  "veh": "QQQ en CONTADO",
                                  "lev": "TQQQ (3x) SOLO con confirmación de 3 sesiones de flujo (un círculo verde = 1 día = ruido), tamaño mínimo, stop obligatorio — su decay diario cobra si el rebote se retrasa"})
            if _dist_conf:
                _confl_html = ("<div style='margin:6px 0 10px;padding:8px 11px;background:rgba(244,96,122,.07);border:1px solid #F4607A44;"
                               "border-radius:8px;font-size:11.5px;color:#F0A9B8'>💡 CONFLUENCIA DE REBOTE — 🔒 <b>BLOQUEADO</b>: "
                               "Centinela en DISTRIBUCIÓN confirmada. En este régimen el rebote comprado (y más con apalancado) es la trampa "
                               "estadística clásica: la sobreventa puede seguir sobrevendida. Las ideas tácticas vuelven cuando el régimen cambie.</div>")
            elif _ideas:
                _its = ""
                for _i in _ideas[:3]:
                    _its += (f"<div style='margin:5px 0;padding:7px 10px;background:#0E1626;border-left:3px solid #4CC2E0;border-radius:7px'>"
                             f"<div style='font-size:12px;color:#4CC2E0'><b>💡 {esc(_i['tit'])}</b> "
                             f"<span style='font-size:9px;color:#F4B740;border:1px solid #F4B74055;border-radius:4px;padding:1px 5px'>TÁCTICO — NO ROTACIÓN</span></div>"
                             f"<div style='font-size:10.5px;color:#8FA3C0;margin-top:2px'>{esc(_i['det'])}</div>"
                             f"<div style='font-size:10.5px;color:#B9C9E2;margin-top:2px'>Vehículo: <b>{esc(_i['veh'])}</b></div>"
                             + (f"<div style='font-size:10px;color:#7A8CA8;margin-top:1px'>Apalancado: {_i['lev']}</div>" if _i.get("lev") else "")
                             + "</div>")
                _confl_html = ("<div style='margin:6px 0 10px'>"
                               "<div style='font-size:10.5px;color:#8FA3C0;text-transform:uppercase;letter-spacing:.8px'>💡 Confluencia de rebote — ideas tácticas (aparte de la cartera)</div>"
                               + _its +
                               "<div style='font-size:9.5px;color:#5E708A;margin-top:3px'>Regla: idea táctica = mesa de póker ≥7/10 + flujo girando. Se juega aparte de la rotación, "
                               "en contado, tamaño pequeño, stop sagrado. Si el Centinela pasa a distribución confirmada, este bloque se bloquea solo.</div></div>")
        except Exception:
            _confl_html = ""
        html.append("<div class='panel full' style='border-color:#5B8CFF55'>"
                    "<h2>⚡ DECISIÓN — todo el terminal sintetizado en un ranking</h2>"
                    "<div class='note'>Cada ficha recopila lo que ya calculan los demás paneles (RRG, flujo, suelos, centinela, plan, correlaciones) "
                    "y lo convierte en un semáforo. Solo se muestra lo que cambia la decisión; el resto, plegado. "
                    "Exposiciones gemelas (p.ej. SMH/SOXX) se agrupan y solo se recomienda el mejor candidato: una señal por movimiento, sin contradicciones. "
                    "«Prob.» = frecuencia histórica del propio ETF en su cuadrante actual (adelante 4 semanas, IC 95%) — estadística, no predicción. No es asesoramiento.</div>"
                    + ("<div style='font-size:12px;color:#B9C9E2;margin:6px 0 10px;padding:7px 10px;background:#0E1626;border-radius:8px'>"
                       + " · ".join(ctx) + "</div>" if ctx else "")
                    + (f"<div style='font-size:11.5px;color:#4CC2E0;margin-bottom:10px'>🌱 Síntomas tempranos de próximo líder "
                       f"(aún débiles, RS acelerando + flujo girando): <b>{esc(', '.join(_lideres_t))}</b></div>" if _lideres_t else "")
                    + _confl_html)
        if _fichas:
            _sm = _semaforo
            cards = ""
            for ff in _fichas[:10]:
                c = ff["c"]
                _pr = ff.get("prob")
                _pr_t = (f"{_pr['p']}% <span style='color:#5E708A;font-size:9.5px'>(IC {_pr['lo']}–{_pr['hi']}, n={_pr['n']})</span>"
                         if _pr else "<span style='color:#5E708A'>sin muestra</span>")
                _gem = ""
                if ff.get("gemelos"):
                    _gem = ("<div style='font-size:10px;color:#8FA3C0;margin-top:4px'>≈ misma exposición: "
                            + ", ".join(f"{g['sym']} ({g['score']})" for g in ff["gemelos"])
                            + " — siguen la señal de este candidato</div>")
                _fav = "".join(f"<div style='font-size:11px;color:#9FE3B9'>· {esc(x)}</div>" for x in ff["favor"]) or "<div style='font-size:11px;color:#5E708A'>· —</div>"
                _con = "".join(f"<div style='font-size:11px;color:#F0A9B8'>· {esc(x)}</div>" for x in ff["contra"]) or "<div style='font-size:11px;color:#5E708A'>· nada relevante en contra</div>"
                _tag = " <span style='font-size:9px;color:#5B8CFF'>EN CARTERA</span>" if ff["en_cart"] else ""
                if ff.get("poker") is not None and ff["poker"] >= 6:
                    _tag += (f" <span style='font-size:9px;color:#F4B740;border:1px solid #F4B74055;border-radius:4px;padding:1px 5px'>"
                             f"🎰 {ff['poker']}/10 rebote — táctico, no rotación</span>")
                cards += (f"<div style='background:#0E1626;border:1px solid {ff['dcol']}44;border-left:3px solid {ff['dcol']};"
                          f"border-radius:10px;padding:11px 14px;margin-bottom:8px'>"
                          f"<div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px'>"
                          f"<div style='font-size:15px'>{_sm(ff['score'])} <b style='color:#E6EDF6'>{ff['sym']}</b>"
                          f" <span style='color:#8FA3C0;font-size:11px'>{esc(NAMES.get(ff['sym'], ('', '', ''))[0])}</span>{_tag}"
                          f" — <b>Score {ff['score']}/100</b></div>"
                          f"<div style='font-size:13px;font-weight:800;color:{ff['dcol']}'>{ff['direc']}</div></div>"
                          f"<div style='font-size:11px;color:#B9C9E2;margin:6px 0;line-height:1.9'>"
                          f"Mercado {_sm(c['mercado'])} · Sector {_sm(c['sector'])} <span style='color:#5E708A'>({esc(ff['sec_lbl'])})</span> · "
                          f"Industria {_sm(c['industria'])} · ETF {_sm(c['etf'])} <span style='color:#5E708A'>({ff['quad']})</span> · "
                          f"Flujo {_sm(c['flujo'])} <span style='color:#5E708A'>({ff['flu_lbl']})</span> · "
                          f"Riesgo {_sm(c['riesgo'])} · Correlación {_sm(c['corr'])} · Prob. {_pr_t}</div>"
                          f"<div style='display:flex;gap:18px;flex-wrap:wrap'>"
                          f"<div style='flex:1;min-width:220px'><div style='font-size:9.5px;color:#8FA3C0;text-transform:uppercase'>A favor</div>{_fav}</div>"
                          f"<div style='flex:1;min-width:220px'><div style='font-size:9.5px;color:#8FA3C0;text-transform:uppercase'>En contra</div>{_con}</div></div>"
                          f"<div style='font-size:11px;color:#D7C9A8;margin-top:6px'><b>Conclusión:</b> {esc(ff['concl'])}</div>"
                          + _gem
                          + f"<details style='margin-top:5px'><summary style='cursor:pointer;font-size:10px;color:#5E708A'>detalle numérico</summary>"
                            f"<div style='font-size:10.5px;color:#8FA3C0;margin-top:4px'>1 sem {ff['rel1']:+.1f}% rel · 4 sem {ff['rel4']:+.1f}% rel"
                          + (f" · 13 sem {ff['abs13']:+.1f}% abs" if ff.get('abs13') is not None else "")
                          + (f" · CMF {ff['cmf']:+.2f}" if ff.get('cmf') is not None else "")
                          + (f" · {ff['hi52']}% del máx 52s" if ff.get('hi52') is not None else "")
                          + f" · corr: {esc(ff['cor_lbl'])} · componentes: M{c['mercado']} S{c['sector']} I{c['industria']} E{c['etf']} F{c['flujo']} R{c['riesgo']} C{c['corr']}</div></details>"
                          "</div>")
            resto = _fichas[10:]
            tabla_resto = ""
            if resto:
                filas = "".join(f"<tr><td style='padding:2px 8px'>{_sm(ff['score'])} <b>{ff['sym']}</b></td>"
                                f"<td class='r' style='padding:2px 8px'>{ff['score']}</td>"
                                f"<td style='padding:2px 8px;color:{ff['dcol']}'>{ff['direc']}</td>"
                                f"<td style='padding:2px 8px;color:#8FA3C0;font-size:10px'>{ff['quad']} · flujo {ff['flu_lbl']}</td></tr>"
                                for ff in resto)
                tabla_resto = (f"<details style='margin-top:6px'><summary style='cursor:pointer;font-size:11px;color:#8FA3C0'>"
                               f"ranking completo — {len(resto)} activos más</summary>"
                               f"<table style='font-size:11.5px;border-collapse:collapse;margin-top:5px'>{filas}</table></details>")
            html.append(cards + tabla_resto)
        else:
            html.append("<div class='note'>No se pudieron generar las fichas esta semana.</div>")
        html.append("</div>")
        # --- CALENDARIO tau (informativo) ---
        if tau:
            _reglas = ("<div style='font-size:11px;color:#B9C9E2;line-height:1.8'>"
                       "· <b>VENTANA</b> (τ−9→τ−3): venta mecánica sobre losers (−7.9 pb/día, t=−3.7). <b>No comprar suelos ni promediar débiles</b>; el CMF ahí es ambiguo. Vender losers va A FAVOR del viento.<br>"
                       f"· <b>TRANSICIÓN</b> ({tau.get('trans_ini','?')} → {tau.get('trans_fin','?')}): la presión amaina pero los datos de órdenes (TAQ) muestran venta residual hasta fin de mes. Aún sin prisa.<br>"
                       f"· <b>REBOTE</b> (<b style='color:#2FD08A'>{tau['reb_ini']} → {tau['reb_fin']}</b>): el desagüe termina y ~70% del castigo revierte en la semana; los rallies violentos de losers se concentran en el arranque de mes. La franja del cazador de suelos.<br>"
                       "· Si el lunes de ejecución cae en ventana Y el activo es un loser: <b>aplazar la compra a la zona de rebote</b>. Winners no se aplazan (el efecto es 100% de losers).<br>"
                       "· Apalancados 3x/5x sobre sectores débiles: su mayor riesgo mensual es la ventana — vigilar margen XTB. Inversos sobre losers (tipo SOXS): el arranque de mes es donde más duelen.</div>")
            html.append(f"<div class='panel full' style='border-color:{tau['col']}55'>"
                        f"<h2>📅 CALENDARIO τ — ciclo intramensual de momentum</h2>"
                        f"<div style='display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin-bottom:8px'>"
                        f"<div style='font-size:20px;font-weight:800;color:{tau['col']}'>{tau['estado']}</div>"
                        f"<div style='font-size:11.5px;color:#8FA3C0'>ventana de presión: <b>{tau['win_ini']} → {tau['win_fin']}</b> · "
                        f"τ (última sesión del mes): <b>{tau['tau']}</b>"
                        + (f" · faltan {tau['faltan_ventana']} sesiones para la ventana" if tau.get('faltan_ventana') else "") + "</div></div>"
                        + _reglas +
                        "<div class='note' style='margin-top:6px'>Verificado contra el paper completo (Nathan, Suominen &amp; Tasa, SSRN 6426026): PreTOM base [τ−9, τ−4]; "
                        "la reforma T+1 (may-2024) movió el día marginal de venta de τ−4 a τ−3 (dif. +85.9 pb, t=2.68) — el borde izquierdo no está retestado, así que la ventana aquí es [τ−9, τ−3] por prudencia. "
                        "El efecto lo generan los losers del decil inferior; ordenar por <b>distancia al máximo de 52 semanas</b> (lo que mide DURMIENTES) captura la venta forzada aún mejor que el momentum clásico ($45.7 vs $18.8 por dólar en ventana). "
                        "~70% del castigo de ventana revierte en la semana siguiente; el 30% restante tarda meses. Overlay informativo sobre tu ritmo viernes→lunes, no un sistema. "
                        "<b>Invalidación:</b> 6 meses de registro losers dentro-vs-fuera de ventana; si dentro no es peor, se retira. Anomalía muy publicada (Money Stuff, mar-2026): puede decaer rápido.</div></div>")
        # --- todo lo clasico de Operativa queda debajo, plegado por defecto (nada se elimina) ---
        html.append("<details style='margin:4px 0 10px'><summary style='cursor:pointer;font-size:13px;color:#8FA3C0;"
                    "padding:8px 12px;background:#0E1626;border:1px solid #24344F;border-radius:8px'>"
                    "🔧 Detalle completo — todos los paneles clásicos de Operativa (mesa, candidatos, sintético, apalancados…)</summary>")
        _op_details_abierto = True
    except Exception as _e_dec:
        print(f"  panel decision: {_e_dec}")
        _op_details_abierto = False

    # ===== MESA DE OPERACIONES: todo lo accionable de la semana en una pantalla =====
    try:
        _box = lambda titulo, cuerpo, bcol="#24344F": (f"<div style='flex:1 1 300px;min-width:280px;background:#0E1626;border:1px solid {bcol};"
                                                       f"border-radius:10px;padding:12px 14px'><div style='font-size:11px;color:#8FA3C0;"
                                                       f"text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px'>{titulo}</div>{cuerpo}</div>")
        mesa = []
        # 1) semaforo + ordenes de cartera
        _fg_t = f" · F&G {fg_idx['score']}" if fg_idx else ""
        c1 = (f"<div style='font-size:14px;margin-bottom:8px'><b style='color:{light}'>{esc(sem_short)}</b> · {esc(reg_short)} · {esc(risk['label'])}{_fg_t}</div>")
        c1 += ("<div style='font-size:12px;margin-bottom:6px;padding:6px 8px;background:rgba(91,140,255,.08);border:1px solid #5B8CFF33;border-radius:6px'>"
               "CARTERA FINAL: <b style='color:#5B8CFF'>" + esc(", ".join(CARTERA_FINAL) if CARTERA_FINAL else "liquidez") + "</b>"
               "<span style='color:#8FA3C0;font-size:10px'> — la única lista que se opera; el resto son candidatos</span></div>")
        _ent = ", ".join(entering[:4]) or "—"
        _sal = ", ".join(leaving[:4]) or "—"
        c1 += (f"<div style='font-size:12px;line-height:1.7'>Entran (Mejorando): <b style='color:#4CC2E0'>{esc(_ent)}</b><br>"
               f"Salen (Debilitándose): <b style='color:#F4B740'>{esc(_sal)}</b>")
        if mi_plan and mi_plan.get("rows"):
            _vnd = [r for r in mi_plan["rows"] if str(r.get("act", "")).upper().startswith("VENDER")]
            _veur = sum(r["eur"] for r in _vnd if isinstance(r.get("eur"), (int, float)))
            _vt = ", ".join(r["tk"] for r in _vnd[:5]) + ("…" if len(_vnd) > 5 else "")
            if _vnd:
                c1 += (f"<br>Tu cartera en señal de salida: <b style='color:#F4607A'>{len(_vnd)} posiciones · ~{_veur:,.0f} €</b>"
                       f"<br><span style='color:#8FA3C0;font-size:11px'>{esc(_vt)}</span>").replace(",", ".")
            else:
                c1 += "<br>Tu cartera: <b style='color:#2FD08A'>sin señales de venta esta semana</b>"
        c1 += "</div>"
        mesa.append(_box("🚦 La semana en una línea + órdenes", c1, light + "55"))
        # 1b) CENTINELA compacto: el régimen manda sobre todas las demás cajas
        if centinela:
            _flblo = {"DISTRIBUCION": "DISTRIBUCIÓN", "TRANSICION": "TRANSICIÓN"}
            cbx = (f"<div style='font-size:16px;font-weight:800;letter-spacing:1px;color:{centinela['col']};margin-bottom:4px'>"
                   f"{_flblo.get(centinela['estado'], centinela['estado'])}"
                   + ("  <span style='font-size:9.5px;color:#2FD08A'>✓ confirmado</span>" if centinela["confirmado"]
                      else "  <span style='font-size:9.5px;color:#F4B740'>⧗ sin confirmar</span>") + "</div>")
            cbx += (f"<div style='font-size:11.5px;color:#8FA3C0;margin-bottom:5px'>spread beta−def <b style='color:"
                    + ("#2FD08A" if centinela["spread"] > 0 else "#F4607A") + f"'>{centinela['spread']:+.2f}</b>"
                    f" · Δ3s {centinela['d3']:+.2f}"
                    + (f" · CMF explosivos {centinela['cmf_beta']:+.2f}" if centinela.get("cmf_beta") is not None else "") + "</div>")
            if centinela.get("despierta"):
                cbx += f"<div style='font-size:11px;color:#2FD08A'>🌅 despertando: {esc(', '.join(centinela['despierta'][:4]))}</div>"
            if centinela.get("acecho"):
                cbx += f"<div style='font-size:11px;color:#4CC2E0'>🌱 pre-despertar: {esc(', '.join(centinela['acecho'][:4]))}</div>"
            cbx += (f"<div style='font-size:10.5px;color:#9FB0C8;margin-top:5px'>{esc(centinela['que'][:200])}{'…' if len(centinela['que']) > 200 else ''}"
                    "<br><span style='color:#5E708A;font-size:9.5px'>El reloj completo, con invalidación y confirmadores, en Contexto → 🛰️ CENTINELA.</span></div>")
            mesa.append(_box("🛰️ Centinela — el régimen manda", cbx, centinela["col"] + "55"))
        # 2) candidato del sistema
        if candidato:
            _t = candidato["top"]
            c2 = (f"<div style='font-size:16px'><b style='color:#5B8CFF'>{_t['stock']['sym']}</b> "
                  f"<span style='color:#8FA3C0;font-size:12px'>vía {_t['etf']}</span></div>"
                  f"<div style='font-size:11px;color:#B9C9E2;margin-top:6px;line-height:1.6'>{esc(_t['why'])}</div>"
                  f"<div style='font-size:10px;color:#5E708A;margin-top:6px'>se ejecuta el lunes si el viernes lo confirma · detalle en Contexto</div>")
            mesa.append(_box("🏆 Candidato de la semana (lo elige el sistema)", c2))
        # 3) tempranos: giro al alza sin extender, con flujo
        if early:
            c3 = ""
            for r in early[:5]:
                fl = (flow or {}).get(r["sym"], {}) or {}
                if fl.get("diverg") == "distribucion oculta":
                    tag, tcol = "⚠ sale dinero", "#F4607A"
                elif fl.get("obv_above") and fl.get("cmf_pos"):
                    tag, tcol = "✓ flujo confirma", "#2FD08A"
                elif fl.get("obv_above") or fl.get("cmf_pos"):
                    tag, tcol = "~ parcial", "#F4B740"
                else:
                    tag, tcol = "sin flujo aún", "#5E708A"
                c3 += (f"<div style='display:flex;justify-content:space-between;font-size:12px;margin:4px 0'>"
                       f"<span><b>{r['sym']}</b> <span style='color:#8FA3C0;font-size:10px'>ext {r['ext']}%</span></span>"
                       f"<span style='color:{tcol};font-size:11px'>{tag}</span></div>")
            c3 += "<div style='font-size:10px;color:#5E708A;margin-top:6px'>girando al alza y aún cerca de la media — la entrada barata, si el flujo acompaña</div>"
            mesa.append(_box("🌱 Tempranos — giro sin extender", c3))
        # 4) DURMIENTES: suelo + silencio + giro (unificado; sustituye a suelos y giros al alza)
        if suelo:
            _c_set = {c["sym"] for c in (contra_sigs or [])}
            c4 = ""
            for r in suelo[:6]:
                if r["sangra"]:
                    verd, vcol = "aún sangra", "#F4607A"
                elif r["despertando"] and r["sil"] >= 2:
                    verd, vcol = "🌅 DESPIERTA EN SILENCIO", "#2FD08A"
                elif r["despertando"]:
                    verd, vcol = "despertando", "#2FD08A"
                elif r.get("fase") == "PRE-DESPERTAR":
                    verd, vcol = f"🌱 pre-despertar {r.get('pre', 0)}/4", "#4CC2E0"
                elif r.get("fase") == "ACUMULACION":
                    verd, vcol = "🧲 acumulando", "#7FD8A0"
                else:
                    verd, vcol = "dormido", "#9FB0C8"
                badge = " <span style='color:#7BD88F;font-size:9px;border:1px solid #7BD88F55;border-radius:3px;padding:0 3px'>0/3</span>" if r["sym"] in _c_set else ""
                _sq = "🤫" * max(r["sil"], 0)
                c4 += (f"<div style='display:flex;justify-content:space-between;font-size:12px;margin:4px 0'>"
                       f"<span><b>{r['sym']}</b>{badge} <span style='color:#8FA3C0;font-size:10px'>{r['pts']}/10 {_sq}"
                       + (f" · giro {r['vert']:.1f}×" if (r.get('vert') and (r.get('dmom') or 0) >= 1.5) else "") + "</span></span>"
                       f"<span style='color:{vcol};font-size:11px'>{verd}</span></div>")
            c4 += ("<div style='font-size:10px;color:#5E708A;margin-top:6px'>castigado + 🤫 silencio (nadie habla de él) + giro vertical con el precio aún quieto = "
                   "anticipación. Solo con cierre de viernes, flujo que no sale y tamaño de manga. Detalle completo en Contexto → 😴 DURMIENTES.</div>")
            mesa.append(_box("😴 Durmientes — suelo + silencio + giro", c4, "#7BD88F44"))
        # 5b) giro intradia de la ultima sesion (el patron de la trampa de apertura)
        if giro and giro.get("rows"):
            c5b = ""
            if giro.get("rotacion"):
                c5b += ("<div style='font-size:12px;margin-bottom:8px;padding:7px 9px;background:rgba(244,183,64,.1);"
                        "border:1px solid #F4B74055;border-radius:7px;color:#F4B740'><b>⚠ ROTACIÓN INTRADÍA DETECTADA</b>: "
                        "en la misma sesión vendieron lo caliente (gap arriba → cierre abajo) y compraron lo frío "
                        "(gap abajo → cierre arriba). Si se repite 2-3 sesiones, suele anticipar el relevo semanal.</div>")
            for g in giro["rows"][:6]:
                if g["sig"] == "bajista":
                    ic, col, lect = "🔻", "#F4607A", f"abrió {g['gap']:+.1f}%, cerró en el {g['pos']}% del rango — vendieron la subida"
                else:
                    ic, col, lect = "🔹", "#2FD08A", f"abrió {g['gap']:+.1f}%, cerró en el {g['pos']}% del rango — compraron el miedo"
                vtxt = f" · vol {g['vol_rel']}×" if g.get("vol_rel") else ""
                c5b += (f"<div style='font-size:12px;margin:4px 0'>{ic} <b>{g['sym']}</b> "
                        f"<span style='color:{col}'>{lect}</span><span style='color:#5E708A;font-size:10px'>{vtxt}</span></div>")
            c5b += (f"<div style='font-size:10px;color:#5E708A;margin-top:6px'>vela diaria del {esc(giro.get('fecha', ''))} · "
                    "aviso A CIERRE VENCIDO (sin datos intradía en vivo): léelo por la mañana antes de la apertura. "
                    "Observación diaria, ejecución el viernes — como siempre.</div>")
            mesa.append(_box("🔀 Giro intradía — quién vendió la subida y quién compró el miedo", c5b, "#F4B74055"))
        # 6) alertas de riesgo (margen + escalones)
        c6 = ""
        if apal:
            for b in apal["brokers"]:
                e5 = b["esc"].get(-5) or {}
                if e5.get("estado") and e5["estado"] != "ok":
                    c6 += (f"<div style='font-size:12px;margin:4px 0'>🚨 <b>{esc(b['broker'])}</b>: a S&P −5% → "
                           f"<b style='color:#F4607A'>{esc(e5['estado'])}</b>"
                           + (f" (nivel {e5['nivel_after']:.0f}%)" if e5.get("nivel_after") else "") + "</div>")
        if dd is not None:
            try:
                _fal = 5.0 - abs(dd)
                if 0 < _fal <= 3.5:
                    c6 += (f"<div style='font-size:12px;margin:4px 0'>⏳ Escalón −5% a <b>{_fal:.1f}%</b> de distancia — "
                           "¿la pólvora está líquida y FUERA de las cuentas con margen?</div>")
            except Exception:
                pass
        if c6:
            c6 += "<div style='font-size:10px;color:#5E708A;margin-top:6px'>detalle completo en Contexto → Apalancamiento consolidado</div>"
            mesa.append(_box("⚠️ Riesgo antes que rentabilidad", c6, "#F4607A55"))
        html.append("<div class='panel full'><h2>🎛️ Mesa de operaciones — la semana en una pantalla</h2>"
                    "<div class='note'>Lo accionable de todo el terminal, junto: semáforo y órdenes, el candidato, los <b>tempranos</b> (girando sin extender), "
                    "y los <b>😴 durmientes</b> (castigo + silencio + giro con el precio aún quieto — la anticipación, con la señal contraria 0/3 marcada). "
                    "El detalle y el porqué de cada cosa siguen en Contexto — esto es la chuleta del viernes por la tarde. No es asesoramiento.</div>"
                    "<div style='display:flex;flex-wrap:wrap;gap:12px'>" + "".join(mesa) + "</div>"
                    "<div class='note' style='margin-top:10px;color:#5E708A'>Ritual: 1) cierre del viernes confirmado → 2) órdenes de venta primero (liberan margen) → "
                    "3) rotaciones de la cartera → 4) candidato/tempranos solo si el flujo confirma → 5) suelos y 0/3 con tamaño de manga contraria, nunca apalancados.</div></div>")
    except Exception:
        pass

    # ===== RESUMEN SENCILLO: DONDE ESTAR (funde scoring + cuadrante + flujo) =====
    try:
        _estar, _evitar = [], []
        for r in (scores or []):
            sym = r["sym"]
            d = rrg.get(sym)
            if d is None:
                continue
            quad = d["quad"]
            fcmf = flow.get(sym, {}).get("cmf")
            if r.get("distrib"):
                _evitar.append((sym, "dinero saliendo"))
            elif quad in ("leading", "improving") and r["score"] >= 4 and (fcmf is None or fcmf >= 0):
                _estar.append({"sym": sym, "sc": r["score"], "quad": quad, "cmf": fcmf, "in_cart": sym in cartera_syms})
            elif r["score"] <= 2:
                _evitar.append((sym, f"débil {r['score']}/5"))
        _estar.sort(key=lambda x: (0 if x["in_cart"] else 1, -x["sc"], -(x["cmf"] or 0)))
        # mini-lineas: precio del ETF y fuerza vs mercado (ETF/SPY), ultimas ~10 semanas (como la estela)
        def _pv(sym, n=10):
            try:
                return list(df[sym].dropna().iloc[-n:])
            except Exception:
                return []
        def _rsv(sym, n=10):
            try:
                return list((df[sym] / df[BENCH]).dropna().iloc[-n:])
            except Exception:
                return []
        er = ""
        for e in _estar[:9]:
            nm = NAMES.get(e["sym"], (e["sym"], e["sym"], ""))[1]
            qn = QUAD.get(e["quad"], (e["quad"], ""))[0]
            star = "⭐ " if e["in_cart"] else ""
            cmftxt = (f"{e['cmf']:+.2f}" if e["cmf"] is not None else "—")
            base = "líder" if e["quad"] == "leading" else "girando al alza"
            flujo_txt = "dinero entrando" if (e["cmf"] or 0) > 0.03 else "flujo tibio (vigila)"
            verd = f"{base} + {flujo_txt}"
            vcol = "#2FD08A" if (e["cmf"] or 0) > 0.03 else "#F4B740"
            er += (f"<tr><td class='se-l'>{star}<b>{e['sym']}</b> <span style='color:var(--txt3);font-size:11px'>{esc(nm)}</span></td>"
                   f"<td class='r'>{e['sc']}/5</td><td class='r' style='font-size:11px'>{esc(qn)}</td>"
                   f"<td class='r' style='font-size:11px'>CMF {cmftxt}</td>"
                   f"<td class='r'>{_spark(_pv(e['sym']), w=62, h=18)}</td>"
                   f"<td class='r' style='font-size:11px;color:{vcol}'>{esc(verd)}</td></tr>")
        evtxt = ", ".join(f"<b>{s}</b> ({esc(w)})" for s, w in _evitar[:12])
        html.append("<div class='panel full'><h2>✅ Dónde estar — CANDIDATOS por puntuación (⭐ = en la CARTERA FINAL)</h2>"
                    "<div style='font-size:13px;margin:6px 0;padding:8px 10px;background:rgba(91,140,255,.08);border:1px solid #5B8CFF33;border-radius:7px'>"
                    "CARTERA FINAL de la semana: <b style='color:#5B8CFF'>" + esc(", ".join(CARTERA_FINAL) if CARTERA_FINAL else "liquidez") + "</b>"
                    "<span style='color:#8FA3C0;font-size:11px'> — esta tabla son los candidatos que pasan el corte de puntuación; la cartera además exige cuadrante, momentum absoluto, flujo y tope de posiciones. Si un 4/5 no lleva ⭐, algún filtro lo dejó fuera (lo dice la Cartera de Contexto).</span></div>"
                    "<div class='note'>Todo el panel en una tabla: los sectores donde <b>coinciden las tres cosas</b> — tendencia (Líder o Mejorando), "
                    "puntuación alta (≥4/5) y <b>el dinero entrando</b>. La ⭐ marca los que están en tu <b>Cartera</b> "
                    "(el <b>% exacto</b> en <b>Contexto → Cartera de la semana</b>). La columna <b>precio 8s</b> es la mini-línea del precio (verde sube, rojo baja). No es asesoramiento.</div>"
                    "<div class='scrollx'><table class='se'><tr><th class='se-l'>sector</th><th class='r'>nota</th>"
                    "<th class='r'>tendencia</th><th class='r'>flujo</th><th class='r'>precio 8s</th><th class='r'>por qué</th></tr>"
                    + (er or "<tr><td colspan='6' style='color:#9FB0C8'>Ninguno cumple las tres a la vez esta semana — mejor esperar.</td></tr>")
                    + "</table></div>"
                    + (f"<div class='note' style='margin-top:8px;color:#F4607A'>⛔ <b>Fuera / evitar:</b> {evtxt}.</div>" if evtxt else "")
                    + "</div>")

        # ===== MURAL: TODOS los sectores, estela (fuerza) vs precio =====
        def _lectura(pch, rch):
            if rch > 1 and pch > 2:   return "sube de verdad", "#2FD08A"
            if rch > 1 and abs(pch) <= 2:  return "posible acumulación (fuerza↑ precio plano)", "#5AA9E6"
            if rch > 1:               return "solo fuerza relativa", "#F4B740"
            if rch < -1 and abs(pch) <= 2: return "posible distribución (fuerza↓ precio plano)", "#F4B740"
            if pch > 2 and rch < -1:  return "sube pero pierde fuerza", "#F4B740"
            if pch < -2:              return "flojo", "#F4607A"
            return "plano", "#9FB0C8"
        _qorder = {"leading": 0, "improving": 1, "weakening": 2, "lagging": 3}
        _all = sorted(((s, d) for s, d in rrg.items() if s != BENCH),
                      key=lambda kv: (_qorder.get(kv[1]["quad"], 9), -kv[1].get("rel4", 0)))
        mu, _lastq = "", None
        for s, d in _all:
            pv, rv = _pv(s), _rsv(s)
            if len(pv) < 3:
                continue
            pch = (pv[-1] / pv[0] - 1) * 100 if pv[0] else 0
            rch = (rv[-1] / rv[0] - 1) * 100 if (len(rv) >= 2 and rv[0]) else 0
            vd, vc = _lectura(pch, rch)
            qn, qc = QUAD.get(d["quad"], (d["quad"], "#9FB0C8"))[0], {"leading": "#2FD08A", "improving": "#5AA9E6", "weakening": "#F4B740", "lagging": "#F4607A"}.get(d["quad"], "#9FB0C8")
            if d["quad"] != _lastq:
                mu += f"<tr><td colspan='5' style='color:{qc};font-weight:700;font-size:11px;padding-top:10px'>— {esc(qn)} —</td></tr>"
                _lastq = d["quad"]
            nm = NAMES.get(s, (s, s, ""))[1]
            mu += (f"<tr><td class='se-l'><b>{s}</b> <span style='color:var(--txt3);font-size:11px'>{esc(nm)}</span></td>"
                   f"<td class='r'>{_spark(pv, w=76, h=20)}</td>"
                   f"<td class='r'>{_spark(rv, w=76, h=20, color='#5B8CFF')}</td>"
                   f"<td class='r' style='font-size:11px'>{pch:+.1f}%</td>"
                   f"<td class='r' style='font-size:11px;color:{vc}'>{esc(vd)}</td></tr>")
        if mu:
            html.append("<div class='panel full'><h2>🧱 Mural — todos los sectores: estela vs precio</h2>"
                        "<div class='note'>Los ~8 últimas semanas de <b>todos</b> los ETF, para comparar de un vistazo. "
                        "<b>Precio</b> (verde/rojo) = qué hizo el ETF · <b>fuerza vs mercado</b> (azul) = su estela del RRG en línea · <b>% 8s</b> = lo que ha hecho el precio. "
                        "Agrupados por cuadrante (Líder arriba). Si la fuerza sube pero el precio está plano = <b>posible acumulación</b>; "
                        "si la fuerza baja con precio plano = <b>posible distribución</b>. No es asesoramiento.</div>"
                        "<div class='scrollx'><table class='se'><tr><th class='se-l'>ETF</th><th class='r'>precio 8s</th>"
                        "<th class='r'>fuerza 8s</th><th class='r'>% 8s</th><th class='r'>lectura</th></tr>" + mu + "</table></div></div>")

        # ===== PLAN DE SALIDA (media semanal como stop de tendencia) =====
        _exit_syms = list(dict.fromkeys(list(cartera_syms) + [e["sym"] for e in _estar]))
        xr = ""
        for sym in _exit_syms:
            try:
                ser = df[sym].dropna()
            except Exception:
                continue
            if len(ser) < SALIDA_MA_SEMANAS + 9:
                continue
            price = float(ser.iloc[-1])
            ma_s = ser.rolling(SALIDA_MA_SEMANAS).mean()
            ma = float(ma_s.iloc[-1])
            if ma <= 0:
                continue
            # capa 1: banda adaptativa = K x volatilidad semanal propia (26s). En laterales la banda absorbe el ruido.
            ret = ser.pct_change().iloc[-26:].dropna()
            sig = float(ret.std()) if len(ret) >= 8 else 0.02
            banda = max(0.01, SALIDA_BANDA_K * sig)
            # capa 3: stop duro (chandelier con cierres): pico 12s - K x volatilidad
            peak12 = float(ser.iloc[-12:].max())
            chand = peak12 * (1 - SALIDA_STOP_K * sig)
            # capa 2: confirmacion -> semanas consecutivas cerrando bajo la media (calculado del propio historico, sin estado)
            below = (ser < ma_s).dropna()
            n_below = 0
            for v in reversed(list(below)):
                if v:
                    n_below += 1
                else:
                    break
            pct = (price / ma - 1) * 100
            if price < chand:
                st, sc = "🔴 SALIR — stop duro (desplome desde el pico)", "#F4607A"
            elif price < ma * (1 - banda):
                st, sc = "🔴 SALIR — ruptura clara (fuera de banda)", "#F4607A"
            elif price < ma and n_below >= 2:
                st, sc = f"🔴 SALIR — {n_below}ª semana bajo la media (confirmado)", "#F4607A"
            elif price < ma:
                st, sc = "⚠ 1ª semana bajo media — confirma el próximo viernes", "#F4B740"
            elif pct < banda * 100:
                st, sc = "🟡 cerca de la media — vigila", "#F4B740"
            else:
                st, sc = "🟢 mantén", "#2FD08A"
            nm = NAMES.get(sym, (sym, sym, ""))[1]
            xr += (f"<tr><td class='se-l'><b>{sym}</b> <span style='color:var(--txt3);font-size:11px'>{esc(nm)}</span></td>"
                   f"<td class='r'>{_spark(list(ser.iloc[-12:]))}</td>"
                   f"<td class='r' style='font-size:11px'>{price:,.2f}</td>"
                   f"<td class='r' style='font-size:11px'>{ma:,.2f} <span style='color:var(--txt3)'>±{banda*100:.1f}%</span></td>"
                   f"<td class='r' style='font-size:11px'>{chand:,.2f}</td>"
                   f"<td class='r' style='font-size:11px;color:{sc};white-space:nowrap'>{esc(st)}</td></tr>")
        if xr:
            html.append("<div class='panel full'><h2>🛑 Plan de salida — para no devolver la plusvalía</h2>"
                        f"<div class='note'>Motor de salida en <b>3 capas anti-latigazo</b> (el fallo de una media simple es que en lateral te saca y mete sin parar): "
                        f"<b>① Banda adaptativa</b> — cerrar bajo la media de {SALIDA_MA_SEMANAS}s <i>dentro</i> de la banda (±K×volatilidad propia del ETF) NO dispara la venta; "
                        "en laterales el ruido queda absorbido. <b>② Confirmación</b> — bajo la media dentro de banda, hace falta la <b>2ª semana consecutiva</b> para SALIR (la 1ª es aviso). "
                        "<b>③ Stop duro</b> — pico de 12 semanas − K×volatilidad: si el precio cae ahí, SALIR sin esperar a la media (protege del desplome rápido). "
                        "Salir = ruptura clara fuera de banda, o 2ª semana confirmada, o stop duro. Ajustable en SALIDA_BANDA_K / SALIDA_STOP_K.</div>"
                        "<div class='scrollx'><table class='se'><tr><th class='se-l'>ETF</th><th class='r'>precio 12s</th>"
                        f"<th class='r'>precio</th><th class='r'>media {SALIDA_MA_SEMANAS}s ± banda</th><th class='r'>stop duro</th><th class='r'>señal</th></tr>"
                        + xr + "</table></div>"
                        "<div class='note' style='margin-top:8px;color:#F4B740'>⚠ <b>Para tu LABU (biotech x3) y cualquier apalancado:</b> NO uses la media del propio apalancado (el decay la distorsiona). "
                        "Usa la señal del <b>ETF base</b> — para LABU es <b>XBI</b>: cuando XBI cierre bajo su media, sal de LABU. Y en apalancado sé aún más estricto (media más corta, o salir al primer cierre por debajo), porque la vuelta con 3x + decay es brutal. No es asesoramiento.</div></div>")
    except Exception:
        pass

    try:
        QL = {"leading": "Líder", "improving": "Mejorando", "weakening": "Debilitándose", "lagging": "Rezagado"}
        QC = {"leading": "#2FD08A", "improving": "#5AA9E6", "weakening": "#F4B740", "lagging": "#F4607A"}
        GL = {"sector": "Sector", "subsector": "Subsector", "tech": "Tech", "limpia": "E.limpia", "materiales": "Materiales", "iainfra": "IA/infra", "internac": "Internac.", "refugio": "Refugio"}
        cand, warns = [], []
        for r in (scores or []):
            s = r["sym"]; sc = r["score"]; distrib = bool(r.get("distrib")); am = r.get("abs_mom", 0)
            q = (rrg.get(s, {}) or {}).get("quad")
            f = (flow or {}).get(s, {})
            money_in = bool(f.get("obv_above")) and bool(f.get("cmf_pos"))
            cmf_val = f.get("cmf", 0.0) or 0.0
            if (q in ("leading", "improving")) and sc >= 3 and not distrib and money_in and am > 0:
                cand.append((s, sc, q, am, cmf_val))
            elif distrib or (q == "weakening" and sc >= 3):
                warns.append((s, q, sc, "distribución oculta" if distrib else "debilitándose"))
        cand.sort(key=lambda c: -(c[4] or 0))   # ordenar por fuerza de flujo (CMF), de más a menos dinero entrando
        crows = ""
        for s, sc, q, am, cmf in cand:
            desc = NAMES.get(s, (s, "", ""))[1] or s
            grp = GL.get(GRUPO.get(s, ""), "")
            _fsc = fresh_stocks(leaders, s)
            lid = (", ".join((PHASE_INFO.get(r.get("phase"), ("",))[0] + " " + r["sym"] + f" ↑{r['drs']}").strip() for r in _fsc)) if _fsc else TOP_HOLDING.get(s, "")
            lid_lbl = "acciones" if _fsc else "líder"
            in_cart = s in cartera_syms
            badge = ("<span style='color:#2FD08A;font-size:10px;font-weight:700'> ✓ en cartera</span>"
                     if in_cart else "<span style='color:#5AA9E6;font-size:10px;font-weight:700'> 🆕 nueva</span>")
            cmf_col = "#2FD08A" if cmf >= 0.10 else ("#7BC47F" if cmf > 0 else "#9FB0C8")
            crows += (f"<tr><td class='se-l'><b>{s}</b>{badge} <span style='color:var(--txt3);font-size:11px'>{esc(desc)}</span>"
                      + (f"<br><span style='color:#5E708A;font-size:10px'>{lid_lbl}: {esc(lid)}</span>" if lid else "") + "</td>"
                      f"<td class='r'><span style='color:{QC.get(q, '#9FB0C8')}'>{QL.get(q, q)}</span></td>"
                      f"<td class='r' style='font-weight:700;color:{cmf_col}'>{cmf:+.2f}</td>"
                      f"<td class='r' style='font-weight:700;color:{'#2FD08A' if sc >= 4 else '#F4B740'}'>{sc}/5</td>"
                      f"<td class='r' style='color:#2FD08A'>+{am:g}%</td>"
                      f"<td class='r' style='color:#5E708A;font-size:11px'>{grp}</td></tr>")
        if not crows:
            crows = "<tr><td colspan='6' style='color:#9FB0C8;padding:12px'>Ningún candidato pasa todos los filtros ahora mismo. En seco: no fuerces entradas.</td></tr>"
        # ---- 3 VÍAS DE ENTRAR por cada candidato: ETF normal / apalancado / cesto sintético ----
        destr = ""
        for s, sc, q, am, cmf in cand:
            rl = (leaders or {}).get(s)
            if not rl:
                continue
            lev = LEVERAGED.get(s)
            if lev:
                via2 = f"<b>{lev[0]}</b> ({lev[1]}) <span style='color:#F4B740;font-size:10px'>⚠ decay diario</span>"
            else:
                via2 = "<span style='color:#9FB0C8'>sin ETF apalancado limpio → vía <b>CFD en XTB</b> sobre las acciones</span>"
            basket = [rr for rr in rl if rr.get("rs", 0) >= SINT_MIN_RS and (rr.get("drs") or 0) > 0 and rr.get("hi", 100) < SINT_MAX_HI][:SINT_TOP]
            if basket:
                wgt = round(100.0 / len(basket))
                chips = " · ".join(f"{PHASE_INFO.get(b.get('phase'),('',))[0]} <b>{b['sym']}</b> {wgt}%" for b in basket)
                nota = "(equiponderado)" if len(basket) >= SINT_MIN_N else "(pocas cumplen hoy; cesto fino)"
                via3 = f"{chips} <span style='color:#5E708A;font-size:10px'>{nota}</span>"
            else:
                fs = fresh_stocks(leaders, s, n=3, max_hi=97)
                if fs:
                    chips2 = " · ".join(f"{PHASE_INFO.get(r.get('phase'),('',))[0]} <b>{r['sym']}</b> RS{r['rs']} ↑{r['drs']} <span style='color:#5E708A;font-size:10px'>({r['hi']}% máx)</span>" for r in fs)
                    via3 = f"{chips2} <span style='color:#5E708A;font-size:10px'>(las que más aceleran y menos estiradas; revisa cada semana)</span>"
                else:
                    via3 = "<span style='color:#9FB0C8'>sin acciones claras hoy → mejor el ETF o esperar</span>"
            trows = ""
            for j, rr in enumerate(rl[:8]):
                sym2 = rr["sym"]; rs2 = rr.get("rs", 0); hi2 = rr.get("hi", 0); dr = rr.get("drs")
                tag = " 🔥" if (rs2 >= 70 and (dr or 0) > 0) else ""
                if hi2 >= SINT_MAX_HI:
                    tag += " <span style='color:#F4B740;font-size:10px'>⚠ extendida</span>"
                if (dr or 0) > 0:
                    acc = f"<span style='color:#2FD08A'>⚡ +{dr}</span>"
                elif dr is not None and dr < 0:
                    acc = f"<span style='color:#F4607A'>▼ {dr}</span>"
                else:
                    acc = "—"
                in_b = any(b["sym"] == sym2 for b in basket)
                stl = "font-weight:700;color:#2FD08A" if in_b else ""
                ph2 = PHASE_INFO.get(rr.get("phase"), ("",))[0]
                trows += (f"<tr><td class='se-l' style='{stl}'>{ph2} {sym2}{' 🧺' if in_b else ''}{tag}</td>"
                          f"<td class='r'>{rs2}</td><td class='r'>{hi2}%</td><td class='r'>{acc}</td></tr>")
            desc = NAMES.get(s, (s, "", ""))[1] or s
            destr += (
                f"<div style='margin:14px 0 6px;padding:10px;border:1px solid var(--line);border-radius:8px'>"
                f"<div style='font-weight:700;margin-bottom:6px'>{s} · <span style='color:var(--txt3);font-weight:400'>{esc(desc)}</span> — 3 vías de entrar:</div>"
                f"<div class='note' style='margin:2px 0'>① <b>ETF</b>: {s}</div>"
                f"<div class='note' style='margin:2px 0'>② <b>Apalancado</b>: {via2}</div>"
                f"<div class='note' style='margin:2px 0'>③ <b>Sintético</b> (fuertes sin estar en máximos): {via3}</div>"
                f"<details style='margin-top:6px'><summary style='cursor:pointer;color:#9FB0C8;font-size:12px'>ver ranking completo de {s} (🧺 = entra al cesto)</summary>"
                "<div class='scrollx'><table class='se'><tr><th class='se-l'>empresa</th><th class='r'>percentil</th><th class='r'>% máx 52s</th><th class='r'>acel 3m</th></tr>"
                + trows + "</table></div></details></div>")
        destr_block = (("<div class='note' style='margin-top:16px'><b>🧺 Cómo entrar en cada candidato — 3 vías, tú eliges:</b> "
                        "el <b>ETF</b> normal, su <b>apalancado</b> (⚠ con decay diario, tu mayor riesgo en lateral), "
                        "o un <b>cesto sintético</b> con las acciones más fuertes que <b>aún no estén pegadas a máximos</b> "
                        f"(percentil ≥ {SINT_MIN_RS}, acelerando, por debajo del {SINT_MAX_HI}% de máximos — el filtro que evita comprar la punta, como pasó con MLI).</div>"
                        + destr
                        + "<div class='note' style='margin-top:6px;color:#5E708A'>El cesto reduce el riesgo de una sola acción, pero 4-5 mid-caps siguen siendo más concentrado que el ETF entero. Y es momentum: lo fuerte hoy puede revertir. No es asesoramiento.</div>") if destr else "")
        wrows = ""
        for s, q, sc, why in warns[:10]:
            desc = NAMES.get(s, (s, "", ""))[1] or s
            wrows += (f"<tr><td class='se-l'><b>{s}</b> <span style='color:var(--txt3);font-size:11px'>{esc(desc)}</span></td>"
                      f"<td class='r' style='color:#F4607A'>{esc(why)}</td></tr>")
        op = (
            "<div class='panel full'><h2>🎯 Operativa — candidatos ya filtrados</h2>"
            "<div class='note'>Lista corta de <b>posibles entradas</b> que pasan <b>todos</b> los filtros a la vez: "
            "cuadrante <b>Líder o Mejorando</b> + puntuación ≥ 3/5 + <b>el flujo confirma</b> (OBV y CMF a favor) + "
            "sin distribución oculta + ganando dinero a 3 meses. No es una orden de compra; es lo que merece mirar. "
            "<b style='color:#2FD08A'>✓ en cartera</b> = ya está en tu cartera de la semana · <b style='color:#5AA9E6'>🆕 nueva</b> = entrada fresca con flujo confirmando que aún no tienes. "
            "<b>Ordenado por flujo (CMF)</b>: arriba = donde más dinero está entrando ahora. Ojo: el CMF más alto no es automáticamente la mejor entrada (puede estar ya extendida) — cruza con ✓/🆕 y el destripado.</div>"
            "<div class='scrollx'><table class='se'><tr><th class='se-l'>candidato</th><th class='r'>cuadrante</th><th class='r'>flujo (CMF)</th><th class='r'>nota</th><th class='r'>mom 3m</th><th class='r'>grupo</th></tr>"
            + crows + "</table></div>"
            + destr_block
            + (("<div class='note' style='margin-top:14px;color:#F4607A'><b>⚠ Ojo / evitar (no entrar):</b></div>"
                "<div class='scrollx'><table class='se'>" + wrows + "</table></div>") if wrows else "")
            + "<div class='note' style='margin-top:14px'><b>Cómo ejecutar (tu rutina):</b> decides en el <b>cierre del viernes</b> y ejecutas el lunes; "
              "tamaño por <b>volatilidad inversa</b> (menos en lo que más se mueve); <b>stop</b> bajo el mínimo de las últimas semanas o un % fijo que aguantes; "
              "y si está en <b>vertical</b> (mom 3m muy alto), mejor esperar una pausa que perseguir la punta. No es asesoramiento.</div>"
            "<div class='note' style='margin-top:8px;color:#5E708A'>Próximo paso (Fase 2): aquí se conectará tu <b>cartera</b> (archivo cartera.json) para mapear tus posiciones a mantener/añadir/recortar/salir y ver el saldo por broker.</div>"
            "</div>")
        html.append(op)
    except Exception:
        pass
    if _op_details_abierto:
        html.append("</details>")
    html.append("</div>")

    # ===== V-PRO — TERMINAL PRO (estetica de terminal profesional: negro, ambar, monoespaciada, densa) =====
    html.append("<div id='vista-bbg' style='display:none'>")
    _bbg_mark = len(html)
    try:
        AMB, GRN, RED, GRY, CYN = "#FFB000", "#00E676", "#FF5252", "#8A96A8", "#4CC2E0"
        html.append(
            "<style>"
            ".bbgp{background:#050505;border:1px solid #2A2A2A;border-radius:4px;padding:0;margin:0 0 10px 0;"
            "font-family:'IBM Plex Mono','Cascadia Mono','Consolas','Courier New',monospace;overflow:hidden}"
            ".bbgh{background:#141414;color:#FFB000;font-size:11px;letter-spacing:1.5px;padding:6px 10px;"
            "border-bottom:1px solid #2A2A2A;font-weight:700}"
            ".bbgb{padding:8px 10px;font-size:12px;line-height:1.75;color:#D8DEE9}"
            ".bbgb table{width:100%;border-collapse:collapse;font-size:11.5px}"
            ".bbgb th{color:#8A96A8;text-align:right;font-weight:400;border-bottom:1px solid #222;padding:2px 6px;font-size:10px;letter-spacing:.5px}"
            ".bbgb th:first-child,.bbgb td:first-child{text-align:left}"
            ".bbgb td{text-align:right;padding:2.5px 6px;border-bottom:1px solid #141414;white-space:nowrap}"
            ".bbgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:10px;grid-column:1/-1}"
            ".bbgtapewrap{overflow:hidden;white-space:nowrap;background:#050505;border:1px solid #2A2A2A;border-radius:4px;"
            "padding:7px 0;margin-bottom:10px;grid-column:1/-1}"
            ".bbgtape{display:inline-block;animation:bbgtape 55s linear infinite;font-family:'Consolas','Courier New',monospace;font-size:12px}"
            "@keyframes bbgtape{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}"
            ".bbgfk{display:inline-block;background:#141414;border:1px solid #333;color:#FFB000;font-size:10px;"
            "padding:3px 10px;border-radius:3px;margin-right:6px;cursor:pointer;letter-spacing:1px}"
            ".bbgfk:hover{background:#FFB000;color:#000}"
            "</style>")
        def _ser(sym):
            try:
                if sym == "QQQ" and sym not in df.columns and nq_close is not None:
                    s = nq_close.dropna()              # QQQ llega por nq_close, no por df
                else:
                    s = df[sym].dropna()
                return s if len(s) else None
            except Exception as _dege:
                _deg("build_html:9315", _dege)
                return None
        def _chg(sym, n=1):
            s = _ser(sym)
            if s is None or len(s) <= n:
                return None
            try:
                return float(s.iloc[-1] / s.iloc[-1 - n] - 1) * 100
            except Exception as _dege:
                _deg("build_html:9323", _dege)
                return None
        def _ytd(sym):
            s = _ser(sym)
            if s is None or len(s) < 2:
                return None
            try:
                y = s.index[-1].year
                prev = s[s.index.year < y]
                base = prev.iloc[-1] if len(prev) else s.iloc[0]
                return float(s.iloc[-1] / base - 1) * 100
            except Exception as _dege:
                _deg("build_html:9334", _dege)
                return None
        def _fp(v, dec=1):
            if v is None:
                return f"<span style='color:{GRY}'>—</span>"
            return f"<span style='color:{GRN if v >= 0 else RED}'>{v:+.{dec}f}%</span>"
        def _bsp(sym, n=14):
            s = _ser(sym)
            if s is None or len(s) < 4:
                return ""
            v = list(s.iloc[-n:])
            mn, mx = min(v), max(v)
            rng = (mx - mn) or 1.0
            blocks = "▁▂▃▄▅▆▇█"
            c = GRN if v[-1] >= v[0] else RED
            return ("<span style='color:%s;letter-spacing:1px;font-size:10px'>" % c
                    + "".join(blocks[int((x - mn) / rng * 7)] for x in v) + "</span>")
        _mod = lambda titulo, cuerpo: f"<div class='bbgp'><div class='bbgh'>{titulo}</div><div class='bbgb'>{cuerpo}</div></div>"
        # --- CINTA DE COTIZACIONES ---
        tape = ""
        for s in [x for x in rrg.keys() if x in df.columns]:
            c = _chg(s, 1)
            if c is None:
                continue
            col = GRN if c >= 0 else RED
            arrow = "▲" if c >= 0 else "▼"
            tape += f"<span style='color:#E8E8E8;margin-left:26px'>{s}</span> <span style='color:{col}'>{arrow}{abs(c):.1f}%</span>"
        html.append(f"<div class='bbgtapewrap'><div class='bbgtape'>{tape}{tape}</div></div>")
        # --- CABECERA + TECLAS DE FUNCION ---
        _rk = risk.get("label", "—") if isinstance(risk, dict) else str(risk)
        html.append("<div class='bbgp' style='grid-column:1/-1'><div class='bbgb' style='display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;align-items:center'>"
                    f"<span style='color:{AMB};font-size:14px;font-weight:700;letter-spacing:2px'>PeVR TERMINAL <span style='color:#555'>|</span> PRO</span>"
                    f"<span style='color:{GRY};font-size:11px'>cierre {last_lbl} · {esc(sem_short)} · {esc(reg_short)} · {esc(_rk)}"
                    + (f" · F&G {fg_idx['score']}" if fg_idx else "") + "</span>"
                    "<span><span class='bbgfk' onclick=\"document.querySelectorAll('.mainview')[0].click()\">F1 CONTEXTO</span>"
                    "<span class='bbgfk' onclick=\"document.querySelectorAll('.mainview')[1].click()\">F2 OPERATIVA</span>"
                    "<span class='bbgfk' onclick=\"document.querySelectorAll('.mainview')[2].click()\">F3 VIGILANCIA</span>"
                    "<span class='bbgfk' onclick='descargarPDF()'>F9 PDF</span></span>"
                    "</div></div>")
        html.append("<div class='bbgrid'>")
        # --- MODULO 1: MARKET MONITOR ---
        mm = "<table><tr><th>TICKER</th><th>1S</th><th>4S</th><th>12S</th><th>YTD</th><th>14 SEM</th></tr>"
        for s in ["SPY", "QQQ", "IWM", "TLT", "GLD", "UUP", "HYG", "IBIT", "EURUSD", "FXI", "KWEB", "EWP"]:
            if s not in df.columns:
                continue
            mm += (f"<tr><td style='color:{AMB};font-weight:700'>{s}</td><td>{_fp(_chg(s, 1))}</td>"
                   f"<td>{_fp(_chg(s, 4))}</td><td>{_fp(_chg(s, 12))}</td><td>{_fp(_ytd(s))}</td><td>{_bsp(s)}</td></tr>")
        mm += "</table>"
        html.append(_mod("MARKET MONITOR — ÍNDICES · REFUGIO · FX", mm))
        # --- MODULO 2: FLOW MONITOR (CMF) ---
        _fl = sorted([(s, f) for s, f in (flow or {}).items() if f.get("cmf") is not None and s in rrg],
                     key=lambda x: -x[1]["cmf"])
        fm = "<table><tr><th>ENTRA $</th><th>CMF</th><th>VOL</th><th></th><th>SALE $</th><th>CMF</th><th>VOL</th><th></th></tr>"
        _in = [x for x in _fl if x[1]["cmf"] > 0.05][:8]
        _out = [x for x in _fl if x[1]["cmf"] < -0.05][-8:][::-1]
        for i in range(max(len(_in), len(_out))):
            fm += "<tr>"
            for grp, col in ((_in, GRN), (_out, RED)):
                if i < len(grp):
                    s, f = grp[i]
                    vr = f.get("vol_rel5", f.get("vol_rel"))
                    dv = f"<span style='color:{AMB}'>DIV!</span>" if f.get("diverg") == "distribucion oculta" else ("↑OBV" if f.get("obv_above") else "")
                    fm += (f"<td style='color:{col};font-weight:700'>{s}</td><td style='color:{col}'>{f['cmf']:+.2f}</td>"
                           f"<td style='color:{GRY}'>{(str(round(vr, 2)) + 'x') if vr is not None else '—'}</td><td style='font-size:10px'>{dv}</td>")
                else:
                    fm += "<td></td><td></td><td></td><td></td>"
            fm += "</tr>"
        fm += "</table><div style='font-size:10px;color:#666;margin-top:4px'>CMF 20s · umbral ±0.05 · DIV! = distribución oculta (precio sube, dinero sale)</div>"
        # --- SALUD DEL BUILD: todo lo que se degrado en esta ejecucion, a la vista (cambio 1 de la revision) ---
        try:
            if SALUD_BUILD:
                _sb = ("<table><tr style='color:#888;font-size:10px'><td>origen</td><td>aviso</td><td>veces</td></tr>")
                for _o, _t, _n in SALUD_BUILD[:40]:
                    _sb += (f"<tr><td style='color:{AMB};white-space:nowrap'>{esc(_o)}</td>"
                            f"<td style='color:#B9C9E2'>{esc(_t)}</td>"
                            f"<td style='color:{GRY}'>{('×' + str(_n)) if _n > 1 else ''}</td></tr>")
                _sb += ("</table><div style='font-size:10px;color:#666;margin-top:4px'>"
                        "Cada fila es un dato que NO llegó o se descartó por sospechoso. El terminal siguió funcionando, "
                        "pero estos huecos explican paneles ausentes o marcados. Detalle completo en rotacion.log junto al script. "
                        "Un build limpio no muestra este panel.</div>")
                html.append(_mod(f"🩺 SALUD DEL BUILD — {len(SALUD_BUILD)} AVISOS (LO QUE SE DEGRADÓ Y POR QUÉ)", _sb))
            _dg = _deg_resumen(25)
            if _dg:
                _tot = sum(x[1] for x in _dg)
                _db = ("<table><tr style='color:#888;font-size:10px'><td>funcion:linea</td>"
                       "<td>ultimo error</td><td>veces</td></tr>")
                for _o, _n, _e in _dg:
                    _db += (f"<tr><td style='color:{AMB};white-space:nowrap'>{esc(_o)}</td>"
                            f"<td style='color:#B9C9E2;font-size:10px'>{esc(_e)}</td>"
                            f"<td style='color:{GRY}'>×{_n}</td></tr>")
                _db += ("</table><div style='font-size:10px;color:#666;margin-top:4px'>"
                        "Calculos que fallaron y usaron un valor de reserva SIN avisar. No son errores del build: "
                        "son huecos que pueden explicar un numero raro. Si una fila crece de golpe respecto a otros dias, "
                        "revisa ese calculo antes de decidir el viernes.</div>")
                html.append(_mod(f"🔎 DEGRADACIONES SILENCIOSAS — {_tot} EN {len(_dg)} PUNTOS DE CALCULO", _db))
            if not SALUD_BUILD:
                html.append(_mod("🩺 SALUD DEL BUILD — LIMPIO",
                                 "<div style='color:" + GRN + ";font-size:12px'>✓ Sin incidencias: todas las fuentes respondieron y ningún dato fue descartado por los filtros de cordura.</div>"))
        except Exception:
            pass
        # --- ETFs CON HISTORIAL CORTO (v4.6) ------------------------------
        try:
            _nuevos = []
            for _ns in (SECTORS + THEMATIC + EXTRA):
                _hist_av = aviso_historial(_ns, df)
                if _hist_av:
                    _nuevos.append((_ns, semanas_de_historia(_ns, df)))
            if _nuevos:
                _nuevos.sort(key=lambda x: x[1])
                _nb = "<table><tr style='color:#888;font-size:10px'><td>ETF</td><td>semanas</td><td>qué SÍ vale</td></tr>"
                for _ns, _nn in _nuevos:
                    _hist_pc = int(round(100 * _nn / MIN_SEMANAS_FIABLE))
                    _nb += (f"<tr><td style='font-weight:700'>{esc(_ns)} "
                            f"<span style='color:{GRY};font-weight:400'>{esc(NAMES.get(_ns, ''))}</span></td>"
                            f"<td style='color:{AMB}'>{_nn}/{MIN_SEMANAS_FIABLE} ({_hist_pc}%)</td>"
                            f"<td style='color:{GRY};font-size:11px'>"
                            + ("CMF y volumen" if _nn >= 30 else "nada todavía (&lt;30 sesiones)")
                            + "</td></tr>")
                _nb += ("</table><div style='font-size:10px;color:#666;margin-top:6px'>"
                        "Estos fondos son demasiado nuevos para tener media de 40 semanas, así que "
                        "<b>su scoring sale incompleto por falta de datos, no por debilidad</b>: un 2/5 aquí "
                        "no significa lo mismo que un 2/5 de XLK. Tampoco tienen suelo que medir todavía "
                        "(solo han conocido una dirección), así que lo que diga de ellos el cockpit o el libro "
                        "de despertares es ruido hasta que corrijan por primera vez. "
                        "El CMF y el volumen sí son válidos a partir de 30 sesiones. "
                        "Se completan solos cada semana.</div>")
                html.append(_mod(f"⏳ HISTORIAL CORTO — {len(_nuevos)} ETF AÚN SIN MEDIA DE 40 SEMANAS", _nb))
        except Exception as _dege:
            _deg("panel_historial_corto", _dege)

        # --- DESPERTARES POR APUESTA INDEPENDIENTE (v4.5) -----------------
        try:
            _fam = (despertares or {}).get("familias") if isinstance(despertares, dict) else None
            _lib = (despertares or {}).get("libro") if isinstance(despertares, dict) else None
            if _fam:
                _fb = ""
                if _lib:
                    _fb += (f"<div style='color:{GRY};font-size:11px;margin-bottom:6px'>"
                            f"Contado por FICHAS: {_lib['n']} · acierto {_lib['p']}% "
                            f"(IC {_lib['lo']}–{_lib['hi']}%) · media {_lib['avg']:+.1f}%</div>")
                _fb += (f"<div style='font-size:26px;font-weight:800;color:"
                        f"{GRN if _fam['p'] >= 55 else AMB}'>{_fam['p']}%</div>"
                        f"<div style='color:{GRY};font-size:11px'>acierto sobre "
                        f"<b>{_fam['n_familias']} apuestas independientes</b> "
                        f"(no {_fam['n_filas']} fichas) · Wilson 95% "
                        f"<b>{_fam['lo']}–{_fam['hi']}%</b> · media {_fam['avg']:+.1f}%</div>")
                if not _fam["maduro"]:
                    _fb += (f"<div style='color:{AMB};font-size:11px;margin:6px 0'>"
                            f"MUESTRA NO MADURA: {_fam['n_familias']} apuestas. Hacen falta 12 para que "
                            f"el intervalo se estreche lo suficiente como para afirmar algo.</div>")
                _fb += (f"<div style='color:{AMB};font-size:11px;margin:6px 0'>"
                        f"CONCENTRACIÓN: el {_fam['concentracion']}% del resultado lo aporta una sola "
                        f"apuesta ({esc(_fam['top'])}). Si esa se hubiera girado, el libro entero cambia.</div>")
                _fb += ("<table><tr style='color:#888;font-size:10px'><td>apuesta</td>"
                        "<td>resultado</td><td>fichas que la componen</td></tr>")
                for _fam_fila in _fam["filas"]:
                    _fb += (f"<tr><td style='font-weight:700'>{esc(_fam_fila['familia'])}</td>"
                            f"<td style='color:{GRN if _fam_fila['ret']>0 else RED};font-weight:700'>{_fam_fila['ret']:+.1f}%</td>"
                            f"<td style='color:{GRY};font-size:11px'>{esc(', '.join(_fam_fila['syms']))}</td></tr>")
                _fb += "</table>"
                _fb += ("<div style='font-size:10px;color:#666;margin-top:8px'>"
                        "<b>Por qué se cuenta así.</b> GDX, GLD, SIL, SLV y XME no son cinco aciertos: "
                        "son <b>la misma apuesta</b> (metales) expresada cinco veces. Se mueven juntos, y si "
                        "el oro se gira caen los cinco a la vez. Contar fichas en vez de apuestas infla la N, "
                        "estrecha el intervalo y te hace creer que sabes algo que todavía no sabes. "
                        "El número de arriba es más feo que el de fichas: <b>ese es el punto</b>. "
                        "Si esto se vende algún día, es el número que aguanta que lo miren de cerca.</div>")
                html.append(_mod("LIBRO DE DESPERTARES — CONTADO POR APUESTAS, NO POR FICHAS", _fb))
        except Exception as _dege:
            _deg("panel_familias", _dege)

        # --- AMPLITUD ESTILO McCLELLAN (v4.4) -----------------------------
        try:
            if mcc and mcc.get("osc") is not None:
                _mc_o = mcc["ultimo"]
                _mc_u = MCC_UMBRAL
                _mc_up = mcc.get("umbral_pct")
                _mc_col = RED if _mc_o < _mc_u else (AMB if _mc_o < 0 else GRN)
                _mc_est = ("bajo el umbral — amplitud castigada" if _mc_o < _mc_u
                        else "por encima del umbral" if _mc_o > 0 else "negativo pero sobre el umbral")
                # ¿esta armada la senal ahora mismo?
                _mc_ser = mcc["osc"]
                _arm, _mc_seg = False, 0
                for _mc_v in _mc_ser.iloc[-40:]:
                    if _mc_v < _mc_u:
                        _arm, _mc_seg = True, 0
                    elif _arm:
                        _mc_seg += 1
                _mc_aviso = ""
                if _arm and 0 < _mc_seg < MCC_CONFIRMACIONES:
                    _mc_aviso = (f"<div style='color:{AMB};margin:6px 0'>SEÑAL ARMÁNDOSE: "
                              f"{_mc_seg} de {MCC_CONFIRMACIONES} cierres por encima de {_mc_u:.0f}. "
                              f"Falta{'n' if MCC_CONFIRMACIONES - _mc_seg > 1 else ''} "
                              f"{MCC_CONFIRMACIONES - _mc_seg}.</div>")
                elif _arm and _mc_seg >= MCC_CONFIRMACIONES:
                    _mc_aviso = (f"<div style='color:{GRN};margin:6px 0'>SEÑAL COMPLETADA: "
                              f"{_mc_seg} cierres por encima de {_mc_u:.0f} tras caer por debajo.</div>")
                _mc_sp = _spark(list(_mc_ser.iloc[-60:]), w=260, h=34)
                _mc_b = (f"<div style='font-size:30px;font-weight:800;color:{_mc_col}'>{_mc_o:+.1f}</div>"
                      f"<div style='color:{GRY};font-size:11px'>{esc(_mc_est)} · "
                      f"{mcc['n_acciones']} acciones · {mcc['n_sesiones']} sesiones · "
                      f"hoy {mcc['adv']} suben / {mcc['dec']} bajan</div>{_mc_sp}{_mc_aviso}")
                # tabla de backtest
                for _mc_k, _mc_tit in (("bt_nyse", f"umbral {_mc_u:.0f} (el clásico del NYSE)"),
                                 ("bt_pct", f"umbral {_mc_up} (equivalente por percentil en ESTA serie)")):
                    _mc_bt = mcc.get(_mc_k)
                    if not _mc_bt or not _mc_bt.get("filas"):
                        continue
                    _mc_b += (f"<div style='margin-top:10px;color:{CYN};font-size:11px'>{esc(_mc_tit)} — "
                           f"{_mc_bt['n_disparos']} disparos históricos</div>")
                    if _mc_bt["n_disparos"] < 10:
                        _mc_b += (f"<div style='color:{AMB};font-size:10px'>Muestra muy corta "
                               f"(N={_mc_bt['n_disparos']}): los porcentajes de abajo no distinguen "
                               f"nada todavía. Mira el intervalo, no el número central.</div>")
                    _mc_b += ("<table><tr style='color:#888;font-size:10px'><td>horizonte</td>"
                           "<td>veces en positivo</td><td>Wilson 95%</td><td>N</td>"
                           "<td>media</td><td>peor</td></tr>")
                    for _mc_f in _mc_bt["filas"]:
                        if not _mc_f.get("n"):
                            _mc_b += (f"<tr><td>T+{_mc_f['h']}</td><td colspan='5' style='color:{GRY}'>"
                                   f"sin casos con recorrido suficiente</td></tr>")
                            continue
                        _mc_b += (f"<tr><td>T+{_mc_f['h']}</td>"
                               f"<td style='font-weight:700'>{_mc_f['pos']}%</td>"
                               f"<td style='color:{GRY};font-size:11px'>{_mc_f['lo']}–{_mc_f['hi']}%</td>"
                               f"<td style='color:{GRY}'>{_mc_f['n']}</td>"
                               f"<td style='color:{GRN if _mc_f['media']>0 else RED}'>{_mc_f['media']:+.2f}%</td>"
                               f"<td style='color:{RED};font-size:11px'>{_mc_f['peor']:+.2f}%</td></tr>")
                    _mc_b += "</table>"
                _mc_b += ("<div style='font-size:10px;color:#666;margin-top:8px'>"
                       "<b>Esto NO es el McClellan del NYSE (NYMO).</b> El NYMO usa los avances y "
                       "descensos de los ~2.800 títulos del NYSE, un dato que Yahoo, Stooq y FRED no "
                       "publican. Aquí se aplica la <b>misma fórmula</b> (RANA ajustado por ratio, "
                       "EMA 19 menos EMA 39) al universo que el terminal ya descarga: el S&amp;P 500. "
                       "Son grandes valores; el NYSE incluye small caps, ADRs y fondos, que se mueven "
                       "distinto. <b>Por eso el umbral −100 no se traslada tal cual</b>, y por eso "
                       "verás arriba el equivalente calculado por percentil sobre esta misma serie. "
                       "Los porcentajes son <b>frecuencia histórica observada, no predicción</b>. "
                       "Es contexto: la decisión sigue siendo del cierre del viernes.</div>")
                html.append(_mod("AMPLITUD ESTILO McCLELLAN — ¿CUÁNTAS ACCIONES ACOMPAÑAN?", _mc_b))
        except Exception as _dege:
            _deg("panel_mcclellan", _dege)
            _avisar("mcclellan", f"panel no generado: {_dege}")

        # --- FLOW SCORE + CONFIDENCE SCORE (v4.2) -------------------------
        try:
            _mc_dias = None
            try:
                _mc_dias = int((pd.Timestamp.today().normalize() - df.index[-1].normalize()).days)
            except Exception as _dege:
                _deg("panel_scores:dias", _dege)
            _mc_srow = {r["sym"]: r for r in (scores or [])}
            _mc_fils = []
            for _mc_sy in (SECTORS + THEMATIC + EXTRA):
                _mc_fs = compute_flow_score(_mc_sy, flow)
                if _mc_fs is None:
                    continue
                _mc_cf = compute_confidence(_mc_sy, df, flow, _mc_srow.get(_mc_sy), _mc_dias)
                _mc_fils.append((_mc_sy, _mc_fs, _mc_cf))
            if _mc_fils:
                _mc_fils.sort(key=lambda x: -x[1]["score"])
                _mc_cols = {"ALTA": GRN, "MEDIA": AMB, "BAJA": "#C98A3A", "INSUFICIENTE": "#8A5A5A"}
                _mc_t = ("<table><tr style='color:#888;font-size:10px'><td>ETF</td><td>FLOW 0-100</td>"
                      "<td>CMF</td><td>CONFIANZA EN EL DATO</td><td>barras</td></tr>")
                for _mc_sy, _mc_fs, _mc_cf in _mc_fils[:30]:
                    _mc_v = _mc_fs["score"]
                    _mc_fc = GRN if _mc_v >= 65 else (AMB if _mc_v >= 40 else RED)
                    _mc_cc = _mc_cols.get(_mc_cf["etiqueta"], GRY)
                    _mc_cmf = ((flow.get(_mc_sy) or {}).get("cmf"))
                    _mc_t += (f"<tr><td style='font-weight:700'>{esc(_mc_sy)}</td>"
                           f"<td style='color:{_mc_fc};font-weight:700'>{_mc_v}</td>"
                           f"<td style='color:{GRY};font-size:11px'>{_mc_cmf:+.2f}</td>"
                           f"<td style='color:{_mc_cc}'>{_mc_cf['score']} · {_mc_cf['etiqueta']}</td>"
                           f"<td style='color:{GRY};font-size:11px'>{_mc_cf['n']}</td></tr>")
                _mc_t += ("</table><div style='font-size:10px;color:#666;margin-top:6px'>"
                       "<b>FLOW SCORE</b> no es informacion nueva: es el mismo CMF/OBV/divergencia/volumen "
                       "que ya ves en los otros paneles, resumido en una cifra para poder ordenar. "
                       "<b>CONFIANZA</b> mide <b>calidad del dato</b>, NO probabilidad de acierto: cuantas barras "
                       "hay detras (30), cuanto coinciden entre si las 5 senales del scoring (25), si el dato esta "
                       "completo y sin fallos silenciosos (25) y si el cierre es reciente (20). "
                       "Un ETF con confianza ALTA puede caer perfectamente: significa que la lectura era limpia, "
                       "no que acertara. Aqui NO hay ningun motor de probabilidades, y es a proposito: con ~70 "
                       "semanas de muestra cualquier porcentaje de acierto seria ruido con decimales. "
                       "El flujo sigue confirmando los viernes.</div>")
                html.append(_mod("FLOW SCORE + CONFIANZA EN EL DATO", _mc_t))
        except Exception as _dege:
            _deg("panel_flow_confidence", _dege)
            _avisar("scores", f"panel Flow/Confianza no generado: {_dege}")
        html.append(_mod("FLOW MONITOR — DÓNDE ENTRA Y SALE EL DINERO", fm))
        # --- MODULO OPTIONS DESK: put/call, IV percentil, skew, max pain y DIVERGENCIA con el CMF ---
        if options:
            _vparc = any(o.get("vol_parcial") for o in options.values())
            _nexp = next((o.get("n_exp_pcr") for o in options.values() if o.get("n_exp_pcr")), None)
            _dte_ej = next((o.get("dte_iv") for o in options.values() if o.get("dte_iv") is not None), None)
            # ¿el interes abierto tampoco esta poblado? (Yahoo suele NO dar OI antes de la apertura USA)
            _oi_vacio = sum(1 for o in options.values() if o.get("pcr_oi") is not None) < max(3, len(options) // 5)
            _ordit = sorted(options.items(), key=lambda kv: (kv[1].get("diverg") is None, -(kv[1].get("pcr_vol") or 0)))
            _banner = ""
            if _vparc and _oi_vacio:
                _banner = (f"<div style='background:{AMB}22;border:1px solid {AMB}66;border-radius:6px;padding:6px 9px;"
                           f"margin-bottom:6px;font-size:11px;color:{AMB}'>⚠ Build lanzado con la bolsa USA CERRADA (pre-market): "
                           "a esta hora Yahoo casi no da datos de opciones fiables — ni volumen (P/C vol) ni interés abierto (P/C OI) ni "
                           "IV limpia. Por eso ves muchos «—»: <b>no es un fallo, es que el dato no existe todavía</b>. El resto del terminal "
                           "(RRG, scoring, flujo, régimen) va perfecto. <b>Para que el panel de opciones sirva, lanza el build tras el cierre USA "
                           "(a partir de las ~22:15 hora de España).</b></div>")
            elif _vparc:
                _banner = (f"<div style='background:{AMB}22;border:1px solid {AMB}66;border-radius:6px;padding:6px 9px;"
                           f"margin-bottom:6px;font-size:11px;color:{AMB}'>⚠ Build con la sesión de EE.UU. abierta: "
                           "el volumen de opciones va a medio llenar, así que la liquidez y las señales se calculan por "
                           "<b>interés abierto (P/C OI)</b>, que es estable; el <b>P/C vol sale «n/d» a propósito</b>. "
                           "Para el put/call de volumen completo, el build del cierre.</div>")
            od = (_banner + "<table><tr style='color:#888;font-size:10px'><td>ETF</td><td>P/C vol</td><td>P/C OI</td>"
                  "<td>IV</td><td>IV pct</td><td>skew</td><td>max pain</td><td>señal</td></tr>")
            for _s, _o in _ordit:
                _pcr = _o.get("pcr_vol")
                _pcc = RED if (_pcr and _pcr > 1.3) else (GRN if (_pcr and _pcr < 0.7) else GRY)
                _pcr_txt = ("n/d" if (_pcr is None and _o.get("vol_parcial")) else (_pcr if _pcr is not None else "—"))
                _ivp = _o.get("iv_rank") if _o.get("iv_rank") is not None else _o.get("iv_pct")
                _ivpc = RED if (_ivp is not None and _ivp >= 80) else (GRN if (_ivp is not None and _ivp <= 20) else GRY)
                _sk = _o.get("skew")
                _skc = RED if (_sk is not None and _sk > 6) else (CYN if (_sk is not None and _sk < 0) else GRY)
                _mp = _o.get("mp_dist")
                _mptxt = (f"{_o['maxpain']:g} ({_mp:+.1f}%)" if _o.get("maxpain") and _mp is not None else "—")
                _dv = _o.get("diverg")
                _dvtxt = (f"<span style='color:{AMB}'>⚠ {esc(_dv[:38])}</span>" if _dv else "")
                _pxl = _o.get("proxy")
                if _pxl:
                    _dvtxt = f"<span style='color:{CYN};font-size:9px'>vía {esc(_pxl)}</span> " + _dvtxt
                od += (f"<tr><td><b style='color:{CYN}'>{_s}</b></td>"
                       f"<td style='color:{_pcc}'>{_pcr_txt}</td>"
                       f"<td style='color:{GRY}'>{_o.get('pcr_oi') if _o.get('pcr_oi') is not None else '—'}</td>"
                       f"<td style='color:{GRY}'>{(str(_o['iv']) + '%') if _o.get('iv') is not None else '—'}</td>"
                       f"<td style='color:{_ivpc}'>{(str(_ivp)) if _ivp is not None else '—'}</td>"
                       f"<td style='color:{_skc}'>{(f'{_sk:+.1f}') if _sk is not None else '—'}</td>"
                       f"<td style='color:{GRY};font-size:10px'>{_mptxt}</td>"
                       f"<td style='font-size:10px'>{_dvtxt}</td></tr>")
            od += ("</table><div style='font-size:10px;color:#666;margin-top:4px'>"
                   "Opciones de Yahoo (gratis). "
                   + (f"P/C agrega los {_nexp} vencimientos más próximos (como el put/call «de portada» que ves en las webs); "
                      if _nexp and _nexp > 1 else "")
                   + (f"IV medida al vencimiento más cercano a ~30 días ({_dte_ej}d en este build) para que el rank compare siempre el mismo plazo. "
                      if _dte_ej is not None else "")
                   + "P/C&gt;1.3 = miedo/protección (rojo); &lt;0.7 = codicia (verde). "
                   "IV pct = rank contra su PROPIA historia de IV cuando hay &ge;10 registros guardados del MISMO plazo/modo (options_iv.json); mientras se llena, aproximación vs vol realizada — "
                   "ojo: el seguro casi SIEMPRE cotiza con prima sobre el movimiento real, así que en modo aproximado solo los extremos (&ge;97) significan algo. "
                   "El P/C OI (interés abierto) es T-1 y estable a cualquier hora; el P/C vol necesita el cierre para estar completo. "
                   "Si una IV sale «—» es que Yahoo dio un valor por strike no plausible (fuera de rango vs la volatilidad realizada del ETF) y se descarta para no ensuciar el rank. "
                   "skew&gt;6 = pagan por protección a la baja. max pain = imán de precio al vencimiento (se calcula solo sobre el vencimiento más cercano; útil el 3er viernes). "
                   "⚠ = DIVERGENCIA con el CMF: el flujo dice una cosa y las opciones otra — tu confirmación por segunda vía. "
                   "Liquidez fiable solo en ETFs USA; sirven de señal aunque operes los UCITS.</div>")
            html.append(_mod("OPTIONS DESK — POSICIONAMIENTO EN DERIVADOS · DIVERGENCIA vs FLUJO", od))
        # --- MODULO 3: ROTATION READOUT (RRG) ---
        _qcount = {"leading": [], "improving": [], "weakening": [], "lagging": []}
        _movers = []
        for s, d in rrg.items():
            if s == BENCH:
                continue
            if d["quad"] in _qcount:
                _qcount[d["quad"]].append(s)
            tail = d.get("tail") or []
            if len(tail) >= 4:
                _movers.append((s, tail[-1][1] - tail[-4][1]))
        _movers.sort(key=lambda x: -x[1])
        _qlbl = {"leading": ("LÍDER", GRN), "improving": ("MEJORANDO", CYN), "weakening": ("DEBILITÁNDOSE", AMB), "lagging": ("REZAGADO", RED)}
        rr = "<table><tr><th>CUADRANTE</th><th>N</th><th style='text-align:left'>MIEMBROS</th></tr>"
        for q in ("leading", "improving", "weakening", "lagging"):
            lbl, col = _qlbl[q]
            mem = " ".join(_qcount[q][:11]) + ("…" if len(_qcount[q]) > 11 else "")
            rr += f"<tr><td style='color:{col};font-weight:700'>{lbl}</td><td>{len(_qcount[q])}</td><td style='text-align:left;color:#BFC7D5;font-size:10.5px'>{mem}</td></tr>"
        rr += "</table>"
        up5 = " · ".join(f"<span style='color:{GRN}'>{s} +{v:.1f}</span>" for s, v in _movers[:5])
        dn5 = " · ".join(f"<span style='color:{RED}'>{s} {v:.1f}</span>" for s, v in _movers[-5:][::-1])
        rr += (f"<div style='margin-top:6px;font-size:11px'><span style='color:{GRY}'>IMPULSO 3S ▲</span> {up5}<br>"
               f"<span style='color:{GRY}'>IMPULSO 3S ▼</span> {dn5}</div>")
        html.append(_mod("ROTATION READOUT — RRG EN TEXTO", rr))
        # --- MODULO 4: SCORE BOARD ---
        sb = "<table><tr><th>RK</th><th style='text-align:left'>ETF</th><th>SCORE</th><th>SEÑALES</th><th>CMF</th><th>Q</th></tr>"
        _ss = sorted(scores or [], key=lambda r: -r["score"])
        for i, r in enumerate(_ss[:10], 1):
            dots = "".join("●" if v else "○" for _, v in r["parts"])
            cmf = (flow or {}).get(r["sym"], {}).get("cmf")
            q = rrg.get(r["sym"], {}).get("quad", "")
            qc = _qlbl.get(q, ("—", GRY))
            di = f" <span style='color:{RED}'>✕DIV</span>" if r.get("distrib") else ""
            sb += (f"<tr><td style='color:{GRY}'>{i:02d}</td><td style='text-align:left;color:{AMB};font-weight:700'>{r['sym']}{di}</td>"
                   f"<td>{r['score']}/5</td><td style='letter-spacing:2px;color:{GRN}'>{dots}</td>"
                   f"<td style='color:{GRN if (cmf or 0) > 0 else RED}'>{(f'{cmf:+.2f}' if cmf is not None else '—')}</td>"
                   f"<td style='color:{qc[1]};font-size:10px'>{qc[0][:4]}</td></tr>")
        sb += "</table><div style='font-size:10px;color:#666;margin-top:4px'>● tendencia · fuerza · impulso · flujo · amplitud — ✕DIV excluido por distribución oculta</div>"
        html.append(_mod("SCORE BOARD — RANKING DEL SISTEMA", sb))
        # --- MODULO 5: SENTIMENT & INTERNALS ---
        si = ""
        if fg_idx:
            try:
                _fgv = float(fg_idx["score"])
                fgc = RED if _fgv <= 25 else AMB if _fgv <= 45 else GRN if _fgv < 75 else AMB
                bar_n = max(0, min(20, int(round(_fgv / 5))))
                si += (f"<div>FEAR &amp; GREED <span style='color:{fgc};font-weight:700'>{_fgv:.0f}</span> "
                       f"<span style='color:{fgc}'>{'█' * bar_n}</span><span style='color:#222'>{'█' * (20 - bar_n)}</span> "
                       f"<span style='color:{GRY};font-size:10px'>{esc(str(fg_idx.get('rating', '')))} · 1s:{fg_idx.get('week', '—')} 1m:{fg_idx.get('month', '—')} 1a:{fg_idx.get('year', '—')}</span></div>")
            except Exception:
                pass
        if isinstance(risk, dict):
            si += f"<div>RISK APPETITE <span style='color:{AMB};font-weight:700'>{esc(str(risk.get('label', '—')))}</span> <span style='color:{GRY}'>({float(risk.get('score', 0)):+.0f})</span></div>"
        si += f"<div>RÉGIMEN <span style='color:{AMB}'>{esc(reg_short)}</span> · SEMÁFORO <span style='color:{light};font-weight:700'>{esc(sem_short)}</span></div>"
        if dd is not None:
            try:
                si += f"<div>SPY vs MÁXIMO <span style='color:{RED if dd <= -3 else GRY}'>{dd:+.1f}%</span> · escalones plan: −5/−10/−20</div>"
            except Exception:
                pass
        if spy_flow:
            _sc = spy_flow.get("cmf")
            _so = spy_flow.get("obv_above")
            _sc_col = GRN if (_sc or 0) > 0 else RED
            _sc_val = _sc if _sc is not None else 0
            _obv_txt = ("<span style=" + '"' + "color:" + GRN + '"' + ">" + '↑' + " sobre media</span>") if _so else ("<span style=" + '"' + "color:" + RED + '"' + ">" + '↓' + " bajo media</span>")
            si += (f"<div>SPY FLOW CMF <span style='color:{_sc_col}'>{_sc_val:+.2f}</span>"
                   f" · OBV {_obv_txt}"
                   + (f" · <span style='color:{AMB}'>DISTRIBUCIÓN</span>" if spy_flow.get("diverg") == "distribucion oculta" else "") + "</div>")
        _nlead = len(_qcount["leading"]) + len(_qcount["improving"])
        _ntot = sum(len(v) for v in _qcount.values()) or 1
        si += f"<div>AMPLITUD RRG <span style='color:{GRN if _nlead / _ntot >= .5 else AMB}'>{_nlead}/{_ntot}</span> en Líder+Mejorando ({100 * _nlead / _ntot:.0f}%)</div>"
        html.append(_mod("SENTIMENT & INTERNALS", si))
        # --- MODULO 6: PORTFOLIO DESK ---
        if apal:
            pd_ = (f"<div>EQUITY <span style='color:{AMB};font-weight:700'>{apal['tot_eur']:,.0f} €</span>"
                   f" · EXPOSICIÓN {apal['tot_expo']:,.0f} €"
                   f" · LEV <span style='color:{RED if apal['lev_ef'] >= 1.6 else AMB}'>{apal['lev_ef']:.2f}x</span></div>").replace(",", ".")
            pd_ += "<table><tr><th style='text-align:left'>BROKER</th><th>EQ €</th><th>LEV</th><th>S&P−5%</th><th>ESTADO</th></tr>"
            for b in apal["brokers"]:
                e5 = b["esc"].get(-5) or {}
                st5 = e5.get("estado", "ok")
                stc = RED if st5 not in ("ok",) else GRN
                pd_ += (f"<tr><td style='text-align:left;color:{AMB}'>{esc(b['broker'])}</td>"
                        f"<td>{b['equity']:,.0f}</td><td>{b['lev_ef']:.2f}x</td>"
                        f"<td style='color:{RED}'>{e5.get('loss', 0):+,.0f}</td>"
                        f"<td style='color:{stc};font-size:10px'>{esc(st5.upper())}</td></tr>").replace(",", ".")
            pd_ += "</table>"
            if mi_plan and mi_plan.get("rows"):
                _vnd = [r for r in mi_plan["rows"] if str(r.get("act", "")).upper().startswith("VENDER")]
                _veur = sum(r["eur"] for r in _vnd if isinstance(r.get("eur"), (int, float)))
                _mnt = [r for r in mi_plan["rows"] if r.get("act") == "MANTENER"]
                _meur = sum(r["eur"] for r in _mnt if isinstance(r.get("eur"), (int, float)))
                _tot = mi_plan.get("total") or 1
                pd_ += (f"<div style='margin-top:4px'>ALINEACIÓN <span style='color:{GRN}'>{100 * _meur / _tot:.0f}% mantener</span> · "
                        f"<span style='color:{RED}'>{len(_vnd)} pos en señal de salida (~{_veur:,.0f} €)</span></div>").replace(",", ".")
            _top = sorted(apal["rows"], key=lambda r: -r["expo"])[:6]
            pd_ += ("<div style='font-size:10.5px;color:#BFC7D5;margin-top:2px'>TOP EXPO: "
                    + " · ".join(f"{r['tk']} {r['expo']:,.0f}€".replace(",", ".") for r in _top) + "</div>")
            html.append(_mod("PORTFOLIO DESK — LOS 3 BROKERS", pd_))
        # --- MODULO 6b: MESAS DE PÓKER — semis, materiales y espacio (rebote desk genérico) ---
        for dk in (desks or []):
            if not dk:
                continue
            _cfg = next((c for c in DESKS_POKER if c["id"] == dk.get("id")), None) or DESKS_POKER[0]
            _card = lambda k, v, c="#D8DEE9": (f"<span style='display:inline-block;background:#101010;border:1px solid #333;"
                                               f"border-radius:5px;padding:4px 8px;margin:2px 3px 2px 0;font-size:10.5px'>"
                                               f"<span style='color:#777'>{k}</span> <b style='color:{c}'>{v}</b></span>")
            sd = ""
            # LA MANO
            _qs = {"leading": ("LÍDER", GRN), "improving": ("MEJORANDO", CYN), "weakening": ("DEBILITÁNDOSE", AMB), "lagging": ("REZAGADO", RED)}
            _q = _qs.get(dk.get("quad"), ("—", GRY))
            sd += "<div style='color:#777;font-size:10px;letter-spacing:1px;margin-bottom:3px'>LA MANO (estado actual)</div><div>"
            sd += _card("cuadrante", _q[0], _q[1])
            if dk.get("score") is not None:
                sd += _card("score", f"{dk['score']}/5", GRN if dk["score"] >= 4 else AMB if dk["score"] >= 3 else RED)
            sd += _card("vs máx 52s", f"{dk['dd52']:+.0f}%", RED if dk["dd52"] <= -10 else GRY)
            sd += _card("z 4 sem", f"{dk['z4']:+.1f}", RED if dk["z4"] <= -1.5 else GRY)
            if dk.get("vs40") is not None:
                sd += _card("vs media 40s", f"{dk['vs40']:+.1f}%", GRN if dk["vs40"] > 0 else RED)
            _cmf = dk.get("cmf")
            if _cmf is not None:
                sd += _card("CMF", f"{_cmf:+.2f}", GRN if _cmf > 0.05 else RED if _cmf < -0.05 else GRY)
            if dk.get("streak"):
                sd += _card("racha", f"{dk['streak']} sem rojas", AMB)
            if dk.get("wash") is not None:
                sd += _card("washout comp.", f"{dk['wash']}%", AMB if dk["wash"] >= 50 else GRY)
            if dk.get("giro"):
                _gg = dk["giro"]
                sd += _card("giro intradía", "compraron el miedo" if _gg["sig"] == "alcista" else "vendieron la subida",
                            GRN if _gg["sig"] == "alcista" else RED)
            if dk.get("distrib"):
                sd += _card("⚠", "DISTRIBUCIÓN OCULTA", RED)
            sd += "</div>"
            # REBOTE SCORE
            _pc = GRN if dk["pts"] >= 8 else AMB if dk["pts"] >= 5 else GRY
            _verd = ("MANO FUERTE — setup de rebote sobre la mesa" if dk["pts"] >= 8 else
                     "proyecto de mano — faltan cartas" if dk["pts"] >= 5 else
                     "no hay mano — no fuerces la entrada")
            _bar = int(round(dk["pts"] / 10 * 20))
            sd += (f"<div style='margin:8px 0'>REBOTE SCORE <b style='color:{_pc};font-size:15px'>{dk['pts']}</b>"
                   f"<span style='color:#555;font-size:10px'>/10</span> "
                   f"<span style='color:{_pc}'>{'█' * _bar}</span><span style='color:#1c1c1c'>{'█' * (20 - _bar)}</span> "
                   f"<span style='color:{_pc};font-size:11px'>{_verd}</span></div>")
            if dk.get("det"):
                sd += f"<div style='font-size:10.5px;color:#9AA7B8;margin-bottom:8px'>{esc(' · '.join(dk['det']))}</div>"
            # LA MESA
            if dk.get("tbl"):
                sd += ("<div style='color:#777;font-size:10px;letter-spacing:1px;margin:6px 0 3px'>LA MESA — % de veces que estaba MÁS ARRIBA 4 semanas después "
                       f"(histórico propio, {dk['n_hist']} sem)</div>")
                sd += "<table><tr><th style='text-align:left'>CAÍDA DESDE MÁX</th><th>PROB.</th><th>IC 95%</th><th>MEDIA 4S</th><th>N</th></tr>"
                for t in dk["tbl"]:
                    mark = f" <b style='color:{AMB}'>◄ AHORA</b>" if t["now"] else ""
                    _tc = GRN if t["p"] >= 60 else AMB if t["p"] >= 50 else RED
                    sd += (f"<tr><td style='text-align:left'>{t['lbl']}{mark}</td>"
                           f"<td style='color:{_tc};font-weight:700'>{t['p']}%</td>"
                           f"<td style='color:#667'>{t['lo']}–{t['hi']}%</td>"
                           f"<td>{_fp(t['avg'])}</td><td style='color:#667'>{t['n']}</td></tr>")
                sd += "</table>"
            if dk.get("zview"):
                zv = dk["zview"]
                _zn = f" <b style='color:{AMB}'>◄ AHORA</b>" if zv["now"] else ""
                sd += (f"<div style='font-size:11px;margin-top:4px'>SOBREVENTA (z≤−1.5){_zn}: rebotó el "
                       f"<b style='color:{GRN if zv['p'] >= 60 else AMB}'>{zv['p']}%</b> "
                       f"<span style='color:#667'>(IC {zv['lo']}–{zv['hi']}%, n={zv['n']})</span> · media {_fp(zv['avg'])}</div>")
            # EL BOTE
            if dk.get("ev"):
                e = dk["ev"]
                sd += (f"<div style='margin-top:6px;font-size:11px'>EL BOTE: en el cubo actual, prob. {e['p']}% y media {e['avg']:+.1f}% a 4 sem → "
                       f"tamaño orientativo ¼-Kelly ≈ <b style='color:{CYN}'>{min(e['kelly4'], 3.0):.1f}%</b> de cartera (tope 3%), "
                       "en <b>contado</b>, nunca promediando el corto.</div>")
            # --- ANÁLOGOS DE FLUJO: cuando la condicion "cae + sale dinero N sesiones seguidas" ya paso
            #     antes, ¿que hizo el precio despues? Contexto, no señal (el flujo sigue confirmando el viernes).
            an = dk.get("analogos")
            if an and an.get("filas"):
                _act = (f"<b style='color:{AMB}'>◄ ACTIVA HOY</b> (racha {an['racha_hoy']} sesiones, CMF {an['cmf_hoy']:+.3f})"
                        if an.get("activa") else
                        f"<span style='color:#667'>no activa hoy · última vez {an.get('ultima') or '—'}</span>")
                sd += (f"<div style='color:#777;font-size:10px;letter-spacing:1px;margin:8px 0 3px'>ANÁLOGOS DE FLUJO — "
                       f"{dk['sym']} CAE + sale dinero de {an['flujo']} ×{an['n_ses']} sesiones seguidas · {an['casos']} casos · {_act}</div>"
                       "<table style='width:100%;font-size:11px'><tr style='color:#777'><td>DESPUÉS</td><td class='r'>SUBIÓ</td>"
                       "<td class='r'>IC 95%</td><td class='r'>MEDIA</td><td class='r'>MEDIANA</td><td class='r'>N</td></tr>")
                for f in an["filas"]:
                    _c = GRN if f["p"] >= 60 else (RED if f["p"] <= 40 else AMB)
                    sd += (f"<tr><td>T+{f['h']}</td><td class='r' style='color:{_c}'><b>{f['p']}%</b></td>"
                           f"<td class='r' style='color:#667'>{f['lo']}–{f['hi']}%</td>"
                           f"<td class='r'>{_fp(f['avg'])}</td><td class='r'>{_fp(f['med'])}</td>"
                           f"<td class='r' style='color:#667'>{f['n']}</td></tr>")
                sd += ("</table><div style='font-size:10px;color:#666;margin-top:3px'>Frecuencia histórica sobre TU serie, "
                       "<b>no una predicción</b>: mira el IC y la N antes que el % central. El flujo se mide con el CMF "
                       "(dice «sale dinero», <b>no</b> «vendió el minorista»: ese dato es de pago y no lo tenemos). "
                       "Es contexto para entender el momento, no un disparador — la ejecución la sigue mandando el cierre del viernes.</div>")
            sd += ("<div style='font-size:10px;color:#666;margin-top:8px'>REGLAS DE LA PARTIDA: ① " + _cfg["veh"] + ". "
                   "② La mesa son frecuencias in-sample con IC ancho, no una promesa. ③ Mano fuerte sin flujo (CMF sangrando) = proyecto, no mano: espera el cierre semanal. "
                   "④ " + _cfg["riesgo"] + ".</div>")
            html.append(_mod(f"{_cfg['emoji']} {_cfg['titulo']} — PÓKER DE REBOTE ({dk['sym']})", sd))
        # --- MODULO 6c: CENTINELA — el reloj de régimen en formato de mesa ---
        if centinela:
            cn = centinela
            _flbl2 = {"DISTRIBUCION": "DISTRIBUCIÓN", "TRANSICION": "TRANSICIÓN"}
            _ccol = {"RISK-ON": GRN, "DISTRIBUCION": AMB, "LIQUIDEZ": RED, "ACECHO": CYN, "REENTRADA": GRN, "TRANSICION": GRY}.get(cn["estado"], GRY)
            cd = (f"<div style='font-size:16px;font-weight:800;letter-spacing:2px;color:{_ccol};margin-bottom:4px'>{_flbl2.get(cn['estado'], cn['estado'])}"
                  + ("  <span style='font-size:10px;color:" + GRN + "'>✓ CONFIRMADO</span>" if cn["confirmado"]
                     else "  <span style='font-size:10px;color:" + AMB + "'>⧗ SIN CONFIRMAR (1 cierre)</span>") + "</div>")
            cd += (f"<div>SPREAD BETA−DEF <b style='color:{GRN if cn['spread'] > 0 else RED}'>{cn['spread']:+.2f}</b>"
                   f" · Δ3S <b style='color:{GRN if cn['d3'] >= 0 else RED}'>{cn['d3']:+.2f}</b>"
                   f" · {cn['lado']} sem mismo lado</div>")
            if cn.get("cmf_beta") is not None:
                cd += (f"<div>CMF EXPLOSIVOS <b style='color:{GRN if cn['cmf_beta'] > 0 else RED}'>{cn['cmf_beta']:+.2f}</b>"
                       + (f" · {cn['beta_pos']}% en positivo" if cn.get("beta_pos") is not None else "") + "</div>")
            if cn.get("hyg_tlt") is not None:
                cd += f"<div>CRÉDITO HYG/TLT 4S <b style='color:{GRN if cn['hyg_tlt'] > 0 else RED}'>{cn['hyg_tlt']:+.1f}%</b></div>"
            if dix:
                cd += (f"<div>DIX DARK POOLS <b style='color:{GRN if cn.get('dix_fuerte') else GRY}'>{dix['m5']}%</b>"
                       f" <span style='color:#667'>p{dix['pct']}</span>"
                       + (f" · GEX {dix['gex']:,.0f}".replace(",", ".") if dix.get("gex") is not None else "") + "</div>")
            if cn.get("acecho"):
                cd += f"<div style='color:{CYN}'>PRE-DESPERTAR: {', '.join(cn['acecho'][:6])}</div>"
            if cn.get("despierta"):
                cd += f"<div style='color:{GRN}'>DESPERTANDO: {', '.join(cn['despierta'][:6])}</div>"
            cd += f"<div style='font-size:10px;color:#888;margin-top:5px'>{esc(cn['que'][:220])}{'…' if len(cn['que']) > 220 else ''}</div>"
            cd += f"<div style='font-size:9.5px;color:{AMB};margin-top:3px'>INVALIDACIÓN: {esc(cn['inval'][:160])}{'…' if len(cn['inval']) > 160 else ''}</div>"
            html.append(_mod("🛰️ CENTINELA — RELOJ DE RÉGIMEN", cd))
        # --- MODULO 7: SIGNALS WIRE (cable de señales, con memoria entre sesiones) ---
        wire = []
        def _wadd(col, tag, txt, sym=None, dr=0):
            wire.append({"col": col, "tag": tag, "txt": txt, "sym": sym, "dir": dr})
        for dk in (desks or []):
            if dk and dk.get("pts", 0) >= 8:
                _cfgw = next((c for c in DESKS_POKER if c["id"] == dk.get("id")), None)
                _nm = (_cfgw or {}).get("titulo", "DESK")
                _wadd(GRN, "DESK", f"{dk['sym']}: REBOTE SCORE {dk['pts']}/10 — mano fuerte sobre la mesa, mira el {_nm}", dk["sym"], 1)
        if centinela:
            _cdir = 1 if centinela["estado"] in ("RISK-ON", "REENTRADA") else -1 if centinela["estado"] in ("LIQUIDEZ", "DISTRIBUCION") else 0
            _ccl = GRN if _cdir > 0 else RED if _cdir < 0 else CYN
            if centinela.get("prev") and centinela["prev"] != centinela["estado"]:
                _wadd(_ccl, "RÉGIMEN", f"CENTINELA cambia: {centinela['prev']} → {centinela['estado']} (spread {centinela['spread']:+.2f}) — confirmar el próximo cierre", "MERCADO", _cdir)
            elif centinela["estado"] in ("REENTRADA", "ACECHO", "DISTRIBUCION"):
                _wadd(_ccl, "RÉGIMEN", f"CENTINELA: {centinela['estado']} (spread {centinela['spread']:+.2f}, Δ3s {centinela['d3']:+.2f})", "MERCADO", _cdir)
        for r in (suelo or []):
            if r.get("fase") == "PRE-DESPERTAR" and r["sym"] in SECTORES_EXPLOSIVOS:
                _wadd(CYN, "PRE-DESP", f"{r['sym']}: patrón {r.get('pre', 0)}/4 con precio quieto — ventana de anticipación (💥 {EXPLOSIVO_TIPO.get(r['sym'], '')})", r["sym"], 1)
        # clima del dia: vela anomala vs su volatilidad tipica (el timeline cuenta si se repite: 1 dia = aviso, 3 = patron)
        _climas = sorted([(s2, f2) for s2, f2 in (flow or {}).items() if f2.get("clima") and s2 in rrg],
                         key=lambda x: -abs(x[1].get("zday") or 0))
        for s2, f2 in [x for x in _climas if x[1]["clima"] == "climax"][:3]:
            _wadd(AMB, "CLÍMAX", f"{s2}: {f2.get('ret1d', 0):+.1f}% {clima_dia(f2.get('clima_hace') or 0)} (z {f2.get('zday', 0):+.1f}) — la vela que ve todo el mundo; posible agotamiento, no fuerza", s2, -1)
        for s2, f2 in [x for x in _climas if x[1]["clima"] == "capitulacion"][:3]:
            _wadd("#B980FF", "CAPITUL", f"{s2}: {f2.get('ret1d', 0):+.1f}% {clima_dia(f2.get('clima_hace') or 0)} (z {f2.get('zday', 0):+.1f}) — pánico de un día; el cazador de suelos empieza a vigilar", s2, 1)
        for s2, f2 in sorted([(s3, f3) for s3, f3 in (flow or {}).items() if f3.get("acum_ext") and s3 in rrg],
                             key=lambda x: -(x[1].get("noct20") or 0))[:4]:
            _wadd(CYN, "NOCTURNO", f"{s2}: gap nocturno {f2.get('noct20', 0):+.1f}% en 20 sesiones con CMF {f2.get('cmf', 0):+.2f} — la compra ocurre en su bolsa local; el CMF americano no la ve", s2, 1)
        for g2 in (graduados or [])[:4]:
            _gsm = "esta semana" if g2["sem"] == 0 else ("hace 1 sem" if g2["sem"] == 1 else "hace %d sem" % g2["sem"])
            _wadd("#7BD88F", "GRADUADO", f"{g2['sym']}: despertó {_gsm}, {g2['pct']:+.1f}% desde el cruce, ext {g2.get('ext')}% — sigue en el panel de recién despertados", g2["sym"], 1)
        if giro and giro.get("rotacion"):
            _wadd(AMB, "GIRO", "Rotación intradía: vendieron lo caliente y compraron lo frío en la misma sesión (" + giro.get("fecha", "") + ")", "MERCADO", -1)
        for g in (giro.get("rows", [])[:3] if giro else []):
            _gt = "vendieron la subida" if g["sig"] == "bajista" else "compraron el miedo"
            _wadd((RED if g["sig"] == "bajista" else GRN), "GIRO",
                  f"{g['sym']}: gap {g['gap']:+.1f}% → cierre en {g['pos']}% del rango — {_gt}",
                  g["sym"], -1 if g["sig"] == "bajista" else 1)
        for b in (apal["brokers"] if apal else []):
            e5 = (b["esc"].get(-5) or {})
            if e5.get("estado") and e5["estado"] != "ok":
                _wadd(RED, "RISK", f"{b['broker']}: a S&P −5% → {e5['estado'].upper()}", b["broker"], -1)
        for s in (excluded_di or []):
            _wadd(AMB, "FLOW", f"{s}: DISTRIBUCIÓN OCULTA — precio sube, dinero sale. Excluido.", s, -1)
        for c in (contra_sigs or []):
            _wadd(GRN, "0/3", f"{c['sym']}: señal contraria {c['n3']}/3 · verticalidad {c['vert']}x · tamaño manga", c["sym"], 1)
        for r in (suelo or [])[:4]:
            if r["pts"] >= 8 and not r["sangra"]:
                _wadd(GRN, "SUELO", f"{r['sym']}: {r['pts']}/10 — castigo+olvido y dejó de sangrar", r["sym"], 1)
            elif r["sangra"]:
                _wadd(GRY, "SUELO", f"{r['sym']}: {r['pts']}/10 pero AÚN SANGRA — sin prisa", r["sym"], 0)
        for r in (early or [])[:3]:
            _wadd(CYN, "EARLY", f"{r['sym']}: girando al alza, ext {r['ext']}% — entrada sin perseguir", r["sym"], 1)
        if entering:
            _wadd(CYN, "RRG", "Entran a Mejorando: " + ", ".join(entering[:5]))
        if leaving:
            _wadd(AMB, "RRG", "Salen a Debilitándose: " + ", ".join(leaving[:5]))
        if candidato:
            _wadd(AMB, "PICK", f"Candidato del sistema: {candidato['top']['stock']['sym']} vía {candidato['top']['etf']}")
        if fg_idx and fg_idx["score"] <= 25:
            _wadd(RED, "SENT", f"F&G en MIEDO EXTREMO ({fg_idx['score']}) — histórico contrarian, confirma con flujo", "F&G", 1)
        # persistencia entre sesiones: guardar hoy + analizar las ultimas sesiones
        _wire_date = (giro or {}).get("fecha") or str(df.index[-1].date())
        wtl = None
        try:
            wtl = analyze_wire_persistence(update_wire_ledger(wire, _wire_date))
        except Exception:
            wtl = None
        _pers = {}
        if wtl:
            for sgn in wtl["sigs"]:
                _pers[(sgn["tag"], sgn["sym"])] = sgn
        sw = ""
        for it in wire[:14]:
            badge = ""
            p = _pers.get((it["tag"], it["sym"]))
            if p and p["today"] and it["sym"]:
                if p["streak"] >= 3:
                    badge = f" <b style='color:{GRN}'>×{p['streak']} sesiones ✓</b>"
                elif p["streak"] == 2:
                    badge = f" <span style='color:{AMB}'>×2 sesiones</span>"
                if p.get("contradice"):
                    badge += f" <span style='color:{RED}'>⚠ ayer al revés</span>"
            sw += (f"<div style='margin:3px 0;font-size:11.5px'><span style='color:#000;background:{it['col']};padding:0 5px;"
                   f"font-size:9px;font-weight:700;border-radius:2px'>{it['tag']}</span> <span style='color:#D8DEE9'>{esc(it['txt'])}</span>{badge}</div>")
        html.append(_mod(f"SIGNALS WIRE — {last_lbl}", sw or "<span style='color:#666'>sin señales relevantes esta semana</span>"))
        # --- MODULO 7b: WIRE TIMELINE — persistencia de señales entre sesiones ---
        if wtl and wtl.get("sigs"):
            _dts = wtl["dates"]
            _hdr = "".join(f"<th style='min-width:26px'>{d[8:10]}/{d[5:7]}</th>" for d in _dts)
            wt = f"<table><tr><th style='text-align:left'>SEÑAL</th>{_hdr}<th style='text-align:left'>LECTURA</th></tr>"
            _lvlc = {"alta": GRN, "media": AMB, "ruido": RED, "baja": GRY}
            for sgn in wtl["sigs"]:
                dots = ""
                for v in sgn["tl"]:
                    if v is None:
                        dots += "<td style='color:#333'>·</td>"
                    else:
                        _dc = GRN if v > 0 else RED if v < 0 else AMB
                        dots += f"<td style='color:{_dc}'>●</td>"
                _vc = _lvlc.get(sgn["lvl"], GRY)
                wt += (f"<tr><td style='text-align:left'><span style='color:#777;font-size:9px'>{sgn['tag']}</span> "
                       f"<b style='color:{AMB}'>{esc(str(sgn['sym']))}</b></td>{dots}"
                       f"<td style='text-align:left;color:{_vc};font-size:10.5px'>{esc(sgn['verd'])}</td></tr>")
            wt += "</table>"
            wt += ("<div style='font-size:10px;color:#666;margin-top:6px'>● verde = señal alcista ese cierre · ● rojo = bajista · ● ámbar = neutra · '·' = no apareció. "
                   "La regla que pediste, codificada: <b>un día es ruido; tres cierres seguidos en la misma dirección es un patrón confirmándose</b>; "
                   "un día y al siguiente lo contrario, el TIMELINE lo marca como mercado indeciso y le quita validez. "
                   "El histórico se guarda en <code>senales_wire.json</code> y empieza a contar desde hoy: necesita unas sesiones para llenarse.</div>")
            html.append(_mod(f"⏱ WIRE TIMELINE — persistencia de señales (últimas {len(_dts)} sesiones)", wt))
        # --- MODULO 8: FX & CROSS-ASSET ---
        xa = "<table><tr><th style='text-align:left'>ACTIVO</th><th>ÚLT</th><th>1S</th><th>12S</th><th style='text-align:left'>LECTURA</th></tr>"
        _lect = {"EURUSD": "€ fuerte = viento en contra en tus USD", "TLT": "TLT ↑ = tipos largos ↓",
                 "GLD": "refugio / tu manga metales", "UUP": "dólar: inverso a emergentes",
                 "HYG": "crédito HY: canario del riesgo", "IBIT": "beta cripto de tu perp"}
        for s in ["EURUSD", "TLT", "GLD", "UUP", "HYG", "IBIT"]:
            if s not in df.columns:
                continue
            ser = _ser(s)
            last = f"{float(ser.iloc[-1]):,.2f}".replace(",", " ") if ser is not None else "—"
            xa += (f"<tr><td style='text-align:left;color:{AMB};font-weight:700'>{s}</td><td style='color:#D8DEE9'>{last}</td>"
                   f"<td>{_fp(_chg(s, 1))}</td><td>{_fp(_chg(s, 12))}</td>"
                   f"<td style='text-align:left;color:{GRY};font-size:10px'>{_lect.get(s, '')}</td></tr>")
        xa += "</table>"
        html.append(_mod("FX & CROSS-ASSET — EL TABLERO ALREDEDOR", xa))
        html.append("</div>")  # cierre bbgrid
        html.append("<div class='bbgp' style='grid-column:1/-1'><div class='bbgb' style='font-size:10px;color:#666'>"
                    "PeVR TERMINAL PRO · datos de cierre semanal (Stooq/Yahoo, posible retardo) · todos los módulos beben de los mismos cálculos "
                    "que Contexto y Operativa, aquí en formato denso de mesa · el detalle y el porqué, en sus pestañas · no es asesoramiento</div></div>")
    except Exception as _pro_e:
        # CRITICO: si algo falla a mitad, descartamos TODO el HTML parcial de esta vista.
        # Si no, quedarian divs sin cerrar y las pestanas siguientes (Vigilancia, Claude) quedarian anidadas e invisibles.
        # v4.4: hasta ahora este except era MUDO. Una vista entera podia caerse y el
        # unico rastro era un cartel generico en pantalla, sin decir NI QUE fallo NI DONDE.
        # Ahora deja el error y la linea exacta en SALUD DEL BUILD y en la consola.
        import traceback as _tb
        _linea = "?"
        try:
            _tt = _tb.extract_tb(_pro_e.__traceback__)
            if _tt:
                _linea = str(_tt[-1].lineno)
        except Exception:
            pass
        _deg(f"vista_PRO:{_linea}", _pro_e)
        _avisar("PRO", f"la vista PRO no se genero: {type(_pro_e).__name__}: {_pro_e} (linea {_linea})")
        try:
            print(f"\n  [PRO] ERROR: {type(_pro_e).__name__}: {_pro_e}  -> linea {_linea}")
            _tb.print_exc()
        except Exception:
            pass
        del html[_bbg_mark:]
        html.append("<div class='panel full'><h2>🖥️ PRO</h2><div class='note'>Esta vista no se pudo generar "
                    f"(error: {esc(type(_pro_e).__name__)} en la línea {esc(_linea)}). "
                    "El detalle está en SALUD DEL BUILD y en la consola. El resto del terminal funciona con normalidad.</div></div>")
    html.append("</div>")

    # ===== V-REDES — SUPER RESUMEN PARA PUBLICAR (tarjeta JPG + texto + PDF) =====
    html.append("<div id='vista-rds' style='display:none'>")
    _rds_mark = len(html)
    try:
        _wk2 = df.index[-1].strftime("%G-W%V")
        # --- tarjeta visual (formato vertical para redes) ---
        card = []
        card.append(f"<div style='border-bottom:3px solid {light};padding-bottom:10px;margin-bottom:14px'>"
                    f"<div style='font-size:24px;font-weight:800;letter-spacing:2px'>ROTACIÓN <span style='color:{light}'>SEMANAL</span></div>"
                    f"<div style='color:#8FA3C0;font-size:12px;margin-top:2px'>{_wk2} · cierre {last_lbl} · sistema PeVR de flujo y rotación sectorial</div></div>")
        _kv = lambda k, v: (f"<div style='display:flex;gap:12px;margin:9px 0;align-items:baseline'>"
                            f"<span style='min-width:120px;font-size:10.5px;color:#8FA3C0;text-transform:uppercase;letter-spacing:.8px'>{k}</span>"
                            f"<span style='font-size:14px;line-height:1.55'>{v}</span></div>")
        # ticker + nombre corto, para que nadie tenga que adivinar qué es cada activo
        def _tkn(sym):
            nm = NAMES.get(sym, (sym, sym, ""))[1]
            return f"<b>{esc(sym)}</b> <span style='color:#8FA3C0;font-size:11px'>{esc(nm)}</span>"
        def _lista(syms, col, n=6):
            return "<br>".join(f"<span style='color:{col}'>{_tkn(s)}</span>" for s in syms[:n])
        card.append(_kv("Semáforo", f"<b style='color:{light};font-size:17px'>{esc(sem_short)}</b> · {esc(reg_short)} · {esc(risk['label'])}"
                        + (f" · F&G <b>{fg_idx['score']}</b> ({esc(str(fg_idx.get('rating', '')))})" if fg_idx else "")))
        _cart_list = [s.strip() for s in cartera_txt.split(",")] if ("," in cartera_txt or cartera_txt in NAMES) else None
        if _cart_list and all(s in NAMES for s in _cart_list):
            card.append(_kv("📦 En cartera ahora", _lista(_cart_list, "#5B8CFF", 8)
                            + "<br><span style='color:#5E708A;font-size:10px'>lo que el sistema tiene abierto esta semana</span>"))
        else:
            card.append(_kv("📦 En cartera ahora", f"<b style='color:#5B8CFF'>{esc(cartera_txt)}</b>"))
        if entering:
            card.append(_kv("🟢 Reforzando", _lista(entering, "#4CC2E0", 5)
                            + "<br><span style='color:#5E708A;font-size:10px'>ganan fuerza — el dinero empieza a entrar</span>"))
        if leaving:
            card.append(_kv("🟡 Reduciendo", _lista(leaving, "#F4B740", 5)
                            + "<br><span style='color:#5E708A;font-size:10px'>pierden fuerza — se sale poco a poco</span>"))
        if excluded_di:
            card.append(_kv("🔴 Trampa", _lista(excluded_di, "#F4607A", 4)
                            + "<br><span style='color:#5E708A;font-size:10px'>el precio sube pero el dinero SALE — no fiarse</span>"))
        if candidato:
            _t = candidato["top"]
            card.append(_kv("Pick sistema", f"<b style='color:#5B8CFF'>{_t['stock']['sym']}</b> vía {_t['etf']}"))
        _su8 = [r for r in (suelo or []) if r["pts"] >= 8 and not r["sangra"]][:3]
        if _su8:
            card.append(_kv("Radar suelo", "<span style='color:#2FD08A'>" + esc(", ".join(f"{r['sym']} ({r['pts']}/10)" for r in _su8)) + "</span> — castigados, olvidados y dejando de sangrar"))
        if contra_sigs:
            card.append(_kv("Contraria 0/3", "<span style='color:#7BD88F'>" + esc(", ".join(s["sym"] for s in contra_sigs)) + "</span>"))
        if tperf:
            _c2 = tperf["cum"]
            _d2 = (_c2.get("sys", 0) - _c2.get("SPY", 0)) * 100
            card.append(_kv("Track record", f"sistema {_c2.get('sys', 0) * 100:+.1f}% vs SPY {_c2.get('SPY', 0) * 100:+.1f}% "
                            f"({tperf['n']} sem, verificable)"))
        # tabla: cada ETF de la cartera desde que el sistema le dio ENTRADA, vs SPY y QQQ en ese mismo periodo.
        # FUENTE UNICA: el % del ETF sale de pct_desde_entrada sobre los PRECIOS GRABADOS en el ledger — exactamente
        # los mismos numeros que la columna "desde entrada" de la Cartera de la semana (antes esta tabla recalculaba
        # por fechas contra la serie re-descargada de Yahoo, que ajusta precios retroactivamente por dividendos, y
        # por eso los porcentajes no cuadraban entre paneles). SPY y QQQ se miden desde la FECHA REAL grabada en el
        # registro de entrada (rec["date"]), no desde un viernes reconstruido: misma ventana exacta para los tres.
        try:
            _dRows = ""
            def _rec_entrada(sym):
                """Registro (dict) de la semana de ENTRADA de la racha continua actual de sym, o None si es nuevo esta semana."""
                rows = [r for r in sorted(_recs_e or [], key=lambda r: r.get("week", "")) if r.get("week") != _cur_week]
                ent = None
                for r in reversed(rows):
                    if sym in r.get("basket", []):
                        ent = r
                    else:
                        break
                return ent
            def _precio_en_fecha(serie, fecha):
                try:
                    s = serie.dropna()
                    if not len(s):
                        return None
                    idx = s.index.searchsorted(pd.Timestamp(fecha))
                    if idx >= len(s):
                        idx = len(s) - 1
                    return float(s.iloc[idx])
                except Exception as _dege:
                    _deg("build_html:9919", _dege)
                    return None
            try:
                _qqq_serie = nq_close if (nq_close is not None and len(nq_close.dropna())) else (df["QQQ"] if "QQQ" in df.columns else None)
            except Exception:
                _qqq_serie = df["QQQ"] if "QQQ" in df.columns else None
            _f2 = lambda v: (f"<span style='color:{('#2FD08A' if v >= 0 else '#F4607A')}'>{v:+.1f}%</span>" if v is not None else "<span style='color:#5E708A'>—</span>")
            for _s2 in CARTERA_FINAL:
                if _s2 not in df.columns:
                    continue
                _px_now = float(df[_s2].dropna().iloc[-1])
                _res = pct_desde_entrada(_recs_e, _s2, "basket", _cur_week, True, _px_now, df)
                if _res is None:
                    continue
                _p2, _wk2b = _res
                _rec = _rec_entrada(_s2)
                _spyp, _qqqp, _audit = None, None, ""
                # fecha FINAL comun = la ultima fecha del propio ETF: los tres retornos se cierran EN ESE DIA.
                # (antes QQQ se cerraba en la ultima fecha de la serie Stooq del Nasdaq, que suele ir 1 sesion
                # por detras -> en semanas malas del Nasdaq la columna QQQ salia demasiado alta: ventanas distintas)
                try:
                    _fecha_fin = df[_s2].dropna().index[-1]
                except Exception:
                    _fecha_fin = None
                if _rec is not None and _rec.get("date"):
                    _fecha_e = _rec.get("date")
                    _pxg = _rec.get("px", {}) or {}
                    _spy_e = _pxg.get("SPY") or _precio_en_fecha(df["SPY"] if "SPY" in df.columns else None, _fecha_e)
                    if _spy_e and _spy_e > 0 and "SPY" in df.columns and _fecha_fin is not None:
                        _spy_f = _precio_en_fecha(df["SPY"], _fecha_fin) or float(df["SPY"].dropna().iloc[-1])
                        _spyp = (_spy_f / float(_spy_e) - 1) * 100
                    _qqq_e = _precio_en_fecha(_qqq_serie, _fecha_e)
                    _qqq_f = _precio_en_fecha(_qqq_serie, _fecha_fin) if _fecha_fin is not None else None
                    if _qqq_e and _qqq_e > 0 and _qqq_f:
                        _qqqp = (_qqq_f / _qqq_e - 1) * 100
                    # AUTO-AUDITORIA: recalcular el % del ETF por FECHAS puras sobre la serie re-descargada;
                    # si difiere >3pp del calculo por ledger, marcar la fila (huecos o precio mal grabado).
                    try:
                        _etf_e_chk = _precio_en_fecha(df[_s2], _fecha_e)
                        if _etf_e_chk and _etf_e_chk > 0:
                            _p_chk = (_px_now / _etf_e_chk - 1) * 100
                            if abs(_p_chk - _p2) > 3.0:
                                _audit = (f" <span title='ledger {_p2:+.1f}% vs por-fechas {_p_chk:+.1f}%: revisar precio grabado' "
                                          f"style='color:#F4B740;font-size:10px'>⚠</span>")
                    except Exception:
                        pass
                _nuevo = (_rec is None)
                _wk_lbl = ("<span style='color:#4CC2E0;font-size:9px'>nueva</span>" if _nuevo
                           else f"<span style='color:#8FA3C0;font-size:9px'>{_wk2b}s</span>") + _audit
                _win = (_p2 - _spyp) if (_spyp is not None) else None
                _wcol = "#5E708A" if _win is None else ("#2FD08A" if _win >= 0 else "#F4607A")
                _dRows += (f"<tr><td style='text-align:left;padding:3px 6px'><b style='color:#5B8CFF'>{_s2}</b> {_wk_lbl}</td>"
                           f"<td style='text-align:right;padding:3px 6px'>{_f2(_p2)}</td>"
                           f"<td style='text-align:right;padding:3px 6px'>{_f2(_spyp)}</td>"
                           f"<td style='text-align:right;padding:3px 6px'>{_f2(_qqqp)}</td>"
                           f"<td style='text-align:right;padding:3px 6px;color:{_wcol};font-weight:700'>{(f'{_win:+.1f}' if _win is not None else '—')}</td></tr>")
            if _dRows:
                card.append("<div style='margin-top:12px'><div style='font-size:10.5px;color:#8FA3C0;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px'>"
                            "Desde que el sistema dio entrada (mismo periodo)</div>"
                            "<table style='width:100%;border-collapse:collapse;font-size:12px'>"
                            "<tr style='color:#8FA3C0;font-size:9.5px'><th style='text-align:left;padding:3px 6px'>ETF · semanas</th>"
                            "<th style='text-align:right;padding:3px 6px'>ETF</th><th style='text-align:right;padding:3px 6px'>SPY</th>"
                            "<th style='text-align:right;padding:3px 6px'>QQQ</th><th style='text-align:right;padding:3px 6px'>vs SPY</th></tr>"
                            + _dRows + "</table>"
                            "<div style='font-size:9px;color:#7A8CA8;margin-top:4px'>⚖ Esta tabla muestra las posiciones ACTUALES desde su entrada (los que siguen vivos), "
                            "con los <b>mismos precios grabados en el ledger</b> que la columna «desde entrada» de la Cartera de la semana — un solo número para la misma pregunta. "
                            "SPY y QQQ se miden desde la fecha real de ese registro y se CIERRAN en la misma fecha final que el ETF (ventana idéntica en los dos extremos). "
                            "⚠ = el % del ledger difiere >3pp del recálculo por fechas: precio grabado sospechoso, revisar. «nueva» = entró esta semana (aún 0%). "
                            "El track record de arriba encadena la cesta completa semana a semana, incluidos los que salieron: por eso puede ser peor que la media de esta tabla. "
                            "Ambos son correctos; miden preguntas distintas.</div></div>")
        except Exception:
            pass
        card.append("<div style='margin-top:14px;padding:9px 11px;background:rgba(91,140,255,.06);border:1px solid #5B8CFF22;border-radius:8px;"
                    "font-size:10.5px;color:#9FB0C8;line-height:1.6'>💡 Cómo leerlo: <b style='color:#5B8CFF'>📦 En cartera</b> es lo que el sistema tiene abierto "
                    "ahora mismo. <b style='color:#4CC2E0'>🟢 Reforzando</b> y <b style='color:#F4B740'>🟡 Reduciendo</b> son los <b>movimientos</b> de esta semana "
                    "(hacia dónde va el dinero), no compras nuevas. Un activo puede estar en cartera y a la vez reduciéndose.</div>")
        card.append("<div style='margin-top:12px;padding:10px 12px;background:rgba(76,194,224,.07);border:1px solid #4CC2E033;border-radius:8px;"
                    "font-size:12px;color:#B9C9E2'>📬 Análisis completo cada sábado · señales de rotación, flujo institucional y radar de suelos"
                    "<br><span style='color:#4CC2E0;font-weight:700'>La Estela — próximamente en Substack y Telegram</span></div>")
        card.append("<div style='margin-top:12px;padding-top:8px;border-top:1px solid #2A3A55;font-size:8.5px;color:#7A8CA8;line-height:1.5'>"
                    "Contenido informativo y educativo de carácter general. NO es asesoramiento financiero personalizado ni recomendación de inversión "
                    "(MiFID II / criterios CNMV para divulgadores). El autor puede tener posiciones en los activos mencionados. "
                    "Rendimientos pasados no garantizan resultados futuros. Los productos apalancados conllevan alto riesgo. "
                    "Cada inversor es responsable de sus decisiones.</div>")
        # --- texto plano para copiar (X / Telegram): ticker + nombre y etiquetas que se explican solas ---
        def _tkn_txt(sym):
            return f"{sym} ({NAMES.get(sym, (sym, sym, ''))[1]})"
        _txt = [f"📊 ROTACIÓN SEMANAL {_wk2}",
                f"Semáforo: {sem_short} · {reg_short} · {risk['label']}" + (f" · F&G {fg_idx['score']}" if fg_idx else ""),
                "",
                "📦 EN CARTERA AHORA (lo que el sistema tiene abierto):",
                "  " + ", ".join(_tkn_txt(s.strip()) for s in cartera_txt.split(",")) if all(s.strip() in NAMES for s in cartera_txt.split(",")) else f"📦 En cartera: {cartera_txt}"]
        if entering:
            _txt.append("")
            _txt.append("🟢 REFORZANDO (ganan fuerza esta semana): " + ", ".join(_tkn_txt(s) for s in entering[:5]))
        if leaving:
            _txt.append("🟡 REDUCIENDO (pierden fuerza): " + ", ".join(_tkn_txt(s) for s in leaving[:5]))
        if excluded_di:
            _txt.append("🔴 TRAMPA (sube el precio pero sale el dinero): " + ", ".join(_tkn_txt(s) for s in excluded_di[:4]))
        if candidato:
            _txt.append(f"🏆 Pick del sistema: {candidato['top']['stock']['sym']} (vía {candidato['top']['etf']})")
        if _su8:
            _txt.append("🕳️ Radar suelo: " + ", ".join(f"{r['sym']} {r['pts']}/10" for r in _su8))
        _txt.append("")
        _txt.append("El flujo confirma, no predice. Análisis completo el sábado.")
        _txt.append("No es asesoramiento financiero. #inversión #ETF #rotaciónsectorial")
        _txt_js = json.dumps("\n".join(_txt), ensure_ascii=False)
        html.append("<script>var RDTXT=" + _txt_js + ";"
                    "function copiarRedes(){if(navigator.clipboard&&navigator.clipboard.writeText){"
                    "navigator.clipboard.writeText(RDTXT).then(function(){alert('Texto copiado. Pégalo en X o Telegram.');},"
                    "function(){alert('No se pudo copiar automáticamente. Abre \"Ver el texto plano\" y cópialo a mano.');});}"
                    "else{alert('Tu navegador bloquea el portapapeles aquí. Abre \"Ver el texto plano\" y cópialo a mano.');}}</script>")
        html.append("<div class='panel full'><h2>📣 Redes — el resumen que se publica</h2>"
                    "<div class='note'>Tu escaparate semanal: tarjeta vertical lista para X/Telegram/Instagram, texto plano para pegar y el PDF completo para Substack. "
                    "La tarjeta enseña <b>qué hace el sistema</b> sin regalar el terminal entero — el gancho para monetizar después. "
                    "El disclaimer CNMV/MiFID II va incorporado en la propia imagen: no lo quites.</div>"
                    "<div style='display:flex;gap:8px;flex-wrap:wrap;margin:10px 0'>"
                    f"<button class='viewtab' onclick=\"_h2c(document.getElementById('redes-card'),'rotacion_redes_{_wk2}.jpg')\" "
                    "style='border-color:#4CC2E055;color:#4CC2E0'>📸 Descargar tarjeta JPG</button>"
                    "<button class='viewtab' onclick='copiarRedes()' "
                    "style='border-color:#4CC2E055;color:#4CC2E0'>📋 Copiar texto para X/Telegram</button>"
                    "<button class='viewtab' onclick='descargarPDF()' style='border-color:#5B8CFF55;color:#5B8CFF'>📄 PDF completo (Substack)</button>"
                    "</div>"
                    "<div id='redes-card' style='max-width:560px;margin:0 auto;background:linear-gradient(160deg,#0A0E17 0%,#0D1524 100%);"
                    "border:1px solid #24344F;border-radius:14px;padding:26px 28px;color:#E8EEF9'>" + "".join(card) + "</div>"
                    "<details style='margin-top:12px'><summary style='cursor:pointer;color:#9FB0C8;font-size:12px'>Ver el texto plano (por si el botón de copiar no funciona)</summary>"
                    f"<pre style='background:#0E1626;border:1px solid #ffffff18;border-radius:8px;padding:12px;font-size:11.5px;white-space:pre-wrap;color:#CDE3FF'>{esc(chr(10).join(_txt))}</pre></details>"
                    "<div class='note' style='margin-top:8px;color:#5E708A'>Ritual de publicación del sábado: 1) genera el terminal con el cierre del viernes → "
                    "2) descarga tarjeta + PDF → 3) tarjeta a X/Telegram por la mañana, PDF a Substack → 4) mismo formato cada semana: la constancia ES el producto. "
                    "Recuerda el marco: análisis público NO personalizado, con posiciones propias declaradas.</div></div>")
        # ============ LOS 3 BLOQUES DEL RADAR DE ANTICIPACIÓN ============
        # Lo que nadie mas publica: la ficha FECHADA con sus huellas y su nivel de invalidacion,
        # la cadena de despertares detectados, y el libro con la tasa base — fallos incluidos.
        if despertares:
            _dsp = despertares
            # ---------- BLOQUE 1: FICHAS DE DESPERTAR (activas) ----------
            _act = _dsp.get("activas") or []
            _b1 = ("<div class='note'>Cada ficha se congela el día que el sistema detecta el despertar, con "
                   "<b>las huellas que se cumplieron</b> y <b>el nivel que la invalida</b> — declarado ANTES de saber el resultado. "
                   "No es una recomendación: es un registro. Y cada ficha viva lleva su <b>gestión</b>: un trailing medido en volatilidad del propio activo (máximo − 3×ATR), que es lo que evita las dos cosas malas — devolver lo ganado y salirte demasiado pronto por un susto normal. La ejecución sigue siendo tuya y con el cierre del viernes.</div>")
            if _act:
                for _a in _act[:8]:
                    _rc = RED if _a.get("roto") else (GRN if (_a.get("ret") or 0) > 0 else GRY)
                    _hu = "".join(f"<li style='margin:1px 0'>{h}</li>" for h in (_a.get("huellas") or [])) or "<li>—</li>"
                    _vs = (f" · vs {BENCH} <b style='color:{GRN if (_a.get('vs') or 0) > 0 else RED}'>{_a['vs']:+.1f}</b>"
                           if _a.get("vs") is not None else "")
                    _mc = _a.get("macro") or {}
                    _mtxt = ""
                    if _mc:
                        _u = _mc.get("usd"); _ch = _mc.get("china")
                        _partes = []
                        if _u:
                            _partes.append(f"<span style='color:{GRN if _u == 'baja' else AMB}'>dólar {_u}</span>")
                        if _ch:
                            _cc = GRN if _ch == "fuerte" else (AMB if _ch == "mixta" else RED)
                            _partes.append(f"<span style='color:{_cc}'>China {_ch}</span>")
                        if _mc.get("eslabon"):
                            _partes.append(f"<span style='color:#8FA3C0'>lideraba {esc(str(_mc['eslabon']))}</span>")
                        if _partes:
                            _mtxt = ("<div style='font-size:10.5px;color:#7A8AA3;margin-top:3px'>📌 macro al abrir la ficha: "
                                     + " · ".join(_partes) + "</div>")
                    _g = _a.get("gestion")
                    _gtxt = ""
                    if _g:
                        _gc = {"bueno": GRN, "aviso": AMB, "malo": RED}.get(_g["nivel"], GRY)
                        _dev = (f"<span style='color:{AMB}'>devuelto {_g['devol']:.0f}% de lo ganado</span>"
                                if _g.get("devol") is not None and _g["devol"] > 0 else
                                "<span style='color:#7A8AA3'>sin devolver nada</span>")
                        _gtxt = (f"<div style='background:{_gc}14;border-left:2px solid {_gc};border-radius:4px;"
                                 f"padding:5px 8px;margin-top:5px;font-size:11px'>"
                                 f"🎯 <b style='color:{_gc}'>{_g['estado']}</b>"
                                 f"<div style='color:#8FA3C0;margin-top:2px'>máximo desde la ficha <b>{_g['px_max']}</b> "
                                 f"(pico {_g['g_pico']:+.1f}%) · ahora <b>{_g['px_now']}</b> ({_g['g_hoy']:+.1f}%) · {_dev}</div>"
                                 + (f"<div style='color:#8FA3C0;margin-top:2px'>trailing por volatilidad (máx − 3×ATR): "
                                    f"<b style='color:{_gc}'>{_g['stop']}</b>"
                                    + (f" · te queda <b>{_g['margen']:+.1f}%</b> hasta él" if _g.get("margen") is not None else "")
                                    + "</div>" if _g.get("stop") else "")
                                 + "</div>")
                    _b1 += (f"<div style='border-left:3px solid {_rc};background:#0D111A;border-radius:6px;padding:8px 10px;margin:7px 0'>"
                            f"<div style='display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px'>"
                            f"<span><b style='color:{CYN};font-size:14px'>{_a['sym']}</b> "
                            f"<span style='font-size:10px;color:#8FA3C0'>{_a.get('fase')} · ficha del {_a.get('date')}</span></span>"
                            f"<span style='font-size:11px'>desde la ficha <b style='color:{_rc}'>{_a.get('ret', 0):+.1f}%</b>{_vs}</span></div>"
                            f"<div style='font-size:11px;color:#93A4BC;margin-top:3px'>"
                            f"caída {_a.get('caida')}% desde máximos · CMF {_a.get('cmf')} · silencio {_a.get('vr')}× · patrón {_a.get('pts')}/10</div>"
                            f"<ul style='margin:4px 0 2px 16px;padding:0;font-size:11px;color:#B9C6D8'>{_hu}</ul>"
                            + _mtxt + _gtxt +
                            f"<div style='font-size:11px;margin-top:3px'>"
                            + (f"<b style='color:{RED}'>✗ INVALIDADA</b>: perdió {_a.get('inval')} — la base se rompió, la tesis queda anulada."
                               if _a.get("roto") else
                               f"<span style='color:#8FA3C0'>Se invalida si pierde <b style='color:{AMB}'>{_a.get('inval')}</b></span>")
                            + f" · <span style='color:#667'>madura en {_a.get('faltan')} sesiones</span></div></div>")
            else:
                _b1 += "<div class='note'>Ninguna ficha abierta ahora mismo: no hay ningún sector en fase de despertar sin sangrar. Es información, no un fallo.</div>"
            html.append("<div class='panel full'><h2>🎯 FICHAS DE DESPERTAR — lo que el sistema ve antes que el titular</h2>" + _b1 + "</div>")

            # ---------- BLOQUE 2: LA CADENA ----------
            _cad = _dsp.get("cadena") or []
            if _cad:
                _b2 = ("<div class='note'>La secuencia de despertares que el sistema fue detectando, en orden. "
                       "Aquí es donde se ve —o no— la ventaja: la fecha de la ficha frente a lo que hizo el precio después. "
                       "Nada se borra; los que salieron mal siguen en la lista.</div>"
                       "<div class='scrollx'><table style='width:100%;font-size:11px;min-width:520px'>"
                       "<tr style='color:#777;font-size:10px'><td>FICHA</td><td>SECTOR</td><td>FASE</td>"
                       f"<td class='r'>CAÍDA</td><td class='r'>A 4 SEM</td><td class='r'>{BENCH}</td><td class='r'>VS</td><td>DESENLACE</td></tr>")
                for _c in _cad:
                    _cc = GRN if _c.get("gana") else RED
                    _des = ("<span style='color:#F4607A'>invalidada (perdió su nivel)</span>" if _c.get("roto")
                            else ("<span style='color:#2FD08A'>despertar confirmado</span>" if _c.get("gana")
                                  else "<span style='color:#93A4BC'>no despegó</span>"))
                    _vsx = (f"<b style='color:{GRN if (_c.get('vs') or 0) > 0 else RED}'>{_c['vs']:+.1f}</b>"
                            if _c.get("vs") is not None else "—")
                    _b2 += (f"<tr><td style='color:#8FA3C0'>{_c.get('date')}</td>"
                            f"<td><b style='color:{CYN}'>{_c['sym']}</b></td>"
                            f"<td style='color:#93A4BC;font-size:10px'>{_c.get('fase')}</td>"
                            f"<td class='r' style='color:#93A4BC'>{_c.get('caida')}%</td>"
                            f"<td class='r'><b style='color:{_cc}'>{_c.get('ret', 0):+.1f}%</b></td>"
                            f"<td class='r' style='color:#93A4BC'>{('%+.1f' % _c['ret_b']) if _c.get('ret_b') is not None else '—'}</td>"
                            f"<td class='r'>{_vsx}</td><td>{_des}</td></tr>")
                _b2 += "</table></div>"
                html.append("<div class='panel full'><h2>🔗 LA CADENA — los despertares detectados, en orden</h2>" + _b2 + "</div>")

            # ---------- BLOQUE 3: EL LIBRO ----------
            _lb = _dsp.get("libro")
            _b3 = ("<div class='note'>La tasa base del radar de anticipación, medida <b>fuera de muestra</b>: cada ficha se evalúa sola "
                   "a las 4 semanas, gane o pierda, con el resultado recalculado siempre desde precios reales. "
                   "Esto es lo que convierte el sistema en algo creíble — y lo que te protege: sin libro, cualquier acierto es una anécdota.</div>")
            if _lb:
                _pc = GRN if _lb["p"] >= 60 else (AMB if _lb["p"] >= 45 else RED)
                _b3 += (f"<div style='display:flex;gap:14px;flex-wrap:wrap;align-items:baseline;margin:8px 0'>"
                        f"<div><span style='font-size:26px;font-weight:700;color:{_pc}'>{_lb['p']}%</span>"
                        f"<span style='font-size:11px;color:#8FA3C0'> de fichas en positivo a 4 semanas</span></div>"
                        f"<div style='font-size:11px;color:#667'>IC 95% {_lb['lo']}–{_lb['hi']}% · n={_lb['n']} "
                        f"({_lb['gan']} aciertos / {_lb['n'] - _lb['gan']} fallos)</div></div>"
                        f"<div style='font-size:12px'>Media <b>{_lb['avg']:+.1f}%</b> · mediana <b>{_lb['med']:+.1f}%</b>"
                        + (f" · vs {BENCH} <b style='color:{GRN if _lb['avg_vs'] > 0 else RED}'>{_lb['avg_vs']:+.1f} pp</b>" if _lb.get("avg_vs") is not None else "")
                        + f" · invalidadas <b style='color:{RED}'>{_lb['rotas']}</b> de {_lb['n']}</div>")
                _pf = _lb.get("porfase") or {}
                if _pf:
                    _fil = ""
                    for _fn, _fv in _pf.items():
                        _fc = GRN if _fv["p"] >= 60 else (AMB if _fv["p"] >= 45 else RED)
                        _fil += (f"<tr><td style='color:#CDE3FF'>{'🌅' if _fn == 'DESPERTANDO' else '🌱'} {_fn}</td>"
                                 f"<td class='r'><b style='color:{_fc}'>{_fv['p']}%</b></td>"
                                 f"<td class='r'>{_fv['avg']:+.1f}%</td>"
                                 f"<td class='r' style='color:#667'>{_fv['gan']}/{_fv['n']}</td></tr>")
                    _b3 += ("<div style='color:#777;font-size:10px;letter-spacing:1px;margin:10px 0 3px'>¿COMPENSA ENTRAR TEMPRANO? — "
                            "RENDIMIENTO POR FASE DE LA FICHA</div>"
                            "<table style='width:100%;font-size:11.5px'><tr style='color:#777;font-size:10px'>"
                            "<td>FASE AL ABRIR LA FICHA</td><td class='r'>ACIERTO</td><td class='r'>MEDIA 4 SEM</td><td class='r'>N</td></tr>"
                            + _fil + "</table>"
                            "<div style='font-size:10px;color:#666;margin-top:3px'>Tu tesis dice que el dinero está en entrar "
                            "<b>en el giro</b> (🌅 DESPERTANDO) o incluso antes (🌱 PRE-DESPERTAR), no cuando el movimiento ya está maduro. "
                            "Esta tabla es la que la confirma o la desmiente con tus propios datos. Con pocas fichas todavía no dice nada: "
                            "déjala acumular.</div>")
                _pd = _lb.get("pordolar") or {}
                if _pd:
                    _fd = ""
                    for _dn, _dv in _pd.items():
                        _dc = GRN if _dv["p"] >= 60 else (AMB if _dv["p"] >= 45 else RED)
                        _fd += (f"<tr><td style='color:#CDE3FF'>{'📉' if _dn == 'baja' else '📈'} dólar {_dn}</td>"
                                f"<td class='r'><b style='color:{_dc}'>{_dv['p']}%</b></td>"
                                f"<td class='r'>{_dv['avg']:+.1f}%</td>"
                                f"<td class='r' style='color:#667'>{_dv['gan']}/{_dv['n']}</td></tr>")
                    _b3 += ("<div style='color:#777;font-size:10px;letter-spacing:1px;margin:10px 0 3px'>¿IMPORTA EL DÓLAR? — "
                            "RENDIMIENTO SEGÚN EL MACRO DEL DÍA DE LA FICHA</div>"
                            "<table style='width:100%;font-size:11.5px'><tr style='color:#777;font-size:10px'>"
                            "<td>DÓLAR AL ABRIR LA FICHA</td><td class='r'>ACIERTO</td><td class='r'>MEDIA 4 SEM</td><td class='r'>N</td></tr>"
                            + _fd + "</table>"
                            "<div style='font-size:10px;color:#666;margin-top:3px'>La teoría dice que mineras y emergentes lo hacen "
                            "peor con el dólar fuerte. Aquí se comprueba con TUS fichas. Ojo: la relación dólar-materias primas es fuerte "
                            "pero <b>se rompe</b> (en 2022 subieron los dos a la vez), por eso el macro va como <b>contexto y no como veto</b> — "
                            "un filtro duro te dejaría fuera de la buena algún día.</div>")
                if not _lb["maduro"]:
                    _b3 += (f"<div style='background:{AMB}18;border:1px solid {AMB}55;border-radius:6px;padding:7px 9px;margin-top:8px;font-size:11px;color:{AMB}'>"
                            f"⚠ Muestra corta: {_lb['n']} fichas maduras (el IC va de {_lb['lo']}% a {_lb['hi']}%, que es enorme). "
                            "<b>Hasta las ~20 no publiques esto como track record</b>: con esta N, el número central no significa casi nada. "
                            "Sigue acumulando y deja que el libro hable solo.</div>")
            else:
                _b3 += ("<div class='note'>Todavía no hay ninguna ficha madura (hacen falta 4 semanas desde la primera). "
                        "El libro empieza a contar desde hoy: es normal que esté vacío al principio.</div>")
            _b3 += ("<div style='font-size:10px;color:#666;margin-top:8px'>Honestidad del método: la ficha se congela el día de la detección "
                    "y el resultado se recalcula desde precios reales en cada build, así que no hay números guardados que puedan maquillarse. "
                    "Se cuentan TODAS las fichas, también las que salieron mal. El edge demostrado de este sistema es "
                    "<b>reducir drawdown, no batir al mercado</b>: la promesa honesta es anticipación y disciplina de salida. "
                    "Contenido informativo, NO asesoramiento personalizado (MiFID II / criterios CNMV).</div>")
            html.append("<div class='panel full'><h2>📒 EL LIBRO — la tasa base, con los fallos dentro</h2>" + _b3 + "</div>")
        # --- HISTORIAL COMPLETO: todas las entradas que el sistema ha dado, episodio a episodio, PERDIDAS INCLUIDAS ---
        try:
            _eps = episodios_cartera(_recs_e, df=df, cur_week=_cur_week)
            if _eps:
                _hRows = ""
                for _e in _eps:
                    _det_ep = ""
                    for _ep in _e["eps"]:
                        if _ep["ret"] is None:
                            continue
                        _rc = "#2FD08A" if _ep["ret"] >= 0 else "#F4607A"
                        _fin = "abierta" if _ep["abierto"] else (_ep["out"] or "?")
                        _det_ep += (f"<span style='display:inline-block;margin:1px 4px 1px 0;padding:1px 6px;background:#0A1220;"
                                    f"border:1px solid {_rc}44;border-radius:4px;font-size:9.5px;color:{_rc}'>"
                                    f"{_ep['in']}→{_fin} <b>{_ep['ret']:+.1f}%</b></span>")
                    _ac = _e["acum"]
                    _acc = "#2FD08A" if _ac >= 0 else "#F4607A"
                    _vs = None
                    if _e["acum_spy"] is not None:
                        _vs = _ac - _e["acum_spy"]
                    _vsc = "#5E708A" if _vs is None else ("#2FD08A" if _vs >= 0 else "#F4607A")
                    _ab = " <span style='font-size:8.5px;color:#4CC2E0'>(abierta)</span>" if _e["abierto"] else ""
                    _spy_txt = (f"{_e['acum_spy']:+.1f}%" if _e["acum_spy"] is not None else "—")
                    _hRows += (f"<tr><td style='text-align:left;padding:3px 6px;vertical-align:top'><b style='color:#5B8CFF'>{_e['sym']}</b>{_ab}"
                               f"<div style='font-size:8.5px;color:#8FA3C0'>{_e['gan']}/{_e['n']} ganadores</div></td>"
                               f"<td style='text-align:left;padding:3px 6px'>{_det_ep}</td>"
                               f"<td style='text-align:right;padding:3px 6px;color:{_acc};font-weight:800'>{_ac:+.1f}%</td>"
                               f"<td style='text-align:right;padding:3px 6px;color:#8FA3C0'>{_spy_txt}</td>"
                               f"<td style='text-align:right;padding:3px 6px;color:{_vsc};font-weight:700'>{(f'{_vs:+.1f}' if _vs is not None else '—')}</td></tr>")
                _n_perd = sum(1 for _e in _eps if _e["acum"] < 0)
                html.append("<div class='panel full' style='border-color:#5B8CFF33'>"
                            "<h2>📜 HISTORIAL COMPLETO DEL SISTEMA — todas las entradas, pérdidas incluidas</h2>"
                            "<div class='note'>Cada chip es un episodio real entrada→salida grabado en el ledger (viernes a viernes). "
                            "El ACUMULADO encadena todos los episodios del ETF, ganadores y perdedores — nada se borra: "
                            f"{_n_perd} de {len(_eps)} ETFs van en negativo acumulado y ahí se quedan, a la vista. "
                            "La transparencia del fallo es parte del producto: el edge de este sistema es reducir drawdown, y eso solo es creíble enseñando también lo que salió mal.</div>"
                            "<table style='width:100%;border-collapse:collapse;font-size:11.5px'>"
                            "<tr style='color:#8FA3C0;font-size:9.5px'><th style='text-align:left;padding:3px 6px'>ETF</th>"
                            "<th style='text-align:left;padding:3px 6px'>episodios (entrada→salida)</th>"
                            "<th style='text-align:right;padding:3px 6px'>ACUMULADO</th>"
                            "<th style='text-align:right;padding:3px 6px'>SPY mismos periodos</th>"
                            "<th style='text-align:right;padding:3px 6px'>vs SPY</th></tr>"
                            + _hRows + "</table></div>")
        except Exception as _e_hist:
            _avisar("render.historial", f"panel no renderizado: {_e_hist}")
    except Exception:
        del html[_rds_mark:]
        html.append("<div class='panel full'><h2>📣 Redes</h2><div class='note'>La tarjeta no se pudo generar esta semana.</div></div>")
    html.append("</div>")

    # ===== V3 — VISTA VIGILANCIA =====
    html.append("<div id='vista-vig' style='display:none'>")
    try:
        if watch:
            wrows = ""
            for r in watch:
                if not r.get("ok"):
                    wrows += (f"<tr><td class='se-l'><b>{r['sym']}</b> <span style='color:var(--txt3);font-size:11px'>{esc(r['name'])}</span></td>"
                              "<td class='r' colspan='6' style='color:#5E708A'>sin datos (¿ticker correcto?)</td></tr>")
                    continue
                pe, pl, pc = PHASE_INFO.get(r["phase"], ("", "—", "#9FB0C8"))
                cmf = r.get("cmf")
                cmf_s = (f"<span style='color:{'#2FD08A' if (cmf or 0) > 0 else '#F4607A'}'>{cmf:+.2f}</span>") if cmf is not None else "—"
                obv_s = ("<span style='color:#2FD08A'>OBV↑</span>" if r.get("obv_above") else "<span style='color:#F4607A'>OBV↓</span>")
                if r.get("obv_cross"):
                    obv_s += " <span style='color:#2FD08A'>⚡cruce</span>"
                hicol = "#F4607A" if r["hi52"] >= 90 else "#9FB0C8"
                momcol = "#2FD08A" if r["mom3"] > 0 else "#F4607A"
                wrows += (f"<tr><td class='se-l'><b>{r['sym']}</b> <span style='color:var(--txt3);font-size:11px'>{esc(r['name'])}</span></td>"
                          f"<td class='r'>{r['price']:,.2f}</td>"
                          f"<td class='r' style='color:{pc};white-space:nowrap'>{pe} {pl}</td>"
                          f"<td class='r' style='white-space:nowrap'>{cmf_s} · {obv_s}</td>"
                          f"<td class='r' style='color:{momcol}'>{r['mom3']:+.1f}%</td>"
                          f"<td class='r' style='color:{hicol};white-space:nowrap'>{r['hi52']}% máx · +{r['frm_lo']}% mín</td>"
                          f"<td class='r' style='color:{r['ecol']};white-space:nowrap;font-size:11px'>{esc(r['estado'])}</td></tr>")
            html.append("<div class='panel full'><h2>📋 Vigilancia — ¿cuándo empieza a acumular?</h2>"
                        "<div class='note'>Las acciones que vigilas o tienes y crees que a largo plazo lo harán bien. El objetivo: no estar solo "
                        "<b>esperando</b> a que recuperen, sino <b>ver</b> la señal de cuándo el dinero empieza a entrar — el primer chispazo del cambio de base a subida, "
                        "antes de que el precio lo confirme. <b>Estado:</b> 🔴 aún cayendo (cuchillo) → 🟦 en base sin flujo (espera) → "
                        "🟢 empezando a acumular (el dinero entra, ojo) → 🟢 subiendo (ya arrancó). Es un <b>mapa de probabilidad, no una predicción</b>: una hundida puede seguir cayendo, "
                        "y el semáforo te lo dirá igual de claro. Edita la lista en WATCHLIST. No es asesoramiento.</div>"
                        "<div class='scrollx'><table class='se'><tr><th class='se-l'>acción</th><th class='r'>precio</th><th class='r'>fase</th>"
                        "<th class='r'>flujo (CMF · OBV)</th><th class='r'>mom 3m</th><th class='r'>rango 52s</th><th class='r'>estado</th></tr>"
                        + wrows + "</table></div></div>")
        else:
            html.append("<div class='panel full'><h2>📋 Vigilancia</h2><div class='note'>Sin datos de la watchlist. Revisa la lista WATCHLIST y que haya conexión.</div></div>")
    except Exception:
        html.append("<div class='panel full'><h2>📋 Vigilancia</h2><div class='note'>No se pudo construir la vigilancia esta vez.</div></div>")
    html.append("</div>")
    # ---- PESTAÑA MODO CLAUDE: la decision limpia en una pantalla ----
    try:
        _cl = ["<div id='vista-cl' style='display:none'>",
               "<div class='panel full'><h2>🤖 Modo Claude — la decisión, limpia</h2>",
               "<div class='note'>Solo lo esencial para decidir el viernes y ejecutar el lunes: dónde estar (⭐ = en cartera), qué evitar, y los giros verticales de los dormidos. El detalle completo sigue en Contexto y Operativa. No es asesoramiento.</div></div>"]
        est = "".join(
            f"<tr><td class='se-l'>{'⭐ ' if e['in_cart'] else ''}<b>{e['sym']}</b> "
            f"<span style='color:var(--txt3);font-size:11px'>{esc(NAMES.get(e['sym'], (e['sym'], e['sym'], ''))[1])}</span></td>"
            f"<td class='r'>{e['sc']}/5</td>"
            f"<td class='r' style='font-size:11px'>{QUAD.get(e['quad'], (e['quad'],))[0]}</td>"
            f"<td class='r' style='font-size:11px'>CMF {(e['cmf'] if e['cmf'] is not None else 0):+.2f}</td></tr>"
            for e in (_estar or [])[:9])
        _cl.append("<div class='panel full'><h2>🧺 CARTERA FINAL de la semana</h2>"
                   "<div style='font-size:15px;padding:6px 0'><b style='color:#5B8CFF'>" + esc(", ".join(CARTERA_FINAL) if CARTERA_FINAL else "liquidez — sin señal suficiente") + "</b></div>"
                   "<div class='note'>La única lista que se opera (viernes confirma, lunes ejecuta). Los porcentajes, en Contexto → Cartera de la semana.</div></div>")
        _cl.append("<div class='panel full'><h2>✅ Candidatos por puntuación (⭐ = en cartera)</h2><div class='scrollx'><table class='se'>"
                   "<tr><th class='se-l'>sector</th><th class='r'>nota</th><th class='r'>tendencia</th><th class='r'>flujo</th></tr>"
                   + (est or "<tr><td colspan='4' style='color:#9FB0C8'>Nada cumple las tres condiciones — mejor esperar.</td></tr>")
                   + "</table></div></div>")
        ev = ", ".join(f"<b>{s}</b> <span style='font-size:11px'>({esc(w)})</span>" for s, w in (_evitar or [])[:14])
        if ev:
            _cl.append(f"<div class='panel full'><h2>⛔ Evitar / fuera</h2><div class='note' style='color:#F4607A'>{ev}</div></div>")
        try:
            vr2 = "".join(
                f"<tr><td class='se-l'>🚀 <b>{s}</b> <span style='color:var(--txt3);font-size:11px'>{esc(NAMES.get(s, (s, s, ''))[1])}</span></td>"
                f"<td class='r' style='color:#7BD88F;font-weight:700'>{vert:.1f}×</td>"
                f"<td class='r'>{(str(n3) + '/3') if n3 is not None else '—'}</td><td class='r'>{fl}</td></tr>"
                for vert, s, d, dmom, drat, n3, fl in (vrows or [])[:6])
            if vr2:
                _cl.append("<div class='panel full'><h2>🚀 Dormidos girando en vertical</h2>"
                           "<div class='note'>Abajo en Rezagado y despertando (0-1/3 señales = históricamente 65% a 4 semanas). Especulativo: tamaño pequeño.</div>"
                           "<div class='scrollx'><table class='se'><tr><th class='se-l'>sector</th><th class='r'>verticalidad</th><th class='r'>señales</th><th class='r'>flujo</th></tr>"
                           + vr2 + "</table></div></div>")
        except Exception:
            pass
        # --- OPCIONES EN CRISTIANO: el OPTIONS DESK traducido a frases simples, ETF a ETF ---
        try:
            _exp = explicar_opciones(options, flow=flow, rrg=rrg, cartera=(set(CARTERA_FINAL or []) | ({t[0] for t in MI_CARTERA} if MI_CARTERA else set())))
            if _exp:
                _bloq = ""
                _visibles = [e for e in _exp if e["en_cart"] or e["prio"] <= 1][:14]
                _resto = [e for e in _exp if e not in _visibles]
                for _e in _visibles:
                    _tagc = " <span style='font-size:9px;color:#5B8CFF'>EN CARTERA</span>" if _e["en_cart"] else ""
                    _fr = " ".join(esc(x) for x in _e["frases"])
                    _bloq += (f"<div style='margin:7px 0;padding:9px 12px;background:#0E1626;border-left:3px solid {_e['vcol']};border-radius:8px'>"
                              f"<div style='font-size:13px'><b style='color:#E6EDF6'>{_e['sym']}</b>{_tagc}</div>"
                              f"<div style='font-size:12px;color:#B9C9E2;margin:3px 0;line-height:1.65'>{_fr}</div>"
                              f"<div style='font-size:12px;color:{_e['vcol']};font-weight:600'>{esc(_e['ver'])}</div></div>")
                if _resto:
                    _filas_r = "".join(f"<div style='font-size:11px;margin:3px 0'><b style='color:#8FA3C0'>{_e['sym']}</b> "
                                       f"<span style='color:{_e['vcol']}'>{esc(_e['ver'])}</span></div>" for _e in _resto)
                    _bloq += (f"<details style='margin-top:5px'><summary style='cursor:pointer;font-size:11px;color:#8FA3C0'>"
                              f"el resto del universo — {len(_resto)} ETFs más (solo veredicto)</summary>{_filas_r}</details>")
                _cl.append("<div class='panel full' style='border-color:#4CC2E055'>"
                           "<h2>🎓 OPCIONES EN CRISTIANO — qué está pasando en cada ETF, sin jerga</h2>"
                           "<div class='note'>Para leerlo solo necesitas esto: un <b>put es un seguro contra caídas</b>, un <b>call es una apuesta a que sube</b>, "
                           "y la <b>IV es el precio de ese seguro</b>. Aquí cruzo lo que hace el dinero de contado (tu CMF) con lo que hacen en opciones: "
                           "cuando las dos vías coinciden, la señal es fuerte; cuando discrepan, alguien miente — y suele mentir el precio. "
                           "Cartera primero, luego los avisos. No es asesoramiento.</div>"
                           + _bloq + "</div>")
        except Exception as _e_exp:
            _avisar("render.cristiano", f"panel no renderizado: {_e_exp}")
        # --- PANEL DE IA AUTOMATICA: la respuesta del maestro, generada EN ESTE BUILD ---
        try:
            if ia_auto:
                for _k in (["resumen"] + [x for x in (IA_AUTO_EXTRA or []) if x != "resumen"]):
                    _r = ia_auto.get(_k)
                    if not _r:
                        continue
                    _col = "#FFB000" if _r["ok"] else "#F4607A"
                    _cuerpo = esc(_r["text"]).replace(chr(10) + chr(10), "</p><p>").replace(chr(10), "<br>")
                    _cl.append(f"<div class='panel full' style='border:1px solid {_col}55'>"
                               f"<h2 style='color:{_col}'>🤖 {esc(_r['title'])} — RESPUESTA AUTOMÁTICA DE ESTE BUILD</h2>"
                               "<div class='note'>Generada al ejecutar el terminal: el prompt se lanzó a la API con el snapshot de datos de este cierre inyectado"
                               + (" y permiso de búsqueda web" if IA_WEB_SEARCH else "") + ". Es una hipótesis de máquina, no asesoramiento — el veredicto lo dan tus viernes.</div>"
                               f"<div style='font-size:13px;line-height:1.75;color:#DCE6F5'><p>{_cuerpo}</p></div>"
                               f"<div class='note' style='margin-top:8px;color:#5E708A'>modelo {esc(_r['modelo'])} · para auto-ejecutar más prompts, añade sus claves en <code>IA_AUTO_EXTRA</code> (cada uno suma tiempo y coste)</div></div>")
            elif IA_AUTO:
                _cl.append("<div class='panel full'><h2>🤖 IA automática — SIN ACTIVAR</h2>"
                           "<div class='note'>El terminal está listo para <b>ejecutar el prompt maestro automáticamente en cada build</b> y pintar aquí la respuesta, "
                           "pero falta la API key. Activación SIN tocar código: <b>(1)</b> consigue una key (GRATIS en <b>aistudio.google.com/apikey</b> con IA_PROVIDER=openai_compat, o de pago en <b>console.anthropic.com</b>, "
                           "independiente de tu suscripción de claude.ai — el análisis maestro con búsqueda web cuesta del orden de céntimos por ejecución); "
                           "<b>(2)</b> crea un archivo de texto <code>ia_key.txt</code> (proveedor gratis) o <code>anthropic_key.txt</code> (Anthropic) en la MISMA carpeta que rotacion.py y pega dentro solo la key, en una sola línea; "
                           "<b>(3)</b> vuelve a ejecutar — el terminal la encuentra sola y, si la carpeta es un repositorio git, añade el archivo a .gitignore automáticamente para que la key nunca acabe subida a GitHub. "
                           "<b>Vía GRATIS</b>: pon <code>IA_PROVIDER = \"openai_compat\"</code> y una key gratuita de Google AI Studio (aistudio.google.com/apikey) en <code>IA_COMPAT_KEY</code> — automático a coste cero, con los límites del tier gratuito y sin búsqueda web. "
                           "Mientras tanto, los botones de abajo copian cada prompt con tus datos para pegarlo a mano en claude.ai.</div></div>")
        except Exception:
            pass
        # --- BIBLIOTECA DE PROMPTS: cada uno se copia CON los datos del terminal inyectados (cierra el circulo) ---
        try:
            _plib = IA_PROMPTS or [
                ("sectorial", "🕰 Rotación sectorial — 30 años de precursores",
                 "Analiza los últimos 30 años y encuentra qué indicadores (tipos de interés, inflación, ISM, PMI, curva de tipos, desempleo, beneficios empresariales, dólar y petróleo) han anticipado las rotaciones entre tecnología, financieras, industriales, energía, consumo, salud y utilities."),
                ("flujos", "💸 Flujos institucionales",
                 "Detecta qué sectores están recibiendo entradas de dinero institucional durante las últimas cuatro semanas comparándolo con los últimos cinco años."),
                ("liderazgo", "🏁 Liderazgo antes de que se vea",
                 "¿Qué industrias están mostrando fortaleza relativa frente al S&P 500 antes de que el mercado general las reconozca?"),
                ("ocultas", "🕵️ Rotaciones ocultas",
                 "Busca acciones que estén rompiendo máximos de 52 semanas mientras el sector todavía no aparece entre los mejores del S&P 500."),
                ("ciclo", "🕐 Ciclo económico",
                 "Según los datos macro actuales, ¿en qué fase del ciclo económico está Estados Unidos y qué sectores suelen liderar históricamente esa fase?"),
                ("insiders", "🐋 Insiders y grandes fondos",
                 "Cruza compras de insiders, posiciones de hedge funds y cambios en las carteras de Berkshire Hathaway, Bridgewater, Pershing Square y otros grandes gestores para detectar posibles rotaciones."),
                ("narrativas", "🗣 Narrativas emergentes",
                 "¿Qué temas empiezan a aparecer cada vez más en las conferencias de resultados (earnings calls) antes de que el mercado los descuente?"),
                ("multifactor", "🧮 Ranking multifactor",
                 "Construye un ranking semanal de sectores utilizando fortaleza relativa, beneficios revisados al alza, momentum, volumen institucional y valoración."),
                ("gestor", "🎖 GESTOR DE HEDGE FUND MACRO (el maestro)",
                 "Actúa como un gestor de un hedge fund macro. Analiza diariamente datos macroeconómicos de EE. UU., flujos institucionales, fortaleza relativa de sectores, revisiones de beneficios, mercado de bonos, dólar, VIX, materias primas y amplitud de mercado. Identifica qué sectores tienen mayor probabilidad de liderar durante las próximas 2 a 8 semanas y explica por qué. Asigna una probabilidad a cada escenario y señala qué datos invalidarían esa hipótesis."),
            ]
            _pdata = ia_data_block(snap, last_lbl)
            _clp = {k: p + _pdata for k, _, p in _plib}
            cards = ""
            for k, tit, p in _plib:
                _dest = (k == "gestor")
                _bg = "rgba(255,176,0,.07)" if _dest else "#0E1626"
                _bd = "#FFB00055" if _dest else "#24344F"
                _w = "grid-column:1/-1;" if _dest else ""
                cards += (f"<div style='{_w}background:{_bg};border:1px solid {_bd};border-radius:10px;padding:12px 14px'>"
                          f"<div style='font-size:12.5px;font-weight:700;color:{'#FFB000' if _dest else '#E8EEF9'};margin-bottom:6px'>{tit}</div>"
                          f"<div style='font-size:11px;color:#9FB0C8;line-height:1.5;margin-bottom:8px'>{esc(p[:170])}{'…' if len(p) > 170 else ''}</div>"
                          f"<button class='viewtab' onclick=\"copiarPromptCL('{k}',this)\" "
                          f"style='font-size:11px;padding:5px 10px;border-color:{_bd};color:{'#FFB000' if _dest else '#5B8CFF'}'>📋 Copiar CON mis datos</button></div>")
            _cl.append("<div class='panel full'><h2>📚 Biblioteca de prompts — pregunta como un hedge fund</h2>"
                       "<div class='note'>El círculo cerrado: cada botón copia el prompt <b>con el snapshot de datos de este cierre inyectado debajo</b> "
                       "(RRG, flujo, scoring, régimen, plan). Pégalo en Claude o en la IA que uses: no le preguntas al aire — le preguntas <b>sobre tu terminal</b>, "
                       "y le exiges fuentes para lo que tu terminal no ve (13F, insiders, earnings calls). El maestro en ámbar es el de diario; "
                       "los demás, munición del fin de semana.</div>"
                       "<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px'>" + cards + "</div>"
                       "<div style='margin-top:10px'><a class='ai-btn alt' href='https://claude.ai/new' target='_blank' rel='noopener'>Abrir Claude</a></div>"
                       "<div class='note' style='margin-top:8px;color:#5E708A'>Honestidad de ingeniero: la IA razona, no backtestea — las respuestas sobre \"30 años de historia\" "
                       "son conocimiento general, no un backtest tuyo; y los datos de 13F/insiders llegan con retraso regulatorio de semanas. "
                       "Úsalo como generador de hipótesis; el veredicto lo siguen dando tus cierres de viernes. No es asesoramiento.</div></div>")
            _cl.append("<script>var CLP=" + json.dumps(_clp, ensure_ascii=False) + ";"
                       "function copiarPromptCL(k,btn){if(navigator.clipboard&&navigator.clipboard.writeText){"
                       "navigator.clipboard.writeText(CLP[k]).then(function(){var t=btn.textContent;btn.textContent='✓ Copiado — pégalo en Claude';"
                       "setTimeout(function(){btn.textContent=t;},2500);},function(){alert('El navegador bloquea el portapapeles. Abre el terminal por https (GitHub Pages) y volverá a funcionar.');});}"
                       "else{alert('Portapapeles no disponible en este navegador.');}}</script>")
        except Exception:
            pass
        _cl.append("</div>")
        html.append("".join(_cl))
    except Exception:
        html.append("<div id='vista-cl' style='display:none'></div>")

    # ===== V-VEREDICTO — las tres vías (flujo+RRG+opciones) fundidas en una línea por ETF =====
    try:
        html.append("<div id='vista-vd' style='display:none'>")
        _vd = veredicto_unico(_fichas if "_fichas" in dir() else None, options=options)
        if _vd:
            # leyenda de claridad
            html.append("<div class='panel full' style='border-color:#4CC2E055'>"
                        "<h2>⚖️ VEREDICTO — todo cruzado, en una línea por ETF</h2>"
                        "<div class='note'>Aquí se juntan las tres vías que mira el terminal — el <b>dinero de contado</b> (flujo/CMF), "
                        "la <b>fuerza relativa</b> (si es líder o rezagado) y las <b>opciones</b> (miedo o confianza) — y te doy un veredicto "
                        "en cristiano por cada ETF. Ordenado por claridad: primero lo tuyo, luego las señales más claras, al final lo dudoso. "
                        "Cuando las tres vías coinciden, la señal es fuerte; cuando se contradicen, el aviso lo dice. "
                        "Esto es el mismo motor de la pestaña Operativa, resumido para leer de un vistazo. No es asesoramiento.</div>")
            # agrupar por claridad
            _grupos, _orden_g = {}, []
            for _v in _vd:
                g = _v["claridad"]
                if g not in _grupos:
                    _grupos[g] = []; _orden_g.append(g)
                _grupos[g].append(_v)
            _cart = [_v for _v in _vd if _v["en_cart"]]
            if _cart:
                html.append("<div style='font-size:11px;color:#5B8CFF;text-transform:uppercase;letter-spacing:1px;margin:8px 0 4px'>⭐ Tu cartera</div>")
                for _v in _cart:
                    html.append(_vd_card(_v))
            for g in _orden_g:
                _items = [x for x in _grupos[g] if not x["en_cart"]]
                if not _items:
                    continue
                _gc = _items[0]["cl_col"]
                html.append(f"<div style='font-size:11px;color:{_gc};text-transform:uppercase;letter-spacing:1px;margin:12px 0 4px'>{esc(g)}</div>")
                for _v in _items:
                    html.append(_vd_card(_v))
            html.append("</div>")
        else:
            html.append("<div class='panel full'><h2>⚖️ VEREDICTO</h2><div class='note'>Se genera con las fichas de Operativa; ejecuta con datos para verlo.</div></div>")
        html.append("</div>")
    except Exception as _e_vd:
        _avisar("render.veredicto", f"panel no renderizado: {_e_vd}")
        html.append("<div id='vista-vd' style='display:none'></div>")

    # ===== V-NEWS — solo noticias/catalizadores CON FECHA que mueven las posiciones =====
    try:
        html.append("<div id='vista-news' style='display:none'>")
        # 1) respuesta de la IA con busqueda web (si hay key): el filtro duro de noticias
        _rn = (ia_auto or {}).get("news")
        if _rn:
            _ncol = "#2FD08A" if _rn["ok"] else "#F4607A"
            _ncuerpo = esc(_rn["text"]).replace(chr(10) + chr(10), "</p><p>").replace(chr(10), "<br>")
            html.append(f"<div class='panel full' style='border:1px solid {_ncol}55'>"
                        f"<h2 style='color:{_ncol}'>📰 NEWS — catalizadores con fecha, filtrados para tu universo</h2>"
                        "<div class='note'>Generado en este build con búsqueda web: solo eventos fechados que pueden mover tus ETFs. "
                        "Sin opiniones de analistas, sin price targets, sin ruido. Contrasta las fechas antes de operar — la IA puede equivocarse. No es asesoramiento.</div>"
                        f"<div style='font-size:13px;line-height:1.75;color:#DCE6F5'><p>{_ncuerpo}</p></div>"
                        f"<div class='note' style='margin-top:6px;color:#5E708A'>modelo {esc(_rn['modelo'])} · se regenera en cada ejecución del terminal</div></div>")
        else:
            html.append("<div class='panel full'><h2>📰 NEWS — SIN ACTIVAR</h2>"
                        "<div class='note'>Esta pestaña se llena automáticamente en cada build con los catalizadores fechados de las próximas 2 semanas "
                        "(FOMC, resultados que arrastran a tus ETFs, regulación, geopolítica), muy filtrados para tu universo. "
                        "Necesita la API key de Anthropic (crea <code>anthropic_key.txt</code> junto al script) y <code>IA_WEB_SEARCH=True</code>. "
                        "El prompt «news» ya está en la biblioteca y en <code>IA_AUTO_EXTRA</code>.</div></div>")
        # 2) CALENDARIO FIJO: fechas estructurales que no dependen de la IA (verificadas jul-2026)
        _hoy_n = dt.date.today()
        _fomc = [("2026-07-29", "FOMC — decisión de tipos 14:00 ET (reunión 28-29; sin dot plot)"),
                 ("2026-09-16", "FOMC — decisión + dot plot (SEP)"),
                 ("2026-10-28", "FOMC — decisión de tipos"),
                 ("2026-12-09", "FOMC — decisión + dot plot (SEP)")]
        _prox = [(f, t) for f, t in _fomc if dt.date.fromisoformat(f) >= _hoy_n][:3]
        try:
            _prox = sorted(_prox + [(f, "⚡ " + t) for f, t in (EVENTOS_MERCADO or [])
                                    if dt.date.fromisoformat(f) >= _hoy_n - dt.timedelta(days=2)])[:6]
        except Exception:
            pass
        _rows_cal = "".join(f"<tr><td style='padding:3px 8px;color:#F4B740;white-space:nowrap'><b>{f}</b></td>"
                            f"<td style='padding:3px 8px'>{t}</td></tr>" for f, t in _prox)
        _tau_row = ""
        if tau:
            _tau_row = (f"<tr><td style='padding:3px 8px;color:{tau['col']};white-space:nowrap'><b>ciclo τ</b></td>"
                        f"<td style='padding:3px 8px'>ventana {tau['win_ini']}→{tau['win_fin']} · transición {tau['trans_ini']}→{tau['trans_fin']} · "
                        f"rebote <b style='color:#2FD08A'>{tau['reb_ini']}→{tau['reb_fin']}</b></td></tr>")
        html.append("<div class='panel full' style='border-color:#F4B74033'>"
                    "<h2>🗓 CALENDARIO ESTRUCTURAL — fechas que no cambian con el ruido</h2>"
                    "<table style='width:100%;border-collapse:collapse;font-size:12px'>" + _rows_cal + _tau_row +
                    "<tr><td style='padding:3px 8px;color:#8FA3C0;white-space:nowrap'><b>mensuales</b></td>"
                    "<td style='padding:3px 8px;color:#8FA3C0'>NFP: primer viernes de mes · CPI: ~mediados · PCE: fin de mes · "
                    "vencimiento de opciones: tercer viernes — confirmar horas en el calendario económico</td></tr></table>"
                    "<div class='note' style='margin-top:6px'>Fechas FOMC verificadas contra el calendario oficial de la Fed (jul-2026). "
                    "La regla de la casa: los catalizadores fechados se cruzan SIEMPRE con el ciclo τ — un FOMC en transición τ (como el del 29-jul) "
                    "amplifica el giro de fin de mes en las dos direcciones.</div></div>")
        html.append("</div>")
    except Exception as _e_news:
        _avisar("render.news", f"panel no renderizado: {_e_news}")
        html.append("<div id='vista-news' style='display:none'></div>")

    # ---- RESUMEN SEMANAL DESCARGABLE (PDF imprimible / JPG para redes) ----
    try:
        _wk_lbl = df.index[-1].strftime("%G-W%V")
    except Exception:
        _wk_lbl = "semana"
    _res_mark = len(html)
    try:
        _rline = lambda k, v, col="#E8EEF9": (f"<div style='display:flex;gap:10px;margin:7px 0;align-items:baseline'>"
                                              f"<span style='min-width:150px;font-size:11px;color:#8FA3C0;text-transform:uppercase;letter-spacing:.5px'>{k}</span>"
                                              f"<span style='font-size:13px;color:{col};line-height:1.5'>{v}</span></div>")
        rs_parts = []
        rs_parts.append(f"<div style='display:flex;justify-content:space-between;align-items:baseline;border-bottom:2px solid {light};padding-bottom:8px;margin-bottom:12px'>"
                        f"<div><span style='font-size:20px;font-weight:800;letter-spacing:1px'>ROTACIÓN</span> "
                        f"<span style='color:#8FA3C0;font-size:12px'>· Resumen semanal</span></div>"
                        f"<div style='color:#8FA3C0;font-size:12px'>{_wk_lbl} · cierre {last_lbl}</div></div>")
        rs_parts.append(_rline("¿Invierto?", f"<b style='color:{light}'>{esc(sem_short)}</b> · {esc(reg_short)} · {esc(risk['label'])} · mercado {mkt}"))
        if fg_idx:
            _fgc = "#F4607A" if fg_idx["score"] <= 25 else "#F4B740" if fg_idx["score"] <= 45 else "#2FD08A" if fg_idx["score"] < 75 else "#F4B740"
            rs_parts.append(_rline("Fear & Greed (CNN)", f"<b style='color:{_fgc}'>{fg_idx['score']}</b> · {esc(fg_idx['rating'])} "
                                                          f"<span style='color:#8FA3C0;font-size:11px'>(hace 1 sem: {fg_idx.get('week', '—')} · 1 mes: {fg_idx.get('month', '—')})</span>"))
        rs_parts.append(_rline("Cartera de la semana", f"<b>{esc(cartera_txt)}</b>"))
        _ent = ", ".join(entering[:5]) or "—"
        _sal = ", ".join(leaving[:5]) or "—"
        rs_parts.append(_rline("Entrando (Mejorando)", f"<span style='color:#4CC2E0'>{esc(_ent)}</span>"))
        rs_parts.append(_rline("Saliendo (Debilitándose)", f"<span style='color:#F4B740'>{esc(_sal)}</span>"))
        if candidato:
            _t = candidato["top"]
            rs_parts.append(_rline("Candidato del sistema", f"<b style='color:#5B8CFF'>{_t['stock']['sym']}</b> (vía {_t['etf']}) — "
                                                             f"<span style='font-size:11px;color:#B9C9E2'>{esc(_t['why'])}</span>"))
        if contra_sigs:
            _cs = ", ".join(f"{s['sym']} ({s['n3']}/3)" for s in contra_sigs)
            rs_parts.append(_rline("Señal contraria 0/3", f"<span style='color:#7BD88F'>{esc(_cs)}</span> <span style='color:#8FA3C0;font-size:11px'>· tamaño pequeño, manga aparte</span>"))
        if suelo:
            _su = [r for r in suelo if r["pts"] >= 8 and not r["sangra"]]
            if _su:
                _st = ", ".join(f"{r['sym']} ({r['pts']}/10)" for r in _su[:4])
                rs_parts.append(_rline("Suelos potenciales", f"<span style='color:#2FD08A'>{esc(_st)}</span> <span style='color:#8FA3C0;font-size:11px'>· castigados, olvidados y dejando de sangrar</span>"))
        if excluded_di:
            rs_parts.append(_rline("Distribución oculta", f"<span style='color:#F4607A'>{esc(', '.join(excluded_di))}</span> — sube el precio, sale el dinero: fuera", "#F4607A"))
        if liq:
            rs_parts.append(_rline("Plan de liquidez", esc(liq)))
        if tperf:
            _c = tperf["cum"]
            _bc = _c["sys"] - _c.get("SPY", 0.0)
            _bcol = "#2FD08A" if _bc >= 0 else "#F4607A"
            rs_parts.append(_rline("Track record", f"sistema <b style='color:{_bcol}'>{_c['sys']*100:+.1f}%</b> vs SPY {_c.get('SPY', 0)*100:+.1f}% "
                                                    f"en {tperf['n']} semanas (<b style='color:{_bcol}'>{_bc*100:+.1f}%</b> de diferencia)"))
        rs_parts.append(_rline("Ojo esta semana", ojo))
        rs_parts.append("<div style='margin-top:14px;padding-top:8px;border-top:1px solid #2A3A55;font-size:9.5px;color:#7A8CA8;line-height:1.5'>"
                        "Contenido informativo y educativo. No es asesoramiento financiero personalizado ni recomendación de inversión (MiFID II / criterios CNMV). "
                        "Datos de cierre semanal (Stooq/Yahoo) con posible retardo. Rendimientos pasados no garantizan rendimientos futuros. "
                        "Los productos apalancados y CFD conllevan alto riesgo de pérdida rápida. Cada uno es responsable de sus decisiones."
                        "</div>")
        html.append("<div id='resumen-semanal' style='display:none;max-width:720px;margin:20px auto;background:#0A0E17;border:1px solid #24344F;"
                    "border-radius:12px;padding:22px 26px;color:#E8EEF9;font-family:inherit'>" + "".join(rs_parts) + "</div>")
    except Exception:
        # rollback: si el contenido falla, descartamos lo parcial y dejamos un resumen minimo,
        # para que las funciones de descarga (que van FUERA de este try) existan siempre.
        del html[_res_mark:]
        html.append("<div id='resumen-semanal' style='display:none;max-width:720px;margin:20px auto;background:#0A0E17;"
                    "border:1px solid #24344F;border-radius:12px;padding:22px 26px;color:#E8EEF9'>"
                    "<b>ROTACIÓN — resumen semanal</b><div class='note'>El resumen completo no se pudo generar esta semana. "
                    "Los datos están en las pestañas del terminal.</div></div>")
    # CSS de impresion + funciones de descarga: SIEMPRE presentes.
    # Clave del arreglo: antes de imprimir/capturar movemos #resumen-semanal a hijo directo de <body>;
    # si no, el selector de impresion ocultaba <main> entero y el PDF salia EN BLANCO.
    html.append("<style>@page{size:A4;margin:12mm}"
                "@media print{body.print-resumen>*:not(#resumen-semanal){display:none!important}"
                "body.print-resumen #resumen-semanal{display:block!important;-webkit-print-color-adjust:exact;print-color-adjust:exact;border:none;margin:0 auto}"
                "body.print-resumen{background:#0A0E17!important}}</style>")
    html.append("<script>"
                "function _resEl(){var r=document.getElementById('resumen-semanal');"
                "if(!r){alert('No hay resumen esta semana.');return null;}"
                "if(r.parentNode!==document.body){document.body.appendChild(r);}return r;}"
                "function descargarPDF(){var r=_resEl();if(!r)return;r.style.display='block';"
                "document.body.classList.add('print-resumen');"
                "setTimeout(function(){window.print();setTimeout(function(){r.style.display='none';document.body.classList.remove('print-resumen');},400);},80);}"
                "function _h2c(el,nombre,bg){function go(){html2canvas(el,{backgroundColor:bg||'#0A0E17',scale:2,useCORS:true}).then(function(c){"
                "var a=document.createElement('a');a.download=nombre;a.href=c.toDataURL('image/jpeg',0.92);a.click();"
                "if(el.id==='resumen-semanal'){el.style.display='none';}"
                "}).catch(function(e){alert('No se pudo generar el JPG: '+e);});}"
                "if(window.html2canvas){go();}else{var s=document.createElement('script');"
                "s.src='https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';"
                "s.onload=go;s.onerror=function(){alert('El JPG necesita internet (html2canvas). El botón PDF funciona sin conexión.');};"
                "document.head.appendChild(s);}}"
                "function descargarJPG(){var r=_resEl();if(!r)return;r.style.display='block';"
                f"_h2c(r,'resumen_rotacion_{_wk_lbl}.jpg');}}"
                "</script>")

    # ---- TOOLTIP UNIVERSAL: nombre del activo en CUALQUIER aparicion de un ticker en la pagina ----
    try:
        _tknames = {}
        for k, v in NAMES.items():
            try:
                _corto = v[1] if len(v) > 1 and v[1] else ""
                _largo = v[0] if v and v[0] else k
                _tknames[k.upper()] = (_corto + " · " + _largo) if (_corto and _corto != _largo) else _largo
            except Exception:
                continue
        for k, v in CARTERA_NOMBRES.items():
            _tknames.setdefault(k.upper(), v)
        for k, v in ALIAS2ETF.items():
            if v and k.upper() not in _tknames:
                _tknames[k.upper()] = f"→ se evalúa vía {v}"
        html.append("<script>var TKN=" + json.dumps(_tknames, ensure_ascii=False) + ";"
                    "(function(){"
                    # tooltip flotante
                    "var tip=document.createElement('div');"
                    "tip.style.cssText='position:fixed;z-index:9999;background:#111A2B;border:1px solid #3A5078;border-radius:6px;"
                    "padding:5px 10px;font-size:11.5px;color:#E8EEF9;pointer-events:none;display:none;max-width:280px;"
                    "box-shadow:0 4px 14px rgba(0,0,0,.55);line-height:1.4';"
                    "document.body.appendChild(tip);var hideT=null;"
                    "function showTip(el,txt){var r=el.getBoundingClientRect();tip.textContent=txt;tip.style.display='block';"
                    "var x=Math.min(r.left,window.innerWidth-290);var y=r.bottom+6;"
                    "if(y>window.innerHeight-56){y=r.top-34;}tip.style.left=Math.max(4,x)+'px';tip.style.top=y+'px';}"
                    # caminante del DOM: envuelve CADA aparicion de un ticker en nodos de texto
                    "var RX=new RegExp('\\\\b('+Object.keys(TKN).sort(function(a,b){return b.length-a.length;})"
                    ".map(function(k){return k.replace(/[-\\/\\\\^$*+?.()|[\\]{}]/g,'\\\\$&');}).join('|')+')\\\\b','g');"
                    "function walk(node){"
                    "if(node.nodeType===1){"
                    "var tg=node.tagName;"
                    "if(tg==='SCRIPT'||tg==='STYLE'||tg==='TEXTAREA'||tg==='CANVAS'||node.namespaceURI==='http://www.w3.org/2000/svg'||node.classList.contains('tkw')||node.classList.contains('bbgtape'))return;"
                    "for(var i=node.childNodes.length-1;i>=0;i--){walk(node.childNodes[i]);}"
                    "}else if(node.nodeType===3){"
                    "var t=node.nodeValue;if(!t||t.length<2)return;RX.lastIndex=0;if(!RX.test(t))return;RX.lastIndex=0;"
                    "var frag=document.createDocumentFragment();var last=0;var m;"
                    "while((m=RX.exec(t))!==null){"
                    "if(m.index>last){frag.appendChild(document.createTextNode(t.slice(last,m.index)));}"
                    "var sp=document.createElement('span');sp.className='tkw';sp.setAttribute('data-tk',m[1]);"
                    "sp.textContent=m[1];sp.style.cssText='border-bottom:1px dotted rgba(150,170,205,.45);cursor:help';"
                    "frag.appendChild(sp);last=m.index+m[1].length;}"
                    "if(last<t.length){frag.appendChild(document.createTextNode(t.slice(last)));}"
                    "node.parentNode.replaceChild(frag,node);}}"
                    "function marcar(){try{walk(document.querySelector('main')||document.body);}catch(e){}}"
                    "if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',marcar);}else{marcar();}"
                    # delegacion: raton y toque sobre los spans marcados (y fallback a elementos hoja)
                    "function chk(e){var el=e.target;if(!el||!el.getAttribute)return null;"
                    "var t=el.getAttribute('data-tk');"
                    "if(!t&&el.children&&el.children.length===0&&el.textContent){"
                    "t=el.textContent.replace(/[\\u25B2\\u25BC\\u2191\\u2193]/g,'').trim().toUpperCase();"
                    "if(t.length<2||t.length>16||!TKN[t])t=null;}"
                    "return t?{el:el,txt:t+' \\u2014 '+TKN[t]}:null;}"
                    "document.addEventListener('pointerover',function(e){var m=chk(e);"
                    "if(m){clearTimeout(hideT);showTip(m.el,m.txt);}"
                    "else{clearTimeout(hideT);hideT=setTimeout(function(){tip.style.display='none';},140);}});"
                    "document.addEventListener('click',function(e){var m=chk(e);"
                    "if(m){showTip(m.el,m.txt);clearTimeout(hideT);hideT=setTimeout(function(){tip.style.display='none';},2600);}},true);"
                    "window.addEventListener('scroll',function(){tip.style.display='none';},true);})();</script>")
    except Exception:
        pass

    html.append("<script>function mainView(v,b){document.getElementById('vista-ctx').style.display=(v=='ctx')?'contents':'none';"
                "document.getElementById('vista-op').style.display=(v=='op')?'contents':'none';"
                "var vg=document.getElementById('vista-vig');if(vg)vg.style.display=(v=='vig')?'contents':'none';"
                "var bg=document.getElementById('vista-bbg');if(bg)bg.style.display=(v=='bbg')?'contents':'none';"
                "var rd=document.getElementById('vista-rds');if(rd)rd.style.display=(v=='rds')?'contents':'none';"
                "var cl=document.getElementById('vista-cl');if(cl)cl.style.display=(v=='cl')?'contents':'none';"
                "var vd=document.getElementById('vista-vd');if(vd)vd.style.display=(v=='vd')?'contents':'none';"
                "var nw=document.getElementById('vista-news');if(nw)nw.style.display=(v=='news')?'contents':'none';"
                "document.querySelectorAll('.mainview').forEach(function(x){x.classList.remove('active')});b.classList.add('active');window.scrollTo(0,0);}</script>")
    html.append("</main>")
    gen = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    html.append("<footer>Actualizado: " + gen + " &middot; Herramienta de apoyo a la decision basada en fuerza relativa (estilo RRG) con datos de cierre reales "
                "de Stooq/Yahoo. No es asesoramiento financiero; los datos de fin de dia van con retardo y no sustituyen tu "
                "gestion de riesgo (tamano de posicion y stops).</footer>")
    html.append("<script>if('serviceWorker' in navigator){window.addEventListener('load',function(){navigator.serviceWorker.register('sw.js').catch(function(){});});}</script>")
    html.append("</body></html>")
    page = "".join(html)
    # Reordenar: el RRG (+ grafico TradingView) sube a la posicion del Radar de atencion; el radar baja a donde estaba el RRG.
    try:
        _rs = page.find("<div class='panel full'><h2>Grafico de rotacion relativa (RRG)</h2>")
        _re = page.find("<div class='panel full'><h2>Zona de entrada temprana")
        _rad = page.find("<div class='panel full'><h2>📡 Radar de atención")
        if 0 <= _rad < _rs < _re:
            seg = page[_rs:_re]
            page = page[:_rs] + page[_re:]
            page = page[:_rad] + seg + page[_rad:]
    except Exception:
        pass
    return page

# ======================================================================
# LA ESTELA — EXPORTADOR PUBLICO
# ----------------------------------------------------------------------
# Escribe site/estela/datos.json con lo que se publica. NO calcula nada:
# recibe los objetos que main() ya tiene en memoria. Coste del build: 0.
#
# La cara publica (static/estela/index.html) lee ese JSON y lo pinta.
# Un solo cerebro, dos caras.
#
# OJO: todo lo que entra aqui es PUBLICO de verdad. Cualquiera puede
# abrir el .json directamente. Lo que no quieras regalar, no lo metas.
# ======================================================================

ESTELA_DIR = SITE_DIR                     # La Estela manda en la raiz del sitio
ESTELA_JSON = os.path.join(ESTELA_DIR, "datos.json")

ESTELA_MARCA = "LA ESTELA"
ESTELA_LEMA = "El flujo confirma, la narrativa propone."
ESTELA_LINKS = {"substack": "", "telegram": "", "x": ""}   # rellenar con los tuyos

# Los cuatro andenes. Derivados de las fases que YA calcula compute_suelo
# y compute_graduados: no hay clasificacion nueva, solo agrupacion.
ANDENES = [
    ("dormido",    "Dormido",      "#5B7794", "Sin volumen, sin precio, sin nadie mirando."),
    ("removiendo", "Removiendose", "#8AA2BC", "Aparece volumen. El precio todavia quieto."),
    ("despertando", "Despertando", "#C8973F", "El dinero entra y el precio empieza a girar."),
    ("titular",    "Ya es titular", "#B85A55", "Esta en la prensa. Aqui ya llegas tarde."),
]
_FASE_ANDEN = {"SANGRA": "dormido", "DORMIDO": "dormido",
               "ACUMULACION": "removiendo", "PRE-DESPERTAR": "removiendo",
               "DESPERTANDO": "despertando"}
# Un sector "graduado" con esta extension sobre su media ya esta en portadas
ESTELA_EXT_TITULAR = 12.0
ESTELA_SEM_TITULAR = 5


def _est_nombre(sym):
    n = NAMES.get(sym)
    return (n[1] or n[0]) if n else sym


def _est_estela(rrg_row, n=8):
    """La ESTELA: fuerza relativa al indice de las ultimas n semanas.
    Es el rastro que deja el sector detras de si. Dato real (ratio del RRG),
    no adorno: si sube, el sector le esta ganando al S&P."""
    ser = (rrg_row or {}).get("ratio_series") or []
    vals = [v for v in ser[-n:] if v is not None]
    return [round(float(v), 2) for v in vals] if len(vals) >= 3 else None


def _est_flujo_frase(cmf):
    if cmf is None:
        return "Sin lectura fiable de flujo."
    if cmf < -0.05:
        return "Sigue saliendo dinero: mientras eso no pare, no hay trato."
    if cmf <= 0.05:
        return "El dinero esta quieto. Todavia no confirma nada."
    return "Ya entra dinero de verdad, con volumen detras."


def _est_lectura_suelo(r):
    """Compone la lectura en cristiano SOLO con ingredientes reales de la ficha."""
    p = []
    wk = r.get("wk_lag")
    if wk:
        p.append(f"Lleva {wk} semanas por detras del indice")
        if r.get("sil") is not None and r["sil"] >= 6:
            p[-1] += " y con un volumen anormalmente bajo: nadie lo mira"
        p[-1] += "."
    if r.get("hi52") is not None:
        p.append(f"Esta un {abs(round(r['hi52'] - 100, 1))} % por debajo de sus maximos de un ano.")
    if r.get("quieto") is not None and r.get("fase") in ("PRE-DESPERTAR", "ACUMULACION"):
        p.append("El precio apenas se ha movido todavia: esa es justo la parte interesante.")
    p.append(_est_flujo_frase(r.get("cmf")))
    if r.get("fase") == "DESPERTANDO":
        p.append("El giro ya esta en marcha: la ventana de entrada temprana se esta cerrando.")
    elif r.get("fase") == "PRE-DESPERTAR":
        p.append("Patron previo casi completo. Vigilar, no comprar: falta que el flujo confirme.")
    elif r.get("fase") == "SANGRA":
        p.append("Esta en la lista de espera, no en la de compra.")
    return " ".join(p)


def _est_lectura_grad(g):
    """Para los ya despertados se reutiliza el veredicto que el terminal ya
    redacta (compute_graduados), quitando el emoji."""
    v = str(g.get("ver") or "")
    for e in ("🔴", "🟢", "🟡", "⚪"):
        v = v.replace(e, "")
    v = v.strip()
    base = f"Desperto hace {g.get('sem')} semanas y desde el cruce lleva {g.get('pct'):+.1f} %."
    return (base + " " + (v[:1].upper() + v[1:] + "." if v else "")).strip()


def export_estela(rrg, flow, scores, suelo, graduados, despertares, centinela,
                  close_date, breadth=None, risk=None, salud=None, momento=None):
    """Escribe site/estela/datos.json. Devuelve la ruta."""
    rrg = rrg or {}
    flow = flow or {}
    vistos = set()
    items = []

    # --- 1) los ya despertados (mandan sobre la lectura de suelo) ---
    for g in (graduados or []):
        s = g.get("sym")
        if not s or s in vistos:
            continue
        ext = g.get("ext")
        sem = g.get("sem") or 0
        anden = "titular" if ((ext is not None and ext > ESTELA_EXT_TITULAR)
                              or sem >= ESTELA_SEM_TITULAR) else "despertando"
        items.append({"sym": s, "nombre": _est_nombre(s), "anden": anden,
                      "fase_raw": "GRADUADO", "cmf": g.get("cmf"), "sem": sem,
                      "pct": g.get("pct"), "ext": ext,
                      "estela": _est_estela(rrg.get(s)),
                      "huellas": [h for h in ([f"desperto hace {sem} sem",
                                               (f"extendido {ext} % sobre su media" if ext is not None else None),
                                               ("acumulacion extranjera" if g.get("aext") else None),
                                               ("flujo mejorando" if g.get("mejora") else None)]) if h],
                      "lectura": _est_lectura_grad(g)})
        vistos.add(s)

    # --- 2) los durmientes ---
    for r in (suelo or []):
        s = r.get("sym")
        if not s or s in vistos:
            continue
        items.append({"sym": s, "nombre": _est_nombre(s),
                      "anden": _FASE_ANDEN.get(r.get("fase"), "dormido"),
                      "fase_raw": r.get("fase"), "cmf": r.get("cmf"),
                      "sem": r.get("wk_lag"), "pct": None, "ext": None,
                      "pts": r.get("pts"), "pre": r.get("pre"),
                      "estela": _est_estela(rrg.get(s)),
                      "huellas": [str(h) for h in (r.get("det") or [])][:5],
                      "lectura": _est_lectura_suelo(r)})
        vistos.add(s)

    # --- 2b) el cuadro de momento tapa el limbo ---
    # Sin esto el anden "Ya es titular" se alimenta solo de graduados (cruces de <=4
    # semanas), asi que un sector que lleva meses corriendo NO PUEDE aparecer nunca.
    # Es justo la casilla que mas vende: "aqui ya llegas tarde".
    # Tope por anden: con ~55 simbolos, MADURO solo ya inflaria "Ya es titular" hasta
    # hacerlo ilegible. La rejilla publica es una seleccion, no un volcado.
    _cupo = {"titular": 6, "despertando": 4, "removiendo": 4}
    for r in sorted(((momento or {}).get("rows") or []),
                    key=lambda x: (-(x.get("pm") or 0), -(x.get("sem") or 0))):
        s_ = r.get("sym")
        if not s_ or s_ in vistos:
            continue
        cj, sem_, ext_ = r.get("caja"), r.get("sem") or 1, r.get("ext")
        if cj == "MADURO":
            anden = "titular"
        elif cj == "EN MARCHA":
            anden = ("titular" if ((ext_ is not None and ext_ > ESTELA_EXT_TITULAR)
                                   or sem_ >= ESTELA_SEM_TITULAR) else "despertando")
        elif cj == "GIRANDO" and sem_ >= 2:
            anden = "removiendo"          # aviso temprano: acelera, precio aun flojo
        else:
            continue                       # CAYENDO no se publica
        if _cupo.get(anden, 0) <= 0:
            continue
        _cupo[anden] -= 1
        items.append({"sym": s_, "nombre": _est_nombre(s_), "anden": anden,
                      "fase_raw": "MOMENTO/" + str(cj), "cmf": r.get("cmf"),
                      "sem": sem_, "pct": r.get("m12"), "ext": ext_,
                      "estela": _est_estela(rrg.get(s_)),
                      "huellas": [h for h in [f"momento 12-1 {r.get('m12'):+.1f} %",
                                              f"percentil {r.get('pm')} de fuerza, {r.get('pa')} de aceleracion",
                                              f"{sem_} sem seguidas en {cj.lower()}",
                                              ("no salia en ningun otro panel" if r.get("huerfano") else None)] if h],
                      "lectura": str(r.get("ver") or "")})
        vistos.add(s_)

    andenes = []
    for aid, tit, col, desc in ANDENES:
        andenes.append({"id": aid, "titulo": tit, "color": col, "desc": desc,
                        "items": [i for i in items if i["anden"] == aid]})

    # --- 3) semaforo ---
    sem = None
    if centinela:
        sem = {"estado": centinela.get("estado"), "color": centinela.get("col"),
               "confirmado": bool(centinela.get("confirmado")), "anterior": centinela.get("prev"),
               "que": centinela.get("que"), "invalidacion": centinela.get("inval"),
               "spread": centinela.get("spread"), "d3": centinela.get("d3")}

    # --- 4) fichas vivas (la llamada; la gestion NO se publica) ---
    fichas = []
    for f in ((despertares or {}).get("activas") or []):
        fichas.append({"sym": f.get("sym"), "nombre": _est_nombre(f.get("sym")),
                       "fase": f.get("fase"), "fecha": f.get("date"),
                       "px0": f.get("px0"), "inval": f.get("inval"),
                       "ret": f.get("ret"), "vs": f.get("vs"),
                       "sesiones": f.get("n_ses"), "faltan": f.get("faltan"),
                       "rota": bool(f.get("roto")),
                       "huellas": [str(h) for h in (f.get("huellas") or [])][:4]})

    cuadro = None
    if momento and momento.get("cajas"):
        cuadro = {c: [{"sym": r["sym"], "nombre": _est_nombre(r["sym"]), "sem": r["sem"],
                       "m12": r["m12"], "pm": r["pm"], "pa": r["pa"]}
                      for r in v[:8]]
                  for c, v in momento["cajas"].items()}

    # --- 5) marcador ---
    lb = (despertares or {}).get("libro")
    marcador = None
    if lb:
        marcador = {"n": lb.get("n"), "aciertos": lb.get("gan"), "pct": lb.get("p"),
                    "ic_lo": lb.get("lo"), "ic_hi": lb.get("hi"), "media": lb.get("avg"),
                    "mediana": lb.get("med"), "vs_spy": lb.get("avg_vs"),
                    "invalidadas": lb.get("rotas"), "maduro": bool(lb.get("maduro"))}

    # --- 6) archivo (fichas ya cerradas, con los fallos) ---
    archivo = []
    for c in ((despertares or {}).get("cadena") or [])[:40]:
        archivo.append({"sym": c.get("sym"), "nombre": _est_nombre(c.get("sym")),
                        "fecha": c.get("date"), "fase": c.get("fase"),
                        "ret": c.get("ret"), "vs": c.get("vs"),
                        "gana": bool(c.get("gana")), "rota": bool(c.get("roto"))})

    # --- 7) dia del ciclo semanal ---
    try:
        _dow = dt.date.today().weekday()          # 0=lunes
    except Exception as _dege:
        _deg("export_estela:10940", _dege)
        _dow = 0

    payload = {
        "marca": ESTELA_MARCA, "lema": ESTELA_LEMA, "links": ESTELA_LINKS,
        "cierre": str(close_date),
        "generado": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "dia_ciclo": _dow,
        "semaforo": sem, "andenes": andenes, "fichas": fichas,
        "marcador": marcador, "archivo": archivo, "cuadro": cuadro,
        "amplitud": breadth, "riesgo": risk,
        "n_sectores": len(items),
        "salud": [{"origen": o, "texto": t, "veces": n} for o, t, n in (salud or [])][:12],
        "aviso": ("Contenido informativo y educativo. No es asesoramiento financiero ni una "
                  "recomendacion personalizada de inversion. Rentabilidades pasadas no "
                  "garantizan resultados futuros."),
    }
    os.makedirs(ESTELA_DIR, exist_ok=True)
    with open(ESTELA_JSON, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
    return os.path.abspath(ESTELA_JSON)


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    print("=" * 56)
    print(" ROTACION - Smart-Money Flow Terminal (escritorio)")
    print("=" * 56)
    df, daily, sources = download_all()
    df = add_sinteticos(df)
    if BENCH not in df.columns or len(df) < 30:
        print("\nNo hay suficientes datos comunes para calcular. Reintenta mas tarde.")
        return
    print(f"\nMatriz alineada: {len(df)} semanas x {len(df.columns)} activos.")

    rrg = compute_rrg(df)
    alerts = build_alerts(rrg)
    breadth, risk = breadth_risk(rrg)
    flow = compute_volume_flow(daily)
    spy_flow = compute_volume_flow(daily, only=BENCH).get(BENCH)
    heatmap = compute_heatmap(daily)
    scores = compute_scores(df, rrg, daily, flow)
    early = compute_early(df, rrg)
    meanrev = compute_mean_reversion(SECTORS + THEMATIC + EXTRA)
    fg_idx = fetch_fear_greed()
    probs = compute_probabilities(df, rrg)
    fred, fred_sig = fetch_fred()
    regime = detect_regime(df, rrg, risk, fred_sig)
    buy, avoid = conviction(rrg, regime)
    bt = backtest(df, rrg, hold=("leading", "improving")) if BACKTEST else None
    bt2 = backtest(df, rrg, hold=("leading", "improving", "weakening")) if BACKTEST else None
    long_close, long_src, long_hl = fetch_long_close()
    # FIX caida-desde-ATH: Stooq llega con retraso -> se refresca con Yahoo, usando el MISMO activo
    # que la fuente real de la serie (si cayo al fallback SPY, refrescar con SPY: mezclar escalas
    # SPY ~740 / ^GSPC ~7400 corromperia el drawdown). El pico usa Highs intradia.
    _ysym_ref = "SPY" if "spy" in str(long_src).lower() else "^GSPC"
    long_close, long_hl = refrescar_con_yahoo(long_close, long_hl, _ysym_ref)
    es_fut = fetch_es_futuro()
    if not es_fut:
        _avisar("es_futuro", "futuro ES no disponible: la referencia casi-24h no se muestra este build", nivel="info")
    # SPY entra aqui aunque no sea un "sector": es la vara de medir del panel de cobertura
    # (¿se cubren MAS en semis que en el mercado entero?). Sin el, ese panel no tiene contra que comparar.
    _uni_opt = [s for s in ([BENCH] + SECTORS + THEMATIC + EXTRA) if s in df.columns]
    print("  OPTIONS DESK: descargando cadenas de opciones de Yahoo ...")
    options = compute_options(_uni_opt, flow=flow, daily=daily)
    _n_opt = len(options) if options else 0
    print(f"  OPTIONS DESK: {_n_opt} ETFs con datos de opciones")
    _cobertura = None
    try:
        _cobertura = compute_cobertura(options, rrg=rrg, flow=flow)
        if _cobertura:
            for _c in _cobertura["cestas"]:
                print(f"  🛡 Cobertura {_c['titulo']}: {_c['estado']}"
                      + (f" (percentil {_c['rank']}, n={_c['n_min']})" if _c["rank"] is not None else ""))
    except Exception as _e_cob:
        _avisar("cobertura", f"panel de cobertura no disponible: {_e_cob}")
        _cobertura = None
    if _n_opt == 0:
        _avisar("options", "OPTIONS DESK vacío: Yahoo no devolvió ninguna cadena (¿rate limit / sin conexión?); paneles de opciones ausentes este build")
    elif _n_opt < max(5, len(_uni_opt) // 3):
        _avisar("options", f"OPTIONS DESK parcial: solo {_n_opt}/{len(_uni_opt)} ETFs con cadena — posible rate limit de Yahoo a mitad de descarga")
    tau = calendario_tau()
    analogos = compute_analogos(long_close) if long_close is not None else None
    dd, dd_meta = (drawdown_stats(long_close, DD_THRESHOLDS, hl=long_hl) if long_close is not None else (None, None))
    plan = cash_plan(long_close, hl=long_hl) if long_close is not None else None
    season = {}
    sp_se = compute_seasonality(long_close) if long_close is not None else None
    if sp_se:
        season["S&P 500"] = sp_se
    print("  Estacionalidad: descargando Nasdaq y Russell (historico largo)...")
    nq_close, _, _ = _fetch_long("^ndx", "QQQ", "^NDX")
    nq_close, _ = refrescar_con_yahoo(nq_close, None, "^NDX")
    nq_se = compute_seasonality(nq_close) if nq_close is not None else None
    if nq_se:
        season["Nasdaq 100"] = nq_se
    rut_close, _, _ = _fetch_long("^rut", "IWM", "^RUT")
    rut_close, _ = refrescar_con_yahoo(rut_close, None, "^RUT")
    rut_se = compute_seasonality(rut_close) if rut_close is not None else None
    if rut_se:
        season["Russell 2000"] = rut_se
    # Dow Jones: el indice "value" clasico (industriales, sin la distorsion de las megacaps tech).
    # Util justo por eso: cuando el Dow y el Nasdaq divergen, te esta contando la rotacion de estilo.
    dji_close, _, _ = _fetch_long("^dji", "DIA", "^DJI")
    dji_close, _ = refrescar_con_yahoo(dji_close, None, "^DJI")
    dji_se = compute_seasonality(dji_close) if dji_close is not None else None
    if dji_se:
        season["Dow Jones"] = dji_se
    # VIX: la estacionalidad del MIEDO. OJO con la fuente: sin fallback a ETF, porque VIXY y compania
    # son futuros de VIX (sufren contango y decaen brutalmente) — su estacionalidad NO es la del VIX
    # al contado y meteria un dato falso. Solo Stooq -> Yahoo, o no se pinta.
    try:
        vix_close, _vsrc, _ = _fetch_long("^vix", None, "^VIX")
        vix_close, _ = refrescar_con_yahoo(vix_close, None, "^VIX")
        vix_se = compute_seasonality(vix_close) if vix_close is not None else None
        if vix_se:
            season["VIX (miedo)"] = vix_se
            print(f"  Estacionalidad VIX: {vix_se['years']} años ({_vsrc})")
        else:
            _avisar("season.vix", "sin histórico suficiente del VIX: la columna de estacionalidad del miedo no se pinta")
    except Exception as _e_vix:
        _avisar("season.vix", f"VIX no disponible para estacionalidad: {_e_vix}")
    if not season:
        season = None
    fx = fetch_fx()
    _stk_univ = fetch_stock_universe() if STOCK_LEADERS else {}
    leaders, leaders_n, sector_breadth = compute_rs_leaders(_stk_univ) if STOCK_LEADERS else (None, 0, {})
    # --- amplitud estilo McClellan sobre ese mismo universo (v4.4): 0 descargas extra
    _mcc = None
    try:
        _mcc = compute_mcclellan(_stk_univ)
        if _mcc:
            _bench_d = None
            try:
                _bench_d = daily.get(BENCH, {}).get("Close") if isinstance(daily, dict) else None
            except Exception:
                _bench_d = None
            if _bench_d is None:
                _bench_d = df[BENCH] if BENCH in df.columns else None
            _mcc["umbral_pct"] = mcc_umbral_percentil(_mcc["osc"], 10.0)
            _mcc["bt_nyse"] = mcc_backtest(_mcc["osc"], _bench_d, umbral=MCC_UMBRAL)
            if _mcc["umbral_pct"] is not None and abs(_mcc["umbral_pct"] - MCC_UMBRAL) > 5:
                _mcc["bt_pct"] = mcc_backtest(_mcc["osc"], _bench_d, umbral=_mcc["umbral_pct"])
            print(f"  Amplitud McClellan: {_mcc['ultimo']:+.1f} "
                  f"({_mcc['n_acciones']} acciones, {_mcc['n_sesiones']} sesiones) "
                  f"· disparos historicos: {_mcc['bt_nyse']['n_disparos']}")
    except Exception as _e_mcc:
        _avisar("mcclellan", f"oscilador de amplitud no calculado: {_e_mcc}")
    print("  Vigilancia: descargando acciones de la watchlist...")
    watch = compute_watchlist(WATCHLIST)
    # --- CENTINELA y compañía ANTES del snapshot: así la IA automática conoce el régimen ---
    _giro = compute_giro_intradia(daily, rrg)
    _suelo = None
    _cascada = None
    try:
        _cascada = compute_cascada(df, rrg, flow)
        if _cascada:
            print(f"  🔗 Cascada IA: lidera {_cascada['lider_corto']} — {_cascada['sentido']}")
    except Exception as _e_casc:
        _avisar("cascada", f"mapa de cascada IA no disponible: {_e_casc}")
    try:
        _suelo = compute_suelo(df, rrg, scores, flow, meanrev)
    except Exception:
        _suelo = None
    _despertares = None
    try:
        _ult_cierre = str((daily.get(BENCH).index[-1].date()) if daily.get(BENCH) is not None else df.index[-1].date())
        _macro_hoy = _sello_macro(df, rrg, flow, _cascada)
        _despertares = update_despertares(_suelo, daily, _ult_cierre, bench=BENCH, macro=_macro_hoy)
        if _despertares:
            _lb = _despertares.get("libro")
            print(f"  📒 Libro de despertares: {len(_despertares['activas'])} fichas activas · "
                  + (f"{_lb['n']} maduras, acierto {_lb['p']}% (IC {_lb['lo']}-{_lb['hi']}%)" if _lb else "aún ninguna madura"))
            _fm = _despertares.get("familias")
            if _fm:
                print(f"     · por APUESTAS independientes: {_fm['n_familias']} (de {_fm['n_filas']} fichas) "
                      f"· acierto {_fm['p']}% (IC {_fm['lo']}-{_fm['hi']}%) · media {_fm['avg']:+.1f}%")
                print(f"     · concentracion: {_fm['concentracion']}% del resultado lo aporta '{_fm['top']}'"
                      + ("" if _fm['maduro'] else "  [muestra AUN NO madura: <12 apuestas]"))
    except Exception as _e_dsp:
        _avisar("despertares", f"libro de despertares no disponible: {_e_dsp}")
        _despertares = None
    _graduados = None
    try:
        _graduados = compute_graduados(df, rrg, flow)
        if _graduados:
            print("  🌅 Recién despertados: " + ", ".join(f"{g['sym']}({g['sem']}s, {g['pct']:+.1f}%)" for g in _graduados[:6]))
    except Exception:
        _graduados = None
    _momento = None
    try:
        _momento = compute_momento(df, rrg, flow, suelo=_suelo, graduados=_graduados)
        if _momento:
            _cj = {c: len(v) for c, v in _momento["cajas"].items()}
            print(f"  📐 Cuadro de momento: {_cj['EN MARCHA']} en marcha · {_cj['GIRANDO']} girando · "
                  f"{_cj['MADURO']} maduros · {_cj['CAYENDO']} cayendo")
            if _momento["huerfanos"]:
                print("     ⚠ corren y no salen en ningún otro panel: "
                      + ", ".join(r["sym"] for r in _momento["huerfanos"][:8]))
    except Exception as _e_mom:
        _avisar("momento", f"cuadro de momento no disponible: {_e_mom}")
        _momento = None
    _dix = fetch_dix() if DIX_ON else None
    if _dix:
        print(f"  DIX (dark pools): {_dix['m5']}% media 5d ({_dix['senal']}) · {_dix['fecha']}")
    elif DIX_ON:
        print("  DIX (dark pools): sin respuesta de SqueezeMetrics — el terminal sigue sin él.")
    _centinela = None
    try:
        _centinela = compute_centinela(df, rrg, flow, _suelo, dix=_dix, plan=plan)
        if _centinela:
            print(f"\n  🛰️ CENTINELA: {_centinela['estado']}"
                  + (" (confirmado)" if _centinela["confirmado"] else " (nuevo — confirma el próximo cierre)")
                  + f" · spread beta−def {_centinela['spread']:+.2f} · Δ3s {_centinela['d3']:+.2f}")
            if _centinela.get("despierta"):
                print(f"     DESPERTANDO: {', '.join(_centinela['despierta'])}")
            if _centinela.get("acecho"):
                print(f"     PRE-DESPERTAR/ACUMULACIÓN: {', '.join(_centinela['acecho'])}")
    except Exception as _e:
        print(f"  CENTINELA: no calculado ({_e})")
    _desks = []
    for _dc in DESKS_POKER:
        try:
            _dk = compute_rebote_desk(df, daily, rrg, flow, scores, leaders, _giro,
                                      prefs=_dc["prefs"], lead_keys=_dc.get("lead_keys"), desk_id=_dc["id"])
            if _dk:
                # análogos de flujo: para SEMIS se mide el precio de SOXX contra el flujo de SMH
                # (el par del post de r/Daytrading); para el resto, el propio ETF del desk.
                try:
                    _sy = _dk.get("sym")
                    if _sy in ("SMH", "SOXX"):
                        # par del post: PRECIO de SOXX contra el FLUJO de SMH (si ambos llegaron)
                        _pp = "SOXX" if "SOXX" in (daily or {}) else _sy
                        _pf = "SMH" if "SMH" in (daily or {}) else _sy
                    else:
                        _pp = _pf = _sy
                    if _pp in (daily or {}) and _pf in (daily or {}):
                        _dk["analogos"] = compute_analogos_flujo(daily, _pp, _pf, n_sesiones=2)
                except Exception:
                    _dk["analogos"] = None
                _desks.append(_dk)
        except Exception:
            continue
    _snap_main = state_summary(rrg, risk, regime, breadth, plan, flow)
    if _centinela:
        _snap_main += (f"\nCENTINELA (reloj de regimen): {_centinela['estado']}"
                       + (" CONFIRMADO" if _centinela["confirmado"] else " sin confirmar (1 cierre)")
                       + f", spread alta-beta menos defensivos {_centinela['spread']:+.2f} (Δ3 semanas {_centinela['d3']:+.2f}).")
        if _centinela.get("despierta"):
            _snap_main += f" Explosivos DESPERTANDO: {', '.join(_centinela['despierta'][:5])}."
        if _centinela.get("acecho"):
            _snap_main += f" En pre-despertar/acumulacion: {', '.join(_centinela['acecho'][:5])}."
    if _graduados:
        _snap_main += "\nRecien despertados (graduados de la cueva): " + ", ".join(
            f"{g['sym']} (desperto hace {g['sem']} sem, {g['pct']:+.1f}% desde el cruce, ext {g.get('ext')}%)" for g in _graduados[:5]) + "."
    _noct_ia = [(s3, f3.get("noct20")) for s3, f3 in (flow or {}).items() if f3.get("acum_ext")]
    if _noct_ia:
        _snap_main += "\nAcumulacion extranjera (gap nocturno 20 sesiones con CMF<=0, el CMF americano no la ve): " + ", ".join(
            f"{s3} {n3:+.1f}%" for s3, n3 in sorted(_noct_ia, key=lambda x: -(x[1] or 0))[:5]) + "."
    if _dix:
        _snap_main += f"\nDIX dark pools: {_dix['m5']}% media 5d ({_dix['senal']}, percentil {_dix['pct']} del año)."
    # --- piezas nuevas para que el resumen las vea: opciones, calendario tau, analogos y eventos con fecha ---
    if tau:
        _snap_main += (f"\nCALENDARIO tau (ciclo intramensual de momentum): estado {tau['estado']}. "
                       f"Ventana de presion vendedora sobre losers {tau['win_ini']}-{tau['win_fin']}; "
                       f"zona de rebote {tau['reb_ini']}-{tau['reb_fin']}.")
    if analogos:
        _a3 = analogos.get("m3", {})
        _snap_main += (f"\nANALOGOS historicos desde {analogos.get('desde')}: en las {analogos.get('n')} situaciones mas parecidas "
                       f"a hoy, a 3 meses el mercado acabo positivo el {_a3.get('pos')}% de las veces "
                       f"(mediana {_a3.get('med')}%). Es frecuencia historica, no prediccion.")
    if options:
        _div = [f"{s} ({o['diverg']})" for s, o in options.items() if o.get("diverg")]
        _mied = [s for s, o in options.items() if o.get("pcr_vol") and o["pcr_vol"] > 1.3 and not o.get("iliquido")]
        if _div:
            _snap_main += "\nOPCIONES - divergencias con el flujo de contado: " + "; ".join(_div[:8]) + "."
        if _mied:
            _snap_main += "\nOPCIONES - miedo/proteccion (put/call alto, liquido): " + ", ".join(_mied[:8]) + "."
    try:
        _ev = [f"{f}: {t}" for f, t in (EVENTOS_MERCADO or []) if dt.date.fromisoformat(f) >= dt.date.today() - dt.timedelta(days=1)]
        if _ev:
            _snap_main += "\nEVENTOS CON FECHA proximos: " + " | ".join(_ev[:6]) + "."
    except Exception:
        pass
    ai_text = ai_commentary(_snap_main)
    ia_auto = run_ia_auto(_snap_main, str(df.index[-1].date()))
    if ai_text:
        print("\n  Comentario IA generado.")

    # resumen en consola
    print("\n--- ALERTAS DE ROTACION ---")
    if alerts:
        for s, k, t in alerts:
            print(f"  [{k.upper():4s}] {s:5s} {t}")
    else:
        print("  Sin giros relevantes; liderazgo estable.")
    print(f"\n  Apetito de riesgo: {risk['label']} ({risk['score']:+})")
    print(f"  Amplitud: {breadth['leaders']}% con fuerza>indice | {breadth['uptrend']}% en tendencia")
    print(f"  Regimen macro{' (con FRED)' if fred else ''}: {regime['label']}")
    if buy:   print(f"  Alta conviccion alcista: {', '.join(buy)}")
    if avoid: print(f"  Evitar/reducir: {', '.join(avoid)}")
    divs = [s for s, d in (flow or {}).items() if d.get("diverg")]
    if divs: print(f"  Divergencias de flujo: {', '.join(divs)}")
    if bt:   print(f"  Backtest: estrategia {bt['tot_s']:+}% vs {BENCH} {bt['tot_b']:+}% ({bt['weeks']} sem)")
    if plan: print(f"  Caida actual del {BENCH} desde maximos: {plan['dd']}%")

    # avisos automaticos (Telegram / webhook) si hay giros, divergencias o caidas alcanzadas
    lines = []
    if _centinela and _centinela.get("prev") and _centinela["prev"] != _centinela["estado"]:
        lines.append(f"• 🛰️ CENTINELA cambia de régimen: {_centinela['prev']} → {_centinela['estado']} "
                     f"(spread {_centinela['spread']:+.2f}) — un cierre es ruido: confirmar el próximo viernes")
    if _centinela and _centinela["estado"] in ("REENTRADA", "ACECHO") and _centinela.get("despierta"):
        lines.append(f"• 🌅 Explosivos DESPERTANDO desde el suelo: {', '.join(_centinela['despierta'][:5])}")
    for _r in (_suelo or []):
        if _r.get("fase") == "PRE-DESPERTAR" and _r["sym"] in SECTORES_EXPLOSIVOS:
            lines.append(f"• 🌱 {_r['sym']}: patrón pre-despertar {_r.get('pre', 0)}/4 con el precio aún quieto")
    for s, k, t in alerts:
        lines.append(f"• {s}: {t}")
    for s, d in (flow or {}).items():
        if d.get("diverg"):
            lines.append(f"• {s}: {d['diverg']} (flujo de volumen)")
    if plan:
        for r in plan["rungs"]:
            if r["hit"]:
                lines.append(f"• Caida −{r['thr']}% del {BENCH} ALCANZADA → plan: desplegar {r['pct']}%")
    if lines:
        msg = (f"ROTACION {dt.date.today()} — {risk['label']} — {regime['label']}\n"
               + "\n".join(lines))
        if notify(msg):
            print("\nAviso enviado.")

    html = build_html(df, rrg, alerts, breadth, risk, regime, buy, avoid, sources, fred, flow=flow, bt=bt,
                      dd=dd, dd_meta=dd_meta, plan=plan, fx=fx, long_src=long_src, ai_text=ai_text, leaders=leaders, leaders_n=leaders_n, bt2=bt2, heatmap=heatmap, scores=scores, probs=probs, season=season, early=early, sector_breadth=sector_breadth, meanrev=meanrev, nq_close=nq_close, fg_idx=fg_idx, spy_flow=spy_flow, watch=watch, giro=_giro, desks=_desks, dix=_dix, suelo_pre=_suelo, centinela=_centinela, graduados=_graduados, daily=daily, ia_auto=ia_auto, tau=tau, analogos=analogos, es_fut=es_fut, options=options, despertares=_despertares, cascada=_cascada, momento=_momento, cobertura=_cobertura, mcc=_mcc)
    os.makedirs(SITE_DIR, exist_ok=True)
    # copiar archivos estaticos (iconos, manifest, service worker) al sitio
    if os.path.isdir(STATIC_DIR):
        import shutil
        for root, _, files in os.walk(STATIC_DIR):
            rel = os.path.relpath(root, STATIC_DIR)
            dest = os.path.join(SITE_DIR, rel) if rel != "." else SITE_DIR
            os.makedirs(dest, exist_ok=True)
            for fn in files:
                shutil.copy2(os.path.join(root, fn), os.path.join(dest, fn))
    out = os.path.abspath(OUTPUT_HTML)
    os.makedirs(os.path.dirname(out), exist_ok=True)   # site/pro/ puede no existir aun
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nPanel generado: {out}")
    # --- VERSION LITE / PUBLICA (v4.3) -------------------------------------
    # Se genera con los datos que YA estan en memoria: cero descargas extra.
    # Va en site/lite/ para no tocar nada de lo que ya funciona.
    try:
        _tp = None
        try:
            _recs = json.load(open(TRACK_FILE, encoding="utf-8")) if os.path.exists(TRACK_FILE) else []
            _tp = compute_track_perf(_recs) if _recs else None
        except Exception as _dege:
            _deg("lite:track_load", _dege)
        _lite = build_html_lite(str(df.index[-1].date()), centinela=_centinela,
                                scores=scores, flow=flow, df=df, track=_tp,
                                dd=dd, regime=regime, risk=risk)
        _lp = os.path.abspath(LITE_HTML)
        os.makedirs(os.path.dirname(_lp), exist_ok=True)
        with open(_lp, "w", encoding="utf-8") as f:
            f.write(_lite)
        print(f"Version publica (lite): {_lp}  [{len(_lite) // 1024} KB]")
    except Exception as _e_lite:
        _avisar("lite", f"version publica no generada: {_e_lite}")

    # --- EL TERMINAL MANDA EN LA RAIZ (v4.1) -------------------------------
    # Antes la raiz del sitio la ocupaba la pagina publica de La Estela, que
    # se rellenaba leyendo datos.json. Si ese JSON no salia completo, la raiz
    # mostraba el diseno con TODOS los campos vacios y el terminal de verdad
    # quedaba escondido en /pro/. Ahora la raiz ES el terminal completo:
    #   ...github.io/Terminal-PeVR/        -> terminal completo
    #   ...github.io/Terminal-PeVR/pro/    -> el mismo, para no romper enlaces
    try:
        _raiz = os.path.abspath(os.path.join(SITE_DIR, "index.html"))
        with open(_raiz, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Terminal publicado tambien en la raiz: {_raiz}")
    except Exception as _e_raiz:
        _avisar("publicar", f"no se pudo escribir la raiz del sitio: {_e_raiz}")
    # --- LA ESTELA: DESACTIVADA (v4.1) -------------------------------------
    # La funcion export_estela() sigue en el archivo, intacta. Solo se ha
    # dejado de LLAMAR. Para reactivarla algun dia basta con quitar el "if 0:"
    # y devolver la raiz a la pagina publica. No se ha borrado ni un calculo.
    if 0:   # <- poner "if 1:" para volver a publicar La Estela
        try:
            _est = export_estela(rrg, flow, scores, _suelo, _graduados, _despertares, _centinela,
                                 str(df.index[-1].date()), breadth=breadth, risk=risk,
                                 salud=SALUD_BUILD, momento=_momento)
            print(f"Web publica (La Estela): {_est}")
        except Exception as _e_est:
            _avisar("estela", f"datos de la web publica no generados: {_e_est}")
    # --- resumen de salud del build (tambien queda en rotacion.log) ---
    if SALUD_BUILD:
        print(f"\n  🩺 SALUD DEL BUILD: {len(SALUD_BUILD)} avisos — detalle en la pestaña PRO y en rotacion.log")
        for _o, _t, _n in SALUD_BUILD[:10]:
            print(f"     · [{_o}] {_t}" + (f" (×{_n})" if _n > 1 else ""))
        if len(SALUD_BUILD) > 10:
            print(f"     · ... y {len(SALUD_BUILD) - 10} más")
    _dg = _deg_resumen(8)
    if _dg:
        print(f"\n  🔎 DEGRADACIONES SILENCIOSAS: {sum(x[1] for x in _dg)} en {len(_DEG)} puntos de cálculo")
        for _o, _n, _e in _dg:
            print(f"     · {_o} ×{_n}  ({_e[:60]})")
    else:
        print("\n  🩺 SALUD DEL BUILD: limpio — sin datos degradados ni descartados")
    if scores:
        print("\n  PUNTUACION (de mayor a menor) — entra en 4-5/5, vende <=2/5:")
        for r in scores[:12]:
            acc = " ⚡" if r["obv_cross"] else ""
            ticks = "".join("✓" if v else "·" for _, v in r["parts"])
            print(f"    {r['sym']:5s} {r['score']}/5  [{ticks}]  mom3m {r['abs_mom']:+5.1f}%{acc}")
    if not os.environ.get("CI"):     # en local abre el navegador; en GitHub no
        try:
            webbrowser.open("file://" + out)
            print("Abriendo en el navegador...")
        except Exception:
            print("Abre el archivo manualmente en tu navegador.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelado.")
