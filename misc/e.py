import pyautogui as pg

for i in range(10000):
    pg.keyDown('e')
    pg.sleep(.1)
    pg.keyUp('e')
    pg.sleep(5)