#!/usr/bin/env python3
"""Check the built HTML against all seven notebooks, including code and interactive markup."""
import argparse
import json
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
        expected_code = ["".join(c["source"]).rstrip() for c in notebook["cells"] if c["cell_type"] == "code"]
        actual_code = [c.get_text() for c in article.select("code.language-python")]
        assert actual_code == expected_code, f"{source.name}: code cells differ or are out of order"
        markdown = "\n".join("".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "markdown")
        assert len(article.select(".mermaid")) == markdown.count("```mermaid"), f"{source.name}: missing diagrams"
        assert len(article.select("details > summary")) == markdown.count("<details>"), f"{source.name}: missing answer reveals"
        expected_url = f"https://github.com/rhpds/agent-antipatterns-lab/blob/{args.source_ref}/notebooks/{source.name}"
        assert article.find("a", href=expected_url), f"{source.name}: wrong notebook source link"
        for link in article.select("a[href]"):
            href = link["href"]
            assert "{lab-source" not in href and not href.startswith("../agent/"), f"{source.name}: unresolved link {href}"
            if "/blob/" in href:
                assert f"/blob/{args.source_ref}/" in href, f"{source.name}: wrong source branch in {href}"
        assert article.find("h1"), f"{source.name}: no page title"
        assert "Prototype notebook." in article.get_text(), f"{source.name}: draft label lost"
        count += 1
        print(f"Verified {source.name}: {len(actual_code)} code cells, {len(article.select('.mermaid'))} diagrams")
    assert count == 7, f"Expected seven modules, found {count}"
    print("All seven HTML mirrors preserve code, diagrams, answer reveals and source links.")


if __name__ == "__main__":
    main()
