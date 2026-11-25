# Notebook Showroom Implementation Plan

**Goal:** Generate reviewable Showroom mirrors of the seven existing notebooks and prevent drift.

**Architecture:** nbconvert exports notebook cells; a small adapter repairs Antora-specific constructs. Generated pages are committed with notebook changes and checked by CI. Work inline on `docs/notebook-showroom-mirror` from current `origin/dev`; do not change agent code or deployment charts.

**Tech stack:** Python, nbconvert, Pandoc, Antora, GitHub Actions.

## Tasks

- [x] Establish project-local documentation dependencies and inspect nbconvert's AsciiDoc output on a real notebook.
- [x] Write failing tests in `publishing-house/showroom/tests/test_generate.py` for code preservation, Mermaid, collapsible answers, relative links, excluded outputs, and non-mutating drift detection. Run with `.venv/bin/python -m unittest discover -s publishing-house/showroom/tests -v` and confirm failures expose the missing generator.
- [x] Implement `publishing-house/showroom/generate.py` using the existing exporter, without executing notebooks. Re-run the tests until they pass.
- [x] Generate all seven module pages, read the existing overview before replacing it, and add a reader-facing index.
- [x] Add `publishing-house/showroom/README.md`, pinned build dependencies, a local Antora preview command and `.github/workflows/showroom-docs.yml` that checks generation and builds a preview artifact.
- [x] Verify regeneration is deterministic and the test deliberately changes and removes generated pages to confirm check mode fails without writing. Build Antora and inspect all seven HTML pages.
- [ ] Inspect browser-rendered representative content. Blocked: the computer-use browser host is unavailable; HTML structure was checked instead, including the Mermaid initialization script and collapsible answer content.
- [x] Review the diff, record validation, and commit the completed change on the feature branch. Preserve the branch and report publication status accurately.

## Validation

Four conversion tests pass, including deliberately stale and missing page checks. All seven Antora HTML modules preserve the 55 original code cells, seven Mermaid diagrams, collapsible answers and branch-specific source links. Default source-ref and explicit `test` builds both pass with warnings treated as failures. The generated-page check and `git diff --check` pass. The existing agent suite reports 69 passed and eight setup errors: the local Podman VM is stopped, so the pgvector fixture cannot start. No runtime or deployment changes were made. Browser inspection remains blocked as recorded above.
