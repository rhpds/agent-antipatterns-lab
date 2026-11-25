# Approved by David in the LB8000 working chat on 2026-11-23.
# Locked: changes require David's approval.
# Scope: two-participant functionality; 30-user load testing is separate.
# Verdicts use observable behavior and assertions, without an LLM judge.

Feature: The complete lab is verified before review and release

  Scenario: Readiness means participants can begin the lab
    Given a freshly provisioned workshop with two participants
    When David runs the environment readiness check
    Then both participants can access their own workbench
    And the required model endpoints, database and MLflow respond successfully

  Scenario: Every module works through the participant instructions
    Given a ready workshop running the selected lab release
    When David runs the end-to-end checks for modules 1 through 6
    Then each module demonstrates its approved starting failure and completed behavior
    And the assembled agent passes all five regression cases
    And the checks use the deployed model and real lab services

  Scenario: Incomplete testing cannot be mistaken for success
    Given a required service is unavailable or a module check cannot finish
    When David runs the end-to-end checks
    Then the overall result is unsuccessful
    And the report identifies the affected checks and their reasons

  Scenario: Each module is ready for David to review
    Given the notebooks and Showroom pages for the selected release
    When David opens the module review report
    Then every module has links to its notebook and matching rendered Showroom page
    And each module shows its test evidence and unresolved issues
    And no module is marked ready while a required check is failing or incomplete

  Scenario: The reviewed release is the release promoted
    Given a tested release on test
    When David prepares its promotion to main
    Then the release PR identifies the tested commit and its verification results
    And merging requires passing checks and Ishu's approval
    And subsequent changes require renewed approval

  Scenario: Participants complete the lab independently
    Given two participants
    When both complete the lab
    Then their workbenches remain isolated from each other
