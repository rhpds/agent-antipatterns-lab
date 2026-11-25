#!/usr/bin/env python3
"""Check each built module guide against its notebook: steps, questions, diagrams, links, and no copied code."""
import argparse
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]


def workbench_url():
    """The workbench URL the guides link to, built from content/antora.yml's default attributes.
    Showroom replaces those with each participant's user and cluster domain."""
    antora = (ROOT / "content/antora.yml").read_text()

    def default(name):
        match = re.search(rf"^\s+{name}: '([^']+)'$", antora, re.MULTILINE)
        assert match, f"content/antora.yml: no default for {name}"
        return match.group(1).removesuffix("@")
    return (f"https://rh-ai.{default('openshift_cluster_ingress_domain')}/notebook/{default('user')}-app"
            "/kestrel-agent/lab/tree/agent-antipatterns-lab")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, default=ROOT / "www")
    # The guides link to the participant's workbench, not to a branch on GitHub, so no ref is
    # checked. The option stays so existing build commands keep working.
    parser.add_argument("--source-ref", help="Ignored")
    args = parser.parse_args()
    workbench = workbench_url()
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
        expected_url = f"{workbench}/notebooks/{source.name}"
        notebook_link = article.find("a", href=expected_url)
        assert notebook_link and notebook_link.get_text().replace("\u2019", "'") == "Open this module's notebook", \
            f"{source.name}: wrong notebook link"
        for link in article.select("a[href]"):
            href = link["href"]
            assert "{" not in href and not href.startswith("../"), f"{source.name}: unresolved link {href}"
            assert "github.com/rhpds/agent-antipatterns-lab" not in href, f"{source.name}: {href} still points to GitHub"
            if href.startswith(workbench):
                # Each file link opens a file that exists in the lab folder.
                path = href[len(workbench) + 1:]
                assert (ROOT / path).exists(), f"{source.name}: {href} names a file the lab doesn't have"
                # A new tab keeps the guide beside the Notebook tab.
                assert link.get("target") == "_blank", f"{source.name}: {href} would open inside Showroom"
        # A repository link written as a code span must still render as code.
        code_named = set(re.findall(r"\[`([^`]+)`\]\((?!https?:)[^)]+\)", markdown))
        for link in article.select("a[href]"):
            if link["href"].startswith(workbench) and link.get_text() in code_named:
                assert link.select("code"), f"{source.name}: link text `{link.get_text()}` lost its code formatting"
        assert article.find("h1"), f"{source.name}: no page title"
        assert "Prototype notebook." not in article.get_text(), f"{source.name}: draft label on the guide"
        count += 1
        print(f"Verified {source.name}: {len(steps)} steps, {len(article.select('.mermaid'))} diagrams")
    assert count == 7, f"Expected seven modules, found {count}"
    print("All seven module guides match their notebooks' steps, questions, diagrams and workbench links.")


if __name__ == "__main__":
    main()
