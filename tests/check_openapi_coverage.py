#!/usr/bin/env python3
"""
Drift-protection check for wismap/openapi.yaml.

Asserts:
  1. Every /api/v1/* route registered on the Flask app has a corresponding
     path entry in openapi.yaml (and vice versa).
  2. `info.version` in openapi.yaml matches `wismap.__version__`.

Routes for the docs/openapi assets themselves are exempted (they serve the
documentation surface — there is no value in documenting them).

Run from repo root:
    python tests/check_openapi_coverage.py

Exit code 0 on success, 1 on drift.
"""
import os
import sys
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

from wismap import __version__  # noqa: E402
from wismap.api import app      # noqa: E402

OPENAPI_PATH = os.path.join(REPO, "wismap", "openapi.yaml")

# Routes that serve the documentation surface itself — exempt from coverage.
EXEMPT_PREFIXES = (
    "/api/v1/openapi.yaml",
    "/api/v1/docs",
)


import re

# Path-template comparison ignores the placeholder name — only structure
# matters. /cores/<core_id> and /cores/{id} both normalize to /cores/{}.
_PLACEHOLDER = re.compile(r"<[^>]+>|\{[^}]+\}")


def normalize_path(p: str) -> str:
    return _PLACEHOLDER.sub("{}", p)


def main():
    # 1. Inventory routes registered under the v1 blueprint.
    registered = set()
    for r in app.url_map.iter_rules():
        if not r.endpoint.startswith("api_v1."):
            continue
        if any(r.rule.startswith(p) for p in EXEMPT_PREFIXES):
            continue
        registered.add(normalize_path(r.rule))

    # 2. Inventory paths declared in openapi.yaml.
    with open(OPENAPI_PATH) as f:
        doc = yaml.safe_load(f)
    documented = {normalize_path(p) for p in doc.get("paths", {}).keys()}

    # 3. Compare.
    missing_in_yaml = registered - documented
    missing_in_routes = documented - registered
    errors = []
    if missing_in_yaml:
        errors.append("Routes registered but not documented in openapi.yaml:")
        errors.extend(f"  + {r}" for r in sorted(missing_in_yaml))
    if missing_in_routes:
        errors.append("Documented in openapi.yaml but not registered as a route:")
        errors.extend(f"  - {p}" for p in sorted(missing_in_routes))

    # 4. info.version must match __version__.
    yaml_version = (doc.get("info") or {}).get("version")
    if yaml_version != __version__:
        errors.append(
            f"info.version mismatch: openapi.yaml has '{yaml_version}', "
            f"wismap.__version__ is '{__version__}'."
        )

    if errors:
        print("openapi drift detected:")
        for line in errors:
            print(" ", line)
        sys.exit(1)

    print(f"OK — {len(registered)} routes documented, version={__version__}.")


if __name__ == "__main__":
    main()
