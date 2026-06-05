━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GROWTH REFLECTION
Betsy — Autonomous Procurement Agent
LO7 Personal Leadership
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

How I approached DL1:

In DL1, I was deciding which framework to use. I went in with a
working assumption: the three main agent frameworks (LangGraph,
AutoGen, CrewAI) were broadly comparable options and the choice
would come down to familiarity or community support. I had read the
documentation for each and had a rough sense that they all "did
agents." I thought the decision would involve trade-offs — maybe one
was faster, one had better documentation, one had more examples — and
I would pick the one that seemed most practical.

I did not assume I needed a controlled test. I thought I could read
about the frameworks and make a reasonable judgment.

What broke that assumption:

When I ran the comparison test, I found that AutoGen and CrewAI do
not have a pause mechanism. Not "their pause mechanism is harder to
use" — they genuinely cannot stop mid-workflow and wait for a human
response. They are built for a completely different pattern: an agent
that reasons to a conclusion and returns an answer. I assumed the
difference between frameworks was a matter of degree. The test showed
the difference was architectural — two of the three frameworks could
not do the most important thing the project required, no matter how
the prompt or configuration was adjusted.

The assumption that broke was: "agent frameworks are roughly
interchangeable for agent tasks." They are not. Framework choice
determines what is and is not possible, not just how convenient the
implementation is.

How I approached my last DL differently:

By DL6, I was not making any design assumption without first seeing
what the system actually did under real conditions. When monitoring
showed that G3 was firing incorrectly, I did not immediately go to
the code and look for a logical error. I went to the audit log first,
read what values the system was using when the gate fired, and traced
the problem from the observed behaviour back to its cause. I found a
null-value assumption I had never explicitly made — it was just an
implicit gap in the data model that only appeared with data the test
scenarios had not covered.

In DL1, I thought I could decide by reading. By DL6, I was
consistently waiting to observe before deciding. The shift was from
"I can reason about what will work" to "I need to see what actually
happens, because real conditions produce problems that reasoning
alone misses."

What this project revealed about how I work:

Strength: I am systematic when I set up a test. The framework
comparison, the gate test, the model comparison — each one was
designed before it was run, with criteria defined in advance, the
same input used for every option, and the results recorded in a
format that made the answer clear. This is something I did
consistently across every LO stage, not just once. When I set up
a proper test, I get evidence I can actually defend.

Development area: I underestimate how much real operation differs
from prepared test scenarios. The G3 bug did not appear in any of
the test scripts because every test used data where the last price
was populated. New suppliers with no history were never in the test
data. I thought "it works on the test scenarios" meant "it works."
It means "it works on the scenarios I thought of." The difference
matters more than I expected, and I want to build the habit of
asking "what data condition did I not think to test?" before
declaring something complete.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
