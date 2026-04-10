from __future__ import annotations

from dataclasses import replace
from typing import Dict, Optional
import random

from cognition.bridge import GlobalModulators
from cognition.experience_memory import ExperienceMemory


class AdaptiveController:
    """
    Controller che sceglie i modulatori usando:
    1. intent base dal bridge
    2. memoria di episodi simili
    3. piccola esplorazione casuale controllata

    Inoltre registra l'esito dopo una finestra temporale.
    """

    def __init__(
        self,
        memory: Optional[ExperienceMemory] = None,
        seed: int = 999,
        evaluation_window: int = 4,
    ) -> None:
        self.memory = memory or ExperienceMemory()
        self.rng = random.Random(seed)
        self.evaluation_window = evaluation_window

        self.pending_state: Optional[Dict[str, float]] = None
        self.pending_action: Optional[Dict[str, float]] = None
        self.pending_tick: Optional[int] = None
        self.pending_summary: Optional[dict] = None

    def _clamp(self, value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def _state_vector(self, summary: dict) -> Dict[str, float]:
        body = summary["body"]
        env = summary["environment"]
        derived = summary["derived"]
        dist = body["cell_type_distribution"]

        return {
            "mass": float(body["mass"]),
            "mean_energy": float(body["mean_energy"]),
            "mean_health": float(body["mean_health"]),
            "compactness": float(body["compactness"]),
            "stem_ratio": float(dist.get("stem", 0.0)),
            "membrane_ratio": float(dist.get("membrane", 0.0)),
            "storage_ratio": float(dist.get("storage", 0.0)),
            "hazard_proximity": float(env.get("hazard_proximity", 0.0)),
            "resource_grad_x": float(env["nutrient_gradient"][0]),
            "resource_grad_y": float(env["nutrient_gradient"][1]),
            "net_energy_delta": float(derived.get("net_energy_delta", 0.0)),
            "surface_ratio": float(derived.get("surface_ratio", 0.0)),
            "growth_efficiency": float(derived.get("growth_efficiency", 0.0)),
            "mobility": float(derived.get("mobility", 0.0)),
        }

    def _mods_to_action(self, mods: GlobalModulators) -> Dict[str, float]:
        return {
            "growth_strength": float(mods.growth_strength),
            "repair_bias": float(mods.repair_bias),
            "prune_bias": float(mods.prune_bias),
            "metabolic_thrift": float(mods.metabolic_thrift),
            "hazard_avoidance": float(mods.hazard_avoidance),
            "compactness_bias": float(mods.compactness_bias),
            "storage_bias": float(mods.storage_bias),
            "membrane_bias": float(mods.membrane_bias),
        }

    def _apply_action_to_mods(
        self,
        base_mods: GlobalModulators,
        action: Dict[str, float],
    ) -> GlobalModulators:
        mods = replace(base_mods)

        for key, value in action.items():
            if hasattr(mods, key):
                setattr(mods, key, float(value))

        # clamp globale
        mods.growth_strength = self._clamp(mods.growth_strength, 0.08, 0.60)
        mods.repair_bias = self._clamp(mods.repair_bias, 0.05, 0.95)
        mods.prune_bias = self._clamp(mods.prune_bias, 0.05, 0.65)
        mods.metabolic_thrift = self._clamp(mods.metabolic_thrift, 0.15, 0.85)
        mods.hazard_avoidance = self._clamp(mods.hazard_avoidance, 0.05, 0.95)
        mods.compactness_bias = self._clamp(mods.compactness_bias, 0.20, 0.98)
        mods.storage_bias = self._clamp(mods.storage_bias, 0.12, 0.85)
        mods.membrane_bias = self._clamp(mods.membrane_bias, 0.12, 0.85)

        return mods

    def _mix_actions(
        self,
        base_action: Dict[str, float],
        memory_action: Optional[Dict[str, float]],
        summary: dict,
    ) -> Dict[str, float]:
        """
        Mescola azione base e memoria.
        Più il corpo è in crisi, più si affida alla memoria.
        """
        if memory_action is None:
            return dict(base_action)

        mean_energy = float(summary["body"]["mean_energy"])
        mean_health = float(summary["body"]["mean_health"])

        # in crisi: più peso alla memoria
        if mean_energy < 0.12 or mean_health < 0.55:
            alpha = 0.65
        elif mean_energy < 0.22:
            alpha = 0.50
        else:
            alpha = 0.35

        mixed = {}
        for key in base_action.keys():
            bv = float(base_action[key])
            mv = float(memory_action.get(key, bv))
            mixed[key] = (1.0 - alpha) * bv + alpha * mv

        return mixed

    def _explore(self, action: Dict[str, float], summary: dict) -> Dict[str, float]:
        """
        Piccola esplorazione controllata.
        Se il reward recente sembra buono, esplora meno.
        """
        explored = dict(action)

        mean_energy = float(summary["body"]["mean_energy"])
        compactness = float(summary["body"]["compactness"])
        growth_efficiency = float(summary["derived"]["growth_efficiency"])

        # scala esplorazione
        exploration = 0.03
        if mean_energy < 0.15:
            exploration = 0.015
        elif compactness < 0.20 or growth_efficiency < 0.30:
            exploration = 0.02

        for key in (
            "growth_strength",
            "storage_bias",
            "membrane_bias",
            "compactness_bias",
            "prune_bias",
            "metabolic_thrift",
        ):
            explored[key] = float(explored[key]) + self.rng.uniform(-exploration, exploration)

        return explored

    def _reward(self, summary_before: dict, summary_after: dict) -> float:
        """
        Reward transizionale: valuta se l'azione ha migliorato davvero la situazione.
        """
        b0 = summary_before["body"]
        b1 = summary_after["body"]
        d1 = summary_after["derived"]

        energy0 = float(b0["mean_energy"])
        energy1 = float(b1["mean_energy"])
        health1 = float(b1["mean_health"])
        compact1 = float(b1["compactness"])
        mass1 = float(b1["mass"])

        surface_ratio = float(d1["surface_ratio"])
        growth_efficiency = float(d1["growth_efficiency"])
        mobility = float(d1["mobility"])

        dist = b1["cell_type_distribution"]
        stem_ratio = float(dist.get("stem", 0.0))
        membrane_ratio = float(dist.get("membrane", 0.0))
        storage_ratio = float(dist.get("storage", 0.0))

        reward = 0.0

        reward += (energy1 - energy0) * 6.0
        reward += health1 * 1.5
        reward += compact1 * 1.0
        reward += growth_efficiency * 1.1
        reward += min(0.35, mobility) * 0.6

        if 35 <= mass1 <= 180:
            reward += 0.8
        elif 180 < mass1 <= 240:
            reward += 0.2
        else:
            reward -= 0.8

        if surface_ratio > 0.55:
            reward -= (surface_ratio - 0.55) * 3.0

        if stem_ratio < 0.01:
            reward -= 0.35
        if membrane_ratio > 0.82:
            reward -= 0.45
        if storage_ratio > 0.70:
            reward -= 0.50

        return reward

    def maybe_store_experience(self, tick: int, summary: dict) -> None:
        """
        Quando è passato abbastanza tempo dalla scelta precedente,
        valuta outcome e salva esperienza.
        """
        if self.pending_tick is None:
            return

        if tick - self.pending_tick < self.evaluation_window:
            return

        if self.pending_state is None or self.pending_action is None or self.pending_summary is None:
            return

        reward = self._reward(self.pending_summary, summary)

        outcome = {
            "delta_energy": float(summary["body"]["mean_energy"]) - float(self.pending_summary["body"]["mean_energy"]),
            "delta_mass": float(summary["body"]["mass"]) - float(self.pending_summary["body"]["mass"]),
            "delta_compactness": float(summary["body"]["compactness"]) - float(self.pending_summary["body"]["compactness"]),
            "delta_health": float(summary["body"]["mean_health"]) - float(self.pending_summary["body"]["mean_health"]),
            "mobility": float(summary["derived"]["mobility"]),
            "growth_efficiency": float(summary["derived"]["growth_efficiency"]),
            "surface_ratio": float(summary["derived"]["surface_ratio"]),
            "survived": 1.0,
        }

        self.memory.add(
            tick=tick,
            state=self.pending_state,
            action=self.pending_action,
            outcome=outcome,
            reward=reward,
        )

        self.pending_tick = None
        self.pending_state = None
        self.pending_action = None
        self.pending_summary = None

    def choose_mods(
        self,
        tick: int,
        summary: dict,
        base_mods: GlobalModulators,
    ) -> GlobalModulators:
        """
        Sceglie i modulatori finali:
        - base dal bridge
        - correzione memoria
        - piccola esplorazione
        """
        state = self._state_vector(summary)
        base_action = self._mods_to_action(base_mods)

        memory_action = self.memory.best_action_for_state(state, k=10)
        mixed_action = self._mix_actions(base_action, memory_action, summary)
        explored_action = self._explore(mixed_action, summary)
        final_mods = self._apply_action_to_mods(base_mods, explored_action)

        # prepara episodio pendente
        self.pending_tick = tick
        self.pending_state = state
        self.pending_action = self._mods_to_action(final_mods)
        self.pending_summary = summary

        return final_mods