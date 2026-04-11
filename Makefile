PYTHON ?= python3
UX_PATCH_MAP ?= docs/UX_PATCH_MAP_PYTHON_v2.json
UX_PATCH_RUNNER ?= scripts/apply_ux_patch_map.py

.PHONY: ux-map-check ux-map-dry ux-map-apply

ux-map-check:
	$(PYTHON) $(UX_PATCH_RUNNER) --map $(UX_PATCH_MAP) --dry-run >/dev/null

ux-map-dry:
	$(PYTHON) $(UX_PATCH_RUNNER) --map $(UX_PATCH_MAP) --dry-run

ux-map-apply:
	$(PYTHON) $(UX_PATCH_RUNNER) --map $(UX_PATCH_MAP) --apply
