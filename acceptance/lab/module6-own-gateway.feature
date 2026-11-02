# Approved by David on 2026-11-02, in the LB8000 working chat: the lab's gateway gets its own
# Gateway, never OpenShift AI's, and is reached from inside the cluster only (his answer to Q1).
# Locked: to change a scenario, ask David; don't edit this file.

Feature: The lab's gateway stands apart from OpenShift AI's

  Scenario: OpenShift AI's own pages keep working with the lab's gateway installed
    Given a lab environment with the lab's gateway installed
    When a participant opens MLflow, the OpenShift AI dashboard and their workbench
    Then each one opens as it did before the gateway was installed

  Scenario: The lab's gateway is reached from the workbench
    Given a participant's workbench on a lab environment
    When they run the module 6 notebook
    Then the agent reaches the gateway from inside the cluster, with no public address of its own
