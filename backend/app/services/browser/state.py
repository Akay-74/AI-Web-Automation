"""Normalized browser state — the single description of what the page is now.

The agent re-reads this before every decision, so a page the human navigated
by hand is described the same way as one the agent navigated itself.
"""

from typing import Optional

from pydantic import BaseModel, Field


class TabInfo(BaseModel):
    """Metadata for a single browser tab."""
    tab_id: int
    title: str = ""
    url: str = ""
    active: bool = False


class InteractiveElement(BaseModel):
    """One interactive element, addressable by ``element_id``."""
    element_id: int
    tag: str  # button, a, input, textarea, select, ...
    role: Optional[str] = None  # ARIA role
    name: str = ""  # Accessible name or text content
    type: Optional[str] = None  # input type (text, password, submit, ...)
    value: Optional[str] = None
    placeholder: Optional[str] = None
    href: Optional[str] = None
    selector: str = ""  # CSS selector, used for execution only
    enabled: bool = True


class PageStructure(BaseModel):
    """Headings and visible text, so the agent can read as well as click."""
    headings: list[dict] = Field(default_factory=list)
    text_preview: str = ""
    links_count: int = 0
    images_count: int = 0


class BrowserState(BaseModel):
    """What the browser looks like right now."""
    active_tab: int = 0
    open_tabs: list[TabInfo] = Field(default_factory=list)
    current_url: str = ""
    page_title: str = ""
    page_structure: Optional[PageStructure] = None
    interactive_elements: list[InteractiveElement] = Field(default_factory=list)

    def element_by_id(self, element_id: int) -> Optional[InteractiveElement]:
        for el in self.interactive_elements:
            if el.element_id == element_id:
                return el
        return None

    def summary_for_llm(self, max_elements: int = 100, max_chars: int = 6000) -> str:
        """Compact text description for the planner prompt."""
        parts = [
            f"URL: {self.current_url or 'about:blank'}",
            f"Title: {self.page_title}",
        ]
        if len(self.open_tabs) > 1:
            tabs = ", ".join(
                f"[{t.tab_id}]{'*' if t.active else ''} {t.title[:40]}"
                for t in self.open_tabs
            )
            parts.append(f"Tabs: {tabs}  (* = active)")

        if self.interactive_elements:
            shown = self.interactive_elements[:max_elements]
            parts.append(f"\n## Interactive elements ({len(shown)} of {len(self.interactive_elements)})")
            parts.extend(_describe_element(el) for el in shown)

        ps = self.page_structure
        if ps:
            if ps.headings:
                parts.append("\n## Headings")
                parts.extend(f"  {h.get('level', 'h?')}: {h.get('text', '')[:100]}" for h in ps.headings[:10])
            if ps.text_preview:
                parts.append(f"\n## Visible text\n{ps.text_preview[:2500]}")

        return "\n".join(parts)[:max_chars]


def _describe_element(el: InteractiveElement) -> str:
    desc = f"  [{el.element_id}] <{el.tag}"
    if el.role:
        desc += f' role="{el.role}"'
    if el.type:
        desc += f' type="{el.type}"'
    desc += ">"
    if el.name:
        desc += f' "{el.name[:80]}"'
    if el.placeholder:
        desc += f' placeholder="{el.placeholder[:40]}"'
    if el.value:
        desc += f' value="{el.value[:30]}"'
    if el.href and el.tag == "a":
        desc += f" href={el.href[:60]}"
    if not el.enabled:
        desc += " [disabled]"
    return desc
