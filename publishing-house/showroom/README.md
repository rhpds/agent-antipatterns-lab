# Showroom guides for the module notebooks

Edit the six `notebooks/module-*.ipynb` files, then regenerate their Showroom pages. Do not edit the generated module pages directly. The overview (`content/modules/ROOT/pages/index.adoc`) remains authored AsciiDoc.

## Generate and check

Use a project-local Python environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r publishing-house/showroom/requirements.txt
.venv/bin/python publishing-house/showroom/generate.py
.venv/bin/python publishing-house/showroom/generate.py --check
```

Commit both the notebook and its generated page. `--check` returns a failure for missing or changed module pages and writes nothing. Generation completes for all notebooks before any page is written. No notebook is executed.

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

The Showroom build can also set the `lab-source-ref` AsciiDoc attribute for its deployment branch. CI checks out the pull request's exact head commit and uses that SHA in source links. Push builds use the pushed commit SHA.

## What goes into a guide

Each module page is a short guide to its notebook. The participant works in the notebook in the Notebook tab; the guide keeps them oriented. From the notebook, the generator takes:

- the title, and the opening paragraph under it (what the module covers);
- the numbered step headings (`## 1. ...`), as a list;
- every `**Your read:**` question, with its `<details>` answer as a collapsible block;
- the `**This is the module's success signal:**` paragraph, as "How you know it worked";
- the Mermaid diagrams, in one collapsible block, because a diagram can show the fix;
- a `## Where to go next` section, if the notebook has one, as it stands;
- the `## If the result differs` section, collapsed like the diagrams, because it lists likely causes.

Code cells, saved outputs, the reset section and blockquotes such as draft notices are left out. Relative links to agent files point to the repository files on GitHub. They open in a new tab, as do links to other websites. Notebook attachments, raw cells, unsupported cell types, an answer reveal that doesn't follow its question, a reveal containing code, nested reveals, and `~~~` or longer fences all fail generation rather than slipping through.

So a notebook change shows up in its guide, keep those conventions when editing a notebook: an opening paragraph under the title, numbered step headings, the two bold labels above, and every `<details>` answer straight after its `**Your read:**` question, with no code inside it. Keep code and reveals out of `## Where to go next` and `## If the result differs`.

## Verification and CI

```bash
mkdir -p .cache
.venv/bin/python -m unittest discover -s publishing-house/showroom/tests -v
```

The `showroom-docs` GitHub Actions workflow runs on pull requests and pushes to `dev`, `test` and `main`. It tests conversion, checks committed pages for drift, builds Antora, verifies every built guide against its notebook (steps, questions, diagrams, links, and no copied code), and saves the `showroom-preview` artifact. This workflow builds documentation; it does not deploy a Showroom instance, promote a branch or advance Publishing House stages.
