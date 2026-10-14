# LB8000 facilitator guide

`design.md` (Delivery model) keeps this guide short. Participant content stands
alone, so no step depends on a facilitator. The guide carries two things:

- the discussion beats that benefit from a person present (module 1 framing,
  module 7 customer conversation);
- the operational facts a facilitator needs to keep the room running.

## Discussion beats

<!-- TODO(author): module 1 framing (the rule "the answer is a claim, the evidence is
somewhere else"), and the module 7 symptom-to-layer discussion prompts. -->

## Operations

### Changing endpoint A restarts it fully

Endpoint A (`qwen3-8b-a`, the deliberately mismatched one) runs **one replica on one
GPU**. Any change to its ServingRuntime replaces that pod: an image bump, the
tool-call parser, `maxModelLen`. The predictor rolls with `maxSurge: 0` (#18), so
the old pod stops before the new one starts, and **endpoint A serves nothing until
the new pod is Ready**.

- **How long** (measured on the dev cluster, OpenShift AI 3.5.1, Qwen3-8B from the
  Red Hat ModelCar image):
  - about **2 minutes** when the model image is already on the node;
  - about **5.5 minutes** on a node that has never pulled it (~9.5 GB).
- **When it hurts:** every participant uses endpoint A in modules 1 and 2. **Don't
  change endpoint A while anyone is in module 1 or 2.** Make changes before the
  session, or once the room is past module 2.
- Endpoint B (`qwen3-8b-b`, three replicas on the event layout) rolls one replica at a
  time, so two of three keep serving during a change.
- Wait for `oc rollout status deploy/qwen3-8b-a-predictor -n llm-serving`, not the
  InferenceService `Ready` condition. That condition goes True before the pod can
  serve.

### Deleting `agent/requirements.txt` re-clones the lab repo

When a workbench starts, its setup step checks that the lab checkout
(`~/agent-antipatterns-lab`) contains `agent/requirements.txt`. If it doesn't, the
setup step:

1. moves the whole checkout aside to `~/agent-antipatterns-lab.unusable.<timestamp>`;
2. clones the lab repo fresh in its place.

So a participant who deletes or renames that file sees their work "reset" on the next
workbench restart. **Nothing is lost:** their edits are in the `.unusable.<timestamp>`
directory, and they can copy files back from it. The `~/.venv` with the agent's
packages is kept, so the restart doesn't reinstall anything.

### Putting a participant back on track: `reset.py`

A participant who broke their code, or fell behind the room, can put the agent in the
state any module starts from:

```bash
cd ~/agent-antipatterns-lab/agent
python reset.py 4      # the starting state of module 4
```

- It copies their current versions of any changed files to `agent/.reset-backup/<time>/`
  first.
- It restores the starter code, repoints `config.toml` at the validated endpoint for
  module 3 and later (module 2's change), and applies each earlier module's supplied
  solution.
- Module 7 starts from module 6's starting state, because module 6's gateway change has
  no supplied solution.
- The corpus and MLflow need no reset: the corpus is read-only, and traces only add up.
  Decision 0004 records the design.
