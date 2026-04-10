from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import math


@dataclass
class ExperienceRecord:
    tick: int
    state: Dict[str, float]
    action: Dict[str, float]
    outcome: Dict[str, float]
    reward: float

    def to_dict(self) -> dict:
        return asdict(self)


class ExperienceMemory:
    """
    Memoria esperienziale semplice.

    Salva episodi del tipo:
    - stato osservato
    - azione/modulatori scelti
    - outcome dopo una finestra temporale
    - reward finale

    Poi recupera gli episodi più simili allo stato attuale.
    """

    def __init__(
        self,
        path: str = "saves/experience_memory.jsonl",
        max_records: int = 5000,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_records = max_records
        self.records: List[ExperienceRecord] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return

        try:
            with self.path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    raw = json.loads(line)
                    self.records.append(
                        ExperienceRecord(
                            tick=int(raw["tick"]),
                            state=dict(raw["state"]),
                            action=dict(raw["action"]),
                            outcome=dict(raw["outcome"]),
                            reward=float(raw["reward"]),
                        )
                    )
        except Exception:
            # Se il file è corrotto, meglio non bloccare il runtime
            self.records = []

        if len(self.records) > self.max_records:
            self.records = self.records[-self.max_records :]

    def _append_to_disk(self, record: ExperienceRecord) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    def add(
        self,
        tick: int,
        state: Dict[str, float],
        action: Dict[str, float],
        outcome: Dict[str, float],
        reward: float,
    ) -> None:
        record = ExperienceRecord(
            tick=tick,
            state=state,
            action=action,
            outcome=outcome,
            reward=reward,
        )
        self.records.append(record)
        if len(self.records) > self.max_records:
            self.records = self.records[-self.max_records :]
        self._append_to_disk(record)

    def _distance(self, a: Dict[str, float], b: Dict[str, float]) -> float:
        """
        Distanza euclidea su feature numeriche condivise.
        Più è piccola, più gli stati sono simili.
        """
        keys = sorted(set(a.keys()) & set(b.keys()))
        if not keys:
            return float("inf")

        total = 0.0
        for k in keys:
            av = float(a[k])
            bv = float(b[k])
            total += (av - bv) ** 2
        return math.sqrt(total)

    def nearest(
        self,
        state: Dict[str, float],
        k: int = 12,
        min_reward: Optional[float] = None,
    ) -> List[Tuple[ExperienceRecord, float]]:
        ranked: List[Tuple[ExperienceRecord, float]] = []

        for rec in self.records:
            if min_reward is not None and rec.reward < min_reward:
                continue
            dist = self._distance(state, rec.state)
            if math.isfinite(dist):
                ranked.append((rec, dist))

        ranked.sort(key=lambda item: item[1])
        return ranked[:k]

    def best_action_for_state(
        self,
        state: Dict[str, float],
        k: int = 10,
    ) -> Optional[Dict[str, float]]:
        """
        Cerca episodi simili e restituisce una media pesata delle azioni migliori.
        """
        neighbors = self.nearest(state, k=k)
        if not neighbors:
            return None

        # usa peso inverso della distanza e reward positivo
        accum: Dict[str, float] = {}
        total_weight = 0.0

        for rec, dist in neighbors:
            reward_factor = max(0.05, rec.reward + 2.0)
            weight = reward_factor / max(0.05, dist + 0.05)

            for key, value in rec.action.items():
                accum[key] = accum.get(key, 0.0) + float(value) * weight

            total_weight += weight

        if total_weight <= 0:
            return None

        return {k: v / total_weight for k, v in accum.items()}

    def size(self) -> int:
        return len(self.records)