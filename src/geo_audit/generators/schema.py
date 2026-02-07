"""Generate JSON-LD schema from page content."""

import json
import re
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup


def extract_org_name(soup: BeautifulSoup, url: str) -> str:
    """Try to extract organization name from page."""
    # Try OG site_name first (most reliable)
    og_site = soup.find("meta", property="og:site_name")
    if og_site and og_site.get("content"):
        return og_site["content"].strip()
    
    # Try title - look for the company name part
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)
        # Split on common separators
        parts = re.split(r'\s*[|–—\-\\•·]\s*', title)
        # Filter out generic words like "Home", "Welcome"
        generic_words = {"home", "welcome", "homepage", "official", "site", "website"}
        
        # Try to find the company name (usually last non-generic part, or first if only one)
        candidates = [p.strip() for p in parts if p.strip().lower() not in generic_words]
        if candidates:
            # Prefer shorter names (company names are usually concise)
            candidates.sort(key=len)
            return candidates[0]
        elif parts:
            return parts[-1].strip()
    
    # Fallback to domain
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    return domain.split(".")[0].title()


def extract_logo(soup: BeautifulSoup, url: str) -> str | None:
    """Try to find a logo URL."""
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    # Try OG image
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        img_url = og_image["content"]
        if img_url.startswith("/"):
            img_url = base_url + img_url
        return img_url
    
    # Try to find logo in header
    header = soup.find("header") or soup.find("nav")
    if header:
        img = header.find("img")
        if img and img.get("src"):
            src = img["src"]
            if src.startswith("/"):
                src = base_url + src
            return src
    
    # Try apple-touch-icon or favicon
    for rel in ["apple-touch-icon", "icon"]:
        link = soup.find("link", rel=rel)
        if link and link.get("href"):
            href = link["href"]
            if href.startswith("/"):
                href = base_url + href
            return href
    
    return None


def extract_social_links(soup: BeautifulSoup) -> list[str]:
    """Extract social media links."""
    social_patterns = [
        "twitter.com", "x.com", "linkedin.com", "facebook.com",
        "github.com", "instagram.com", "youtube.com", "wikipedia.org"
    ]
    
    links = []
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        for pattern in social_patterns:
            if pattern in href and href not in links:
                links.append(href)
                break
    
    return links[:10]


def generate_schema(soup: BeautifulSoup, url: str, schema_type: str = "Organization") -> dict[str, Any]:
    """Generate JSON-LD schema from page content.
    
    Args:
        soup: Parsed HTML
        url: Page URL
        schema_type: Type of schema to generate (Organization, WebSite, etc.)
    
    Returns:
        JSON-LD schema as dict
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    # Get basic info
    name = extract_org_name(soup, url)
    logo = extract_logo(soup, url)
    social_links = extract_social_links(soup)
    
    # Description
    desc_tag = soup.find("meta", attrs={"name": "description"})
    description = desc_tag.get("content", "") if desc_tag else ""
    if not description:
        og_desc = soup.find("meta", property="og:description")
        description = og_desc.get("content", "") if og_desc else ""
    
    if schema_type == "Organization":
        schema: dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": name,
            "url": base_url,
        }
        
        if description:
            schema["description"] = description
        
        if logo:
            schema["logo"] = logo
        
        if social_links:
            schema["sameAs"] = social_links
        
        # Add contact point placeholder
        schema["contactPoint"] = {
            "@type": "ContactPoint",
            "contactType": "customer service",
            "url": f"{base_url}/contact"
        }
        
        return schema
    
    elif schema_type == "WebSite":
        schema = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": name,
            "url": base_url,
        }
        
        if description:
            schema["description"] = description
        
        # Add search action if site likely has search
        schema["potentialAction"] = {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": f"{base_url}/search?q={{search_term_string}}"
            },
            "query-input": "required name=search_term_string"
        }
        
        return schema
    
    elif schema_type == "FAQPage":
        # Try to extract FAQ content from page
        faq_items = []
        
        # Look for FAQ-like structures (dt/dd, h3+p, etc.)
        for h in soup.find_all(["h3", "h4"]):
            question = h.get_text(strip=True)
            if "?" in question or len(question) < 100:
                # Find next paragraph as answer
                next_p = h.find_next("p")
                if next_p:
                    answer = next_p.get_text(strip=True)
                    if answer and len(answer) > 20:
                        faq_items.append({
                            "@type": "Question",
                            "name": question,
                            "acceptedAnswer": {
                                "@type": "Answer",
                                "text": answer
                            }
                        })
        
        if not faq_items:
            # Return a template
            faq_items = [
                {
                    "@type": "Question",
                    "name": f"What is {name}?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": description or f"{name} is a [description]. Visit {base_url} to learn more."
                    }
                },
                {
                    "@type": "Question",
                    "name": f"How do I get started with {name}?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": f"Visit {base_url} to get started."
                    }
                }
            ]
        
        schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": faq_items[:10]
        }
        
        return schema
    
    else:
        raise ValueError(f"Unknown schema type: {schema_type}")


def generate_all_schemas(soup: BeautifulSoup, url: str) -> list[dict[str, Any]]:
    """Generate all recommended schemas for a page."""
    return [
        generate_schema(soup, url, "Organization"),
        generate_schema(soup, url, "WebSite"),
    ]


def schema_to_html(schema: dict[str, Any]) -> str:
    """Convert schema dict to HTML script tag."""
    json_str = json.dumps(schema, indent=2, ensure_ascii=False)
    return f'<script type="application/ld+json">\n{json_str}\n</script>'
