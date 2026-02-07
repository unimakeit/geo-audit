"""Check meta tags for GEO optimization."""

from bs4 import BeautifulSoup

from ..models import CheckResult, Finding, Severity


def check_meta_tags(soup: BeautifulSoup, url: str) -> CheckResult:
    """Check meta tags quality for GEO.
    
    Key meta tags for LLM visibility:
    - title: Clear, descriptive
    - description: Comprehensive, keyword-rich
    - og:* tags: Social/preview optimization
    - canonical: Avoid duplicate content
    """
    findings: list[Finding] = []
    score = 0
    max_score = 20
    
    # Check title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""
    
    if not title:
        findings.append(Finding(
            check="meta_tags",
            message="Missing page title",
            severity=Severity.ERROR,
            fix_hint="Add a descriptive <title> tag",
            impact=8
        ))
    elif len(title) < 30:
        findings.append(Finding(
            check="meta_tags",
            message=f"Title too short ({len(title)} chars)",
            severity=Severity.WARNING,
            details=f"Current: '{title}'",
            fix_hint="Expand title to 50-60 characters with key descriptors",
            impact=5
        ))
    elif len(title) > 70:
        findings.append(Finding(
            check="meta_tags",
            message=f"Title too long ({len(title)} chars)",
            severity=Severity.INFO,
            details="May be truncated in search results",
            fix_hint="Trim to under 60 characters",
            impact=3
        ))
        score += 3
    else:
        score += 5
        findings.append(Finding(
            check="meta_tags",
            message=f"Good title length ({len(title)} chars)",
            severity=Severity.PASS
        ))
    
    # Check meta description
    desc_tag = soup.find("meta", attrs={"name": "description"})
    description = desc_tag.get("content", "") if desc_tag else ""
    
    if not description:
        findings.append(Finding(
            check="meta_tags",
            message="Missing meta description",
            severity=Severity.ERROR,
            details="Meta descriptions are often used by LLMs to summarize pages",
            fix_hint="Add a 150-160 character description summarizing the page",
            impact=7
        ))
    elif len(description) < 100:
        findings.append(Finding(
            check="meta_tags",
            message=f"Meta description too short ({len(description)} chars)",
            severity=Severity.WARNING,
            details="Short descriptions miss opportunity to provide context",
            fix_hint="Expand to 150-160 characters with key information",
            impact=5
        ))
        score += 2
    elif len(description) > 170:
        findings.append(Finding(
            check="meta_tags",
            message=f"Meta description slightly long ({len(description)} chars)",
            severity=Severity.INFO,
            details="May be truncated, but more content for LLMs",
            impact=2
        ))
        score += 4
    else:
        score += 5
        findings.append(Finding(
            check="meta_tags",
            message=f"Good meta description length ({len(description)} chars)",
            severity=Severity.PASS
        ))
    
    # Check Open Graph tags
    og_tags = {
        "og:title": soup.find("meta", property="og:title"),
        "og:description": soup.find("meta", property="og:description"),
        "og:image": soup.find("meta", property="og:image"),
        "og:type": soup.find("meta", property="og:type"),
        "og:url": soup.find("meta", property="og:url"),
    }
    
    present_og = [k for k, v in og_tags.items() if v]
    missing_og = [k for k, v in og_tags.items() if not v]
    
    if len(present_og) >= 4:
        score += 5
        findings.append(Finding(
            check="meta_tags",
            message=f"Good Open Graph coverage ({len(present_og)}/5 tags)",
            severity=Severity.PASS
        ))
    elif len(present_og) >= 2:
        score += 2
        findings.append(Finding(
            check="meta_tags",
            message=f"Partial Open Graph tags ({len(present_og)}/5)",
            severity=Severity.INFO,
            details=f"Missing: {', '.join(missing_og)}",
            fix_hint="Add missing OG tags for better social sharing and LLM context",
            impact=3
        ))
    else:
        findings.append(Finding(
            check="meta_tags",
            message="Missing or minimal Open Graph tags",
            severity=Severity.WARNING,
            details="Open Graph helps LLMs and social platforms understand your content",
            fix_hint="Add og:title, og:description, og:image, og:type, og:url",
            impact=4
        ))
    
    # Check canonical URL
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        score += 5
        findings.append(Finding(
            check="meta_tags",
            message="Canonical URL set",
            severity=Severity.PASS
        ))
    else:
        findings.append(Finding(
            check="meta_tags",
            message="No canonical URL",
            severity=Severity.INFO,
            details="Canonical URLs help prevent duplicate content confusion",
            fix_hint="Add <link rel='canonical' href='...'>",
            impact=3
        ))
    
    return CheckResult(
        name="Meta Tags",
        score=score,
        max_score=max_score,
        findings=findings
    )
