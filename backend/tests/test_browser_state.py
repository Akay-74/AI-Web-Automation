"""Browser state rendering.

The page summary is the planner's only view of the page, and the element ids in
it are the only targets it may use, so those ids have to appear and have to
resolve back.
"""

from app.config import Settings
from app.services.browser.state import (
    BrowserState,
    InteractiveElement,
    PageStructure,
    TabInfo,
)


def make_state() -> BrowserState:
    return BrowserState(
        current_url="https://www.example.com/search?q=laptop",
        page_title="Laptops — Example",
        interactive_elements=[
            InteractiveElement(
                element_id=0,
                tag="input",
                type="text",
                name="Search",
                placeholder="Search products",
                selector="#search-box",
            ),
            InteractiveElement(
                element_id=1,
                tag="button",
                name="Submit search",
                selector="#search-submit",
            ),
            InteractiveElement(
                element_id=2,
                tag="a",
                name="Cheap Laptop 15",
                href="/product/123",
                selector="#result-1 > a",
                enabled=False,
            ),
        ],
        page_structure=PageStructure(
            headings=[{"level": "h1", "text": "Results for laptop"}],
            text_preview="Cheap Laptop 15 — $499.00\nAnother Laptop — $899.00",
        ),
    )


def test_summary_lists_every_element_id():
    summary = make_state().summary_for_llm()

    assert "[0]" in summary
    assert "[1]" in summary
    assert "[2]" in summary
    assert "Submit search" in summary
    assert "placeholder=\"Search products\"" in summary


def test_summary_includes_url_title_and_page_text():
    summary = make_state().summary_for_llm()

    assert "https://www.example.com/search?q=laptop" in summary
    assert "Laptops — Example" in summary
    assert "Results for laptop" in summary
    assert "$499.00" in summary


def test_summary_marks_disabled_elements():
    assert "[disabled]" in make_state().summary_for_llm()


def test_summary_caps_the_element_count():
    state = BrowserState(
        interactive_elements=[
            InteractiveElement(element_id=i, tag="button", name=f"Button {i}")
            for i in range(300)
        ]
    )
    summary = state.summary_for_llm(max_elements=10)

    assert "10 of 300" in summary
    assert "Button 9" in summary
    assert "Button 10" not in summary


def test_summary_respects_the_character_budget():
    state = BrowserState(
        page_structure=PageStructure(text_preview="x" * 50_000),
        interactive_elements=[
            InteractiveElement(element_id=i, tag="a", name="y" * 90) for i in range(200)
        ],
    )
    assert len(state.summary_for_llm(max_chars=4000)) <= 4000


def test_summary_lists_tabs_only_when_there_are_several():
    one_tab = BrowserState(open_tabs=[TabInfo(tab_id=0, title="Only", active=True)])
    assert "Tabs:" not in one_tab.summary_for_llm()

    two_tabs = BrowserState(open_tabs=[
        TabInfo(tab_id=0, title="First", active=True),
        TabInfo(tab_id=1, title="Second"),
    ])
    summary = two_tabs.summary_for_llm()
    assert "Tabs:" in summary
    assert "First" in summary and "Second" in summary


def test_blank_page_is_described_as_such():
    assert "about:blank" in BrowserState().summary_for_llm()


def test_element_lookup_by_id():
    state = make_state()
    assert state.element_by_id(1).name == "Submit search"
    assert state.element_by_id(99) is None


def test_openrouter_model_ids_get_namespaced():
    settings = Settings(
        openai_base_url="https://openrouter.ai/api/v1",
        openai_model="gpt-4o-mini",
    )
    assert settings.chat_model == "openai/gpt-4o-mini"


def test_already_namespaced_model_is_left_alone():
    settings = Settings(
        openai_base_url="https://openrouter.ai/api/v1",
        openai_model="anthropic/claude-sonnet-4",
    )
    assert settings.chat_model == "anthropic/claude-sonnet-4"


def test_plain_openai_model_is_left_alone():
    settings = Settings(
        openai_base_url="https://api.openai.com/v1",
        openai_model="gpt-4o-mini",
    )
    assert settings.chat_model == "gpt-4o-mini"


def test_cors_origins_parse_to_a_list():
    settings = Settings(cors_origins="http://localhost:3000, http://127.0.0.1:3000")
    assert settings.cors_origin_list == ["http://localhost:3000", "http://127.0.0.1:3000"]
