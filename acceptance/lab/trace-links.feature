# Approved by David on 2026-11-01, in the LB8000 working chat. Locked:
# to change a scenario, ask David; don't edit this file.

Feature: Every run points the participant at its own trace

  Scenario: A run links to its own trace
    Given tracing is on in the participant's workbench
    When a participant runs the agent on the module 1 question
    Then the agent prints a link that opens that run's trace in MLflow

  Scenario: Without tracing, nothing about traces is printed
    Given tracing is off
    When a participant runs the agent on the module 1 question
    Then the agent prints its answer and where its payloads are, as before, with nothing about traces

  Scenario: A run whose trace couldn't be recorded says so
    Given tracing is on but MLflow can't be reached
    When a participant runs the agent on the module 1 question
    Then it says the trace wasn't recorded and points to python payloads.py instead

  Scenario: The payloads view links to the same run's trace
    Given a participant has run the module 1 question with tracing on
    When they view the run's payloads
    Then they see a link to the same run's trace
