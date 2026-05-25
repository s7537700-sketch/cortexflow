"""
CortexFlow Agents - 10 specialized AI agents for security analysis orchestration.

Agent Catalog:
  Orchestrator       - Pipeline planner and coordinator
  CodeAnalyzer       - Static code analysis and vulnerability patterns
  VulnScanner        - Automated vulnerability discovery
  ExploitSuggester   - Exploit strategy and payload recommendations
  ReportGenerator    - Structured report synthesis
  ConfigExtractor    - Configuration and sensitive data extraction
  MonitorAgent       - Real-time progress and health monitoring
  NetworkAnalyzer    - Network indicator extraction & protocol analysis
  MemoryForensics    - Process injection & memory artifact detection
  ThreatIntel        - MITRE ATT&CK mapping & malware fingerprinting
"""

from .base_agent import BaseAgent, AgentContext, AgentResult
from .orchestrator import OrchestratorAgent
from .code_analyzer import CodeAnalyzerAgent
from .vuln_scanner import VulnScannerAgent
from .exploit_suggester import ExploitSuggesterAgent
from .report_generator import ReportGeneratorAgent
from .config_extractor import ConfigExtractorAgent
from .monitor_agent import MonitorAgent
from .network_analyzer import NetworkAnalyzerAgent
from .memory_forensics import MemoryForensicsAgent
from .threat_intel import ThreatIntelAgent

__all__ = [
    "BaseAgent",
    "AgentContext",
    "AgentResult",
    "OrchestratorAgent",
    "CodeAnalyzerAgent",
    "VulnScannerAgent",
    "ExploitSuggesterAgent",
    "ReportGeneratorAgent",
    "ConfigExtractorAgent",
    "MonitorAgent",
    "NetworkAnalyzerAgent",
    "MemoryForensicsAgent",
    "ThreatIntelAgent",
]
