"""Base skill interface for AutoHySeeker."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class SkillResult(BaseModel):
    success: bool
    data: Any
    message: str
    artifacts: list[str]

    model_config = {"arbitrary_types_allowed": True}


class BaseSkill(ABC):
    """Abstract base class for all AutoHySeeker skills."""

    #: Human-readable skill name
    name: str = ""
    #: Short description of what the skill does
    description: str = ""
    #: Names of tool functions this skill requires
    required_tools: list[str] = []

    @abstractmethod
    async def execute(self, **kwargs: Any) -> SkillResult:
        """Run the skill and return a SkillResult."""
        ...

    def validate_inputs(self, **kwargs: Any) -> bool:
        """Validate input keyword arguments against the skill's schema.

        Returns True if valid, False otherwise.  Override for custom logic.
        """
        schema = self.get_schema()
        required = schema.get("required", [])
        return all(k in kwargs for k in required)

    def get_schema(self) -> dict:
        """Return a JSON Schema dict describing this skill's inputs."""
        return {
            "type": "object",
            "title": self.name,
            "description": self.description,
            "properties": {},
            "required": [],
        }
