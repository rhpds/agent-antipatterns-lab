# Approved by David on 2026-11-02, in the LB8000 working chat (MLflow research R5). His
# answer to the open question (Q3): from module 6 on, the search runs behind the gateway, so
# the agent's trace shows the tool's reply rather than a document list. Locked: to change a
# scenario, ask David; don't edit this file.

Feature: A trace shows what knowledge search retrieved

  Scenario: The F-21 trace shows the passages the agent read
    Given tracing is on and the module 5 fix is applied
    When a participant asks the F-21 question
    Then the run's trace lists the retrieved passages as documents, each labelled with its bulletin, SB-2024-102 among them

  Scenario: An out-of-corpus search shows it retrieved nothing
    Given tracing is on and the module 5 fix is applied
    When a participant asks for the service interval on a K-900
    Then the run's trace shows the search returned no documents
