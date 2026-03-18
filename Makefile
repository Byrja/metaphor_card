.PHONY: ux-map-check ux-map-apply ux-v3-check ux-v3-dry ux-v3-apply ux-v4-check ux-v4-dry ux-v4-apply

PYTHON ?= python3
UX_MAP_PATH ?= docs/UX_PATCH_MAP_PYTHON_v2.json
UX_V3_MAP_PATH ?= docs/UX_PATCH_MAP_PYTHON_v3.json
UX_V4_MAP_PATH ?= docs/UX_PATCH_MAP_PYTHON_v4.json

ux-map-check:
	$(PYTHON) scripts/ux_map_guard.py check --map $(UX_MAP_PATH)

ux-map-apply:
	$(PYTHON) scripts/ux_map_guard.py apply --map $(UX_MAP_PATH)

ux-v3-check:
	$(PYTHON) scripts/ux_map_guard.py check --map $(UX_V3_MAP_PATH)

ux-v3-dry:
	$(PYTHON) scripts/ux_map_guard.py apply --map $(UX_V3_MAP_PATH)

ux-v3-apply:
	$(PYTHON) scripts/ux_map_guard.py apply --map $(UX_V3_MAP_PATH)

ux-v4-check:
	$(PYTHON) scripts/ux_map_guard.py check --map $(UX_V4_MAP_PATH)

ux-v4-dry:
	$(PYTHON) scripts/ux_map_guard.py apply --map $(UX_V4_MAP_PATH)

ux-v4-apply:
	$(PYTHON) scripts/ux_map_guard.py apply --map $(UX_V4_MAP_PATH)
