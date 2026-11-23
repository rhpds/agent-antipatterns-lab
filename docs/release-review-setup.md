# Main release review setup

GitHub reads code ownership from a pull request's base branch. Merge this separately reviewed ownership setup before relying on owner approval for the first `test` to `main` lab release. The designated code owner must retain repository write access.

A repository administrator must enable these settings on `main`:

- Require a pull request and at least one approval, including approval from the code owner.
- Dismiss stale approvals after changes and enforce the policy for administrators.
- Require the `agent-tests`, `showroom-docs` and `live-e2e` checks on the reviewed release commit.
- Prevent force pushes and branch deletion.

If automatic merging after approval is desired, also enable repository auto-merge. A release author can then enable auto-merge on the release PR after attaching its validation evidence.

The lab repair and live acceptance implementation are tracked in [PR #94](https://github.com/rhpds/agent-antipatterns-lab/pull/94). That change includes a proposed branch-protection API input and a live check of the effective policy. Establishing ownership alone does not enforce approval, install those settings or demonstrate that the lab works.

The release must include verification from a freshly provisioned workshop using the selected catalog release, the two-participant live results and matching Showroom pages. A readiness-only result or a patched existing workshop does not satisfy fresh-provision verification.

See [GitHub's code-owner documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners).
