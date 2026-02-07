"""Test runner for brand visibility across LLMs."""

from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .prompts import get_test_prompts
from .providers import LLMProvider, LLMResponse, get_configured_providers


@dataclass
class LLMResult:
    """Result from testing a single LLM."""
    provider: str
    model: str
    responses: list[LLMResponse] = field(default_factory=list)
    
    @property
    def mention_rate(self) -> float:
        """Percentage of responses that mention the brand."""
        if not self.responses:
            return 0.0
        mentions = sum(1 for r in self.responses if r.mentions_brand)
        return (mentions / len(self.responses)) * 100
    
    @property
    def avg_latency_ms(self) -> int:
        """Average response latency."""
        if not self.responses:
            return 0
        return int(sum(r.latency_ms for r in self.responses) / len(self.responses))
    
    @property
    def error_count(self) -> int:
        """Number of errors."""
        return sum(1 for r in self.responses if r.error)


@dataclass
class TestResult:
    """Complete test result across all LLMs."""
    brand: str
    industry: str | None
    llm_results: list[LLMResult] = field(default_factory=list)
    
    @property
    def overall_visibility(self) -> float:
        """Overall visibility score (0-100)."""
        if not self.llm_results:
            return 0.0
        # Weight by provider importance (ChatGPT most important)
        weights = {
            "OpenAI": 3,
            "Google": 2,
            "Anthropic": 1,
            "Perplexity": 2,  # Perplexity is important for search
        }
        total_weight = 0
        weighted_sum = 0
        
        for result in self.llm_results:
            if result.error_count < len(result.responses):  # Has some valid responses
                weight = weights.get(result.provider, 1)
                weighted_sum += result.mention_rate * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.0
        return weighted_sum / total_weight
    
    @property
    def providers_tested(self) -> int:
        """Number of providers successfully tested."""
        return sum(1 for r in self.llm_results if r.error_count < len(r.responses))


def test_brand_visibility(
    brand: str,
    industry: str | None = None,
    product: str | None = None,
    providers: list[LLMProvider] | None = None,
    parallel: bool = True,
) -> TestResult:
    """Test brand visibility across multiple LLMs.
    
    Args:
        brand: Brand name to test
        industry: Optional industry for context
        product: Optional specific product name
        providers: LLM providers to test (default: all configured)
        parallel: Run tests in parallel (default: True)
    
    Returns:
        TestResult with visibility scores per LLM
    """
    if providers is None:
        providers = get_configured_providers()
    
    if not providers:
        return TestResult(brand=brand, industry=industry)
    
    prompts = get_test_prompts(brand, industry, product)
    result = TestResult(brand=brand, industry=industry)
    
    def test_provider(provider: LLMProvider) -> LLMResult:
        llm_result = LLMResult(provider=provider.name, model=provider.model)
        
        for prompt_info in prompts:
            response = provider.query(prompt_info["prompt"], brand)
            llm_result.responses.append(response)
        
        return llm_result
    
    if parallel and len(providers) > 1:
        with ThreadPoolExecutor(max_workers=len(providers)) as executor:
            futures = {executor.submit(test_provider, p): p for p in providers}
            for future in as_completed(futures):
                try:
                    llm_result = future.result()
                    result.llm_results.append(llm_result)
                except Exception as e:
                    provider = futures[future]
                    result.llm_results.append(LLMResult(
                        provider=provider.name,
                        model=provider.model,
                        responses=[]
                    ))
    else:
        for provider in providers:
            llm_result = test_provider(provider)
            result.llm_results.append(llm_result)
    
    return result
