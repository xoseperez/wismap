"""
WisMAP Flask REST API.
Serves module data and conflict analysis via JSON endpoints,
and the React frontend as static files.
"""

import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from wismap.core import load_data, list_modules, get_module_info, get_base_slots, combine

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

# Resolve data folder relative to project root (one level up from this file)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_data_folder = os.path.join(_project_root, "data")
_frontend_dist = os.path.join(_project_root, "frontend", "dist")

definitions, config = load_data(_data_folder)

app = Flask(__name__, static_folder=_frontend_dist, static_url_path="")
app.json.sort_keys = False
CORS(app)

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
def api_combine():
    body = request.get_json(force=True)
    base = body.get("base")
    slot_assignments = body.get("slots", {})

    if not base:
        return jsonify({"error": "Missing 'base' field"}), 400
    if base.lower() not in definitions:
        return jsonify({"error": f"Base board not found: {base}"}), 404

    result = combine(definitions, config, base, slot_assignments)
    return jsonify(result)

# ---------------------------------------------------------------------------
# SPA fallback — serve React index.html for non-API routes
# ---------------------------------------------------------------------------

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
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
    app.run(host="0.0.0.0", port=5000, debug=True)
