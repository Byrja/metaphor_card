PYTHON ?= python
UX_PACK_ROOT ?= docs/ux-pack-v3-python

.PHONY: ux-check ux-apply-dry ux-apply smoke test

ux-check:
	$(PYTHON) scripts/ux_integrator.py check --pack-root $(UX_PACK_ROOT)

ux-apply-dry:
	$(PYTHON) scripts/ux_integrator.py apply --pack-root $(UX_PACK_ROOT) --dry-run

ux-apply:
	$(PYTHON) scripts/ux_integrator.py apply --pack-root $(UX_PACK_ROOT)

smoke:
	PYTHONPATH=src:. ./scripts/smoke.sh

test:
	pytest
