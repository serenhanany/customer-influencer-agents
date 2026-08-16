
from services.llm_client import LlmClient
from services.tool_executor import ToolExecutor
from agents.ceo_agent import CeoAgent

def main():
    llm = LlmClient()
    executor = ToolExecutor()

    event = "A major salmon supplier went bankrupt, causing a 30% shortage in raw materials."

    # Compare ReAct vs Plan-and-Solve
    print("--- RUNNING PLAN-AND-SOLVE CEO AGENT ---")
    ceo_agent = CeoAgent(llm_client=llm, executor=executor)
    response = ceo_agent.chat(event)
    print("\n[CEO Final Decision]:\n", response)

if __name__ == "__main__":
    main()