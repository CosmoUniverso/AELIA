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

            # Più forte il premio nutrienti, più severa la tossina
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

    # 1. Mantieni sempre un nucleo staminale minimo
    min_stem_count = 4
    if stem_count < min_stem_count:
        return CellType.STEM

    # 2. Le cellule di bordo devono quasi sempre essere membrana
    if alive_neighbors <= 2:
        return CellType.MEMBRANE
    
    # Se i vicini sono tanti e siamo in zona interna, favorisci stem vicino al nucleo
    if alive_neighbors >= 5 and stem_count < 6:
        return CellType.STEM

    # 3. Clamp dello storage: non deve dominare
    storage_score = storage_bias + 0.04 * (alive_neighbors < 3)
    membrane_score = membrane_bias + 0.08 * (alive_neighbors <= 3)
    stem_score = 0.18

    if storage_ratio > 0.45:
        storage_score *= 0.30

    if membrane_ratio < 0.22:
        membrane_score += 0.25

    # 4. Se il corpo è già grande, favorisci più membrana e meno storage
    if total > 180:
        membrane_score += 0.20
        storage_score *= 0.60

    values = [stem_score, membrane_score, storage_score]
    idx = max(range(len(values)), key=lambda i: values[i])
    return CellType(idx)


def try_grow(body, x: int, y: int, cell: BodyCell, world, mods) -> None:
    # Stop di sicurezza per evitare esplosione di massa
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

    # Penalità di crescita se il corpo supera la massa desiderata
    growth_penalty = 0.0
    if current_mass > target_mass_soft:
        growth_penalty = (current_mass - target_mass_soft) / max(1, target_mass_soft)

    for nx, ny, local_score in candidates:
        direction_bias = (nx - x) * gx + (ny - y) * gy
        alive_neighbors = body.count_alive_neighbors(nx, ny)

        # penalizza crescita troppo sottile / a tentacolo
        thin_branch_penalty = 0.35 if alive_neighbors <= 1 else 0.12 if alive_neighbors == 2 else 0.0

        # premia crescita con supporto strutturale
        direction_bias = (nx - x) * gx + (ny - y) * gy
        alive_neighbors = body.count_alive_neighbors(nx, ny)

        thin_branch_penalty = 0.45 if alive_neighbors <= 1 else 0.20 if alive_neighbors == 2 else 0.0
        support_bonus = 0.18 if alive_neighbors >= 4 else 0.08 if alive_neighbors == 3 else 0.0
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
    if neighbor_count <= 2:
        return
    ntype = select_growth_type(body, mods.storage_bias, mods.membrane_bias, body.count_alive_neighbors(nx, ny))

    seed_energy = 0.16 if ntype == CellType.MEMBRANE else 0.14 if ntype == CellType.STEM else 0.12
    seed_health = 0.78 if ntype == CellType.MEMBRANE else 0.72

    body.grid[ny][nx] = BodyCell(
        alive=True,
        energy=seed_energy,
        health=seed_health,
        age=0,
        cell_type=ntype,
        polarity_x=gx,
        polarity_y=gy,
    )
    cell.energy -= body.cfg.growth_cost


def prune_if_needed(body, x: int, y: int, cell: BodyCell, prune_bias: float) -> None:
    # Proteggi le stem: non devono sparire facilmente
    if cell.cell_type == CellType.STEM:
        counts = type_counts(body)
        if counts[CellType.STEM] <= 4:
            return

    # Le membrane sul bordo sono utili, non potarle troppo aggressivamente
    border_neighbors = body.count_alive_neighbors(x, y)
    if cell.cell_type == CellType.MEMBRANE and border_neighbors <= 3:
        energy_threshold = 0.03
        health_threshold = 0.08
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