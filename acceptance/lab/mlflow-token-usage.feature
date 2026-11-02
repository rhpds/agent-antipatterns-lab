# Approved by David on 2026-11-02, in the LB8000 working chat (MLflow research R3). His
# answers to the open questions: when the model reports no token counts, the trace shows
# none and the run is otherwise unchanged (Q1); the counts appear in MLflow only, not in the
# terminal (Q2). Locked: to change a scenario, ask David; don't edit this file.

Feature: A trace shows what a run cost

  Scenario: The looping run's trace shows what it cost
    Given tracing is on in the participant's workbench
    And the agent at the start of module 3
    When a participant asks the module 3 question
    Then the run's trace shows its total token count in the trace list

  Scenario: The fixed loop costs less than the looping one
    Given tracing is on and the module 3 fix is applied
    When a participant asks the module 3 question
    Then the trace list shows a lower token total for this run than for the looping run
