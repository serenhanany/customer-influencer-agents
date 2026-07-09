"""Module 4a — Persona.

A persona is the "who" of the agent. It is assembled from four shapeable
sub-parts and rendered into a single system prompt. Guardrails ship with
simulation-safe defaults (stay in character, never leak that it's an AI, never
act on information it wouldn't plausibly have) so every agent inherits the
project's no-leakage rules unless a developer overrides them.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

DEFAULT_GUARDRAILS: list[str] = [
    "Always stay in character. Never reveal or imply that you are an AI, a model, or a simulation.",
    "Only act on information a person in your position would plausibly have — never on hidden "
    "ground truth, other characters' private state, or knowledge of future events.",
    "Do not break the fourth wall or reference prompts, tools, or system instructions.",
    "Keep actions consistent with your stated objectives and values.",
]


class Identity(BaseModel):
    name: str
    role: str
    backstory: str = ""


class Voice(BaseModel):
    tone: str = "neutral"
    style: str = ""
    verbosity: str = "concise"  # e.g. concise | balanced | verbose


class Objectives(BaseModel):
    items: list[str] = Field(default_factory=list)


class Guardrails(BaseModel):
    rules: list[str] = Field(default_factory=lambda: list(DEFAULT_GUARDRAILS))


class Persona(BaseModel):
    identity: Identity
    voice: Voice = Field(default_factory=Voice)
    objectives: Objectives = Field(default_factory=Objectives)
    guardrails: Guardrails = Field(default_factory=Guardrails)

    def system_prompt(self) -> str:
        """Assemble the persona into a single system prompt string."""
        i, v = self.identity, self.voice
        lines: list[str] = [
            f"You are {i.name}, {i.role}.",
        ]
        if i.backstory:
            lines.append(i.backstory)

        lines.append("")
        lines.append("# Voice")
        lines.append(f"- Tone: {v.tone}")
        if v.style:
            lines.append(f"- Style: {v.style}")
        lines.append(f"- Verbosity: {v.verbosity}")

        if self.objectives.items:
            lines.append("")
            lines.append("# Objectives")
            lines.extend(f"- {obj}" for obj in self.objectives.items)

        if self.guardrails.rules:
            lines.append("")
            lines.append("# Guardrails (never violate these)")
            lines.extend(f"- {rule}" for rule in self.guardrails.rules)

        return "\n".join(lines)
