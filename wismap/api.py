"""
WisMAP Flask REST API.

The canonical API lives under /api/v1 (see wismap/api_v1.py).
This module wires the blueprint, applies rate limits, exposes the
image-proxy utility, and serves the React SPA.
"""

import logging
import os
import requests as http_requests
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from wismap.core import load_data_v1
from wismap.api_v1 import bp as api_v1_bp

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

# Resolve data folder relative to project root (one level up from this file)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_data_folder = os.path.join(_project_root, "data")
_frontend_dist = os.path.join(_project_root, "frontend", "dist")

definitions, config, rules, compat_slots_index = load_data_v1(_data_folder)

app = Flask(__name__, static_folder=_frontend_dist, static_url_path="")
app.json.sort_keys = False
CORS(app)

# Stash the loaded data on the app so the v1 blueprint can access it.
app.config["WISMAP_DATA"] = (definitions, config, rules, compat_slots_index)
app.register_blueprint(api_v1_bp)

# ---------------------------------------------------------------------------
# Rate limiting — configurable via environment variables
# ---------------------------------------------------------------------------

_default_limit = os.environ.get("RATELIMIT_DEFAULT", "120/minute")
_proxy_limit = os.environ.get("RATELIMIT_PROXY", "60/minute")
_storage_uri = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
_enabled = os.environ.get("RATELIMIT_ENABLED", "true").lower() in ("1", "true", "yes")

logger = logging.getLogger(__name__)

def _on_breach(request_limit):
    logger.warning(
        "Rate limit exceeded: %s from %s on %s %s",
        request_limit.limit, get_remote_address(), request.method, request.path,
    )

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[_default_limit],
    storage_uri=_storage_uri,
    enabled=_enabled,
    on_breach=_on_breach,
)


@app.after_request
def set_security_headers(response):
    # Swagger UI's bootstrap is an inline <script> in our vendored index.html.
    # Loosen `script-src` with 'unsafe-inline' for /api/v1/docs* only.
    # SECURITY: do NOT render any user-controlled content into the Swagger UI
    # page or its assets — the carve-out below assumes the page contains only
    # static HTML that boots SwaggerUIBundle against /api/v1/openapi.yaml.
    is_docs = request.path.startswith("/api/v1/docs")
    script_src = "script-src 'self' 'unsafe-inline'; " if is_docs else "script-src 'self'; "
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        + script_src +
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https://images.docs.rakwireless.com; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

# ---------------------------------------------------------------------------
# Image proxy — frontend utility for PDF export (not part of the v1 contract)
# ---------------------------------------------------------------------------

@app.route("/api/image-proxy")
@limiter.limit(_proxy_limit)
def api_image_proxy():
    """Proxy remote images to avoid CORS issues in PDF export."""
    url = request.args.get("url", "")
    if not url.startswith("https://images.docs.rakwireless.com/"):
        return jsonify({"error": "URL not allowed"}), 403
    try:
        resp = http_requests.get(url, timeout=15)
        resp.raise_for_status()
        return Response(
            resp.content,
            content_type=resp.headers.get("Content-Type", "image/png"),
        )
    except Exception:
        return jsonify({"error": "Failed to fetch image"}), 502

# ---------------------------------------------------------------------------
# SPA fallback — serve React index.html for non-API routes
# ---------------------------------------------------------------------------

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
@limiter.exempt
def serve_spa(path):
    # If the file exists in the static folder, serve it
    if path and os.path.isfile(os.path.join(_frontend_dist, path)):
        return send_from_directory(_frontend_dist, path)
    # Otherwise serve index.html (SPA routing)
    index = os.path.join(_frontend_dist, "index.html")
    if os.path.isfile(index):
        return send_from_directory(_frontend_dist, "index.html")
    return jsonify({"error": "Frontend not built. Run: make frontend-build"}), 404

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=5000, debug=debug)
