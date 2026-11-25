# Acceptance coverage audit

The approved scenarios are the contract. Test names establish traceability; the assertions and retained run records establish what was actually checked. Fast CI uses a mock model plus a real disposable database. Candidate notebook execution uses the deployed model and lab services. Neither uses an LLM judge.

| Area | Actual evidence | Boundary or correction |
|---|---|---|
| Stronger prompt and endpoint parsing | Saved system prompts, first response payloads, absence of executed calls before repointing, real pump returned afterward; endpoint comparison also tests an unreachable peer | The author approved checking the stronger saved request instead of requiring different output wording. The exact amendment is committed separately in `4e1442e`. |
| Loop failure and repair | Six identical starting lookups, assistant/tool message IDs, stop reason and dependent Denver stock request using the returned pump number | New counterexamples reject unrelated tool calls and placeholder stock inputs. |
| Error contract | Portland `bad_request`, valid-depot `no_results`, successful stock, transient-only retry and a failed-check explanation in the answer | The older live run had the right category but still called it unavailable stock. Added negative examples expose that failure. |
| Retrieval | Real pgvector ingestion/search in CI, expected bulletin and cause, unsupported-product miss, RETRIEVER document IDs/text and parent tool span | Candidate checks require the source ID in the answer. A citation marker does not prove that every suggested action follows from the source. |
| Participant independence | Each participant's workbench in their own project; the live check confirms neither participant can reach the other's workbench | The 2026-11-25 scope cut removed the gateway and its per-project tool registrations, so there are none left to compare. This isn't an authorization or penetration test. |
| Regression and MLflow evaluation | Five deterministic cases (six before the 2026-11-25 scope cut removed the gateway case), per-case terminal/report/assessment equality, named run, one recorded trace per case and count metrics; earlier-state partial report and unavailable-MLflow behavior | Wrong tools, uncited retrieval and unrelated misses can't pass, nor can a run the model cut off. Fixed answer markers are bounded checks, not a general natural-language judge. |
| Trace links, costs and agent versions | Exact trace IDs/workspaces, saved payload link equality, optional/unreachable tracing, per-call token aggregation, fixed-loop lower token usage, module-start and modified version names | CI records through local MLflow storage; live notebooks exercise the deployed tracking server. The review does not claim that every MLflow UI interaction was manually completed. |
| Reset and notebook integrity | Backups preserve edited/staged files, repeated resets, invalid-path failure, clean notebook outputs and parseable code cells | The closing module's cells run in order straight after its reset, with no setup step. |
| Documentation and incomplete checks | Generator drift/deletion tests; each Showroom guide checked against its notebook (steps, questions, reveals, diagrams, source links, no copied code); excluded saved outputs; failed/missing readiness/doc evidence cannot mark a module ready | A built Showroom guide is separate from a published temporary Showroom or an executed notebook. |
| Infrastructure and release policy | Source/identity Helm checks and effective-policy/live readiness tests exist | Fresh catalog provisioning and enforced main approval are separate outstanding dependencies. They are not inferred from this review. |

## Counterexamples observed failing before repair

Eight synthetic wrong records originally passed the regression verdicts: wrong tool, wrong part, invented dependent stock input, error on an unrelated tool, omitted source citation, unrelated empty result, failed delivery call and wrong delivery time. The new tests first failed against those permissive verdicts. A ninth case exposed a correct error envelope paired with a confident out-of-stock answer. Live-module negative tests also first failed because the original verifier accepted that answer and the incorrect gateway chain.

A positive boundary test then exposed an overstrict comparison: an additional valid seal-kit stock lookup must not invalidate the requested pump's matching facts. The comparison now checks those facts directly. A separate negative test verifies that a stronger prompt which was never sent cannot satisfy module 2.

The actual earlier run records were reassessed with the stronger checks in [historical-reassessment.json](evidence/historical-reassessment.json). Their original green result remains historical evidence, not proof of the stricter verdicts.

The live verifier also rejects a module 5 start that does not demonstrate the known unsupported cause claim. The narrowed module 4 solution leaves the original system prompt unchanged until a tool actually fails; request-level regression assertions protect that boundary. The model output allowance is now 4,096 tokens including reasoning. Token usage and latency can therefore be higher; no concurrency claim follows from the two-participant run.

## Additional criterion proposed for approval

The current F-21 checks establish the known cause and a visible source ID. They do not verify that every recommended maintenance action is supported by a retrieved passage. That remains a specific human review point in modules 5 and 6. A stronger criterion would be: given retrieved passages that document only a symptom, when the participant asks for remediation, the answer distinguishes documented facts from unverified suggested actions and does not attribute unsupported actions to a bulletin. This would extend the current bounded checks; it has not been added to a locked feature or implemented as an LLM judge.

## Scenario-to-test index

Each link points to the actual test definition; the evidence scope and limitations are described above.

### checks

[Approved scenarios](../../acceptance/lab/checks.feature)

- A check that can't run is reported as failing, not passing: [test_a_bulletin_database_that_cannot_start_fails_the_module_5_and_6_checks](../../tests/agent/test_checks_report_failing.py#L42), [test_missing_podman_fails_the_module_5_and_6_checks](../../tests/agent/test_checks_report_failing.py#L36)

### end-to-end

[Approved scenarios](../../acceptance/lab/end-to-end.feature)

- Readiness means participants can begin the lab: [test_readiness_means_participants_can_begin_the_lab](../../tests/e2e/test_workshop.py#L61)
- Every module works through the participant instructions: [test_live_closing_module_needs_every_case_to_pass](../../tests/agent/test_live_module_verdicts.py#L76), [test_live_module4_rejects_an_answer_that_still_calls_bad_input_out_of_stock](../../tests/agent/test_live_module_verdicts.py#L50), [test_every_module_works_through_the_participant_instructions](../../tests/e2e/test_workshop.py#L85)
- Incomplete testing cannot be mistaken for success: [test_live_checks_without_environment_write_failure_report](../../tests/agent/test_live_checks.py#L12)
- Each module is ready for David to review: [test_each_module_is_ready_for_david_to_review](../../tests/e2e/test_workshop.py#L112)
- The reviewed release is the release promoted: [test_the_reviewed_release_is_the_release_promoted](../../tests/e2e/test_workshop.py#L121)
- Participants complete the lab independently: [test_participants_complete_the_lab_independently](../../tests/e2e/test_workshop.py#L98)

### mlflow-agent-versions

[Approved scenarios](../../acceptance/lab/mlflow-agent-versions.feature)

- Every trace says which build of the agent produced it: [test_every_trace_says_which_build_produced_it](../../tests/agent/test_agent_versions.py#L48)
- The evaluation run names the agent version it tested: [test_the_evaluation_run_names_the_agent_version_it_tested](../../tests/agent/test_agent_versions.py#L66)

### mlflow-regression-evaluation

[Approved scenarios](../../acceptance/lab/mlflow-regression-evaluation.feature)

- The regression run is recorded as an evaluation: [test_the_regression_run_is_recorded_as_an_evaluation](../../tests/agent/test_regression_evaluation.py#L41)
- MLflow's verdicts match the terminal's: [test_mlflows_verdicts_match_the_terminals](../../tests/agent/test_regression_evaluation.py#L62)
- Without tracing, the regression run is unchanged: [test_without_tracing_the_regression_run_is_unchanged](../../tests/agent/test_regression_evaluation.py#L76)

### mlflow-retrieved-passages

[Approved scenarios](../../acceptance/lab/mlflow-retrieved-passages.feature)

- The F-21 trace shows the passages the agent read: [test_the_f21_trace_shows_the_passages_the_agent_read](../../tests/agent/test_retrieved_passages.py#L28)
- An out-of-corpus search shows it retrieved nothing: [test_an_out_of_corpus_search_shows_it_retrieved_nothing](../../tests/agent/test_retrieved_passages.py#L42)

### mlflow-token-usage

[Approved scenarios](../../acceptance/lab/mlflow-token-usage.feature)

- The looping run's trace shows what it cost: [test_the_looping_run_shows_its_token_total](../../tests/agent/test_token_usage.py#L26)
- The fixed loop costs less than the looping one: [test_the_fixed_loop_costs_less_than_the_looping_one](../../tests/agent/test_token_usage.py#L40)

### modules

[Approved scenarios](../../acceptance/lab/modules.feature)

- Module 1's agent answers confidently without calling a tool: [test_module1_confident_answer_no_tool_calls_and_payloads_saved](../../tests/agent/test_starting_state.py#L9)
- The payload viewer shows the module 1 evidence: [test_payload_viewer_shows_the_evidence](../../tests/agent/test_starting_state.py#L27)
- A stronger prompt doesn't make the tools fire: [test_live_module2_rejects_a_stronger_prompt_that_was_never_sent](../../tests/agent/test_live_module_verdicts.py#L33), [test_module2_sends_the_stronger_prompt_without_executing_tools](../../tests/agent/test_starting_state.py#L37)
- The endpoint whose parser matches the model makes the tool fire: [test_module2_repoint_populates_tool_calls_and_tool_executes](../../tests/agent/test_starting_state.py#L53)
- Comparing endpoints shows both responses side by side: [test_compare_endpoints_reports_an_unreachable_endpoint_and_carries_on](../../tests/agent/test_starting_state.py#L98), [test_compare_endpoints_sends_exactly_what_the_agent_sends](../../tests/agent/test_starting_state.py#L108), [test_compare_endpoints_shows_both_responses_side_by_side](../../tests/agent/test_starting_state.py#L84)
- Module 3's starting loop calls the same tool until the turn cap: [test_module3_starter_loop_repeats_until_cap](../../tests/agent/test_starting_state.py#L65)
- With the supplied loop fix, the agent stops when the model is done: [test_module3_fix_terminates_on_stop_with_results_in_messages](../../tests/agent/test_loop_and_tool_fixes.py#L11)
- Module 4's unknown depot reads as out of stock: [test_module4_swallowed_failure_then_surfaced](../../tests/agent/test_loop_and_tool_fixes.py#L51)
- With the error contract, a bad depot is no longer mistaken for out of stock: [test_error_guidance_does_not_change_the_unsupported_knowledge_start](../../tests/agent/test_loop_and_tool_fixes.py#L91), [test_module4_no_results_and_ok_are_distinguishable](../../tests/agent/test_loop_and_tool_fixes.py#L72), [test_module4_only_upstream_unavailable_is_retried](../../tests/agent/test_loop_and_tool_fixes.py#L128), [test_module4_swallowed_failure_then_surfaced](../../tests/agent/test_loop_and_tool_fixes.py#L51), [test_a_categorized_error_cannot_hide_a_confident_out_of_stock_answer](../../tests/agent/test_regression_verdicts.py#L59)
- Without knowledge search, the agent invents a cause for fault F-21: [test_module5_invention_then_grounded_then_explicit_miss](../../tests/agent/test_knowledge_and_regression.py#L83), [test_live_module5_rejects_a_start_that_did_not_demonstrate_the_invention](../../tests/agent/test_live_module_verdicts.py#L40), [test_error_guidance_does_not_change_the_unsupported_knowledge_start](../../tests/agent/test_loop_and_tool_fixes.py#L91)
- With knowledge search, the F-21 answer follows the service bulletin: [test_module5_invention_then_grounded_then_explicit_miss](../../tests/agent/test_knowledge_and_regression.py#L83)
- The agent says so when the bulletins have nothing: [test_module5_invention_then_grounded_then_explicit_miss](../../tests/agent/test_knowledge_and_regression.py#L83)
- The regression run checks every earlier case against the assembled agent: [test_module6_full_regression_against_assembled_agent](../../tests/agent/test_knowledge_and_regression.py#L105), [test_regression_reports_per_case_on_each_state](../../tests/agent/test_loop_and_tool_fixes.py#L141), [test_regression_rejects_evidence_that_does_not_prove_the_case](../../tests/agent/test_regression_verdicts.py#L39), [test_valid_tool_results_are_accepted_with_or_without_a_name_prefix](../../tests/agent/test_regression_verdicts.py#L45)
- Resetting to a module's start keeps the participant's edits: [test_a_file_obstructing_a_parent_stops_reset_without_changing_any_edits](../../tests/agent/test_reset.py#L161), [test_a_genuinely_missing_parent_directory_can_still_be_restored](../../tests/agent/test_reset.py#L200), [test_reset_builds_each_module_start_and_backs_up_edits](../../tests/agent/test_reset.py#L36), [test_resetting_to_module_4_restores_its_start_and_keeps_the_edits](../../tests/agent/test_reset.py#L60), [test_symbolic_links_are_preserved_instead_of_restored_through](../../tests/agent/test_reset.py#L177)

### provisioning

[Approved scenarios](../../acceptance/lab/provisioning.feature)

- A new workshop uses deployable lab sources: [test_a_new_workshop_uses_deployable_lab_sources](../../tests/agent/test_provisioning_contract.py#L20)
- Each participant gets their own workbench: [test_each_participant_gets_their_own_workbench](../../tests/agent/test_provisioning_contract.py#L32)

### regression-cut-off-runs

[Approved scenarios](../../acceptance/lab/regression-cut-off-runs.feature)

- A regression case whose run was cut off doesn't pass: [test_a_case_cut_off_before_its_answer_fails_and_says_to_rerun](../../tests/agent/test_cut_off_runs.py#L23), [test_the_regression_set_reports_a_cut_off_case_as_failed](../../tests/agent/test_cut_off_runs.py#L32), [test_live_closing_module_rejects_a_cut_off_case](../../tests/agent/test_live_module_verdicts.py#L81)
- Any regression case cut off before its answer fails: [test_any_cut_off_case_fails_whatever_its_check_found](../../tests/agent/test_cut_off_runs.py#L47)

### short-closing-module

[Approved scenarios](../../acceptance/lab/short-closing-module.feature)

- The closing module checks every fix in one run: [test_the_closing_module_checks_every_fix_in_one_run](../../tests/agent/test_short_closing_module.py#L142)
- The closing module needs no setup of its own: [test_the_closing_module_needs_no_setup_of_its_own](../../tests/agent/test_short_closing_module.py#L162)
- Comparing runs in MLflow is optional: [test_comparing_runs_in_mlflow_is_optional](../../tests/agent/test_short_closing_module.py#L182)
- The checklist names where tool access is governed: [test_the_checklist_names_where_tool_access_is_governed](../../tests/agent/test_short_closing_module.py#L210)

### trace-links-untraced-payloads

[Approved scenarios](../../acceptance/lab/trace-links-untraced-payloads.feature)

- The payloads of an untraced run say nothing about traces: [test_the_payloads_of_an_untraced_run_say_nothing_about_traces](../../tests/agent/test_trace_links.py#L55)

### trace-links

[Approved scenarios](../../acceptance/lab/trace-links.feature)

- A run links to its own trace: [test_a_run_links_to_its_own_trace](../../tests/agent/test_trace_links.py#L21)
- Without tracing, nothing about traces is printed: [test_without_tracing_nothing_about_traces_is_printed](../../tests/agent/test_trace_links.py#L32)
- A run whose trace couldn't be recorded says so: [test_a_run_whose_trace_could_not_be_recorded_says_so](../../tests/agent/test_trace_links.py#L39)
- The payloads view links to the same run's trace: [test_the_payloads_view_links_to_the_same_runs_trace](../../tests/agent/test_trace_links.py#L47)

