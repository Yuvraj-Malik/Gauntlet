from .scenario import Scenario, score
from .scenarios import ALL

SCENARIOS = {s.id: s for s in ALL}
assert len(SCENARIOS) == len(ALL), "duplicate scenario id"

__all__ = ["Scenario", "SCENARIOS", "score"]
