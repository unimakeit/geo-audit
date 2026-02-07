"""Check for llms.txt file presence and quality."""

import httpx
from urllib.parse import urljoin, urlparse

from ..models import CheckResult, Finding, Severity


def check_llms_txt(base_url: str, client: httpx.Client) -> CheckResult:
    """Check if the site has a valid llms.txt file.
    
    The llms.txt specification: https://llmstxt.org/
    - /llms.txt - basic version
    - /llms-full.txt - extended version with more content
    """
    findings: list[Finding] = []
    score = 0
    max_score = 25  # llms.txt is important for GEO
    
    parsed = urlparse(base_url)
    root_url = f"{parsed.scheme}://{parsed.netloc}"
    
    # Check for llms.txt
    llms_txt_url = urljoin(root_url, "/llms.txt")
    llms_full_url = urljoin(root_url, "/llms-full.txt")
    
    has_basic = False
    has_full = False
    basic_content = ""
    
    try:
        resp = client.get(llms_txt_url, follow_redirects=True)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("text/"):
            has_basic = True
            basic_content = resp.text
            score += 15
            
            # Check content quality
            lines = basic_content.strip().split("\n")
            if len(lines) < 3:
                findings.append(Finding(
                    check="llms_txt",
                    message="llms.txt exists but is very short",
                    severity=Severity.WARNING,
                    details=f"Only {len(lines)} lines. Consider adding more context.",
                    fix_hint="Add company description, key products/services, and important pages.",
                    impact=6
                ))
            else:
                score += 5
                findings.append(Finding(
                    check="llms_txt",
                    message="llms.txt found with good content",
                    severity=Severity.PASS,
                    details=f"{len(lines)} lines of content"
                ))
                
            # Check for key sections
            content_lower = basic_content.lower()
            if "#" not in basic_content:
                findings.append(Finding(
                    check="llms_txt",
                    message="llms.txt lacks markdown headers",
                    severity=Severity.INFO,
                    details="Using # headers helps LLMs parse sections",
                    fix_hint="Add sections like # About, # Products, # Contact",
                    impact=3
                ))
    except httpx.RequestError:
        pass
    
    # Check for llms-full.txt
    try:
        resp = client.get(llms_full_url, follow_redirects=True)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("text/"):
            has_full = True
            score += 5
            findings.append(Finding(
                check="llms_txt",
                message="llms-full.txt found (extended version)",
                severity=Severity.PASS,
                details="Extended version provides more context for LLMs"
            ))
    except httpx.RequestError:
        pass
    
    if not has_basic and not has_full:
        findings.append(Finding(
            check="llms_txt",
            message="No llms.txt file found",
            severity=Severity.ERROR,
            details="llms.txt helps AI systems understand your site. Only 0.3% of top sites have this - easy win!",
            fix_hint="Create /llms.txt with: company name, description, key pages, and contact info. See llmstxt.org",
            impact=9
        ))
    
    return CheckResult(
        name="llms.txt",
        score=score,
        max_score=max_score,
        findings=findings
    )
