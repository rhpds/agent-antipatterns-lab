# Approved by David in the LB8000 working chat on 2026-11-23.
# Locked: changes require David's approval.

Feature: A workshop deploys the selected lab release for each participant

  Scenario: A new workshop uses deployable lab sources
    Given a lab release has been selected
    When David provisions a workshop
    Then its infrastructure, workbenches and tool server use that release
    And provisioning fails clearly if required deployment content is unavailable

  Scenario: Each participant gets their own workbench
    Given two participants on the same lab environment
    When David provisions their workbenches
    Then each workbench belongs to its assigned participant
