"""Tool registry — collects tools and their JSON schemas for Anthropic tool use."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable

TOOLS: dict[str, "ToolSpec"] = {}


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict
    fn: Callable[..., Any]
    skill: str = "general"


def tool(name: str, description: str, input_schema: dict, skill: str = "general"):
    """Decorator: register a function as a tool callable by the executor LLM."""
    def deco(fn):
        TOOLS[name] = ToolSpec(
            name=name,
            description=description,
            input_schema=input_schema,
            fn=fn,
            skill=skill,
        )
        return fn
    return deco


def tool_specs(skills: list[str] | None = None) -> list[dict]:
    """Return tool specs in Anthropic tool-use format. Optionally filter by skill."""
    out = []
    for spec in TOOLS.values():
        if skills and spec.skill not in skills and spec.skill != "general":
            continue
        out.append({
            "name": spec.name,
            "description": spec.description,
            "input_schema": spec.input_schema,
        })
    return out


def call_tool(name: str, args: dict, state) -> Any:
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")
    return TOOLS[name].fn(state=state, **args)
