import asyncio
import json
import os
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
from playwright.async_api import TimeoutError as PWTimeoutError
from playwright.async_api import async_playwright

load_dotenv()

BASE = os.getenv("URL") or ""  # e.g. https://host (no trailing slash)
STATE_PATH = "storage_state.json"
OUT_PATH = Path("valid_files.txt")

START_N = 1
try:
    last = None
    with open("valid_files.txt", "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
                last = s
    if last and "EFTA" in last:
        temp_n = int(last.split("EFTA", 1)[1].split(".pdf", 1)[0])
        START_N = temp_n + 1
        print(f"Resuming from N={START_N} (EFTA{START_N:08d}.pdf)")
except Exception:
    pass

MAX_N = 2_731_529  # EFTA02731529.pdf -> 2,731,529
CHUNK_SIZE = 50  # open this many tabs at a time
NAV_TIMEOUT_MS = 30_000
RETRIES = 2
PRINT_EVERY_CHUNKS = 1


def n_to_filename(n: int) -> str:
    return f"EFTA{n:08d}.pdf"


def fname_to_n(fname: str) -> int:
    return int(fname.split("EFTA", 1)[1].split(".pdf", 1)[0])


def multimedia_url(filename: str) -> str:
    return f"{BASE}/multimedia-search?keys={filename}&page=1"


def encode_spaces(path_or_url: str) -> str:
    return quote(path_or_url, safe="/:")


async def extract_json_from_page(page) -> dict:
    pre = page.locator("pre")
    if await pre.count():
        text = (await pre.first.inner_text()).strip()
    else:
        text = (await page.locator("body").inner_text()).strip()
    return json.loads(text)


async def probe_one(page, fname: str) -> str | None:
    url = multimedia_url(fname)

    for attempt in range(1, RETRIES + 1):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
            data = await extract_json_from_page(page)

            hits = data.get("hits", {}).get("hits", [])
            if not hits:
                return None

            _source = hits[0].get("_source", {})
            origin = _source.get("ORIGIN_FILE_URI")
            if not origin:
                return None
            return encode_spaces(origin)

        except (PWTimeoutError, json.JSONDecodeError):
            if attempt == RETRIES:
                return None
        except Exception:
            return None

    return None


def append_lines(path: Path, lines: list[str]) -> None:
    if not lines:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        for line in lines:
            f.write(line + "\n")


async def main() -> None:
    if not BASE:
        raise ValueError("URL env var is empty. Set URL in your .env file.")

    start_n = START_N

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=0)

        context = await browser.new_context(
            storage_state=STATE_PATH if os.path.exists(STATE_PATH) else None
        )

        # Keep "mom" (anchor/auth) tab open at all times
        anchor = await context.new_page()
        await anchor.goto(multimedia_url("mom"), wait_until="domcontentloaded")

        print(
            "Authenticate in the browser window. When done, come back here and press Enter."
        )
        input()

        await context.storage_state(path=STATE_PATH)
        print(f"Saved updated state to {STATE_PATH}.")

        chunk_index = 0
        checked = 0
        found = 0

        for chunk_start in range(start_n, MAX_N + 1, CHUNK_SIZE):
            chunk_index += 1
            chunk_end = min(chunk_start + CHUNK_SIZE - 1, MAX_N)
            nums = list(range(chunk_start, chunk_end + 1))
            fnames = [n_to_filename(n) for n in nums]

            # Open CHUNK_SIZE tabs for this chunk
            pages = [await context.new_page() for _ in fnames]

            tasks = [
                asyncio.create_task(probe_one(pg, fn)) for pg, fn in zip(pages, fnames)
            ]
            results = await asyncio.gather(*tasks)

            for pg in pages:
                try:
                    await pg.close()
                except Exception:
                    pass

            checked += len(fnames)

            hits = [r for r in results if r]
            found += len(hits)
            append_lines(OUT_PATH, hits)

            if chunk_index % PRINT_EVERY_CHUNKS == 0:
                print(
                    f"[chunk {chunk_index}] "
                    f"{n_to_filename(chunk_start)}..{n_to_filename(chunk_end)} "
                    f"checked={checked:,} found={found:,} appended={len(hits)}"
                )

        print(f"\nDone. checked={checked:,} found={found:,}")
        print(f"Results appended to: {OUT_PATH}")

        print("Press Enter to close the browser...")
        input()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
