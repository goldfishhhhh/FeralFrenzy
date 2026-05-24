# engine/renderer.py
# Phase 3: map rendering, highscore display, exception handling.
#
# Controls:
#   WASD / Arrow keys  — move
#   Left-click         — shoot toward mouse
#   Space / Enter      — auto-aim + continuous fire (hold)
#   P                  — pause
#   R                  — restart (on Game Over screen)
#   ESC                — quit

import math
import os
import random
import sys
import pygame

from logic.cat     import Cat, Aries, Scorpio, Aquarius
from logic.enemy   import GreenRat, KamikazeRat, IronPigeon, RiotDog
from logic.weapons import Weapon
from logic.items   import apply_tuna_can, apply_energy_drink

try:
    from engine.map_loader import load_map, find_spawns
    from engine.music_beat import BeatDetector, find_music_file
except ImportError:
    from map_loader import load_map, find_spawns
    from music_beat import BeatDetector, find_music_file

# ── Colours ──────────────────────────────────────────────────────────────────
BLACK      = (10,  10,  18)
WHITE      = (240, 240, 240)
ORANGE     = (255, 140,   0)
RED        = (220,  50,  50)
DARK_RED   = (140,  20,  20)
GREEN      = ( 60, 200,  80)
BLUE       = ( 60, 120, 220)
YELLOW     = (255, 220,  60)
GREY       = (100, 100, 110)
LIGHT_GREY = (170, 170, 180)
PURPLE     = (160,  80, 220)
TEAL       = ( 40, 200, 180)
WALL_COL   = ( 55,  55,  75)
FLOOR_COL  = ( 22,  22,  32)

# ── Constants ─────────────────────────────────────────────────────────────────
PLAYER_SIZE      = 36    # was 24 — bigger sprite
ENEMY_SIZE       = 32    # was 22 — bigger sprite
BULLET_SIZE      = 8
ENEMY_SPEED      = 1.6
WAVE_ENEMY_COUNT = 8
AMBUSH_WAIT      = 1.5
AMBUSH_MULT      = 2.0
ITEM_SIZE        = 28    # was 20
TILE_SIZE        = 40
SCORE_FILE       = "highscore.txt"
MAP_FILE         = os.path.join("maps", "level1.txt")


# ── Helpers ───────────────────────────────────────────────────────────────────

def normalise(dx: float, dy: float) -> tuple[float, float]:
    length = math.hypot(dx, dy)
    if length == 0:
        return 0.0, 0.0
    return dx / length, dy / length


def _load_scores() -> list[dict]:
    """Read highscore.txt and return parsed records. Silently ignores bad lines."""
    records = []
    try:
        with open(SCORE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) != 4:
                    continue
                try:
                    records.append({
                        "zodiac": parts[0],
                        "kills":  int(parts[1]),
                        "score":  int(parts[2]),
                        "wave":   int(parts[3]),
                    })
                except ValueError:
                    continue          # corrupted line — skip
    except FileNotFoundError:
        pass                          # no file yet — that's fine
    return records


# ── Game entities ─────────────────────────────────────────────────────────────

class PlayerSprite:
    MAX_HEARTS = 5
    # Each heart = cat.max_hp / MAX_HEARTS damage to absorb

    def __init__(self, cat: Cat, x: float, y: float):
        self.cat              = cat
        self.x                = x
        self.y                = y
        self.size             = PLAYER_SIZE
        self.weapon: Weapon   = Weapon()
        self.still_time       = 0.0
        self.ambush_ready     = False
        self.invincible_timer = 0.0
        self.score            = 0
        self.kills            = 0
        self.facing           = (1.0, 0.0)

    @property
    def hearts(self) -> int:
        """Current hearts (0-5), rounded up so last heart shows until dead."""
        import math
        ratio = self.cat.hp / self.cat.max_hp
        return math.ceil(ratio * self.MAX_HEARTS)

    @property
    def rect(self) -> pygame.Rect:
        s = self.size
        return pygame.Rect(self.x - s // 2, self.y - s // 2, s, s)

    def colour(self):
        return {"Aries": ORANGE, "Leo": YELLOW,
                "Scorpio": PURPLE, "Aquarius": TEAL
                }.get(self.cat.__class__.__name__, WHITE)


class EnemySprite:
    def __init__(self, enemy, x: float, y: float):
        self.enemy        = enemy
        self.x            = x
        self.y            = y
        self.size         = ENEMY_SIZE
        self.poison_timer = 0.0

    @property
    def rect(self) -> pygame.Rect:
        s = self.size
        return pygame.Rect(self.x - s // 2, self.y - s // 2, s, s)

    def colour(self):
        return {"GreenRat": GREEN, "KamikazeRat": DARK_RED,
                "IronPigeon": GREY, "RiotDog": RED
                }.get(self.enemy.__class__.__name__, RED)


class Bullet:
    def __init__(self, x, y, dx, dy, damage, is_ambush=False):
        self.x      = x
        self.y      = y
        self.dx     = dx * 9
        self.dy     = dy * 9
        self.damage = damage
        self.size   = BULLET_SIZE + (4 if is_ambush else 0)
        self.colour = YELLOW if is_ambush else WHITE

    @property
    def rect(self) -> pygame.Rect:
        s = self.size
        return pygame.Rect(self.x - s // 2, self.y - s // 2, s, s)


class DroppedItem:
    def __init__(self, x, y, kind: str):
        self.x    = x
        self.y    = y
        self.kind = kind
        self.size = ITEM_SIZE

    @property
    def rect(self) -> pygame.Rect:
        s = self.size
        return pygame.Rect(self.x - s // 2, self.y - s // 2, s, s)

    def colour(self):
        return (255, 80, 80) if self.kind == "tuna" else (80, 200, 255)


class Particle:
    def __init__(self, x, y, colour):
        angle   = random.uniform(0, 2 * math.pi)
        speed   = random.uniform(1, 5)
        self.x  = x;  self.y  = y
        self.dx = math.cos(angle) * speed
        self.dy = math.sin(angle) * speed
        self.life   = 1.0
        self.colour = colour

    def update(self):
        self.x    += self.dx;  self.y    += self.dy
        self.life -= 0.04

    @property
    def alive(self): return self.life > 0


# ── Map ───────────────────────────────────────────────────────────────────────

class GameMap:
    """
    Wraps the tile grid.
    - On first load: tries maps/level1.txt, falls back to procedural gen.
    - regenerate(): produces a fresh BSP dungeon (called each new wave set).
    """

    # Map dimensions in tiles — must match window size / TILE_SIZE
    MAP_COLS = 30
    MAP_ROWS = 20

    def __init__(self, w: int, h: int):
        self.W = w
        self.H = h
        self.MAP_COLS = w // TILE_SIZE
        self.MAP_ROWS = h // TILE_SIZE
        self.grid: list[list[str]] = []
        self.wall_rects: list[pygame.Rect] = []
        self.player_spawn = (w // 2, h // 2)
        self.enemy_spawns: list[tuple] = []
        self._load_or_generate()

    def _load_or_generate(self):
        """Load a random map from the 50 pre-built level files."""
        self._load_map_file(random.randint(1, 50))

    def _load_map_file(self, n: int):
        """Load maps/levelN.txt and rebuild wall rects + spawn points."""
        path = os.path.join("maps", f"level{n}.txt")
        try:
            self.grid = load_map(path)
            spawns = find_spawns(self.grid)
            if spawns["player"]:
                raw = spawns["player"][0]
                # Validate P tile has enough clear space, else find best floor tile
                self.player_spawn = self._safe_spawn(raw)
            self.enemy_spawns = spawns["enemy"]
            self._build_wall_rects()
            print(f"[map] Loaded level{n}.txt")
        except Exception as e:
            print(f"[map] Could not load level{n}.txt: {e}")

    def _safe_spawn(self, tile_pos: tuple) -> tuple:
        """
        Verify the P tile and its 8 neighbours are all floor.
        If not, scan the grid for the floor tile with the most open neighbours.
        """
        tx, ty = tile_pos
        col = tx // TILE_SIZE
        row = ty // TILE_SIZE

        def clearance(c, r) -> int:
            """Count how many of the 8 neighbours are floor (not wall)."""
            count = 0
            for dc in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    if dc == 0 and dr == 0:
                        continue
                    nc, nr = c + dc, r + dr
                    if (0 <= nr < len(self.grid) and
                            0 <= nc < len(self.grid[0]) and
                            self.grid[nr][nc] != 'W'):
                        count += 1
            return count

        # If original P tile already has full clearance, use it
        if clearance(col, row) >= 6:
            return tile_pos

        # Otherwise find floor tile with most open neighbours
        best_pos = tile_pos
        best_score = -1
        for r, row_data in enumerate(self.grid):
            for c, tile in enumerate(row_data):
                if tile != 'W':
                    score = clearance(c, r)
                    if score > best_score:
                        best_score = score
                        best_pos = (c * TILE_SIZE, r * TILE_SIZE)
        return best_pos

    def regenerate(self, enemy_count: int = 6):
        """Pick a new random map from the 50 pre-built files."""
        self._load_map_file(random.randint(1, 50))
        self.enemy_spawns = [s for s in self.enemy_spawns]  # ensure fresh list

    def _build_wall_rects(self):
        self.wall_rects = []
        cols = len(self.grid[0]) if self.grid else 0
        rows = len(self.grid)
        for row_i, row in enumerate(self.grid):
            for col_i, tile in enumerate(row):
                if tile == "W":
                    self.wall_rects.append(pygame.Rect(
                        col_i * TILE_SIZE, row_i * TILE_SIZE,
                        TILE_SIZE, TILE_SIZE))

    def valid_floor_pos(self, x: float, y: float,
                        margin: int = TILE_SIZE) -> bool:
        """Return True if pixel (x, y) is inside the map bounds and not a wall."""
        if x < margin or y < margin or x > self.W - margin or y > self.H - margin:
            return False
        col = int(x // TILE_SIZE)
        row = int(y // TILE_SIZE)
        if not (0 <= row < len(self.grid) and 0 <= col < len(self.grid[0])):
            return False
        return self.grid[row][col] != "W"

    def open_spawn_pos(self, x: float, y: float,
                       min_clearance: int = 5) -> bool:
        """
        Return True only if the tile at (x,y) AND enough neighbours are open.
        Prevents enemies spawning in narrow corridors where they get stuck.
        """
        if not self.valid_floor_pos(x, y):
            return False
        col = int(x // TILE_SIZE)
        row = int(y // TILE_SIZE)
        open_count = 0
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                nc, nr = col + dc, row + dr
                if (0 <= nr < len(self.grid) and
                        0 <= nc < len(self.grid[0]) and
                        self.grid[nr][nc] != "W"):
                    open_count += 1
        return open_count >= min_clearance

    def draw(self, surface: pygame.Surface):
        if not self.grid:
            return
        for row_i, row in enumerate(self.grid):
            for col_i, tile in enumerate(row):
                rx = col_i * TILE_SIZE
                ry = row_i * TILE_SIZE
                if tile == "W":
                    pygame.draw.rect(surface, WALL_COL,
                                     (rx, ry, TILE_SIZE, TILE_SIZE))
                    pygame.draw.line(surface, (80, 80, 100),
                                     (rx, ry), (rx + TILE_SIZE, ry))
                    pygame.draw.line(surface, (80, 80, 100),
                                     (rx, ry), (rx, ry + TILE_SIZE))
                # Floor: transparent — background shows through


# ── Main renderer ─────────────────────────────────────────────────────────────

class GameRenderer:

    SHOOT_INTERVAL = 0.18

    def __init__(self, screen: pygame.Surface, cat: Cat, w: int, h: int):
        self.screen  = screen
        self.W       = w
        self.H       = h
        self.font_sm = pygame.font.SysFont(None, 26)
        self.font_md = pygame.font.SysFont(None, 36)
        self.font_lg = pygame.font.SysFont(None, 60)
        self.game_map = GameMap(w, h)

        # ── Sprite loader ────────────────────────────────────────────────────
        # Place 16×16 (or 20×20 for dog) PNG files in assets/sprites/.
        # Any missing file silently falls back to geometry drawing.
        self.sprites: dict[str, pygame.Surface | None] = {}
        self._load_sprites()

        # ── Sound effects ────────────────────────────────────────────────────
        self.sfx = self._load_sfx()
        self._hit_cd   = 0.0   # cooldown to avoid spamming hit sound
        music_path = find_music_file("assets")
        if music_path:
            self.beat = BeatDetector(music_path)
            self.beat.play()
            self._has_music = True
        else:
            self.beat = BeatDetector.__new__(BeatDetector)
            self.beat._loaded = False
            self.beat._timer  = 0.0
            self.beat._cd_timer = 0.0
            self.beat._fallback_interval = 0.5
            self._has_music = False

        self._beat_flash = 0.0

        # ── Settings panel state ──────────────────────────────────────────────
        self.settings_open   = False
        self._volume         = 0.7     # 0.0 – 1.0
        self._dragging_vol   = False
        pygame.mixer.music.set_volume(self._volume)

        self._init_game(cat)

    # ── Sound effects ─────────────────────────────────────────────────────────

    SFX_DIR = os.path.join("assets", "sfx")
    SFX_FILES = {
        "hit":        "hit.wav",
        "kill":       "kill.wav",
        "item_drop":  "item_drop.wav",
        "item_pick":  "item_pick.wav",
        "wave_clear": "wave_clear.wav",
        "level_up":   "level_up.wav",
    }

    def _load_sfx(self) -> dict:
        """Load all sfx from assets/sfx/. Missing files silently skipped."""
        sounds = {}
        for key, fname in self.SFX_FILES.items():
            path = os.path.join(self.SFX_DIR, fname)
            try:
                sounds[key] = pygame.mixer.Sound(path)
                sounds[key].set_volume(0.6)
                print(f"[sfx] loaded {fname}")
            except Exception:
                sounds[key] = None
        return sounds

    def _play(self, key: str):
        """Play a sound effect if loaded."""
        s = self.sfx.get(key)
        if s:
            s.play()

    # ── Sprite loading ────────────────────────────────────────────────────────

    SPRITE_DIR = os.path.join("assets", "sprites")

    # Maps sprite key → filename in assets/sprites/
    SPRITE_FILES = {
        # Players (2-frame animation)
        "cat_aries_1":   "cat_aries_1.png",
        "cat_aries_2":   "cat_aries_2.png",
        "cat_leo_1":     "cat_leo_1.png",
        "cat_leo_2":     "cat_leo_2.png",
        "cat_scorpio_1": "cat_scorpio_1.png",
        "cat_scorpio_2": "cat_scorpio_2.png",
        "cat_aquarius_1":"cat_aquarius_1.png",
        "cat_aquarius_2":"cat_aquarius_2.png",
        # Enemies (2-frame animation)
        "enemy_rat_1":      "enemy_rat_1.png",
        "enemy_rat_2":      "enemy_rat_2.png",
        "enemy_kamikaze_1": "enemy_kamikaze_1.png",
        "enemy_kamikaze_2": "enemy_kamikaze_2.png",
        "enemy_pigeon_1":   "enemy_pigeon_1.png",
        "enemy_pigeon_2":   "enemy_pigeon_2.png",
        "enemy_dog_1":      "enemy_dog_1.png",
        "enemy_dog_2":      "enemy_dog_2.png",
        # Items (static)
        "item_tuna":  "item_tuna.png",
        "item_drink": "item_drink.png",
    }

    # Background images — one per difficulty tier (3 waves each)
    BG_FILES = ["bg_1.png", "bg_2.png", "bg_3.png", "bg_4.png"]

    def _remove_white_bg(self, surf: pygame.Surface,
                          threshold: int = 30) -> pygame.Surface:
        """Remove white background using colorkey — instant, no pixel loops."""
        surf = surf.convert_alpha()
        # Use top-left corner pixel as background colour key
        bg_col = surf.get_at((0, 0))[:3]
        surf.set_colorkey(bg_col, pygame.RLEACCEL)
        return surf

    def _load_sprites(self):
        """
        Load all sprites and backgrounds from assets/sprites/.
        Missing files caught silently — geometry / colour fallback used instead.
        """
        for key, fname in self.SPRITE_FILES.items():
            path = os.path.join(self.SPRITE_DIR, fname)
            try:
                surf = pygame.image.load(path).convert_alpha()
                surf = self._remove_white_bg(surf)   # auto-remove white bg
                self.sprites[key] = surf
                print(f"[sprite] loaded {fname}")
            except FileNotFoundError:
                self.sprites[key] = None
            except Exception as e:
                print(f"[sprite] could not load {fname}: {e}")
                self.sprites[key] = None

        # Load backgrounds — scaled to window on load for efficiency
        self._bg_surfs: list[pygame.Surface | None] = []
        for fname in self.BG_FILES:
            path = os.path.join(self.SPRITE_DIR, fname)
            try:
                surf = pygame.image.load(path).convert()
                self._bg_surfs.append(surf)
                print(f"[bg] loaded {fname}")
            except FileNotFoundError:
                self._bg_surfs.append(None)
            except Exception as e:
                print(f"[bg] could not load {fname}: {e}")
                self._bg_surfs.append(None)

        self._current_bg_idx  = 0    # which background is showing
        self._bg_fade_alpha   = 255  # 255 = fully opaque new bg
        self._bg_fade_surface: pygame.Surface | None = None  # outgoing bg

    def _draw_sprite_or_shape(self, key_base: str, cx: float, cy: float,
                               size: int, fallback_fn, anim_offset: int = 0):
        """
        Draw a 2-frame animated sprite centred at (cx, cy).
        Tries key_base + '_1' and '_2'; falls back to key_base (static),
        then to fallback_fn() if nothing is loaded.
        Frame switches every 0.4 s, staggered by anim_offset.
        """
        period = 0.8
        phase  = (self._anim_timer + anim_offset * 0.13) % period
        frame  = "1" if phase < period / 2 else "2"

        surf = (self.sprites.get(f"{key_base}_{frame}")
                or self.sprites.get(key_base))   # static fallback
        if surf:
            scaled = pygame.transform.scale(surf, (size, size))
            self.screen.blit(scaled, (int(cx - size // 2), int(cy - size // 2)))
        else:
            fallback_fn()

    # ── Init ──────────────────────────────────────────────────────────────────

    def _init_game(self, cat: Cat):
        sx, sy = self.game_map.player_spawn
        self.player     = PlayerSprite(cat, float(sx + TILE_SIZE // 2),
                                            float(sy + TILE_SIZE // 2))
        self.enemies:   list[EnemySprite]  = []
        self.bullets:   list[Bullet]       = []
        self.particles: list[Particle]     = []
        self.items:     list[DroppedItem]  = []
        self.wave       = 1
        self.game_over  = False
        self.paused     = False
        self.shoot_cd   = 0.0
        self._anim_timer    = 0.0
        self._spawn_cd: dict[tuple, float] = {}
        self._wave_banner   = ""
        self._wave_banner_t = 0.0
        # Trickle spawn state
        self._wave_remaining = 0
        self._spawn_timer    = 0.0
        self._wave_speed_mul = 1.0
        self._kills_since_drop = 0   # drop item every 10 kills
        self._start_wave(self.wave)

    SPAWN_CD       = 3.0    # seconds before same E tile can reuse
    SPAWN_MIN_DIST = 200    # pixels — never spawn this close to the player

    def _pick_spawn(self, spawns: list[tuple]) -> tuple[float, float]:
        """Pick a spawn point not on cooldown, not too close to player,
        and confirmed to be on a valid floor tile inside the map."""
        px, py = self.player.x, self.player.y

        def is_valid(s):
            tx, ty = s
            cx = tx + TILE_SIZE // 2
            cy = ty + TILE_SIZE // 2
            too_close = math.hypot(cx - px, cy - py) < self.SPAWN_MIN_DIST
            in_map    = self.game_map.open_spawn_pos(cx, cy)
            return in_map and not too_close

        available = [s for s in spawns
                     if s not in self._spawn_cd and is_valid(s)]

        if not available:
            available = [s for s in spawns if is_valid(s)]

        if not available:
            # All valid points too close — pick furthest valid one
            valid_all = [s for s in spawns
                         if self.game_map.valid_floor_pos(
                             s[0] + TILE_SIZE // 2, s[1] + TILE_SIZE // 2)]
            available = sorted(valid_all,
                               key=lambda s: math.hypot(s[0] - px, s[1] - py),
                               reverse=True)[:1] or spawns[:1]

        chosen = random.choice(available)
        self._spawn_cd[chosen] = self.SPAWN_CD
        tx, ty = chosen
        # Use exact tile centre — no random jitter to avoid clipping into walls
        x = float(tx + TILE_SIZE // 2)
        y = float(ty + TILE_SIZE // 2)
        return x, y

    # ── Wave parameters ───────────────────────────────────────────────────────
    WAVE_BASE_COUNT  = 10    # enemies in wave 1
    WAVE_COUNT_STEP  = 10   # +10 enemies per wave
    WAVE_MAX_COUNT   = 100
    TRICKLE_INTERVAL = 2.0   # seconds between spawns (shrinks each wave)
    SPEED_STEP       = 0.08  # speed multiplier increase per wave

    def _start_wave(self, wave: int):
        """Set quota for this wave — enemies trickle in over time."""
        count = min(self.WAVE_BASE_COUNT + (wave - 1) * self.WAVE_COUNT_STEP,
                    self.WAVE_MAX_COUNT)
        self._wave_remaining = count
        self._spawn_interval = max(0.6, self.TRICKLE_INTERVAL - wave * 0.1)
        self._spawn_timer    = 0.0
        self._wave_speed_mul = 1.0 + (wave - 1) * self.SPEED_STEP
        # Spawn first 2 immediately
        for _ in range(min(2, self._wave_remaining)):
            self._trickle_one()
        self._wave_remaining = max(0, self._wave_remaining - 2)

    def _edge_spawn_pos(self) -> tuple[float, float]:
        """
        Spawn outside the visible screen, distributed across all 4 edges.
        Weighted away from the player's side for fairness.
        """
        margin = TILE_SIZE * 1.5
        edge = random.choice(["top", "bottom", "left", "right"])
        if edge == "top":
            return random.uniform(margin, self.W - margin), -margin
        elif edge == "bottom":
            return random.uniform(margin, self.W - margin), self.H + margin
        elif edge == "left":
            return -margin, random.uniform(margin, self.H - margin)
        else:
            return self.W + margin, random.uniform(margin, self.H - margin)

    def _trickle_one(self):
        """Spawn a single enemy from the map edge, far from the player."""
        x, y = self._edge_spawn_pos()
        wave = self.wave
        roll = random.random()
        if wave <= 2 or roll < 0.5:   enemy = GreenRat()
        elif roll < 0.7:               enemy = KamikazeRat()
        elif roll < 0.85:              enemy = IronPigeon()
        else:                          enemy = RiotDog()
        enemy.speed *= self._wave_speed_mul
        self.enemies.append(EnemySprite(enemy, float(x), float(y)))

    def _spawn_beat_enemies(self, count: int):
        """Beat-driven bonus spawn — fast rats from map edge."""
        for _ in range(count):
            x, y = self._edge_spawn_pos()
            e = GreenRat()
            e.speed *= self._wave_speed_mul
            self.enemies.append(EnemySprite(e, float(x), float(y)))

    def _fallback_spawns(self) -> list[tuple]:
        """Unused — kept for compatibility."""
        return [(TILE_SIZE * 2, TILE_SIZE * 2)]

    # ── Run loop ──────────────────────────────────────────────────────────────

    def run(self, clock: pygame.time.Clock, fps: int):
        while True:
            dt = clock.tick(fps) / 1000.0
            self._handle_events()
            if not self.game_over and not self.paused:
                self._update(dt)
            self._draw()
            pygame.display.flip()

    # ── Events ────────────────────────────────────────────────────────────────

    # ── Settings panel geometry (top-right corner) ────────────────────────────
    GEAR_SIZE   = 36
    PANEL_W     = 280
    PANEL_H     = 220

    def _gear_rect(self) -> pygame.Rect:
        # Bottom-right corner — away from all HUD elements
        return pygame.Rect(self.W - self.GEAR_SIZE - 8,
                           self.H - self.GEAR_SIZE - 8,
                           self.GEAR_SIZE, self.GEAR_SIZE)

    def _panel_rect(self) -> pygame.Rect:
        return pygame.Rect(self.W - self.PANEL_W - 8,
                           self.H - self.GEAR_SIZE - 8 - self.PANEL_H - 4,
                           self.PANEL_W, self.PANEL_H)

    def _vol_track_rect(self) -> pygame.Rect:
        pr = self._panel_rect()
        return pygame.Rect(pr.x + 20, pr.y + 80, self.PANEL_W - 40, 6)

    def _vol_handle_x(self) -> int:
        tr = self._vol_track_rect()
        return int(tr.x + self._volume * tr.width)

    def _handle_events(self):
        mx, my = pygame.mouse.get_pos()
        gear   = self._gear_rect()
        tr     = self._vol_track_rect()

        for event in pygame.event.get():
            # Block IME text input — only process key events, not composed text
            if event.type == pygame.TEXTINPUT:
                continue
            if event.type == pygame.QUIT:
                self._save_score(); pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.settings_open:
                        self.settings_open = False
                        self.paused = False
                    else:
                        self._save_score(); pygame.quit(); sys.exit()
                if event.key == pygame.K_r and self.game_over:
                    self._init_game(self.player.cat.__class__())

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Gear button — toggle settings
                if gear.collidepoint(mx, my):
                    self.settings_open = not self.settings_open
                    self.paused = self.settings_open
                elif self.settings_open:
                    pr = self._panel_rect()
                    # Volume slider drag start
                    handle = pygame.Rect(self._vol_handle_x() - 8,
                                         tr.y - 8, 16, 22)
                    if handle.collidepoint(mx, my) or tr.collidepoint(mx, my):
                        self._dragging_vol = True
                        self._volume = max(0.0, min(1.0,
                            (mx - tr.x) / tr.width))
                        pygame.mixer.music.set_volume(self._volume)
                    # "Change Music" button
                    btn = pygame.Rect(pr.x + 20, pr.y + 130, pr.width - 40, 32)
                    if btn.collidepoint(mx, my):
                        self.settings_open = False
                        self.paused = False
                        self._change_music()
                    # Close if click outside panel
                    if not pr.collidepoint(mx, my) and not gear.collidepoint(mx, my):
                        self.settings_open = False
                        self.paused = False
                elif not self.game_over:
                    self._shoot(pygame.mouse.get_pos())

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._dragging_vol = False

            if event.type == pygame.MOUSEMOTION and self._dragging_vol:
                self._volume = max(0.0, min(1.0,
                    (mx - tr.x) / tr.width))
                pygame.mixer.music.set_volume(self._volume)

    def _change_music(self):
        """Open file picker and reload beat detector with new music."""
        import subprocess, tempfile
        picker_code = """
import tkinter as tk
from tkinter import filedialog
import sys
root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
path = filedialog.askopenfilename(
    title="Choose music for Feral Frenzy",
    filetypes=[("Audio", "*.mp3 *.wav *.ogg"), ("All", "*.*")])
root.destroy()
if path: print(path, end="")
sys.exit(0)
"""
        try:
            import os, shutil
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py",
                                             delete=False) as f:
                f.write(picker_code); tmp = f.name
            result = subprocess.run([sys.executable, tmp],
                                    capture_output=True, text=True, timeout=120)
            os.unlink(tmp)
            src = result.stdout.strip()
            if src:
                dst = os.path.join("assets", os.path.basename(src))
                if os.path.abspath(src) != os.path.abspath(dst):
                    shutil.copy2(src, dst)
                self.beat.stop()
                self.beat = BeatDetector(dst)
                self.beat.play()
                self._has_music = True
        except Exception as e:
            print(f"[music] {e}")

    # ── Update ────────────────────────────────────────────────────────────────

    # How many enemies to trickle-spawn per beat (scales with wave)
    BEAT_SPAWN_BASE = 1
    BEAT_SPAWN_MAX  = 3

    def _update(self, dt: float):
        if self.shoot_cd > 0:
            self.shoot_cd -= dt

        keys = pygame.key.get_pressed()
        if (keys[pygame.K_SPACE] or keys[pygame.K_RETURN]) and self.shoot_cd <= 0:
            self._shoot_nearest()
            self.shoot_cd = self.SHOOT_INTERVAL

        # ── Beat-driven spawning — speeds up trickle on beat ────────────────
        if self.beat.update(dt):
            self._beat_flash = 0.08
            # On beat: instantly trigger next trickle if quota remains
            if self._wave_remaining > 0 and self._spawn_timer > 0:
                self._spawn_timer = 0.0   # fast-forward trickle timer

        if self._beat_flash > 0:
            self._beat_flash -= dt

        # Tick hit sound cooldown
        if self._hit_cd > 0:
            self._hit_cd -= dt

        # Tick animation timer
        self._anim_timer += dt
        if self._wave_banner_t > 0:
            self._wave_banner_t -= dt

        # Tick spawn point cooldowns
        for k in list(self._spawn_cd):
            self._spawn_cd[k] -= dt
            if self._spawn_cd[k] <= 0:
                del self._spawn_cd[k]

        self._move_player(dt)
        self._update_ambush(dt)
        self._move_bullets(dt)
        self._move_enemies(dt)
        self._check_bullet_enemy_collisions()
        self._check_player_enemy_collisions(dt)
        self._check_item_pickups()
        self._update_particles()

        # ── Trickle spawn timer ──────────────────────────────────────────────
        if self._wave_remaining > 0:
            self._spawn_timer -= dt
            if self._spawn_timer <= 0:
                self._trickle_one()
                self._wave_remaining -= 1
                self._spawn_timer = self._spawn_interval

        # ── Wave clear: all spawned AND all killed ───────────────────────────
        if self._wave_remaining <= 0 and len(self.enemies) == 0:
            self.wave += 1
            is_new_level = self.wave % 3 == 1 and self.wave > 1

            if is_new_level:
                self.game_map.regenerate(enemy_count=min(6 + self.wave, 12))
                self._spawn_cd.clear()
                self._wave_banner   = f"— LEVEL {(self.wave - 1) // 3 + 1} —"
                self._wave_banner_t = 2.5
                self._play("level_up")
            else:
                self._wave_banner   = f"Wave {self.wave}"
                self._wave_banner_t = 1.2
                self._play("wave_clear")

            self._start_wave(self.wave)
            # Move player to new map's spawn point after map regeneration
            if is_new_level:
                sx, sy = self.game_map.player_spawn
                self.player.x = float(sx + TILE_SIZE // 2)
                self.player.y = float(sy + TILE_SIZE // 2)
            # Wave clear bonus drop — always at player position (guaranteed valid)
            self.items.append(DroppedItem(
                self.player.x, self.player.y,
                random.choice(["tuna", "drink"])))

            # Switch background every 3 waves
            new_bg_idx = min((self.wave - 1) // 3, len(self._bg_surfs) - 1)
            if new_bg_idx != self._current_bg_idx:
                self._bg_fade_surface = self._bg_surfs[self._current_bg_idx]
                self._current_bg_idx  = new_bg_idx
                self._bg_fade_alpha   = 0

        if not self.player.cat.is_alive():
            self.game_over = True
            self._save_score()

    def _move_player(self, dt: float):
        keys = pygame.key.get_pressed()
        spd  = self.player.cat.speed * 160 * dt
        dx = dy = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1

        ndx, ndy = normalise(dx, dy)
        # Note: facing is NOT updated here — only shooting updates facing direction

        new_x = self.player.x + ndx * spd
        new_y = self.player.y + ndy * spd

        # Wall collision — try X and Y separately for sliding
        pr = self.player.rect
        test_x = pygame.Rect(new_x - pr.width // 2, pr.y, pr.width, pr.height)
        test_y = pygame.Rect(pr.x, new_y - pr.height // 2, pr.width, pr.height)

        blocked_x = any(test_x.colliderect(w) for w in self.game_map.wall_rects)
        blocked_y = any(test_y.colliderect(w) for w in self.game_map.wall_rects)

        if not blocked_x:
            self.player.x = max(PLAYER_SIZE, min(self.W - PLAYER_SIZE, new_x))
        if not blocked_y:
            self.player.y = max(PLAYER_SIZE, min(self.H - PLAYER_SIZE, new_y))

        if dx == 0 and dy == 0:
            self.player.still_time += dt
        else:
            self.player.still_time = 0
            self.player.ambush_ready = False

    def _update_ambush(self, dt: float):
        if self.player.still_time >= AMBUSH_WAIT and not self.player.ambush_ready:
            self.player.ambush_ready = True

    def _shoot(self, mouse_pos):
        """Mouse click — shoot toward cursor, update facing."""
        px, py  = self.player.x, self.player.y
        dx, dy  = normalise(mouse_pos[0] - px, mouse_pos[1] - py)
        self.player.facing = (dx, dy)
        is_amb  = self.player.ambush_ready
        dmg     = int(self.player.cat.basic_attack_damage() * (AMBUSH_MULT if is_amb else 1.0))
        self.bullets.append(Bullet(px, py, dx, dy, dmg, is_amb))
        if is_amb:
            self.player.ambush_ready = False
            self.player.still_time   = 0

    def _has_line_of_sight(self, x1: float, y1: float,
                           x2: float, y2: float) -> bool:
        """
        Step along the line from (x1,y1) to (x2,y2) in small increments.
        Returns True if no wall rect is hit along the way.
        """
        dist   = math.hypot(x2 - x1, y2 - y1)
        if dist == 0:
            return True
        steps  = max(4, int(dist / 16))   # one check every ~16 px
        dx, dy = (x2 - x1) / steps, (y2 - y1) / steps
        for i in range(1, steps):
            px = x1 + dx * i
            py = y1 + dy * i
            probe = pygame.Rect(px - 4, py - 4, 8, 8)
            if any(probe.colliderect(w) for w in self.game_map.wall_rects):
                return False
        return True

    def _shoot_nearest(self):
        """
        Space / Enter — smart auto-aim:
        Only lock onto enemies with clear line of sight.
        If none visible, hold last facing direction (don't shoot through walls).
        """
        px, py = self.player.x, self.player.y

        if not self.enemies:
            dx, dy = self.player.facing
        else:
            visible = [e for e in self.enemies
                       if self._has_line_of_sight(px, py, e.x, e.y)]
            if visible:
                target = min(visible,
                             key=lambda e: math.hypot(e.x - px, e.y - py))
                dx, dy = normalise(target.x - px, target.y - py)
                self.player.facing = (dx, dy)
            else:
                # All enemies behind walls — fire in last known direction
                dx, dy = self.player.facing

        is_amb = self.player.ambush_ready
        dmg    = int(self.player.cat.basic_attack_damage() * (AMBUSH_MULT if is_amb else 1.0))
        self.bullets.append(Bullet(px, py, dx, dy, dmg, is_amb))
        if is_amb:
            self.player.ambush_ready = False
            self.player.still_time   = 0

    def _move_bullets(self, dt: float):
        keep = []
        for b in self.bullets:
            b.x += b.dx;  b.y += b.dy
            # Remove if out of bounds or hits a wall
            if (0 <= b.x <= self.W and 0 <= b.y <= self.H and
                    not any(b.rect.colliderect(w) for w in self.game_map.wall_rects)):
                keep.append(b)
            else:
                # Small spark on wall impact
                self._explode(b.x, b.y, GREY, count=4)
        self.bullets = keep

    LEO_AURA_RADIUS = 180   # pixels
    LEO_SLOW_FACTOR = 0.45  # enemies move at 45 % speed inside aura

    def _move_enemies(self, dt: float):
        px, py   = self.player.x, self.player.y
        is_leo   = self.player.cat.__class__.__name__ == "Leo"

        for es in self.enemies:
            spd = es.enemy.speed * ENEMY_SPEED * 60 * dt

            # ── Leo King's Aura: slow nearby enemies ─────────────────────────
            if is_leo:
                dist = math.hypot(es.x - px, es.y - py)
                if dist <= self.LEO_AURA_RADIUS:
                    spd *= self.LEO_SLOW_FACTOR

            dx, dy = normalise(px - es.x, py - es.y)
            new_x  = es.x + dx * spd
            new_y  = es.y + dy * spd
            # Enemies move freely — no wall collision (they're mutant monsters!)
            es.x = new_x
            es.y = new_y

            if es.poison_timer > 0:
                es.poison_timer -= dt
                es.enemy.take_damage(int(5 * dt))

    def _check_bullet_enemy_collisions(self):
        live_bullets = []
        for b in self.bullets:
            hit = False
            for es in self.enemies:
                if b.rect.colliderect(es.rect):
                    es.enemy.take_damage(b.damage)
                    if isinstance(self.player.cat, Scorpio):
                        es.poison_timer = 3.0
                    hit = True
                    self._explode(es.x, es.y, es.colour(), count=6)
                    # Hit sound with cooldown to avoid spam
                    if self._hit_cd <= 0:
                        self._play("hit")
                        self._hit_cd = 0.08
                    break
            if not hit:
                live_bullets.append(b)
        self.bullets = live_bullets

        live_enemies = []
        for es in self.enemies:
            if es.enemy.is_alive():
                live_enemies.append(es)
            else:
                self.player.kills += 1
                self.player.score += 10
                self._play("kill")
                self._explode(es.x, es.y, es.colour(), count=14)
                # 10% chance to drop item on kill — at enemy death position
                if random.random() < 0.10:
                    self.items.append(DroppedItem(
                        es.x, es.y,
                        random.choice(["tuna", "drink"])))
                    self._play("item_drop")
                if isinstance(es.enemy, KamikazeRat):
                    if math.hypot(self.player.x - es.x,
                                  self.player.y - es.y) < es.enemy.EXPLOSION_RADIUS:
                        self.player.cat.take_damage(es.enemy.EXPLOSION_DAMAGE)
        self.enemies = live_enemies

    def _check_player_enemy_collisions(self, dt: float):
        if self.player.invincible_timer > 0:
            self.player.invincible_timer -= dt
            return
        for es in self.enemies:
            if self.player.rect.colliderect(es.rect):
                if isinstance(self.player.cat, Aquarius):
                    if random.random() < Aquarius.DODGE_CHANCE:
                        self._explode(self.player.x, self.player.y, TEAL, count=8)
                        self.player.invincible_timer = 0.5
                        return
                self.player.cat.take_damage(es.enemy.attack)
                self.player.invincible_timer = 0.8
                self._explode(self.player.x, self.player.y, (255, 80, 80), count=8)
                break

    def _check_item_pickups(self):
        keep = []
        for item in self.items:
            if self.player.rect.colliderect(item.rect):
                if item.kind == "tuna":
                    apply_tuna_can(self.player.cat)
                else:
                    apply_energy_drink(self.player.cat)
                self._explode(item.x, item.y, item.colour(), count=20)
                self._play("item_pick")
            else:
                keep.append(item)
        self.items = keep

    def _update_particles(self):
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.alive]

    def _explode(self, x, y, colour, count=12):
        for _ in range(count):
            self.particles.append(Particle(x, y, colour))

    # ── Score I/O ─────────────────────────────────────────────────────────────

    def _save_score(self):
        try:
            with open(SCORE_FILE, "a", encoding="utf-8") as f:
                f.write(f"{self.player.cat.__class__.__name__},"
                        f"{self.player.kills},{self.player.score},{self.wave}\n")
        except OSError:
            pass

    # ── Drawing ───────────────────────────────────────────────────────────────

    BG_FADE_SPEED = 180   # alpha units per second (255 = ~1.4 s full fade)

    def _draw(self):
        # ── Background ───────────────────────────────────────────────────────
        self.screen.fill(BLACK)
        cur_bg = self._bg_surfs[self._current_bg_idx] if self._bg_surfs else None

        if cur_bg:
            # Scale bg to fill window
            scaled_bg = pygame.transform.scale(cur_bg, (self.W, self.H))

            if self._bg_fade_alpha < 255:
                # Crossfade: draw outgoing bg first, then blend new one on top
                if self._bg_fade_surface:
                    old_scaled = pygame.transform.scale(
                        self._bg_fade_surface, (self.W, self.H))
                    self.screen.blit(old_scaled, (0, 0))
                scaled_bg.set_alpha(self._bg_fade_alpha)
                self.screen.blit(scaled_bg, (0, 0))
                scaled_bg.set_alpha(255)
                self._bg_fade_alpha = min(255,
                    self._bg_fade_alpha + int(self.BG_FADE_SPEED * (1/60)))
            else:
                self.screen.blit(scaled_bg, (0, 0))
                self._bg_fade_surface = None
        else:
            # No background image — draw subtle grid
            for x in range(0, self.W, 40):
                pygame.draw.line(self.screen, (25, 25, 35), (x, 0), (x, self.H))
            for y in range(0, self.H, 40):
                pygame.draw.line(self.screen, (25, 25, 35), (0, y), (self.W, y))

        self.game_map.draw(self.screen)
        self._draw_items()
        self._draw_bullets()
        self._draw_enemies()
        self._draw_player()
        self._draw_particles()

        # Beat flash
        if self._beat_flash > 0:
            alpha = int(self._beat_flash / 0.08 * 60)
            flash = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            pygame.draw.rect(flash, (255, 220, 80, alpha),
                             (0, 0, self.W, self.H), 6)
            self.screen.blit(flash, (0, 0))

        self._draw_hud()
        self._draw_gear_button()
        if self.settings_open:
            self._draw_settings()
        if self._wave_banner_t > 0:
            self._draw_wave_banner()
        if self.game_over:
            self._draw_game_over()
        if self.paused:
            self._draw_paused()

    def _draw_player(self):
        p   = self.player
        col = p.colour()
        if p.invincible_timer > 0 and int(p.invincible_timer * 10) % 2 == 0:
            col = WHITE
        if p.ambush_ready:
            pygame.draw.circle(self.screen, YELLOW,
                               (int(p.x), int(p.y)), p.size + 8, 2)

        key  = "cat_" + self.player.cat.__class__.__name__.lower()
        size = p.size * 2
        # Flip when shooting RIGHT (sprite default faces left)
        flip_x = self.player.facing[0] > 0

        def _geo():
            pygame.draw.circle(self.screen, col, (int(p.x), int(p.y)), p.size // 2)
            pygame.draw.polygon(self.screen, col, [
                (int(p.x) - 8,  int(p.y) - 10),
                (int(p.x) - 2,  int(p.y) - 18),
                (int(p.x) + 2,  int(p.y) - 10)])
            pygame.draw.polygon(self.screen, col, [
                (int(p.x) + 4,  int(p.y) - 10),
                (int(p.x) + 10, int(p.y) - 18),
                (int(p.x) + 14, int(p.y) - 10)])

        # Get sprite with animation frame
        period = 0.8
        phase  = self._anim_timer % period
        frame  = "1" if phase < period / 2 else "2"
        surf   = (self.sprites.get(f"{key}_{frame}") or self.sprites.get(key))

        if surf:
            if flip_x:
                surf = pygame.transform.flip(surf, True, False)
            scaled = pygame.transform.scale(surf, (size, size))
            self.screen.blit(scaled, (int(p.x - size // 2), int(p.y - size // 2)))
        else:
            _geo()

    def _draw_enemies(self):
        key_map = {
            "GreenRat":    "enemy_rat",
            "KamikazeRat": "enemy_kamikaze",
            "IronPigeon":  "enemy_pigeon",
            "RiotDog":     "enemy_dog",
        }
        for i, es in enumerate(self.enemies):
            col = (80, 220, 80) if es.poison_timer > 0 else es.colour()
            key = key_map.get(es.enemy.__class__.__name__, "enemy_rat")

            def _geo(es=es, col=col):
                pygame.draw.rect(self.screen, col, es.rect)

            self._draw_sprite_or_shape(key, es.x, es.y, es.size * 2, _geo,
                                       anim_offset=i)

            # HP bar always drawn on top of sprite
            bw    = es.size * 2
            ratio = es.enemy.hp / es.enemy.max_hp
            pygame.draw.rect(self.screen, DARK_RED,
                             (int(es.x) - bw // 2, int(es.y) - es.size - 6, bw, 4))
            pygame.draw.rect(self.screen, GREEN,
                             (int(es.x) - bw // 2, int(es.y) - es.size - 6,
                              int(bw * ratio), 4))

    def _draw_bullets(self):
        for b in self.bullets:
            pygame.draw.circle(self.screen, b.colour,
                               (int(b.x), int(b.y)), b.size // 2)

    def _draw_particles(self):
        for p in self.particles:
            pygame.draw.circle(self.screen, p.colour,
                               (int(p.x), int(p.y)), 3)

    def _draw_items(self):
        for item in self.items:
            key = "item_tuna" if item.kind == "tuna" else "item_drink"

            def _geo(item=item):
                pygame.draw.rect(self.screen, item.colour(), item.rect, border_radius=4)
                lbl = self.font_sm.render("T" if item.kind == "tuna" else "E", True, WHITE)
                self.screen.blit(lbl, (int(item.x) - 6, int(item.y) - 8))

            self._draw_sprite_or_shape(key, item.x, item.y, item.size * 2, _geo)

    def _draw_hud(self):
        p   = self.player
        cat = p.cat
        pad = 12

        # ── Semi-transparent background panel (left side) ────────────────────
        panel = pygame.Surface((380, 100), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 150))
        self.screen.blit(panel, (0, 0))

        # ── 5 hearts ─────────────────────────────────────────────────────────
        hearts     = p.hearts          # 0-5
        heart_size = 22
        for i in range(p.MAX_HEARTS):
            hx = pad + i * (heart_size + 4)
            hy = pad
            col = RED if i < hearts else DARK_RED
            # Draw heart shape using two circles + polygon
            pygame.draw.circle(self.screen, col,
                               (hx + heart_size//4, hy + heart_size//4),
                               heart_size//4)
            pygame.draw.circle(self.screen, col,
                               (hx + 3*heart_size//4, hy + heart_size//4),
                               heart_size//4)
            pygame.draw.polygon(self.screen, col, [
                (hx, hy + heart_size//3),
                (hx + heart_size//2, hy + heart_size),
                (hx + heart_size, hy + heart_size//3),
            ])

        self.screen.blit(
            self.font_sm.render(
                f"{cat.__class__.__name__}  |  Wave {self.wave}"
                f"  |  Kills {p.kills}  |  Score {p.score}"
                f"  |  Remaining {len(self.enemies) + self._wave_remaining}",
                True, LIGHT_GREY),
            (pad, pad + 30))

        if p.ambush_ready:
            self.screen.blit(
                self.font_sm.render("AMBUSH READY", True, YELLOW), (pad, pad + 68))
        elif p.still_time > 0.3:
            pct = min(100, int(p.still_time / AMBUSH_WAIT * 100))
            self.screen.blit(
                self.font_sm.render(f"Ambush charge: {pct}%", True, GREY),
                (pad, pad + 68))

        # ── Top-right controls strip ─────────────────────────────────────────
        ctrl = self.font_sm.render(
            "WASD move  |  Click shoot  |  Space/Enter auto-aim  |  ⚙ settings/pause  |  R restart",
            True, GREY)
        ctrl_panel = pygame.Surface((ctrl.get_width() + pad * 2, 44), pygame.SRCALPHA)
        ctrl_panel.fill((0, 0, 0, 130))
        self.screen.blit(ctrl_panel, (self.W - ctrl.get_width() - pad * 2, 0))
        self.screen.blit(ctrl, (self.W - ctrl.get_width() - pad, pad))

        # Music / beat indicator (top-right, second line)
        if self._has_music:
            music_txt = self.font_sm.render("♪ beat mode", True, YELLOW if self._beat_flash > 0 else GREY)
        else:
            music_txt = self.font_sm.render("♪ drop music in assets/ for beat mode", True, GREY)
        self.screen.blit(music_txt, (self.W - music_txt.get_width() - pad, pad + 20))

    def _draw_gear_button(self):
        """Small ⚙ button in the top-right corner."""
        r    = self._gear_rect()
        col  = (180, 180, 200) if not self.settings_open else YELLOW
        pygame.draw.rect(self.screen, (30, 30, 45), r, border_radius=6)
        pygame.draw.rect(self.screen, col, r, 2, border_radius=6)
        lbl = self.font_sm.render("⚙", True, col)
        self.screen.blit(lbl, (r.centerx - lbl.get_width() // 2,
                                r.centery - lbl.get_height() // 2))

    def _draw_settings(self):
        """Settings panel with volume slider and change-music button."""
        pr = self._panel_rect()

        # Panel background
        panel = pygame.Surface((pr.width, pr.height), pygame.SRCALPHA)
        panel.fill((20, 20, 35, 220))
        self.screen.blit(panel, (pr.x, pr.y))
        pygame.draw.rect(self.screen, YELLOW, pr, 2, border_radius=8)

        # Title
        title = self.font_md.render("Settings", True, YELLOW)
        self.screen.blit(title, (pr.centerx - title.get_width() // 2,
                                  pr.y + 12))

        # Volume label
        vol_lbl = self.font_sm.render(
            f"Volume: {int(self._volume * 100)} %", True, WHITE)
        self.screen.blit(vol_lbl, (pr.x + 20, pr.y + 55))

        # Slider track
        tr = self._vol_track_rect()
        pygame.draw.rect(self.screen, GREY, tr, border_radius=3)
        filled = pygame.Rect(tr.x, tr.y,
                             int(self._volume * tr.width), tr.height)
        pygame.draw.rect(self.screen, TEAL, filled, border_radius=3)

        # Slider handle
        hx = self._vol_handle_x()
        pygame.draw.circle(self.screen, WHITE, (hx, tr.centery), 9)
        pygame.draw.circle(self.screen, TEAL,  (hx, tr.centery), 6)

        # Change music button
        btn = pygame.Rect(pr.x + 20, pr.y + 130, pr.width - 40, 32)
        pygame.draw.rect(self.screen, (50, 50, 70), btn, border_radius=6)
        pygame.draw.rect(self.screen, GREY, btn, 1, border_radius=6)
        btn_lbl = self.font_sm.render("♪  Change Music", True, LIGHT_GREY)
        self.screen.blit(btn_lbl, (btn.centerx - btn_lbl.get_width() // 2,
                                    btn.centery - btn_lbl.get_height() // 2))

        # Hint
        hint = self.font_sm.render("ESC or ⚙ to close", True, GREY)
        self.screen.blit(hint, (pr.centerx - hint.get_width() // 2,
                                 pr.y + pr.height - 28))

    def _draw_wave_banner(self):
        """Centre-screen wave/level announcement that fades out."""
        alpha   = min(255, int(self._wave_banner_t * 180))
        is_lvl  = "LEVEL" in self._wave_banner
        colour  = YELLOW if is_lvl else LIGHT_GREY
        font    = self.font_lg if is_lvl else self.font_md
        txt     = font.render(self._wave_banner, True, colour)
        txt.set_alpha(alpha)
        self.screen.blit(txt, (
            self.W // 2 - txt.get_width()  // 2,
            self.H // 2 - txt.get_height() // 2))

    def _draw_game_over(self):
        overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        cx = self.W // 2

        go = self.font_lg.render("GAME OVER", True, RED)
        self.screen.blit(go, (cx - go.get_width() // 2, self.H // 2 - 130))

        info = self.font_md.render(
            f"Wave {self.wave}  ·  Kills {self.player.kills}"
            f"  ·  Score {self.player.score}",
            True, WHITE)
        self.screen.blit(info, (cx - info.get_width() // 2, self.H // 2 - 70))

        # ── Highscore table ──────────────────────────────────────────────────
        records = _load_scores()
        if records:
            best = max(records, key=lambda r: r["score"])
            self.screen.blit(
                self.font_sm.render("── All-time best ──", True, YELLOW),
                (cx - 90, self.H // 2 - 20))
            self.screen.blit(
                self.font_sm.render(
                    f"{best['zodiac']}  ·  Score {best['score']}"
                    f"  ·  Kills {best['kills']}  ·  Wave {best['wave']}",
                    True, LIGHT_GREY),
                (cx - 180, self.H // 2 + 10))

            # Top 3 sorted by score
            top3 = sorted(records, key=lambda r: r["score"], reverse=True)[:3]
            for i, rec in enumerate(top3):
                medal = ["#1", "#2", "#3"][i]
                col   = [YELLOW, LIGHT_GREY, ORANGE][i]
                line  = (f"{medal}  {rec['zodiac']:<10}"
                         f"  Score {rec['score']:>5}"
                         f"  Kills {rec['kills']:>3}"
                         f"  Wave {rec['wave']:>2}")
                self.screen.blit(
                    self.font_sm.render(line, True, col),
                    (cx - 190, self.H // 2 + 40 + i * 24))

        hint = self.font_sm.render(
            "Press R to restart  |  ESC to quit", True, LIGHT_GREY)
        self.screen.blit(hint, (cx - hint.get_width() // 2, self.H // 2 + 150))

    def _draw_paused(self):
        txt = self.font_lg.render("PAUSED", True, YELLOW)
        self.screen.blit(txt, (self.W // 2 - txt.get_width() // 2, self.H // 2 - 30))