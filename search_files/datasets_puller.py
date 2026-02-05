import asyncio
import json
import re
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import TimeoutError as PWTimeoutError
from playwright.async_api import async_playwright

BASE = "https://www.justice.gov"

OUT_LINKS = Path("all_epstein_file_links.txt")
OUT_NAMES = Path("all_epstein_filenames.txt")
STATE_PATH = Path("storage_state.json")
RESUME_PATH = Path("resume_state.json")

YES_TEXT_RE = re.compile(r"^Yes$", re.IGNORECASE)
FILENAME_RE = re.compile(r"^EFTA(?P<num>\d{8})\.pdf$", re.IGNORECASE)
DATASET_RE = re.compile(r"/DataSet(?:%20|\s)(?P<ds>\d{1,2})/", re.IGNORECASE)

# Your confirmed last pages (inclusive)
LAST_PAGES: dict[int, int] = {
    1: 63,
    2: 11,
    3: 1,
    4: 3,
    5: 2,
    6: 0,
    7: 0,
    8: 220,
    12: 2,
}

# Throttle / rate-limit handling
EMPTY_RETRIES = 4
EMPTY_BACKOFF_S = [2, 5, 12, 25]  # len should be >= EMPTY_RETRIES
PAGE_DELAY_MS = 75  # set 0 to disable; 50-150 helps avoid temporary blocks

NAV_TIMEOUT_MS = 30_000


def dataset_page_url(dataset_i: int, page: int) -> str:
    return f"{BASE}/epstein/doj-disclosures/data-set-{dataset_i}-files?page={page}"


def append_lines(path: Path, lines: list[str]) -> None:
    if not lines:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        for line in lines:
            f.write(line + "\n")


def extract_dataset_num(full_url: str) -> int | None:
    m = DATASET_RE.search(full_url)
    if not m:
        return None
    try:
        return int(m.group("ds"))
    except Exception:
        return None


def extract_efta_num(filename: str) -> int | None:
    m = FILENAME_RE.match(filename.strip())
    if not m:
        return None
    try:
        return int(m.group("num"))
    except Exception:
        return None


def load_resume_state() -> tuple[int, int]:
    """
    Returns (dataset, next_page_to_process).
    If no resume file exists, start at the earliest dataset, page 0.
    """
    if not RESUME_PATH.exists():
        ds0 = min(LAST_PAGES.keys())
        return ds0, 0

    data = json.loads(RESUME_PATH.read_text(encoding="utf-8"))
    ds = int(data.get("dataset", min(LAST_PAGES.keys())))
    next_page = int(data.get("next_page", 0))
    return ds, next_page


def save_resume_state(dataset: int, next_page: int) -> None:
    """
    Persist where to resume next time.
    next_page is the next page index to attempt for the given dataset.
    """
    RESUME_PATH.write_text(
        json.dumps({"dataset": dataset, "next_page": next_page}, indent=2),
        encoding="utf-8",
    )


def advance_to_next_dataset(current_ds: int) -> int | None:
    ds_sorted = sorted(LAST_PAGES.keys())
    try:
        idx = ds_sorted.index(current_ds)
    except ValueError:
        return None
    if idx + 1 >= len(ds_sorted):
        return None
    return ds_sorted[idx + 1]


async def maybe_accept_age_gate(page) -> None:
    btn = page.get_by_role("button", name=YES_TEXT_RE)
    if await btn.count():
        try:
            await btn.first.click()
            await page.wait_for_timeout(300)
        except Exception:
            pass


async def extract_item_list_hrefs(page) -> list[str]:
    loc = page.locator("div.item-list a[href]")
    count = await loc.count()
    if count == 0:
        return []
    hrefs: list[str] = []
    for i in range(count):
        href = await loc.nth(i).get_attribute("href")
        if href:
            hrefs.append(href.strip())
    return hrefs


def hrefs_to_urls_and_names(hrefs: list[str]) -> tuple[list[str], list[str]]:
    urls: list[str] = []
    names: list[str] = []
    for h in hrefs:
        full = urljoin(BASE, h)
        urls.append(full)

        fname = full.rsplit("/", 1)[-1]
        if FILENAME_RE.match(fname):
            names.append(fname)
    return urls, names


async def manual_auth_once(page, context) -> None:
    await page.goto(
        dataset_page_url(1, 0), wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS
    )
    await maybe_accept_age_gate(page)

    print("Authenticate in the opened browser window (click Yes / any prompts).")
    print("When the page shows the file list, come back here and press Enter...\n")
    input()

    await context.storage_state(path=str(STATE_PATH))
    print(f"Saved session state to {STATE_PATH}.\n")


async def goto_with_retry(page, url: str) -> None:
    for attempt in range(1, 4):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
            return
        except PWTimeoutError:
            if attempt == 3:
                raise
            await page.wait_for_timeout(750 * attempt)


async def get_hrefs_with_backoff(page, ds: int, pageno: int) -> list[str]:
    url = dataset_page_url(ds, pageno)

    for i in range(EMPTY_RETRIES + 1):
        await goto_with_retry(page, url)
        await maybe_accept_age_gate(page)

        hrefs = await extract_item_list_hrefs(page)
        if hrefs:
            return hrefs

        if i < EMPTY_RETRIES:
            wait_s = EMPTY_BACKOFF_S[min(i, len(EMPTY_BACKOFF_S) - 1)]
            print(
                f"[rate-limit?] ds={ds} page={pageno} empty; retry {i + 1}/{EMPTY_RETRIES} in {wait_s}s"
            )
            await page.wait_for_timeout(int(wait_s * 1000))
        else:
            print(f"[blocked] ds={ds} page={pageno} still empty after retries.")
            print("Let it cool down in the browser. Press Enter here to resume...")
            input()

    return []


async def main() -> None:
    # NOTE: This is resume-aware. We do NOT clear outputs automatically.
    # If you want a fresh run, delete the output files and resume_state.json manually.

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=0)
        context = await browser.new_context(
            storage_state=str(STATE_PATH) if STATE_PATH.exists() else None
        )
        page = await context.new_page()

        await manual_auth_once(page, context)

        # Load already-written links/names into memory so we can de-dupe across restarts
        seen_urls: set[str] = set()
        seen_names: set[str] = set()

        if OUT_LINKS.exists():
            for line in OUT_LINKS.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    seen_urls.add(line)

        if OUT_NAMES.exists():
            for line in OUT_NAMES.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    seen_names.add(line)

        # Latest tracking (optional)
        latest_dataset_seen: int | None = None
        latest_filename_num: int = -1
        latest_filename_seen: str | None = None
        latest_url_seen: str | None = None

        resume_ds, resume_next_page = load_resume_state()
        print(f"[resume] Starting at dataset={resume_ds}, next_page={resume_next_page}")

        ds_sorted = sorted(LAST_PAGES.keys())

        for ds in ds_sorted:
            if ds < resume_ds:
                continue

            last_page = LAST_PAGES[ds]
            start_page = resume_next_page if ds == resume_ds else 0

            print(f"=== Data Set {ds} (pages {start_page}..{last_page}) ===")

            for pageno in range(start_page, last_page + 1):
                hrefs = await get_hrefs_with_backoff(page, ds, pageno)
                if not hrefs:
                    print(f"[warn] ds={ds} page={pageno}: no items (skipping)")
                    # Still advance resume to avoid being stuck forever on a flaky page
                    save_resume_state(ds, pageno + 1)
                    continue

                urls, names = hrefs_to_urls_and_names(hrefs)

                new_urls = [u for u in urls if u not in seen_urls]
                new_names = [n for n in names if n not in seen_names]

                for u in new_urls:
                    seen_urls.add(u)
                    ds_num = extract_dataset_num(u)
                    if ds_num is not None:
                        latest_dataset_seen = ds_num

                    fname = u.rsplit("/", 1)[-1]
                    nnum = extract_efta_num(fname)
                    if nnum is not None and nnum > latest_filename_num:
                        latest_filename_num = nnum
                        latest_filename_seen = fname
                        latest_url_seen = u

                for n in new_names:
                    seen_names.add(n)

                append_lines(OUT_LINKS, new_urls)
                append_lines(OUT_NAMES, new_names)

                # Critical: persist where to continue next time
                save_resume_state(ds, pageno + 1)

                latest_str = (
                    f"latest_ds={latest_dataset_seen} latest_file={latest_filename_seen}"
                    if latest_filename_seen
                    else "latest_file=?"
                )
                print(f"[ds={ds}] page={pageno} new={len(new_urls)} {latest_str}")

                if PAGE_DELAY_MS:
                    await page.wait_for_timeout(PAGE_DELAY_MS)

            # Finished this dataset: advance resume to the next dataset, page 0
            next_ds = advance_to_next_dataset(ds)
            if next_ds is not None:
                save_resume_state(next_ds, 0)

            print()

        print("Done.")
        print(f"Wrote/updated links at: {OUT_LINKS.resolve()}")
        print(f"Wrote/updated names at: {OUT_NAMES.resolve()}")
        print(f"Session state saved at: {STATE_PATH.resolve()}")
        print(f"Resume state saved at: {RESUME_PATH.resolve()}")

        if latest_filename_seen:
            print("\nLatest observed in THIS RUN:")
            print(f"  dataset: {latest_dataset_seen}")
            print(f"  file:    {latest_filename_seen} (#{latest_filename_num})")
            print(f"  url:     {latest_url_seen}")

        print("\nPress Enter to close...")
        input()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
