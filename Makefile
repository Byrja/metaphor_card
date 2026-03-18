.PHONY: ux-map-check ux-map-apply

PYTHON ?= python3
UX_MAP_PATH ?= docs/UX_PATCH_MAP_PYTHON_v2.json

ux-map-check:
	$(PYTHON) scripts/ux_map_guard.py check --map $(UX_MAP_PATH)

ux-map-apply:
	$(PYTHON) scripts/ux_map_guard.py apply --map $(UX_MAP_PATH)
