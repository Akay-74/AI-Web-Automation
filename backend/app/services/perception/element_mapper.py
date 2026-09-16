"""Element mapper — assigns ``element_id`` to every interactive element.

The planner never writes a CSS selector. It picks an ``element_id`` off the
list this module produced from the real page, and the mapper resolves that id
back to a selector at execution time. A model cannot hallucinate an id that
is not on the page it was just shown.
"""

from typing import Optional

import structlog

from app.services.browser.state import InteractiveElement

logger = structlog.get_logger()

_MAX_ELEMENTS = 200

_EXTRACT_ELEMENTS_JS = """(maxElements) => {
    const selectors = [
        'a[href]', 'button', 'input', 'textarea', 'select',
        '[role="button"]', '[role="link"]', '[role="tab"]', '[role="menuitem"]',
        '[role="checkbox"]', '[role="radio"]', '[role="combobox"]',
        '[role="searchbox"]', '[role="textbox"]',
        '[contenteditable="true"]', 'summary',
    ];

    const elements = [];
    const seen = new Set();
    let id = 0;

    for (const sel of selectors) {
        for (const el of document.querySelectorAll(sel)) {
            if (seen.has(el)) continue;
            seen.add(el);

            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) continue;
            const style = getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;

            const name = (el.getAttribute('aria-label')
                || el.getAttribute('title')
                || el.getAttribute('alt')
                || el.getAttribute('placeholder')
                || (el.innerText || '').trim()
                || el.value
                || '').slice(0, 100);

            let selector = '';
            if (el.id) {
                selector = '#' + CSS.escape(el.id);
            } else if (el.getAttribute('data-testid')) {
                selector = `[data-testid="${CSS.escape(el.getAttribute('data-testid'))}"]`;
            } else if (el.getAttribute('name')) {
                selector = `${el.tagName.toLowerCase()}[name="${CSS.escape(el.getAttribute('name'))}"]`;
            } else if (el.getAttribute('aria-label')) {
                selector = `[aria-label="${CSS.escape(el.getAttribute('aria-label'))}"]`;
            } else {
                // Structural path, stopping at the nearest id'd ancestor.
                const path = [];
                let node = el;
                while (node && node !== document.body) {
                    if (node.id) {
                        path.unshift('#' + CSS.escape(node.id));
                        break;
                    }
                    let seg = node.tagName.toLowerCase();
                    const parent = node.parentElement;
                    if (parent) {
                        const twins = Array.from(parent.children).filter(c => c.tagName === node.tagName);
                        if (twins.length > 1) seg += `:nth-of-type(${twins.indexOf(node) + 1})`;
                    }
                    path.unshift(seg);
                    node = parent;
                }
                selector = path.join(' > ');
            }

            elements.push({
                element_id: id++,
                tag: el.tagName.toLowerCase(),
                role: el.getAttribute('role') || null,
                name: name,
                type: el.getAttribute('type') || null,
                value: (el.value || '').slice(0, 100) || null,
                placeholder: el.getAttribute('placeholder') || null,
                href: (el.getAttribute('href') || '').slice(0, 200) || null,
                selector: selector,
                enabled: !el.disabled,
            });

            if (elements.length >= maxElements) return elements;
        }
    }

    return elements;
}"""


class ElementMapper:
    """Maps page elements to stable ids for the current page."""

    def __init__(self):
        self._elements: list[InteractiveElement] = []
        self._by_id: dict[int, InteractiveElement] = {}

    async def map_elements(self, page) -> list[InteractiveElement]:
        """Re-read the interactive elements of the current page."""
        try:
            raw_elements = await page.evaluate(_EXTRACT_ELEMENTS_JS, _MAX_ELEMENTS)
        except Exception as e:
            logger.warning("Element mapping failed", error=str(e)[:200])
            return []

        self._elements = [InteractiveElement(**raw) for raw in raw_elements]
        self._by_id = {el.element_id: el for el in self._elements}
        logger.info("Elements mapped", count=len(self._elements))
        return self._elements

    def get(self, element_id: int) -> Optional[InteractiveElement]:
        """Return the mapped element, or None if that id is not on this page."""
        return self._by_id.get(element_id)

    def resolve(self, element_id: int) -> Optional[str]:
        """Return the CSS selector for an ``element_id``."""
        el = self._by_id.get(element_id)
        return el.selector if el else None
