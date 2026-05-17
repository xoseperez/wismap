"""
WisMAP Flask REST API.
Serves module data and conflict analysis via JSON endpoints,
and the React frontend as static files.
"""

import logging
import os
import requests as http_requests
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from wismap.core import (
    load_data_v1, list_modules, get_module_info, get_base_slots, combine,
)
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
_combine_limit = os.environ.get("RATELIMIT_COMBINE", "30/minute")
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
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
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
# API routes
# ---------------------------------------------------------------------------

@app.route("/api/modules")
def api_list_modules():
    type_filter = request.args.get("type", None)
    modules = list_modules(definitions, type_filter)
    return jsonify(modules)


@app.route("/api/modules/<module_id>")
def api_module_info(module_id):
    show_nc = request.args.get("show_nc", "false").lower() == "true"
    info = get_module_info(definitions, config, module_id, show_nc)
    if info is None:
        return jsonify({"error": f"Module not found: {module_id}"}), 404
    return jsonify(info)


@app.route("/api/bases/<base_id>/slots")
def api_base_slots(base_id):
    slots = get_base_slots(definitions, config, base_id)
    if slots is None:
        return jsonify({"error": f"Base board not found: {base_id}"}), 404
    return jsonify(slots)


@app.route("/api/combine", methods=["POST"])
@limiter.limit(_combine_limit)
def api_combine():
    body = request.get_json(force=True)
    base = body.get("base")
    slot_assignments = body.get("slots", {})

    if not base:
        return jsonify({"error": "Missing 'base' field"}), 400
    if base.lower() not in definitions:
        return jsonify({"error": f"Base board not found: {base}"}), 404

    result = combine(definitions, config, base, slot_assignments, rules)
    return jsonify(result)

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
