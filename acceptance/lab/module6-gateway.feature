# Approved by David on 2026-11-02, in the LB8000 working chat: the scenarios as drafted,
# with his answers to the open questions (a shared read-only copy of the bulletins behind
# the gateway; registration per participant; registration from a notebook cell in the
# participant's own project; MCP Gateway enabled on the dev cluster). Locked: to change a
# scenario, ask David; don't edit this file.

Feature: Module 6 runs through the lab's real gateway

  Scenario: The agent reaches its tools through the lab's gateway
    Given a participant's workbench on a lab environment
    When they point the agent at the lab's gateway and ask the module 3 question
    Then the agent answers as it did with its own tools, using tools it found at the gateway

  Scenario: Search through the gateway still cites the service bulletin
    Given a participant's agent points at the lab's gateway
    When they ask the F-21 question
    Then the F-21 answer through the gateway cites SB-2024-102, as it did in module 5

  Scenario: Registering the delivery tool changes only that participant's catalog
    Given two participants on the same lab environment
    When one of them registers the delivery tool
    Then the other's agent still doesn't see it until they register it themselves

  Scenario: Module 7 passes every case on a lab environment
    Given a participant who has finished module 6
    When they run the regression set
    Then all 6 cases pass
