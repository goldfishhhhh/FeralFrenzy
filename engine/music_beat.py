# engine/music_beat.py
# Beat detection using only pygame.mixer — no numpy / librosa required.
#
# How it works:
#   pygame.mixer.Sound can read raw PCM samples via get_raw().
#   We slice the audio into short windows (~50 ms) and compute the
#   root-mean-square (RMS) energy of each window manually.
#   A "beat" fires when RMS crosses a threshold that is dynamically
#   updated based on the recent average (so it adapts to quiet/loud
#   sections automatically).
#
# Usage:
#   detector = BeatDetector("assets/my_song.mp3")
#   detector.play()
#   # in game loop:
#   if detector.update(dt):   # returns True on beat
#       spawn_enemies()

import os
import struct
import pygame


# Audio files we will scan for in assets/
SUPPORTED = (".mp3", ".wav", ".ogg")


def find_music_file(folder: str = "assets") -> str | None:
    """Return the first supported audio file found in *folder*, or None."""
    try:
        for fname in sorted(os.listdir(folder)):
            if fname.lower().endswith(SUPPORTED):
                return os.path.join(folder, fname)
    except FileNotFoundError:
        pass
    return None


class BeatDetector:
    """
    Lightweight beat detector that works purely with pygame.

    Parameters
    ----------
    filepath : str
        Path to the audio file.
    sensitivity : float
        How much above the rolling average the RMS must spike to count
        as a beat. 1.4 = 40 % above average (good default).
    cooldown : float
        Minimum seconds between beats (prevents rapid double-triggers).
    window_sec : float
        Length of each analysis window in seconds.
    history : int
        Number of windows kept for computing the rolling average.
    """

    def __init__(self, filepath: str, sensitivity: float = 1.4,
                 cooldown: float = 0.3, window_sec: float = 0.05,
                 history: int = 43):
        self.filepath    = filepath
        self.sensitivity = sensitivity
        self.cooldown    = cooldown
        self.window_sec  = window_sec

        self._timer      = 0.0   # counts up; beat fires when >= next_beat_t
        self._cd_timer   = 0.0   # cooldown countdown
        self._history    : list[float] = [0.01] * history
        self._windows    : list[list[int]] = []
        self._win_idx    = 0
        self._loaded     = False
        self._fallback_interval = 0.5   # used when no audio file available

        self._load(filepath)

    # ── Loading ───────────────────────────────────────────────────────────────

    def _load(self, path: str):
        """
        Pre-compute per-window RMS values from raw PCM samples.
        Falls back gracefully if the file is missing or unreadable.
        """
        try:
            sound      = pygame.mixer.Sound(path)
            raw        = sound.get_raw()           # bytes of 16-bit signed PCM
            freq, size, channels = pygame.mixer.get_init()
            samples_per_window   = max(1, int(freq * self.window_sec))
            bytes_per_sample     = abs(size) // 8 * channels

            windows = []
            offset  = 0
            fmt     = "<h" if size < 0 else "<H"   # signed / unsigned 16-bit
            while offset + bytes_per_sample <= len(raw):
                chunk = raw[offset: offset + samples_per_window * bytes_per_sample]
                vals  = [struct.unpack_from(fmt, chunk, i)[0]
                         for i in range(0, len(chunk), bytes_per_sample)]
                if vals:
                    rms = (sum(v * v for v in vals) / len(vals)) ** 0.5
                    windows.append(rms)
                offset += samples_per_window * bytes_per_sample

            self._windows = windows
            self._loaded  = True
            print(f"[beat] Loaded '{path}' — {len(windows)} windows "
                  f"@ {self.window_sec*1000:.0f} ms each")
        except Exception as e:
            print(f"[beat] Could not analyse '{path}': {e} — using tempo fallback")

    # ── Playback ──────────────────────────────────────────────────────────────

    def play(self, loops: int = -1):
        """Start playing the music track (loops=-1 = infinite)."""
        try:
            pygame.mixer.music.load(self.filepath)
            pygame.mixer.music.play(loops)
        except Exception as e:
            print(f"[beat] Music playback failed: {e}")

    def stop(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    # ── Per-frame update ──────────────────────────────────────────────────────

    def update(self, dt: float) -> bool:
        """
        Call once per frame with the elapsed time in seconds.
        Returns True exactly on frames where a beat is detected.
        """
        if self._cd_timer > 0:
            self._cd_timer -= dt

        self._timer += dt

        if self._loaded and self._windows:
            return self._analyse_beat()
        else:
            return self._fallback_beat()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _analyse_beat(self) -> bool:
        """Advance through pre-computed RMS windows and detect spikes."""
        idx = int(self._timer / self.window_sec) % len(self._windows)
        if idx == self._win_idx:
            return False          # same window as last frame — nothing new
        self._win_idx = idx

        rms     = self._windows[idx]
        avg     = sum(self._history) / len(self._history)
        # Rolling history update
        self._history.pop(0)
        self._history.append(rms)

        if rms > avg * self.sensitivity and self._cd_timer <= 0:
            self._cd_timer = self.cooldown
            return True
        return False

    def _fallback_beat(self) -> bool:
        """No audio data — fire at a fixed tempo (120 BPM ≈ 0.5 s)."""
        if self._timer >= self._fallback_interval and self._cd_timer <= 0:
            self._timer    = 0.0
            self._cd_timer = self.cooldown
            return True
        return False