# Notebook mirrors in Showroom

David approved a readable mirror of all seven Jupyter notebooks on November 11, 2026, and asked to generate it from the material already present. Readers must be able to inspect the whole lesson without provisioning a workbench.

The notebooks are the authored source for the seven module pages. Use Jupyter nbconvert's AsciiDoc exporter, backed by Pandoc, with a small Antora adapter. Preserve Markdown and code cells in order, including headings, Mermaid diagrams and answer reveals. Preserve the prototype wording; conversion is not editorial approval. Code cells are Python listings, including IPython syntax. Do not execute notebooks or publish saved outputs; the current notebooks contain none. Explain that environment-dependent evidence appears only during execution rather than inventing examples.

Resolve repository-relative links against the same branch on GitHub using an Antora attribute, so test documents point at test sources. Leave environment-dependent links as visible code rather than constructing fake live URLs. Keep the existing module filenames and navigation, and replace the empty overview with a short index explaining the mirror and linking all seven modules.

A local command regenerates the committed pages. A check mode reports missing or stale pages without modifying them. CI checks deterministic regeneration and builds Antora on pull requests and pushes to dev, test and main. A preview artifact allows inspection without deploying the lab. Generation and site building do not advance Publishing House stages, promote branches or update a live environment.

Validation covers actual notebook content, preservation of code, answer reveals and diagrams, repository links, exclusion of outputs, and stale-page detection. Build and inspect the HTML for all seven modules, including a rendered browser check. Keep source and generated documentation in one reviewable feature branch.

Reuse: nbconvert already provides notebook parsing and AsciiDoc export, and Pandoc provides Markdown conversion. Use those maintained projects rather than writing a Markdown parser. The adapter handles only this repository's Antora conventions.
