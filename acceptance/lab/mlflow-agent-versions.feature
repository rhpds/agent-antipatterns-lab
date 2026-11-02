# Approved by David on 2026-11-02, in the LB8000 working chat (MLflow research R4, #77). His
# answers to the open questions: after the participant edits the agent, a run is labelled
# with the starting version plus "modified" (Q6); the lab points participants at version
# labels in module 7 only (Q7). Locked: to change a scenario, ask David; don't edit this file.

Feature: Every trace and evaluation names the agent version behind it

  Scenario: Every trace says which build of the agent produced it
    Given a participant has reset to the start of a module
    When they run the agent
    Then its trace is labelled with that module's starting version

  Scenario: The evaluation run names the agent version it tested
    Given tracing is on in the participant's workbench
    When a participant runs the regression set
    Then the evaluation run is linked to the agent version that produced it
