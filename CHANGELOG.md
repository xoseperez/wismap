Changelog
=========

All notable changes to this project will be documented in this file.


## 0.3.0 — 2026-02-27

* Add searchable tags to all ~140 modules (protocol, sensor type, communication, use case)
* Tags stored in patch files and merged into definitions.yml during import
* Web UI: search now matches against module tags in addition to ID and description
* Web UI: module detail page shows tags as clickable badges that filter the module list
* CLI: new `search` action to filter modules by type, description, or tags
* CLI: `info` action now displays tags
* CLI: `list` and `search` actions now include a Documentation column


## 0.2.1 — 2026-02-27

* Add version flag (`-v`/`--version`) to the CLI
* Show version in the web UI footer and in exported documents
* Preserve module list filters (type, search) when navigating to a module detail and back
* Add "Clear" button to reset active filters in the modules list
* Refactor WisCore module data to use pin numbers instead of names
* Rename the "mapping" key in definitions.yml for WisBase modules to "naming"


## 0.2.0 — 2026-02-16

First release with the web interface.

* REST API (Flask) serving module data, slot info, and combine analysis
* React 19 SPA (Vite) with module browser, detail view, and combine tool
* Export combine results to PDF or Markdown
* Shareable hash-based URLs for combine configurations (`#combine/base/mod1/...`)
* Docker multi-stage build and docker-compose support
* Split `patches.yml` into per-module files under `data/patches/`
* Combine view as default landing page
* Dynamic combine table updates as modules are selected
* Module images and schematics shown in detail view
* Keep page context when switching between Combine and Modules views
* Sort slots in canonical order across base boards
* Data cleanup: fix typos, inconsistencies, and documentation links


## 0.1.0 — 2024-07-29

Initial CLI-only release.

* List all WisBlock modules with type and description
* View detailed pin mappings and documentation for any module
* Combine modules on a base board and detect pin conflicts:
  - I2C address collisions
  - AIN0 / ADC_VBAT conflicts
  - Duplicate IO/AIN/GPIO/UART/LED/SW/SPI_CS usage
  - IO2 vs 3V3_S enable signal conflict
  - SPI chip-select conflicts
* Double-sensor slot blocking
* Import definitions from the official RAKwireless Pin Mapper spreadsheet
* Per-module patch files for custom overrides
* Support for ~140 modules across all WisBlock types (Base, Core, IO, Sensor, Power)
* Markdown table output (`-m`) and NC pin display (`-n`) options
* Pass module arguments directly on the command line (non-interactive mode)
* Reproduce configuration command printed after combine output
