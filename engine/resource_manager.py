"""Resource bookkeeping shared by the player UI, end of turn and the AI."""
from config import RESOURCES


class ResourceManager:
    RESOURCES = list(RESOURCES)
    MINE_INCOME = {"gold_mine": 1000, "wood_mine": 2, "ore_mine": 2,
                   "mercury_mine": 1, "sulfur_mine": 1, "crystal_mine": 1, "gems_mine": 1}

    @staticmethod
    def can_afford(resources, cost_dict):
        return all(resources.get(r, 0) >= amt for r, amt in cost_dict.items())

    @staticmethod
    def spend(resources, cost_dict):
        """Deduct the cost if affordable. Returns False (and changes nothing) otherwise."""
        if not ResourceManager.can_afford(resources, cost_dict):
            return False
        for r, amt in cost_dict.items():
            resources[r] = resources.get(r, 0) - amt
        return True

    @staticmethod
    def add(resources, income_dict):
        """Add (or, with negative amounts, remove) resources; never below zero."""
        for r, amt in income_dict.items():
            resources[r] = max(0, resources.get(r, 0) + amt)

    @staticmethod
    def daily_income(owned_mines, owner="player"):
        """Total per-day income from the mines `owner` holds."""
        out = {}
        for m in owned_mines:
            if getattr(m, "owner", None) == owner and getattr(m, "object_type", "") in ResourceManager.MINE_INCOME:
                out[m.resource_type] = out.get(m.resource_type, 0) + m.daily_income
        return out

    @staticmethod
    def apply_daily_income(resources, owned_mines, owner="player"):
        income = ResourceManager.daily_income(owned_mines, owner)
        ResourceManager.add(resources, income)
        return income
