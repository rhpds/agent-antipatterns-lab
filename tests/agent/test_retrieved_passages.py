"""A trace shows what knowledge search retrieved (acceptance/lab/mlflow-retrieved-passages.feature).

search_bulletins records a RETRIEVER span under its tool span. Its output is the passages
the agent received, as MLflow documents, each labelled with its bulletin (doc_uri), which
the trace view shows as retrieved documents. The pgvector fixtures come from
test_knowledge_and_gateway.
"""
import pytest

from test_knowledge_and_gateway import ingested, pg  # noqa: F401  (pytest fixtures)


def retriever_spans(uri, question_tag):
    mlflow = pytest.importorskip("mlflow")
    mlflow.set_tracking_uri(uri)
    exp = mlflow.get_experiment_by_name("kestrel-agent")
    traces = [t for t in mlflow.search_traces(locations=[exp.experiment_id], return_type="list")
              if t.info.tags.get("question") == question_tag]
    assert len(traces) == 1
    spans = traces[0].data.spans
    by_id = {s.span_id: s for s in spans}
    found = [s for s in spans if s.span_type == "RETRIEVER"]
    for s in found:   # each sits under the search_bulletins tool span
        assert by_id[s.parent_id].span_type == "TOOL" and by_id[s.parent_id].name.endswith("search_bulletins")
    return found


def test_the_f21_trace_shows_the_passages_the_agent_read(work, ingested, tmp_path):
    """Scenario: The F-21 trace shows the passages the agent read"""
    uri = f"sqlite:///{tmp_path}/mlflow.db"
    work.repoint_to_validated()
    summary, _ = work.agent("m5", env={**ingested, "MLFLOW_TRACKING_URI": uri})
    (span,) = retriever_spans(uri, "m5")
    docs = span.outputs
    passages = summary["tool_calls"][0]["result"]["data"]["passages"]
    assert [d["page_content"] for d in docs] == [p["text"] for p in passages]
    assert [d["metadata"]["doc_uri"] for d in docs] == [p["source"] for p in passages]
    assert "SB-2024-102" in {d["metadata"]["doc_uri"] for d in docs}
    assert span.inputs["query"] == "F-21"


def test_an_out_of_corpus_search_shows_it_retrieved_nothing(work, ingested, tmp_path):
    """Scenario: An out-of-corpus search shows it retrieved nothing"""
    uri = f"sqlite:///{tmp_path}/mlflow.db"
    work.repoint_to_validated()
    summary, _ = work.agent("m5-miss", env={**ingested, "MLFLOW_TRACKING_URI": uri})
    assert summary["tool_calls"][0]["result"]["category"] == "no_results"
    (span,) = retriever_spans(uri, "m5-miss")
    assert span.outputs == []


def test_without_tracing_search_returns_the_same(work, ingested):
    """The span is only a record: with tracing off, search_bulletins answers exactly as before."""
    work.repoint_to_validated()
    summary, _ = work.agent("m5", env=ingested)
    call = summary["tool_calls"][0]
    assert call["result"]["category"] == "ok"
    assert "SB-2024-102" in {p["source"] for p in call["result"]["data"]["passages"]}
