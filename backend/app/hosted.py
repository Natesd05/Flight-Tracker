"""Single-service hosted demo: static frontend, API and a shared access gate."""
import base64
import binascii
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles


def create_hosted_app(api, static_dir, password, origin):
    if len(password) < 16:
        raise RuntimeError('Set DEMO_PASSWORD to a secret of at least 16 characters.')
    origin = origin.rstrip('/')
    parsed = urlsplit(origin)
    local = parsed.hostname in ('localhost', '127.0.0.1')
    if (not parsed.hostname or parsed.path or parsed.query or parsed.fragment or
            parsed.username or parsed.password or
            (parsed.scheme != 'https' and not (local and parsed.scheme == 'http'))):
        raise RuntimeError('Set RENDER_EXTERNAL_URL or DEMO_ORIGIN to the HTTPS site origin.')
    if not (Path(static_dir) / 'index.html').is_file():
        raise RuntimeError('Build the frontend before starting the hosted demo.')

    class DemoAccess(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            # Render polls this liveness endpoint. Avoid waking Neon on each poll.
            if request.url.path == '/healthz' and request.method in ('GET', 'HEAD'):
                return await call_next(request)
            user, supplied = b'', b''
            try:
                scheme, encoded = request.headers.get('authorization', '').split(' ', 1)
                if scheme.lower() == 'basic':
                    user, supplied = base64.b64decode(encoded, validate=True).split(b':', 1)
            except (ValueError, binascii.Error):
                pass
            user_ok = secrets.compare_digest(user, b'demo')
            password_ok = secrets.compare_digest(supplied, password.encode('utf-8'))
            if not (user_ok and password_ok):
                response = PlainTextResponse('Authentication required', status_code=401,
                                             headers={'WWW-Authenticate': 'Basic realm="FlightPlanner", charset="UTF-8"'})
            elif request.method in ('POST', 'PUT', 'PATCH', 'DELETE') and (
                    request.headers.get('sec-fetch-site') == 'cross-site' or
                    ('origin' in request.headers and request.headers['origin'] != origin)):
                response = PlainTextResponse('Cross-origin writes are not allowed', status_code=403)
            else:
                response = await call_next(request)
            response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                                     'X-Frame-Options': 'DENY', 'Referrer-Policy': 'same-origin'})
            return response

    async def health(request):
        return PlainTextResponse('ok')

    api.mount('/', StaticFiles(directory=static_dir, html=True), name='frontend')
    app = Starlette(routes=[Route('/healthz', health), Mount('/', api)])
    app.add_middleware(DemoAccess)
    return app


def create_app():
    from .config import settings
    if settings.flight_provider != 'mock':
        raise RuntimeError('The free hosted demo only supports the sample-flight provider.')
    if not os.environ.get('DATABASE_URL'):
        raise RuntimeError('Set DATABASE_URL using the Neon connection string.')
    from .main import app
    return create_hosted_app(
        app, os.environ.get('STATIC_DIR', '/app/static'), os.environ.get('DEMO_PASSWORD', ''),
        os.environ.get('RENDER_EXTERNAL_URL') or os.environ.get('DEMO_ORIGIN', ''),
    )
