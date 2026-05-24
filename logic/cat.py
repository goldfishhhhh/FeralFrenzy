# logic/cat.py
# Player character classes — pure Python, no Pygame.
# Cat (base class) + one subclass per Zodiac sign.


class Cat:
    """Base class for all player characters."""

    def __init__(self, name: str, hp: int, attack: int, speed: float):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.attack = attack
        self.speed = speed

    def take_damage(self, amount: int) -> None:
        """Reduce HP by amount, flooring at 0."""
        self.hp = max(0, self.hp - amount)

    def is_alive(self) -> bool:
        return self.hp > 0

    def basic_attack_damage(self) -> int:
        """Returns damage for a standard melee hit."""
        return self.attack

    def __repr__(self):
        return f"{self.__class__.__name__}(hp={self.hp}/{self.max_hp})"


class Aries(Cat):
    """♈ Explosive Orange Tabby — Berserker passive."""

    def __init__(self):
        super().__init__(name="Aries", hp=120, attack=18, speed=1.2)

    def basic_attack_damage(self) -> int:
        """Berserker: damage scales up as HP drops."""
        ratio = 1 - (self.hp / self.max_hp)          # 0.0 (full) → 1.0 (empty)
        bonus = int(ratio * self.attack)              # up to +100 % extra
        return self.attack + bonus


class Leo(Cat):
    """♌ Lionhearted Maine Coon — King's Aura passive."""

    def __init__(self):
        super().__init__(name="Leo", hp=150, attack=14, speed=1.0)

    # King's Aura (slow nearby enemies) is applied in the engine layer.


class Scorpio(Cat):
    """♏ Shadow Void Cat — Venomous Claws passive."""

    POISON_DPS = 5          # damage per second while poisoned
    POISON_DURATION = 3     # seconds

    def __init__(self):
        super().__init__(name="Scorpio", hp=100, attack=16, speed=1.1)

    def poison_info(self) -> dict:
        """Returns poison parameters to be applied by the engine."""
        return {"dps": self.POISON_DPS, "duration": self.POISON_DURATION}


class Aquarius(Cat):
    """♒ Quantum Alien Meow — Schrödinger's Dodge passive."""

    DODGE_CHANCE = 0.25     # 25 % chance to fully evade a hit

    def __init__(self):
        super().__init__(name="Aquarius", hp=110, attack=15, speed=1.15)
