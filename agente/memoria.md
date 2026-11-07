# Memoria del compañero

(Este cuaderno lo actualiza el agente cada día. Máximo unas 150 líneas.)

## Estado del sistema (al instalar el agente, 6-nov-2026)
- Terminal v8.4.2. Se ejecuta de lunes a viernes; GitHub suele arrancarla con horas de retraso (el histórico se guarda hacia las 03:00-05:00 de Madrid).
- 5-nov-2026: SPY −6,2 % desde máximo, QQQ −15,2 %, IWM −11,0 %, MAGS −10,6 %; VIX 28,2; pánico agudo ACTIVO (VIX9D/VIX 1,16; VIX/VIX3M 1,10); PLAN SPY con el tramo −5 % tocado.

## Problemas abiertos
- (6-nov) Telegram de la terminal sin activar (decisión de Pe, pendiente). Cuando lo active, además de los secretos hace falta pasar TELEGRAM_TOKEN y TELEGRAM_CHAT_ID en el `env:` del paso "Ejecutar el terminal" de build.yml.
- (6-nov) 6 acciones de SECTOR_STOCKS sin datos en Yahoo (CTRA, EA, GATO…): probablemente compradas o con ticker nuevo. Revisar config.
- (6-nov) Yahoo no da cierres válidos de CL=F (petróleo); la terminal pasa a otra fuente.
- (30-oct) Incoherencia pendiente de que Pe decida: en `_op_veredicto`, ACECHO bloquea más que DISTRIBUCIÓN.

## Trabajo a medias
- Nada todavía.

## Qué ha decidido Pe
- Quiere el informe todos los días, al terminar la terminal.
- Usa su suscripción Pro (secreto CLAUDE_CODE_OAUTH_TOKEN), no API de pago. Repaso corto de lunes a jueves; investigación solo los viernes, para no gastar su cupo semanal.
- No quiere de momento el agente auditor aparte (gasta muchos tokens).
