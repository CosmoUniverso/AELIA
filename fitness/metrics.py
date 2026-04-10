from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import math

from cognition.summary_builder import build_summary


@dataclass
class FitnessSnapshot:
    tick: int
    mass: int
    mean_energy: float
    mean_health: float
    compactness: float
    total_resources_collected: float
    total_damage_taken: float


class FitnessEngine:
    def __init__(self) -> None:
        self.history: List[FitnessSnapshot] = []

    def _resource_gradient(self, world, cx: float, cy: float, radius: int = 4) -> Tuple[float, float]:
        sx = sy = 0.0
        for y in range(max(0, int(cy) - radius), min(world.cfg.grid_h, int(cy) + radius + 1)):
            for x in range(max(0, int(cx) - radius), min(world.cfg.grid_w, int(cx) + radius + 1)):
                dx = x - cx
                dy = y - cy
                cell = world.get_cell(x, y)
                weight = cell.nutrient + 0.4 * cell.light - 0.8 * cell.toxin
                sx += dx * weight
                sy += dy * weight
        mag = math.sqrt(sx * sx + sy * sy)
        if mag > 1e-6:
            sx /= mag
            sy /= mag
        return sx, sy

    def _hazard_proximity(self, world, cx: float, cy: float, radius: int = 6) -> int:
        best = radius + 1
        for y in range(max(0, int(cy) - radius), min(world.cfg.grid_h, int(cy) + radius + 1)):
            for x in range(max(0, int(cx) - radius), min(world.cfg.grid_w, int(cx) + radius + 1)):
                cell = world.get_cell(x, y)
                if int(cell.terrain) == 2 or cell.toxin > 0.25:
                    dist = abs(x - int(cx)) + abs(y - int(cy))
                    best = min(best, dist)
        return best

    def summarize_for_cognition(self, tick: int, body, world) -> dict:
        cx, cy = body.center_of_mass()
        rgx, rgy = self._resource_gradient(world, cx, cy)
        tox_x, tox_y = self._resource_gradient(world, cx, cy, radius=3)
        env_summary = {
            'nutrient_gradient': [round(rgx, 4), round(rgy, 4)],
            'toxin_gradient': [round(-tox_x, 4), round(-tox_y, 4)],
            'hazard_proximity': self._hazard_proximity(world, cx, cy),
        }
        return build_summary(tick, body.summarize(), env_summary)

    def capture(self, tick: int, body) -> FitnessSnapshot:
        snap = FitnessSnapshot(
            tick=tick,
            mass=body.mass(),
            mean_energy=body.mean_energy(),
            mean_health=body.mean_health(),
            compactness=body.compactness(),
            total_resources_collected=body.total_resources_collected,
            total_damage_taken=body.total_damage_taken,
        )
        self.history.append(snap)
        return snap
