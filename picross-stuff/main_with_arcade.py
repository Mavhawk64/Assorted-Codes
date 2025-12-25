"""
Array Backed Grid

Show how to use a two-dimensional list/array to back the display of a
grid on-screen.
"""

import arcade
from arcade.types import Color
from arcade.types.vector_like import AnchorPoint
from main import create_grid, get_grid_one_step

HAS_PARTIAL_HINTS = False

# Set how many rows and columns we will have
ROW_COUNT = create_grid(has_partial_hints=HAS_PARTIAL_HINTS)[1].__len__()
COLUMN_COUNT = create_grid(has_partial_hints=HAS_PARTIAL_HINTS)[2].__len__()

# This sets the WIDTH and HEIGHT of each grid location
WIDTH = 20
HEIGHT = 20

# This sets the margin between each cell
# and on the edges of the screen.
MARGIN = 5

OUTSIDE_EDGE = 5 * MARGIN

# Do the math to figure out our screen dimensions
SCREEN_LEFT_BORDER = (WIDTH + MARGIN) * 8 + MARGIN
SCREEN_UPPER_BORDER = (HEIGHT + MARGIN) * 8 + MARGIN
SCREEN_WIDTH = (WIDTH + MARGIN) * (COLUMN_COUNT + 8) + MARGIN + OUTSIDE_EDGE
SCREEN_HEIGHT = (HEIGHT + MARGIN) * (ROW_COUNT + 8) + MARGIN + OUTSIDE_EDGE


class MyGame(arcade.Window):
    """
    Main application class.
    """

    def __init__(self, width, height):
        """
        Set up the application.
        """
        super().__init__(width, height)
        # Create a 2 dimensional array. A two dimensional
        # array is simply a list of lists.
        (
            self.GRID,
            self.ROWS,
            self.COLUMNS,
            self.ROW_NUMS_DISPLAY,
            self.COL_NUMS_DISPLAY,
            self.WIDTH,
            self.HEIGHT,
        ) = create_grid(has_partial_hints=HAS_PARTIAL_HINTS)
        self.is_finished = False
        self.row_idx = 0
        self.col_idx = 0
        self.prev_grid = [row[:] for row in self.GRID]

        arcade.set_background_color(arcade.color.BLACK)

    def on_draw(self):
        """
        Render the screen.
        """

        row_col_idx = (None, None)
        if self.row_idx < ROW_COUNT:
            row_col_idx = (self.row_idx, None)
            self.row_idx += 1
        elif self.col_idx < COLUMN_COUNT:
            row_col_idx = (None, self.col_idx)
            self.col_idx += 1
        else:
            if self.prev_grid == self.GRID:
                self.is_finished = True
            self.prev_grid = [row[:] for row in self.GRID]
            self.row_idx = 0
            self.col_idx = 0
            row_col_idx = (self.row_idx, None)
            self.row_idx += 1

        # This command has to happen before we start drawing
        self.clear()

        # Draw the outside
        arcade.draw_rect_filled(
            arcade.XYWH(
                0,
                SCREEN_HEIGHT,
                SCREEN_WIDTH + MARGIN,
                SCREEN_HEIGHT + MARGIN,
                anchor=AnchorPoint.TOP_LEFT,
            ),
            Color(100, 100, 100),
        )

        arcade.draw_rect_filled(
            arcade.XYWH(
                x=SCREEN_LEFT_BORDER - MARGIN,
                y=SCREEN_HEIGHT - SCREEN_UPPER_BORDER + MARGIN,
                width=SCREEN_WIDTH - SCREEN_LEFT_BORDER - OUTSIDE_EDGE + MARGIN,
                height=SCREEN_HEIGHT - SCREEN_UPPER_BORDER - OUTSIDE_EDGE + MARGIN,
                anchor=AnchorPoint.TOP_LEFT,
            ),
            Color(20, 20, 20),
        )

        BLUE_LINES_ROWS_COUNT = ROW_COUNT // 5
        BLUE_LINES_COLUMNS_COUNT = COLUMN_COUNT // 5
        # Draw the blue lines every 5 rows/columns
        for row in range(1, BLUE_LINES_ROWS_COUNT):
            y = (MARGIN + HEIGHT) * (row * 5 + 8) + MARGIN / 2
            arcade.draw_line(
                SCREEN_LEFT_BORDER,
                SCREEN_HEIGHT - y,
                SCREEN_WIDTH - MARGIN - OUTSIDE_EDGE,
                SCREEN_HEIGHT - y,
                Color(50, 96, 168),
                MARGIN,
            )
        for column in range(1, BLUE_LINES_COLUMNS_COUNT):
            x = (MARGIN + WIDTH) * (column * 5 + 8) + MARGIN / 2
            arcade.draw_line(
                x,
                MARGIN + OUTSIDE_EDGE,
                x,
                SCREEN_HEIGHT - SCREEN_UPPER_BORDER,
                Color(50, 96, 168),
                MARGIN,
            )
        # Draw the numbers around the outside, using ROW_NUMS_DISPLAY and COL_NUMS_DISPLAY
        for row in range(ROW_COUNT):
            y = SCREEN_HEIGHT - ((MARGIN + HEIGHT) * (row + 8) + MARGIN + HEIGHT // 2)
            for idx, num in enumerate(self.ROW_NUMS_DISPLAY[row]):
                x = (MARGIN + WIDTH) * idx + MARGIN + (WIDTH // 2)
                if num is not None:
                    arcade.draw_text(
                        str(num),
                        x - 7 * len(str(num)),
                        y - 7,
                        Color(255, 255, 255),
                        14,
                        align="right",
                    )
        for column in range(COLUMN_COUNT):
            x = (MARGIN + WIDTH) * (column + 8) + MARGIN + WIDTH // 2
            for idx, num in enumerate(self.COL_NUMS_DISPLAY[column]):
                y = SCREEN_HEIGHT - (MARGIN + HEIGHT) * idx - MARGIN - (HEIGHT // 2)
                if num is not None:
                    arcade.draw_text(
                        str(num),
                        x - 7 * len(str(num)),
                        y,
                        Color(255, 255, 255),
                        14,
                        align="right",
                    )
        # Draw the grid
        for row in range(ROW_COUNT):
            for column in range(COLUMN_COUNT):
                # Figure out what color to draw the box
                if self.GRID[row][column] == 1:
                    color = Color(0, 0, 0)
                elif self.GRID[row][column] == 0:
                    color = Color(51, 51, 51)
                else:
                    if row_col_idx[0] == row or row_col_idx[1] == column:
                        color = Color(204, 204, 0)
                    else:
                        color = Color(200, 200, 200)

                # Do the math to figure out where the box is
                x = (MARGIN + WIDTH) * (column + 8) + MARGIN + WIDTH // 2
                y = SCREEN_HEIGHT - (
                    (MARGIN + HEIGHT) * (row + 8) + MARGIN + HEIGHT // 2
                )

                # Draw the box
                arcade.draw_rect_filled(arcade.XYWH(x, y, WIDTH, HEIGHT), color)
        # Do one step of the solver
        if not self.is_finished:
            self.GRID = get_grid_one_step(
                self.GRID, self.ROWS, self.COLUMNS, self.HEIGHT, row_col_idx
            )
        # self.GRID[random.randint(0, ROW_COUNT - 1)][
        #     random.randint(0, COLUMN_COUNT - 1)
        # ] = 1

    def on_mouse_press(self, x, y, button, modifiers):
        """
        Called when the user presses a mouse button.
        """

        # Change the x/y screen coordinates to grid coordinates
        column = int(x) // (WIDTH + MARGIN) - 8
        row = int(SCREEN_HEIGHT - y) // (HEIGHT + MARGIN) - 8

        print(f"Click coordinates: ({x}, {y}). Grid coordinates: ({column}, {row})")

        # Make sure we are on-grid. It is possible to click in the upper right
        # corner in the margin and go to a grid location that doesn't exist
        if 0 <= row < ROW_COUNT and 0 <= column < COLUMN_COUNT:
            # Flip the location between 1 and 0.
            if self.GRID[row][column] == 0:
                self.GRID[row][column] = 1
            else:
                self.GRID[row][column] = 0


def main():
    MyGame(SCREEN_WIDTH, SCREEN_HEIGHT)
    arcade.run()


if __name__ == "__main__":
    main()
    main()
