from dataclasses import dataclass
from enum import IntEnum


class CellType(IntEnum):
    STEM = 0
    MEMBRANE = 1
    STORAGE = 2


@dataclass
class BodyCell:
    alive: bool = False
    energy: float = 0.0
    health: float = 0.0
    age: int = 0
    cell_type: CellType = CellType.STEM
    polarity_x: float = 0.0
    polarity_y: float = 0.0
    stress: float = 0.0
    repair_signal: float = 0.0
    resource_signal: float = 0.0
