# `<your_collection_name>`

Starter Ansible collection for this project's custom automation — the base to build your
own roles on top of. It ships with a single no-op `example` role (`roles/example/`) so
the collection is valid and installable from the start.

This collection is never published to Ansible Galaxy. It's referenced straight from this
project's git repository. See the [Custom Ansible Automation](https://rhpds.github.io/rhdp-publishing-house/user/custom-automation/)
guide for the full walkthrough, including how to wire it into an AgnosticV
`requirements_content`.

## Before you use this

1. Run `scaffold.py --automation ansible` (or `--automation both` alongside GitOps)
   at the template repo root — this copies this directory into your project as
   `automation/ansible/` for you. Do this on your **first** `scaffold.py` run,
   since scaffolding removes the whole `.scaffolds/` directory afterward. If
   you've already scaffolded without the flag, pull this directory from the
   `rhdp-publishing-house-template` repository directly instead.
2. Edit `galaxy.yml` — replace `<your_namespace>`, `<your_collection_name>`, and
   the author line. These become the prefix for every role's fully qualified name
   (`<your_namespace>.<your_collection_name>.<role_name>`).
3. Rename or remove `roles/example/` and add your own roles under `roles/`.
4. Commit, then tag a release once it's ready to be consumed
   (`git tag v1.0.0 && git push --tags`).

## Structure

```
automation/ansible/
├── galaxy.yml
├── README.md
├── meta/
│   └── runtime.yml
└── roles/
    └── example/
        ├── README.md
        ├── defaults/
        │   └── main.yml
        ├── meta/
        │   └── main.yml
        └── tasks/
            └── main.yml
```

## Adding a role

```bash
ansible-galaxy role init --init-path roles/ my_role_name
```

Then reference it by its fully qualified name once the collection is installed:

```yaml
- name: Run my_role_name
  ansible.builtin.include_role:
    name: <your_namespace>.<your_collection_name>.my_role_name
```

## Testing locally

Install the collection straight from your working tree to confirm it's structured
correctly before pushing:

```bash
ansible-galaxy collection install . --force
```
