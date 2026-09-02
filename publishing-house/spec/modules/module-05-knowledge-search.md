# Module 5. Giving the agent knowledge it can search

### Brief Overview

The agent can call tools, terminate correctly, and report failure honestly. What it still cannot do is answer anything outside the model's training data, and when asked it invents a plausible answer rather than admitting the gap. Participants add a retrieval tool over a pre-populated corpus, so that answers come from retrieved passages instead of model memory.

Because module 4's error contract is already in place, the interesting case is available immediately: a query that retrieves nothing returns `no_results` and the agent says so, rather than falling back on invention. That contrast is the module's point, and it is why retrieval comes after the contract rather than before it.

### Audience and Time

Technical Sellers and Services, intermediate. 14 minutes, the shortest of the build modules.

Requires module 4. Without the error contract, an empty retrieval is indistinguishable from a successful one and the module's success signal does not exist.

### Learning Objectives

- Integrate a searchable knowledge source so the agent grounds its answers in retrieved content rather than in model memory.
- Verify that a retrieval miss produces an explicit gap rather than an invented answer.

### Lab Structure

| Section | Title | Duration |
|---------|-------|----------|
| 1 | The confident invention | 3 min |
| 2 | Register the retrieval tool | 5 min |
| 3 | Ask again, grounded | 4 min |
| 4 | Ask something outside the corpus | 2 min |

### Detailed Steps

1. Ask the agent a question whose answer lives only in the lab's document corpus, which the model has never seen.
2. Observe a specific, plausible, wrong answer. Note that nothing in module 4's work catches this, because no tool failed. The model simply answered from memory.
3. Confirm in the trace that no retrieval happened, because no retrieval tool exists yet.
4. Inspect the pre-populated knowledge source. Confirm the corpus is already ingested and searchable, and run one query directly against it outside the agent to see what a passage looks like.
5. Register the supplied retrieval tool with the agent: its declaration, its parameters, and its return shape, which uses module 4's contract.
6. Note the return shape carries the retrieved passages and their source identifiers, not just concatenated text. The source identifier is what makes the answer checkable.
7. Re-run the original question.
8. Confirm in the trace that the retrieval tool was called, that passages came back, and that the answer's content corresponds to a passage rather than to the model's prior. **This is the module's success signal.**
9. Ask a question deliberately outside the corpus.
10. Confirm the retrieval returns `no_results` and that the agent reports the gap rather than inventing. Compare directly against the module's opening run, which invented.
11. Note the remaining limitation for module 7: grounding makes the answer checkable, it does not make it correct, and nothing yet verifies that the retrieved passage actually answers the question asked.

### Key Takeaways

- An agent with no knowledge source does not decline to answer. It answers from the model's prior and sounds identical either way.
- Retrieval returning source identifiers alongside passages is what lets a reader check an answer. Concatenated text without provenance is not much better than invention.
- A retrieval miss is only useful if the contract can express it, which is why the error work came first.
- Grounding constrains where the answer comes from. It does not guarantee the passage was the right one.

### Infrastructure Notes

- **The corpus is read-only and ingested at provisioning time.** Nothing is written during the lab. This keeps the vector store a shared, pre-warmed service and avoids per-participant ingestion cost inside a 14-minute module.
- **Vector store settled 2026-09-02: PostgreSQL with the pgvector extension**, deployed as a plain Deployment via GitOps, queried directly by the retrieval tool. Red Hat OpenShift AI is standardizing on pgvector as a remote vector store provider, so a participant meets the direction the platform is going rather than an arbitrary pick. No operator is required, and nothing here is pre-GA.
- **The RHOAI built-in pgvector provider integration is deliberately not used.** It is EA2 as of 3.5. Querying Postgres directly from the retrieval tool needs nothing pre-GA, keeps this design's non-GA dependency count at one, and stays forward-compatible with that integration when it reaches GA. If it has GA'd by authoring time, switching to it is a contained change to one tool.
- **Alternatives were checked against the dev cluster and rejected.** There is no Milvus, Qdrant, Weaviate or Chroma operator in any catalog source. The Milvus path runs through OGX, the renamed Llama Stack, which is being de-emphasized and is mid-rename. Red Hat Data Grid and certified Postgres or Elasticsearch operators all work but add an operator dependency for no teaching benefit at this module's depth.
- **The corpus must be genuinely outside the model's training data.** Synthetic internal documentation for a fictional product works. Anything drawn from public sources risks the model answering correctly from memory, which destroys the opening beat.
- **The opening invention must be reliable rather than stochastic.** Choose a question where the model's prior is strong and specific, so it invents confidently every time rather than hedging. Verify this against the actual served model during authoring, not against a different one.
- **The out-of-corpus question must be unambiguous.** It should be obviously unanswerable from the corpus, so the `no_results` path is clearly the correct behaviour and not a retrieval tuning problem.
- **Scope discipline.** This module deliberately does not tune retrieval quality, chunking, or embedding choice. The objective is a grounded agent, not a tuned retriever. Three existing assets already own retrieval in depth and going deeper here would duplicate one of them: LB1782 in this same topic slot builds a full RAG pipeline over enterprise documentation, `showroom-agentic-ai-llamastack` carries a dedicated RAG module, and `enterprise-rag-intel-continuum` is an entire lab about the pipeline. Checked against the published repositories on 2026-09-02.
