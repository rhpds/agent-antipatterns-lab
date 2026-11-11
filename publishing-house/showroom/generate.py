#!/usr/bin/env python3
"""Generate Showroom module mirrors. Never execute notebooks or include saved outputs."""
import argparse
from pathlib import Path
import re
import subprocess
import sys

import nbformat
from nbconvert import ASCIIDocExporter
import pypandoc

DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[1]
NOTEBOOKS = ROOT / "notebooks"
PAGES = ROOT / "content/modules/ROOT/pages"
# Use the bundled, pinned Pandoc rather than whichever version happens to be on PATH.
PANDOC = Path(pypandoc.__file__).parent / "files" / ("pandoc.exe" if sys.platform == "win32" else "pandoc")


def markdown_to_asciidoc(source):
    return subprocess.run(
        [str(PANDOC), "--from=markdown-smart", "--to=asciidoc", "--wrap=none",
         "--lua-filter=" + str(DIRECTORY / "antora.lua")],
        input=source, text=True, capture_output=True, check=True,
    ).stdout.rstrip()


def listing(source):
    """A code cell stays byte-for-byte readable, including IPython magics."""
    longest = max((len(line) for line in source.splitlines() if re.fullmatch(r"-+", line)), default=0)
    fence = "-" * max(4, longest + 1)
    return f"[source,python]\n{fence}\n{source.rstrip()}\n{fence}"


def render(source):
    notebook = nbformat.read(source, as_version=4)
    # The exporter must not silently drop a future attachment or an unknown cell type.
    for cell in notebook.cells:
        if cell.cell_type not in {"markdown", "code"} or cell.get("attachments"):
            raise ValueError(f"{source.name}: only Markdown and code cells without attachments are supported")
    exporter = ASCIIDocExporter(
        exclude_output=True, exclude_input_prompt=True, exclude_output_prompt=True,
        template_file=str(DIRECTORY / "mirror.asciidoc.j2"),
        filters={"markdown2asciidoc": markdown_to_asciidoc, "code_listing": listing},
    )
    body, _ = exporter.from_notebook_node(notebook)
    title, separator, remainder = body.lstrip().partition("\n")
    if not separator or not title.startswith("= "):
        raise ValueError(f"{source.name}: the first cell must start with a level-one Markdown heading")
    introduction = f"""// Generated from notebooks/{source.name}; edit the notebook, then run:
// python publishing-house/showroom/generate.py
{title}
ifndef::lab-source-ref[]
ifdef::page-origin-refname[]
:lab-source-ref: {{page-origin-refname}}
endif::[]
ifndef::page-origin-refname[]
:lab-source-ref: dev
endif::[]
endif::[]
:lab-source-url: https://github.com/rhpds/agent-antipatterns-lab/blob/{{lab-source-ref}}

NOTE: This page mirrors the link:{{lab-source-url}}/notebooks/{source.name}[Jupyter notebook]. You can review the lesson here without a running lab. Code cells are shown in order and run in JupyterLab, not on this page. Saved outputs are excluded; evidence tables, model responses and environment-specific links appear when you execute the notebook.
"""
    return introduction + "\n" + remainder.strip() + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Report stale or missing pages without writing")
    parser.add_argument("--output-dir", type=Path, default=PAGES)
    args = parser.parse_args()
    sources = sorted(NOTEBOOKS.glob("module-*.ipynb"))
    if not sources:
        parser.error(f"No module notebooks found in {NOTEBOOKS}")
    # Render everything before writing anything, so a failed conversion leaves the pages alone.
    pages = {args.output_dir / source.with_suffix(".adoc").name: render(source) for source in sources}
    stale = [path for path, text in pages.items() if not path.exists() or path.read_text() != text]
    if args.check:
        for path in stale:
            print(f"Stale or missing: {path.name}")
        if stale:
            print("Regenerate with: python publishing-house/showroom/generate.py")
        else:
            print(f"All {len(pages)} Showroom module pages match the notebooks.")
        return bool(stale)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for path in stale:
        path.write_text(pages[path])
    print(f"Generated {len(pages)} module pages ({len(stale)} updated).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Showroom generation failed: {error}", file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stderr, file=sys.stderr)
        sys.exit(1)
