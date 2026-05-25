"""Pytest configuration and shared fixtures."""

import pytest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def event_loop():
    """Provide an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_binary_data():
    """Sample bytes representing a fake PE binary."""
    return (
        b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00"
        b"This program cannot be run in DOS mode\r\r\n$\x00\x00\x00\x00\x00\x00\x00"
        b"PE\x00\x00\x4c\x01\x05\x00"
        b"VirtualAllocEx\x00WriteProcessMemory\x00CreateRemoteThread\x00"
        b"https://malicious-c2.example.com/gate?id=12345\x00"
        b"192.168.1.100:4444\x00"
        b"sleep=60\x00jitter=15\x00"
    )


@pytest.fixture
def sample_python_code():
    return """
import os
import subprocess

def vulnerable_function(user_input):
    os.system(f"ls {user_input}")
    eval(user_input)
    pickle.loads(user_input)

API_KEY = "sk-abc123def456ghi789jkl012"
AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
"""


@pytest.fixture
def mock_provider_config():
    from providers.base import ProviderConfig, ProviderType
    return ProviderConfig(
        provider_type=ProviderType.MIMO,
        api_key="test-key",
        base_url="https://test.example.com/v1",
        model="mimo-v2.5",
    )
