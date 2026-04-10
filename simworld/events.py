import random


def apply_random_events(world, rng: random.Random) -> None:
    if rng.random() < 0.02:
        x = rng.randint(1, world.cfg.grid_w - 2)
        y = rng.randint(1, world.cfg.grid_h - 2)
        cell = world.grid[y][x]
        cell.nutrient = min(1.0, cell.nutrient + rng.uniform(0.08, 0.18))

    if rng.random() < 0.006:
        x = rng.randint(2, world.cfg.grid_w - 3)
        y = rng.randint(2, world.cfg.grid_h - 3)
        for yy in range(y - 1, y + 2):
            for xx in range(x - 1, x + 2):
                world.grid[yy][xx].toxin = min(1.0, world.grid[yy][xx].toxin + rng.uniform(0.05, 0.12))
