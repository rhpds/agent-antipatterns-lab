#!/usr/bin/env python3
"""Generate each module's Showroom guide from its notebook. Never execute notebooks or copy code."""
import argparse
from pathlib import Path
import re
import subprocess
import sys

import nbformat
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


def blocks(markdown, name="notebook"):
    """Split Markdown into blocks at blank lines, keeping ``` fences and <details> whole.
    Forms the guide can't place safely fail loudly instead of slipping through."""
    out, current, fence, details = [], [], False, False
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith(("~~~", "````")):
            raise ValueError(f"{name}: use plain ``` fences; ~~~ and longer fences aren't supported")
        if stripped.startswith("```"):
            if details:
                raise ValueError(f"{name}: an answer reveal must not contain code")
            fence = not fence
        if not fence and stripped.startswith("<details"):
            if details:
                raise ValueError(f"{name}: nested <details> aren't supported")
            details = True
        if not stripped and not fence and not details and current:
            out.append("\n".join(current)); current = []
            continue
        if stripped or current:
            current.append(line)
        if details and line.startswith(("    ", "\t")) and stripped:
            raise ValueError(f"{name}: an answer reveal must not contain code")
        if details and stripped.endswith("</details>"):
            details = False
    if current:
        out.append("\n".join(current))
    return out


SUCCESS = "**This is the module's success signal:**"
QUESTION = "**Your read:**"
DRAFT = "> **Prototype notebook.**"
STEP = re.compile(r"^## (\d+)\. (.+)$")


def guide(notebook, name):
    """The module's Showroom guide, as Markdown: what the module covers, its steps, the
    questions with their answers, how you know you're done, its diagrams and what to do if
    the result differs. Everything comes from the notebook; no code is copied."""
    cells = ["".join(c.source) if isinstance(c.source, list) else c.source
             for c in notebook.cells if c.cell_type == "markdown"]
    if not cells or not cells[0].startswith("# "):
        raise ValueError(f"{name}: the first cell must start with a level-one Markdown heading")
    title, _, opening = cells[0].partition("\n")
    intro = [b for b in blocks(opening, name) if not b.startswith(">")]
    steps, questions, success, diagrams, differs = [], [], [], [], []
    section, previous = None, None
    for cell in cells[1:]:
        for block in blocks(cell, name):
            if block.startswith("## "):
                step = STEP.match(block.splitlines()[0])
                section = "differs" if block.startswith("## If the result differs") else "step" if step else None
                if step:
                    steps.append(step.group(2).strip())
                rest = block.split("\n", 1)[1].strip() if "\n" in block else ""
                if section == "differs" and rest:
                    differs.append(rest)
                previous = None
                continue
            if section == "differs":
                if block.startswith(("<details", "```")):
                    raise ValueError(f"{name}: keep reveals and code out of 'If the result differs'")
                differs.append(block)
            elif block.startswith("```mermaid"):
                diagrams.append(block)
            elif block.startswith(QUESTION):
                questions.append(block)
            elif block.startswith("<details"):
                # An answer reveal belongs to the question right before it, and nothing else.
                if previous is None or not previous.startswith(QUESTION):
                    raise ValueError(f"{name}: an answer reveal must follow a **Your read:** question")
                questions[-1] += "\n\n" + block
            elif block.startswith(SUCCESS):
                success.append(block[len(SUCCESS):].strip())
            previous = block
    parts = [title, ""]
    if intro:
        parts += ["\n\n".join(intro), ""]
    if steps:
        parts += ["## What you'll do in the notebook", ""]
        parts += [f"{i}. {s}" for i, s in enumerate(steps, 1)] + [""]
    if questions:
        parts += ["## Questions to think about", "", "\n\n".join(questions), ""]
    if success:
        done = [s[:1].upper() + s[1:] for s in success]
        parts += ["## How you know it worked", "", "\n\n".join(done), ""]
    if diagrams:
        # Collapsed: a diagram can show the fix, which the participant should find first.
        what = "the module's diagram" if len(diagrams) == 1 else f"the module's {len(diagrams)} diagrams"
        parts += ["## Diagrams", "", f"<details><summary>Show {what}. Open it after you've worked through the "
                  "steps, because it can show the fix.</summary>", "", "\n\n".join(diagrams), "", "</details>", ""]
    if differs:
        # Collapsed too: troubleshooting names the cause of the failure.
        parts += ["## If the result differs", "", "<details><summary>Open this if your result doesn't match "
                  "what the notebook expects. It lists likely causes.</summary>", "", "\n\n".join(differs), "", "</details>", ""]
    return "\n".join(parts)


def render(source):
    notebook = nbformat.read(source, as_version=4)
    # The guide must not silently drop a future attachment or an unknown cell type.
    for cell in notebook.cells:
        if cell.cell_type not in {"markdown", "code"} or cell.get("attachments"):
            raise ValueError(f"{source.name}: only Markdown and code cells without attachments are supported")
    body = markdown_to_asciidoc(guide(notebook, source.name)) + "\n"
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

NOTE: You work through this module in its notebook, `notebooks/{source.name}`, in the *Notebook* tab on the right. This page is your guide to it. The link:{{lab-source-url}}/notebooks/{source.name}[notebook source^] opens on GitHub in a new browser tab.
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
