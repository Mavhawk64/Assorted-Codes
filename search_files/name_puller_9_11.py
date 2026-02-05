import argparse
import asyncio
import json
import os
import re
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
from playwright.async_api import TimeoutError as PWTimeoutError
from playwright.async_api import async_playwright

load_dotenv()

BASE = os.getenv("URL") or "https://www.justice.gov"  # no trailing slash needed
STATE_PATH = Path("storage_state.json")

OUT_LINKS = Path("all_epstein_file_links.txt")
OUT_NAMES = Path("all_epstein_filenames.txt")

# Inclusive ranges you provided
DATASET_RANGES: dict[int, tuple[int, int]] = {
    9: (39_025, 1_262_781),
    10: (1_262_782, 2_205_654),
    11: (2_205_655, 2_730_262),
}

ACCESS_DENIED_RE = re.compile(r"access denied|you don't have permission", re.IGNORECASE)
QUEUE_RE = re.compile(r"queue-it|safetynet|please wait", re.IGNORECASE)
FILENAME_RE = re.compile(r"^EFTA(?P<num>\d{8})\.pdf$", re.IGNORECASE)

NAV_TIMEOUT_MS_DEFAULT = 30_000
RETRIES_DEFAULT = 2
CHUNK_SIZE_DEFAULT = 50
AUTH_FAILS_IN_ROW_DEFAULT = 6


def n_to_filename(n: int) -> str:
    return f"EFTA{n:08d}.pdf"


def filename_to_n(fname: str) -> int:
    m = FILENAME_RE.match(fname.strip())
    if not m:
        raise ValueError(f"Bad filename: {fname!r}")
    return int(m.group("num"))


def multimedia_url(filename: str) -> str:
    return f"{BASE}/multimedia-search?keys={filename}&page=1"


def encode_spaces(path_or_url: str) -> str:
    return quote(path_or_url, safe="/:")


def append_lines(path: Path, lines: list[str]) -> None:
    if not lines:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        for line in lines:
            f.write(line + "\n")


def load_resume(resume_path: Path) -> str | None:
    """
    Resume schema:
      { "last_pulled_file": "EFTA01234567.pdf" }
    """
    if not resume_path.exists():
        return None
    try:
        data = json.loads(resume_path.read_text(encoding="utf-8"))
        v = data.get("last_pulled_file")
        if isinstance(v, str) and v.strip():
            return v.strip()
    except Exception:
        pass
    return None


def save_resume(resume_path: Path, last_pulled_file: str) -> None:
    resume_path.write_text(
        json.dumps({"last_pulled_file": last_pulled_file}, indent=2),
        encoding="utf-8",
    )


async def extract_json_from_page(page) -> dict:
    pre = page.locator("pre")
    if await pre.count():
        text = (await pre.first.inner_text()).strip()
    else:
        text = (await page.locator("body").inner_text()).strip()
    return json.loads(text)


async def probe_one(
    page, fname: str, nav_timeout_ms: int, retries: int
) -> tuple[str | None, str | None]:
    """
    Returns (origin_or_none, error_kind_or_none)
    error_kind in {"auth","timeout","json","other", None}
    """
    url = multimedia_url(fname)
    last_body = ""

    for attempt in range(1, retries + 1):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=nav_timeout_ms)

            try:
                body = (await page.locator("body").inner_text()).strip()
            except Exception:
                body = ""
            last_body = body[:300]

            if ACCESS_DENIED_RE.search(body) or QUEUE_RE.search(body):
                return None, "auth"

            data = await extract_json_from_page(page)
            hits = data.get("hits", {}).get("hits", [])
            if not hits:
                return None, None

            origin = hits[0].get("_source", {}).get("ORIGIN_FILE_URI")
            if not origin:
                return None, None

            return encode_spaces(origin), None

        except PWTimeoutError:
            if attempt == retries:
                return None, "timeout"
        except json.JSONDecodeError:
            if ACCESS_DENIED_RE.search(last_body) or QUEUE_RE.search(last_body):
                return None, "auth"
            if attempt == retries:
                return None, "json"
        except Exception:
            return None, "other"

    return None, "other"


async def reauth_pause(context, anchor_page) -> None:
    print("\n[AUTH REQUIRED]")
    print("Fix the queue/auth in the browser window (refresh, wait, etc.).")
    print("When it works again, press Enter here.\n")
    input()
    await context.storage_state(path=str(STATE_PATH))
    print(f"[auth] Saved updated state to {STATE_PATH}.\n")
    try:
        await anchor_page.goto(
            multimedia_url("mom"),
            wait_until="domcontentloaded",
            timeout=NAV_TIMEOUT_MS_DEFAULT,
        )
    except Exception:
        pass


async def run_dataset(
    dataset: int,
    chunk_size: int,
    nav_timeout_ms: int,
    retries: int,
    auth_fails_in_row_limit: int,
) -> None:
    if dataset not in DATASET_RANGES:
        raise ValueError(
            f"dataset must be one of {sorted(DATASET_RANGES.keys())}, got {dataset}"
        )

    lo, hi = DATASET_RANGES[dataset]
    resume_path = Path(f"resume_ds{dataset}.json")

    last = load_resume(resume_path)
    if last:
        start_n = filename_to_n(last) + 1
    else:
        start_n = lo

    if start_n < lo:
        start_n = lo

    if start_n > hi:
        print(f"[ds={dataset}] already complete (resume start {start_n} > {hi}).")
        return

    print(f"=== Data Set {dataset} ===")
    print(f"[ds={dataset}] range: EFTA{lo:08d}.pdf .. EFTA{hi:08d}.pdf")
    print(f"[ds={dataset}] resuming at: EFTA{start_n:08d}.pdf")
    print(f"[ds={dataset}] resume file: {resume_path.resolve()}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=0)
        context = await browser.new_context(
            storage_state=str(STATE_PATH) if STATE_PATH.exists() else None
        )

        # Anchor tab open
        anchor = await context.new_page()
        await anchor.goto(
            multimedia_url("mom"), wait_until="domcontentloaded", timeout=nav_timeout_ms
        )

        print("Authenticate in the browser window if needed, then press Enter here.")
        input()

        await context.storage_state(path=str(STATE_PATH))
        print(f"Saved updated state to {STATE_PATH}.\n")

        checked = 0
        appended = 0
        auth_fails_in_row = 0

        n = start_n
        while n <= hi:
            chunk_end = min(n + chunk_size - 1, hi)
            nums = list(range(n, chunk_end + 1))
            fnames = [n_to_filename(x) for x in nums]

            pages = [await context.new_page() for _ in fnames]
            tasks = [
                asyncio.create_task(
                    probe_one(pg, fn, nav_timeout_ms=nav_timeout_ms, retries=retries)
                )
                for pg, fn in zip(pages, fnames)
            ]
            results = await asyncio.gather(*tasks)

            for pg in pages:
                try:
                    await pg.close()
                except Exception:
                    pass

            checked += len(fnames)

            # Build outputs
            new_links: list[str] = []
            new_names: list[str] = []

            any_auth_error = any(err == "auth" for _, err in results)
            if any_auth_error:
                auth_fails_in_row += 1
            else:
                auth_fails_in_row = 0

            if auth_fails_in_row >= auth_fails_in_row_limit:
                await reauth_pause(context, anchor)
                auth_fails_in_row = 0

            for (origin, err), fn in zip(results, fnames):
                if origin:
                    # Normalize to absolute URL
                    if origin.startswith("http"):
                        full = origin
                    else:
                        full = f"{BASE}{origin if origin.startswith('/') else '/' + origin}"
                    new_links.append(full)
                    new_names.append(fn)

            append_lines(OUT_LINKS, new_links)
            append_lines(OUT_NAMES, new_names)

            appended += len(new_links)

            # Resume: store LAST attempted file in this chunk (simple, robust)
            save_resume(resume_path, fnames[-1])

            print(
                f"[ds={dataset}] {fnames[0]}..{fnames[-1]} "
                f"checked={checked:,} appended={appended:,} "
                f"(resume last={fnames[-1]})"
            )

            n = chunk_end + 1

        print(f"\n[ds={dataset}] DONE. checked={checked:,} appended={appended:,}")
        print(f"[ds={dataset}] Outputs appended to:")
        print(f"  - {OUT_LINKS.resolve()}")
        print(f"  - {OUT_NAMES.resolve()}")
        print(f"[ds={dataset}] Resume saved at: {resume_path.resolve()}")
        print("\nPress Enter to close the browser...")
        input()
        await browser.close()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dataset",
        type=int,
        required=True,
        choices=[9, 10, 11],
        help="Dataset number: 9, 10, or 11",
    )
    ap.add_argument("--chunk-size", type=int, default=CHUNK_SIZE_DEFAULT)
    ap.add_argument("--timeout-ms", type=int, default=NAV_TIMEOUT_MS_DEFAULT)
    ap.add_argument("--retries", type=int, default=RETRIES_DEFAULT)
    ap.add_argument(
        "--auth-fails",
        type=int,
        default=AUTH_FAILS_IN_ROW_DEFAULT,
        help="Pause for re-auth after this many auth-like chunks in a row",
    )
    return ap.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        run_dataset(
            dataset=args.dataset,
            chunk_size=args.chunk_size,
            nav_timeout_ms=args.timeout_ms,
            retries=args.retries,
            auth_fails_in_row_limit=args.auth_fails,
        )
    )
