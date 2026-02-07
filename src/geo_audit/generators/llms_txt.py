"""Generate llms.txt file from page content."""

from dataclasses import dataclass
from urllib.parse import urlparse, urljoin
import re

from bs4 import BeautifulSoup
import httpx


@dataclass
class PageInfo:
    """Extracted page information."""
    url: str
    domain: str
    title: str
    description: str
    headings: list[str]
    nav_links: list[tuple[str, str]]  # (text, href)
    social_links: list[str]
    has_blog: bool
    has_docs: bool
    has_pricing: bool
    has_about: bool
    has_contact: bool


def extract_page_info(soup: BeautifulSoup, url: str) -> PageInfo:
    """Extract relevant information from a page."""
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    
    # Title - extract clean company/site name
    title_tag = soup.find("title")
    raw_title = title_tag.get_text(strip=True) if title_tag else domain
    
    # Try OG site_name first
    og_site = soup.find("meta", property="og:site_name")
    if og_site and og_site.get("content"):
        title = og_site["content"].strip()
    else:
        # Parse title, removing generic words
        parts = re.split(r'\s*[|–—\-\\•·]\s*', raw_title)
        generic_words = {"home", "welcome", "homepage", "official", "site", "website"}
        candidates = [p.strip() for p in parts if p.strip().lower() not in generic_words]
        title = candidates[0] if candidates else parts[-1].strip() if parts else domain
    
    # Description
    desc_tag = soup.find("meta", attrs={"name": "description"})
    description = desc_tag.get("content", "") if desc_tag else ""
    
    # OG description as fallback
    if not description:
        og_desc = soup.find("meta", property="og:description")
        description = og_desc.get("content", "") if og_desc else ""
    
    # Headings (H1, H2)
    headings = []
    for h in soup.find_all(["h1", "h2"]):
        text = h.get_text(strip=True)
        if text and len(text) < 100:
            headings.append(text)
    
    # Navigation links
    nav_links = []
    nav = soup.find("nav") or soup.find("header")
    if nav:
        for a in nav.find_all("a", href=True):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if text and len(text) < 50 and href.startswith(("/", "http")):
                # Normalize href
                if href.startswith("/"):
                    href = urljoin(url, href)
                nav_links.append((text, href))
    
    # Social links
    social_patterns = ["twitter.com", "x.com", "linkedin.com", "facebook.com", 
                       "github.com", "instagram.com", "youtube.com"]
    social_links = []
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        for pattern in social_patterns:
            if pattern in href and href not in social_links:
                social_links.append(href)
                break
    
    # Detect common pages
    all_links = [a.get("href", "").lower() for a in soup.find_all("a", href=True)]
    all_links_str = " ".join(all_links)
    
    return PageInfo(
        url=url,
        domain=domain,
        title=title,
        description=description,
        headings=headings[:10],
        nav_links=nav_links[:15],
        social_links=social_links[:5],
        has_blog="/blog" in all_links_str,
        has_docs="/docs" in all_links_str or "/documentation" in all_links_str,
        has_pricing="/pricing" in all_links_str,
        has_about="/about" in all_links_str,
        has_contact="/contact" in all_links_str,
    )


def generate_llms_txt(soup: BeautifulSoup, url: str) -> str:
    """Generate llms.txt content from page information.
    
    Following the llms.txt specification: https://llmstxt.org/
    """
    info = extract_page_info(soup, url)
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    lines = []
    
    # Header
    lines.append(f"# {info.title}")
    lines.append("")
    
    # Description
    if info.description:
        lines.append(f"> {info.description}")
        lines.append("")
    
    # About section
    lines.append("## About")
    lines.append("")
    if info.description:
        lines.append(info.description)
    else:
        lines.append(f"{info.title} - Visit {info.domain} to learn more.")
    lines.append("")
    
    # Key pages
    lines.append("## Key Pages")
    lines.append("")
    
    # Always include homepage
    lines.append(f"- [Home]({base_url}/)")
    
    # Add detected pages
    if info.has_about:
        lines.append(f"- [About]({base_url}/about)")
    if info.has_pricing:
        lines.append(f"- [Pricing]({base_url}/pricing)")
    if info.has_docs:
        lines.append(f"- [Documentation]({base_url}/docs)")
    if info.has_blog:
        lines.append(f"- [Blog]({base_url}/blog)")
    if info.has_contact:
        lines.append(f"- [Contact]({base_url}/contact)")
    
    # Add unique nav links (skip duplicates)
    added_paths = {"/", "/about", "/pricing", "/docs", "/blog", "/contact"}
    for text, href in info.nav_links:
        path = urlparse(href).path.rstrip("/") or "/"
        if path not in added_paths and parsed.netloc in href:
            lines.append(f"- [{text}]({href})")
            added_paths.add(path)
            if len(added_paths) > 10:
                break
    
    lines.append("")
    
    # Social/Connect
    if info.social_links:
        lines.append("## Connect")
        lines.append("")
        for link in info.social_links:
            if "twitter.com" in link or "x.com" in link:
                lines.append(f"- [Twitter/X]({link})")
            elif "linkedin.com" in link:
                lines.append(f"- [LinkedIn]({link})")
            elif "github.com" in link:
                lines.append(f"- [GitHub]({link})")
            elif "facebook.com" in link:
                lines.append(f"- [Facebook]({link})")
            elif "instagram.com" in link:
                lines.append(f"- [Instagram]({link})")
            elif "youtube.com" in link:
                lines.append(f"- [YouTube]({link})")
        lines.append("")
    
    # Footer
    lines.append("---")
    lines.append(f"Generated by geo-audit • {info.domain}")
    lines.append("")
    
    return "\n".join(lines)
