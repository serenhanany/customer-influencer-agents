"""Usage example: an always-on listener that handles only the "press" tag.

The pattern is always the same three steps:

    1. create an Event broker,
    2. subscribe a callback to the tag(s) you care about,
    3. stay alive so the callback keeps getting called.

Here the process runs until Ctrl+C, replaying the crisis feed on a loop so
there is always something coming in. In a real deployment step 3 is whatever
keeps your service up (a web server, a queue consumer, a scheduler) and the
events are emitted by that, not by a replay loop.
"""

import time

from event_broker import Event
from event_generator import generate


def press_agent(text: str):
    """Called once per "press" event, with the event text as its only argument.

    This is the seam for the real work: swap the print for a call to your AI
    agent and hand it `text` as the prompt. Emitting is synchronous, so the
    generator waits on this function - keep it quick, or hand the text off to a
    thread or a queue if the agent is slow.
    """
    print(f"[press_agent] received:\n{text}\n")


def main():
    event = Event()

    # Only "press" is subscribed, so this listener sees the Day 3, Day 7 and
    # Day 10 briefings. The "social" and "regulator" events still get emitted,
    # they just have no listener here and pass by untouched. Subscribe to more
    # tags by calling subscribe again with the same callback.
    event.subscribe(press_agent, "press")
    print("Listening on tag 'press'. Ctrl+C to stop.\n")

    try:
        while True:
            # One pass through the 5 scripted events, paced 2s apart so the
            # escalation is readable. delay=0 fires them back to back.
            generate(event, delay=2.0)
            print("--- feed finished, replaying in 5s ---\n")
            time.sleep(5)
    except KeyboardInterrupt:
        # Tidy shutdown: drop the listener so nothing is left registered.
        event.unsubscribe(press_agent)
        print("\nStopped listening.")


if __name__ == "__main__":
    main()
