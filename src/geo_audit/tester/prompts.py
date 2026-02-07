"""Prompt templates for testing brand visibility."""


def get_test_prompts(brand: str, industry: str | None = None, product: str | None = None) -> list[dict[str, str]]:
    """Generate test prompts to check if LLMs know about a brand.
    
    Returns list of dicts with 'category' and 'prompt' keys.
    """
    prompts = []
    
    # Direct brand query
    prompts.append({
        "category": "direct",
        "prompt": f"What is {brand}? Give me a brief overview."
    })
    
    # Recommendation query (most important for GEO)
    if industry:
        prompts.append({
            "category": "recommendation",
            "prompt": f"What are the best {industry} companies or tools? List your top recommendations."
        })
    else:
        prompts.append({
            "category": "recommendation",
            "prompt": f"I'm looking for alternatives to {brand}. What would you recommend?"
        })
    
    # Comparison query
    prompts.append({
        "category": "comparison",
        "prompt": f"How does {brand} compare to its competitors?"
    })
    
    # Product-specific if provided
    if product:
        prompts.append({
            "category": "product",
            "prompt": f"Tell me about {product} from {brand}. What are its key features?"
        })
    
    # Use case query
    prompts.append({
        "category": "use_case",
        "prompt": f"When should someone use {brand}? What problems does it solve?"
    })
    
    return prompts


def get_industry_prompts(industry: str) -> list[dict[str, str]]:
    """Generate industry-specific prompts where we check if brand appears."""
    return [
        {
            "category": "industry_leaders",
            "prompt": f"Who are the leading companies in {industry}?"
        },
        {
            "category": "industry_tools",
            "prompt": f"What are the best tools for {industry}?"
        },
        {
            "category": "industry_recommendations",
            "prompt": f"I need a solution for {industry}. What do you recommend?"
        },
    ]
