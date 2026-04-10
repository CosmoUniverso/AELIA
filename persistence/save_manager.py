from __future__ import annotations

from pathlib import Path

from persistence.snapshot import build_snapshot_payload
from persistence.serializer import to_json


class PersistenceManager:
    def __init__(self, cfg) -> None:
        self.cfg = cfg
        self.save_dir = Path(cfg.save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, tick: int, body, world, mods, last_intent) -> Path:
        world_summary = {
            'resource_cells': sum(1 for row in world.grid for cell in row if int(cell.terrain) == 3),
            'mean_nutrient': round(sum(cell.nutrient for row in world.grid for cell in row) / (world.cfg.grid_w * world.cfg.grid_h), 4),
            'mean_toxin': round(sum(cell.toxin for row in world.grid for cell in row) / (world.cfg.grid_w * world.cfg.grid_h), 4),
        }
        payload = build_snapshot_payload(tick, body.summarize(), vars(mods), last_intent, world_summary)
        path = self.save_dir / f'snapshot_{tick:06d}.json'
        path.write_text(to_json(payload), encoding='utf-8')
        return path
