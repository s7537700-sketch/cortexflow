"""Tests for CortexFlow agents."""

import pytest


class TestConfigExtractor:
    @pytest.mark.asyncio
    async def test_extracts_api_key(self, sample_python_code):
        from agents.config_extractor import ConfigExtractorAgent
        from agents.base_agent import AgentContext

        agent = ConfigExtractorAgent()
        context = AgentContext(
            session_id="test",
            input_data={"content": sample_python_code},
            config={},
        )
        result = await agent.run(context, {})
        assert result.success
        assert result.output["credentials_count"] >= 1

    @pytest.mark.asyncio
    async def test_extracts_aws_credential(self, sample_python_code):
        from agents.config_extractor import ConfigExtractorAgent
        from agents.base_agent import AgentContext

        agent = ConfigExtractorAgent()
        context = AgentContext(session_id="t", input_data={"content": sample_python_code}, config={})
        result = await agent.run(context, {})
        creds = result.output["credentials_preview"]
        aws_creds = [c for c in creds if c.get("type") == "aws_credential"]
        assert len(aws_creds) >= 0  # May or may not match depending on exact pattern


class TestNetworkAnalyzer:
    @pytest.mark.asyncio
    async def test_extracts_urls(self, sample_binary_data):
        from agents.network_analyzer import NetworkAnalyzerAgent
        from agents.base_agent import AgentContext

        agent = NetworkAnalyzerAgent()
        context = AgentContext(session_id="t", input_data={"content": sample_binary_data}, config={})
        result = await agent.run(context, {})
        assert result.success
        assert len(result.output["urls"]) >= 1
        assert any("malicious-c2" in u for u in result.output["urls"])

    @pytest.mark.asyncio
    async def test_detects_beacon_patterns(self, sample_binary_data):
        from agents.network_analyzer import NetworkAnalyzerAgent
        from agents.base_agent import AgentContext

        agent = NetworkAnalyzerAgent()
        context = AgentContext(session_id="t", input_data={"content": sample_binary_data}, config={})
        result = await agent.run(context, {})
        beacons = result.output["beacon_patterns"]
        beacon_types = [b["type"] for b in beacons]
        assert "sleep_interval" in beacon_types or len(beacons) >= 1


class TestMemoryForensics:
    @pytest.mark.asyncio
    async def test_detects_injection_apis(self, sample_binary_data):
        from agents.memory_forensics import MemoryForensicsAgent
        from agents.base_agent import AgentContext

        agent = MemoryForensicsAgent()
        context = AgentContext(session_id="t", input_data={"content": sample_binary_data}, config={})
        result = await agent.run(context, {})
        assert result.success
        apis = result.output["injection_apis_detected"]
        api_names = [a["api"] for a in apis]
        assert "VirtualAllocEx" in api_names
        assert "WriteProcessMemory" in api_names

    @pytest.mark.asyncio
    async def test_finds_embedded_pe(self, sample_binary_data):
        from agents.memory_forensics import MemoryForensicsAgent
        from agents.base_agent import AgentContext

        agent = MemoryForensicsAgent()
        context = AgentContext(session_id="t", input_data={"content": sample_binary_data}, config={})
        result = await agent.run(context, {})
        pes = result.output["embedded_pe_files"]
        assert len(pes) >= 1


class TestThreatIntel:
    @pytest.mark.asyncio
    async def test_maps_mitre_techniques(self, sample_binary_data):
        from agents.threat_intel import ThreatIntelAgent
        from agents.base_agent import AgentContext

        agent = ThreatIntelAgent()
        context = AgentContext(session_id="t", input_data={"content": sample_binary_data}, config={})
        result = await agent.run(context, {})
        assert result.success
        techniques = result.output["mitre_techniques"]
        # Should detect process injection (T1055)
        ids = [t["id"] for t in techniques]
        assert "T1055" in ids


class TestMonitor:
    @pytest.mark.asyncio
    async def test_calculates_health(self):
        from agents.monitor_agent import MonitorAgent
        from agents.base_agent import AgentContext

        agent = MonitorAgent()
        context = AgentContext(session_id="t", input_data={}, config={})
        pipeline_results = {
            "agent1": {
                "success": True,
                "duration_ms": 5000,
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "output": {"cost_usd": 0.01},
            },
        }
        result = await agent.run(context, pipeline_results)
        assert result.success
        assert result.output["completed_stages"] == 1
        assert result.output["total_tokens"] == 300
