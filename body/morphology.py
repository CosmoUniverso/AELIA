from __future__ import annotations

from typing import Dict, Tuple


def center_of_mass(body) -> Tuple[float, float]:
    alive = [(x, y) for x, y, _ in body.iter_alive()]
    if not alive:
        return 0.0, 0.0
    sx = sum(p[0] for p in alive)
    sy = sum(p[1] for p in alive)
    return sx / len(alive), sy / len(alive)


def compactness(body) -> float:
    alive = {(x, y) for x, y, _ in body.iter_alive()}
    if not alive:
        return 0.0
    perimeter = 0
    for x, y in alive:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (x + dx, y + dy) not in alive:
                perimeter += 1
    area = len(alive)
    return area / perimeter if perimeter > 0 else 0.0


def distribution(body) -> Dict[str, float]:
    counts = {ctype.name.lower(): 0 for ctype in body.cell_types_enum}
    total = 0
    for _, _, cell in body.iter_alive():
        counts[cell.cell_type.name.lower()] += 1
        total += 1
    total = max(1, total)
    return {k: v / total for k, v in counts.items()}
