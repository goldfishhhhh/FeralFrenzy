# main.py — ENTRY POINT
# Run: python main.py
#
# Phase 3+: window auto-fits map, IME disabled, beat-driven spawning,
#           in-game music upload (press M on select screen)

import os
import shutil
import sys
import pygame

from logic.cat import Aries, Leo, Scorpio, Aquarius
from engine.map_loader import load_map
from engine.renderer import GameRenderer

FPS   = 60
TITLE = "Feral Frenzy"
TILE  = 40
MIN_W, MIN_H = 480, 360   # absolute floor for tiny maps only
ASSETS_DIR   = "assets"

ZODIAC_CLASSES = [Aries, Leo, Scorpio, Aquarius]
MAP_FILE = os.path.join("maps", "level1.txt")
SUPPORTED_AUDIO = (".mp3", ".wav", ".ogg")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _map_window_size() -> tuple[int, int]:
    try:
        grid = load_map(MAP_FILE)
        cols = max(len(row) for row in grid)
        rows = len(grid)
        return max(MIN_W, cols * TILE), max(MIN_H, rows * TILE)
    except Exception:
        return 800, 600


def _pick_music_file() -> str | None:
    """
    Open a native file-picker dialog.
    On macOS, tkinter must run on the main thread but pygame already owns it,
    so we use a subprocess instead — fully safe on all platforms.
    Returns the chosen file path, or None if cancelled / error.
    """
    import subprocess
    import tempfile

    # Small self-contained picker script written to a temp file
    picker_code = """
import tkinter as tk
from tkinter import filedialog
import sys

root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)
path = filedialog.askopenfilename(
    title="Choose a music file for Feral Frenzy",
    filetypes=[("Audio files", "*.mp3 *.wav *.ogg"), ("All files", "*.*")],
)
root.destroy()
if path:
    print(path, end="")
sys.exit(0)
"""
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py",
                                         delete=False) as f:
            f.write(picker_code)
            tmp_path = f.name

        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True, text=True, timeout=120
        )
        os.unlink(tmp_path)   # clean up temp file

        path = result.stdout.strip()
        return path if path else None
    except Exception as e:
        print(f"[music picker] {e}")
        return None


def _import_music(src_path: str) -> str | None:
    """
    Copy the chosen file into assets/ and return the new path.
    If it's already inside assets/, just return the path as-is.
    Returns None on failure.
    """
    try:
        os.makedirs(ASSETS_DIR, exist_ok=True)
        fname    = os.path.basename(src_path)
        dst_path = os.path.join(ASSETS_DIR, fname)

        if os.path.abspath(src_path) != os.path.abspath(dst_path):
            shutil.copy2(src_path, dst_path)
            print(f"[music] Copied '{fname}' → {ASSETS_DIR}/")
        else:
            print(f"[music] '{fname}' is already in {ASSETS_DIR}/")

        return dst_path
    except Exception as e:
        print(f"[music] Could not import file: {e}")
        return None


# ── Select screen ─────────────────────────────────────────────────────────────

def _load_select_sprites() -> dict:
    """Load cat and enemy sprites for the selection screen."""
    sprite_dir = os.path.join("assets", "sprites")
    keys = {
        "cat_aries":    "cat_aries_1.png",
        "cat_leo":      "cat_leo_1.png",
        "cat_scorpio":  "cat_scorpio_1.png",
        "cat_aquarius": "cat_aquarius_1.png",
        "enemy_rat":      "enemy_rat_1.png",
        "enemy_kamikaze": "enemy_kamikaze_1.png",
        "enemy_pigeon":   "enemy_pigeon_1.png",
        "enemy_dog":      "enemy_dog_1.png",
        "item_tuna":    "item_tuna.png",
        "item_drink":   "item_drink.png",
    }
    sprites = {}
    for k, fname in keys.items():
        try:
            surf = pygame.image.load(os.path.join(sprite_dir, fname)).convert_alpha()
            bg_col = surf.get_at((0, 0))[:3]
            surf.set_colorkey(bg_col, pygame.RLEACCEL)
            sprites[k] = surf
        except Exception:
            sprites[k] = None
    return sprites


def choose_zodiac(screen: pygame.Surface, clock: pygame.time.Clock,
                  w: int, h: int):
    """
    Selection screen with two tabs:
      1-4   — pick a Zodiac cat (default tab)
      Tab   — toggle Bestiary
      M     — import music
    """
    pygame.font.init()
    font_big  = pygame.font.SysFont(None, 52)
    font_md   = pygame.font.SysFont(None, 34)
    font_sm   = pygame.font.SysFont(None, 26)
    font_xs   = pygame.font.SysFont(None, 20)

    sprites = _load_select_sprites()

    ZODIAC_DATA = [
        ("1", "Aries",    "cat_aries",    (255,140,0),
         "Berserker",
         "Low HP = more damage. The angrier, the stronger!"),
        ("2", "Leo",      "cat_leo",      (255,220,60),
         "King's Aura",
         "Nearby enemies move slower. You are the boss."),
        ("3", "Scorpio",  "cat_scorpio",  (160,80,220),
         "Venom Claws",
         "Every hit poisons enemies. Damage over time!"),
        ("4", "Aquarius", "cat_aquarius", (40,200,180),
         "Lucky Dodge",
         "25% chance to dodge any hit. Pure luck saves you!"),
    ]

    ENEMY_DATA = [
        ("enemy_rat",      "Green Rat",      (60,200,80),
         "Weak but fast",
         "HP: 20  ATK: 5  — Runs straight at you. Easy to kill."),
        ("enemy_kamikaze", "Boom Rat",       (140,20,20),
         "Explodes on death!",
         "HP: 20  ATK: 12  — Blows up when it dies. Stay back!"),
        ("enemy_pigeon",   "Iron Pigeon",    (100,100,110),
         "Flies over walls",
         "HP: 45  ATK: 12  — Shoots at you from far away. Kill first!"),
        ("enemy_dog",      "Riot Dog",       (220,50,50),
         "Huge and tough",
         "HP: 350  ATK: 30  — Very hard to kill. Do NOT fight alone!"),
    ]

    bg        = (20, 20, 30)
    tab       = "zodiac"   # "zodiac" | "bestiary"
    from engine.music_beat import find_music_file
    music_status = _music_status_text(find_music_file(ASSETS_DIR))

    def draw_tab_bar():
        bar_y = h - 90
        pygame.draw.line(screen, (50, 50, 70), (0, bar_y), (w, bar_y))
        active_lbl = font_sm.render(
            "[ ZODIAC ]   Tab → bestiary" if tab == "zodiac" else "zodiac ←  Tab   [ BESTIARY ]",
            True, (255, 220, 80))
        hint = font_xs.render("M = upload music", True, (80, 80, 90))
        screen.blit(active_lbl, (w//2 - active_lbl.get_width()//2, bar_y + 10))
        screen.blit(hint,       (w//2 - hint.get_width()//2,       bar_y + 34))

    def draw_zodiac():
        title = font_big.render("Choose your Zodiac Cat", True, (255, 220, 80))
        screen.blit(title, (w//2 - title.get_width()//2, 20))

        spr_sz  = 72
        row_h   = (h - 160) // 4   # distribute 4 rows evenly
        left_x  = w // 6
        text_x  = left_x + spr_sz + 24

        for i, (key, name, spr_key, col, passive, desc) in enumerate(ZODIAC_DATA):
            cy = 90 + i * row_h + row_h // 2

            # Highlight bar on hover-like feel
            bar = pygame.Surface((w - 80, row_h - 8), pygame.SRCALPHA)
            bar.fill((255, 220, 80, 12) if i % 2 == 0 else (80, 80, 120, 12))
            screen.blit(bar, (40, 90 + i * row_h))

            # Sprite
            spr = sprites.get(spr_key)
            if spr:
                scaled = pygame.transform.scale(spr, (spr_sz, spr_sz))
                screen.blit(scaled, (left_x - spr_sz//2, cy - spr_sz//2))
            else:
                pygame.draw.circle(screen, col, (left_x, cy), spr_sz//2)

            # Key badge
            badge = font_big.render(f"[{key}]", True, (255, 220, 80))
            screen.blit(badge, (left_x + spr_sz//2 + 8, cy - badge.get_height()//2))

            # Name + passive on one line
            nm  = font_md.render(f"{name}  —  {passive}", True, col)
            screen.blit(nm, (text_x + 60, cy - 22))

            # Description (single line, condensed)
            short_desc = desc.replace("\n", "  ")
            dl = font_xs.render(short_desc, True, (140, 140, 155))
            screen.blit(dl, (text_x + 60, cy + 10))

    def draw_bestiary():
        title = font_big.render("Enemy Bestiary", True, (220, 80, 80))
        screen.blit(title, (w//2 - title.get_width()//2, 20))

        spr_sz  = 72
        row_h   = (h - 160) // 4
        left_x  = w // 6
        text_x  = left_x + spr_sz + 24

        for i, (spr_key, name, col, role, desc) in enumerate(ENEMY_DATA):
            cy = 90 + i * row_h + row_h // 2

            bar = pygame.Surface((w - 80, row_h - 8), pygame.SRCALPHA)
            bar.fill((220, 60, 60, 12) if i % 2 == 0 else (80, 80, 120, 12))
            screen.blit(bar, (40, 90 + i * row_h))

            spr = sprites.get(spr_key)
            if spr:
                scaled = pygame.transform.scale(spr, (spr_sz, spr_sz))
                screen.blit(scaled, (left_x - spr_sz//2, cy - spr_sz//2))
            else:
                pygame.draw.rect(screen, col,
                                 (left_x - spr_sz//2, cy - spr_sz//2, spr_sz, spr_sz))

            # Name + role
            nm = font_md.render(f"{name}  —  {role}", True, col)
            screen.blit(nm, (text_x + 60, cy - 22))

            # Stats line
            short_desc = desc.split("\n")[0]
            dl = font_xs.render(desc.replace("\n", "  "), True, (140, 140, 155))
            screen.blit(dl, (text_x + 60, cy + 10))

    while True:
        screen.fill(bg)

        if tab == "zodiac":
            draw_zodiac()
        else:
            draw_bestiary()

        draw_tab_bar()
        _draw_music_bar(screen, font_xs, music_status, w, h)
        pygame.display.flip()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.TEXTINPUT:
                continue
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    tab = "bestiary" if tab == "zodiac" else "zodiac"
                if tab == "zodiac":
                    if event.key in (pygame.K_1, pygame.K_KP1): return ZODIAC_CLASSES[0]()
                    if event.key in (pygame.K_2, pygame.K_KP2): return ZODIAC_CLASSES[1]()
                    if event.key in (pygame.K_3, pygame.K_KP3): return ZODIAC_CLASSES[2]()
                    if event.key in (pygame.K_4, pygame.K_KP4): return ZODIAC_CLASSES[3]()
                if event.key == pygame.K_m:
                    src = _pick_music_file()
                    if src:
                        dst = _import_music(src)
                        music_status = _music_status_text(dst)
                    else:
                        music_status = "No file selected."


def _music_status_text(path: str | None) -> str:
    if path and os.path.isfile(path):
        return f"♪  {os.path.basename(path)}  — beat mode active"
    return "♪  No music loaded"


def _draw_music_bar(surface, font, text: str, w: int, h: int):
    """Render a subtle music-status strip at the bottom of the screen."""
    has_music = "beat mode active" in text
    colour    = (180, 160, 60) if has_music else (90, 90, 100)
    surf      = font.render(text, True, colour)
    bar_rect  = pygame.Rect(0, h - 40, w, 40)
    pygame.draw.rect(surface, (30, 30, 40), bar_rect)
    surface.blit(surf, (w // 2 - surf.get_width() // 2, h - 28))

    hint = font.render("M = upload your custom background music", True, (70, 70, 80))
    surface.blit(hint, (w - hint.get_width() - 16, h - 28))


# ── Entry ─────────────────────────────────────────────────────────────────────

def show_title_screen(screen: pygame.Surface, clock: pygame.time.Clock,
                      w: int, h: int):
    """
    Animated title screen showing cover image.
    Press any key or click to continue.
    """
    font_title = pygame.font.SysFont(None, 80)
    font_hint  = pygame.font.SysFont(None, 32)

    # Try to load cover image from assets/sprites/cover.png
    cover = None
    for fname in ("cover.png", "cover.jpg", "cover.jpeg"):
        path = os.path.join("assets", "sprites", fname)
        try:
            cover = pygame.image.load(path).convert()
            # Scale to fit screen while keeping aspect ratio
            img_w, img_h = cover.get_size()
            scale = min(w / img_w, h / img_h)
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            cover = pygame.transform.scale(cover, (new_w, new_h))
            break
        except Exception:
            continue

    pulse = 0.0   # for pulsing "press any key" text

    while True:
        dt = clock.tick(FPS) / 1000.0
        pulse += dt * 2.5

        screen.fill((10, 10, 18))

        if cover:
            cx = (w - cover.get_width())  // 2
            cy = (h - cover.get_height()) // 2
            screen.blit(cover, (cx, cy))
            # Dark gradient overlay at bottom for text legibility
            overlay = pygame.Surface((w, 120), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, h - 120))
        else:
            # No cover — draw text title
            title = font_title.render("FERAL FRENZY", True, (255, 220, 80))
            screen.blit(title, (w//2 - title.get_width()//2, h//3))

        # Pulsing hint
        import math
        alpha = int(180 + 75 * math.sin(pulse))
        hint  = font_hint.render("Press any key to start", True, (255, 255, 255))
        hint.set_alpha(alpha)
        screen.blit(hint, (w//2 - hint.get_width()//2, h - 70))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.TEXTINPUT:
                continue
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return   # proceed to zodiac selection


def main():
    pygame.init()
    pygame.mixer.init()

    w, h = _map_window_size()
    screen = pygame.display.set_mode((w, h))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    show_title_screen(screen, clock, w, h)
    cat = choose_zodiac(screen, clock, w, h)

    renderer = GameRenderer(screen, cat, w, h)
    renderer.run(clock, FPS)


if __name__ == "__main__":
    main()