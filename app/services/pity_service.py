import random


BASE_RARITY_WEIGHTS = {
    "common": 72.9,
    "rare": 20.0,
    "epic": 5.0,
    "legendary": 2.0,
    "unique": 0.1,
}


def _lerp(start: float, end: float, value: int, left: int, right: int) -> float:
    if value <= left:
        return start
    if value >= right:
        return end
    t = (value - left) / (right - left)
    return start + (end - start) * t


def build_rarity_weights(
    pity_epic: int,
    pity_legendary: int,
    pity_unique: int
) -> dict[str, float]:
    # Epic: 1000 -> 2000 -> 3000
    if pity_epic < 1000:
        epic_weight = BASE_RARITY_WEIGHTS["epic"]
    elif pity_epic < 2000:
        epic_weight = _lerp(5.0, 20.0, pity_epic, 1000, 2000)
    elif pity_epic < 3000:
        epic_weight = _lerp(20.0, 95.0, pity_epic, 2000, 3000)
    else:
        epic_weight = 95.0

    # Legendary: 5000 -> 7000 -> 10000
    if pity_legendary < 5000:
        legendary_weight = BASE_RARITY_WEIGHTS["legendary"]
    elif pity_legendary < 7000:
        legendary_weight = _lerp(2.0, 15.0, pity_legendary, 5000, 7000)
    elif pity_legendary < 10000:
        legendary_weight = _lerp(15.0, 98.0, pity_legendary, 7000, 10000)
    else:
        legendary_weight = 98.0

    # Unique: 35000 -> 42000 -> 50000
    if pity_unique < 35000:
        unique_weight = BASE_RARITY_WEIGHTS["unique"]
    elif pity_unique < 42000:
        unique_weight = _lerp(0.1, 10.0, pity_unique, 35000, 42000)
    elif pity_unique < 50000:
        unique_weight = _lerp(10.0, 99.9, pity_unique, 42000, 50000)
    else:
        unique_weight = 99.9

    return {
        "common": BASE_RARITY_WEIGHTS["common"],
        "rare": BASE_RARITY_WEIGHTS["rare"],
        "epic": epic_weight,
        "legendary": legendary_weight,
        "unique": unique_weight,
    }


def roll_rarity_with_pity(
    pity_epic: int,
    pity_legendary: int,
    pity_unique: int
) -> str:
    # Hard pity first
    if pity_unique >= 50000:
        return "unique"
    if pity_legendary >= 10000:
        return "legendary"
    if pity_epic >= 3000:
        return "epic"

    weights = build_rarity_weights(pity_epic, pity_legendary, pity_unique)
    rarities = list(weights.keys())
    values = list(weights.values())
    return random.choices(rarities, weights=values, k=1)[0]


def roll_rarity() -> str:
    # Compatibility for old tests /testrarity
    return roll_rarity_with_pity(0, 0, 0)


def apply_pity_after_roll(
    pity_epic: int,
    pity_legendary: int,
    pity_unique: int,
    rolled_rarity: str,
) -> tuple[int, int, int]:
    """
    counters = "how many rolls passed without the target rarity"
    unique hit     -> reset all
    legendary hit  -> reset epic/legendary, increment unique
    epic hit       -> reset epic, increment legendary/unique
    common/rare    -> increment all
    """
    if rolled_rarity == "unique":
        return 0, 0, 0

    if rolled_rarity == "legendary":
        return 0, 0, pity_unique + 1

    if rolled_rarity == "epic":
        return 0, pity_legendary + 1, pity_unique + 1

    return pity_epic + 1, pity_legendary + 1, pity_unique + 1