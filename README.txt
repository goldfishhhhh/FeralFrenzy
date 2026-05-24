================================================================
  FERAL FRENZY  —  COMP9001 Final Project
================================================================

Author : Jovi
Course : COMP9001
Due    : 24 May 2026


----------------------------------------------------------------
REQUIREMENTS
----------------------------------------------------------------
Python  3.10 or later
Pygame  2.x     ->  conda install pygame
                    (or: pip install pygame)

All other libraries are Python standard library only:
  os, sys, math, random, struct, shutil, subprocess, tempfile,
  unittest, tkinter (built-in on macOS)


----------------------------------------------------------------
HOW TO RUN
----------------------------------------------------------------
1. Open a terminal and go to the FeralFrenzy/ folder:

      cd path/to/FeralFrenzy

2. Generate map files (first time only):

      python generate_maps.py

3. Start the game:

      python main.py


----------------------------------------------------------------
HOW TO RUN TESTS  (no Pygame required)
----------------------------------------------------------------
      python -m unittest discover -s tests

Expected output:  Ran 9 tests in 0.000s   OK


----------------------------------------------------------------
CONTROLS
----------------------------------------------------------------
WASD / Arrow keys     Move
Left-click            Shoot toward mouse cursor
Space / Enter (hold)  Auto-aim continuous fire
                      (targets nearest enemy with clear line of sight)
R                     Restart  (on Game Over screen)
ESC                   Quit  (or close Settings panel)
Tab                   Switch tab on selection screen
M                     Import custom music  (on selection screen)
⚙ button             Open Settings / Pause  (bottom-right corner)


----------------------------------------------------------------
GAME FLOW
----------------------------------------------------------------
Title Screen  ->  Press any key
    |
    v
Selection Screen  (1/2/3/4 to pick Zodiac Cat)
    |  Tab = Enemy Bestiary
    |  M   = Upload custom music (.mp3/.wav/.ogg)
    v
Game
    - Survive endless waves of mutant enemies
    - Wave clear = all enemies in quota defeated
    - Every 3 waves = new map + new background
    - Collect dropped items to restore HP or gain speed
    - Beat-driven spawning: music BPM accelerates enemy arrival


----------------------------------------------------------------
ZODIAC CATS
----------------------------------------------------------------
1  Aries     Berserker      Low HP = more damage. The angrier, the stronger!
2  Leo       King's Aura    Nearby enemies move at 45% speed.
3  Scorpio   Venom Claws    Every hit poisons enemies (5 DPS for 3 sec).
4  Aquarius  Lucky Dodge    25% chance to fully dodge any incoming hit.


----------------------------------------------------------------
ENEMIES
----------------------------------------------------------------
Green Rat      Weak but fast. Charges straight at you. Easy kills.
Boom Rat       Explodes on death. 40 damage in wide radius. Stay back!
Iron Pigeon    Flies over walls. Shoots from range. Kill first!
Riot Dog       350 HP. Very tough. Never fight head-on.


----------------------------------------------------------------
ITEMS
----------------------------------------------------------------
Tuna Can       Increases max HP and attack damage permanently.
Energy Drink   Slightly increases movement speed.

Items drop at enemy death location (10% chance per kill).
One item also drops after each wave is cleared.


----------------------------------------------------------------
PROJECT STRUCTURE
----------------------------------------------------------------
main.py                 Entry point — run this file
generate_maps.py        Run once to create all 50 map files
logic/
  cat.py                Player classes: Cat base + 4 Zodiac subclasses
  enemy.py              Enemy types (GreenRat, KamikazeRat, etc.)
  weapons.py            Weapon strategy pattern
  items.py              Passive item effects
engine/
  renderer.py           Pygame game loop, rendering, all game logic
  map_loader.py         Reads level .txt tile files (File I/O)
  music_beat.py         Beat detection using pygame.mixer only
maps/
  level1.txt            50 pre-generated tile maps (W=wall .=floor P=player E=enemy)
  ...level50.txt
tests/
  test_logic.py         9 unit tests — pure logic, no Pygame needed
assets/
  sprites/              Player, enemy, item, background PNG files
    cover.png           Title screen cover image
    bg_1.png ... bg_4.png  In-game backgrounds (one per level tier)
  sfx/                  Sound effects (.wav)
    hit.wav  kill.wav  item_drop.wav  item_pick.wav
    wave_clear.wav  level_up.wav
  *.mp3 / *.wav         Custom music for beat-driven spawning
highscore.txt           Auto-created on first Game Over


----------------------------------------------------------------
ADVANCED TOPICS IMPLEMENTED  (COMP9001)
----------------------------------------------------------------
1. Object-Oriented Programming
     Cat base class + 4 Zodiac subclasses, each overriding
     basic_attack_damage() and carrying unique passive behaviour.
     Enemy hierarchy with 4 subclasses.
     Weapon strategy pattern allows runtime swap of attack logic.

2. File I/O
     map_loader.py reads level*.txt with open() to build the
     tile grid at runtime — edit the .txt and the map changes.
     highscore.txt is appended on every Game Over and read back
     on the Game Over screen to display the all-time Top 3.

3. Exception Handling
     try/except FileNotFoundError around every file read
     (maps, scores, audio, sprites). Missing files trigger
     graceful fallback instead of crashing.
     try/except ValueError guards score parsing against
     corrupted lines in highscore.txt.

4. Test-Driven Development  (unittest)
     test_logic.py covers 9 test cases across damage calculation,
     Berserker passive scaling, weapon multipliers, and item
     effects — all runnable without Pygame.


----------------------------------------------------------------
KNOWN NOTES
----------------------------------------------------------------
- Pygame may print a UserWarning about pkg_resources on
  Python 3.13. This is a Pygame packaging issue and does
  not affect gameplay.
- macOS may show IME-related messages in the terminal on
  startup. These are system-level and can be ignored.
- Beat detection is amplitude-based. High-contrast music
  (EDM, metal) works best for visible spawning effects.


================================================================