"""Module 4a — persona renders identity, voice, objectives, and default guardrails."""

from modular_agent.persona import Identity, Objectives, Persona, Voice
from modular_agent.persona.persona import DEFAULT_GUARDRAILS


def test_system_prompt_contains_all_sections():
    persona = Persona(
        identity=Identity(name="Dana", role="loyal customer", backstory="Ten years a fan."),
        voice=Voice(tone="warm", verbosity="concise"),
        objectives=Objectives(items=["Protect your family"]),
    )
    prompt = persona.system_prompt()
    assert "You are Dana, loyal customer." in prompt
    assert "Ten years a fan." in prompt
    assert "Tone: warm" in prompt
    assert "Protect your family" in prompt
    assert "# Guardrails" in prompt


def test_default_guardrails_enforce_no_leakage():
    persona = Persona(identity=Identity(name="X", role="y"))
    prompt = persona.system_prompt()
    # The anti-AI-leakage guardrail must be present by default.
    assert any(rule in prompt for rule in DEFAULT_GUARDRAILS)
    assert "never" in prompt.lower()
