# Approved by David on 2026-11-25, in the LB8000 working session (learner pass, D6 and Q3-Q4).
# Only the exact gateway address the workbench provides (LAB_GATEWAY_URL) counts as the lab's
# own setting; any other gateway_url is a participant edit. Locked: to change a scenario, ask
# David; don't edit this file.

Feature: The lab's own gateway setup isn't a participant edit

  Scenario: Module 7's gateway setup doesn't count as a participant edit
    Given a participant has reset to module 7 and run its setup cell, which connects the agent to the lab's gateway
    When they run the regression set
    Then the evaluation run and its traces are labelled with module 7's starting version, not as modified

  Scenario: A participant's own change to the agent is still labelled modified
    Given a participant has reset to module 7 and run its setup cell
    When they change one of the agent's files and run the regression set
    Then the evaluation run is labelled with module 7's starting version plus "modified"

  Scenario: Following module 6's instruction to set the gateway doesn't count as a participant edit
    Given a participant has reset to module 6 and set gateway_url to the lab's gateway address as instructed
    When they run the agent
    Then its trace is labelled with module 6's starting version, not as modified
