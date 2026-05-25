"""
Example: API Client for CortexFlow.

Demonstrates how to use the CortexFlow REST API from any language/client.
This Python example uses httpx for the actual HTTP calls.
"""

import asyncio
import httpx
import json


class CortexFlowClient:
    """Async client for CortexFlow REST API."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    async def health(self) -> dict:
        """Get platform health status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/v1/health")
            return response.json()

    async def list_agents(self) -> list:
        """List all available agents."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/v1/agents")
            return response.json()

    async def submit_analysis(
        self,
        target: str,
        content: str,
        pipeline: str = "default",
        priority: int = 5,
    ) -> str:
        """Submit a new analysis job. Returns job_id."""
        payload = {
            "type": "codebase",
            "target": target,
            "content": content,
            "pipeline": pipeline,
            "priority": priority,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/analyze",
                json=payload,
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()["job_id"]

    async def get_job_status(self, job_id: str) -> dict:
        """Check status of a submitted job."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/jobs/{job_id}",
                headers=self.headers,
            )
            return response.json()

    async def wait_for_completion(self, job_id: str, timeout: int = 300) -> dict:
        """Poll until job completes or times out."""
        import time
        start = time.time()
        while time.time() - start < timeout:
            status = await self.get_job_status(job_id)
            if status.get("status") in ("completed", "failed", "cancelled"):
                return status
            await asyncio.sleep(2)
        raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")

    async def get_token_usage(self) -> dict:
        """Get token usage analytics."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/tokens",
                headers=self.headers,
            )
            return response.json()


async def main():
    """Example workflow using the API client."""
    client = CortexFlowClient(base_url="http://localhost:8000")

    print("[1] Checking platform health...")
    try:
        health = await client.health()
        print(f"    Status: {health.get('status')}")
        print(f"    Agents loaded: {health.get('agents_loaded')}")
    except Exception as e:
        print(f"    [ERROR] {e}")
        print("    (Start the API server with: cortexflow serve)")
        return

    print("\n[2] Listing available agents...")
    agents = await client.list_agents()
    print(f"    Available agents: {agents.get('total', 0)}")

    print("\n[3] Submitting analysis job...")
    sample_code = "import os\nos.system(input())  # vulnerable!"
    job_id = await client.submit_analysis(
        target="example.py",
        content=sample_code,
        pipeline="code_review",
    )
    print(f"    Job ID: {job_id}")

    print("\n[4] Waiting for completion...")
    result = await client.wait_for_completion(job_id, timeout=120)
    print(f"    Final status: {result.get('status')}")
    print(f"    Progress: {result.get('progress')}%")

    print("\n[5] Token usage...")
    tokens = await client.get_token_usage()
    print(f"    Total tokens: {tokens.get('total_all_time', 0):,}")
    print(f"    Total API calls: {tokens.get('total_api_calls', 0)}")

    return result


if __name__ == "__main__":
    asyncio.run(main())
