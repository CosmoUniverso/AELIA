import random
from .terrain import Terrain


def populate_world(grid, cfg, rng: random.Random) -> None:
    for y in range(cfg.grid_h):
        for x in range(cfg.grid_w):
            cell = grid[y][x]
            cell.light = cfg.ambient_light

            if x in (0, cfg.grid_w - 1) or y in (0, cfg.grid_h - 1):
                cell.terrain = Terrain.WALL
                continue

            roll = rng.random()
            if roll < 0.065:
                cell.terrain = Terrain.RESOURCE
                cell.nutrient = rng.uniform(0.65, 1.0)
                cell.light = rng.uniform(0.10, 0.22)
            elif roll < 0.085:
                cell.terrain = Terrain.HAZARD
                cell.toxin = rng.uniform(0.35, 0.8)
            else:
                cell.nutrient = rng.uniform(0.01, 0.16)
                cell.toxin = rng.uniform(0.0, 0.03)
