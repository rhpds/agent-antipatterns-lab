# Live workshop acceptance

The fast `tests/agent` suite uses a mock model and a real disposable pgvector database. It needs no LLM or GPU. Live acceptance is separate: it uses two real workbenches, the deployed model endpoints, pgvector and MLflow. Verdicts come from recorded behavior, without an LLM judge.

Use a dedicated freshly provisioned workshop with two participants. Notebook runs use isolated local clones on the workbench PVC; participant edits are preserved. Executed notebooks stay on the PVC and their paths are returned as evidence.

## Run

Use the project-local environment with `tests/agent/requirements.txt` and `publishing-house/showroom/requirements.txt` installed, plus the existing `oc`, `gh` and Node documentation dependencies. Workbench images must include nbclient, nbformat and a Python Jupyter kernel.

Set these non-secret selectors. The kubeconfig itself stays outside Git and is never copied into a report:

```bash
export LB8000_KUBECONFIG=/path/to/private/kubeconfig
export LB8000_PARTICIPANTS=user-first,user-second
export LB8000_RELEASE=$(git rev-parse origin/test)
export LB8000_RELEASE_PR=123
npm run build --prefix publishing-house/showroom -- --attribute "lab-source-ref=$LB8000_RELEASE"
.venv/bin/python qa-automation/run.py --output .cache/live-e2e
```

For readiness without executing notebooks:

```bash
.venv/bin/python qa-automation/run.py --output .cache/live-healthcheck --readiness-only
```

The Ansible `healthcheck.yml` and `e2e.yml` playbooks invoke the same entry point and inherit these selectors. Set `lab_evidence_dir` to change their output directory. Readiness success does not certify module completion.

## Evidence and review

Each invocation writes `report.json` and `review.md`, plus uniquely named pytest JUnit XML when tests run. Missing configuration and unavailable services fail. Module rows require both participants' module checks, readiness and matching rendered documentation. Required incomplete or failed checks cannot produce a ready verdict.

The review index links all six notebooks at the selected commit and their local Showroom guide pages. Build the preview before opening those links. A local build or downloadable CI preview is not proof that a Showroom instance is published.

The full run also verifies the test-to-main release PR and effective branch protection. Until that PR and its required approval/check policy exist, the overall result remains unsuccessful even if individual modules pass. Keep the commit fixed through validation and review; changes require rerunning the checks and renewing approval.

The catalog must point at the verified release before a fresh provision is meaningful. Patching existing Argo Applications proves repair of that workshop, not repeatability from the catalog.

## Repository administrator setup

Use GitHub's native code-owner review requirement. The repository's `.github/CODEOWNERS` names the release reviewer, who must have write access. GitHub reads ownership from the PR's **base branch**, so that file must reach `main` before the first release can rely on the requirement. Establish it through a separately reviewed setup PR, then verify the effective rule before opening or enabling auto-merge on a release. See [GitHub's code-owner documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners).

`main-protection.json` is a proposed administrator input, not an installed rule. It requires the agent and Showroom CI checks plus `live-e2e`, requires owner approval and dismisses stale approvals. Compare it with any existing policy before applying; never overwrite stronger existing restrictions.

After reviewing the policy, a repository administrator can apply it:

```bash
gh api --method PUT repos/rhpds/agent-antipatterns-lab/branches/main/protection --input qa-automation/main-protection.json
```

The administrator must also enable repository auto-merge if automatic merging after approval is desired. The live promotion check reads the actual GitHub policy and the owner file on `main`; committed JSON alone cannot satisfy it. Publish a successful `live-e2e` status only after a complete live run on the exact release commit, retaining its evidence with the release PR. A readiness-only run cannot satisfy that check.
