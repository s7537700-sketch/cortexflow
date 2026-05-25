"""
Base Agent — Abstract interface for all CortexFlow agents.

Defines the contract that every agent must implement, with built-in
token tracking, timeout handling, and structured output validation.
"""

import logging
import time
import json
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from abc import ABC, abstractmethod

logger = logging.getLogger("cortexflow.agent")


@dataclass
class AgentContext:
    """Execution context passed through the agent pipeline."""
    session_id: str
    input_data: dict
    config: dict
    pipeline_results: dict = field(default_factory=dict)
    start_time: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentResult:
    """Standardized output from any agent execution."""
    success: bool
    agent_name: str
    output: dict
    prompt_tokens: int = 0
    completion_tokens: int = 0
    duration_ms: int = 0
    error: Optional[str] = None
    warnings: list = field(default_factory=list)


class BaseAgent(ABC):
    """Abstract base agent with common infrastructure."""

    def __init__(self, name: str, config: Optional[dict] = None):
        self.name = name
        self.config = config or {}
        self.version = "1.0.0"
        self.total_calls = 0

    @abstractmethod
    async def run(self, context: AgentContext,
                  pipeline_results: dict) -> AgentResult:
        """Execute the agent's core logic.

        Args:
            context: Execution context with session and config data.
            pipeline_results: Results from previously executed agents.

        Returns:
            AgentResult with structured output and token counts.
        """
        pass

    async def execute(self, context: AgentContext,
                      pipeline_results: dict) -> AgentResult:
        """Execute with timing, error handling, and logging wrapper."""
        start = time.time()
        self.total_calls += 1

        logger.info(f"Agent {self.name} starting (call #{self.total_calls})")
        try:
            result = await self.run(context, pipeline_results)
            result.duration_ms = int((time.time() - start) * 1000)

            if result.success:
                logger.info(
                    f"Agent {self.name} completed in {result.duration_ms}ms "
                    f"(tokens: {result.prompt_tokens}+{result.completion_tokens})"
                )
            else:
                logger.warning(
                    f"Agent {self.name} returned failure: {result.error}")

            return result

        except Exception as e:
            duration = int((time.time() - start) * 1000)
            logger.error(f"Agent {self.name} crashed after {duration}ms: {e}")
            return AgentResult(
                success=False,
                agent_name=self.name,
                output={},
                error=str(e),
                duration_ms=duration,
            )

    def estimate_tokens(self, text: str) -> int:
        """Rough token count estimate (4 chars per token)."""
        return len(text) // 4

    def truncate(self, text: str, max_chars: int = 100000) -> str:
        """Truncate text to fit context window."""
        if len(text) > max_chars:
            return text[:max_chars] + "\n\n[... truncated ...]"
        return text

    def get_info(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "class": self.__class__.__name__,
            "total_calls": self.total_calls,
        }
