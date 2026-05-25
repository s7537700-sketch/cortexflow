"""
Example CortexFlow Plugin - Demonstrates the plugin API.

Shows how to:
    1. Subclass Plugin
    2. Register a custom agent
    3. Provide initialization hooks
"""

import logging
import sys
from pathlib import Path

# Make CortexFlow imports work
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.plugin_manager import Plugin
from agents.base_agent import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger("cortexflow.plugins.example")


class ExampleHelloAgent(BaseAgent):
    """A trivial agent that greets the user."""

    def __init__(self, config: dict = None):
        super().__init__("example_hello", config)

    async def run(self, context: AgentContext, pipeline_results: dict) -> AgentResult:
        greeting = self.config.get("greeting", "Hello from plugin")
        target = context.input_data.get("target", "world")
        return AgentResult(
            success=True,
            agent_name=self.name,
            output={
                "message": f"{greeting}, {target}!",
                "summary": "Example plugin executed successfully",
            },
            prompt_tokens=100,
            completion_tokens=50,
        )


class ExamplePlugin(Plugin):
    """Example plugin showcasing the extension API."""

    name = "example_plugin"
    version = "1.0.0"
    description = "Example CortexFlow plugin"
    author = "CortexFlow Team"

    def initialize(self, engine):
        logger.info(f"ExamplePlugin initialized with engine: {engine}")

    def teardown(self):
        logger.info("ExamplePlugin shutting down")

    def get_agents(self):
        return {"example_hello": ExampleHelloAgent}
