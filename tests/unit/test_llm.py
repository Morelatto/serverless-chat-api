"""
Unit tests for LLM providers and factory.
Tests Gemini, OpenRouter, Mock providers and fallback logic.
"""
import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from src.shared.llm import (
    LLMProviderFactory,
    GeminiProvider,
    OpenRouterProvider,
    MockProvider
)


class TestMockProvider:
    """Test the MockProvider implementation."""
    
    @pytest.mark.asyncio
    async def test_mock_generate(self):
        """Test mock provider generates response."""
        provider = MockProvider()
        result = await provider.generate("Test prompt")
        
        assert "response" in result
        assert "Mock response for: 'Test prompt" in result["response"]
        assert result["model"] == "mock"
        assert result["tokens"] == 2  # "Test prompt" = 2 words
    
    @pytest.mark.asyncio
    async def test_mock_health_check(self):
        """Test mock provider health check."""
        provider = MockProvider()
        result = await provider.health_check()
        assert result is True


class TestGeminiProvider:
    """Test the GeminiProvider implementation."""
    
    @pytest.fixture
    def mock_genai(self):
        """Mock Google Generative AI module."""
        # We need to mock at the import level
        import sys
        mock_google = MagicMock()
        mock_genai = MagicMock()
        mock_google.generativeai = mock_genai
        sys.modules['google'] = mock_google
        sys.modules['google.generativeai'] = mock_genai
        
        # Mock the model and response
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Gemini response"
        mock_response.usage_metadata = MagicMock(total_token_count=100)
        mock_model.generate_content.return_value = mock_response
        
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.configure = MagicMock()
        
        yield mock_genai, mock_model
        
        # Cleanup
        if 'google' in sys.modules:
            del sys.modules['google']
        if 'google.generativeai' in sys.modules:
            del sys.modules['google.generativeai']
    
    def test_gemini_initialization(self, mock_genai):
        """Test Gemini provider initialization."""
        mock_genai_module, _ = mock_genai
        
        provider = GeminiProvider("test-api-key")
        
        mock_genai_module.configure.assert_called_once_with(api_key="test-api-key")
        mock_genai_module.GenerativeModel.assert_called_once_with('gemini-pro')
        assert provider.api_key == "test-api-key"
    
    @pytest.mark.asyncio
    async def test_gemini_generate(self, mock_genai):
        """Test Gemini generate method."""
        _, mock_model = mock_genai
        
        provider = GeminiProvider("test-api-key")
        result = await provider.generate("Test prompt")
        
        assert result["response"] == "Gemini response"
        assert result["model"] == "gemini-pro"
        assert result["tokens"] == 100
        
        mock_model.generate_content.assert_called_once_with("Test prompt")
    
    @pytest.mark.asyncio
    async def test_gemini_generate_without_usage_metadata(self, mock_genai):
        """Test Gemini generate when response lacks usage metadata."""
        _, mock_model = mock_genai
        
        # Create response without usage_metadata
        mock_response = MagicMock()
        mock_response.text = "Gemini response"
        del mock_response.usage_metadata  # Remove the attribute
        mock_model.generate_content.return_value = mock_response
        
        provider = GeminiProvider("test-api-key")
        result = await provider.generate("Test prompt")
        
        assert result["tokens"] == 0
    
    @pytest.mark.asyncio
    async def test_gemini_generate_error(self, mock_genai):
        """Test Gemini generate error handling."""
        _, mock_model = mock_genai
        mock_model.generate_content.side_effect = Exception("API Error")
        
        provider = GeminiProvider("test-api-key")
        
        with pytest.raises(Exception, match="API Error"):
            await provider.generate("Test prompt")
    
    @pytest.mark.asyncio
    async def test_gemini_health_check(self, mock_genai):
        """Test Gemini health check."""
        provider = GeminiProvider("test-api-key")
        
        # Test successful health check
        result = await provider.health_check()
        assert result is True
        
        # Test failed health check
        _, mock_model = mock_genai
        mock_model.generate_content.side_effect = Exception("API Error")
        
        result = await provider.health_check()
        assert result is False


class TestOpenRouterProvider:
    """Test the OpenRouterProvider implementation."""
    
    @pytest.fixture
    def mock_httpx(self):
        """Mock httpx client."""
        with patch('src.shared.llm.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Default successful response
            mock_response = AsyncMock()
            mock_response.status_code = 200
            # json() should be a regular method, not async
            mock_response.json = MagicMock(return_value={
                "choices": [{
                    "message": {"content": "OpenRouter response"}
                }],
                "model": "google/gemini-pro",
                "usage": {"total_tokens": 150}
            })
            mock_response.raise_for_status = MagicMock()
            
            mock_client.post.return_value = mock_response
            mock_client.get.return_value = mock_response
            
            yield mock_client
    
    def test_openrouter_initialization(self):
        """Test OpenRouter provider initialization."""
        provider = OpenRouterProvider("test-api-key")
        
        assert provider.api_key == "test-api-key"
        assert provider.base_url == "https://openrouter.ai/api/v1"
        assert provider.default_model == "google/gemini-pro"
    
    def test_openrouter_custom_model(self):
        """Test OpenRouter with custom model from env."""
        os.environ["OPENROUTER_MODEL"] = "anthropic/claude-2"
        
        provider = OpenRouterProvider("test-api-key")
        assert provider.default_model == "anthropic/claude-2"
        
        # Cleanup
        del os.environ["OPENROUTER_MODEL"]
    
    @pytest.mark.asyncio
    async def test_openrouter_generate(self, mock_httpx):
        """Test OpenRouter generate method."""
        provider = OpenRouterProvider("test-api-key")
        result = await provider.generate("Test prompt")
        
        assert result["response"] == "OpenRouter response"
        assert result["model"] == "google/gemini-pro"
        assert result["tokens"] == 150
        
        # Verify API call (may be called multiple times due to retry decorator)
        assert mock_httpx.post.called
        call_args = mock_httpx.post.call_args
        
        assert call_args[0][0] == "https://openrouter.ai/api/v1/chat/completions"
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-api-key"
        assert call_args[1]["json"]["messages"][0]["content"] == "Test prompt"
    
    @pytest.mark.asyncio
    async def test_openrouter_generate_error(self, mock_httpx):
        """Test OpenRouter error handling."""
        mock_httpx.post.side_effect = httpx.HTTPError("Connection failed")
        
        provider = OpenRouterProvider("test-api-key")
        
        # The retry decorator will retry 3 times then raise
        with pytest.raises(Exception):  # Could be tenacity.RetryError or the original exception
            await provider.generate("Test prompt")
    
    @pytest.mark.asyncio
    async def test_openrouter_health_check(self, mock_httpx):
        """Test OpenRouter health check."""
        provider = OpenRouterProvider("test-api-key")
        
        # Test successful health check
        result = await provider.health_check()
        assert result is True
        
        mock_httpx.get.assert_called_with(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": "Bearer test-api-key"},
            timeout=5.0
        )
        
        # Test failed health check
        mock_httpx.get.side_effect = Exception("Connection error")
        result = await provider.health_check()
        assert result is False


class TestLLMProviderFactory:
    """Test the LLMProviderFactory orchestration."""
    
    @pytest.fixture
    def clean_env(self):
        """Clean environment variables."""
        env_vars = ["GEMINI_API_KEY", "OPENROUTER_API_KEY", "LLM_PROVIDER", "LLM_FALLBACK"]
        original = {var: os.environ.get(var) for var in env_vars}
        
        # Clear vars
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
        
        yield
        
        # Restore
        for var, value in original.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]
    
    def test_factory_with_no_keys(self, clean_env):
        """Test factory initialization with no API keys."""
        factory = LLMProviderFactory()
        
        assert "mock" in factory.providers
        assert len(factory.providers) == 1
        assert isinstance(factory.providers["mock"], MockProvider)
    
    def test_factory_with_gemini_key(self, clean_env):
        """Test factory initialization with Gemini key."""
        os.environ["GEMINI_API_KEY"] = "test-gemini-key"
        
        with patch('src.shared.llm.GeminiProvider') as mock_gemini_class:
            mock_gemini_class.return_value = MagicMock()
            
            factory = LLMProviderFactory()
            
            assert "gemini" in factory.providers
            mock_gemini_class.assert_called_once_with("test-gemini-key")
    
    def test_factory_with_openrouter_key(self, clean_env):
        """Test factory initialization with OpenRouter key."""
        os.environ["OPENROUTER_API_KEY"] = "test-openrouter-key"
        
        with patch('src.shared.llm.OpenRouterProvider') as mock_or_class:
            mock_or_class.return_value = MagicMock()
            
            factory = LLMProviderFactory()
            
            assert "openrouter" in factory.providers
            mock_or_class.assert_called_once_with("test-openrouter-key")
    
    def test_factory_with_multiple_keys(self, clean_env):
        """Test factory with multiple provider keys."""
        os.environ["GEMINI_API_KEY"] = "test-gemini-key"
        os.environ["OPENROUTER_API_KEY"] = "test-openrouter-key"
        
        with patch('src.shared.llm.GeminiProvider'), \
             patch('src.shared.llm.OpenRouterProvider'):
            
            factory = LLMProviderFactory()
            
            assert "gemini" in factory.providers
            assert "openrouter" in factory.providers
            assert "mock" not in factory.providers
    
    def test_factory_primary_provider_setting(self, clean_env):
        """Test setting primary provider via environment."""
        os.environ["LLM_PROVIDER"] = "openrouter"
        
        factory = LLMProviderFactory()
        assert factory.primary_provider == "openrouter"
    
    def test_factory_fallback_setting(self, clean_env):
        """Test fallback enable/disable via environment."""
        # Default is true
        factory = LLMProviderFactory()
        assert factory.fallback_enabled is True
        
        # Disable fallback
        os.environ["LLM_FALLBACK"] = "false"
        factory = LLMProviderFactory()
        assert factory.fallback_enabled is False
    
    @pytest.mark.asyncio
    async def test_generate_with_primary_success(self, clean_env):
        """Test generate with successful primary provider."""
        factory = LLMProviderFactory()
        
        # Mock the mock provider (yes, really!)
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = {
            "response": "Test response",
            "model": "mock",
            "tokens": 10
        }
        factory.providers["mock"] = mock_provider
        factory.primary_provider = "mock"
        
        result = await factory.generate("Test prompt", trace_id="trace123")
        
        assert result["response"] == "Test response"
        assert "latency_ms" in result
        mock_provider.generate.assert_called_once_with("Test prompt")
    
    @pytest.mark.asyncio
    async def test_generate_with_fallback(self, clean_env):
        """Test generate with primary failure and fallback."""
        factory = LLMProviderFactory()
        
        # Create two mock providers
        primary_provider = AsyncMock()
        primary_provider.generate.side_effect = Exception("Primary failed")
        
        fallback_provider = AsyncMock()
        fallback_provider.generate.return_value = {
            "response": "Fallback response",
            "model": "fallback",
            "tokens": 20
        }
        
        factory.providers = {
            "primary": primary_provider,
            "fallback": fallback_provider
        }
        factory.primary_provider = "primary"
        factory.fallback_enabled = True
        
        result = await factory.generate("Test prompt")
        
        assert result["response"] == "Fallback response"
        assert result["fallback"] is True
        assert "latency_ms" in result
        
        primary_provider.generate.assert_called_once()
        fallback_provider.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_no_fallback(self, clean_env):
        """Test generate with fallback disabled."""
        factory = LLMProviderFactory()
        factory.fallback_enabled = False
        
        primary_provider = AsyncMock()
        primary_provider.generate.side_effect = Exception("Primary failed")
        
        factory.providers = {"primary": primary_provider}
        factory.primary_provider = "primary"
        
        with pytest.raises(Exception, match="Primary failed"):
            await factory.generate("Test prompt")
    
    @pytest.mark.asyncio
    async def test_generate_all_providers_fail(self, clean_env):
        """Test when all providers fail."""
        factory = LLMProviderFactory()
        
        # Create failing providers
        provider1 = AsyncMock()
        provider1.generate.side_effect = Exception("Provider 1 failed")
        
        provider2 = AsyncMock()
        provider2.generate.side_effect = Exception("Provider 2 failed")
        
        factory.providers = {
            "provider1": provider1,
            "provider2": provider2
        }
        factory.primary_provider = "provider1"
        
        with pytest.raises(Exception, match="All LLM providers failed"):
            await factory.generate("Test prompt")
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, clean_env):
        """Test health check with at least one healthy provider."""
        factory = LLMProviderFactory()
        
        healthy_provider = AsyncMock()
        healthy_provider.health_check.return_value = True
        
        unhealthy_provider = AsyncMock()
        unhealthy_provider.health_check.side_effect = Exception("Unhealthy")
        
        factory.providers = {
            "unhealthy": unhealthy_provider,
            "healthy": healthy_provider
        }
        
        result = await factory.health_check()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_all_fail(self, clean_env):
        """Test health check when all providers are unhealthy."""
        factory = LLMProviderFactory()
        
        provider1 = AsyncMock()
        provider1.health_check.side_effect = Exception("Unhealthy 1")
        
        provider2 = AsyncMock()
        provider2.health_check.side_effect = Exception("Unhealthy 2")
        
        factory.providers = {
            "provider1": provider1,
            "provider2": provider2
        }
        
        result = await factory.health_check()
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])