import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import TimeoutError as PWTimeoutError
from playwright.sync_api import sync_playwright

load_dotenv()

STATE_PATH = "storage_state.json"
PAGE_URL = os.getenv("URL") or ""  # change
PAGE_URL_E = PAGE_URL + "/epstein"
PAGE_URL_MULTIMEDIA_SEARCH = PAGE_URL + "/multimedia-search?page=1&keys="

NO_RESULTS_RE = re.compile(r"No results found\.", re.IGNORECASE)
RESULT_RE = re.compile(
    r"^(?P<filename>.+\.pdf)\s*-\s*(?P<dataset>DataSet\s*(?:#\s*)?\d+)\s*$",
    re.IGNORECASE,
)

DEBUG_DIR = Path("pw_debug")
DEBUG_DIR.mkdir(exist_ok=True)


@dataclass(frozen=True)
class FoundItem:
    filename: str
    dataset: str


def parse_result_items(page) -> list[FoundItem]:
    items: list[FoundItem] = []
    for h3 in page.locator("#results .result-item h3").all():
        text = " ".join(h3.inner_text().split())
        m = RESULT_RE.match(text)
        if m:
            items.append(FoundItem(m.group("filename"), m.group("dataset")))
    return items


def dump_debug(page, label: str) -> None:
    png = DEBUG_DIR / f"{label}.png"
    html = DEBUG_DIR / f"{label}.html"

    page.screenshot(path=str(png), full_page=True)
    html.write_text(page.content(), encoding="utf-8")

    print(f"[debug] wrote {png} and {html}")
    print(f"[debug] url={page.url}")
    print(f"[debug] title={page.title()}")


def ensure_selectors_exist(page) -> None:
    for sel in ["#searchInput", "#searchButton", "#results"]:
        count = page.locator(sel).count()
        print(f"[debug] selector {sel} count={count}")
        if count == 0:
            dump_debug(page, f"missing_{sel.strip('#')}")
            raise RuntimeError(f"Selector not found on page: {sel}")


def wait_for_results_update(
    page, previous_signature: str, timeout_ms: int = 10_000
) -> None:
    try:
        page.wait_for_function(
            """(prev) => {
                const el = document.querySelector("#results");
                if (!el) return false;
                const now = (el.innerText || "").trim();
                return now !== prev;
            }""",
            arg=previous_signature,
            timeout=timeout_ms,
        )
    except PWTimeoutError:
        print("[debug] timed out waiting for #results to change")
        print("[debug] previous_signature:", repr(previous_signature))
        current = (
            page.locator("#results").inner_text().strip()
            if page.locator("#results").count()
            else ""
        )
        print("[debug] current_results_text:", repr(current))
        dump_debug(page, "timeout_wait_for_results_update")
        raise


def search(page, query: str) -> tuple[list[FoundItem], str]:
    results_el = page.locator("#results")
    prev = results_el.inner_text().strip() if results_el.count() else ""

    print(f"[debug] searching for: {query}")
    print(f"[debug] prev results text: {repr(prev)}")

    page.fill("#searchInput", query)
    page.click("#searchButton")

    # Some sites update via fetch/XHR; this helps stabilize in debug:
    page.wait_for_load_state("networkidle", timeout=10_000)

    wait_for_results_update(page, prev, timeout_ms=15_000)

    raw = results_el.inner_text().strip()
    print(f"[debug] raw results text: {repr(raw)}")

    items = parse_result_items(page)
    print(f"[debug] parsed items: {items}")

    return items, raw


def main() -> None:
    queries = ["EFTA00257787.pdf"]

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # headed for debugging
            slow_mo=250,
        )
        context = browser.new_context(storage_state=STATE_PATH)
        page = context.new_page()

        if not PAGE_URL:
            raise ValueError("URL env var is empty. Set URL in your .env file.")

        page.goto(PAGE_URL, wait_until="domcontentloaded")
        dump_debug(page, "loaded_page")

        ensure_selectors_exist(page)

        for q in queries:
            try:
                items, raw = search(page, q)
            except Exception as e:
                print("[debug] exception:", repr(e))
                dump_debug(page, "exception")
                raise

            if items:
                for it in items:
                    print(f"{q} -> {it.filename} | {it.dataset}")
                    with open("search_results.txt", "a", encoding="utf-8") as f:
                        f.write(
                            f"{PAGE_URL}/{it.dataset.split(' ')[0]}%20{it.dataset.split(' ')[1]}/{it.filename}\n"
                        )
            elif NO_RESULTS_RE.search(raw):
                print(f"{q} -> No results found.")
            else:
                print(f"{q} -> Unrecognized results format. Raw:\n{raw}\n")

        browser.close()


if __name__ == "__main__":
    main()
