from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import random

from config import Config
from .terrain import Terrain
from .generators import populate_world
from .events import apply_random_events


@dataclass
class WorldCell:
    terrain: Terrain = Terrain.EMPTY
    nutrient: float = 0.0
    toxin: float = 0.0
    light: float = 0.0
    temperature: float = 0.5
    occupancy: int = 0


class SimWorld:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.grid: List[List[WorldCell]] = [
            [WorldCell() for _ in range(cfg.grid_w)] for _ in range(cfg.grid_h)
        ]
        self.rng = random.Random(42)
        populate_world(self.grid, cfg, self.rng)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.cfg.grid_w and 0 <= y < self.cfg.grid_h

    def get_cell(self, x: int, y: int) -> WorldCell:
        return self.grid[y][x]

    def get_patch(self, x: int, y: int, radius: int = 1) -> List[Tuple[int, int, WorldCell]]:
        patch = []
        for py in range(y - radius, y + radius + 1):
            for px in range(x - radius, x + radius + 1):
                if self.in_bounds(px, py):
                    patch.append((px, py, self.grid[py][px]))
        return patch

    def consume_nutrient(self, x: int, y: int, amount: float) -> float:
        cell = self.get_cell(x, y)
        consumed = min(cell.nutrient, amount)
        cell.nutrient -= consumed
        return consumed

    def inject_user_energy(self, x: int, y: int, amount: float) -> None:
        if self.in_bounds(x, y):
            cell = self.get_cell(x, y)
            cell.nutrient = min(1.0, cell.nutrient + amount)
            cell.light = min(1.0, cell.light + amount * 0.15)

    def inject_toxin(self, x: int, y: int, amount: float) -> None:
        if self.in_bounds(x, y):
            cell = self.get_cell(x, y)
            cell.toxin = min(1.0, cell.toxin + amount)

    def apply_body_occupancy(self, occupied_positions: List[Tuple[int, int]]) -> None:
        for row in self.grid:
            for cell in row:
                cell.occupancy = 0
        for x, y in occupied_positions:
            self.grid[y][x].occupancy = 1

    def _diffuse_scalar(self, attr: str, rate: float, decay: float) -> None:
        new_values = [[0.0 for _ in range(self.cfg.grid_w)] for _ in range(self.cfg.grid_h)]
        for y in range(self.cfg.grid_h):
            for x in range(self.cfg.grid_w):
                cell = self.grid[y][x]
                if cell.terrain == Terrain.WALL:
                    continue
                current = getattr(cell, attr)
                neighbors = []
                for ny in range(max(0, y - 1), min(self.cfg.grid_h, y + 2)):
                    for nx in range(max(0, x - 1), min(self.cfg.grid_w, x + 2)):
                        if nx == x and ny == y:
                            continue
                        neighbors.append(getattr(self.grid[ny][nx], attr))
                avg_neighbors = sum(neighbors) / len(neighbors) if neighbors else current
                mixed = current + rate * (avg_neighbors - current)
                if self.grid[y][x].terrain == Terrain.RESOURCE and attr == 'nutrient':
                    mixed += 0.01
                new_values[y][x] = max(0.0, min(1.0, mixed - decay))
        for y in range(self.cfg.grid_h):
            for x in range(self.cfg.grid_w):
                if self.grid[y][x].terrain != Terrain.WALL:
                    setattr(self.grid[y][x], attr, new_values[y][x])

    def step(self) -> None:
        self._diffuse_scalar('nutrient', self.cfg.nutrient_diffusion, self.cfg.nutrient_decay)
        self._diffuse_scalar('toxin', self.cfg.toxin_diffusion, self.cfg.toxin_decay)
        apply_random_events(self, self.rng)

        for _ in range(3):
            x = self.rng.randint(1, self.cfg.grid_w - 2)
            y = self.rng.randint(1, self.cfg.grid_h - 2)
            cell = self.grid[y][x]
            if cell.terrain == Terrain.EMPTY:
                cell.nutrient = min(1.0, cell.nutrient + self.rng.uniform(0.01, 0.04))
