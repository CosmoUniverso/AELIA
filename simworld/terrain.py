from enum import IntEnum


class Terrain(IntEnum):
    EMPTY = 0
    WALL = 1
    HAZARD = 2
    RESOURCE = 3
