"""Ecosystem provider adapters for OpenAI, Anthropic, Gemini, Ollama, and LangChain."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, Protocol

import httpx

from paradecomp.core.models import AggregatedOutput
from paradecomp.workloads.deep_research import DeepResearchEngine, ResearchFacet


class LLMProvider(Protocol):
    """Protocol defining the standard asynchronous LLM provider interface."""

    async def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate response text for given prompt."""
        ...


class MockLLMClient:
    """Deterministic mock client for offline testing and benchmarking."""

    def __init__(self, default_response: str = "Mock synthesis payload.") -> None:
        self.default_response = default_response
        self.calls_count = 0
        self.total_tokens = 0

    async def generate(self, prompt: str, system: Optional[str] = None) -> str:
        await asyncio.sleep(0.01)
        self.calls_count += 1
        tokens = len(prompt.split()) + 20
        self.total_tokens += tokens
        return f"{self.default_response} [Prompt: {prompt[:30]}...]"


class OpenAIAdapter:
    """REST adapter for OpenAI compatible endpoints."""

    def __init__(
        self,
        api_key: str = "mock-key",
        model: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def generate(self, prompt: str, system: Optional[str] = None) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {"model": self.model, "messages": messages, "temperature": 0.2}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            return f"OpenAI error {resp.status_code}: {resp.text}"


class AnthropicAdapter:
    """REST adapter for Anthropic Claude models."""

    def __init__(
        self,
        api_key: str = "mock-key",
        model: str = "claude-3-5-sonnet-20241022",
        base_url: str = "https://api.anthropic.com/v1",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def generate(self, prompt: str, system: Optional[str] = None) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["content"][0]["text"]
            return f"Anthropic error {resp.status_code}: {resp.text}"


class GeminiAdapter:
    """REST adapter for Google Gemini models via Gemini API."""

    def __init__(
        self,
        api_key: str = "mock-key",
        model: str = "gemini-1.5-pro",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def generate(self, prompt: str, system: Optional[str] = None) -> str:
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        contents = [{"parts": [{"text": prompt}]}]
        payload: Dict[str, Any] = {"contents": contents}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            return f"Gemini error {resp.status_code}: {resp.text}"


class OllamaAdapter:
    """REST adapter for local Ollama instances."""

    def __init__(
        self,
        model: str = "llama3:latest",
        base_url: str = "http://localhost:11434",
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def generate(self, prompt: str, system: Optional[str] = None) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            if resp.status_code == 200:
                return resp.json().get("response", "")
            return f"Ollama error {resp.status_code}: {resp.text}"


class LangChainToolAdapter:
    """Adapter exposing ParaDecomp high-breadth research as a LangChain/LlamaIndex tool."""

    name: str = "paradecomp_deep_research"
    description: str = (
        "High-breadth multi-agent research tool. Decomposes queries into orthogonal "
        "facets, executing N concurrent sub-agents to gather 300+ sources with critic verification."
    )

    def __init__(self, engine: Optional[DeepResearchEngine] = None) -> None:
        self.engine = engine or DeepResearchEngine()

    async def arun(self, query: str, num_facets: int = 5) -> Dict[str, Any]:
        """Async entrypoint for LangChain tool execution."""
        facets = [
            ResearchFacet(
                facet_id=f"f_{i}",
                title=f"Facet {i} for {query[:20]}",
                query=f"{query} sub-aspect {i}",
                expected_sources=20,
            )
            for i in range(num_facets)
        ]
        result: AggregatedOutput = await self.engine.run(
            objective_title=query,
            facets=facets,
        )
        return {
            "task_id": result.task_id,
            "strategy": result.strategy_used.value,
            "total_sources": result.total_sources_gathered,
            "duration_ms": result.wall_clock_duration_ms,
            "coverage_per_second": result.coverage_per_second,
            "synthesis": result.synthesized_content,
            "verification": (result.verification.model_dump() if result.verification else None),
        }
