from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import math


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

    def _resource_gradient(
        self,
        world,
        cx: float,
        cy: float,
        radius: int = 4,
        light_weight: float = 0.4,
        toxin_weight: float = 0.8,
    ) -> Tuple[float, float]:
        sx = sy = 0.0

        for y in range(max(0, int(cy) - radius), min(world.cfg.grid_h, int(cy) + radius + 1)):
            for x in range(max(0, int(cx) - radius), min(world.cfg.grid_w, int(cx) + radius + 1)):
                dx = x - cx
                dy = y - cy
                cell = world.get_cell(x, y)

                weight = cell.nutrient + light_weight * cell.light - toxin_weight * cell.toxin
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

        rgx, rgy = self._resource_gradient(
            world,
            cx,
            cy,
            radius=4,
            light_weight=0.4,
            toxin_weight=0.8,
        )

        tgx, tgy = self._resource_gradient(
            world,
            cx,
            cy,
            radius=3,
            light_weight=0.0,
            toxin_weight=-1.0,  # serve solo a leggere il gradiente tossico
        )

        mean_energy = body.mean_energy()
        previous_energy = body.prev_mean_energy if body.prev_mean_energy is not None else mean_energy
        net_energy_delta = mean_energy - previous_energy

        mass = max(1, body.mass())
        perimeter = body.perimeter()
        surface_ratio = perimeter / mass

        created = body.created_cells_recent
        died = body.died_cells_recent
        growth_efficiency = created / max(1, created + died)

        previous_center = body.prev_center_of_mass if body.prev_center_of_mass is not None else (cx, cy)
        mobility = math.sqrt((cx - previous_center[0]) ** 2 + (cy - previous_center[1]) ** 2)

        summary = {
            "tick": tick,
            "body": body.summarize(),
            "environment": {
                "nutrient_gradient": [round(rgx, 4), round(rgy, 4)],
                "toxin_gradient": [round(tgx, 4), round(tgy, 4)],
                "hazard_proximity": self._hazard_proximity(world, cx, cy),
            },
            "derived": {
                "net_energy_delta": round(net_energy_delta, 5),
                "surface_ratio": round(surface_ratio, 5),
                "growth_efficiency": round(growth_efficiency, 5),
                "mobility": round(mobility, 5),
                "created_cells_recent": created,
                "died_cells_recent": died,
                "perimeter": perimeter,
            },
        }

        body.prev_mean_energy = mean_energy
        body.prev_center_of_mass = (cx, cy)

        return summary

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