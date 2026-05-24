# tests/test_logic.py
# Run with: python -m unittest discover -s tests
#
# Tests cover pure logic only — no Pygame required.

import unittest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from logic.cat import Cat, Aries, Scorpio, Aquarius
from logic.enemy import GreenRat, KamikazeRat
from logic.weapons import Shotgun, LaserPointer
from logic.items import apply_tuna_can, apply_energy_drink


class TestCatDamage(unittest.TestCase):

    def test_take_damage_normal(self):
        """HP decreases correctly on a normal hit."""
        cat = Cat("TestCat", hp=100, attack=10, speed=1.0)
        cat.take_damage(30)
        self.assertEqual(cat.hp, 70)

    def test_take_damage_floors_at_zero(self):
        """HP never goes negative — edge case."""
        cat = Cat("TestCat", hp=100, attack=10, speed=1.0)
        cat.take_damage(9999)
        self.assertEqual(cat.hp, 0)

    def test_is_alive_after_lethal_hit(self):
        cat = Cat("TestCat", hp=50, attack=10, speed=1.0)
        cat.take_damage(50)
        self.assertFalse(cat.is_alive())


class TestAriesBerserker(unittest.TestCase):

    def test_full_hp_no_bonus(self):
        """At full HP the berserker bonus is 0."""
        aries = Aries()
        self.assertEqual(aries.basic_attack_damage(), aries.attack)

    def test_half_hp_increases_damage(self):
        """At half HP the berserker passive should increase output."""
        aries = Aries()
        base = aries.basic_attack_damage()
        aries.hp = aries.max_hp // 2
        self.assertGreater(aries.basic_attack_damage(), base)


class TestWeapons(unittest.TestCase):

    def test_shotgun_ranged_uses_pellets(self):
        """Shotgun ranged damage = pellet_count * ratio * base."""
        gun = Shotgun()
        base = 20
        expected = int(base * gun.PELLET_DAMAGE_RATIO * gun.PELLET_COUNT)
        self.assertEqual(gun.ranged_damage(base), expected)

    def test_laser_pointer_high_ranged(self):
        """Laser ranged must exceed default weapon ranged."""
        from logic.weapons import Weapon
        laser = LaserPointer()
        default = Weapon()
        base = 20
        self.assertGreater(laser.ranged_damage(base), default.ranged_damage(base))


class TestItems(unittest.TestCase):

    def test_tuna_can_increases_attack(self):
        cat = Cat("Test", hp=100, attack=20, speed=1.0)
        apply_tuna_can(cat)
        self.assertGreater(cat.attack, 20)

    def test_energy_drink_increases_speed(self):
        cat = Cat("Test", hp=100, attack=10, speed=1.0)
        apply_energy_drink(cat)
        self.assertGreater(cat.speed, 1.0)


if __name__ == "__main__":
    unittest.main()
