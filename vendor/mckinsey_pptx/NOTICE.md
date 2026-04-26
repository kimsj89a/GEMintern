# Vendored: mckinsey-pptx

Source: https://github.com/seulee26/mckinsey-pptx
License: MIT (see LICENSE)
Upstream: AX Labs — 이승필 (Seungpil Lee), 2026
Vendored revision: main @ 2026-04-26 (clone --depth 1)

## Why vendored
Not on PyPI. Vendored to lock the version, make Railway deploy
self-contained, and avoid runtime git fetches.

## What changed
None. Files copied verbatim except `agent/` directory (Claude Code
plugin layer not used by the FastAPI backend).

## Public API used by GEMintern
- `vendor.mckinsey_pptx.builder.PresentationBuilder`
- `vendor.mckinsey_pptx.builder.build_from_spec`

Adapter: `core_mckinsey_ppt.py` at repo root.

## Updating
1. `git clone --depth 1 https://github.com/seulee26/mckinsey-pptx /tmp/m`
2. `cp /tmp/m/mckinsey_pptx/*.py vendor/mckinsey_pptx/`
3. `cp -r /tmp/m/mckinsey_pptx/slides vendor/mckinsey_pptx/`
4. Verify: `python -c "from vendor.mckinsey_pptx.builder import PresentationBuilder"`
5. Run smoke test: `python -m core_mckinsey_ppt --smoke`
