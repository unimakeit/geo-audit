"""Check for JSON-LD structured data."""

import json
import re
from typing import Any

from bs4 import BeautifulSoup

from ..models import CheckResult, Finding, Severity


# Schema types that are particularly valuable for GEO
HIGH_VALUE_SCHEMAS = {
    "Organization",
    "LocalBusiness",
    "Product",
    "Service",
    "Person",
    "Article",
    "BlogPosting",
    "FAQPage",
    "HowTo",
    "Recipe",
    "Event",
    "Course",
    "SoftwareApplication",
    "WebApplication",
}

RECOMMENDED_ORG_FIELDS = {"name", "description", "url", "logo", "sameAs", "contactPoint"}
RECOMMENDED_PRODUCT_FIELDS = {"name", "description", "brand", "offers", "image"}


def extract_json_ld(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Extract all JSON-LD scripts from the page."""
    scripts = soup.find_all("script", type="application/ld+json")
    results = []
    
    for script in scripts:
        try:
            content = script.string
            if content:
                data = json.loads(content)
                if isinstance(data, list):
                    results.extend(data)
                else:
                    results.append(data)
        except json.JSONDecodeError:
            continue
    
    return results


def get_schema_types(data: dict[str, Any]) -> set[str]:
    """Extract @type values from JSON-LD, handling various formats."""
    types: set[str] = set()
    
    if "@type" in data:
        type_val = data["@type"]
        if isinstance(type_val, list):
            types.update(type_val)
        else:
            types.add(type_val)
    
    # Check @graph
    if "@graph" in data:
        for item in data["@graph"]:
            if isinstance(item, dict):
                types.update(get_schema_types(item))
    
    return types


def check_structured_data(soup: BeautifulSoup, url: str) -> CheckResult:
    """Check JSON-LD structured data quality.
    
    JSON-LD is the preferred format for LLMs because it's:
    - Machine-readable
    - Self-contained
    - Easy to parse
    """
    findings: list[Finding] = []
    score = 0
    max_score = 25
    
    json_ld_data = extract_json_ld(soup)
    
    if not json_ld_data:
        findings.append(Finding(
            check="structured_data",
            message="No JSON-LD structured data found",
            severity=Severity.ERROR,
            details="JSON-LD helps LLMs understand your content structure and entity relationships.",
            fix_hint="Add at minimum an Organization schema. Use Google's Structured Data Markup Helper.",
            impact=8
        ))
        return CheckResult(
            name="Structured Data",
            score=score,
            max_score=max_score,
            findings=findings
        )
    
    # Base score for having any JSON-LD
    score += 5
    findings.append(Finding(
        check="structured_data",
        message=f"Found {len(json_ld_data)} JSON-LD block(s)",
        severity=Severity.PASS
    ))
    
    # Collect all schema types
    all_types: set[str] = set()
    for data in json_ld_data:
        all_types.update(get_schema_types(data))
    
    # Check for high-value schemas
    found_high_value = all_types.intersection(HIGH_VALUE_SCHEMAS)
    if found_high_value:
        score += 10
        findings.append(Finding(
            check="structured_data",
            message=f"High-value schemas found: {', '.join(sorted(found_high_value))}",
            severity=Severity.PASS
        ))
    else:
        findings.append(Finding(
            check="structured_data",
            message="No high-value schema types found",
            severity=Severity.WARNING,
            details=f"Consider adding: Organization, Product, Article, FAQPage, or HowTo",
            fix_hint="Add Organization schema at minimum - helps LLMs identify your brand.",
            impact=7
        ))
    
    # Check Organization schema completeness
    has_org = False
    for data in json_ld_data:
        types = get_schema_types(data)
        if "Organization" in types or "LocalBusiness" in types:
            has_org = True
            present_fields = set(data.keys())
            missing = RECOMMENDED_ORG_FIELDS - present_fields
            if missing:
                findings.append(Finding(
                    check="structured_data",
                    message="Organization schema missing recommended fields",
                    severity=Severity.INFO,
                    details=f"Missing: {', '.join(sorted(missing))}",
                    fix_hint=f"Add {', '.join(sorted(missing))} to your Organization schema",
                    impact=4
                ))
            else:
                score += 5
                findings.append(Finding(
                    check="structured_data",
                    message="Organization schema has all recommended fields",
                    severity=Severity.PASS
                ))
            break
    
    if not has_org and "Organization" not in all_types and "LocalBusiness" not in all_types:
        findings.append(Finding(
            check="structured_data",
            message="No Organization/LocalBusiness schema",
            severity=Severity.WARNING,
            details="Organization schema establishes your brand identity for LLMs",
            fix_hint="Add Organization schema with name, description, logo, url, and sameAs (social links)",
            impact=7
        ))
    
    # Check for sameAs (social proof / entity linking)
    has_same_as = False
    for data in json_ld_data:
        if "sameAs" in data:
            same_as = data["sameAs"]
            if isinstance(same_as, list) and len(same_as) >= 2:
                has_same_as = True
                score += 5
                findings.append(Finding(
                    check="structured_data",
                    message=f"Good entity linking via sameAs ({len(same_as)} links)",
                    severity=Severity.PASS,
                    details="Social links help LLMs verify your brand identity"
                ))
                break
    
    if not has_same_as:
        findings.append(Finding(
            check="structured_data",
            message="Missing or minimal sameAs links",
            severity=Severity.INFO,
            details="sameAs links to social profiles help LLMs connect your brand across the web",
            fix_hint="Add sameAs array with links to LinkedIn, Twitter, Facebook, Wikipedia if applicable",
            impact=5
        ))
    
    return CheckResult(
        name="Structured Data",
        score=score,
        max_score=max_score,
        findings=findings
    )
