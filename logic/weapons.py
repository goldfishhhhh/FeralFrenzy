# logic/weapons.py
# Weapon strategy pattern — each weapon overrides attack behaviour.


class Weapon:
    """Abstract base — default unarmed claws."""

    def melee_damage(self, base_attack: int) -> int:
        return base_attack

    def ranged_damage(self, base_attack: int) -> int:
        return int(base_attack * 0.75)

    def __repr__(self):
        return self.__class__.__name__


class Shotgun(Weapon):
    """Sawed-off Shotgun: melee = stock bash, ranged = 5-pellet fan."""
    PELLET_COUNT = 5
    PELLET_DAMAGE_RATIO = 0.4

    def melee_damage(self, base_attack: int) -> int:
        return int(base_attack * 1.2)

    def ranged_damage(self, base_attack: int) -> int:
        return int(base_attack * self.PELLET_DAMAGE_RATIO * self.PELLET_COUNT)


class LaserPointer(Weapon):
    """Doomsday Laser Pointer: continuous beam, high ranged DPS."""
    DPS_MULTIPLIER = 3.0

    def melee_damage(self, base_attack: int) -> int:
        return int(base_attack * 0.5)      # awkward in melee

    def ranged_damage(self, base_attack: int) -> int:
        return int(base_attack * self.DPS_MULTIPLIER)
