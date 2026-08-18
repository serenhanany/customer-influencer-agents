"""
PLAN:

Make the event generator work in one of two ways:
Either it invokes an llm to generate a crisis feed, or it uses a pre-scripted feed. The latter is useful for demos and tests, while the former is useful for generating new scenarios.

For the llm approach, the generator will go through a fixed loop every 0.25 seconds or so:
5 customer events -> 1 press event -> [repeat]

The main difference between the press and customer events is that the press events are more detailed and grounded (assumed to always be real events). Whereas the customer events are more likely to be emotional or sensationalized.

[optional - USED via 6 stages] There exist a 'guiding hand' for the events that follows a pre scriped narrative. eg: start -> spread -> escalate -> lawsuits -> disease vanishes -> calm     (you could also let an llm create the narrative)

[optional - NOT USED] Use coded statistics to determine what the llm should produce. (prompt engineering)

Inside the generation loop:
- determine if to generate a 'customer' or 'press' event.
- run the statistics to create engineered prompt.
- invoke llm to generate event
- emit said event
"""


import time

from event_broker import Event

from langchain_ollama import ChatOllama

llm = ChatOllama(model="gemma4:e2b", temperature=0.9)
system_msg = ("You are an event generator."
              "Backstory: There is a tuna company called HappyTuna that is goes through a Salmonella outbreak crisis with their product."
              "There are 6 stages to this narrative, and they are as follows:"
              "1. PRE-CRISIS: The company is operating normally, and there are no known issues with the product. The product is being sold and enjoyed without incident."
              "2. START: Faint signs of a problem begin to appear, but the company is unaware of the issue. The product is still being sold and consumed."
              "3. SPREAD: Customers experience recurring issues with the product, and the company begins to receive complaints. The issue is still not fully understood, and the product continues to be sold."
              "4. EXPOSURE: Major bad experiences occur with customers, stores, factory workers, or the company's lab. The issue is now widely known, and the company is under scrutiny."
              "5. CRISIS: The public, authorities, and the company react to the crisis. The company may face lawsuits, recalls, and negative publicity. Whilst Salmonella spreads rapidly decreases in the background due to the company's efforts to contain it."
              "6. RESOLUTION: The Salmonella outbreak is fully contained, and the company takes steps to prevent future incidents. The company may face long-term consequences, but the crisis is resolved.")


# def generate(event: Event ,delay: float = 0.2):
def generate(delay: float = 0.2):
    """Emits the crisis feed through the broker, one event at a time.

    `delay` puts a pause between events so a live demo can be followed at
    reading speed; leave it at 0 for tests.
    """
    # for tag, text in CRISIS_FEED:
    #     event.emit(tag, text)
    #     if delay:
    #         time.sleep(delay)

    ## loop over all stages, in each one do  5 customer events -> 1 press event
    for i in range(6):
        for j in range(5):
            ## build 5 prompts for customer events
            stage = {0: "PRE-CRISIS", 1: "START", 2: "SPREAD", 3: "EXPOSURE", 4: "CRISIS", 5: "RESOLUTION"}
            customer_event_description = "Generate one plausible customer event that happens DURING THE " + stage[i] + " STAGE ONLY. The event should be 3-5 lines long, The event should be written in a way that is consistent with the narrative of the crisis. You MUST NOT invent actions on behalf of HappyTuna."

            messages = [
                ("system", system_msg),
                ("human", str(customer_event_description)),
            ]

            print("\n--- Customer event generation for stage "+ stage[i] + " ----")
            response = llm.invoke(messages)
            print(response.content)

            # emit response content to relevant event listeners
            event.emit("customer", response.content)
            
            if delay:
                time.sleep(delay)


        ## build one prompt for press event
        press_event_description = "Generate one plausible press event that happens DURING THE " + stage[i] + " STAGE ONLY. The event should be 5-15 lines long, The event should be written in a way that is consistent with the narrative of the crisis. You MUST NOT invent actions on behalf of HappyTuna."

        messages = [
            ("system", system_msg),
            ("human", str(customer_event_description)),
        ]

        print("\n--- Press event generation for stage "+ stage[i] + " ----")
        response = llm.invoke(messages)
        print(response.content)

        # emit response content to relevant event listeners
        # event.emit("press", response.content)
        
        if delay:
            time.sleep(delay)


if __name__ == "__main__":
    print("Hello")
    generate()