# Notebook Showroom Implementation Plan

**Goal:** Generate reviewable Showroom mirrors of the seven existing notebooks and prevent drift.

**Architecture:** nbconvert exports notebook cells; a small adapter repairs Antora-specific constructs. Generated pages are committed with notebook changes and checked by CI. Work inline on `docs/notebook-showroom-mirror` from current `origin/dev`; do not change agent code or deployment charts.

**Tech stack:** Python, nbconvert, Pandoc, Antora, GitHub Actions.

## Tasks

- [ ] Establish project-local documentation dependencies and inspect nbconvert's AsciiDoc output on a real notebook.
- [ ] Write failing tests in `publishing-house/showroom/tests/test_generate.py` for code preservation, Mermaid, collapsible answers, relative links, excluded outputs, and non-mutating drift detection. Run with `.venv/bin/python -m unittest discover -s publishing-house/showroom/tests -v` and confirm failures expose the missing generator.
- [ ] Implement `publishing-house/showroom/generate.py` using the existing exporter, without executing notebooks. Re-run the tests until they pass.
- [ ] Generate all seven module pages, read the existing overview before replacing it, and add a reader-facing index.
- [ ] Add `publishing-house/showroom/README.md`, pinned build dependencies, a local Antora preview command and `.github/workflows/showroom-docs.yml` that checks generation and builds a preview artifact.
- [ ] Verify regeneration is deterministic, deliberately change a generated page to confirm check mode fails, regenerate it and confirm a clean check. Build Antora and inspect all seven HTML pages and browser-rendered representative content.
- [ ] Review the diff, record validation, and commit the completed change on the feature branch. Preserve the branch and report publication status accurately.
