━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Decision Log Entry 4 — Betsy Autonomous Procurement Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

0. Context

Project:
Betsy is an autonomous procurement agent built on LangGraph.
The architecture (DL3) defines that the Decide node uses an
LLM for one specific task: confirm the highest-scored
supplier and write a plain-language explanation of why that
supplier was selected.

Why this decision needs to be made now:
The Decide node is implemented and ready to call the LLM,
but the model has not been chosen. Two local models are
available via Ollama: llama3.2:3b and gemma4:e4b. Choosing
the wrong one risks slow response times that make the system
painful to use in development and demos, or inconsistent
JSON output that causes the node to fail. The model must
be confirmed before the full system is tested.

Where this fits:
DL3 defined that the LLM's role is narrow: confirm a
selection from a scored list and explain it in plain
language. DL4 chooses which model performs that narrow
task reliably and fast enough. Once confirmed, DL5 (managing
and monitoring) can be written knowing the full system
runs end-to-end.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Research question

Which local language model produces reliable, parseable
JSON output for the supplier selection task consistently
and quickly enough that it does not become a bottleneck
in development, testing, or demonstration?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2. LO stage

[ ] Analysing   [ ] Advising   [ ] Designing
[X] Realising   [ ] Managing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3. Criteria for a good decision

Criterion 1:
The model must return valid, parseable JSON on every run.
If the model returns prose instead of the required JSON
format, the Decide node fails and the order cannot be
placed. Confirmed by running the selection task three times
per model and checking whether each response can be parsed
without error.

Criterion 2:
The model must select the correct supplier — the one with
the highest pre-calculated SAW score — on every run.
The task is not ambiguous: the scores are provided in the
prompt and the correct answer is the highest one. Confirmed
by checking the selected supplier ID against the expected
answer across three runs.

Criterion 3:
The model must respond in under 10 seconds per run. Betsy
runs on a 4-hour cycle so cycle time is not the concern —
development and demonstration are. A 30-second wait per
LLM call makes iterative testing and live demos painful.
Confirmed by timing each run with a stopwatch and recording
the average.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4. What I decided

llama3.2:3b was selected. Both models passed the accuracy
criteria. llama3.2:3b was 8.6 times faster than gemma4:e4b
(4.0 seconds versus 34.3 seconds average) with no
difference in output quality on this task.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5. Why this decision

Research method — Lab + Showroom:
I used the Lab strategy to run a controlled test — both
models were given the exact same prompt, the same supplier
data, and the same task, and their outputs were recorded
across three runs each. I then used the Showroom strategy
to demonstrate the selected model working inside the full
Betsy system end-to-end, confirming that the model performs
correctly in its actual operating context, not just in the
isolated test.

What I found:

From the Lab test:
The test scenario gave each model three suppliers with
pre-calculated SAW scores: Supplier A at 0.87 (highest),
Supplier B at 0.71, and Supplier C at 0.79. Both models
were asked to return a JSON object identifying the selected
supplier and providing a two-sentence explanation.

llama3.2:3b results across three runs:
- Valid JSON returned: all three runs
- Correct selection (Supplier A): all three runs
- Average response time: 4.0 seconds

gemma4:e4b results across three runs:
- Valid JSON returned: all three runs
- Correct selection (Supplier A): all three runs
- Average response time: 34.3 seconds

Both models achieved identical accuracy. The only measurable
difference was speed: gemma4:e4b took 8.6 times longer to
return the same quality output.

From the Showroom demonstration:
llama3.2:3b was run inside the complete Betsy system — a
full monitoring cycle from inventory check through to the
Decide node calling the model, receiving its selection, and
the gate evaluation running after it. The model returned
valid JSON in every run, the selected supplier matched the
highest SAW score, and the reasoning text it generated was
readable and accurate.

Evidence:
Model comparison table — side-by-side results from three
runs per model showing JSON validity, correct selection,
and response time. Produced by the model comparison test
script using the same input data for both models.

Full system run log — the Decide node calling llama3.2:3b
in context, with the LLM's JSON response and the plain-
language reasoning visible in the terminal output. Shows
the model working correctly inside the full workflow.

What this means:
The supplier selection task is a structured, constrained
problem: pick the highest score from a numbered list. This
does not require deep reasoning or large model capacity —
it requires reliable JSON output and correct reading of
numerical values. llama3.2:3b, as a smaller and faster
model, handles this task just as well as the larger model.
The larger model adds cost (thermal load, memory, time)
without adding benefit for this specific task.

A critical point about model trust: neither model is trusted
to calculate the SAW scores. The scores are calculated by
Python before the model sees them. The model only reads
the pre-calculated scores and selects the highest. This
means that even if the model were to hallucinate slightly,
the hallucination cannot affect the arithmetic — the
financial decision is determined by Python, not the model.

So I decided:
Because both models performed identically on accuracy and
llama3.2:3b was 8.6 times faster, and because the speed
difference has a real impact on development workflow and
demonstration quality, llama3.2:3b was selected. There was
no trade-off to navigate — the faster model was also the
more practical choice with no quality cost.

One additional constraint confirmed the decision: both
models run locally via Ollama. No data leaves the machine.
Supplier pricing, inventory levels, and purchase order data
are commercially sensitive — local execution was a hard
requirement, not a preference.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

6. Does this hold up?

Criterion 1: ✅ — llama3.2:3b returned valid, parseable
JSON on all three test runs and in every full system run.
One early version of the prompt occasionally produced prose
instead of JSON — this was fixed by making the output
format instruction more explicit in the prompt, not by
switching models.

Criterion 2: ✅ — The correct supplier (highest SAW score)
was selected on all three test runs and in all subsequent
full system runs.

Criterion 3: ✅ — Average response time of 4.0 seconds,
well under the 10-second target. In practice this means a
full Betsy cycle from inventory check to purchase order
takes under 30 seconds in demonstration mode.

Assumptions I am making:
llama3.2:3b is assumed to continue producing reliable JSON
output as the prompt and input data vary. The JSON
reliability has held across all test runs, but edge cases
(unusual supplier names, very large supplier lists, non-
Latin characters) have not been tested. A fallback to the
highest Python-calculated score is coded into the Decide
node in case JSON parsing ever fails — this fallback is
logged in the reasoning log so the audit trail remains
honest.

The local Ollama setup requires the model to be pulled and
the Ollama service to be running. If Ollama is not running
when Betsy starts, the Decide node will fail. This is a
deployment dependency that would need to be managed in a
production environment.

What surprised me:
The size of the speed gap was unexpected. A model that is
larger and presumably more capable taking 8.6 times longer
to return the same quality output on a simple structured
task was counterintuitive. The lesson is that model size is
not the right metric for task suitability. A 3-billion-
parameter model that is well-suited to structured output
tasks can outperform a much larger model on those tasks —
both in speed and in practical reliability. The task defines
the right model, not the other way around.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

7. What this unlocks

Evidence artifacts:
Model comparison table — llama3.2:3b versus gemma4:e4b,
three runs each, showing JSON validity, correct selection,
and response time side by side. Produced by the model
comparison test script with consistent results.

Full system run log — the complete Betsy cycle with
llama3.2:3b running in the Decide node, showing the LLM
call, the JSON response, and the selected supplier in the
terminal output.

Next LO stage: Moving to Managing

What I can now do that I could not before:
I can now run the full Betsy system with confidence that the
LLM component will not be a source of errors or slowdowns.
The model selection is confirmed and documented. The
fallback is coded and logged. The system is ready to be
tested across multiple cycles to observe how it performs
over time (DL5).

How I will know this worked:
Over multiple monitoring cycles, the Decide node should
call the model, receive valid JSON, select the correct
supplier, and log the reasoning text without errors. If
the JSON parsing fallback fires more than once in ten
cycles, the prompt design needs revision. If the response
time increases significantly (above 10 seconds), the Ollama
setup needs to be checked.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
