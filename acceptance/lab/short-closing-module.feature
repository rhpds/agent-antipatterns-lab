# Approved by David on 2026-11-25, in the LB8000 working session (scope cut S1 + S2, Q5-Q7).
# Module 6 (MCP Gateway) is cut; module 7 becomes a short closing module, module 6,
# titled "Running it for real". A cut-off run in the closing regression is covered by
# regression-cut-off-runs.feature (Q5). Locked: to change a scenario, ask David; don't
# edit this file.

Feature: The lab ends with a short check of everything that was fixed

  Scenario: The closing module checks every fix in one run
    Given a participant has reset to the closing module
    When they run its regression cell
    Then they see one row per earlier fix, each PASS with its reason, and the symptom-to-layer checklist

  Scenario: The closing module needs no setup of its own
    Given a participant has reset to the closing module
    When they run its cells in order
    Then nothing asks them to connect, register or configure anything first

  Scenario: Comparing runs in MLflow is optional
    Given a participant has finished the closing module's regression run
    When they skip the MLflow evaluation step
    Then the module is still complete

  Scenario: The checklist names where tool access is governed
    Given the closing module's regression report
    When a participant reads the symptom-to-layer checklist
    Then "Who can see what?" points to governed tool access on the platform as the next step, with no hands-on step
