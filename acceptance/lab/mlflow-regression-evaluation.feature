# Approved by David on 2026-11-02, in the LB8000 working chat (MLflow research R2; decision
# 0005). His answers to the open questions: the evaluation run keeps the passed, failed and
# skipped counts on the Runs tab (Q4); when MLflow can't be reached, the regression run still
# reports every case and says the evaluation wasn't recorded (Q5). Locked: to change a
# scenario, ask David; don't edit this file.

Feature: Module 7's regression run is recorded as an evaluation

  Scenario: The regression run is recorded as an evaluation
    Given tracing is on in the participant's workbench
    When a participant runs the regression set with a name
    Then MLflow shows an evaluation run with that name, one row per case, each with its trace and its PASS, FAIL or SKIP with the reason

  Scenario: MLflow's verdicts match the terminal's
    Given tracing is on in the participant's workbench
    When a participant runs the regression set
    Then each case's result in MLflow is the result printed in the terminal and the report

  Scenario: A later run can be compared with the baseline
    Given a participant recorded a baseline on an earlier module's state
    When they finish module 6, run the regression set again and compare it with the baseline in MLflow
    Then each case shows both results side by side, and the cases that changed stand out

  Scenario: Without tracing, the regression run is unchanged
    Given tracing is off
    When a participant runs the regression set
    Then it prints each case and writes its report as before, with nothing about MLflow
