# Reading Plan Generator

A Python utility designed to parse textbook reading assignments and distribute them evenly across a set number of days. It accounts for fractional page starts and ends (e.g., starting halfway down a page) to give an accurate measurement of reading volume.

## Features

* **Fractional Page Support:** Calculates exact reading volume using a `(part/total)` notation.
* **Dynamic Rebalancing:** If one day's subsections put you over the daily average, the script automatically recalculates the "pages per day" for the remaining time.
* **Dual Output:** Prints the plan to the console and saves it to a structured `reading_plan.txt` file.

## Input Format

The script looks for a file named `ch8.txt` (feel free to rename it) in the same directory. The file should use the following syntax for subsections:

`Chapter.Section.Sub:StartPage (StartFraction)-EndPage (EndFraction)`

This input text also should have a new line between subsections and two new lines between sections. For example:

```txt
8.1.1:274 (0/0)-277 (1/3)
8.1.2:277 (1/3)-279 (1/2)
8.1.3:279 (1/2)-285 (1/2)

8.2.1:285 (1/2)-287 (1/4)
8.2.2:287 (1/4)-287 (2/3)
8.2.3:287 (2/3)-287 (4/5)
8.2.4:287 (4/5)-288 (3/4)
8.2.5:288 (3/4)-289 (1/4)
```

### Example

`8.01.1:274 (0/0)-277 (1/3)`

* **`274 (0/0)`**: Starts at the top of page 274.
* **`277 (1/3)`**: Ends one-third of the way through page 277.

## Logic Overview

1. **Parsing**: The script identifies sections and subsections.
2. **Volume Calculation**: Converts fractional strings into floats to determine the precise "length" of each assignment.
3. **Dynamic Greedy (Proactive) Distribution**: Stacks *full* subsections until the daily target is met.
4. **Adjustment**: After each day, it recalculates the target for the remaining days.

## Usage

1. Create `ch8.txt` with your reading list.
2. Set the desired number of days in the script with the `DAYS` list.
3. Run the script: `python your_script_name.py`
4. View the plan in `reading_plan.txt`.