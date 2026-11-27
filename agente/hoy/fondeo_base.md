# Fondeo · línea base (plan de Pe, 1.00 % por operación; cierre del viernes: no)
- Mínimo + Flujo verde (CMF > 0,025): SPX, NAS, EURJPY, riesgo entero.
- Caída desde el máximo (−2,4 % del máximo de 20 días, stop 3,6 %, 1 R / 2 R): NAS, SPX, medio riesgo cada una.

## SPX
```
            tramo   N      R     t  acierto  peor_racha  ops_año
             todo 351  0.071  1.40       63           8     15.0
          2003-15 182 -0.006 -0.08       57           8      NaN
          2016-22 108  0.123  1.38       69           4      NaN
          2023-26  61  0.209  1.82       72           3      NaN
   aprender ≤2018 230  0.049  0.78       61           8      NaN
comprobar 2019-22  60  0.015  0.12       62           4      NaN
    caja 2023-hoy  61  0.209  1.82       72           3      NaN
```
## NAS
```
            tramo   N     R    t  acierto  peor_racha  ops_año
             todo 357 0.095 1.86       63           5     15.3
          2003-15 191 0.014 0.21       59           5      NaN
          2016-22 102 0.126 1.34       65           3      NaN
          2023-26  64 0.284 2.42       72           4      NaN
   aprender ≤2018 231 0.048 0.75       60           5      NaN
comprobar 2019-22  62 0.072 0.62       65           3      NaN
    caja 2023-hoy  64 0.284 2.42       72           4      NaN
```
## EURJPY
```
            tramo   N      R     t  acierto  peor_racha  ops_año
             todo 319 -0.017 -0.33       60           8     14.6
          2003-15 164 -0.151 -2.14       54           8      NaN
          2016-22  86 -0.010 -0.09       57           5      NaN
          2023-26  69  0.292  2.70       75           3      NaN
   aprender ≤2018 192 -0.111 -1.67       56           8      NaN
comprobar 2019-22  58 -0.076 -0.56       53           5      NaN
    caja 2023-hoy  69  0.292  2.70       75           3      NaN
```
## CAÍDA NAS
```
            tramo   N     R    t  acierto  peor_racha  ops_año
             todo 424 0.121 2.52       57           6     18.1
          2003-15 210 0.105 1.54       57           4      NaN
          2016-22 142 0.099 1.16       55           5      NaN
          2023-26  72 0.209 1.91       62           3      NaN
   aprender ≤2018 254 0.106 1.74       57           6      NaN
comprobar 2019-22  98 0.092 0.87       54           4      NaN
    caja 2023-hoy  72 0.209 1.91       62           3      NaN
```
## CAÍDA SPX
```
            tramo   N     R    t  acierto  peor_racha  ops_año
             todo 348 0.096 1.99       58           5     14.9
          2003-15 186 0.067 1.00       55           5      NaN
          2016-22 105 0.122 1.31       59           5      NaN
          2023-26  57 0.144 1.38       67           3      NaN
   aprender ≤2018 216 0.056 0.90       55           5      NaN
comprobar 2019-22  75 0.175 1.58       61           5      NaN
    caja 2023-hoy  57 0.144 1.38       67           3      NaN
```
## Retos con el plan entero
```
firma  riesgo   tramo  intentos  pasa  quema  ≤3m  ≤6m  ≤12m  ≤18m  mediana_m
 5ers colchón 2003-15       151    48     52   26   40    46    48        2.9
 5ers colchón 2016-22        84    76     24   31   52    69    74        3.7
 5ers colchón 2023-26        47    96      0   64   80   100   100        2.1
 5ers   2.00% 2003-15       151    40     60   17   33    38    40        3.2
 5ers   2.00% 2016-22        84    81     19   23   46    70    76        5.0
 5ers   2.00% 2023-26        47    91      4   55   78    94    97        3.0
firma riesgo   tramo  intentos  pasa  quema  ≤3m  ≤6m  ≤12m  ≤18m  mediana_m
ftmo1  1.00% 2003-15       151    34     66    1    7    20    26       10.1
ftmo1  1.00% 2016-22        84    77     23    2   12    44    56       10.4
ftmo1  1.00% 2023-26        47    91      0    5   49    97   100        5.8
```
## Retos solo con el mínimo + Flujo verde (para comparar)
```
firma  riesgo   tramo  intentos  pasa  quema  ≤3m  ≤6m  ≤12m  ≤18m  mediana_m
 5ers colchón 2003-15       151    38     62   15   29    34    38        3.4
 5ers colchón 2016-22        84    79     21   27   44    62    68        5.1
 5ers colchón 2023-26        47    96      0   45   80   100   100        3.2
firma riesgo   tramo  intentos  pasa  quema  ≤3m  ≤6m  ≤12m  ≤18m  mediana_m
ftmo1  1.00% 2003-15       151    34     66    0    5    10    16       20.1
ftmo1  1.00% 2016-22        84    79     21    0    2    29    50       13.4
ftmo1  1.00% 2023-26        47    89      0    0   24    86   100        8.0
```
Peor día de la historia con el plan entero al 1.00 %: -3.65 % (FTMO 1 paso quema al −3 % en el día; The5ers pausa el día al −3 %).

## Vigilancia de la caída (tarea F-021)
- caída nas: 424 operaciones; R medio de las 20 últimas -0.10 (histórico +0.12; 2023-hoy +0.21). En la historia, las 20 últimas estuvieron bajo 0 el 26 % del tiempo y bajo -0.14 solo el 10 %. Dentro de lo normal.
  Operaciones nuevas desde 2026-11-09: 2, R medio -0.39
- caída spx: 348 operaciones; R medio de las 20 últimas +0.09 (histórico +0.10; 2023-hoy +0.14). En la historia, las 20 últimas estuvieron bajo 0 el 28 % del tiempo y bajo -0.20 solo el 10 %. Dentro de lo normal.
  Operaciones nuevas desde 2026-11-09: 2, R medio -0.46
## Reto en la sombra desde 2026-11-09 (plan entero, 1.00 %; las caídas a la mitad)
Estado: {'saldo_pct': -0.3, 'peor_pct': -0.75, 'objetivo_pct': 10.0, 'firma': 'ftmo1', 'riesgo_pct': 1.0}
Objetivo +10 % en las dos firmas. Suelo: −6 % fijo en The5ers; −10 % desde el mayor cierre en FTMO.

   activo     entrada      salida  precio     R  peso  abierta
      spx 17-11 19:00 18-11 15:38  7339.7  0.35   1.0    False
      spx 18-11 19:00 19-11 16:22  7337.9  0.35   1.0    False
      nas 16-11 17:00 16-11 19:35 27497.0 -1.02   1.0    False
      nas 17-11 19:00 18-11 15:48 26920.2  0.36   1.0    False
   eurjpy 12-11 19:00 13-11 16:18   176.5  0.27   1.0    False
   eurjpy 23-11 21:00 24-11 01:55   173.3  0.26   1.0    False
caída nas 17-11 17:01 20-11 16:25 26898.4 -1.02   0.5    False
caída nas 26-11 00:01 26-11 08:52 25977.8  0.23   0.5    False
caída spx 17-11 17:01 20-11 17:01  7342.5 -1.02   0.5    False
caída spx 26-11 00:01 26-11 09:02  7180.6  0.10   0.5    False
