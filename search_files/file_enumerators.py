import os

DATASET_RANGES: dict[int, tuple[int, int]] = {
    9: (39_025, 1_262_781),
    10: (1_262_782, 2_205_654),
    11: (2_205_655, 2_730_262),
}

unverified_files = [
    {
        "url": f"https://www.justice.gov/epstein/files/DataSet%20{j}/EFTA{i:08d}.pdf",
        "verified": False,
    }
    for j in DATASET_RANGES
    for i in range(DATASET_RANGES[j][0], DATASET_RANGES[j][1] + 1)
]

with open(
    os.path.join(os.path.dirname(__file__), "all_epstein_file_links.txt"),
    "r",
    encoding="utf-8",
) as f:
    verified_files = [
        {"url": line.strip(), "verified": True}
        for line in f.read().split("\n")
        if line.strip()
    ]

# Convert to sets of URLs (strings are hashable, dicts are not)
unverified_urls = {item["url"] for item in unverified_files}
verified_urls = {item["url"] for item in verified_files}

# Perform set subtraction
remaining_urls = unverified_urls - verified_urls

# Convert back to list of dicts if needed
unverified_files = [{"url": url, "verified": False} for url in remaining_urls]

print(f"Total unverified files remaining: {len(unverified_files)}")

print("Sample remaining URLs:")
for item in unverified_files[:10]:
    print(item["url"])

# back 10
print("Last 10 remaining URLs:")
for item in unverified_files[-10:]:
    print(item["url"])

all_files = verified_files + unverified_files
print(f"Total files to process: {len(all_files)}")
