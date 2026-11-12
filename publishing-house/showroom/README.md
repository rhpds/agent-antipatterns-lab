# Showroom mirrors of the module notebooks

Edit the seven `notebooks/module-*.ipynb` files, then regenerate their Showroom pages. Do not edit the generated module pages directly. The overview (`content/modules/ROOT/pages/index.adoc`) remains authored AsciiDoc.

## Generate and check

Use a project-local Python environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r publishing-house/showroom/requirements.txt
.venv/bin/python publishing-house/showroom/generate.py
.venv/bin/python publishing-house/showroom/generate.py --check
```

Commit both the notebook and its generated page. `--check` returns a failure for missing or changed module pages and writes nothing. Conversion completes for all notebooks before any page is written. No notebook is executed.

## Preview

```bash
npm ci --prefix publishing-house/showroom
npm run build --prefix publishing-house/showroom
.venv/bin/python publishing-house/showroom/verify.py
python3 -m http.server 8765 --bind 127.0.0.1 --directory www
```

Open <http://127.0.0.1:8765/modules/index.html>. The site uses the existing Antora playbook and Showroom theme. Mermaid diagrams load the library configured in `site.yml`, so diagram rendering requires network access.

Antora source links use the branch or tag from which Antora reads the pages. Local previews use your current branch. Plain AsciiDoc rendering outside Antora falls back to `dev`. To override the publishing branch:

```bash
npm run build --prefix publishing-house/showroom -- --attribute lab-source-ref=test
.venv/bin/python publishing-house/showroom/verify.py --source-ref test
```

The Showroom build can also set the `lab-source-ref` AsciiDoc attribute for its deployment branch. CI sets it to the pull request's target branch, or the branch being pushed.

## What is mirrored

Markdown and code cells remain in order. Code cells are Python listings, including notebook-only `!` commands and `%` magics; they are not rewritten as terminal instructions. Mermaid blocks become rendered diagrams, and HTML `details` answers become collapsible AsciiDoc blocks. Relative links to agent files point to the corresponding repository files. Links to another module notebook become Showroom cross-references.

Saved outputs and execution counts are always excluded. The current notebooks contain no captured outputs. Each page explains that evidence tables, model responses and environment-specific links become available during execution. Prototype labels and current wording are retained; this pipeline does not certify instructional completeness. Notebook attachments, raw cells and unsupported HTML blocks fail conversion rather than disappearing silently.

The converter uses nbconvert's AsciiDoc exporter, Pandoc from the pinned `pypandoc-binary` wheel, and a small Lua filter for Antora conventions. There is no custom Markdown parser.

## Verification and CI

```bash
mkdir -p .cache
.venv/bin/python -m unittest discover -s publishing-house/showroom/tests -v
```

The `showroom-docs` GitHub Actions workflow runs on pull requests and pushes to `dev`, `test` and `main`. It tests conversion, checks committed pages for drift, builds Antora, verifies the HTML of every module against the notebooks, and saves the `showroom-preview` artifact. This workflow builds documentation; it does not deploy a Showroom instance, promote a branch or advance Publishing House stages.
