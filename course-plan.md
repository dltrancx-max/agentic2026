# Agentic AI Course — Planning Notes

**Audience:** Production-level developers
**Source taxonomy:** 20 patterns from YouTube video `youtu.be/e2zIr_2JMbE` (full list in `design patterns.docx`)

---

## Taxonomy choice

For production-level developers, **the video's taxonomy is the better spine** — it matches how this audience already thinks (reliability, cost, monitoring, failure modes). Reasoning techniques like Tree-of-Thoughts are intellectually interesting but they will deal with retries and eval pipelines far more often in their day jobs.

## Additions worth slotting in

The video has a few gaps for a developer audience:

- **The ReAct loop** — taught *before* Pattern 1. It is the foundational mental model. Developers need to see the thought → action → observation loop before they see chaining.
- **Agentic RAG** — as a variant on Pattern 13 (Retrieval). Naive RAG breaks down quickly in real systems.
- **CodeAct (code-as-action)** — under Pattern 5 (Tool Use). Relevant for any data/ops automation.

## Teaching order (≠ numerical order)

The video numbers the patterns topically. That is not how to teach them. A sequence that builds momentum:

| Day | Module | Patterns |
|---|---|---|
| 1 | **Foundations** — what is an agent vs a workflow | ReAct loop, Tool Use (5), Prompt Chaining (1), Routing (2), Parallelization (3). Build a working agent by end of day. |
| 2 | **Reasoning & quality** | Reasoning Techniques (16), Reflection (4), Planning (6), Memory (8). Build a planner. |
| 2.5 | **Knowledge** | RAG (13) + Agentic RAG. Build a doc-grounded assistant. |
| 3 | **Multi-agent** | Multi-Agent Collaboration (7), Inter-Agent Communication (14). Build a small crew. |
| 4 | **Production hardening** (where this audience perks up) | HITL (12), Guardrails (18), Exception Handling (11), Monitoring (10/17), Resource-Aware (15), Learning loops (9). |
| 5 | **Advanced / open-ended + capstone** | Prioritization (19), Exploration & Discovery (20). |

## Emphasis points for this audience

- **Every pattern gets a "what breaks in prod" discussion.** Production developers respect this and tune out without it.
- **Pair each pattern with a concrete framework binding** — LangGraph node, CrewAI primitive, plain Python with the Anthropic SDK. Abstract patterns without code do not stick.
- **Spend disproportionate time on Evaluation (Pattern 17).** Most teams skip it and regret it within three months.
- **Explicitly cover when NOT to use an agent** — a deterministic workflow or a single LLM call is often the right answer. Without this lesson, junior-ish teams over-agentify everything.
- **Cost/latency math per pattern.** Show actual token counts. Developers respond to numbers.

---

## Next steps (pick one)

1. **Day 1 slide-by-slide outline** — actual slide-level content and a hands-on lab spec.
2. **Consolidated reference doc** — all 20 patterns + additions, framework bindings, failure modes.
3. **One pattern, end-to-end, as a template** — definition, code, failure modes, exercise. Then replicate the format across the other 19.
4. **Capstone exercise spec** — what students build by end of week.

Recommended starting point: **#3** — getting one pattern's pedagogy right gives a template that scales to the other 19 without re-litigating format each time.
