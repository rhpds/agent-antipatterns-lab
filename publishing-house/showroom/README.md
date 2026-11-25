# Showroom guides for the module notebooks

Edit the seven `notebooks/module-*.ipynb` files, then regenerate their Showroom pages. Do not edit the generated module pages directly. The overview (`content/modules/ROOT/pages/index.adoc`) remains authored AsciiDoc.

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

Each guide links to its notebook, and to the agent files its text names, in the participant's own workbench: `https://rh-ai.{openshift_cluster_ingress_domain}/notebook/{user}-app/kestrel-agent/lab/tree/agent-antipatterns-lab/<path>`. The links open in a new tab. Showroom supplies `user` and `openshift_cluster_ingress_domain` from each environment's user data. A local or CI build uses the defaults in `content/antora.yml`, so its links point to a placeholder cluster; `verify.py` checks them against those defaults. Plain AsciiDoc rendering outside Antora uses fallbacks in each page's header.

The build still accepts `--attribute lab-source-ref=<ref>` and `verify.py` still accepts `--source-ref`, so existing build commands run unchanged, but the guides no longer link to a branch.

## What goes into a guide

Each module page is a short guide to its notebook. The participant works in the notebook in the Notebook tab; the guide keeps them oriented. From the notebook, the generator takes:

- the title, and the opening paragraph under it (what the module covers);
- the numbered step headings (`## 1. ...`), as a list;
- every `**Your read:**` question, with its `<details>` answer as a collapsible block;
- the `**This is the module's success signal:**` paragraph, as "How you know it worked";
- the Mermaid diagrams, in one collapsible block, because a diagram can show the fix;
- the `## If the result differs` section, also collapsed, because it lists likely causes.

Code cells, saved outputs, the reset section and blockquotes such as draft notices are left out. Relative links to agent files open the file in the participant's workbench, in a new tab. Notebook attachments, raw cells, unsupported cell types, an answer reveal that doesn't follow its question, a reveal containing code, nested reveals, and `~~~` or longer fences all fail generation rather than slipping through.

So a notebook change shows up in its guide, keep those conventions when editing a notebook: an opening paragraph under the title, numbered step headings, the two bold labels above, and every `<details>` answer straight after its `**Your read:**` question, with no code inside it.

## Verification and CI

```bash
mkdir -p .cache
.venv/bin/python -m unittest discover -s publishing-house/showroom/tests -v
```

The `showroom-docs` GitHub Actions workflow runs on pull requests and pushes to `dev`, `test` and `main`. It tests conversion, checks committed pages for drift, builds Antora, verifies every built guide against its notebook (steps, questions, diagrams, workbench links, and no copied code), and saves the `showroom-preview` artifact. This workflow builds documentation; it does not deploy a Showroom instance, promote a branch or advance Publishing House stages.
