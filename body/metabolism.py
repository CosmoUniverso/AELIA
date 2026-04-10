from __future__ import annotations

from body.cells import CellType, BodyCell


def upkeep_cost(cfg, cell: BodyCell, thrift: float, body_mass: int = 0) -> float:
    type_cost_map = {
        CellType.STEM: cfg.cost_stem * 1.10,
        CellType.MEMBRANE: cfg.cost_membrane,
        CellType.STORAGE: cfg.cost_storage * 1.08,
    }

    upkeep = cfg.base_cost_alive + type_cost_map[cell.cell_type] * (1.0 - 0.35 * thrift)

    # Penalità globale per corpi troppo grandi
    if body_mass > 140:
        upkeep *= 1.0 + (body_mass - 140) * 0.003

    return upkeep


def resource_gain(cfg, x: int, y: int, cell: BodyCell, world) -> float:
    wcell = world.get_cell(x, y)
    nutrient_gain = world.consume_nutrient(x, y, cfg.base_nutrient_gain)
    light_gain = wcell.light * cfg.base_light_gain

    # Storage ancora bravo ad accumulare, ma meno sbilanciato
    if cell.cell_type == CellType.STORAGE:
        nutrient_gain *= 1.10
    elif cell.cell_type == CellType.MEMBRANE:
        light_gain *= 1.18
    elif cell.cell_type == CellType.STEM:
        nutrient_gain *= 0.95
        light_gain *= 1.05

    return nutrient_gain + light_gain


def damage_from_world(cfg, x: int, y: int, world, hazard_avoidance: float, cell: BodyCell | None = None) -> float:
    wcell = world.get_cell(x, y)
    terrain_damage = cfg.hazard_damage_scale if int(wcell.terrain) == 2 else 0.0
    toxin_damage = wcell.toxin * cfg.toxin_damage_scale
    damage = (terrain_damage + toxin_damage) * (1.0 - 0.5 * hazard_avoidance)

    # Membrana un po' più resistente
    if cell is not None and cell.cell_type == CellType.MEMBRANE:
        damage *= 0.82

    return damage


def repair_cell(cfg, cell: BodyCell, repair_bias: float) -> None:
    if cell.health < 0.94 and cell.energy > cfg.repair_cost:
        repair_amount = cfg.repair_cost * (0.8 + 0.7 * repair_bias)

        # Storage ripara meno bene, membrane un po' meglio
        if cell.cell_type == CellType.STORAGE:
            repair_amount *= 0.88
        elif cell.cell_type == CellType.MEMBRANE:
            repair_amount *= 1.08

        cell.energy -= cfg.repair_cost
        cell.health = min(1.0, cell.health + repair_amount)