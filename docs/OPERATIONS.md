# Deployment and rollback

## Scope

Deploy on the **WAN Nginx proxy host** only. The code here represents the functioning setup of 2026-11-08. It is not a change to Stremio Core, the VPN Gateway, or the Stremio App. Review hardcoded domain, address, certificate path and local file permissions before using on another host.

## Prerequisites

Ubuntu/Debian with Nginx including `http_auth_request_module`, Python 3, systemd, reachable Stremio LAN host and an already valid certificate for `str.lusosolutions.com`. Keep public DNS and TLS configuration independently managed.

## One-time local secrets

Never commit or export any of these files:

- `/etc/nginx/.stremio-users` (Basic auth users and password hashes)
- `/etc/nginx/.stremio-session-key` (HMAC signing key)
- `/etc/letsencrypt/live/npm-11/privkey.pem` (TLS private key)

Example new installation:

```bash
sudo install -d -m 755 /usr/local/libexec
sudo python3 -c 'import secrets,pathlib; p=pathlib.Path("/etc/nginx/.stremio-session-key"); p.write_text(secrets.token_hex(32)); p.chmod(0o640)'
sudo chown root:www-data /etc/nginx/.stremio-session-key
sudo htpasswd -c /etc/nginx/.stremio-users YOUR_USERNAME
sudo chown root:www-data /etc/nginx/.stremio-users
sudo chmod 640 /etc/nginx/.stremio-users
```

Do not run `htpasswd -c` on an existing installation: it truncates the current user database. Preserve the session key during upgrades, otherwise all existing sessions expire.

## Controlled installation

```bash
sudo cp -a /etc/nginx/sites-available/str.lusosolutions.com /etc/nginx/sites-available/str.lusosolutions.com.bak-$(date -u +%Y%m%dT%H%M%SZ)
sudo install -m 755 session/stremio-proxy-session.py /usr/local/libexec/stremio-proxy-session.py
sudo install -m 644 systemd/stremio-proxy-session.service /etc/systemd/system/stremio-proxy-session.service
sudo install -m 644 nginx/str.lusosolutions.com.conf /etc/nginx/sites-available/str.lusosolutions.com
sudo python3 -m py_compile /usr/local/libexec/stremio-proxy-session.py
sudo systemctl daemon-reload
sudo systemctl enable --now stremio-proxy-session.service
sudo nginx -t
sudo systemctl reload nginx
```

The `sites-enabled` symlink to `sites-available` should already exist or be created separately. Review which file is actually included by `nginx -T`. Never overwrite Nginx configuration before preparing a rollback.

## Basic checks

```bash
systemctl is-active nginx stremio-proxy-session.service
curl -sS -o /dev/null -w '%{http_code}\n' https://str.lusosolutions.com/
curl -sS -o /dev/null -w '%{http_code}\n' https://192-168-1-199.519b6502d940.stremio.rocks:12470/settings
curl -sS -o /dev/null -w '%{http_code}\n' http://192.168.1.199:8080/settings
```

Expected: first URL is 401 unauthenticated; LAN and internal HTTPS settings GET are 200. Visit `https://str.lusosolutions.com/_session/start` to issue a signed browser session. Test the same movie externally and internally, including HLS `master.m3u8`, `index.m3u8`, `init.mp4`, `seg0.m4s` and byte ranges. Anonymous requests must continue returning 401.

For the native Stremio App on the LAN, explicitly select `https://192-168-1-199.519b6502d940.stremio.rocks:12470` and click Reload; do not select the proxy domain because native clients may not carry browser cookies. The default `127.0.0.1:11470` points to the client device, not the server.

## Rollback

```bash
sudo cp -a /etc/nginx/sites-available/str.lusosolutions.com.bak-YYYYMMDDTHHMMSSZ /etc/nginx/sites-available/str.lusosolutions.com
sudo nginx -t && sudo systemctl reload nginx
```

Keep the session service running unless it is no longer referenced. Rollback is limited to the virtual host; never reset the Stremio database, torrent cache, or VPN host policy.

## Risk notes

- Port 80 retains inherited direct forwarding, which lacks the HTTPS authentication boundary. Do not treat it as private or safe to expose on an untrusted WAN.
- The HLS rewriting map is intentionally narrow and does **not** act as a general URL proxy. Validate query parameter variations before broadening it.
- The signing service is loopback-only. Restrict access to its files and do not log cookie contents.
- This is an operational baseline, not a security audit or proof of compatibility with every Stremio client.
