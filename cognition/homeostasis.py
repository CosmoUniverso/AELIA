from __future__ import annotations

from dataclasses import replace
import math
import random
from typing import Optional


class HomeostasisController:
    """
    Meta-controller adattivo leggero.

    Non si basa solo su regole fisse:
    - osserva summary + metriche derivate
    - valuta un reward omeostatico
    - propone piccole mutazioni dei modulatori
    - mantiene quelle che migliorano il reward
    - scarta o inverte quelle che peggiorano

    Obiettivo:
    trovare da solo un equilibrio fra:
    - crescita
    - accumulo
    - compattezza
    - mobilità
    - sopravvivenza
    """

    def __init__(self, seed: int = 777) -> None:
        self.rng = random.Random(seed)
        self.last_reward: Optional[float] = None
        self.last_candidate = None
        self.last_base_mods = None

        self.best_reward_seen: float = -10**9
        self.steps_since_improvement: int = 0
        self.mutation_scale: float = 0.06

    def _clamp(self, value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def _reward(self, summary: dict) -> float:
        body = summary['body']
        derived = summary['derived']

        mass = float(body['mass'])
        mean_energy = float(body['mean_energy'])
        mean_health = float(body['mean_health'])
        compactness = float(body['compactness'])

        distribution = body['cell_type_distribution']
        stem_ratio = float(distribution.get('stem', 0.0))
        membrane_ratio = float(distribution.get('membrane', 0.0))
        storage_ratio = float(distribution.get('storage', 0.0))

        net_energy_delta = float(derived['net_energy_delta'])
        surface_ratio = float(derived['surface_ratio'])
        growth_efficiency = float(derived['growth_efficiency'])
        mobility = float(derived['mobility'])

        # Reward composito:
        # - energia buona ma non eccessiva
        # - salute alta
        # - crescita efficiente
        # - corpo non troppo filamentoso
        # - un minimo di mobilità
        # - composizione non collassata
        energy_target = 0.22
        energy_score = 1.0 - abs(mean_energy - energy_target) / max(energy_target, 0.01)
        energy_score = self._clamp(energy_score, -1.0, 1.0)

        health_score = mean_health
        delta_score = self._clamp(net_energy_delta * 8.0, -1.0, 1.0)
        compact_score = self._clamp(compactness * 2.0, 0.0, 1.2)
        efficiency_score = self._clamp(growth_efficiency, 0.0, 1.0)
        mobility_score = self._clamp(mobility * 1.5, 0.0, 0.6)

        # Penalità massa troppo alta o troppo bassa
        if mass < 12:
            mass_score = -0.8
        elif mass < 70:
            mass_score = 0.25
        elif mass < 180:
            mass_score = 0.55
        elif mass < 260:
            mass_score = 0.15
        else:
            mass_score = -0.9

        # Penalità per forme troppo sottili / frastagliate
        surface_penalty = self._clamp((surface_ratio - 0.42) * 2.5, 0.0, 1.5)

        # Penalità per collasso di tipo cellulare
        composition_penalty = 0.0
        if membrane_ratio > 0.82:
            composition_penalty += 0.5
        if storage_ratio > 0.68:
            composition_penalty += 0.6
        if stem_ratio < 0.01:
            composition_penalty += 0.35

        reward = (
            1.8 * health_score +
            1.2 * energy_score +
            1.0 * efficiency_score +
            0.7 * compact_score +
            0.6 * delta_score +
            0.35 * mobility_score +
            1.0 * mass_score
            - 1.2 * surface_penalty
            - 1.0 * composition_penalty
        )

        return reward

    def _mutate_mods(self, mods):
        candidate = replace(mods)

        # Mutazioni piccole e progressive
        candidate.growth_strength = self._clamp(
            candidate.growth_strength + self.rng.uniform(-self.mutation_scale, self.mutation_scale),
            0.08, 0.55
        )
        candidate.storage_bias = self._clamp(
            candidate.storage_bias + self.rng.uniform(-self.mutation_scale, self.mutation_scale),
            0.18, 0.82
        )
        candidate.membrane_bias = self._clamp(
            candidate.membrane_bias + self.rng.uniform(-self.mutation_scale, self.mutation_scale),
            0.18, 0.82
        )
        candidate.compactness_bias = self._clamp(
            candidate.compactness_bias + self.rng.uniform(-self.mutation_scale, self.mutation_scale),
            0.20, 0.98
        )
        candidate.prune_bias = self._clamp(
            candidate.prune_bias + self.rng.uniform(-self.mutation_scale * 0.7, self.mutation_scale * 0.7),
            0.08, 0.60
        )
        candidate.metabolic_thrift = self._clamp(
            candidate.metabolic_thrift + self.rng.uniform(-self.mutation_scale * 0.5, self.mutation_scale * 0.5),
            0.20, 0.82
        )

        return candidate

    def _stabilize(self, summary: dict, mods):
        """
        Piccoli vincoli di sicurezza.
        Non sono regole comportamentali complete:
        servono solo a impedire collassi stupidi.
        """
        body = summary['body']
        derived = summary['derived']

        mass = float(body['mass'])
        mean_energy = float(body['mean_energy'])
        compactness = float(body['compactness'])
        distribution = body['cell_type_distribution']

        membrane_ratio = float(distribution.get('membrane', 0.0))
        storage_ratio = float(distribution.get('storage', 0.0))

        net_energy_delta = float(derived['net_energy_delta'])
        surface_ratio = float(derived['surface_ratio'])

        # Se è enorme e affamato, frena
        if mass > 180 and mean_energy < 0.12 and net_energy_delta < 0:
            mods.growth_strength = self._clamp(mods.growth_strength - 0.03, 0.08, 0.55)
            mods.storage_bias = self._clamp(mods.storage_bias + 0.03, 0.18, 0.82)
            mods.compactness_bias = self._clamp(mods.compactness_bias + 0.04, 0.20, 0.98)

        # Se è troppo filamentoso, compatta
        if surface_ratio > 0.48 or compactness < 0.20:
            mods.growth_strength = self._clamp(mods.growth_strength - 0.02, 0.08, 0.55)
            mods.compactness_bias = self._clamp(mods.compactness_bias + 0.05, 0.20, 0.98)
            mods.prune_bias = self._clamp(mods.prune_bias + 0.03, 0.08, 0.60)

        # Se la membrana domina troppo, spingi riserva
        if membrane_ratio > 0.78 and storage_ratio < 0.15:
            mods.storage_bias = self._clamp(mods.storage_bias + 0.04, 0.18, 0.82)
            mods.membrane_bias = self._clamp(mods.membrane_bias - 0.03, 0.18, 0.82)

        # Se lo storage domina troppo, riequilibra
        if storage_ratio > 0.58 and membrane_ratio < 0.18:
            mods.storage_bias = self._clamp(mods.storage_bias - 0.04, 0.18, 0.82)
            mods.membrane_bias = self._clamp(mods.membrane_bias + 0.04, 0.18, 0.82)

        return mods

    def adapt(self, summary: dict, mods):
        current_reward = self._reward(summary)

        # Primo giro: nessun confronto possibile
        if self.last_reward is None:
            self.last_reward = current_reward
            candidate = self._mutate_mods(mods)
            candidate = self._stabilize(summary, candidate)
            self.last_candidate = candidate
            self.last_base_mods = replace(mods)
            return candidate

        # Valuta se la mutazione dell'ultimo ciclo è stata utile
        if current_reward > self.last_reward:
            # La mutazione è andata bene: la teniamo e proviamo a esplorare ancora
            accepted_mods = mods
            if current_reward > self.best_reward_seen:
                self.best_reward_seen = current_reward
                self.steps_since_improvement = 0
                self.mutation_scale = self._clamp(self.mutation_scale * 0.98, 0.02, 0.10)
            else:
                self.steps_since_improvement += 1
        else:
            # La mutazione ha peggiorato: torno vicino alla base precedente
            accepted_mods = replace(self.last_base_mods) if self.last_base_mods is not None else mods
            self.steps_since_improvement += 1
            self.mutation_scale = self._clamp(self.mutation_scale * 1.03, 0.02, 0.14)

        # Se da troppo non migliora, aumenta leggermente esplorazione
        if self.steps_since_improvement > 10:
            self.mutation_scale = self._clamp(self.mutation_scale + 0.01, 0.02, 0.16)
            self.steps_since_improvement = 0

        # Crea il prossimo candidato
        base_for_next = replace(accepted_mods)
        next_candidate = self._mutate_mods(base_for_next)
        next_candidate = self._stabilize(summary, next_candidate)

        self.last_reward = current_reward
        self.last_base_mods = replace(accepted_mods)
        self.last_candidate = next_candidate

        return next_candidate