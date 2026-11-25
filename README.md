# LB8000: Four ways your agent can break

Build a field service agent for Kestrel Industrial, a fictional chiller manufacturer. Diagnose failures from model request and response payloads, tool results and execution traces, then apply and verify each fix.

The lab runs in a JupyterLab workbench on Red Hat OpenShift AI. It uses locally served Qwen model endpoints, a pgvector knowledge store, MLflow and MCP Gateway. The notebooks are the lesson source. Each Showroom page is a short guide generated from its notebook: what the module covers, its steps, how you know it worked, its diagrams and, where the module has them, its questions and answers. Showroom pages carry no code.

## Start the lab

Open the Showroom URL supplied by your provisioned tenant, then launch its OpenShift AI workbench. Begin with module 1 in the workbench's `agent-antipatterns-lab/notebooks` directory. Environment URLs and credentials come from provisioning.

| Module | Notebook | Focus |
|---|---|---|
| 1 | [What you are building](notebooks/module-01-what-you-are-building.ipynb) | Inspect the prototype and its evidence |
| 2 | [The model interface](notebooks/module-02-model-interface.ipynb) | Make tool calls parse and execute |
| 3 | [The agent loop](notebooks/module-03-agent-loop.ipynb) | Stop correctly and use dependent tool results |
| 4 | [Tool returns](notebooks/module-04-tool-returns.ipynb) | Distinguish failures from empty results |
| 5 | [Knowledge search](notebooks/module-05-knowledge-search.ipynb) | Ground answers in retrieved service bulletins |
| 6 | [Platform tool access](notebooks/module-06-platform-tool-access.ipynb) | Reach and register tools through MCP Gateway |
| 7 | [Verification](notebooks/module-07-running-it-for-real.ipynb) | Run the regression cases and inspect recorded evaluations |

To resume at a module, run this from the repository root in the workbench:

```bash
python agent/reset.py 2
```

Change `2` to the module you want to start. Reset saves participant edits under `agent/.reset-backup/`, leaves added files in place and stops if a tracked path is obstructed. The [agent README](agent/README.md) covers direct execution, payload inspection and configuration.

## Review without provisioning

Start with the [module review index](docs/review/README.md). It links the modules 2 through 7 checklists, acceptance coverage and recorded execution evidence. Human content review remains open.

The `showroom-docs` check on a pull request provides a downloadable `showroom-preview` artifact. Open `modules/index.html` after extracting it. The preview contains each module's guide (steps, success signal, diagrams, and questions where the module has them); the lesson text and code are in the notebooks, and saved model outputs belong to the separate execution evidence. A passing preview build does not publish a Showroom instance.

The review candidate is tracked in [PR #98](https://github.com/rhpds/agent-antipatterns-lab/pull/98). An existing workshop can serve an older branch or checkout, so compare its source revision with the review candidate before reporting results.

## Change a lesson

Edit its notebook, then regenerate and check the committed Showroom pages:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r publishing-house/showroom/requirements.txt
.venv/bin/python publishing-house/showroom/generate.py
.venv/bin/python publishing-house/showroom/generate.py --check
```

Commit the notebook and its generated page together. The overview page is authored separately. See the [Showroom build instructions](publishing-house/showroom/README.md) for local previews and rendered-page verification.

## Test the lab

Approved [acceptance scenarios](acceptance/lab/) describe participant-visible behavior. Changes that alter those promises require approval before implementation.

The fast suite uses a mock model and a real disposable pgvector database. It requires Podman and Helm, with no LLM or GPU:

```bash
.venv/bin/python -m pip install -r tests/agent/requirements.txt
.venv/bin/python -m pytest tests/agent -q -rs
```

Live acceptance uses two real workbenches, the deployed models and the lab services. Its verdicts inspect recorded behavior without an LLM judge. Follow the [live workshop acceptance instructions](qa-automation/README.md) for configuration, execution and evidence requirements.

## Deployment and review

`dev` is the development branch, `test` holds release candidates and `main` holds the approved release. Operational fixes can enter `test` after independent code review and required checks. The lab author reviews module content before the designated release reviewer approves promotion from `test` to `main`.

The infrastructure chart, tenant chart, runtime clones and Showroom must all select the intended release. See the [GitOps deployment contract](automation/gitops/README.md) and [main release review setup](docs/release-review-setup.md). The proposed protection settings must be applied and verified by a repository administrator; committing them does not enforce approval.

[Release PR #96](https://github.com/rhpds/agent-antipatterns-lab/pull/96) tracks the first lab promotion and its remaining fresh-provisioning and repository-policy requirements. The [implementation provenance](docs/implementation-provenance.md) records recent Codex contributions and the limits of automated review.
