"""Interactive local Kite login; credentials and session token stay in memory."""
import getpass
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import secrets
import sys
import time
import webbrowser
from urllib import parse, request, error
import kite_repair


def callback_token(path, state):
    url = parse.urlsplit(path)
    params = parse.parse_qs(url.query)
    if url.path != '/' or params.get('state') != [state]:
        raise ValueError('Unmatched login callback.')
    token = params.get('request_token', [])
    if len(token) != 1 or not token[0] or params.get('status') != ['success']:
        raise ValueError('Login did not return a successful request token.')
    return token[0]


def exchange_form(key, secret, token):
    checksum = hashlib.sha256((key + token + secret).encode()).hexdigest()
    return parse.urlencode({'api_key': key, 'request_token': token, 'checksum': checksum}).encode()


def exchange(key, secret, token):
    req = request.Request('https://api.kite.trade/session/token', data=exchange_form(key, secret, token),
                          headers={'X-Kite-Version': '3', 'Content-Type': 'application/x-www-form-urlencoded'}, method='POST')
    try:
        with request.build_opener(kite_repair.NoRedirect).open(req, timeout=30) as response:
            payload = json.load(response)
    except error.HTTPError as exc:
        raise ValueError(f'Login token exchange failed (HTTP {exc.code}). Check the key/secret and repeat login.') from None
    except (error.URLError, TimeoutError):
        raise ValueError('Could not reach Kite for token exchange. Repeat login when the connection is available.') from None
    data = payload.get('data', {}) if isinstance(payload, dict) else {}
    if payload.get('status') != 'success' or not isinstance(data.get('access_token'), str) or not data['access_token']:
        raise ValueError('Kite did not return an access token.')
    return data['access_token']


def login(key, secret):
    state = secrets.token_urlsafe(24)
    received = {}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # callback URLs contain short-lived credentials

        def do_GET(self):
            try:
                token = callback_token(self.path, state)
            except ValueError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Login callback not accepted. Use the login opened by the local research script.')
                return
            received['token'] = token
            page = b'<html><head><meta name="referrer" content="no-referrer"></head><body>Login received. Return to PowerShell for the download results.<script>history.replaceState(null,"","/");</script></body></html>'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            self.wfile.write(page)
    try:
        server = HTTPServer(('127.0.0.1', 8080), Handler)
    except OSError:
        raise ValueError('Local port 8080 is unavailable. Close any old login helper using that port and retry.') from None
    server.timeout = 1
    url = 'https://kite.zerodha.com/connect/login?' + parse.urlencode({'v': 3, 'api_key': key, 'redirect_params': parse.urlencode({'state': state})})
    with server:
        print('Opening Kite login. Sign in yourself in the browser; do not enter your password in this terminal.')
        print('Your app Redirect URL must be http://localhost:8080/ (as in your developer settings).')
        print('If no browser opens, paste this login URL into your browser:\n' + url)
        webbrowser.open(url, new=2)
        deadline = time.monotonic() + 300
        while not received and time.monotonic() < deadline:
            server.handle_request()
    if not received:
        raise ValueError('Login timed out after five minutes. Run the command again.')
    return exchange(key, secret, received.pop('token'))


def main():
    print('Kite browser-login setup: API KEY and API SECRET, not an access token.')
    key = getpass.getpass('API key (hidden): ').strip()
    secret = getpass.getpass('API secret (hidden): ').strip()
    if not key or not secret:
        raise ValueError('Both API key and API secret are required.')
    token = login(key, secret)
    secret = None
    print('Kite login succeeded. Starting historical-data pilot; no orders will be placed.')
    old = {name: os.environ.get(name) for name in ['KITE_API_KEY', 'KITE_ACCESS_TOKEN']}
    original_argv = sys.argv
    try:
        os.environ['KITE_API_KEY'], os.environ['KITE_ACCESS_TOKEN'] = key, token
        for command in ['instruments', 'fetch']:
            sys.argv = ['kite_repair.py', command, '--execute']
            kite_repair.cli()
        import compare_downloads
        compare_downloads.main()
    finally:
        sys.argv = original_argv
        for name, value in old.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, kite_repair.ApiFailure) as exc:
        print(f'Stopped: {exc}')
        sys.exit(1)
    except KeyboardInterrupt:
        print('Login cancelled.')
        sys.exit(1)
