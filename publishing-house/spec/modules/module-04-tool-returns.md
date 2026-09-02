# Module 4. Tool returns that tell the truth

### Brief Overview

The agent now calls tools and terminates properly, so the next failure is one it reports as a success. A tool is asked for something it cannot supply, and rather than failing it returns a well-formed envelope with an empty result set and a 200 status. The model reads that as valid data meaning "nothing found", summarises it fluently, and the agent reports success on an answer built from nothing.

Participants find the empty result in the trace, then change the contract the tools return: a category, a retryable flag, and a detail string, so that failure is representable at all. This is the module that makes every later layer debuggable, which is why it comes before retrieval.

### Audience and Time

Technical Sellers and Services, intermediate. 14 minutes.

Requires module 3. Tool results must be reaching the model before the shape of those results matters.

### Learning Objectives

- Implement a structured tool-error contract of category, retryable flag and detail so that failed tool calls surface instead of becoming confident empty answers.
- Analyze a trace to distinguish a tool that returned no data from a tool that failed to run.

### Lab Structure

| Section | Title | Duration |
|---------|-------|----------|
| 1 | The success that is not one | 3 min |
| 2 | Find the empty envelope | 3 min |
| 3 | Give failure a shape | 6 min |
| 4 | Re-run and see it surface | 2 min |

### Detailed Steps

1. Run the agent on the supplied question whose subject falls outside what the backing data covers.
2. Observe a fluent answer that reads as authoritative and reports no problem.
3. Open the trace. The tool was called, returned quickly, and the run terminated cleanly on the model's stop condition. Every signal says success.
4. Open the tool's actual return value. It is a valid object with an empty results array and no indication that anything went wrong.
5. Identify the ambiguity: this exact response is what the tool returns both when the query legitimately matched nothing and when the query was malformed, the backend was unreachable, or the parameters were rejected. Those cases are indistinguishable to the model.
6. Open the tool wrapper code. Note that it catches exceptions and returns the empty envelope for all of them.
7. Apply the supplied error contract. Every tool return carries a category such as `ok`, `no_results`, `bad_request`, `upstream_unavailable`; a boolean indicating whether a retry could help; and a detail string carrying the underlying cause.
8. Update the tool wrapper so failures populate the contract instead of collapsing into an empty success.
9. Update the loop so a non-`ok` category is passed back to the model as a distinct result rather than as data, and so a retryable failure is retried once before being surfaced.
10. Re-run the same question.
11. Confirm the run now surfaces a categorized failure rather than a confident answer. **This is the module's success signal.**
12. Re-run a question the data does cover, and confirm `no_results` and `ok` are now distinguishable in the trace.

### Key Takeaways

- A well-formed empty result is the most dangerous tool response, because every layer above it reads it as valid.
- "The tool returned successfully" and "the tool did what was asked" are different claims, and only the contract can separate them.
- Catching every exception and returning a default is how silent failure gets built deliberately, usually for good reasons, usually early.
- A retryable flag belongs in the contract rather than in the caller's guesswork about which errors are transient.
- The model can only reason about failure it can see. Anything flattened before it reaches the model is invisible to the agent's reasoning.

### Infrastructure Notes

- **The empty envelope must be structurally guaranteed.** The supplied tool wrapper returns the same object for a legitimate empty match and for a thrown exception. Do not rely on the model choosing to misread anything.
- **At least one failure case must be non-obvious.** A tool that is simply unreachable is easy. The instructive case is a query the backend accepts and answers with nothing because a parameter was silently dropped, which looks identical to a genuine miss.
- **The retry path must not mask the lesson.** Retrying a `no_results` is wrong and must be visible as wrong. Only `upstream_unavailable` should retry.
- **The categories must be few and obvious.** Four is enough. A larger taxonomy turns the module into a design discussion and it only has 14 minutes.
- **This module's contract is a hard dependency for module 5.** Retrieval that returns nothing has to be distinguishable from retrieval that failed, and module 5's success signal depends on that distinction already existing.
- Tool call ids from module 3 must be correct, or categories attach to the wrong call and the trace becomes unreadable.
