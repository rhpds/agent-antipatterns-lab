#!/usr/bin/env python3
"""Check each built module guide against its notebook: steps, questions, diagrams, links, and no copied code."""
import argparse
import json
import re
from pathlib import Path
import subprocess

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, default=ROOT / "www")
    parser.add_argument("--source-ref", default=subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=ROOT, text=True).strip())
    args = parser.parse_args()
    count = 0
    for source in sorted((ROOT / "notebooks").glob("module-*.ipynb")):
        notebook = json.loads(source.read_text())
        html = (args.site_dir / "modules" / source.with_suffix(".html").name).read_text()
        page = BeautifulSoup(html, "html.parser")
        article = page.select_one("article.doc")
        assert article is not None, f"{source.name}: no document body"
        cells = [c for c in notebook["cells"] if c["cell_type"] == "markdown"]
        markdown = "\n".join("".join(c["source"]) for c in cells)
        # A guide, not a copy: the code lives only in the notebook.
        assert not article.select(".listingblock, .literalblock"), f"{source.name}: the guide copies notebook code"
        steps = re.findall(r"^## \d+\. (.+)$", markdown, re.MULTILINE)
        # Asciidoctor curls apostrophes; compare the plain text.
        listed = [li.get_text(" ", strip=True).replace("\u2019", "'") for li in article.select(".olist li")]
        assert [s.strip() for s in steps] == listed[:len(steps)], f"{source.name}: steps differ from the notebook"
        assert len(article.select(".mermaid")) == markdown.count("```mermaid"), f"{source.name}: missing diagrams"
        answers = markdown.count("<details")
        diagrams = 1 if "```mermaid" in markdown else 0
        differs = 1 if "## If the result differs" in markdown else 0
        assert len(article.select("details > summary")) == answers + diagrams + differs, f"{source.name}: missing reveals"
        text = article.get_text(" ")
        questions = len(re.findall(r"^\*\*Your read:\*\*", markdown, re.MULTILINE))
        assert text.count("Your read:") == questions, f"{source.name}: questions differ from the notebook"
        if "**This is the module's success signal:**" in markdown:
            assert article.find(id="_how_you_know_it_worked"), f"{source.name}: no 'How you know it worked'"
        expected_url = f"https://github.com/rhpds/agent-antipatterns-lab/blob/{args.source_ref}/notebooks/{source.name}"
        assert article.find("a", href=expected_url), f"{source.name}: wrong notebook source link"
        for link in article.select("a[href]"):
            href = link["href"]
            assert "{lab-source" not in href and not href.startswith("../agent/"), f"{source.name}: unresolved link {href}"
            if "/blob/" in href:
                assert f"/blob/{args.source_ref}/" in href, f"{source.name}: wrong source branch in {href}"
                # GitHub refuses to load inside Showroom's frame.
                assert link.get("target") == "_blank", f"{source.name}: {href} would open inside Showroom"
        # A repository link written as a code span must still render as code.
        code_named = set(re.findall(r"\[`([^`]+)`\]\((?!https?:)[^)]+\)", markdown))
        for link in article.select("a[href*='/blob/']"):
            if link.get_text() in code_named:
                assert link.select("code"), f"{source.name}: link text `{link.get_text()}` lost its code formatting"
        assert article.find("h1"), f"{source.name}: no page title"
        assert "Prototype notebook." not in article.get_text(), f"{source.name}: draft label on the guide"
        count += 1
        print(f"Verified {source.name}: {len(steps)} steps, {len(article.select('.mermaid'))} diagrams")
    assert count == 7, f"Expected seven modules, found {count}"
    print("All seven module guides match their notebooks' steps, questions, diagrams and source links.")


if __name__ == "__main__":
    main()
