# Approved by David on 2026-11-01 (approval record: issue #65). Locked:
# to change a scenario, ask David; don't edit this file.

Feature: The lab's checks can be trusted

  Scenario: A check that can't run is reported as failing, not passing
    Given the machine running the lab's checks can't start the bulletin database
    When the checks run
    Then the module 5, 6 and 7 checks are reported as failing
