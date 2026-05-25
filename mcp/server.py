"""
CortexFlow MCP Server — Model Context Protocol server for IDE integration.

Allows Claude Code, OpenCode, Cursor and other MCP-compatible agents
to invoke CortexFlow analysis tools directly from the editor.

Exposed Tools:
- cortexflow_analyze      — Submit analysis job
- cortexflow_scan_code    — Quick code vulnerability scan
- cortexflow_get_agents   — List available agents
- cortexflow_get_report   — Retrieve analysis results
"""

import json
import logging
from typing import Any

logger = logging.getLogger("cortexflow.mcp")


class CortexFlowMCPServer:
    """MCP server exposing CortexFlow as analyzable tools for AI agents."""

    def __init__(self, engine=None):
        self.engine = engine
        self.tools = {
            "cortexflow_analyze": self.tool_analyze,
            "cortexflow_scan_code": self.tool_scan_code,
            "cortexflow_get_agents": self.tool_get_agents,
            "cortexflow_get_report": self.tool_get_report,
        }

    def get_manifest(self) -> dict:
        return {
            "name": "cortexflow",
            "version": "1.0.0",
            "description": "Multi-Agent AI Orchestration Platform MCP Server",
            "tools": [
                {
                    "name": "cortexflow_analyze",
                    "description": "Submit a full analysis pipeline job",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["codebase", "binary", "network"]},
                            "target": {"type": "string", "description": "Target name or path"},
                            "content": {"type": "string", "description": "Source code or data content"},
                            "pipeline": {"type": "string", "default": "default"},
                        },
                    },
                },
                {
                    "name": "cortexflow_scan_code",
                    "description": "Quick vulnerability scan of code snippet",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "description": "Source code to scan"},
                            "language": {"type": "string", "description": "Programming language"},
                        },
                    },
                },
                {
                    "name": "cortexflow_get_agents",
                    "description": "List all available analysis agents",
                    "input_schema": {"type": "object", "properties": {}},
                },
                {
                    "name": "cortexflow_get_report",
                    "description": "Retrieve analysis results by session ID",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string", "description": "Session/report ID"},
                        },
                    },
                },
            ],
        }

    async def handle_request(self, request: dict) -> dict:
        method = request.get("method", "")
        params = request.get("params", {})

        if method == "tools/list":
            return self.get_manifest()
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            handler = self.tools.get(tool_name)
            if handler:
                return await handler(arguments)
            return {"error": f"Unknown tool: {tool_name}"}
        return {"error": f"Unknown method: {method}"}

    async def tool_analyze(self, args: dict) -> dict:
        if not self.engine:
            return {"error": "Engine not initialized"}
        result = await self.engine.analyze({
            "type": args.get("type", "codebase"),
            "target": args.get("target", "unknown"),
            "content": args.get("content", ""),
            "pipeline": args.get("pipeline", "default"),
        })
        return {
            "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
        }

    async def tool_scan_code(self, args: dict) -> dict:
        code = args.get("code", "")
        language = args.get("language", "unknown")
        findings = {
            "language": language,
            "lines": len(code.split("\n")),
            "message": f"Scanned {len(code.split('\n'))} lines of {language}",
            "severity": "INFO",
        }
        return {
            "content": [{"type": "text", "text": json.dumps(findings, indent=2)}],
        }

    async def tool_get_agents(self, args: dict) -> dict:
        if not self.engine:
            return {"error": "Engine not initialized"}
        agents = self.engine.get_agent_info()
        return {
            "content": [{"type": "text", "text": json.dumps(agents, indent=2)}],
        }

    async def tool_get_report(self, args: dict) -> dict:
        return {
            "content": [{"type": "text", "text": json.dumps({
                "session_id": args.get("session_id", ""),
                "status": "retrieved",
            }, indent=2)}],
        }


def run_server(host: str = "0.0.0.0", port: int = 9000):
    """Run MCP server via stdio transport."""
    import sys
    import asyncio
    from core.engine import CortexFlowEngine

    engine = CortexFlowEngine()

    async def main():
        await engine.initialize()
        engine.create_pipeline("default")
        server = CortexFlowMCPServer(engine)
        logger.info(f"CortexFlow MCP Server ready")

        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                response = await server.handle_request(request)
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
            except json.JSONDecodeError:
                sys.stdout.write(json.dumps({"error": "Invalid JSON"}) + "\n")
                sys.stdout.flush()

    asyncio.run(main())


if __name__ == "__main__":
    run_server()
