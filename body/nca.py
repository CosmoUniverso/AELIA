from __future__ import annotations

from typing import Dict, List, Tuple
import random

from config import Config
from body.cells import BodyCell, CellType
from body import metabolism, growth, morphology


class BodyNCA:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.grid: List[List[BodyCell]] = [
            [BodyCell() for _ in range(cfg.grid_w)] for _ in range(cfg.grid_h)
        ]
        self.rng = random.Random(123)
        self.total_resources_collected = 0.0
        self.total_damage_taken = 0.0
        self.cell_types_enum = CellType
        self._spawn_seed(cfg.seed_x, cfg.seed_y)

    def _spawn_seed(self, x: int, y: int) -> None:
        for dx, dy, ctype in [
            (0, 0, CellType.STEM),
            (1, 0, CellType.MEMBRANE),
            (-1, 0, CellType.MEMBRANE),
            (0, 1, CellType.STORAGE),
            (0, -1, CellType.STORAGE),
        ]:
            px, py = x + dx, y + dy
            if 0 <= px < self.cfg.grid_w and 0 <= py < self.cfg.grid_h:
                self.grid[py][px] = BodyCell(
                    alive=True,
                    energy=0.42,
                    health=0.92,
                    age=0,
                    cell_type=ctype,
                )

    def iter_alive(self):
        for y in range(self.cfg.grid_h):
            for x in range(self.cfg.grid_w):
                cell = self.grid[y][x]
                if cell.alive:
                    yield x, y, cell

    def occupied_positions(self) -> List[Tuple[int, int]]:
        return [(x, y) for x, y, _ in self.iter_alive()]

    def count_alive_neighbors(self, x: int, y: int) -> int:
        count = 0
        for ny in range(max(0, y - 1), min(self.cfg.grid_h, y + 2)):
            for nx in range(max(0, x - 1), min(self.cfg.grid_w, x + 2)):
                if nx == x and ny == y:
                    continue
                if self.grid[ny][nx].alive:
                    count += 1
        return count

    def mean_energy(self) -> float:
        cells = [c.energy for _, _, c in self.iter_alive()]
        return sum(cells) / len(cells) if cells else 0.0

    def mean_health(self) -> float:
        cells = [c.health for _, _, c in self.iter_alive()]
        return sum(cells) / len(cells) if cells else 0.0

    def mass(self) -> int:
        return sum(1 for _ in self.iter_alive())

    def center_of_mass(self):
        return morphology.center_of_mass(self)

    def compactness(self) -> float:
        return morphology.compactness(self)

    def summarize(self) -> Dict[str, object]:
        return {
            'mass': self.mass(),
            'mean_energy': round(self.mean_energy(), 4),
            'mean_health': round(self.mean_health(), 4),
            'compactness': round(self.compactness(), 4),
            'center_of_mass': self.center_of_mass(),
            'cell_type_distribution': morphology.distribution(self),
            'total_resources_collected': round(self.total_resources_collected, 4),
            'total_damage_taken': round(self.total_damage_taken, 4),
        }

    def _share_energy(self) -> None:
        deltas = [[0.0 for _ in range(self.cfg.grid_w)] for _ in range(self.cfg.grid_h)]
        for x, y, cell in list(self.iter_alive()):
            neighbors = []
            for ny in range(max(0, y - 1), min(self.cfg.grid_h, y + 2)):
                for nx in range(max(0, x - 1), min(self.cfg.grid_w, x + 2)):
                    if nx == x and ny == y:
                        continue
                    other = self.grid[ny][nx]
                    if other.alive:
                        neighbors.append((nx, ny, other))
            for nx, ny, other in neighbors:
                diff = cell.energy - other.energy
                if diff > 0.04:
                    transfer = min(diff * self.cfg.energy_share_rate, cell.energy * 0.06)
                    deltas[y][x] -= transfer
                    deltas[ny][nx] += transfer
        for y in range(self.cfg.grid_h):
            for x in range(self.cfg.grid_w):
                cell = self.grid[y][x]
                if cell.alive:
                    cell.energy = max(0.0, min(1.0, cell.energy + deltas[y][x]))

    def update(self, world, mods) -> None:
        alive_snapshot = [(x, y, cell) for x, y, cell in self.iter_alive()]
        current_mass = len(alive_snapshot)

        for x, y, cell in alive_snapshot:
            cell.age += 1

            gain = metabolism.resource_gain(self.cfg, x, y, cell, world)
            damage = metabolism.damage_from_world(self.cfg, x, y, world, mods.hazard_avoidance, cell)
            upkeep = metabolism.upkeep_cost(self.cfg, cell, mods.metabolic_thrift, current_mass)

            cell.energy = max(0.0, min(1.0, cell.energy + gain - upkeep))
            cell.health = max(0.0, min(1.0, cell.health - damage))
            cell.stress = min(1.0, damage * 5.0 + max(0.0, 0.18 - cell.energy))

            self.total_resources_collected += gain
            self.total_damage_taken += damage

            metabolism.repair_cell(self.cfg, cell, mods.repair_bias)
            growth.try_grow(self, x, y, cell, world, mods)

            if cell.energy <= 0.0 or cell.health <= 0.0:
                cell.alive = False
                cell.energy = 0.0
                cell.health = 0.0
            else:
                growth.prune_if_needed(self, x, y, cell, mods.prune_bias)

        self.enforce_minimum_stem_core()
        self._share_energy()
        world.apply_body_occupancy(self.occupied_positions())

    def enforce_minimum_stem_core(self) -> None:
        stem_positions = []
        candidates = []

        cx, cy = self.center_of_mass()

        for x, y, cell in self.iter_alive():
            if cell.cell_type == CellType.STEM:
                stem_positions.append((x, y))
            elif cell.cell_type == CellType.STORAGE:
                if cell.energy > 0.10 and cell.health > 0.45:
                    dist = abs(x - cx) + abs(y - cy)
                    candidates.append((dist, x, y, cell))

        if len(stem_positions) >= 5:
            return

        needed = 5 - len(stem_positions)
        candidates.sort(key=lambda item: item[0])  # preferisci vicino al centro

        converted = 0
        for _, _, _, cell in candidates:
            if converted >= needed:
                break
            cell.cell_type = CellType.STEM
            cell.energy *= 0.88
            converted += 1
