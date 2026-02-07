"""Technical checks for GEO optimization."""

import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from ..models import CheckResult, Finding, Severity


def check_technical(
    soup: BeautifulSoup,
    url: str,
    final_url: str,
    response: httpx.Response,
    client: httpx.Client
) -> CheckResult:
    """Check technical factors affecting GEO.
    
    Key factors:
    - robots.txt (allow AI crawlers)
    - sitemap.xml
    - Page load time
    - Mobile-friendliness
    - HTTPS
    """
    findings: list[Finding] = []
    score = 0
    max_score = 10
    
    parsed = urlparse(final_url)
    root_url = f"{parsed.scheme}://{parsed.netloc}"
    
    # Check HTTPS
    if parsed.scheme == "https":
        score += 2
        findings.append(Finding(
            check="technical",
            message="HTTPS enabled ✓",
            severity=Severity.PASS
        ))
    else:
        findings.append(Finding(
            check="technical",
            message="Not using HTTPS",
            severity=Severity.WARNING,
            details="HTTPS is a trust signal",
            fix_hint="Enable HTTPS on your site",
            impact=5
        ))
    
    # Check robots.txt for AI crawler blocking
    try:
        robots_url = urljoin(root_url, "/robots.txt")
        robots_resp = client.get(robots_url, follow_redirects=True)
        
        if robots_resp.status_code == 200:
            robots_content = robots_resp.text.lower()
            
            # Check for AI crawler blocks
            ai_crawlers = ["gptbot", "chatgpt", "anthropic", "claude", "google-extended", "ccbot"]
            blocked_crawlers = []
            
            for crawler in ai_crawlers:
                if f"user-agent: {crawler}" in robots_content:
                    # Check if disallow follows
                    idx = robots_content.find(f"user-agent: {crawler}")
                    section = robots_content[idx:idx+200]
                    if "disallow: /" in section:
                        blocked_crawlers.append(crawler)
            
            if blocked_crawlers:
                findings.append(Finding(
                    check="technical",
                    message=f"AI crawlers blocked: {', '.join(blocked_crawlers)}",
                    severity=Severity.WARNING,
                    details="Blocking AI crawlers reduces LLM training/indexing",
                    fix_hint="Consider allowing GPTBot and other AI crawlers if you want LLM visibility",
                    impact=6
                ))
            else:
                score += 3
                findings.append(Finding(
                    check="technical",
                    message="No AI crawler blocks detected",
                    severity=Severity.PASS
                ))
        else:
            score += 2
            findings.append(Finding(
                check="technical",
                message="No robots.txt (all crawlers allowed by default)",
                severity=Severity.INFO
            ))
    except httpx.RequestError:
        findings.append(Finding(
            check="technical",
            message="Could not check robots.txt",
            severity=Severity.INFO
        ))
    
    # Check sitemap
    try:
        sitemap_url = urljoin(root_url, "/sitemap.xml")
        sitemap_resp = client.get(sitemap_url, follow_redirects=True)
        
        if sitemap_resp.status_code == 200 and "xml" in sitemap_resp.headers.get("content-type", ""):
            score += 2
            findings.append(Finding(
                check="technical",
                message="sitemap.xml found ✓",
                severity=Severity.PASS
            ))
        else:
            findings.append(Finding(
                check="technical",
                message="No sitemap.xml found",
                severity=Severity.INFO,
                details="Sitemaps help crawlers discover content",
                fix_hint="Add a sitemap.xml file",
                impact=3
            ))
    except httpx.RequestError:
        pass
    
    # Check viewport meta tag (mobile-friendliness)
    viewport = soup.find("meta", attrs={"name": "viewport"})
    if viewport:
        score += 2
        findings.append(Finding(
            check="technical",
            message="Mobile viewport set ✓",
            severity=Severity.PASS
        ))
    else:
        findings.append(Finding(
            check="technical",
            message="No viewport meta tag",
            severity=Severity.INFO,
            details="Mobile-friendliness is a ranking factor",
            fix_hint="Add <meta name='viewport' content='width=device-width, initial-scale=1'>",
            impact=3
        ))
    
    # Check for language declaration
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        score += 1
        findings.append(Finding(
            check="technical",
            message=f"Language declared: {html_tag.get('lang')}",
            severity=Severity.PASS
        ))
    else:
        findings.append(Finding(
            check="technical",
            message="No language declaration",
            severity=Severity.INFO,
            details="Language helps LLMs serve content to right audiences",
            fix_hint="Add lang attribute to <html> tag",
            impact=2
        ))
    
    return CheckResult(
        name="Technical",
        score=score,
        max_score=max_score,
        findings=findings
    )
