# Mapping to the OpenAI Agents SDK

The blueprint targets the OpenAI Agents SDK (`Agent`, `Runner`, `function_tool`, `handoff`,
guardrails, Sessions). This implementation mirrors those concepts with a thin abstraction so
it runs offline, and provides a drop-in adapter to the real SDK.

| Blueprint / SDK concept | This repo |
|---|---|
| `Agent(name, instructions, model, tools, handoffs)` | `agents/base.py::BaseAgent` subclasses |
| `Runner.run(agent, input, context)` | `pipeline.py::CareerPipeline.run(...)` |
| `function_tool` | plain callables in `tools/` (typed, side-effect-isolated) |
| `handoff(agent)` | orchestrator calling the next agent in sequence |
| `@input_guardrail` / `@output_guardrail` | `guardrails/` pure functions |
| Sessions / context | `models/profile.py::ProfileContext` + `storage/` |
| Tracing | `logging_config.py` + `agent_chain` audit list |

## Drop-in SDK adapter (illustrative)

When you install `openai-agents` and want the real SDK, the specialist agents map directly:

```python
from agents import Agent, Runner, function_tool, handoff
from agents.guardrails import input_guardrail, output_guardrail

from career_assistant.tools import match_score, company_verify, resume_builder

job_matching_agent = Agent(
    name="JobMatchingAgent",
    instructions="Rank verified jobs by weighted skills/experience/location/goals.",
    model="gpt-4o-mini",
    tools=[function_tool(match_score.calculate_match_score)],
)

career_orchestrator = Agent(
    name="CareerOrchestrator",
    instructions="Sequence discovery, verification, matching, customization, application, tracking, skills.",
    model="gpt-4o",
    handoffs=[job_matching_agent, ...],
)

async def run(user_id, action, context):
    return (await Runner.run(career_orchestrator, input=action, context=context)).final_output
```

The `tools/` functions are written to be SDK-compatible (typed args, JSON-serializable
returns), so wrapping them in `function_tool` requires no changes.
