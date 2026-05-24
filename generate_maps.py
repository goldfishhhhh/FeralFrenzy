"""
Run from FeralFrenzy/ to regenerate all 50 map files:
    python generate_maps.py
Corridors are 2 tiles wide so the player can pass through easily.
"""
import random, os

COLS, ROWS = 30, 20

def clearance(grid, c, r):
    count = 0
    for dc in (-1, 0, 1):
        for dr in (-1, 0, 1):
            nc, nr = c+dc, r+dr
            if 0 <= nr < ROWS and 0 <= nc < COLS and grid[nr][nc] != 'W':
                count += 1
    return count

def carve_corridor(grid, x1, y1, x2, y2):
    """Carve a 2-tile-wide L-shaped corridor between two points."""
    cx, cy = x1, y1
    # Horizontal leg
    while cx != x2:
        cx += 1 if cx < x2 else -1
        for dy in (0, 1):   # 2 tiles wide vertically
            r = cy + dy
            if 0 < r < ROWS-1 and 0 < cx < COLS-1:
                grid[r][cx] = '.'
    # Vertical leg
    while cy != y2:
        cy += 1 if cy < y2 else -1
        for dx in (0, 1):   # 2 tiles wide horizontally
            c = cx + dx
            if 0 < cy < ROWS-1 and 0 < c < COLS-1:
                grid[cy][c] = '.'

def make_map(seed):
    random.seed(seed)
    grid = [['W'] * COLS for _ in range(ROWS)]
    rooms = []
    attempts = 0
    while len(rooms) < random.randint(4, 7) and attempts < 100:
        attempts += 1
        w = random.randint(5, 10)
        h = random.randint(4, 7)
        x = random.randint(1, COLS - w - 2)
        y = random.randint(1, ROWS - h - 2)
        overlap = False
        for (rx, ry, rw, rh) in rooms:
            if x < rx+rw+2 and x+w+2 > rx and y < ry+rh+2 and y+h+2 > ry:
                overlap = True; break
        if not overlap:
            rooms.append((x, y, w, h))
            for row in range(y, y+h):
                for col in range(x, x+w):
                    grid[row][col] = '.'

    # Connect rooms with 2-wide corridors
    for i in range(len(rooms)-1):
        x1 = rooms[i][0] + rooms[i][2]//2
        y1 = rooms[i][1] + rooms[i][3]//2
        x2 = rooms[i+1][0] + rooms[i+1][2]//2
        y2 = rooms[i+1][1] + rooms[i+1][3]//2
        carve_corridor(grid, x1, y1, x2, y2)

    # Place P in best spot in first room
    if rooms:
        rx, ry, rw, rh = rooms[0]
        best, best_c = -1, (rx+rw//2, ry+rh//2)
        for r in range(ry, ry+rh):
            for c in range(rx, rx+rw):
                cl = clearance(grid, c, r)
                if cl > best: best, best_c = cl, (c, r)
        grid[best_c[1]][best_c[0]] = 'P'

    # Place E in best open spot in each other room
    for rx, ry, rw, rh in rooms[1:]:
        best, best_c = -1, None
        for r in range(ry, ry+rh):
            for c in range(rx, rx+rw):
                if grid[r][c] != 'W':
                    cl = clearance(grid, c, r)
                    if cl > best: best, best_c = cl, (c, r)
        if best_c and best >= 6:
            grid[best_c[1]][best_c[0]] = 'E'

    # Enforce border
    for c in range(COLS): grid[0][c] = grid[ROWS-1][c] = 'W'
    for r in range(ROWS): grid[r][0] = grid[r][COLS-1] = 'W'
    return grid

os.makedirs("maps", exist_ok=True)
for i in range(1, 51):
    grid = make_map(seed=i * 137 + 42)
    path = os.path.join("maps", f"level{i}.txt")
    with open(path, 'w') as f:
        f.write('\n'.join(''.join(row) for row in grid) + '\n')
    print(f"  created maps/level{i}.txt")

print(f"\n✓ Done — 50 maps regenerated with 2-tile-wide corridors")