import pyautogui as pg


def down_row(direction_key):
    # hold left click to break crops
    pg.mouseDown(button='left')
    # move right for a short duration to break crops in a row
    pg.keyDown(direction_key)
    pg.sleep(25)  # Adjust duration as needed
    pg.keyUp(direction_key)
    pg.mouseUp(button='left')
    # move forward to the next row
    pg.keyDown('w')
    pg.sleep(3)  # Adjust duration as needed
    pg.keyUp('w')


def auto_farmer():
    """
    Automates farming in Minecraft by simulating mouse clicks and keyboard presses.
    This function assumes the player is already in the farming area and ready to farm.
    """
    try:
        i = 1
        while i <= 40:
            down_row('a')
            down_row('d')
            i += 1

    except KeyboardInterrupt:
        print("Auto farmer stopped by user.")


if __name__ == "__main__":
    auto_farmer()
