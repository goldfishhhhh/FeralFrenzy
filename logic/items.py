# logic/items.py
# Passive and active item effects — pure Python.


def apply_tuna_can(cat) -> None:
    """Mutated Tuna Can: +10 % base attack, +20 max HP."""
    cat.attack = int(cat.attack * 1.1)
    cat.max_hp += 20
    cat.hp = min(cat.hp + 20, cat.max_hp)


def apply_energy_drink(cat) -> None:
    """Spilled Energy Drink: +15 % movement speed."""
    cat.speed *= 1.015
