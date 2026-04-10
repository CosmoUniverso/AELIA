from __future__ import annotations

from typing import List, Optional, Tuple

from body.cells import BodyCell, CellType


def candidate_growth_sites(body, x: int, y: int, world) -> List[Tuple[int, int, float]]:
    candidates = []

    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue

            nx, ny = x + dx, y + dy
            if not world.in_bounds(nx, ny):
                continue
            if body.grid[ny][nx].alive:
                continue

            wcell = world.get_cell(nx, ny)
            if int(wcell.terrain) == 1:
                continue

            # premio nutrienti, luce moderata, tossina penalizzata forte
            score = wcell.nutrient + 0.35 * wcell.light - 0.95 * wcell.toxin
            candidates.append((nx, ny, score))

    return candidates


def type_counts(body) -> dict[CellType, int]:
    counts = {
        CellType.STEM: 0,
        CellType.MEMBRANE: 0,
        CellType.STORAGE: 0,
    }

    for _, _, cell in body.iter_alive():
        counts[cell.cell_type] += 1

    return counts


def select_growth_type(body, storage_bias: float, membrane_bias: float, alive_neighbors: int) -> CellType:
    counts = type_counts(body)
    total = max(1, sum(counts.values()))

    stem_count = counts[CellType.STEM]
    membrane_ratio = counts[CellType.MEMBRANE] / total
    storage_ratio = counts[CellType.STORAGE] / total

    min_stem_count = 4
    if stem_count < min_stem_count:
        return CellType.STEM

    # bordo estremo -> membrana
    if alive_neighbors <= 1:
        return CellType.MEMBRANE

    # bordo leggero -> alterna membrana/storage in base alla riserva
    if alive_neighbors == 2:
        if storage_ratio < 0.18:
            return CellType.STORAGE
        return CellType.MEMBRANE

    # interno denso -> consenti un piccolo nucleo staminale stabile
    if alive_neighbors >= 5 and stem_count < 6:
        return CellType.STEM

    # interno supportato -> favorisci storage
    storage_score = storage_bias + 0.10 * (alive_neighbors >= 3)
    membrane_score = membrane_bias + 0.06 * (alive_neighbors <= 3)
    stem_score = 0.18

    # clamp anti-dominanza
    if storage_ratio > 0.48:
        storage_score *= 0.45

    if membrane_ratio > 0.70:
        membrane_score *= 0.55

    if membrane_ratio < 0.18:
        membrane_score += 0.10

    if storage_ratio < 0.12:
        storage_score += 0.12

    # se il corpo è già grande, meno storage esplosivo e un po' più membrana
    if total > 180:
        membrane_score += 0.08
        storage_score *= 0.82

    values = [stem_score, membrane_score, storage_score]
    idx = max(range(len(values)), key=lambda i: values[i])
    return CellType(idx)


def try_grow(body, x: int, y: int, cell: BodyCell, world, mods) -> None:
    target_mass_soft = 180
    target_mass_hard = 240

    current_mass = body.mass()
    if current_mass >= target_mass_hard:
        return

    if cell.energy < body.cfg.growth_cost + 0.12 or cell.health < 0.45:
        return

    candidates = candidate_growth_sites(body, x, y, world)
    if not candidates:
        return

    gx = mods.growth_direction_x
    gy = mods.growth_direction_y

    best_site: Optional[Tuple[int, int, float]] = None
    best_value = -10**9

    growth_penalty = 0.0
    if current_mass > target_mass_soft:
        growth_penalty = (current_mass - target_mass_soft) / max(1, target_mass_soft)

    for nx, ny, local_score in candidates:
        direction_bias = (nx - x) * gx + (ny - y) * gy
        alive_neighbors = body.count_alive_neighbors(nx, ny)

        # penalizza tentacoli/rami troppo sottili
        thin_branch_penalty = 0.45 if alive_neighbors <= 1 else 0.20 if alive_neighbors == 2 else 0.0

        # premia crescita con supporto vero
        support_bonus = 0.18 if alive_neighbors >= 4 else 0.08 if alive_neighbors == 3 else 0.0

        # penalizza crescita troppo affollata
        crowd_penalty = alive_neighbors * (0.05 + 0.06 * mods.compactness_bias)

        total = (
            local_score
            + direction_bias * (mods.growth_strength * (1.0 - growth_penalty) * 0.25)
            + support_bonus
            - crowd_penalty
            - thin_branch_penalty
        )

        if total > best_value:
            best_value = total
            best_site = (nx, ny, total)

    if best_site is None or best_value < -0.15:
        return

    nx, ny, _ = best_site
    neighbor_count = body.count_alive_neighbors(nx, ny)

    # niente crescita in siti troppo debolmente supportati
    if neighbor_count <= 2:
        return

    ntype = select_growth_type(body, mods.storage_bias, mods.membrane_bias, neighbor_count)

    if ntype == CellType.MEMBRANE:
        seed_energy = 0.16
        seed_health = 0.78
    elif ntype == CellType.STEM:
        seed_energy = 0.14
        seed_health = 0.72
    else:
        seed_energy = 0.12
        seed_health = 0.72

    body.grid[ny][nx] = BodyCell(
        alive=True,
        energy=seed_energy,
        health=seed_health,
        age=0,
        cell_type=ntype,
        polarity_x=gx,
        polarity_y=gy,
    )
    body.created_cells_recent += 1
    cell.energy -= body.cfg.growth_cost


def prune_if_needed(body, x: int, y: int, cell: BodyCell, prune_bias: float) -> None:
    # proteggi nucleo stem minimo
    if cell.cell_type == CellType.STEM:
        counts = type_counts(body)
        if counts[CellType.STEM] <= 4:
            return

    border_neighbors = body.count_alive_neighbors(x, y)

    # membrane sottili isolate devono morire più facilmente
    if cell.cell_type == CellType.MEMBRANE and border_neighbors <= 2:
        energy_threshold = 0.06
        health_threshold = 0.14
    else:
        energy_threshold = 0.05
        health_threshold = 0.12

    if cell.energy > energy_threshold or cell.health > health_threshold:
        return

    if border_neighbors >= 3 and body.rng.random() > prune_bias:
        return

    cell.alive = False
    cell.energy = 0.0
    cell.health = 0.0