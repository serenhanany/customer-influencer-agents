FROM python:3.11-slim
WORKDIR /app

COPY pyproject.toml .
COPY register.py personas.py system_prompt.py ./
COPY personas.yaml workflow.yml ./
COPY guardrails_config ./guardrails_config

# Installing as a real package (not just "pip install -r requirements.txt")
# is required -- this is what registers our customer_agent_decision
# function type with the "nat" CLI's plugin discovery. Without this,
# "nat mcp serve" has no way of knowing register.py exists.
RUN pip install --no-cache-dir .

# personas.py resolves its default path via Path(__file__).parent -- but
# a real (non-editable) pip install copies personas.py into site-packages,
# separate from personas.yaml which only exists here in /app. Point it
# explicitly at the copy that's actually sitting next to this Dockerfile's
# other files, rather than relying on the two staying adjacent by accident.
ENV PERSONAS_CONFIG_PATH=/app/personas.yaml

EXPOSE 8000

# --tool_names restricts what's exposed via MCP to just our own agent
# tool (customer_agent_react). Without it, nat also tries to expose the
# Customer Support tools discovered through our MCP function group,
# which are already served directly by the Customer Support MCP server
# and don't resolve correctly through this path.
CMD ["nat", "mcp", "serve", "--config_file", "workflow.yml", "--host", "0.0.0.0", "--port", "8000", "--tool_names", "customer_agent_react"]