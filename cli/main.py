"""
CortexFlow CLI - Main entry point with typer.

Usage:
    cortexflow analyze --target file.exe --pipeline binary
    cortexflow workflow run security_audit --input ./code
    cortexflow agents list
    cortexflow tokens stats --since 30d
    cortexflow serve --port 8000
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional

try:
    import typer
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    HAS_TYPER = True
except ImportError:
    HAS_TYPER = False
    typer = None
    Console = None

logger = logging.getLogger("cortexflow.cli")


if HAS_TYPER:
    cli = typer.Typer(
        name="cortexflow",
        help="🧠 CortexFlow - Multi-Agent AI Orchestration Platform",
        add_completion=False,
        rich_markup_mode="rich",
    )

    agents_cmd = typer.Typer(name="agents", help="Manage agents")
    workflows_cmd = typer.Typer(name="workflow", help="Workflow operations")
    tokens_cmd = typer.Typer(name="tokens", help="Token analytics")

    cli.add_typer(agents_cmd, name="agents")
    cli.add_typer(workflows_cmd, name="workflow")
    cli.add_typer(tokens_cmd, name="tokens")

    console = Console()

    @cli.command()
    def analyze(
        target: str = typer.Option(..., "--target", "-t", help="Target file or directory"),
        pipeline: str = typer.Option("default", "--pipeline", "-p", help="Pipeline type"),
        output: Optional[str] = typer.Option(None, "--output", "-o", help="Output JSON file"),
        provider: str = typer.Option("anthropic", "--provider", help="LLM provider"),
        model: Optional[str] = typer.Option(None, "--model", help="Specific model"),
        format: str = typer.Option("text", "--format", "-f", help="Output: text, json, markdown"),
    ):
        """Run analysis pipeline on a target."""
        console.print(f"[bold cyan]🧠 CortexFlow Analysis[/bold cyan]")
        console.print(f"Target: [yellow]{target}[/yellow]")
        console.print(f"Pipeline: {pipeline}")
        console.print(f"Provider: {provider}")
        console.print()

        target_path = Path(target)
        if not target_path.exists():
            console.print(f"[red]Error:[/red] Target not found: {target}")
            raise typer.Exit(1)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Running analysis...", total=None)
            result = asyncio.run(_run_analysis(target, pipeline, provider, model))

        if format == "json":
            output_text = json.dumps(result, indent=2, default=str)
        elif format == "markdown":
            output_text = _format_markdown(result)
        else:
            output_text = _format_text(result)

        if output:
            Path(output).write_text(output_text, encoding="utf-8")
            console.print(f"[green]✓[/green] Saved to {output}")
        else:
            console.print(output_text)

    @agents_cmd.command("list")
    def agents_list():
        """List all available agents."""
        from agents import (
            OrchestratorAgent, CodeAnalyzerAgent, VulnScannerAgent,
            ExploitSuggesterAgent, ReportGeneratorAgent, ConfigExtractorAgent,
            MonitorAgent, NetworkAnalyzerAgent, MemoryForensicsAgent, ThreatIntelAgent,
        )
        agents = [
            ("Orchestrator", "Pipeline planner and coordinator"),
            ("CodeAnalyzer", "Static code analysis"),
            ("VulnScanner", "Vulnerability discovery"),
            ("ExploitSuggester", "Exploit strategy"),
            ("ReportGenerator", "Report synthesis & YARA"),
            ("ConfigExtractor", "Configuration & credential extraction"),
            ("Monitor", "Health & resource monitoring"),
            ("NetworkAnalyzer", "Network IOC extraction"),
            ("MemoryForensics", "Memory injection detection"),
            ("ThreatIntel", "MITRE ATT&CK mapping"),
        ]
        table = Table(title="🤖 CortexFlow Agents")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        for name, desc in agents:
            table.add_row(name, desc)
        console.print(table)
        console.print(f"\n[bold]{len(agents)} agents available[/bold]")

    @workflows_cmd.command("list")
    def workflows_list():
        """List available workflow templates."""
        workflow_dir = Path(__file__).parent.parent / "workflows"
        if not workflow_dir.exists():
            console.print("[yellow]No workflows directory found[/yellow]")
            return
        templates = list(workflow_dir.glob("*.yaml"))
        if not templates:
            console.print("[yellow]No workflows defined[/yellow]")
            return
        table = Table(title="📋 Workflow Templates")
        table.add_column("Name", style="cyan")
        table.add_column("File")
        for tpl in templates:
            table.add_row(tpl.stem, str(tpl.name))
        console.print(table)

    @workflows_cmd.command("run")
    def workflow_run(
        name: str = typer.Argument(..., help="Workflow name"),
        input: str = typer.Option(..., "--input", "-i", help="Input target"),
    ):
        """Execute a workflow template."""
        console.print(f"[bold]Running workflow:[/bold] {name}")
        workflow_path = Path(__file__).parent.parent / "workflows" / f"{name}.yaml"
        if not workflow_path.exists():
            console.print(f"[red]Workflow not found:[/red] {name}")
            raise typer.Exit(1)
        result = asyncio.run(_run_workflow(workflow_path, input))
        console.print(f"[green]✓[/green] Workflow completed")
        console.print(json.dumps(result, indent=2, default=str))

    @tokens_cmd.command("stats")
    def tokens_stats(
        since: str = typer.Option("7d", "--since", help="Time range (e.g. 7d, 30d, 1m)"),
    ):
        """Show token usage statistics."""
        console.print(f"[bold]📊 Token Statistics[/bold] (since {since})")
        try:
            from storage import get_db, TokenUsageRepository
            from datetime import datetime, timedelta

            now = datetime.utcnow()
            if since.endswith("d"):
                start = now - timedelta(days=int(since[:-1]))
            elif since.endswith("h"):
                start = now - timedelta(hours=int(since[:-1]))
            else:
                start = now - timedelta(days=7)

            with get_db().session() as db_sess:
                repo = TokenUsageRepository(db_sess)
                by_provider = repo.aggregate_by_provider(start)

            table = Table(title="By Provider")
            table.add_column("Provider", style="cyan")
            table.add_column("Calls", justify="right")
            table.add_column("Tokens", justify="right")
            table.add_column("Cost USD", justify="right", style="yellow")
            for prov, stats in by_provider.items():
                table.add_row(
                    prov,
                    str(stats["calls"]),
                    f"{stats['prompt_tokens'] + stats['completion_tokens']:,}",
                    f"${stats['total_cost_usd']:.4f}",
                )
            console.print(table)
        except Exception as e:
            console.print(f"[yellow]No data: {e}[/yellow]")

    @cli.command()
    def serve(
        host: str = typer.Option("0.0.0.0", "--host", help="API server host"),
        port: int = typer.Option(8000, "--port", help="API server port"),
        reload: bool = typer.Option(False, "--reload", help="Enable auto-reload"),
    ):
        """Start the CortexFlow API server."""
        console.print(f"[bold green]🚀 Starting CortexFlow API[/bold green]")
        console.print(f"   http://{host}:{port}")
        try:
            import uvicorn
            uvicorn.run("api.server:app", host=host, port=port, reload=reload)
        except ImportError:
            console.print("[red]uvicorn not installed[/red]")
            raise typer.Exit(1)

    @cli.command()
    def init(
        path: str = typer.Option(".", "--path", help="Project initialization path"),
    ):
        """Initialize a new CortexFlow project."""
        target = Path(path)
        target.mkdir(parents=True, exist_ok=True)
        config = target / "cortexflow.yaml"
        if config.exists():
            console.print(f"[yellow]Already initialized at {target}[/yellow]")
            raise typer.Exit(0)
        config.write_text(
            "# CortexFlow project configuration\n"
            "name: my-project\n"
            "version: 1.0.0\n"
            "default_pipeline: default\n"
            "providers:\n"
            "  - type: anthropic\n"
            "    model: claude-sonnet-4.5\n",
            encoding="utf-8",
        )
        console.print(f"[green]✓[/green] Initialized at {target / 'cortexflow.yaml'}")

    @cli.command()
    def version():
        """Show CortexFlow version."""
        console.print("[bold cyan]CortexFlow[/bold cyan] v2.0.0")
        console.print("Multi-Agent AI Orchestration Platform")


async def _run_analysis(target: str, pipeline: str, provider: str, model: Optional[str]) -> dict:
    """Run analysis via CortexFlowEngine."""
    from core.engine import CortexFlowEngine
    import os

    target_path = Path(target)
    content = ""
    if target_path.is_file():
        try:
            content = target_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            content = str(target_path.read_bytes()[:50000])

    # Build provider config from env
    provider_cfg = None
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("MIMO_API_KEY")
    if api_key:
        provider_cfg = {
            "type": provider,
            "api_key": api_key,
            "base_url": os.environ.get(
                "ANTHROPIC_BASE_URL") or os.environ.get("MIMO_BASE_URL"),
            "model": model or os.environ.get("CORTEXFLOW_MODEL", ""),
        }

    engine = CortexFlowEngine(config={"provider": provider_cfg})
    result = await engine.analyze(
        input_data={
            "target": target,
            "content": content,
            "type": pipeline,
        },
        pipeline_name=pipeline,
    )
    return result


async def _run_workflow(workflow_path: Path, input_target: str) -> dict:
    """Execute a YAML workflow via CortexFlowEngine."""
    import re
    import yaml
    from core.engine import CortexFlowEngine

    workflow = yaml.safe_load(workflow_path.read_text())

    # Mapping: YAML class names → engine agent dict keys
    _AGENT_MAP = {
        "OrchestratorAgent": "orchestrator",
        "Orchestrator": "orchestrator",
        "CodeAnalyzerAgent": "code_analyzer",
        "CodeAnalyzer": "code_analyzer",
        "VulnScannerAgent": "vuln_scanner",
        "VulnScanner": "vuln_scanner",
        "ExploitSuggesterAgent": "exploit_suggester",
        "ExploitSuggester": "exploit_suggester",
        "ReportGeneratorAgent": "report_generator",
        "ReportGenerator": "report_generator",
        "ConfigExtractorAgent": "config_extractor",
        "ConfigExtractor": "config_extractor",
        "MemoryForensicsAgent": "memory_forensics",
        "MemoryForensics": "memory_forensics",
        "MonitorAgent": "monitor_agent",
        "Monitor": "monitor_agent",
        "NetworkAnalyzerAgent": "network_analyzer",
        "NetworkAnalyzer": "network_analyzer",
        "ThreatIntelAgent": "threat_intel",
        "ThreatIntel": "threat_intel",
    }

    raw_names = [s.get("agent", s.get("name")) for s in workflow.get("stages", [])]
    agent_names = []
    for n in raw_names:
        if n in _AGENT_MAP:
            agent_names.append(_AGENT_MAP[n])
        else:
            # Fallback: CamelCase → snake_case
            s = re.sub(r'Agent$', '', n)
            s = re.sub(r'(?<!^)(?=[A-Z])', '_', s)
            agent_names.append(s.lower())
    pipeline_name = workflow.get("name", "custom")

    engine = CortexFlowEngine()
    await engine.initialize()

    result = await engine.analyze(
        input_data={
            "target": input_target,
            "content": "",
            "type": pipeline_name,
        },
        pipeline_name=pipeline_name,
        agent_names=agent_names,
    )
    return result


def _format_text(result: dict) -> str:
    lines = ["[bold]CortexFlow Analysis Result[/bold]\n"]
    for k, v in result.items():
        lines.append(f"  [cyan]{k}:[/cyan] {v}")
    return "\n".join(lines)


def _format_markdown(result: dict) -> str:
    lines = ["# CortexFlow Analysis Result\n"]
    for k, v in result.items():
        lines.append(f"- **{k}**: {v}")
    return "\n".join(lines)


def run_cli():
    """CLI entry point."""
    if not HAS_TYPER:
        print("Error: typer and rich are required. Install: pip install typer rich")
        sys.exit(1)
    cli()


if __name__ == "__main__":
    run_cli()
