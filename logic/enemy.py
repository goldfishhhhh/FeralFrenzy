# logic/enemy.py
# Enemy types — pure Python, no Pygame.


class Enemy:
    """Base class for all enemies."""

    def __init__(self, name: str, hp: int, attack: int, speed: float):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.attack = attack
        self.speed = speed

    def take_damage(self, amount: int) -> None:
        self.hp = max(0, self.hp - amount)

    def is_alive(self) -> bool:
        return self.hp > 0

    def __repr__(self):
        return f"{self.__class__.__name__}(hp={self.hp}/{self.max_hp})"


class GreenRat(Enemy):
    """Swarm / cannon fodder."""
    def __init__(self):
        super().__init__(name="Green Rat", hp=20, attack=5, speed=1.4)


class KamikazeRat(Enemy):
    """Zone denial — explodes on death."""
    EXPLOSION_DAMAGE = 30
    EXPLOSION_RADIUS = 80   # pixels, used by engine

    def __init__(self):
        super().__init__(name="Kamikaze Rat", hp=15, attack=0, speed=1.6)


class IronPigeon(Enemy):
    """Ranged harassment."""
    def __init__(self):
        super().__init__(name="Iron Pigeon", hp=35, attack=8, speed=0.8)


class NeonCrow(Enemy):
    """High-value target — buffs nearby enemies."""
    BUFF_RADIUS = 150
    SPEED_BUFF = 1.3

    def __init__(self):
        super().__init__(name="Neon Crow", hp=50, attack=0, speed=0.5)


class RiotDog(Enemy):
    """Heavy tank — frontal immunity."""
    def __init__(self):
        super().__init__(name="Riot Dog", hp=200, attack=25, speed=0.6)
