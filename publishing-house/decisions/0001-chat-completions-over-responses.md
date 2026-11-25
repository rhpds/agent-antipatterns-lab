# 0001. The agent uses Chat Completions, not the Responses API

- **Status:** Accepted
- **Date:** 2026-10-13
- **Affects:** modules 1 to 3, the starter agent (`agent/llm.py`)

## Context

vLLM serves both `/v1/chat/completions` and `/v1/responses`. A team analysis
proposed moving module 3 to Responses on the grounds that the server runs the
tool loop, which would shorten the module and remove its loop bugs.

## Decision

The lab agent calls `/v1/chat/completions`, non-streaming, and keeps the tool
loop in the participant's code.

## Reasons

1. **Responses does not execute this lab's tools.** `find_part`, `check_stock`
   and the other tools are Python functions in the participant's workbench. For
   function tools, Responses returns a `function_call` output item, the client
   runs the tool, and the client sends a `function_call_output` back. The loop
   stays client-side either way, so module 3's defects (results never appended,
   the same tool called repeatedly, no stop condition) exist on both APIs.
   Server-side execution applies only to built-in and MCP tool types.
2. **Modules 1 and 2 are written against Chat Completions payloads.** Their
   evidence is an empty `tool_calls` array and the call stranded in `content`.
   Responses has no `tool_calls` field: a parsed call is a `function_call` item
   and a stranded one is text inside a `message` item. Switching would rewrite
   both modules, not just module 3.
3. **Stateful Responses conflicts with the serving design.** `previous_response_id`
   depends on vLLM's response store, which lives in each server process's memory.
   The validated endpoint runs several replicas behind one Service, so a
   follow-up request can reach a replica that never saw the first. Stateless use
   avoids this but resends the full input, which is the Chat Completions pattern.
4. **Non-streaming is required regardless.** Upstream vLLM issue #31871 reports
   the hermes tool-call parser returning raw text in streaming mode, which would
   make module 2's fix appear not to work.

## What carries over from the analysis

The mismatched-parser failure happens on either endpoint, because the parser
runs below the API layer. Module 2's teaching point does not depend on this
decision.

## Consequences

- The model call is isolated in `agent/llm.py` (`call_model()`), so a later
  switch is a contained change.
- Open check: if Red Hat's reference agents for OpenShift AI standardise on
  Responses, add a short module 7 sidebar showing the same loop on Responses.
  Do not restructure modules 1 to 3 for it.
