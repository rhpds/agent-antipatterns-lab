# Implementation provenance

Codex prepared the recent module review candidate and the operational repairs listed below. The implementation commits used the repository owner's Git identity but omitted Codex co-author trailers. This note records those contributions without rewriting published history.

| Work | Commits | Review state |
|---|---|---|
| Tool-server init retry and runtime-ref validation, PR #97 | `2e044adbf8f88d5aab2e4f19ad288243456fc2b9` | Independent Codex review found no actionable issues; 21 focused tests passed; merged into `test` |
| Reset parent-path and symbolic-link safety, PR #99 | `b5e72f53134899aebf334740759416cde8c1e44a` | Independent Codex review found no actionable issues; 19 reset/version tests passed and unsafe base behavior was reproduced; merged into `test` |
| Module checks, model-facing fixes, notebooks, mirrors and execution evidence, PR #98 | `5cee4f6`, `4e1442e`, `55a1fc8`, `94e6ea5`, `5e93411`, `063acb2` | Automated verification is recorded in the review evidence; human content review remains open |
| Review integration of the operational fixes | `821a7ec`, `b8c8681` | Merges completed without conflict resolution; lesson content and model-facing solution code match `063acb2` |

The independent operational reviewer used `gpt-6.1-sol` at medium reasoning effort and did not implement the reviewed changes. These were automated code reviews, not human content or release approvals.

The lab author retains module content review. The designated release reviewer approves promotion from `test` to `main`. Automated authorship, tests and reviews do not establish either approval.

New Codex-assisted commits identify that contribution with a `Co-authored-by: Codex <noreply@openai.com>` trailer alongside any required acceptance trailer. This note is limited to the contributions listed here; it does not assign authorship to earlier repository history.
