"""Load the service-bulletin corpus into PostgreSQL + pgvector.

Run once at provisioning time (needs the `vector` extension available on the server).
Connection comes from PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD.
Safe to re-run: it replaces the table contents.

    python ingest_corpus.py
"""
import pathlib
import re

import psycopg

from retrieval import DIM, embed, vector_literal

BULLETINS = pathlib.Path(__file__).parent / "fixtures" / "bulletins"


def chunks():
    """One chunk per '## ' section, tagged with the bulletin id and products it applies to."""
    for path in sorted(BULLETINS.glob("*.md")):
        text = path.read_text()
        title = text.splitlines()[0].lstrip("# ").strip()
        source = path.stem
        products = sorted(set(re.findall(r"K-\d{3}", text)))
        for block in re.split(r"\n(?=## )", text)[1:]:
            heading, _, body = block.partition("\n")
            section = heading.lstrip("# ").strip()
            content = body.strip()
            yield source, section, products, f"{title}. {section}. {content}", content


def main():
    with psycopg.connect() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute("DROP TABLE IF EXISTS bulletins")
        conn.execute(f"""CREATE TABLE bulletins (
            id serial PRIMARY KEY, source text, section text, products text[],
            content text, embedding vector({DIM}))""")
        n = 0
        for source, section, products, to_embed, content in chunks():
            conn.execute(
                "INSERT INTO bulletins (source, section, products, content, embedding) "
                "VALUES (%s, %s, %s, %s, %s::vector)",
                (source, section, products, content, vector_literal(embed(to_embed))))
            n += 1
    print(f"ingested {n} passages from {len(list(BULLETINS.glob('*.md')))} bulletins")


if __name__ == "__main__":
    main()
