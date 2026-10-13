"""The test questions the lab runs on, by name. Use:  python agent.py --q m1"""

QUESTIONS = {
    # Modules 1 and 2: unanswerable without a tool
    "m1": "A customer's K-400 is showing a coolant pressure fault. What's the replacement part number for the coolant pump?",
    # Module 3: needs find_part, then check_stock with find_part's output
    "m3": "Can we get a replacement coolant pump for a K-400 to the Denver depot this week?",
    # Module 4: Portland is not a Kestrel depot
    "m4": "Is the K-600 high-pressure sensor available at the Portland depot?",
    # Module 5: answer exists only in a service bulletin
    "m5": "What's the recommended service interval for the K-400 coolant pump seal?",
    # Module 5: no K-900 exists, so there is nothing to find
    "m5-miss": "What's the service interval on a Kestrel K-900?",
    # Module 6: needs estimate_delivery, which is added at the gateway
    "m6": "If we ship that pump from Denver to the customer site in Boulder, when does it arrive?",
}
