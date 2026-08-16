import json
from dataclasses import dataclass
from typing import List, Dict, Any
import re

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from base.agent_base import AgentBase
from services.llm_client import LlmClient
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

def _build_planner_prompt(tool_schemas: List[Dict[str, Any]], user_event: str) -> str:
    """Generates the initial plan for the CEO agent."""
    tools_summary = "\n".join([f"- {s['name']}: {s['description']}" for s in tool_schemas])

    return f"""You are a CEO Agent in Food Manufacturing Company Named **HappyTuna**. managing corporate operations.
This information about the company and his agnet and roles: "{company_information}"     
A major event/problem has occurred: "{user_event}"

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


def _build_executor_prompt(
        tool_schemas: List[Dict[str, Any]],
        overall_event: str,
        plan: List[str],
        current_step_idx: int,
        previous_results: List[Dict[str, Any]]
) -> str:
    """Focuses the LLM purely on executing ONE specific step of the plan."""
    tools_section = ""
    for s in tool_schemas:
        props = s["parameters"].get("properties", {})
        required_args = s["parameters"].get("required", [])
        args_lines = "".join([f"\n   - {k} ({v['type']}): {v.get('description', '')}" for k, v in props.items()])
        tools_section += f"\nTool: {s['name']}\nDescription: {s['description']}\nArgs:{args_lines}\n"

    formatted_history = "\n".join([
        f"- Step {r['step']}: {r['task']} --> Outcome: {r['result']}"
        for r in previous_results
    ]) if previous_results else "None"

    return f"""You are the CEO Agent executing a plan.

OVERALL EVENT: {overall_event}
CURRENT PLAN: {json.dumps(plan, indent=2)}

PROGRESS SO FAR:
{formatted_history}

CURRENT TASK TO COMPLETE NOW: Step {current_step_idx + 1}: "{plan[current_step_idx]}"

RESPONSE FORMAT — follow exactly:
- To call a tool/sub-agent for this step, output:
  {{"action": "tool_name", "args": {{"arg_name": "value"}}}}
- When this specific step is COMPLETED, output:
  {{"action": "step_complete", "result": "Summary of step execution outcome"}}

Available Tools:
{tools_section}"""


# =====================================================================
# STEP 2: CONFIGURATION & CEO AGENT CLASS
# =====================================================================

@dataclass
class CeoConfig:
    max_tool_retries_per_step: int = 6
    max_plan_steps: int = 15


class CeoAgent(AgentBase):
    def __init__(
            self,
            llm_client: LlmClient,
            executor: ToolExecutor,
            config: CeoConfig = CeoConfig(),
    ) -> None:
        self._llm = llm_client
        self._executor = executor
        self._config = config

    def chat(self, user_input: str) -> str:
        self._executor.clear_traces()
        tool_schemas = self._executor.tool_schemas()

        # ==========================================
        # PHASE 1: PLANNING
        # ==========================================
        self._executor.log_trace(0, "PLAN", None, "CEO generating initial plan...")

        planner_prompt = _build_planner_prompt(tool_schemas, user_input)
        raw_plan = self._llm.invoke([HumanMessage(content=planner_prompt)])
        parsed_plan = _parse_json(raw_plan)

        if not parsed_plan or "plan" not in parsed_plan:
            return "Failed to generate a valid operational plan for the event."

        plan: List[str] = parsed_plan["plan"][:self._config.max_plan_steps]
        self._executor.log_trace(0, "PLAN", None, f"Generated Plan: {json.dumps(plan)}")

        # ==========================================
        # PHASE 2: EXECUTION LOOP
        # ==========================================
        previous_results: List[Dict[str, Any]] = []

        for step_idx, step_task in enumerate(plan):
            self._executor.log_trace(
                step_idx + 1, "EXECUTE_STEP", None, f"Starting Step {step_idx + 1}: {step_task}"
            )

            # Execute step with retries for tool calls
            step_outcome = self._execute_single_step(
                user_event=user_input,
                plan=plan,
                current_step_idx=step_idx,
                previous_results=previous_results,
                tool_schemas=tool_schemas,
            )

            previous_results.append({
                "step": step_idx + 1,
                "task": step_task,
                "result": step_outcome
            })

            self._executor.log_trace(
                step_idx + 1, "STEP_COMPLETE", None, f"Outcome: {step_outcome}"
            )

        # ==========================================
        # PHASE 3: FINAL CEO DECISION / SUMMARY
        # ==========================================
        summary_prompt = f"""You are the CEO. You have completed all planned actions for the event: "{user_input}".

Execution Summary:
{json.dumps(previous_results, indent=2)}

Provide a final decision/summary report to the board and other team agents."""

        final_response = self._llm.invoke([HumanMessage(content=summary_prompt)])
        return final_response

    def _execute_single_step(
            self,
            user_event: str,
            plan: List[str],
            current_step_idx: int,
            previous_results: List[Dict[str, Any]],
            tool_schemas: List[Dict[str, Any]]
    ) -> str:
        """Sub-loop to handle tool calls for a single step in the plan."""

        exec_system_prompt = _build_executor_prompt(
            tool_schemas, user_event, plan, current_step_idx, previous_results
        )
        step_messages = [SystemMessage(content=exec_system_prompt)]

        for attempt in range(1, self._config.max_tool_retries_per_step + 1):
            raw = self._llm.invoke(step_messages)
            step_messages.append(AIMessage(content=raw))

            parsed = _parse_json(raw)
            if not parsed:
                step_messages.append(
                    HumanMessage(content="Invalid JSON format. Respond with a valid single JSON object.")
                )
                continue

            action = parsed.get("action", "")

            # If LLM finishes the current step:
            if action == "step_complete":
                return str(parsed.get("result", "Step finished."))

            # Execute tool call for this step
            tool_name = action
            args = parsed.get("args", {})
            result = self._executor.execute(current_step_idx + 1, tool_name, args)

            if result.ok:
                obs = f"Tool '{tool_name}' output: {result.value}"
            else:
                obs = f"Tool '{tool_name}' failed: {result.error}"

            step_messages.append(HumanMessage(content=obs))

        return "Step finished with maximum retries exceeded."

    def reset(self) -> None:
        self._executor.clear_traces()