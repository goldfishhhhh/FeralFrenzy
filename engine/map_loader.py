# engine/map_loader.py
# Reads level layout from a .txt tile matrix file.
# Uses open() for File I/O (Advanced Topic).
#
# Tile legend:
#   W — wall
#   . — empty floor
#   P — player spawn
#   E — enemy spawn


def load_map(filepath: str) -> list[list[str]]:
    """
    Parse a tile matrix text file into a 2-D list of strings.

    Returns a list of rows, each row a list of single-char tile codes.
    Raises FileNotFoundError if the file is missing (caught in main.py).
    """
    grid = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            row = list(line.rstrip("\n"))
            if row:
                grid.append(row)
    return grid


def find_spawns(grid: list[list[str]]) -> dict:
    """Return pixel-coordinate spawn positions keyed by tile type."""
    TILE_SIZE = 32
    spawns = {"player": [], "enemy": []}
    for row_idx, row in enumerate(grid):
        for col_idx, tile in enumerate(row):
            x = col_idx * TILE_SIZE
            y = row_idx * TILE_SIZE
            if tile == "P":
                spawns["player"].append((x, y))
            elif tile == "E":
                spawns["enemy"].append((x, y))
    return spawns
