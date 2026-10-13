"""Knowledge search over Kestrel service bulletins held in PostgreSQL + pgvector.

Connection comes from the standard libpq environment variables:
PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD.

Retrieval quality is not the point of this lab, so the embedding is deliberately
simple: a hashed bag of words, computed in plain Python. Ingest and search must
use the same embed(). To use a real embedding model later, replace embed() and
the vector size DIM in both places that use them (here and ingest_corpus.py).

Try it outside the agent:   python retrieval.py "coolant pump seal service interval"
"""
import hashlib
import json
import math
import re
import sys

import psycopg

DIM = 256
MIN_SCORE = 0.35   # cosine similarity below this is treated as "no passage answers this"
STOPWORDS = {"the", "a", "an", "of", "for", "on", "in", "is", "are", "what", "whats",
             "s", "to", "and", "or", "does", "do", "how", "at", "with", "it", "its", "be", "by"}


def embed(text):
    """Hashed bag-of-words vector, L2 normalised."""
    vec = [0.0] * DIM
    for token in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower()):
        if token in STOPWORDS:
            continue
        digest = hashlib.md5(token.encode()).digest()
        vec[int.from_bytes(digest[:4], "big") % DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def vector_literal(vec):
    return "[" + ",".join(f"{v:.6f}" for v in vec) + "]"


# --- The tool the agent registers in module 5 -----------------------------------

SEARCH_BULLETINS_DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_bulletins",
        "description": "Search Kestrel service bulletins. Returns matching passages with "
                       "their bulletin identifiers. Use for service intervals, procedures "
                       "and fault guidance.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to look up"},
                "product": {"type": "string", "description": "Chiller model to restrict to, e.g. K-400"},
            },
            "required": ["query"],
        },
    },
}


def search_bulletins(query, product=None, top_k=3):
    """Return module 4's contract: category, retryable, detail, plus passages in data."""
    sql = ("SELECT source, section, content, 1 - (embedding <=> %s::vector) AS score "
           "FROM bulletins {where} ORDER BY embedding <=> %s::vector LIMIT %s")
    vec = vector_literal(embed(query))
    where, params = "", [vec]
    if product:
        where = "WHERE %s = ANY(products)"
        params.append(product.upper())
    params += [vec, top_k]
    try:
        with psycopg.connect(connect_timeout=5) as conn:
            rows = conn.execute(sql.format(where=where), params).fetchall()
    except psycopg.Error as exc:
        return {"category": "upstream_unavailable", "retryable": True,
                "detail": f"knowledge store unreachable: {exc}", "data": None}
    passages = [{"source": s, "section": sec, "text": text, "score": round(score, 3)}
                for s, sec, text, score in rows if score >= MIN_SCORE]
    if not passages:
        return {"category": "no_results", "retryable": False,
                "detail": f"no bulletin passage matched {query!r}"
                          + (f" for product {product!r}" if product else ""),
                "data": {"passages": []}}
    return {"category": "ok", "retryable": False, "detail": "", "data": {"passages": passages}}


if __name__ == "__main__":
    print(json.dumps(search_bulletins(" ".join(sys.argv[1:]) or "coolant pump seal service interval"), indent=2))
