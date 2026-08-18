# Role: example

A no-op placeholder role. It prints a debug message and does nothing else — start here.

## What to do with this role

- Rename `roles/example/` to something that describes what it does.
- Replace the task in `tasks/main.yml` with real automation.
- Add variables to `defaults/main.yml`, prefixed with the role name.
- Delete this role entirely once you've added your own.

## Requirements

- Ansible >= 2.14

## Role Variables

Defined in `defaults/main.yml`:

- `example_message` — the message printed by the placeholder task.

## Example Usage

```yaml
- hosts: all
  roles:
    - <your_namespace>.<your_collection_name>.example
```
