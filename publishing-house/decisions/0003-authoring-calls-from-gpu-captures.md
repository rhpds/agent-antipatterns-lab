# 0003. Authoring calls from the GPU captures (F4, F5, F6, F9)

- **Status:** Accepted
- **Date:** 2026-10-14
- **Decided by:** the agent driving LB8000 decisions, on David's delegation. David can overturn any item.
- **Affects:** module specs 1, 3, 4, 5 and 7; `agent/questions.py`; `agent/regression.py`; the test mock

## Context

The 2026-10-13 GPU captures (`publishing-house/spec/captures/2026-10-13-gpu/`) ran
the starter agent and every module solution against the served model:
`RedHatAI/Qwen3-8B-FP8-dynamic`, temperature 0, seed 0. Four findings showed the model
doing something other than what the module specs describe.

For each one the choice was the same: **change the module to match what the model
really does, or change the setup to get the behaviour the module needs.** The rule
used:

- **Change the setup** only when the module's teaching point depends on the behaviour,
  and a setup change produces it deterministically.
- **Otherwise change the module**, because the real behaviour is what participants
  will see.

## F4. Module 3: the fixed loop makes two `check_stock` calls in one turn

- **Evidence:** `m3-fixed` and `m4-fixed-m3`, three model calls:
  1. `find_part(coolant pump, K-400)`.
  2. `check_stock(KI-CP-40817, Denver)` **and** `check_stock(KI-SK-40233, Denver)`, in
     the same turn.
  3. The answer.

  `find_part` returns the pump and its seal kit, so the model checks both. The spec's
  step 12 says "the two tools were called".
- **Decision: change the module to match.** Step 12 now expects one `find_part` and one
  `check_stock` per part returned, in the same turn, each with its own tool-call id.
- **Why:**
  - It's correct agent behaviour, and it strengthens the module. Parallel tool calls in
    one turn are exactly where the loop must append a result per tool-call id, which is
    module 3's fix.
  - Forcing a single call (dropping the seal kit from `find_part`) would remove a
    realistic detail for no teaching gain.

## F5. Module 4: the starter answer is milder than "confident"

- **Evidence:** `m4-start`. With the swallowed error, the answer is:

  > The high-pressure sensor (KI-HS-60233) for the K-600 is not currently available at the Portland depot. Would you like me to check availability at another depot …

  The spec's step 2 says "a fluent answer that reads as authoritative and reports no
  problem".
- **Decision: change the module to match.** The planted failure is unchanged: the tool
  silently drops an unknown depot and returns an empty success. The spec now describes
  the answer as what it is: a fluent, plausible answer that treats Portland as a real
  depot that is out of stock. It reports no problem with the request itself.
- **Why:**
  - The teaching point holds as observed. The participant gets a wrong answer
    ("unavailable at a depot that doesn't exist") with every signal saying success.
  - A setup change to provoke a stronger claim, such as returning fake stock, would
    plant model behaviour rather than a structural fault, which `design.md` rules out.

## F6. Module 5: the opening run refuses instead of inventing

- **Evidence:**
  - With the original question ("What's the recommended service interval for the K-400
    coolant pump seal?") and no retrieval tool, the model refuses ("I don't have access
    to service interval recommendations").
  - Two rewordings of the seal question, a torque question and a glycol question also
    refuse.
  - The spec's own infrastructure note says: "swap the question if the model refuses
    instead".
- **What was tried** (endpoint B, 2026-10-14, each without and with retrieval):

  | Question | Without retrieval | With retrieval |
  |---|---|---|
  | seal service interval (3 wordings) | refuses | grounded, SB-2024-117 |
  | K-600 fan motor bolt torque | refuses | says it's not in the bulletins |
  | K-400 glycol concentration | refuses | says it's not in the bulletins (the deliberately simple embedding misses SB-2024-131) |
  | **"A K-400 is showing fault F-21. What should the technician do?"** | **invents**: "a temperature sensor or control board", invented part `KI-400-CTRL` | **grounded**: "coolant loop pressure low" from SB-2024-102 |

  The F-21 result was identical in 3 of 3 runs each way. Without retrieval the model
  first calls `find_part("F-21")`, gets no match, then invents. No retrieval happens.
- **Decision: change the setup.**
  - `m5` becomes the F-21 question.
  - `regression.py`'s module 5 check now expects SB-2024-102.
  - `m5-miss` stays "What's the service interval on a Kestrel K-900?". It still reports
    the gap cleanly. An F-21 variant for the K-900 leaked invented "common triggers".
- **Why:**
  - Module 5's premise and first key takeaway ("an agent with no knowledge source does
    not decline to answer") need the invention.
  - The spec prescribes this exact remedy, and the new question produces it
    deterministically.
  - F-21 also continues module 1's "coolant pressure fault" storyline.
  - Like modules 1 and 2, this opening is *evidence* that depends on a model decision,
    not a planted fault. It's covered by the same greedy-decoding mitigation, and
    `design.md` now says so.
- **Captures:** `publishing-house/spec/captures/2026-10-14-m5-f21/`.

## F9. Module 5: the grounded answer goes beyond its passages

- **Evidence:**
  - With the old seal question, the grounded answer added "Replace seal kit KI-SK-40233
    with pump assembly KI-CP-40817", which no passage says.
  - With the new F-21 question, retrieval returns SB-2024-102's *Symptom* passage
    (with SB-2024-117's *Applies to*) but not its *Action* passage. The answer names the
    cause correctly ("coolant loop pressure low"), then gives steps that aren't the
    bulletin's (it omits "bleed air … 2.1 bar within 90 seconds").
- **Decision: change the module to match, and keep the behaviour.**
  - Module 5's success signal stays "the answer corresponds to a retrieved passage",
    which it does for the cause.
  - Step 11 and module 7 use this exact answer as the worked example of "grounding makes
    an answer checkable, not correct": the participant compares the answer's steps with
    the retrieved passages and finds the gap.
- **Why:**
  - The spec already wants this limitation shown ("nothing yet verifies that the
    retrieved passage actually answers the question asked"), and the served model
    supplies a real, reproducible instance.
  - Tightening the prompt or tuning retrieval would hide it. The module 5 spec rules out
    retrieval tuning ("Scope discipline").

## Related: module 1's evidence (from F1)

- **Evidence:** on the mismatched endpoint (`pythonic`), the module 1 response is not an
  invented prose answer. It's `tool_calls` null and the `find_part` call stranded in
  `content` as `<tool_call>{…}</tool_call>`, in 20 of 20 runs
  (`captures/2026-10-14-m1-repeat/`).
- **Decision: change the module to match.** The module 1 spec's overview, steps 5, 6 and
  8, and its "invents a plausible part number" note now describe the stranded call,
  which is the evidence `design.md`'s qualification already designs for.
- **Why:** it's what every participant will see. The lesson is unchanged: the tools
  were offered and the call never fired.

## Not changed

Module prose (`content/modules/ROOT/pages/*.adoc`) is for the author. The module 5 page
gets new CAPTURED data and a `TODO(author)` noting the question change.
