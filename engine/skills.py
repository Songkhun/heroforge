"""Secondary skills: per-level values and descriptions. 1=Basic 2=Advanced 3=Expert."""

LEVEL_NAMES = {1: "Basic", 2: "Advanced", 3: "Expert"}
MAX_SKILLS = 8

# name -> (values per level, description template using {v})
SKILLS = {
    "Logistics":   ((10, 20, 30), "+{v}% movement points"),
    "Archery":     ((10, 25, 50), "+{v}% ranged damage"),
    "Leadership":  ((1, 2, 3), "+{v} morale for all stacks"),
    "Wisdom":      ((3, 4, 5), "Can learn spells up to level {v}"),
    "Earth Magic": ((25, 50, 100), "+{v}% power for Earth spells"),
    "Fire Magic":  ((25, 50, 100), "+{v}% power for Fire spells"),
    "Air Magic":   ((25, 50, 100), "+{v}% power for Air spells"),
    "Water Magic": ((25, 50, 100), "+{v}% power for Water spells"),
    "Tactics":     ((3, 4, 5), "Arrange troops in {v} columns before battle"),
    "Offense":     ((10, 20, 30), "+{v}% melee damage"),
    "Armorer":     ((5, 10, 15), "-{v}% damage taken"),
    "Luck":        ((1, 2, 3), "+{v} luck ({v}0% chance of double damage)"),
    "Morale":      ((1, 2, 3), "+{v} morale ({v}0% chance of an extra move)"),
    "Scouting":    ((2, 4, 6), "+{v} tiles vision radius"),
    "Eagle Eye":   ((20, 40, 60), "{v}% chance to learn spells enemies cast"),
}
# Navigation and Diplomacy are in the design list but have no effect yet, so they're never offered.

SCHOOL_SKILL = {"earth": "Earth Magic", "fire": "Fire Magic", "air": "Air Magic", "water": "Water Magic"}
SKILL_COLORS = {
    "Logistics": (190, 150, 90), "Archery": (90, 170, 90), "Leadership": (220, 190, 80),
    "Wisdom": (150, 120, 220), "Earth Magic": (150, 110, 60), "Fire Magic": (220, 90, 50),
    "Air Magic": (150, 200, 240), "Water Magic": (70, 130, 220), "Tactics": (200, 80, 80),
    "Offense": (210, 60, 60), "Armorer": (150, 150, 165), "Luck": (90, 200, 130),
    "Morale": (240, 160, 60), "Scouting": (110, 190, 190), "Eagle Eye": (200, 170, 120),
}


def skill_value(hero, name):
    """The skill's value at the hero's level (0 if unknown)."""
    if hero is None:
        return 0
    lvl = hero.skills.get(name, 0)
    return SKILLS[name][0][lvl - 1] if lvl and name in SKILLS else 0


def describe(name, level):
    vals, text = SKILLS[name]
    return text.format(v=vals[level - 1])


def max_spell_level(hero):
    """Without Wisdom a hero can learn spells up to level 2."""
    return skill_value(hero, "Wisdom") or 2


def candidate_skills(hero):
    """Skills that can be offered on level-up: upgrades of known skills plus new ones."""
    upgrades = [n for n, lvl in hero.skills.items() if n in SKILLS and lvl < 3]
    new = [n for n in SKILLS if n not in hero.skills] if len(hero.skills) < MAX_SKILLS else []
    return upgrades + new
