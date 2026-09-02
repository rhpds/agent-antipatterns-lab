# Module 3. The agent loop: stop conditions and turn control

### Brief Overview

The agent calls tools now, which means it can call them badly. Run it again and it calls the same tool with the same arguments over and over until it hits the iteration cap, then returns whatever it has. The cause is in the supplied loop, not in the model: the loop sends the message list, takes the response, and sends the same list again without appending the tool result and without ever reading why the model stopped.

Participants fix the loop so that it appends tool results to the conversation and terminates on the model's reported stop condition. This is the module where the agent stops being a single request and becomes multi-step, which is what the topic slot asks for.

### Audience and Time

Technical Sellers and Services, intermediate. 16 minutes.

Requires module 2. The agent must be able to call a tool before loop behaviour is observable at all.

### Learning Objectives

- Build an agent loop that terminates on the model's reported stop condition rather than on a text heuristic, a first response, or an iteration cap.
- Analyze a multi-turn trace to distinguish a model repeating itself from a harness that discards what the model returned.

### Lab Structure

| Section | Title | Duration |
|---------|-------|----------|
| 1 | Watch it loop | 4 min |
| 2 | Find the discarded result | 4 min |
| 3 | Fix the loop | 6 min |
| 4 | Confirm termination | 2 min |

### Detailed Steps

1. Run the agent on the supplied multi-step question: *"Can we get a replacement coolant pump for a K-400 to the Denver depot this week?"* Answering needs `find_part` and then `check_stock`.
2. Observe that it runs for noticeably longer than the module 2 run and eventually returns a partial or generic answer.
3. Open the trace. Count the turns. The run hit the iteration cap.
4. Read the tool invocations in sequence. The same tool, the same arguments, every turn.
5. Open the loop code. Identify two defects in the supplied implementation.
6. First defect: the tool result is fetched and then never appended to the message list sent back to the model. The model is asked the same question repeatedly and answers it the same way each time. The repetition is caused by code, not by the model.
7. Second defect: the loop's exit condition is an iteration counter and a text check for a phrase like "final answer". It never inspects the field the model uses to report why it stopped.
8. Apply the supplied fix for the first defect: append each tool result to the message list, with the tool call id it corresponds to, before the next request.
9. Apply the supplied fix for the second defect: branch on the model's reported stop condition. If it indicates a tool call, execute and continue. If it indicates the model finished, return. Keep the iteration cap as a backstop, not as the mechanism.
10. Re-run the multi-step question.
11. Confirm in the trace that the turn count is well below the cap and that the run ended on the model's own stop condition. **This is the module's success signal.**
12. Confirm that the two tools were called with different arguments and that both results appear in the message list.

### Key Takeaways

- A loop that discards tool results asks the same question forever and gets the same answer forever. The repetition looks like model stubbornness and is not.
- The model reports why it stopped. A loop that does not read that field is guessing.
- Parsing prose for a completion phrase makes termination depend on wording, which changes between models and between prompts.
- An iteration cap is a safety net. When it is the primary exit path, every run costs the maximum.
- Multi-step behaviour is a property of the harness. The model contributes one turn at a time.

### Infrastructure Notes

- **The repetition must come from the harness, not the model.** The supplied loop discards tool results and re-sends an identical message list, so the repeat is structurally guaranteed. Do not rely on the model choosing to repeat itself; that is stochastic and will not reproduce identically across a room.
- **The chain must be unbreakable.** `check_stock` takes a part number, and the part number exists only in `find_part`'s output, so a loop that discards tool results cannot reach the second call by luck. Do not let `check_stock` accept a free-text description as a fallback.
- **The iteration cap must be low enough to hit quickly** and high enough that the corrected run is visibly below it. A cap around six turns against a corrected run of two or three reads clearly in a trace.
- **Both defects must be fixable independently**, so a participant who only completes the first still sees a behaviour change and is not stuck.
- **Tool call ids matter.** The corrected loop must associate each result with the call it answers. Getting this wrong produces a confusing downstream failure in module 4, where error categories attach to the wrong call.
- Runs must reset cleanly so every participant starts this module from the same looping state.
