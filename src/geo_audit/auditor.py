"""Main auditor that runs all checks."""

import time
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .models import AuditResult, Finding, Severity
from .checks import (
    check_llms_txt,
    check_structured_data,
    check_meta_tags,
    check_content_structure,
    check_technical,
)


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; GEOAudit/1.0; +https://github.com/huiren/geo-audit)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def normalize_url(url: str) -> str:
    """Ensure URL has a scheme."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def audit_url(url: str, timeout: float = 30.0) -> AuditResult:
    """Run a complete GEO audit on a URL.
    
    Args:
        url: The URL to audit
        timeout: Request timeout in seconds
        
    Returns:
        AuditResult with all check results
    """
    url = normalize_url(url)
    start_time = time.time()
    
    result = AuditResult(url=url, final_url=url)
    
    try:
        with httpx.Client(
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            follow_redirects=True
        ) as client:
            # Fetch the page
            response = client.get(url)
            response.raise_for_status()
            
            result.final_url = str(response.url)
            result.fetch_time_ms = int((time.time() - start_time) * 1000)
            
            # Parse HTML
            soup = BeautifulSoup(response.text, "lxml")
            
            # Run all checks
            result.checks = [
                check_llms_txt(result.final_url, client),
                check_structured_data(soup, result.final_url),
                check_meta_tags(soup, result.final_url),
                check_content_structure(soup, result.final_url),
                check_technical(soup, url, result.final_url, response, client),
            ]
            
    except httpx.TimeoutException:
        result.error = f"Timeout after {timeout}s"
    except httpx.HTTPStatusError as e:
        result.error = f"HTTP {e.response.status_code}"
    except httpx.RequestError as e:
        result.error = f"Request failed: {e}"
    except Exception as e:
        result.error = f"Error: {e}"
    
    return result
