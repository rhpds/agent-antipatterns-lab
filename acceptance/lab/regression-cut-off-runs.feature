# Approved by David on 2026-11-25, in the LB8000 working session (learner pass, D5 and Q1-Q2).
# A run cut off because the model ran out of room never passes, whatever its check found.
# The model's token allowance stays as it is. Locked: to change a scenario, ask David; don't
# edit this file.

Feature: A regression case only passes on a finished run

  Scenario: A regression case whose run was cut off doesn't pass
    Given the assembled agent
    When a participant runs the regression set and one case's run stops because the model ran out of room to finish its answer
    Then that case is reported FAIL, saying the run was cut off before it finished its answer
    And the report suggests running the set again

  Scenario: Any regression case cut off before its answer fails
    Given the assembled agent
    When any case's run ends because the model ran out of room
    Then that case is reported FAIL with the reason, whatever else its check found
