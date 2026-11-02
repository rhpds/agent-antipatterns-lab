# Approved by David on 2026-11-01 (approval record: issue #65). Locked:
# to change a scenario, ask David; don't edit this file.
# These record the lab's behavior as it was on that date. Each is tied to a
# mock-model test in tests/agent/ that names the scenario in its docstring.
# A live run on the cluster is separate work (qa-automation/e2e.yml).

Feature: Each module opens with its failure and closes with its fix

  Scenario: Module 1's agent answers confidently without calling a tool
    Given the agent as the lab ships it
    When a participant asks the module 1 question about the K-400 coolant pump
    Then the agent gives a confident answer without the pump's real part number
    And the saved response shows the tool call left in the text, with no tool run and no error

  Scenario: The payload viewer shows the module 1 evidence
    Given a participant has run the module 1 question
    When they run the payload viewer
    Then it shows the tools declared, an empty tool-call list and a normal stop
    And it names the files to open for the full payloads

  Scenario: A stronger prompt doesn't make the tools fire
    Given the agent still points at the mismatched endpoint
    When a participant strengthens the prompt and asks the module 1 question again
    Then the wording of the answer changes but still no tool is called

  Scenario: The endpoint whose parser matches the model makes the tool fire
    When a participant points the agent at the validated endpoint and asks the module 1 question
    Then the tool is called and returns the pump's real part number

  Scenario: Comparing endpoints shows both responses side by side
    When a participant runs the endpoint comparison
    Then they see the same request's response from both endpoints next to each other
    And an endpoint that can't be reached is reported without stopping the comparison

  Scenario: Module 3's starting loop calls the same tool until the turn cap
    Given the agent at the start of module 3
    When a participant asks whether a K-400 pump can reach the Denver depot this week
    Then the agent repeats the same tool call until it hits the turn cap, with no error

  Scenario: With the supplied loop fix, the agent stops when the model is done
    Given the module 3 fix is applied
    When a participant asks the module 3 question
    Then the agent looks up the part, checks stock, and stops with an answer that uses both results

  Scenario: Module 4's unknown depot reads as out of stock
    Given the agent at the start of module 4
    When a participant asks about the K-600 sensor at the Portland depot
    Then the agent confidently says it is not available, though Portland isn't a depot

  Scenario: With the error contract, a bad depot is no longer mistaken for out of stock
    Given the module 4 fix is applied
    When a participant asks the module 4 question
    Then the agent says it could not complete the check, and the tool's reply names Portland as the problem
    And a real out-of-stock result and a bad request are reported differently

  Scenario: Without knowledge search, the agent invents a cause for fault F-21
    Given the agent at the start of module 5
    When a participant asks what to do about fault F-21 on a K-400
    Then the agent finds nothing in the parts catalog and still gives a confident, invented answer

  Scenario: With knowledge search, the F-21 answer follows the service bulletin
    Given the module 5 fix is applied
    When a participant asks the F-21 question
    Then the answer cites bulletin SB-2024-102 and its "coolant loop pressure low" cause

  Scenario: The agent says so when the bulletins have nothing
    Given the module 5 fix is applied
    When a participant asks for the service interval on a K-900
    Then the agent says it won't guess, rather than inventing an interval

  Scenario: A tool added at the gateway is used without redeploying the agent
    Given the agent reaches its tools through the gateway
    When the delivery-estimate tool is registered at the gateway
    And a participant asks when the Denver pump would reach Boulder
    Then the agent calls the new tool and answers "1 day", with no agent files changed

  Scenario: The regression run checks every earlier case against the assembled agent
    Given the agent with every module's fix and the gateway tool
    When a participant runs the regression set
    Then all 6 cases pass
    And on an earlier module's state it still reports each case without stopping

  Scenario: Resetting to a module's start keeps the participant's edits
    Given a participant has edited the agent's files
    When they reset to the start of module 4
    Then the agent is back at module 4's starting state and their edits are saved as a backup
