"""
Example: Binary Analysis with CortexFlow.

Demonstrates running the binary_analysis workflow on a sample.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def analyze_binary_sample():
    """Run binary analysis on a synthetic sample."""
    print("=" * 60)
    print("CortexFlow Binary Analysis Example")
    print("=" * 60)

    # Synthetic PE-like sample with injection APIs and C2
    sample = (
        b"MZ\x90\x00" + b"\x00" * 60 + b"\x40\x00\x00\x00"
        b"This program cannot be run in DOS mode\r\r\n$"
        b"\x00" * 64 +
        b"PE\x00\x00\x4c\x01\x05\x00"
        + b"\x00" * 32 +
        # Injection API references
        b"VirtualAllocEx\x00WriteProcessMemory\x00CreateRemoteThread\x00"
        b"NtMapViewOfSection\x00NtUnmapViewOfSection\x00"
        # Anti-debug
        b"IsDebuggerPresent\x00CheckRemoteDebuggerPresent\x00"
        # Anti-VM
        b"VBOX\x00VMWARE\x00QEMU\x00"
        # C2 indicators
        b"https://malicious-c2.example.com/admin/gate?id=12345\x00"
        b"https://backup-c2.evil.org/panel/check\x00"
        b"http://192.168.1.100:4444/cmd\x00"
        # Beacon config
        b"sleep=60\x00jitter=15\x00mutex=Global\\\\CFTest123\x00"
        b"key=AES256_HARDCODED_KEY_DO_NOT_USE\x00"
        # Embedded JSON config
        b'{"server": "evil.com", "port": 1337, "interval": 300, "key": "abc123def456"}\x00'
        # Base64 encoded payload
        b"VGhpcyBpcyBhIHNhbXBsZSBwYXlsb2FkIGZvciB0ZXN0aW5nIHRoZSBhbmFseXNpcyBlbmdpbmU=\x00"
        # MITRE indicators
        b"powershell.exe -enc \x00"
        b"HKEY_LOCAL_MACHINE\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\x00"
    )

    print(f"\nSample size: {len(sample):,} bytes\n")

    from agents.config_extractor import ConfigExtractorAgent
    from agents.network_analyzer import NetworkAnalyzerAgent
    from agents.memory_forensics import MemoryForensicsAgent
    from agents.threat_intel import ThreatIntelAgent
    from agents.base_agent import AgentContext

    context = AgentContext(
        session_id="example_binary",
        input_data={"content": sample, "type": "binary"},
        config={},
    )

    pipeline_results = {}

    # Run each agent
    for stage_name, agent_class in [
        ("config_extractor", ConfigExtractorAgent),
        ("network_analyzer", NetworkAnalyzerAgent),
        ("memory_forensics", MemoryForensicsAgent),
        ("threat_intel", ThreatIntelAgent),
    ]:
        print(f"[{stage_name.upper().replace('_', ' ')}]")
        agent = agent_class()
        result = await agent.run(context, pipeline_results)
        pipeline_results[stage_name] = {
            "output": result.output,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
        }
        if "summary" in result.output:
            for line in result.output["summary"].split("\n"):
                print(f"  {line}")
        print()

    # Aggregate stats
    total_tokens = sum(
        r["prompt_tokens"] + r["completion_tokens"]
        for r in pipeline_results.values()
    )
    print("=" * 60)
    print(f"Total tokens consumed: {total_tokens:,}")
    print(f"Pipeline stages: {len(pipeline_results)}")

    return pipeline_results


if __name__ == "__main__":
    asyncio.run(analyze_binary_sample())
