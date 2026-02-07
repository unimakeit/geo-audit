"""LLM provider interfaces for testing."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class LLMResponse:
    """Response from an LLM."""
    provider: str
    model: str
    prompt: str
    response: str
    mentions_brand: bool
    mention_context: str | None  # Snippet where brand is mentioned
    latency_ms: int
    error: str | None = None


class LLMProvider(ABC):
    """Base class for LLM providers."""
    
    name: str
    
    @abstractmethod
    def query(self, prompt: str, brand: str) -> LLMResponse:
        """Query the LLM and check if brand is mentioned."""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the provider is properly configured."""
        pass
    
    def _check_mention(self, text: str, brand: str) -> tuple[bool, str | None]:
        """Check if brand is mentioned in text, return context snippet."""
        text_lower = text.lower()
        brand_lower = brand.lower()
        
        # Also check common variations
        variations = [brand_lower, brand_lower.replace(" ", ""), brand_lower.replace("-", "")]
        
        for variant in variations:
            idx = text_lower.find(variant)
            if idx != -1:
                # Extract context (100 chars before and after)
                start = max(0, idx - 50)
                end = min(len(text), idx + len(variant) + 100)
                context = text[start:end]
                if start > 0:
                    context = "..." + context
                if end < len(text):
                    context = context + "..."
                return True, context
        
        return False, None


class OpenAIProvider(LLMProvider):
    """OpenAI (ChatGPT) provider."""
    
    name = "OpenAI"
    
    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.base_url = "https://api.openai.com/v1"
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    def query(self, prompt: str, brand: str) -> LLMResponse:
        import time
        start = time.time()
        
        if not self.is_configured():
            return LLMResponse(
                provider=self.name,
                model=self.model,
                prompt=prompt,
                response="",
                mentions_brand=False,
                mention_context=None,
                latency_ms=0,
                error="OPENAI_API_KEY not set"
            )
        
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1000,
                        "temperature": 0.7
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                
            response_text = data["choices"][0]["message"]["content"]
            latency = int((time.time() - start) * 1000)
            
            mentions, context = self._check_mention(response_text, brand)
            
            return LLMResponse(
                provider=self.name,
                model=self.model,
                prompt=prompt,
                response=response_text,
                mentions_brand=mentions,
                mention_context=context,
                latency_ms=latency
            )
            
        except Exception as e:
            return LLMResponse(
                provider=self.name,
                model=self.model,
                prompt=prompt,
                response="",
                mentions_brand=False,
                mention_context=None,
                latency_ms=int((time.time() - start) * 1000),
                error=str(e)
            )


class AnthropicProvider(LLMProvider):
    """Anthropic (Claude) provider."""
    
    name = "Anthropic"
    
    def __init__(self, api_key: str | None = None, model: str = "claude-3-5-haiku-20241022"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.base_url = "https://api.anthropic.com/v1"
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    def query(self, prompt: str, brand: str) -> LLMResponse:
        import time
        start = time.time()
        
        if not self.is_configured():
            return LLMResponse(
                provider=self.name,
                model=self.model,
                prompt=prompt,
                response="",
                mentions_brand=False,
                mention_context=None,
                latency_ms=0,
                error="ANTHROPIC_API_KEY not set"
            )
        
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{self.base_url}/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 1000,
                        "messages": [{"role": "user", "content": prompt}]
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                
            response_text = data["content"][0]["text"]
            latency = int((time.time() - start) * 1000)
            
            mentions, context = self._check_mention(response_text, brand)
            
            return LLMResponse(
                provider=self.name,
                model=self.model,
                prompt=prompt,
                response=response_text,
                mentions_brand=mentions,
                mention_context=context,
                latency_ms=latency
            )
            
        except Exception as e:
            return LLMResponse(
                provider=self.name,
                model=self.model,
                prompt=prompt,
                response="",
                mentions_brand=False,
                mention_context=None,
                latency_ms=int((time.time() - start) * 1000),
                error=str(e)
            )


class PerplexityProvider(LLMProvider):
    """Perplexity AI provider."""
    
    name = "Perplexity"
    
    def __init__(self, api_key: str | None = None, model: str = "sonar"):
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        self.model = model
        self.base_url = "https://api.perplexity.ai"
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    def query(self, prompt: str, brand: str) -> LLMResponse:
        import time
        start = time.time()
        
        if not self.is_configured():
            return LLMResponse(
                provider=self.name,
                model=self.model,
                prompt=prompt,
                response="",
                mentions_brand=False,
                mention_context=None,
                latency_ms=0,
                error="PERPLEXITY_API_KEY not set"
            )
        
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}]
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                
            response_text = data["choices"][0]["message"]["content"]
            latency = int((time.time() - start) * 1000)
            
            mentions, context = self._check_mention(response_text, brand)
            
            return LLMResponse(
                provider=self.name,
                model=self.model,
                prompt=prompt,
                response=response_text,
                mentions_brand=mentions,
                mention_context=context,
                latency_ms=latency
            )
            
        except Exception as e:
            return LLMResponse(
                provider=self.name,
                model=self.model,
                prompt=prompt,
                response="",
                mentions_brand=False,
                mention_context=None,
                latency_ms=int((time.time() - start) * 1000),
                error=str(e)
            )


class GoogleProvider(LLMProvider):
    """Google Gemini provider."""
    
    name = "Google"
    
    def __init__(self, api_key: str | None = None, model: str = "gemini-2.0-flash"):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.model = model
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    def query(self, prompt: str, brand: str) -> LLMResponse:
        import time
        start = time.time()
        
        if not self.is_configured():
            return LLMResponse(
                provider=self.name,
                model=self.model,
                prompt=prompt,
                response="",
                mentions_brand=False,
                mention_context=None,
                latency_ms=0,
                error="GOOGLE_API_KEY not set"
            )
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}]
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                
            response_text = data["candidates"][0]["content"]["parts"][0]["text"]
            latency = int((time.time() - start) * 1000)
            
            mentions, context = self._check_mention(response_text, brand)
            
            return LLMResponse(
                provider=self.name,
                model=self.model,
                prompt=prompt,
                response=response_text,
                mentions_brand=mentions,
                mention_context=context,
                latency_ms=latency
            )
            
        except Exception as e:
            return LLMResponse(
                provider=self.name,
                model=self.model,
                prompt=prompt,
                response="",
                mentions_brand=False,
                mention_context=None,
                latency_ms=int((time.time() - start) * 1000),
                error=str(e)
            )


def get_all_providers() -> list[LLMProvider]:
    """Get all available LLM providers."""
    return [
        OpenAIProvider(),
        AnthropicProvider(),
        GoogleProvider(),
        PerplexityProvider(),
    ]


def get_configured_providers() -> list[LLMProvider]:
    """Get only providers that are properly configured."""
    return [p for p in get_all_providers() if p.is_configured()]
