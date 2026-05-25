"""
Example: Code Review with CortexFlow.

Demonstrates running the code_review workflow programmatically.
"""

import asyncio
from pathlib import Path


async def review_code_sample():
    """Review a Python file for security issues."""
    sample_code = '''
import os
import pickle

DATABASE_PASSWORD = "admin123"  # Hardcoded credential!
API_KEY = "sk-live-abc123def456"  # Hardcoded API key!

def execute_command(user_input):
    """Vulnerable: command injection."""
    os.system(f"echo {user_input}")  # CRITICAL: command injection

def deserialize(data):
    """Vulnerable: insecure deserialization."""
    return pickle.loads(data)  # CRITICAL: insecure deserialization

def render_html(content):
    """Vulnerable: XSS."""
    return f"<div>{content}</div>"  # No escaping

def get_user(user_id):
    """Vulnerable: SQL injection."""
    query = f"SELECT * FROM users WHERE id = {user_id}"  # SQL injection
    return query
'''

    print("=" * 60)
    print("CortexFlow Code Review Example")
    print("=" * 60)
    print()

    # Direct agent calls (bypasses pipeline for demo simplicity)
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from agents.config_extractor import ConfigExtractorAgent
    from agents.vuln_scanner import VulnScannerAgent
    from agents.threat_intel import ThreatIntelAgent
    from agents.base_agent import AgentContext

    context = AgentContext(
        session_id="example_review",
        input_data={"content": sample_code, "type": "codebase"},
        config={},
    )

    # Stage 1: Configuration extraction
    print("[1/3] Extracting configuration & credentials...")
    config_agent = ConfigExtractorAgent()
    config_result = await config_agent.run(context, {})
    print(f"  Found {config_result.output['credentials_count']} credential(s)")
    for cred in config_result.output["credentials_preview"][:3]:
        print(f"    - [{cred.get('severity', '?')}] {cred.get('type')}: {cred.get('value_preview', cred.get('preview'))}")

    # Stage 2: Vulnerability scanning
    print("\n[2/3] Scanning for vulnerabilities...")
    vuln_agent = VulnScannerAgent()
    vuln_result = await vuln_agent.run(context, {})
    print(f"  Found {len(vuln_result.output['findings'])} vulnerability(s)")
    print(f"  Risk score: {vuln_result.output['risk_score']}/10")

    # Stage 3: Threat intelligence
    print("\n[3/3] Mapping to MITRE ATT&CK...")
    intel_agent = ThreatIntelAgent()
    intel_result = await intel_agent.run(
        context,
        {
            "config_extractor": config_result.__dict__,
            "vuln_scanner": vuln_result.__dict__,
        },
    )
    print(f"  Threat level: {intel_result.output['threat_level']}")
    print(f"  Techniques mapped: {len(intel_result.output['mitre_techniques'])}")

    # Token usage
    total_tokens = (
        config_result.prompt_tokens + config_result.completion_tokens +
        vuln_result.prompt_tokens + vuln_result.completion_tokens +
        intel_result.prompt_tokens + intel_result.completion_tokens
    )
    print(f"\n=== Total Tokens: {total_tokens:,} ===")

    return {
        "config_extraction": config_result.output,
        "vulnerabilities": vuln_result.output,
        "threat_intel": intel_result.output,
        "total_tokens": total_tokens,
    }


if __name__ == "__main__":
    asyncio.run(review_code_sample())
