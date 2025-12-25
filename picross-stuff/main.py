import ast
import os
import re

import numpy as np
from list_checker import run_checker

HAS_PARTIAL_HINTS = False

INPUT = "wario_9b.txt"
HINTS_LENGTH = 8


def display_grid(
    grid,
    ROWS,
    COLUMNS,
    ROW_NUMS_DISPLAY,
    COL_NUMS_DISPLAY,
    WIDTH,
    HEIGHT,
    row_col_idx: tuple | None = None,
    output_file: str | None = None,
):
    # [♦] for filled, [X] for empty, [_] for unknown
    # highlight (blue) every 5 columns/rows (except edges)
    total_output = ""
    for col in np.array(COL_NUMS_DISPLAY).T:
        out = " " * HINTS_LENGTH * 3  # space for row numbers
        for _col_idx, num in enumerate(col):
            if _col_idx != 0 and _col_idx % 5 == 0:
                out += " "
            if num is None:
                out += "   "
            else:
                out += " " * (2 - len(str(num))) + f"{num} "
        if not output_file:
            print(out)
        total_output += out + "\n"
    for _row_idx, row in enumerate(grid):
        display_row = ""
        row_fmt = ""
        row_end_fmt = ""
        if _row_idx != 0 and _row_idx % 5 == 0:
            display_row += (" " * HINTS_LENGTH * 3) + (
                "\033[94m" + "-" * (WIDTH * 3 + (WIDTH // 5) - 1) + "\033[0m\n"
            )

        for idx in range(len(ROW_NUMS_DISPLAY[_row_idx])):
            num = ROW_NUMS_DISPLAY[_row_idx][idx]
            if num is None:
                display_row += "   "
            else:
                display_row += " " * (2 - len(str(num))) + f"{num} "
        if row_col_idx is not None and row_col_idx[0] == _row_idx:
            row_fmt = "\033[93m"
            row_end_fmt = "\033[0m"
        display_row += row_fmt
        for _col_idx, cell in enumerate(row):
            col_fmt = ""
            col_end_fmt = ""

            if row_col_idx is not None and row_col_idx[1] == _col_idx:
                col_fmt = "\033[93m"
                col_end_fmt = "\033[0m"

            if _col_idx != 0 and _col_idx % 5 == 0:
                display_row += row_end_fmt + "\033[94m" + "|" + "\033[0m" + row_fmt
            if cell == 1:
                display_row += row_end_fmt + "\033[92m" + "[♦]" + "\033[0m" + row_fmt
            elif cell == 0:
                display_row += col_fmt + "[X]" + col_end_fmt
            else:
                display_row += col_fmt + "[_]" + col_end_fmt
        if row_col_idx is not None and row_col_idx[0] == _row_idx:
            display_row += row_end_fmt
        if not output_file:
            print(display_row)
        total_output += display_row + "\n"
    if output_file is not None:
        with open(output_file, "w", encoding="utf-8") as f:
            # remove ANSI codes for the file output
            ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
            total_output = ansi_escape.sub("", total_output)
            f.write(total_output)


def create_grid(has_partial_hints: bool = False, dev: bool = False):
    global HINTS_LENGTH
    if not has_partial_hints:
        with open(os.path.join(os.path.dirname(__file__), "puzzles", INPUT), "r") as f:
            content = f.read().strip().split("\n")
            COLUMNS = [[int(x) for x in a.split(",")] for a in content[0].split(" ")]
            ROWS = [[int(x) for x in a.split(",")] for a in content[1].split(" ")]
        if dev:
            print("COLUMNS:", COLUMNS)
            print("ROWS:", ROWS)

        WIDTH = len(COLUMNS)
        HEIGHT = len(ROWS)

        HINTS_LENGTH = max(8, max(len(i) for i in COLUMNS), max(len(i) for i in ROWS))
        print("Using HINTS_LENGTH =", HINTS_LENGTH)

        # Fill in with Nones up to HINTS_LENGTH
        COL_NUMS_DISPLAY = [[None] * (HINTS_LENGTH - len(lst)) + lst for lst in COLUMNS]
        ROW_NUMS_DISPLAY = [[None] * (HINTS_LENGTH - len(lst)) + lst for lst in ROWS]

        GRID = [[None for _ in range(WIDTH)] for _ in range(HEIGHT)]
        if dev:
            print("Parsed input as:")
            display_grid(
                GRID, ROWS, COLUMNS, ROW_NUMS_DISPLAY, COL_NUMS_DISPLAY, WIDTH, HEIGHT
            )
            input("Press Enter to start solving (or Ctrl+C to cancel)...")
    else:
        # open partial hints file
        with open(
            os.path.join(os.path.dirname(__file__), "partial_solution.txt"),
            "r",
            encoding="utf-8",
        ) as f:
            content = f.read().split("\n")
        # first 8* lines are column hints
        for i in range(len(content)):
            if "[" in content[i]:
                HINTS_LENGTH = i
                break
        print("Using HINTS_LENGTH =", HINTS_LENGTH)
        COL_NUMS_DISPLAY = []
        for i in range(HINTS_LENGTH):
            line = content[i][HINTS_LENGTH * 3 :]
            COL_NUMS_DISPLAY.append([])
            counter = 1
            while True:
                next_num = line[: 3 + (1 if counter % 5 == 0 else 0)]
                if next_num.strip() == "":
                    COL_NUMS_DISPLAY[-1].append(None)
                else:
                    COL_NUMS_DISPLAY[-1].append(int(next_num.strip()))
                line = line[3 + (1 if counter % 5 == 0 else 0) :]
                counter += 1
                if line == "":
                    break
        COL_NUMS_DISPLAY = np.array(COL_NUMS_DISPLAY).T.tolist()
        # COLUMNS = remove nones from COL_NUMS_DISPLAY
        COLUMNS = [[num for num in col if num is not None] for col in COL_NUMS_DISPLAY]

        # Parse ROW_NUMS_DISPLAY and ROWS
        ROW_NUMS_DISPLAY = []
        ROWS = []
        counter = 1
        for i in range(HINTS_LENGTH, len(content)):
            if counter % 6 == 0 and counter != 0:
                counter += 1
                continue
            counter += 1
            line = content[i][: HINTS_LENGTH * 3]
            ROW_NUMS_DISPLAY.append([])
            for _ in range(0, HINTS_LENGTH):
                next_num = line[:3]
                if next_num.strip() == "":
                    ROW_NUMS_DISPLAY[-1].append(None)
                else:
                    num = int(next_num.strip())
                    ROW_NUMS_DISPLAY[-1].append(num)
                line = line[3:]
        print(ROW_NUMS_DISPLAY)
        # ROWS = remove nones from ROW_NUMS_DISPLAY
        ROWS = [[num for num in row if num is not None] for row in ROW_NUMS_DISPLAY]

        # parse grid
        GRID = []
        grid_txt = "["
        for i in range(HINTS_LENGTH, len(content)):
            if (i - HINTS_LENGTH + 1) % 6 == 0 and (i - HINTS_LENGTH + 1) != 0:
                continue
            line = content[i][HINTS_LENGTH * 3 :].replace("|", "").replace(
                "][", ","
            ).replace("♦", "1").replace("X", "0").replace("_", "None") + (",")
            grid_txt += line
        grid_txt = grid_txt[:-1] + "]"
        GRID = ast.literal_eval(grid_txt)

        WIDTH = len(COLUMNS)
        HEIGHT = len(ROWS)
        if dev:
            print("PARSED GRID:")
            display_grid(
                GRID, ROWS, COLUMNS, ROW_NUMS_DISPLAY, COL_NUMS_DISPLAY, WIDTH, HEIGHT
            )
    return GRID, ROWS, COLUMNS, ROW_NUMS_DISPLAY, COL_NUMS_DISPLAY, WIDTH, HEIGHT


def run_solver_in_dev_mode(debug: bool = False):
    GRID, ROWS, COLUMNS, ROW_NUMS_DISPLAY, COL_NUMS_DISPLAY, WIDTH, HEIGHT = (
        create_grid(has_partial_hints=HAS_PARTIAL_HINTS, dev=True)
    )
    prev_grid = None
    cnt = 1
    while prev_grid != GRID:
        prev_grid = [row[:] for row in GRID]
        print("Processing Rows:")
        for row_idx in range(HEIGHT):
            row_result = run_checker(ROWS[row_idx], GRID[row_idx], debug=debug)
            GRID[row_idx] = row_result
            display_grid(
                GRID,
                ROWS,
                COLUMNS,
                ROW_NUMS_DISPLAY,
                COL_NUMS_DISPLAY,
                WIDTH,
                HEIGHT,
                row_col_idx=(row_idx, None),
            )
            print(f"^^^^ Row {row_idx + 1}/{HEIGHT} ^^^^\n")
            # time.sleep(1)
        print("Processing Columns:")
        for col_idx in range(WIDTH):
            col = [GRID[row_idx][col_idx] for row_idx in range(HEIGHT)]
            col_result = run_checker(COLUMNS[col_idx], col, debug=debug)
            for row_idx in range(HEIGHT):
                GRID[row_idx][col_idx] = col_result[row_idx]
            display_grid(
                GRID,
                ROWS,
                COLUMNS,
                ROW_NUMS_DISPLAY,
                COL_NUMS_DISPLAY,
                WIDTH,
                HEIGHT,
                row_col_idx=(None, col_idx),
            )
            print(f"^^^^ Column {col_idx + 1}/{WIDTH} ^^^^\n")
            # time.sleep(1)
        # exit()
        print(f"After iteration #{cnt}:")
        display_grid(
            GRID, ROWS, COLUMNS, ROW_NUMS_DISPLAY, COL_NUMS_DISPLAY, WIDTH, HEIGHT
        )
        cnt += 1
        if None not in [cell for row in GRID for cell in row]:
            print("Solved!")
            break

    print("Final Grid:")
    display_grid(GRID, ROWS, COLUMNS, ROW_NUMS_DISPLAY, COL_NUMS_DISPLAY, WIDTH, HEIGHT)

    if None in [cell for row in GRID for cell in row]:
        print(
            "Could not solve the puzzle completely. Saving current state to 'partial_solution.txt'. Feel free to update it with any hints you have and rerun the solver."
        )
        display_grid(
            GRID,
            ROWS,
            COLUMNS,
            ROW_NUMS_DISPLAY,
            COL_NUMS_DISPLAY,
            WIDTH,
            HEIGHT,
            output_file=os.path.join(os.path.dirname(__file__), "partial_solution.txt"),
        )


def get_grid_one_step(GRID, ROWS, COLUMNS, HEIGHT, row_col_idx: tuple):
    if row_col_idx[0] is not None:
        row_idx = row_col_idx[0]
        row_result = run_checker(ROWS[row_idx], GRID[row_idx], debug=False)
        GRID[row_idx] = row_result
    elif row_col_idx[1] is not None:
        col_idx = row_col_idx[1]
        col = [GRID[row_idx][col_idx] for row_idx in range(HEIGHT)]
        col_result = run_checker(COLUMNS[col_idx], col, debug=False)
        for row_idx in range(HEIGHT):
            GRID[row_idx][col_idx] = col_result[row_idx]
    return GRID


def generate_puzzle_from_text():
    GRID, ROWS, COLUMNS, ROW_NUMS_DISPLAY, COL_NUMS_DISPLAY, WIDTH, HEIGHT = (
        create_grid(has_partial_hints=HAS_PARTIAL_HINTS, dev=False)
    )
    display_grid(
        GRID,
        ROWS,
        COLUMNS,
        ROW_NUMS_DISPLAY,
        COL_NUMS_DISPLAY,
        WIDTH,
        HEIGHT,
        output_file=os.path.join(
            os.path.dirname(__file__), "puzzles/puzzle_output.txt"
        ),
    )


if __name__ == "__main__":
    # run_solver_in_dev_mode()
    generate_puzzle_from_text()
