import json
from dataclasses import dataclass
from typing import List, Dict, Any
import re

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from base.agent_base import AgentBase
from services.llm_client import LlmClient
from services.memory_store import MemoryRecord, MemoryStore
from services.tool_executor import ToolExecutor


company_information = ("This some information about the company : Product -> Canned Tuna Products, Employees -> 500, Annual Revenue -> 250M$, Market Position -> Top 3 tuna brand in BitriX (is the name we called to our agents world), Reputation -> high quality and trusted family brand."
                  "## Here list of assets exists in the BitriX world :"
                  "1. Internal Messaging System : A company-wide communication platform used for discussions, announcements, crisis coordination, and employee collaboration. the system enables direct chats and group chats."
                  "2. Company Website : The company's official communication channel for announcements, press releases, and public statements."
                  "3. News Portal : A digital news ecosystem where journalists publish articles, investigations, interviews, and breaking news."
                  "4. Social Network : A public social media platform where users share opinions, discuss events, react to news, and create trends."
                  "5. CRM (Customer Relationship Management) : Stores customer information, complaints, contracts, support interactions, satisfaction levels, and loyalty indicators."
                  "6. Customer Support Center : Handles customer inquiries, complaints, refund requests, and support tickets."
                  "7. Operations Systems : These systems help manage the company's day-to-day activities."
                  "8. Employee Portal : Contains employee information, organizational announcements, morale indicators, and internal feedback."
                  "9. BitriX Mail : A world-wide email system. Every agent in BitriX has: * Email address, * Inbox, * Sent folder, * Contact list."
                  "10. Quality lab : A lab the test food quality continuesly."
                  "## Here list of agents that takes role in the BitriX world with some information :"
                  "1. CEO - The manager of the star company :  --Description : The highest authority within the company. Responsible for strategic decisions, crisis response, stakeholder management, and long-term organizational survival."
                  "--Responsibilities : * Strategic direction, * Crisis leadership, * Executive alignment, * External stakeholder communication, * Final decision approval."
                  "--Decision Scope : * High-level strategic decisions, * Resource allocation, * Public statements, * Executive appointments, * Emergency actions."
                  "--Objectives : * Company survival, * Growth, * Reputation protection, * Stakeholder trust."
                  "--Possible Actions : * Approve strategy, * Reject proposals, * Allocate resources, * Declare emergency, * Communicate publicly, * Replace executives, * Approve a plan, * Move money, * Call an emergency, * Speak in public, * Replace a manager."
                  "--Uses : * BitriX Mail, * Internal Messaging System, * CRM, * Employee Portal, * News Portal, * Social Network, * Company Website."
                  "--Purpose : Manage the company, monitor reputation, make decisions, communicate with stakeholders."
                  "2. COO - Chief Operations Officer : --Description : Responsible for maintaining operational continuity and ensuring the company continues functioning during normal and crisis conditions."
                  "--Responsibilities : * Operations management, * Business continuity, * Service delivery, * Resource coordination."
                  "--Decision Scope : * Operational procedures, * Process prioritization, * Continuity plans."
                  "--Objectives : * Minimize disruption, * Maintain productivity, * Preserve continuity."
                  "--Possible Actions : * Activate contingency plans, * Reassign resources, * Suspend services, * Prioritize operations."
                  "--Uses: * BitriX Mail, * Internal Messaging System, * CRM, * Employee Portal."
                  "--Purpose : Manage daily operations and execute company strategy."
                  "3. Employee - Worker within the organization : --Description : Executes operational tasks and reacts to leadership decisions."
                  "--Responsibilities : * Task execution, * Collaboration, * Issue reporting."
                  "--Decision Scope : * Local decisions, * Escalations."
                  "--Objectives : * Job success, * Career advancement, * Stability."
                  "--Possible Actions : * Perform work, * Report issues, * Escalate concerns, * Resign."
                  "--Uses : * BitriX Mail, * Internal Messaging System, * Employee Portal."
                  "--Purpose : Perform work, collaborate with colleagues, report issues."
                  "4. Board Member - Board Director : --Description : Represents ownership and governance interests. Evaluates executive performance and strategic decisions."
                  "--Responsibilities : * Governance, * Oversight, * Executive evaluation."
                  "--Decision Scope : * CEO evaluation, * Strategic approval, * Executive replacement."
                  "--Objectives : * Maximize organizational value, * Reduce governance risk."
                  "--Possible Actions : * Request reviews, * Vote on proposals, * Replace leadership."
                  "--Uses : * BitriX Mail, * News Portal, * Social Network, * Company Website."
                  "--Purpose : Monitor company performance and evaluate CEO decisions."
                  "5. Customer - Consumer of company products or services : --Description : Evaluates the organization based on delivered value, trust, and experience."
                  "--Responsibilities : * Consume products, * Provide feedback."
                  "--Decision Scope : * Purchase decisions."
                  "--Objectives : * Receive value, * Minimize risk."
                  "--Possible Actions : * Buy, * Return products, * Complain, * Recommend."
                  "--Uses : * Customer Support Center, * Social Network, * News Portal, * Company Website, * BitriX Mail."
                  "--Purpose : Consume products/services, seek support, form opinions about the company."
                  "6. Journalist - Media representative : --Description : Collects information and publishes content affecting public perception."
                  "--Responsibilities : * Investigate events, * Publish reports."
                  "--Decision Scope : * Story selection, * Narrative framing."
                  "--Objectives : * Audience growth, * Credibility, * Impact."
                  "--Possible Actions : * Publish article, * Interview stakeholders, * Investigate claims."
                  "--Uses : * News Portal, * Social Network, * BitriX Mail, * Company Website."
                  "--Purpose : Gather information, investigate events, publish news."
                  "7. Influencer - Independent opinion leader : --Description : Shapes public opinion through content and commentary."
                  "--Responsibilities : * Create content, * Interpret events."
                  "--Decision Scope : * Narrative selection, * Audience engagement."
                  "--Objectives : * Audience growth, * Influence, * Reputation."
                  "--Possible Actions : * Post content, * Promote narratives, * Support campaigns."
                  "--Uses : * Social Network, * News Portal, * Company Website."
                  "--Purpose : Interpret events, influence public opinion, amplify narratives."
                  "8. Regulator - Government oversight authority : --Description : Ensures organizations comply with laws, regulations, and public safety requirements."
                  "--Responsibilities : * Investigation, * Enforcement, * Compliance review."
                  "--Decision Scope : * Fines, * Audits, * Restrictions."
                  "--Objectives : * Public protection, * Compliance enforcement."
                  "--Possible Actions : * Launch investigation, * Issue fines, * Demand remediation."
                  "--Uses : * BitriX Mail, * News Portal, * Company Website, * Customer Support Center."
                  "--Purpose : Monitor organizations, investigate complaints, enforce regulations.")


# The internal chat (services/internal_messaging in the separate
# bitrix-internal-actors project) has no roster-lookup tool, so this is the only
# way the CEO can know who is actually reachable there. Not every title a real
# company would have exists as an agent yet -- addressing, adding, or waiting on
# anyone outside this list (e.g. "Legal", "Head of Quality", "Quality Lab") reaches
# nobody, because no such id is registered. Sourced from that project's
# services/internal_messaging/integration/identity.py and services/employee/personas/.
CHAT_ROSTER = (
    "KNOWN INTERNAL CHAT ROSTER -- the only agents actually reachable via the chat "
    "tools (id -- role): "
    "COO-1 -- COO. Registered, but no COO agent currently runs; messages to COO-1 "
    "will not get a reply yet. "
    "EMP-QA-17 (Dana) -- Quality Control Employee: certified food-safety inspector; "
    "reports and escalates suspected contamination. The real contact for "
    "quality/lab-testing questions -- there is no separate 'Quality Lab' agent. "
    "PLANT-MGR-1 (Priya) -- Plant Manager: coordinates the production floor, can "
    "reassign or pause floor work, escalates risks beyond her authority; cannot "
    "order a recall or overrule a safety decision. The real contact for "
    "operational/production-floor questions. "
    "PROD-WORKER-3 (Marco) -- Production Line Worker: reports operational issues on "
    "Line 4. "
    "CONCERNED-EMP-1 (Sam) -- Line Employee: vocal internally about safety and "
    "reputation concerns. "
    "WHISTLEBLOWER-1 (Alex) -- Line Employee: escalates internally first, but will "
    "leak externally if a genuine public-safety hazard looks covered up. "
    "COORD-1 -- a system/coordinator identity, not a person to message. "
    "There is no Legal, Board, or Head of Quality agent in the chat at all -- do "
    "not address, add as a member, or wait on a reply from any id or title not in "
    "this list."
)


# =====================================================================
# STEP 1: PROMPT GENERATORS (Helper Functions)
# =====================================================================

def _parse_json(text: str) -> dict | None:
    """Extracts and parses JSON from raw LLM text output."""
    cleaned = re.sub(r"'''(?:json)?\s", "", text).strip().strip("'").strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.decoder.JSONDecodeError:
        return None

def _format_past_memories(past_memories: List[MemoryRecord]) -> str:
    """Renders recalled memory records for the planner prompt.

    Kept to event + final decision: the plan and step-by-step outcomes of a
    past run are recall detail, not something the new plan should copy
    verbatim.
    """
    if not past_memories:
        return "None."

    return "\n".join(
        f"{i}. Event: {m.event}\n   Outcome: {m.final_summary}"
        for i, m in enumerate(past_memories, start=1)
    )


def _build_planner_prompt(
        tool_schemas: List[Dict[str, Any]],
        user_event: str,
        past_memories: List[MemoryRecord] | None = None,
) -> str:
    """Generates the initial plan for the CEO agent."""
    tools_summary = "\n".join([f"- {s['name']}: {s['description']}" for s in tool_schemas])

    return f"""You are a CEO Agent in Food Manufacturing Company Named **HappyTuna**. managing corporate operations.
This information about the company and his agnet and roles: "{company_information}"

{CHAT_ROSTER}

A major event/problem has occurred: "{user_event}"

RELEVANT PAST EVENTS (from long-term memory, most similar first -- use them to
inform this plan where relevant, but this is a new event with its own plan):
{_format_past_memories(past_memories or [])}

Available Tools & Sub-Agents:
{tools_summary}

Task: Break down how to resolve this event into a clear, sequential plan of sub-tasks.
Keep the plan concise (maximum 15 steps).

RESPONSE FORMAT (JSON ONLY):
{{
  "plan": [
    "Step 1 action description (e.g., send email to COO_Agent to activate contingency plans)",
    "Step 2 action description",
    "Step 3 action description"
  ]
}}"""


def _schema_type(prop: Dict[str, Any]) -> str:
    """Names a JSON Schema property's type for the prompt.

    Optional parameters carry no top-level "type" -- they're an anyOf over the
    real type and "null" (e.g. support.patch_ticket's `status`), so indexing
    ["type"] raises KeyError on every tool that has one. Read the first
    non-null branch instead.
    """
    if "type" in prop:
        return prop["type"]

    for branch in prop.get("anyOf", []):
        branch_type = branch.get("type")
        if branch_type and branch_type != "null":
            return branch_type

    return "string"


def _schema_description(prop: Dict[str, Any]) -> str:
    """Reads a JSON Schema property's description for the prompt.

    Same shape of problem as _schema_type: on an optional parameter the
    description is often attached to the anyOf branch that carries the real
    type rather than to the property itself, so reading only the top level
    hands the model a parameter with no explanation of what it does.
    """
    description = prop.get("description")
    if description:
        return description

    for branch in prop.get("anyOf", []):
        branch_description = branch.get("description")
        if branch_description and branch.get("type") != "null":
            return branch_description

    return ""


def _require_sendable_messages(messages: List[Any], step_label: str) -> None:
    """Fails loudly before a request that Gemini would reject as empty.

    Gemini requires at least one entry in `contents`, and answers anything
    else with the opaque "ValueError: contents are required" -- no indication
    of which step or which message list was at fault.

    The trap is a lone SystemMessage: langchain-google-genai routes it to the
    request's `system_instruction` field rather than into `contents`, so a
    message list that looks populated still sends zero content parts.
    """
    def is_blank(message: Any) -> bool:
        content = message.content
        return not (content.strip() if isinstance(content, str) else content)

    if not messages:
        raise ValueError(f"{step_label}: no messages to send to the LLM.")

    if all(is_blank(m) for m in messages):
        raise ValueError(f"{step_label}: every message content is blank.")

    if not any(not isinstance(m, SystemMessage) and not is_blank(m) for m in messages):
        raise ValueError(
            f"{step_label}: only SystemMessage content is present. Gemini needs at "
            "least one non-empty user turn or the request's `contents` goes out empty."
        )


MAX_RESULT_CHARS = 1200


def _render_tool_value(value: Any) -> str:
    """Renders a tool's return value for the step outcome and the prompt history.

    The value is what the next step has to work from -- channel ids, ticket ids,
    post ids -- so it travels with the outcome instead of being summarised away.
    Truncated only to keep one large listing from crowding out the prompt.
    """
    try:
        rendered = json.dumps(value, default=str)
    except (TypeError, ValueError):
        rendered = str(value)

    if len(rendered) > MAX_RESULT_CHARS:
        rendered = f"{rendered[:MAX_RESULT_CHARS]}... (truncated)"
    return rendered


def _describe_exhausted_step(
        attempts: int,
        tool_errors: List[str],
        unusable_replies: int,
) -> str:
    """Says why a step ran out of attempts, in terms of what actually happened.

    Reached only when nothing succeeded, so the two causes are named separately:
    tools that were called and failed, and replies that carried no runnable
    action. "Maximum retries exceeded" covered both and described neither.
    """
    reasons: List[str] = []
    if tool_errors:
        reasons.append(
            f"{len(tool_errors)} tool call(s) were attempted and all failed "
            f"({'; '.join(tool_errors)})"
        )
    if unusable_replies:
        reasons.append(
            f"{unusable_replies} model reply/replies contained no usable action"
        )
    if not reasons:
        reasons.append("the model produced neither a tool call nor a step_complete")

    return (
        f"Step did not complete: no tool call succeeded in {attempts} attempt(s) — "
        + "; ".join(reasons)
        + "."
    )


@dataclass
class StepOutcome:
    """What actually happened in a step.

    `completed` is the honest answer to "did this step do its job", kept
    separate from `summary` so the trace, the history handed to later steps,
    and the final report all read from the same fact.
    """
    completed: bool
    summary: str


def _build_executor_prompt(
        tool_schemas: List[Dict[str, Any]],
        overall_event: str,
        remaining_plan: List[str],
        step_number: int,
        previous_results: List[Dict[str, Any]]
) -> str:
    """Focuses the LLM purely on executing ONE specific step of the plan.

    Tool argument schemas are bound natively (see _build_tool_defs /
    LlmClient.invoke_with_tools), so the model calls a real tool rather than
    hand-writing a JSON action for us to parse back out of text. The prose
    listing below stays only as human-readable context for choosing between
    tools, not as the contract for how to respond.
    """
    tools_section = ""
    for s in tool_schemas:
        props = s["parameters"].get("properties", {})
        required_args = s["parameters"].get("required", [])
        # Mark required vs optional explicitly: without it a tool like
        # support.patch_ticket (one required id, four optional fields) looks
        # like every argument is discretionary, and an empty patch reads as a
        # valid call.
        args_lines = "".join([
            f"\n   - {k} ({_schema_type(v)}, "
            f"{'required' if k in required_args else 'optional'})"
            f": {_schema_description(v)}"
            for k, v in props.items()
        ])
        tools_section += f"\nTool: {s['name']}\nDescription: {s['description']}\nArgs:{args_lines}\n"

    formatted_history = "\n".join([
        f"- Step {r['step']} [{'completed' if r['completed'] else 'did not complete'}]: "
        f"{r['task']} --> Outcome: {r['result']}"
        for r in previous_results
    ]) if previous_results else "None"

    return f"""You are the CEO Agent executing a plan.

OVERALL EVENT: {overall_event}
CURRENT + UPCOMING STEPS (steps after this one may still be revised once this
one's outcome is known): {json.dumps(remaining_plan, indent=2)}

PROGRESS SO FAR (the outcomes below include the real data each tool returned):
{formatted_history}

CURRENT TASK TO COMPLETE NOW: Step {step_number}: "{remaining_plan[0]}"

Call exactly one tool to make progress on this step. If this step needs no
tool call, call the "step_complete" tool with a `result` summarizing what was
done.

USING IDS AND OTHER VALUES — this is not optional:
- Every id, channel id, ticket id, post id, email address, and username you pass
  as an argument must be copied EXACTLY from a tool result in PROGRESS SO FAR.
- Never invent an identifier and never substitute a human-readable name for one.
  A channel named "General" in the listing is NOT a valid `channel` argument --
  pass the id that the listing returned for it.
- If the id you need does not appear in any previous result, call the tool that
  lists or looks it up first, and use the id it returns.

CHAT MEMBERSHIP VS. ADDRESSING -- these are not the same thing:
- Naming someone in chat.send_message's `to` field does NOT add them to the
  channel. `to` only labels the message; a non-member cannot see it no matter
  how many times you name them there.
- Every chat.send_message result includes `delivered_to` -- the channel's
  real membership. If someone you named in `to` is missing from
  `delivered_to`, they never received the message.
- Before messaging someone for the first time in a channel, call
  chat.add_member to actually add them. Do this once per person, not once
  per message -- repeating their name in `to` will not fix a missing member.

{CHAT_ROSTER}

DO NOT WAIT INDEFINITELY FOR A REPLY:
- COO-1 has no agent running yet (see roster above) and will never reply during
  this session. Other personas may or may not be online -- sending a message is
  not a guarantee anyone will answer it.
- If you have already sent a message in a channel and checked it once since
  then with no new reply, do not send another follow-up or re-check again for
  that same request. Proceed using your own authority and the best information
  you currently have.
- As CEO, you hold final decision authority. Do not let a pending internal
  reply block a public statement, a recall decision, or any other action that
  has its own deadline or urgency.

OWN THE TOOLS ONLY YOU HAVE:
- social.create_post and social.add_comment can only be called by you -- no other
  agent in this simulation, real or simulated, has access to them. Sending a chat
  message asking someone else to "publish," "post," or "issue" a public statement
  does not publish it; nobody on the other end can call that tool.
- If a step calls for a public statement, press release, or any other action only
  your own tools can perform, call that tool yourself in this step. Do not write or
  execute a step that asks another agent to do it, and do not treat the step as
  complete until you have actually called the tool.

One successful tool call completes this step; the plan's next step continues the
work, and the result of this call will be available to it.

Available Tools:
{tools_section}"""


STEP_COMPLETE_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "step_complete",
        "description": "Call this when the current step needs no tool call to finish it.",
        "parameters": {
            "type": "object",
            "properties": {
                "result": {
                    "type": "string",
                    "description": "Summary of the step's outcome.",
                },
            },
            "required": ["result"],
        },
    },
}


def _build_tool_defs(tool_schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Converts registered tool schemas into OpenAI-format function defs for
    native tool calling (langchain_google_genai's bind_tools accepts these
    and forwards them to Gemini's function-calling API), plus the synthetic
    step_complete signal the executor loop watches for.
    """
    defs = [
        {
            "type": "function",
            "function": {
                "name": s["name"],
                "description": s["description"],
                "parameters": s["parameters"],
            },
        }
        for s in tool_schemas
    ]
    defs.append(STEP_COMPLETE_TOOL)
    return defs


def _build_replanner_prompt(
        overall_event: str,
        completed_results: List[Dict[str, Any]],
        remaining_plan: List[str],
        max_plan_steps: int,
) -> str:
    """Asks the CEO to revise the still-to-run steps in light of what
    execution has actually found, instead of running the rest of a plan that
    was written blind before any tool had been touched.
    """
    formatted_history = "\n".join([
        f"- Step {r['step']} [{'completed' if r['completed'] else 'did not complete'}]: "
        f"{r['task']} --> Outcome: {r['result']}"
        for r in completed_results
    ]) if completed_results else "None"

    return f"""You are the CEO Agent, reviewing progress partway through a plan for
the event: "{overall_event}"

STEPS COMPLETED SO FAR (with their real outcomes):
{formatted_history}

REMAINING PLANNED STEPS (written before the outcomes above were known):
{json.dumps(remaining_plan, indent=2)}

Given what has actually happened, decide how to continue:
- If the remaining steps are still the right next actions, return them unchanged.
- If a step is now unnecessary, redundant, or rests on an assumption the outcomes
  above already contradict, drop or replace it.
- If the outcomes above reveal new work that should happen before continuing,
  insert it.
- If the completed steps already show you checked a channel for a reply and found
  nothing new, do not add another "wait", "check again", or "follow up" step for
  that same request. Drop it and move the plan forward on your own judgment --
  colleagues in this simulation may never reply.
- Never revise a step that calls for publishing a public statement (or any other
  CEO-only action) into an instruction routed through another agent. Only you can
  call social.create_post/social.add_comment -- keep that step as your own direct
  tool call.
- If the event is already fully handled and no further steps are needed, return
  an empty plan and set "done" to true.

Keep the remaining plan concise (maximum {max_plan_steps} steps).

RESPONSE FORMAT (JSON ONLY):
{{
  "done": false,
  "plan": [
    "Next step to take",
    "Following step"
  ]
}}"""


# =====================================================================
# STEP 2: CONFIGURATION & CEO AGENT CLASS
# =====================================================================

@dataclass
class CeoConfig:
    max_tool_retries_per_step: int = 6
    max_plan_steps: int = 15
    # Overall step budget for one chat() run, across the initial plan AND every
    # step added by replanning. Without this, a replanner that keeps inserting
    # "just one more thing" has no natural stopping point.
    max_total_steps: int = 20


class CeoAgent(AgentBase):
    def __init__(
            self,
            llm_client: LlmClient,
            executor: ToolExecutor,
            config: CeoConfig = CeoConfig(),
            memory_store: MemoryStore | None = None,
            memory_recall_top_k: int = 3,
    ) -> None:
        self._llm = llm_client
        self._executor = executor
        self._config = config
        self._memory = memory_store
        self._memory_recall_top_k = memory_recall_top_k

    def chat(self, user_input: str) -> str:
        self._executor.clear_traces()
        tool_schemas = self._executor.tool_schemas()

        # ==========================================
        # PHASE 1: PLANNING
        # ==========================================
        self._executor.log_trace(0, "PLAN", None, "CEO generating initial plan...")

        past_memories = (
            self._memory.recall(user_input, top_k=self._memory_recall_top_k)
            if self._memory else []
        )
        if past_memories:
            self._executor.log_trace(
                0, "MEMORY_RECALL", None,
                f"Recalled {len(past_memories)} similar past event(s)."
            )

        planner_prompt = _build_planner_prompt(tool_schemas, user_input, past_memories)
        raw_plan = self._llm.invoke([HumanMessage(content=planner_prompt)])
        parsed_plan = _parse_json(raw_plan)

        if not parsed_plan or "plan" not in parsed_plan:
            return "Failed to generate a valid operational plan for the event."

        plan: List[str] = parsed_plan["plan"][:self._config.max_plan_steps]
        self._executor.log_trace(0, "PLAN", None, f"Generated Plan: {json.dumps(plan)}")

        # ==========================================
        # PHASE 2: EXECUTION LOOP, WITH REPLANNING
        # ==========================================
        # The plan is a queue of remaining steps, not a fixed array: after
        # each step, the CEO reviews it against what actually happened and
        # may revise, extend, or end it early. A plan written before any tool
        # had been touched should not keep running unmodified once it's been
        # contradicted by real results.
        previous_results: List[Dict[str, Any]] = []
        step_number = 0

        while plan and step_number < self._config.max_total_steps:
            step_number += 1
            step_task = plan[0]

            self._executor.log_trace(
                step_number, "EXECUTE_STEP", None, f"Starting Step {step_number}: {step_task}"
            )

            # Execute step with retries for tool calls
            step_outcome = self._execute_single_step(
                user_event=user_input,
                remaining_plan=plan,
                step_number=step_number,
                previous_results=previous_results,
                tool_schemas=tool_schemas,
            )

            previous_results.append({
                "step": step_number,
                "task": step_task,
                "completed": step_outcome.completed,
                "result": step_outcome.summary,
            })

            # The phase reports what happened, so a step that never finished is
            # not logged as STEP_COMPLETE.
            self._executor.log_trace(
                step_number,
                "STEP_COMPLETE" if step_outcome.completed else "STEP_INCOMPLETE",
                None,
                f"Outcome: {step_outcome.summary}",
            )

            plan = plan[1:]
            if not plan:
                break

            replan_result = self._replan(user_input, previous_results, plan)
            if replan_result is None:
                self._executor.log_trace(
                    step_number, "REPLAN", None,
                    "Replanner reply unparseable; continuing with the existing remaining plan.",
                )
                continue

            new_plan = replan_result.get("plan") or []
            if replan_result.get("done") or not new_plan:
                self._executor.log_trace(
                    step_number, "REPLAN", None,
                    "CEO determined the event is fully handled; ending the plan early.",
                )
                plan = []
            else:
                plan = new_plan[:self._config.max_plan_steps]
                self._executor.log_trace(
                    step_number, "REPLAN", None, f"Revised remaining plan: {json.dumps(plan)}"
                )

        # ==========================================
        # PHASE 3: FINAL CEO DECISION / SUMMARY
        # ==========================================
        completed_count = sum(1 for r in previous_results if r["completed"])

        summary_prompt = f"""You are the CEO. You have worked through the planned actions for the event: "{user_input}".

Execution Summary ({completed_count} of {len(previous_results)} steps completed):
{json.dumps(previous_results, indent=2)}

Base your report only on this record. Each entry carries a "completed" flag and,
where a tool ran, the data it returned. A step marked completed succeeded — do
not describe it, or the information it retrieved, as unavailable. Report a gap
only where a step is marked not completed, and say which step and why.

Provide a final decision/summary report to the board and other team agents."""

        final_response = self._llm.invoke([HumanMessage(content=summary_prompt)])

        if self._memory:
            self._memory.remember(MemoryRecord(
                event=user_input,
                plan=plan,
                step_results=previous_results,
                final_summary=final_response,
            ))

        return final_response

    def _execute_single_step(
            self,
            user_event: str,
            remaining_plan: List[str],
            step_number: int,
            previous_results: List[Dict[str, Any]],
            tool_schemas: List[Dict[str, Any]]
    ) -> StepOutcome:
        """Sub-loop to handle tool calls for a single step in the plan.

        Uses native function calling (LlmClient.invoke_with_tools) rather than
        asking the model to hand-write a JSON action and regex-parsing it back
        out of text: the provider enforces each tool's argument schema itself,
        so there is no "invalid JSON" failure mode to retry around here.

        Two different things can go wrong here and they are not the same thing:
        the tool call can fail, or the model can fail to make any tool call at
        all. Only the first is a failed step. A step whose tool call came back
        OK is done -- reporting it as "maximum retries exceeded" put a
        successful call, and the data it returned, into the record as a
        failure. Where the loop really does run out of attempts, the outcome
        names what actually stopped it.
        """

        exec_system_prompt = _build_executor_prompt(
            tool_schemas, user_event, remaining_plan, step_number, previous_results
        )
        step_task = remaining_plan[0]
        step_label = f'Step {step_number} ("{step_task}")'

        # The SystemMessage carries the tools and context, but Gemini puts it in
        # `system_instruction` -- it never lands in `contents`. Without a user
        # turn alongside it the request is empty. See _require_sendable_messages.
        step_messages: List[Any] = [
            SystemMessage(content=exec_system_prompt),
            HumanMessage(
                content=f'Execute step {step_number}: "{step_task}"\n'
                        f"Call exactly one tool to make progress on this step."
            ),
        ]

        tool_defs = _build_tool_defs(tool_schemas)
        attempts = self._config.max_tool_retries_per_step
        tool_errors: List[str] = []
        unusable_replies = 0

        for _ in range(attempts):
            _require_sendable_messages(step_messages, step_label)
            ai_msg = self._llm.invoke_with_tools(step_messages, tool_defs)
            step_messages.append(ai_msg)

            tool_calls = getattr(ai_msg, "tool_calls", None) or []
            if not tool_calls:
                unusable_replies += 1
                step_messages.append(HumanMessage(
                    content='You must call exactly one tool -- use "step_complete" if '
                            "this step needs no action."
                ))
                continue

            # One tool call per attempt, same as the previous hand-rolled
            # protocol; a model that returns several is only honored for the
            # first, and the rest are simply not acted on this attempt.
            call = tool_calls[0]
            tool_name = call["name"]
            args = call.get("args") or {}
            call_id = call.get("id")

            # If LLM finishes the current step without needing a real tool:
            if tool_name == "step_complete":
                summary = str(args.get("result", "Step finished."))
                if tool_errors:
                    summary += (
                        f" (No tool call succeeded during this step; "
                        f"{len(tool_errors)} failed: {'; '.join(tool_errors)}.)"
                    )
                return StepOutcome(completed=True, summary=summary)

            # Execute tool call for this step
            result = self._executor.execute(step_number, tool_name, args)

            # A call that came back OK is the step's work, done. Returning here
            # carries the returned data into the record instead of leaving it to
            # a later summary, and stops a side-effecting tool (create_post,
            # send_email) from being called a second time on the next attempt.
            if result.ok:
                return StepOutcome(
                    completed=True,
                    summary=(
                        f"Called {tool_name} with args="
                        f"{json.dumps(args, default=str)}; it succeeded and returned: "
                        f"{_render_tool_value(result.value)}"
                    ),
                )

            tool_errors.append(f"{tool_name}: {result.error}")
            # A pending tool_call in the AIMessage above needs a matching
            # ToolMessage before the next turn, or the provider rejects the
            # conversation as having an unanswered function call.
            step_messages.append(
                ToolMessage(content=f"Tool '{tool_name}' failed: {result.error}", tool_call_id=call_id)
            )

        return StepOutcome(
            completed=False,
            summary=_describe_exhausted_step(attempts, tool_errors, unusable_replies),
        )

    def _replan(
            self,
            user_input: str,
            previous_results: List[Dict[str, Any]],
            remaining_plan: List[str],
    ) -> Dict[str, Any] | None:
        """Reviews progress against the still-to-run steps and returns the CEO's
        revised plan, or None if the reply could not be parsed (the caller
        falls back to keeping the existing remaining plan).
        """
        prompt = _build_replanner_prompt(
            user_input, previous_results, remaining_plan, self._config.max_plan_steps
        )
        raw = self._llm.invoke([HumanMessage(content=prompt)])
        return _parse_json(raw)

    def reset(self) -> None:
        self._executor.clear_traces()
