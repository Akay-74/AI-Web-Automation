"""Data extractor — turns page text into structured rows via the LLM.

An earlier version tried a regex "fast path" first, splitting the page on blank
lines and treating anything containing a currency symbol as a product. It
short-circuited the real extraction and produced junk rows, so the LLM is now
the only path.
"""

import json

import structlog
from openai import AsyncOpenAI

from app.config import get_settings

logger = structlog.get_logger()

EXTRACTION_SCHEMAS = {
    "product": {
        "name": "Product name",
        "price": "Price as a number (e.g. 1099.99), no currency symbol",
        "currency": "Currency code (e.g. USD, INR)",
        "rating": "Rating out of 5",
        "url": "Product URL if present",
        "specs": "Key specifications as a short string",
    },
    "job": {
        "title": "Job title",
        "company": "Company name",
        "location": "Location",
        "salary_range": "Salary range if available",
        "url": "Job listing URL",
        "posted_date": "When it was posted",
    },
    "article": {
        "title": "Article title",
        "source": "Publication or website name",
        "summary": "Brief summary, 1-2 sentences",
        "url": "Article URL",
        "published_date": "Publication date",
    },
    "generic": {
        "title": "Title or heading",
        "content": "The relevant content",
        "url": "URL if available",
    },
}

_MAX_ITEMS = 20


class DataExtractor:
    """Extracts structured rows from page text."""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.model = settings.chat_model

    async def extract(self, page_content: str, schema: str = "generic", goal: str = "") -> list[dict]:
        """Extract rows matching *schema* from *page_content*."""
        settings = get_settings()
        schema_def = EXTRACTION_SCHEMAS.get(schema, EXTRACTION_SCHEMAS["generic"])

        prompt = f"""Extract structured data from this web page.

{f'The user is trying to: {goal}' if goal else ''}

Fields to extract for each item:
{json.dumps(schema_def, indent=2)}

Page content:
{page_content[:15000]}

Respond with JSON: {{"items": [{{...}}, ...]}}
Extract up to {_MAX_ITEMS} items. Omit a field when the page does not state it.
Return {{"items": []}} if the page holds nothing matching.
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=settings.max_tokens_extraction,
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        try:
            payload = json.loads(response.choices[0].message.content or "{}")
        except json.JSONDecodeError:
            logger.warning("Extraction returned malformed JSON")
            return []

        items = payload.get("items")
        if not isinstance(items, list):
            return []

        rows = [item for item in items[:_MAX_ITEMS] if isinstance(item, dict)]
        logger.info(
            "Extracted rows",
            count=len(rows),
            schema=schema,
            tokens=getattr(response.usage, "total_tokens", 0),
        )
        return rows
