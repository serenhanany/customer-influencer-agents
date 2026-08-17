"""
Behavioral test for CeoAgent's plan-solve pattern.

Goal: seed one unread email in the CEO's inbox, tell the CEO (via user_input)
that it may have new mail, and check whether the plan-solve loop actually
1) plans to check the inbox, 2) really calls Check_Inbox (not just talks
about it), 3) really reads the seeded email, and 4) takes a sensible
follow-up action.

Why not just run main2.py?
`tools/check_inbox.py` and `tools/send_email.py` go through
`services/mail_client.py`, which makes real HTTP calls to
http://127.0.0.1:8000 (see its docstring). Nothing in this repo currently
serves that API, so those tool calls fail/retry against a dead server.
This script monkeypatches `services.mail_client`'s functions with a small
in-memory mailbox so the CEO agent can be exercised end-to-end (still with
the real Gemini LLM) without needing that server running.

In addition to the email tools, this script now wires in the MCP gateway
(gateway/) so the CEO also has the support/analytics/social tools its role
is allowed to use in roles.yaml. See GatewayToolAdapter and
setup_gateway_tools below. Requires the gateway's own servers reachable
(docker compose up -d social-network customer-support-mcp) -- if they are
not, the run continues with email tools only; see the printed warning.

Run with:  python test_ceo_agent.py
"""
import asyncio
import os
import sys
import threading
from pathlib import Path

from dotenv import load_dotenv

# Windows consoles often default stdout/stderr to a codepage (e.g. cp1252)
# that can't encode emoji -- and the CEO's LLM-drafted social posts routinely
# contain some. Force UTF-8 so a print() here doesn't crash mid-run.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from agents.CEO_Agent import CeoAgent, CeoConfig
from base.tool_base import ToolBase, ToolResult, ToolSchema
from gateway.catalog import build_catalog
from gateway.connection import GatewayConnections
from gateway.registry import load_registry
from gateway.router import Router
from services import mail_client
from services.llm_client import LlmClient, LlmConfig
from services.tool_executor import ToolExecutor
from tools.check_inbox import CheckInbox
from tools.send_email import SendEmail

load_dotenv()

GATEWAY_ROLE = "ceo"
# Keep True until the CEO should actually be allowed to speak in public --
# see README.md "What the CEO can do". Reads and support writes still run for
# real either way; only social.create_post / social.add_comment are held back.
GATEWAY_DRY_RUN = False


# ======================================================================
# Bridges the async MCP gateway into ToolExecutor's synchronous tool.run()
# ======================================================================
class GatewayBridge:
    """Owns the gateway's whole connection lifetime on one background-thread
    event loop, and lets synchronous code (GatewayToolAdapter.run) call into
    it.

    Naive version tried, and why it broke: dispatch every gateway coroutine
    -- __aenter__, connect_all(), each tool call, __aexit__ -- individually
    via `asyncio.run_coroutine_threadsafe(coro, loop)`. That runs each one as
    its OWN asyncio Task, even though they all share the same loop. MCP's
    streamable-http transport opens an anyio task group inside
    GatewayConnections.__aenter__ (one per server) and anyio ties a task
    group's cancel scope to the specific Task that entered it; closing it
    from a different Task -- which is exactly what a separate __aexit__
    submission is -- raises "Attempted to exit cancel scope in a different
    task than it was entered in".

    Fix: __aenter__, connect_all() and __aexit__ all run inside ONE
    coroutine (`_lifecycle`), submitted once, so they share a Task. Between
    connecting and closing, that task blocks on an asyncio.Event; individual
    tool calls are dispatched with their own `run_coroutine_threadsafe` calls
    same as before, which is safe -- a plain `session.call_tool()` doesn't
    open or close the connections' task groups, so it doesn't care which
    Task it runs on.
    """

    def __init__(self, role: str = GATEWAY_ROLE, dry_run: bool = GATEWAY_DRY_RUN) -> None:
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        self._ready = threading.Event()
        self._closed = threading.Event()
        self._setup_error: BaseException | None = None
        self.statuses: list = []
        self.router: Router | None = None

        asyncio.run_coroutine_threadsafe(self._lifecycle(role, dry_run), self.loop)
        self._ready.wait()
        if self._setup_error is not None:
            self._stop_thread()
            raise self._setup_error

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def _lifecycle(self, role: str, dry_run: bool) -> None:
        self._shutdown_event = asyncio.Event()
        try:
            configs = load_registry(profile="local")
            async with GatewayConnections(configs) as connections:
                await connections.connect_all()
                self.statuses = connections.statuses
                catalog = await build_catalog(connections.sessions)
                self.router = Router(connections, catalog, role=role, dry_run=dry_run)
                self._ready.set()
                await self._shutdown_event.wait()
        except Exception as exc:  # noqa: BLE001 -- surfaced to the main thread, not swallowed
            self._setup_error = exc
            self._ready.set()
        finally:
            self._closed.set()

    def call(self, coro):
        """Runs one gateway coroutine (e.g. `router.call_tool(...)`) on the
        background loop and blocks for its result. Safe to call from any
        thread and interleaved freely with other calls -- see class
        docstring for why this is safe but bracketing connect/close was not.
        """
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result()

    def close(self) -> None:
        if self._closed.is_set():
            return
        self.loop.call_soon_threadsafe(self._shutdown_event.set)
        self._closed.wait(timeout=10)
        self._stop_thread()

    def _stop_thread(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)
        self._thread.join(timeout=5)
        self.loop.close()


class GatewayToolAdapter(ToolBase):
    """Wraps one gateway-catalog tool (e.g. "support.patch_ticket") as a
    ToolBase, so ToolExecutor can register and call it exactly like
    Check_Inbox or Send_Email. All the policy/identity/dry-run/audit work
    still happens inside Router.call_tool -- this only adapts sync <-> async.
    """

    def __init__(
        self,
        bridge: GatewayBridge,
        qualified_name: str,
        description: str,
        input_schema: dict,
        is_read: bool,
    ) -> None:
        self._bridge = bridge
        self._qualified_name = qualified_name
        self._is_read = is_read
        self._schema = ToolSchema(
            name=qualified_name,
            description=description or qualified_name,
            parameters=input_schema or {"type": "object", "properties": {}},
        )

    @property
    def schema(self) -> ToolSchema:
        return self._schema

    def run(self, **kwargs) -> ToolResult:
        result = self._bridge.call(self._bridge.router.call_tool(self._qualified_name, kwargs))
        # Reads are safe to retry; writes (support.patch_ticket, social.*)
        # are not -- a retried write could double-fire a side effect.
        if result.ok:
            value = result.data if result.data is not None else result.text
            return ToolResult(value=value, is_idempotent=self._is_read)
        return ToolResult(error=result.error, is_idempotent=self._is_read)


def setup_gateway_tools(
    executor: ToolExecutor, role: str = GATEWAY_ROLE, dry_run: bool = GATEWAY_DRY_RUN
) -> GatewayBridge:
    """Connects to the MCP gateway and registers every tool `role` may call.

    `--profile local` (mirrored here via profile="local"): this script runs
    on the host, not inside the compose network, so it needs the
    host-published ports from docker-compose.yml.

    Never silently loses a server: connect_all() already records a reason
    for each server that did not connect (README: "A silent CEO and one that
    couldn't reach the platform must not look alike"), surfaced below before
    any tool is registered. GatewayBridge cleans up its own thread if
    anything in setup fails (e.g. CatalogError for an unclassified tool) and
    re-raises, so a genuine setup bug is never swallowed.
    """
    bridge = GatewayBridge(role=role, dry_run=dry_run)

    print("=== Gateway connection status ===")
    for status in bridge.statuses:
        if status.connected:
            print(f"  ok      {status.server_id:<10} {status.tool_count} tools")
        else:
            print(f"  SKIPPED {status.server_id:<10} {status.skipped_reason}")

    access_by_name = {entry.qualified_name: entry.access for entry in bridge.router.get_tools()}
    registered = 0
    for spec in bridge.router.get_tools_for_llm():
        qualified_name = spec["name"]
        executor.register(GatewayToolAdapter(
            bridge=bridge,
            qualified_name=qualified_name,
            description=spec["description"],
            input_schema=spec["input_schema"],
            is_read=access_by_name.get(qualified_name) == "read",
        ))
        registered += 1

    print(f"=== Registered {registered} gateway tool(s) for role {role!r} "
          f"(dry_run={dry_run}) ===\n")
    return bridge


def teardown_gateway_tools(bridge: GatewayBridge) -> None:
    bridge.close()


CEO_ADDRESS = "ceo@happytuna.bitrix"
REGULATOR_ADDRESS = "regulator@happytuna.bitrix"
SEED_EMAIL_PATH = Path(__file__).parent / "data" / "email_test.txt"


# ======================================================================
# Fake in-memory mailbox - replaces services.mail_client's HTTP calls
# ======================================================================
class FakeMailbox:
    def __init__(self) -> None:
        self._emails: dict[str, dict] = {}

    def seed(self, from_addr: str, to_addr: str, subject: str, body: str) -> str:
        email_id = f"seed-{len(self._emails) + 1}"
        self._emails[email_id] = {
            "id": email_id,
            "from_addr": from_addr,
            "to_addr": to_addr,
            "subject": subject,
            "body": body,
            "sent_at": "2026-08-16T09:00:00",
            "is_read": False,
        }
        return email_id

    # signature matches mail_client.send_email so it can be swapped in directly
    def send(self, from_addr: str, to_addr: str, subject: str, body: str) -> str:
        return self.seed(from_addr, to_addr, subject, body)

    def unread(self, address: str) -> list[dict]:
        return [e for e in self._emails.values() if e["to_addr"] == address and not e["is_read"]]

    def inbox(self, address: str) -> list[dict]:
        return [e for e in self._emails.values() if e["to_addr"] == address]

    def count_unread(self, address: str) -> int:
        return len(self.unread(address))

    def mark_read(self, email_id: str) -> None:
        if email_id in self._emails:
            self._emails[email_id]["is_read"] = True


def _load_seed_email() -> tuple[str, str]:
    """Parses data/email_test.txt's simple 'Subject : ...' / 'Body : ...' layout."""
    raw = SEED_EMAIL_PATH.read_text(encoding="utf-8")

    subject = "New message"
    for line in raw.splitlines():
        if line.lower().startswith("subject"):
            subject = line.split(":", 1)[1].strip()
            break

    body = raw
    marker = "Body :"
    idx = raw.find(marker)
    if idx != -1:
        body = raw[idx + len(marker):].strip()

    return subject, body


def main() -> None:
    # ------------------------------------------------------------
    # 1) Seed a fake unread email for the CEO, no server required
    # ------------------------------------------------------------
    mailbox = FakeMailbox()
    subject, body = _load_seed_email()
    mailbox.seed(REGULATOR_ADDRESS, CEO_ADDRESS, subject, body)

    mail_client.send_email = mailbox.send
    mail_client.fetch_unread = mailbox.unread
    mail_client.fetch_inbox = mailbox.inbox
    mail_client.count_unread = mailbox.count_unread
    mail_client.mark_read = mailbox.mark_read

    # ------------------------------------------------------------
    # 2) Build the same CEO agent main2.py builds
    # ------------------------------------------------------------
    llm = LlmClient(LlmConfig(
        api_key=os.getenv("GEMINI_API_KEY"),
        model_name=os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash"),
        temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.7")),
    ))

    executor = ToolExecutor(max_retries=3, base_delay=0.2)
    executor.register(SendEmail())
    executor.register(CheckInbox())

    # ------------------------------------------------------------
    # 2b) Wire in the MCP gateway's support/analytics/social tools.
    #     Never fatal: if the gateway's servers aren't up, the run
    #     continues with just the email tools above.
    # ------------------------------------------------------------
    gateway_bridge = None
    try:
        gateway_bridge = setup_gateway_tools(executor)
    except Exception as exc:
        print(f"=== Gateway unavailable, continuing with email tools only: {exc} ===\n")

    ceo = CeoAgent(llm, executor, CeoConfig(max_plan_steps=6, max_tool_retries_per_step=4))

    user_input = (
        f"try post any post in social network"
    )

    print("=== Seeded inbox ===")
    print(f"1 unread email for {CEO_ADDRESS} -> subject: {subject!r}\n")

    # ------------------------------------------------------------
    # 3) Run the plan-solve loop ONCE (not main2.py's infinite loop)
    # ------------------------------------------------------------
    try:
        response = ceo.chat(user_input)
    finally:
        if gateway_bridge is not None:
            teardown_gateway_tools(gateway_bridge)

    # ------------------------------------------------------------
    # 4) Inspect what actually happened, not just what the LLM says
    #    it did. This is the part that tells you the pattern works.
    # ------------------------------------------------------------
    traces = executor.get_traces()
    print("=== Execution trace ===")
    for t in traces:
        print(f"[step {t.step}] {t.phase:15s} {t.tool_name or '':12s} {t.details}")

    checked_inbox_ok = any(
        t.tool_name == "Check_Inbox" and t.details.startswith("OK") for t in traces
    )
    sent_followup_ok = any(
        t.tool_name == "Send_Email" and t.details.startswith("OK") for t in traces
    )
    # The most reliable signal that the email was really read (not just
    # planned-about): CheckInbox marks fetched emails as read via
    # mail_client.mark_read, which flips this flag on our fake mailbox.
    seeded_email_was_read = mailbox.inbox(CEO_ADDRESS)[0]["is_read"]

    print("\n=== Checks ===")
    print(f"Planner produced a plan:        {'YES' if traces else 'NO'}")
    print(f"Check_Inbox called and OK:      {'YES' if checked_inbox_ok else 'NO'}")
    print(f"Seeded email actually read:     {'YES' if seeded_email_was_read else 'NO'}")
    print(f"Agent sent a follow-up email:   {'YES' if sent_followup_ok else 'NO'}")

    print("\n=== Final CEO response ===")
    print(response)


if __name__ == "__main__":
    main()
