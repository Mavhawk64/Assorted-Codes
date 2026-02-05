import time

import autoit
import keyboard
import mouse


def interruptible_sleep(duration):
    start_time = time.time()
    while time.time() - start_time < duration:
        # Check for Space or Mouse Clicks to stop
        if (
            keyboard.is_pressed("space")
            or mouse.is_pressed("left")
            or mouse.is_pressed("right")
        ):
            return True
        time.sleep(0.05)
    return False


print("Script started. Switch to Roblox now!")
time.sleep(3)  # Gives you time to tab into the game

while True:
    # Move forward: '{w down}' holds the key
    autoit.send("{w down}")
    stop = interruptible_sleep(1)
    autoit.send("{w up}")

    if stop:
        break
    time.sleep(0.1)

    # Move backward: '{s down}' holds the key
    autoit.send("{s down}")
    stop = interruptible_sleep(1.25)
    autoit.send("{s up}")

    if stop:
        break
    time.sleep(0.1)

print("Script stopped safely.")
