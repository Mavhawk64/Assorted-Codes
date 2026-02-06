# name_puller_9_11.py
#
# Usage:
#   python name_puller_9_11.py --dataset=9
#   python name_puller_9_11.py --dataset=10
#   python name_puller_9_11.py --dataset=11
#
# Notes:
# - A "VALID" response is ONLY when the loaded page body is JSON AND has:
#     data["hits"] as a dict AND data["hits"]["hits"] as a list (possibly empty)
#   Examples:
#     Empty case: {"hits": {"hits": []}, ...}  -> VALID (no hit)
#     Valid case: {"hits": {"hits": [ ... ]}, ...} -> VALID (hit)
# - Anything else (HTML gate, bot check, access denied, queue) is INVALID -> "auth"
# - When too many "auth-like" chunks occur in a row, we pause for manual re-auth.

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

# Soft heuristics (fast path) — NOT authoritative by themselves
ACCESS_DENIED_RE = re.compile(r"access denied|you don't have permission", re.IGNORECASE)
QUEUE_RE = re.compile(r"queue-it|safetynet|please wait", re.IGNORECASE)

FILENAME_RE = re.compile(r"^EFTA(?P<num>\d{8})\.pdf$", re.IGNORECASE)

NAV_TIMEOUT_MS_DEFAULT = 30_000
RETRIES_DEFAULT = 2
CHUNK_SIZE_DEFAULT = 50

# Number of consecutive "auth-like chunks" before pausing for manual re-auth.
AUTH_FAILS_IN_ROW_DEFAULT = 4

# When determining whether a chunk is "auth-like", require at least this many auth
# results within the chunk (prevents pausing due to 1-2 random tab glitches).
AUTH_MIN_IN_CHUNK_DEFAULT = 10

# Also require this fraction of the chunk to be auth-like before counting it.
AUTH_FRACTION_IN_CHUNK_DEFAULT = 0.5


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
    # Convert spaces to %20 without breaking slashes/colons
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


async def extract_text_payload(page) -> str:
    """
    DOJ JSON responses are often rendered as a document with either <pre> or body text.
    This extracts the visible JSON string (or HTML text if blocked).
    """
    pre = page.locator("pre")
    if await pre.count():
        return (await pre.first.inner_text()).strip()
    return (await page.locator("body").inner_text()).strip()


def is_valid_multimedia_json(data: object) -> bool:
    """
    VALID if and only if:
      - top-level is dict
      - has key "hits" with dict value
      - hits has key "hits" with list value (may be empty)
    """
    if not isinstance(data, dict):
        return False
    hits_obj = data.get("hits")
    if not isinstance(hits_obj, dict):
        return False
    hits_list = hits_obj.get("hits")
    if not isinstance(hits_list, list):
        return False
    return True


async def parse_search_json_or_invalid(page) -> tuple[dict | None, str | None, str]:
    """
    Returns:
      (data, None, payload_head)        -> VALID multimedia-search JSON schema
      (None, "auth", payload_head)      -> INVALID (gate/bot/unauthorized/HTML/other JSON schema)
    """
    text = await extract_text_payload(page)
    head = text[:500]

    # Fast-path hints (not authoritative alone)
    if ACCESS_DENIED_RE.search(head) or QUEUE_RE.search(head):
        return None, "auth", head

    # Must be JSON
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None, "auth", head

    # Must match schema (hits object present)
    if not is_valid_multimedia_json(data):
        return None, "auth", head

    return data, None, head


async def probe_one(
    page, fname: str, nav_timeout_ms: int, retries: int
) -> tuple[str | None, str | None]:
    """
    Returns (origin_or_none, error_kind_or_none)
    error_kind in {"auth","timeout","other", None}
    """
    url = multimedia_url(fname)

    for attempt in range(1, retries + 1):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=nav_timeout_ms)

            data, err, _head = await parse_search_json_or_invalid(page)
            if err == "auth":
                return None, "auth"
            if data is None:
                return None, "other"

            hits = data["hits"]["hits"]
            if not hits:
                return None, None

            origin = hits[0].get("_source", {}).get("ORIGIN_FILE_URI")
            if not origin:
                return None, None

            return encode_spaces(origin), None

        except PWTimeoutError:
            if attempt == retries:
                return None, "timeout"
        except Exception:
            if attempt == retries:
                return None, "other"

    return None, "other"


async def reauth_pause(context, anchor_page) -> None:
    print("\n[AUTH REQUIRED]")
    print("Fix the queue/auth in the browser window (refresh, wait, bot-check, etc.).")
    print(
        "When a /multimedia-search?keys=mom&page=1 page shows JSON, press Enter here.\n"
    )
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
    auth_min_in_chunk: int,
    auth_fraction_in_chunk: float,
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

    start_n = max(start_n, lo)

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
        auth_like_chunks_in_row = 0

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

            auth_count = sum(1 for _, err in results if err == "auth")
            auth_frac = auth_count / max(1, len(results))
            is_auth_like_chunk = (auth_count >= auth_min_in_chunk) and (
                auth_frac >= auth_fraction_in_chunk
            )

            if is_auth_like_chunk:
                auth_like_chunks_in_row += 1
            else:
                auth_like_chunks_in_row = 0

            if auth_like_chunks_in_row >= auth_fails_in_row_limit:
                await reauth_pause(context, anchor)
                auth_like_chunks_in_row = 0

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

            # Resume: store LAST attempted file in this chunk
            save_resume(resume_path, fnames[-1])

            print(
                f"[ds={dataset}] {fnames[0]}..{fnames[-1]} "
                f"checked={checked:,} appended={appended:,} "
                f"auth_in_chunk={auth_count}/{len(results)} "
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
    ap.add_argument(
        "--auth-min-in-chunk",
        type=int,
        default=AUTH_MIN_IN_CHUNK_DEFAULT,
        help="Minimum auth results inside a chunk to treat the chunk as auth-like",
    )
    ap.add_argument(
        "--auth-frac-in-chunk",
        type=float,
        default=AUTH_FRACTION_IN_CHUNK_DEFAULT,
        help="Minimum fraction of auth results inside a chunk to treat the chunk as auth-like",
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
            auth_min_in_chunk=args.auth_min_in_chunk,
            auth_fraction_in_chunk=args.auth_frac_in_chunk,
        )
    )
