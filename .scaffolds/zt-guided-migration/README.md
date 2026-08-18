# zt-guided-migration

This directory is **not** wired into `scaffold.py` — it does not appear in
`PATTERNS`, the interactive menu, or `--pattern` choices. It exists purely as
a source folder for a separate downstream process that migrates an existing
Showroom/nookbag content repo into this Publishing House template.

## Why this isn't a normal scaffold pattern

The `zt-guided` pattern (see `.scaffolds/zt-guided/`) generates a fresh
project with placeholder Ansible playbooks for `runtime-automation/`,
`setup-automation/`, and `config/`. A repo being migrated already has all of
that — including working `runtime-automation/<module>/{solve,validation}-<host>.sh`
shell scripts and a populated `ui-config.yml` — so those stubs would only get
overwritten or ignored.

What a migrated repo is missing is a `qa-automation/` that knows how to drive
those legacy shell scripts (rather than the ansible-playbook-per-module style
the fresh `zt-guided` scaffold assumes). That's all this directory provides.

## Contents

- `qa-automation/e2e.yml` — builds a bastion inventory from `BASTION_*` env
  vars, reads module order from `ui-config.yml`, then solves + validates
  every module by running `tasks/run_script.yml`.
- `qa-automation/healthcheck.yml` — builds the same inventory and pings the
  bastion over SSH to confirm it's reachable.
- `qa-automation/tasks/run_script.yml` — shared logic: copies a
  `{stage}-{hostname}.sh` script from `runtime-automation/{module}/` onto the
  remote host, sources a `fail_validation()` helper, runs the script, and
  fails the play on a non-zero exit or a captured `fail_validation` block.

## Usage

The downstream migration process copies `qa-automation/` from this directory
into the target repo's root, replacing the generic placeholder
`qa-automation/` that ships with every other pattern.
