"""Entry point for cPanel/Namecheap shared hosting ("Setup Python App").

That environment runs apps through Phusion Passenger, which expects a
`passenger_wsgi.py` file exposing a WSGI callable named `application` - not
an ASGI app. FastAPI/Starlette are ASGI-only, so this wraps the real app
with `a2wsgi` (a small, dependency-free ASGI->WSGI adapter) rather than
requiring a Passenger version new enough to speak ASGI natively, which
varies across shared-hosting accounts and isn't worth gambling on.

This file is only used by that deployment path - running locally or on
Render, `app.main:app` is served directly by Uvicorn/ASGI as usual (see
README.md / render.yaml). WSGI has no notion of async streaming, but every
endpoint here is a plain request/response JSON call, so nothing is lost by
going through this adapter.
"""

from a2wsgi import ASGIMiddleware

from app.main import app as _asgi_app

application = ASGIMiddleware(_asgi_app)
