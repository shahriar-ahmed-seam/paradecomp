"""Unit tests for LLM provider adapters and LangChain tool bridge."""

import asyncio

from paradecomp.adapters.providers import (
    LangChainToolAdapter,
    MockLLMClient,
    OllamaAdapter,
    OpenAIAdapter,
)


def test_mock_llm_client():
    async def _test():
        mock = MockLLMClient(default_response="Custom answer.")
        res = await mock.generate("What is 0.55 High-NA EUV lithography?")
        assert "Custom answer." in res
        assert mock.calls_count == 1
        assert mock.total_tokens > 0

    asyncio.run(_test())


def test_langchain_tool_adapter():
    async def _test():
        tool = LangChainToolAdapter()
        assert tool.name == "paradecomp_deep_research"
        payload = await tool.arun(query="Global Semiconductor Subsidies", num_facets=3)
        assert payload["total_sources"] == 60
        assert "synthesis" in payload
        assert payload["verification"] is not None

    asyncio.run(_test())


def test_adapter_initialization():
    oai = OpenAIAdapter(api_key="sk-test", model="gpt-4o")
    assert oai.model == "gpt-4o"
    ollama = OllamaAdapter(model="deepseek-coder")
    assert ollama.model == "deepseek-coder"
