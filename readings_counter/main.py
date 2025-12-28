import os

INPUT_FILE = "ch8_d2.txt"
FILE_OUTPUT = True
OUTPUT_FILE = "reading_plan.txt"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday"]


with open(os.path.join(os.path.dirname(__file__), INPUT_FILE), "r") as file:
    txt_input = [section.split("\n") for section in file.read().split("\n\n")]

# input is like ch.sec.sub:pg# (?/?)-pg# (!/!)
# example: 8.01.1:274 (0/0)-277 (1/3)
# the (0/0) indicates top of page.
# Therefore, this is read as: Subsection 8.1.1 starts at the top of the page on 274 and ends a third of the way through page 277.
# Let's count how much reading there is in total and divide it by 4 days (Mon-Thu) so I can be prepared for my meeting on Friday.
total_pages = 0
pg_cnt = []

for section in txt_input:
    for subsection in section:
        if not subsection.strip():
            continue
        sub = subsection.split(":")[0]
        pages = subsection.split(":")[1]
        start_pg_txt = pages.split("-")[0]
        start_pg = int(start_pg_txt.split(" ")[0])
        start_pg_frac = (
            int(start_pg_txt.split(" ")[1].strip("()").split("/")[0])
            / int(start_pg_txt.split(" ")[1].strip("()").split("/")[1])
            if start_pg_txt.split(" ")[1] != "(0/0)"
            else 0
        )
        end_pg_txt = pages.split("-")[1]
        end_pg = int(end_pg_txt.split(" ")[0])
        end_pg_frac = (
            int(end_pg_txt.split(" ")[1].strip("()").split("/")[0])
            / int(end_pg_txt.split(" ")[1].strip("()").split("/")[1])
            if end_pg_txt.split(" ")[1] != "(0/0)"
            else 0
        )
        page_count = (end_pg + end_pg_frac) - (start_pg + start_pg_frac)
        pg_cnt.append((sub, page_count))
        total_pages += page_count


ppd_txt = f"Pages to read per day ({DAYS[0]}-{DAYS[-1]}, {len(DAYS)} days):"


prefix = (len(ppd_txt) - len("Total pages to read:")) * " "

print("== Reading Plan Summary ==\n")

print(prefix + f"Total pages to read: {total_pages:.2f}")
avg_ppd = total_pages / len(DAYS)
print(f"{ppd_txt} {avg_ppd:.2f}")

if FILE_OUTPUT:
    with open(os.path.join(os.path.dirname(__file__), OUTPUT_FILE), "w") as out_file:
        out_file.write("== Reading Plan Summary ==\n\n")
        out_file.write(prefix + f"Total pages to read: {total_pages:.2f}\n")
        out_file.write(f"{ppd_txt} {avg_ppd:.2f}\n")

# Generate a summary of pages per subsection and estimate the subsections to be covered each day
ss_pointer = 0
tpc = 0  # total pages covered
ppd = avg_ppd
remaining_pages = total_pages
for day in range(len(DAYS)):
    pages_covered = 0
    print(f"\n{DAYS[day]} reading plan:")
    if FILE_OUTPUT:
        with open(
            os.path.join(os.path.dirname(__file__), OUTPUT_FILE), "a"
        ) as out_file:
            out_file.write(f"\n{DAYS[day]} reading plan:\n")
    while pages_covered < ppd and ss_pointer < len(pg_cnt):
        sub, page_count = pg_cnt[ss_pointer]
        if pages_covered > ppd:
            break
        print(f"  Read subsection {sub}: {page_count:.2f} pages")
        if FILE_OUTPUT:
            with open(
                os.path.join(os.path.dirname(__file__), OUTPUT_FILE), "a"
            ) as out_file:
                out_file.write(f"  Read subsection {sub}: {page_count:.2f} pages\n")
        pages_covered += page_count
        ss_pointer += 1
    print(
        "  Total pages for the day:",
        f"{pages_covered:.2f}",
        f"(Target: {ppd:.2f})",
        "{:.2f}% of target".format((pages_covered / ppd) * 100),
    )
    tpc += pages_covered
    print("Pages covered so far:", f"{tpc:.2f}")

    if FILE_OUTPUT:
        with open(
            os.path.join(os.path.dirname(__file__), OUTPUT_FILE), "a"
        ) as out_file:
            out_file.write(
                f"  Total pages for the day: {pages_covered:.2f} (Target: {ppd:.2f}) "
                f"{(pages_covered / ppd) * 100:.2f}% of target\n"
            )
            out_file.write(f"Pages covered so far: {tpc:.2f}\n")
    remaining_pages = total_pages - tpc
    days_left = len(DAYS) - (day + 1)
    if days_left > 0:
        ppd = remaining_pages / days_left
        print(
            f"Updated pages per day for remaining {days_left} days: {ppd:.2f} pages/day"
        )
        if FILE_OUTPUT:
            with open(
                os.path.join(os.path.dirname(__file__), OUTPUT_FILE), "a"
            ) as out_file:
                out_file.write(
                    f"Updated pages per day for remaining {days_left} days: {ppd:.2f} pages/day\n"
                )
    # CATCH IF DONE EARLY
    if (ppd == 0 or ss_pointer >= len(pg_cnt)) and day < len(DAYS) - 1:
        print("\nAll reading completed early!")
        if FILE_OUTPUT:
            with open(
                os.path.join(os.path.dirname(__file__), OUTPUT_FILE), "a"
            ) as out_file:
                out_file.write("\nAll reading completed early!\n")
        break
print("\n== End of Reading Plan ==")

if FILE_OUTPUT:
    with open(os.path.join(os.path.dirname(__file__), OUTPUT_FILE), "a") as out_file:
        out_file.write("\n== End of Reading Plan ==\n")
