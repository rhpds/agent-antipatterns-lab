# 0004. Module reset: a `reset.py` in the agent directory

- **Status:** Accepted
- **Date:** 2026-10-14
- **Decided by:** the agent driving LB8000 decisions, on David's delegation. David can overturn it.
- **Affects:** `agent/reset.py`, the facilitator guide, module content (a recovery line per module)

## Context

`design.md` requires automation to provide "a reset path that returns any module to
its starting state". Module 3's spec also requires that "runs must reset cleanly so
every participant starts this module from the same looping state".

What a participant changes during the lab is small and known:

- **Module 2** repoints `config.toml` from endpoint A to endpoint B.
- **Modules 3–5** copy a supplied solution over `agent.py` and `tools.py`
  (`agent/solutions/module-03` to `module-05`).
- **Module 6** sets the gateway in `config.toml`. No solution is supplied yet.

Everything else is shared and read-only from the participant's side: the endpoints,
the pgvector corpus (ingested at provisioning) and MLflow (traces only accumulate).

## Options considered

1. **A script in the agent directory** that rebuilds a module's start from the git
   checkout plus the supplied solutions.
2. **One git branch or tag per module start**, checked out by participants.
3. **Re-provisioning the workbench**: delete the Notebook and its volume and let
   GitOps recreate them.

## Decision

Option 1: `python reset.py N` in `agent/`.

1. It copies changed tracked files to `agent/.reset-backup/<time>/`, which git ignores.
2. It restores them from the checked-out commit.
3. For modules 3 and later, it applies module 2's repoint to `config.toml`.
4. It applies `solutions/module-NN` for every earlier module that has one.

Module 7 starts from module 6's start until a module 6 solution exists.

## Reasons

1. **It's exactly the participant's own path.** The script performs the same edits the
   modules tell participants to make, in the same order. That's also what the test
   suite's `repoint_to_validated()` and `apply_solution()` do, so a reset state and a
   followed-the-steps state can't drift apart.
2. **It's small and needs nothing new.** Under 100 lines, standard library plus the git
   that the workbench image already ships (2.47.3) and that the pre-clone already uses.
   It has no cluster permissions, needs no facilitator, and works offline.
3. **Nothing is lost.** Edits are backed up before restore, which matters for a
   self-paced lab where a participant may reset by mistake.
4. **Option 2** would duplicate the solutions into branches that must be kept in step
   with `dev`, and asks participants to run git commands.
5. **Option 3** takes minutes, needs facilitator access, and loses work. It stays the
   last resort for a workbench that won't start.

## Verified

`tests/agent/test_reset.py`, in a throwaway git checkout of `agent/`:

- module 5's start gives module 4's `agent.py` and `tools.py`, the validated endpoint,
  and the participant's edit backed up;
- module 4's start gives module 3's `agent.py` with the starter `tools.py`;
- module 1's start is the starter code byte for byte;
- repeating a reset is a no-op.

It was also run in a real workbench on the dev cluster; see the PR.

## Not covered

- **Module 6's start and end.** These need the MCP server and gateway setup (D10, David's).
  When a module 6 solution exists, add it under `solutions/module-06` and `reset.py`
  picks it up for module 7.
- **Each module's participant-facing recovery line** that points to `reset.py` is module
  prose, for the author.
