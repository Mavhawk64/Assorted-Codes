def remove_incorrect_guesses_by_row_col(guesses, row_col):
    # removes guesses that contradict known row/col info
    filtered_guesses = []
    for guess in guesses:
        valid = True
        for i in range(len(guess)):
            if row_col[i] is not None and guess[i] != row_col[i]:
                valid = False
                break
        if valid:
            filtered_guesses.append(guess)
    return filtered_guesses


def form_blocks(arr):
    # converts [1,1,0,1,0] to [2,0,1,0]
    blocks = []
    for i in arr:
        if i == 1:
            if len(blocks) == 0 or blocks[-1] == 0:
                blocks.append(1)
            else:
                blocks[-1] += 1
        else:
            blocks.append(0)
    return blocks


def are_valid_blocks(guess_blocks, target_blocks):
    # if target_blocks[0] in guess_blocks, find index (idx) and check rest...
    # if target_blocks[1] in guess_blocks[idx+1:], find index (idx) and check rest...
    for target in target_blocks:
        found = False
        for idx, guess in enumerate(guess_blocks):
            if guess == target:
                found = True
                guess_blocks = guess_blocks[idx + 1 :]
                break
        if not found:
            return False
    return True


def get_valid_blocks(guesses, target_blocks):
    valid_guesses = []
    for guess in guesses:
        if are_valid_blocks(guess, target_blocks):
            valid_guesses.append(guess)
    return valid_guesses


def expand_blocks(blocks):
    # expands [2,0,1,0] to [1,1,0,1,0]
    expanded = []
    for block in blocks:
        if block == 0:
            expanded.append(0)
        else:
            expanded.extend([1] * block)
    return expanded


def intersection(lists):
    intersection = lists[0]
    for li in range(1, len(lists)):
        intersection = [
            a if a == b else None for a, b in zip(intersection, lists[li], strict=False)
        ]
    return intersection


def fill_nones_with_zeros(row_col):
    return [0 if cell is None else cell for cell in row_col]


def quick_remove_junk(guesses, total_filled):
    filtered = []
    for guess in guesses:
        if sum(guess) == total_filled:
            filtered.append(guess)
    return filtered


def generate_guesses(length, blocks):
    if not blocks:
        return [[0] * length]
    min_needed = sum(blocks) + len(blocks) - 1
    results = []
    for start in range(length - min_needed + 1):
        prefix = [0] * start + [1] * blocks[0]
        if len(blocks) == 1:
            suffix = [0] * (length - len(prefix))
            results.append(prefix + suffix)
        else:
            prefix.append(0)
            for sub_guess in generate_guesses(length - len(prefix), blocks[1:]):
                results.append(prefix + sub_guess)
    return results


def run_checker(LIST, ROW_COL, debug=False):
    LENGTH = len(ROW_COL)
    if sum(LIST) == ROW_COL.count(1):
        if debug:
            print("Already solved!")
        return fill_nones_with_zeros(ROW_COL)
    guesses = generate_guesses(LENGTH, LIST)
    if debug:
        print("Total guesses before quick removal:", len(guesses))
    guesses = quick_remove_junk(guesses, sum(LIST))
    if debug:
        print("Total guesses after quick removal:", len(guesses))

    guesses = remove_incorrect_guesses_by_row_col(guesses, ROW_COL)
    if debug:
        print("Total guesses after removing contradictions:", len(guesses))

    guesses = list(set(tuple(guess) for guess in guesses))  # remove duplicates

    guesses = [list(guess) for guess in guesses]
    if debug:
        print(len(guesses))

    guesses = [form_blocks(guess) for guess in guesses]
    # if debug:
    #     print(guesses)
    valid_guesses = get_valid_blocks(guesses, LIST)
    if debug:
        print(valid_guesses)
    expanded_valid_guesses = [expand_blocks(guess) for guess in valid_guesses]
    # if debug:
    #     print(expanded_valid_guesses)

    final_intersection = intersection(expanded_valid_guesses)
    # if debug:
    #     print(final_intersection)

    return final_intersection


# Fill it in like binary numbers:
# 0000 -> 0001, 0010, 0011, 0100, ..., 1111
# by this, i mean (in a fairly simple case):
# LIST = [2, 1]
# ROW_COL = [None, None, None, None, None]
# Fill in the Nones -> [1,1,0,1,0], [1,1,0,0,1], [0,1,1,0,1] are the only valid options
# Technically, I could just fill this in with the combinations or whatever then do a check to make sure that blocks are in the right place
# Let's try that:

if __name__ == "__main__":
    # LIST = [2, 4, 1, 2]  # list of blocks
    # ROW_COL = [0, 0, 0, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, 0, 0]  # fmt: skip
    LIST = [12]
    ROW_COL = [None, None, None, None, None, None, 1,1,1,1,1,1,None, None, 1, None, None, None, 0, 0]  # fmt: skip
    # None - unknown, 0 - empty, 1 - filled.
    result = run_checker(LIST, ROW_COL, debug=True)
    print("Result:", result)
