"""Page Analyzer — Converts raw HTML into simplified representations for the agent.

Strips unnecessary content, extracts visible text, identifies interactive
elements, and creates compressed page summaries to minimize LLM token usage.
"""

from bs4 import BeautifulSoup
import structlog

logger = structlog.get_logger()


class PageAnalyzer:
    """Analyzes web page content for the agent."""

    REMOVE_TAGS = {"script", "style", "noscript", "svg", "path", "meta", "link", "head"}

    def analyze(self, html: str) -> dict:
        """Convert HTML to a structured page representation."""
        soup = BeautifulSoup(html, "lxml")

        # Remove non-content tags
        for tag in soup.find_all(self.REMOVE_TAGS):
            tag.decompose()

        # Extract visible text (compressed)
        text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        visible_text = "\n".join(lines)

        # Extract links
        links = []
        for a in soup.find_all("a", href=True)[:30]:
            links.append({
                "text": a.get_text(strip=True)[:100],
                "href": a["href"],
            })

        # Extract forms
        forms = []
        for form in soup.find_all("form")[:5]:
            inputs = []
            for inp in form.find_all(["input", "textarea", "select"]):
                inputs.append({
                    "type": inp.get("type", "text"),
                    "name": inp.get("name", ""),
                    "id": inp.get("id", ""),
                    "placeholder": inp.get("placeholder", ""),
                })
            forms.append({"action": form.get("action", ""), "inputs": inputs})

        # Extract headings for structure
        headings = []
        for h in soup.find_all(["h1", "h2", "h3"])[:15]:
            headings.append({"level": h.name, "text": h.get_text(strip=True)[:150]})

        # Extract images with alt text
        images = []
        for img in soup.find_all("img", alt=True)[:10]:
            if img["alt"].strip():
                images.append({"alt": img["alt"][:100], "src": img.get("src", "")})

        result = {
            "visible_text": visible_text[:8000],  # Cap for token efficiency
            "links": links,
            "forms": forms,
            "headings": headings,
            "images": images,
            "text_length": len(visible_text),
        }

        logger.info("Page analyzed", text_len=len(visible_text),
                     links=len(links), forms=len(forms))
        return result

    def create_summary(self, analysis: dict, max_chars: int = 2000) -> str:
        """Create a compressed text summary for LLM context."""
        parts = []

        if analysis.get("headings"):
            parts.append("## Page Structure")
            for h in analysis["headings"]:
                parts.append(f"  {h['level']}: {h['text']}")

        if analysis.get("forms"):
            parts.append("\n## Forms")
            for form in analysis["forms"]:
                inputs = ", ".join(i["name"] or i["placeholder"] or i["type"]
                                   for i in form["inputs"])
                parts.append(f"  Form: {inputs}")

        parts.append(f"\n## Content Preview\n{analysis['visible_text'][:1000]}")

        summary = "\n".join(parts)
        return summary[:max_chars]
