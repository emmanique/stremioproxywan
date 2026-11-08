# Stremio Proxy WAN

Reverse proxy Nginx para disponibilizar o Stremio WebPlayer através de `https://str.lusosolutions.com`, mantendo o Stremio Server na LAN `192.168.1.199`.

## Arquitectura operacional validada em 2026-11-08

| Percurso | Origem | Destino |
| --- | --- | --- |
| WebPlayer HTTPS externo | `https://str.lusosolutions.com` | `https://192-168-1-199.519b6502d940.stremio.rocks:12470` |
| HTTP pré-existente | `http://str.lusosolutions.com` | `http://192.168.1.199:8080` |
| Streaming interno na Stremio App | LAN | `https://192-168-1-199.519b6502d940.stremio.rocks:12470` |
| WebPlayer interno | LAN | `http://192.168.1.199:8080` |

A autenticação Basic permanece no HTTPS; uma sessão HMAC-SHA256 por cookie `Secure; HttpOnly; SameSite=None` (TTL de 12 horas) autoriza o WebPlayer e as playlists/segmentos HLS. O verificador de sessão escuta exclusivamente em `127.0.0.1:18765`. Tokens não-Basic são preservados na passagem para o backend; passwords Basic não são encaminhadas. O proxy mantém `Range`/`If-Range`, certificados TLS verificados e pedidos WebSocket.

No percurso `/hlsv2/`, URLs `mediaURL` que apontam para o domínio público são resolvidas para a origem interna `192.168.1.199:11470`. Isso evita que o próprio FFmpeg volte a chamar o domínio público sem o cookie da sessão. Esta reescrita está limitada ao domínio e à rota HLS configurados.

## Ficheiros

- `nginx/str.lusosolutions.com.conf`: virtual host correspondente à configuração validada (sem certificados nem secrets).
- `session/stremio-proxy-session.py`: emissor/verificador de cookies assinados, serviço local.
- `systemd/stremio-proxy-session.service`: persistência do serviço.
- `docs/OPERATIONS.md`: instalação, testes e rollback.

## Segurança e limites

**Nunca publicar** `/etc/nginx/.stremio-users`, `/etc/nginx/.stremio-session-key`, conteúdo de certificados privados, chaves VPN ou dados de sessões. Os ficheiros referidos são criados localmente, com permissões restritas.

A porta HTTP 80 mantém o comportamento herdado, **não é protegida pela autenticação HTTPS**. Se houver exposição pública dessa porta, deve ser tratada numa alteração separada, com análise de compatibilidade. Uma sessão por cookie funciona no mesmo domínio; clientes externos que não aceitem ou transmitam o cookie não devem ser considerados suportados automaticamente.

## Estado da validação

- Nginx `nginx -t` e `reload`: concluídos.
- HTTPS sem autenticação: `401`; sessão válida: `200`.
- Streams byte-range: `206`.
- HLS master através do domínio público: `200`, playlist não vazia; segmentos HLS observados com `200` durante a reprodução real no WebPlayer.
- Stremio App interna: validada **directamente** pelo HTTPS `stremio.rocks:12470`, sem utilizar o proxy WAN.

Este repositório guarda a configuração reprodutível; **não aplica modificações automaticamente ao servidor activo**.
