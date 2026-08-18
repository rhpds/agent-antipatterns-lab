# [Project Name]

<!-- Replace with your project name and brief description. -->

## Getting Started

1. Clone this template and scaffold your lab pattern:

```bash
git clone https://github.com/rhpds/rhdp-publishing-house-template my-lab
cd my-lab
python scaffold.py
```

2. Install the RHDP Publishing House skills plugin in Claude Code or Cursor
3. Run `/rhdp-publishing-house` in this directory to start intake
4. Follow the orchestrator's guidance

## Lab Patterns

The scaffold script (`scaffold.py`) configures this template for one of three lab patterns:

| Pattern | Infrastructure | Showroom | Created Directories | site.yml |
|---------|---------------|----------|---------------------|----------|
| **AgD v2 Open** | AgnosticD v2 | Classic (no solve/validate) | `content/` only | `rhdp_showroom_theme` (default) |
| **AgD v2 Guided** | AgnosticD v2 | Guided (solve/validate buttons) | `runtime-automation/`, `content/` | `nookbag-bundle` (overwritten) |
| **ZT Guided** | Project Zero | Guided (solve/validate buttons) | `config/`, `setup-automation/`, `runtime-automation/`, `content/` | `nookbag-bundle` (overwritten) |

After scaffolding, edit `ui-config.yml` to configure tabs for your infrastructure target (terminals, OCP console, external URLs).
See the [showroom-template](https://github.com/rhpds/showroom-template) branches for example tab configurations.

Run `python scaffold.py --help` for non-interactive usage. Pass `--automation {ansible,gitops,both}`
in the same invocation to also scaffold an `automation/` directory from `.scaffolds/automation/` —
this must be done up front, since `.scaffolds/` is removed once scaffolding completes. Add
`--topology shared-cluster` to additionally include `automation/gitops/bootstrap-tenant/` (per-user
namespace + RBAC); omit it for single-tenant topologies, where only `automation/gitops/bootstrap-infra/`
is created.

## Structure

Before scaffolding, the repo only has:

- `scaffold.py` — Lab pattern scaffolding script (run once after cloning)
- `.scaffolds/` — Common and pattern-specific files (removed after scaffolding)
- `publishing-house/` — Project state (manifest), specs, reviews, decisions
- `hooks/` — Claude Code hooks

### After Scaffolding

Common to every pattern:

- `content/` — Showroom AsciiDoc content (Antora modules), pre-populated with a minimal `antora.yml`, `nav.adoc`, and `index.adoc`
- `qa-automation/` — Health check and e2e test playbooks
- `site.yml` — Antora playbook. Defaults to the `rhdp_showroom_theme` bundle; guided patterns overwrite it with a `nookbag-bundle` version

Pattern-specific:

- `ui-config.yml` — Showroom UI layout config (set by scaffold, customize tabs afterward)
- `podman-compose.yaml` — Local dev preview (`podman compose up`, then http://localhost:8080). AgD v2 Open only — guided patterns rely on Nookbag to drive navigation and aren't previewable via plain Antora + httpd
- `runtime-automation/` — Per-module solve/validate playbooks (Guided patterns)
- `setup-automation/` — Environment setup playbook (ZT Guided only)
- `config/` — Project Zero instance, network, and firewall definitions (ZT Guided only)

Only if `--automation` was passed to `scaffold.py`:

- `automation/ansible/` — Starter Ansible collection (`ansible`/`both`)
- `automation/gitops/bootstrap-infra/` — Helm chart with a test namespace (`gitops`/`both`)
- `automation/gitops/bootstrap-tenant/` — Per-user namespace + RBAC (`gitops`/`both`, only with `--topology shared-cluster`)
