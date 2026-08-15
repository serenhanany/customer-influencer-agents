"""Scripted crisis feed: a salmonella outbreak traced to a HappyTuna product.

The five events below are ordered by escalation, from a few scattered customer
complaints to a nationwide recall and a lawsuit. Each one is plain text so it
can be handed straight to an AI agent as a prompt.

Tags mark where the news came from, so an agent can subscribe to only the
channels it cares about (e.g. a PR agent on "press", a legal agent on "legal").
"""

import time

from event_broker import Event

# (tag, briefing text) in the order the crisis unfolds.
CRISIS_FEED = [
    (
        "social",
        "Day 1 - Social listening alert.\n"
        "Fourteen posts in the last six hours report nausea, cramps and fever "
        "hours after eating HappyTuna Classic Chunk Light Tuna, 5oz can. "
        "Three posters name the same lot code, HT-4471-B. One post has 22k "
        "shares and a photo of the can. No press coverage yet.",
    ),
    (
        "press",
        "Day 3 - Local news pickup.\n"
        "Two regional outlets are running the story. State health departments "
        "now count 12 confirmed illnesses across 3 states, all interviewed "
        "patients report HappyTuna canned tuna in the week before onset. "
        "A reporter has emailed our press desk asking for comment by 5pm.",
    ),
    (
        "regulator",
        "Day 5 - FDA investigation opened.\n"
        "Lab results identify Salmonella Enteritidis in two opened cans from "
        "lot HT-4471-B, and the strain matches patient isolates. The FDA has "
        "requested production and sanitation records for our Cebu plant and "
        "asked whether we intend a voluntary recall. Case count is now 29 "
        "across 7 states, 4 hospitalizations.",
    ),
    (
        "press",
        "Day 7 - Nationwide recall underway.\n"
        "HappyTuna has issued a voluntary recall of 1.2 million cans spanning "
        "lots HT-4471-B through HT-4478-B. Case count is 47 across 11 states, "
        "9 hospitalizations. The two largest grocery chains have pulled all "
        "HappyTuna SKUs, not just the recalled lots. National broadcast "
        "coverage started this morning; call volume to support is up 900%.",
    ),
    (
        "press",
        "Day 10 - First fatality and litigation.\n"
        "A 71-year-old patient in Ohio has died; the health department links "
        "the death to the outbreak strain. A class action was filed this "
        "morning naming HappyTuna and the Cebu plant operator. Case count "
        "stands at 63. The stock is down 31% since Day 7, a Senate committee "
        "has requested testimony, and our third largest retailer has delisted "
        "the brand indefinitely.",
    ),
]


def generate(event: Event, delay: float = 0.0):
    """Emits the crisis feed through the broker, one event at a time.

    `delay` puts a pause between events so a live demo can be followed at
    reading speed; leave it at 0 for tests.
    """
    for tag, text in CRISIS_FEED:
        event.emit(tag, text)
        if delay:
            time.sleep(delay)
