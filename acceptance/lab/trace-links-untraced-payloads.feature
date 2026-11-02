# Approved by David on 2026-11-01, in the LB8000 working chat. Locked:
# to change a scenario, ask David; don't edit this file.

Feature: A run without a trace says nothing about traces

  Scenario: The payloads of an untraced run say nothing about traces
    Given a participant has run the module 1 question with tracing off
    When they view the run's payloads
    Then they see the payloads as before, with nothing about traces
