"""Data Extractor — Converts page content into structured data.

Uses CSS selector-based extraction first (zero cost), falls back to
LLM-based extraction only when needed.
"""

import json
import re
from typing import Optional
from openai import AsyncOpenAI
import structlog

from app.config import get_settings

logger = structlog.get_logger()

# Known site-specific extraction rules (CSS selectors)
SITE_RULES = {
    "amazon.com": {
        "container": "div[data-component-type='s-search-result']",
        "fields": {
            "name": "h2 span.a-text-normal",
            "price": "span.a-price > span.a-offscreen",
            "rating": "span.a-icon-alt",
            "url": "h2 a.a-link-normal::attr(href)",
        }
    },
    "google.com": {
        "container": "div.g",
        "fields": {
            "title": "h3",
            "url": "a::attr(href)",
            "snippet": "div.VwiC3b",
        }
    },
}

# Schemas for LLM extraction
EXTRACTION_SCHEMAS = {
    "product": {
        "name": "Product name",
        "price": "Price as a numeric value (e.g. 1099.99) - strip currency symbols",
        "currency": "Currency code (e.g. USD, INR)",
        "rating": "Rating out of 5",
        "url": "Product URL or 'No link'",
        "gpu": "Graphics card model (e.g. RTX 4060, Integrated)",
        "cpu": "Processor model",
        "ram": "RAM amount (e.g. 16GB)",
        "storage": "Storage amount (e.g. 1TB SSD)",
        "validation_reason": "Leave empty",
    },
    "job": {
        "title": "Job title",
        "company": "Company name",
        "location": "Location",
        "salary_range": "Salary range if available",
        "url": "Job listing URL",
        "posted_date": "When posted",
    },
    "article": {
        "title": "Article title",
        "source": "Publication/website name",
        "summary": "Brief summary (1-2 sentences)",
        "url": "Article URL",
        "published_date": "Publication date",
    },
    "generic": {
        "title": "Title or heading",
        "content": "Main content",
        "url": "URL if available",
    },
}


class DataExtractor:
    """Extracts structured data from page content."""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

    def _try_deterministic(self, text: str, url: str, schema: str) -> Optional[list[dict]]:
        """Try to extract data using regex and heuristics (zero cost)."""
        # Price extraction heuristic
        if schema == "product":
            prices = re.findall(r'\$[\d,]+\.?\d*', text)
            if prices and len(prices) >= 2:
                # Simple heuristic: extract product-like blocks
                items = []
                blocks = text.split('\n\n')
                for block in blocks[:20]:
                    price_match = re.search(r'\$([\d,]+\.?\d*)', block)
                    if price_match and len(block) > 20:
                        items.append({
                            "name": block.split('\n')[0][:200],
                            "price": float(price_match.group(1).replace(',', '')),
                            "currency": "USD",
                        })
                if len(items) >= 2:
                    return items
        return None

    async def extract(self, page_content: str, schema: str = "generic",
                      url: str = "") -> list[dict]:
        """Extract structured data from page content.

        Tries deterministic extraction first, then LLM.
        """
        # Try deterministic extraction
        det_result = self._try_deterministic(page_content, url, schema)
        if det_result:
            logger.info("Deterministic extraction", items=len(det_result))
            return det_result

        # Fall back to LLM extraction
        schema_def = EXTRACTION_SCHEMAS.get(schema, EXTRACTION_SCHEMAS["generic"])

        prompt = f"""Extract structured data from this web page content.

Schema (extract these fields for each item found):
{json.dumps(schema_def, indent=2)}

Page content:
{page_content[:15000]}

Respond with JSON: {{"items": [{{...}}, ...]}}
Extract up to 10 items. If no items match, return {{"items": []}}.
"""

        response = await self.client.chat.completions.create(
            model=get_settings().openai_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        result = json.loads(content)
        items = result.get("items", [])

        logger.info("LLM extraction", items=len(items),
                     tokens=response.usage.total_tokens)
        return items
