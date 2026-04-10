from __future__ import annotations

from typing import Optional

from config import Config
from simworld.world import SimWorld
from body.nca import BodyNCA
from cognition.cognitive_core import CognitiveCore
from cognition.bridge import BridgeController, GlobalModulators
from cognition.memory import ShortMemory
from cognition.homeostasis import HomeostasisController
from fitness.metrics import FitnessEngine
from persistence.save_manager import PersistenceManager
from runtime.death_rules import is_dead
from runtime.scheduler import should_run_cognition, should_save_snapshot
from cognition.experience_memory import ExperienceMemory
from cognition.adaptive_controller import AdaptiveController


class OrganismRuntime:
    def __init__(self, cfg: Optional[Config] = None) -> None:
        self.cfg = cfg or Config()
        self.world = SimWorld(self.cfg)
        self.body = BodyNCA(self.cfg)
        self.cognitive = CognitiveCore()
        self.bridge = BridgeController()
        self.homeostasis = HomeostasisController()
        self.memory = ShortMemory()
        self.experience_memory = ExperienceMemory()
        self.adaptive = AdaptiveController(self.experience_memory)
        self.fitness = FitnessEngine()
        self.persistence = PersistenceManager(self.cfg)
        self.mods = GlobalModulators()
        self.tick = 0
        self.low_energy_ticks = 0
        self.low_health_ticks = 0
        self.last_intent: Optional[dict] = None

    def reset(self) -> None:
        self.__init__(self.cfg)

    def _death_check(self) -> bool:
        mean_energy = self.body.mean_energy()
        mean_health = self.body.mean_health()

        self.low_energy_ticks = (
            self.low_energy_ticks + 1
            if mean_energy < self.cfg.death_energy_threshold
            else 0
        )
        self.low_health_ticks = (
            self.low_health_ticks + 1
            if mean_health < self.cfg.death_health_threshold
            else 0
        )

        return is_dead(self.cfg, self.body, self.low_energy_ticks, self.low_health_ticks)

    def maybe_help_from_user(self, x: int, y: int, amount: float) -> None:
        self.world.inject_user_energy(x, y, amount)

    def inject_toxin(self, x: int, y: int, amount: float) -> None:
        self.world.inject_toxin(x, y, amount)

    def save_snapshot_now(self) -> None:
        self.persistence.save_snapshot(
            self.tick,
            self.body,
            self.world,
            self.mods,
            self.last_intent,
        )

    def step(self) -> bool:
        self.world.step()
        self.body.update(self.world, self.mods)
        self.fitness.capture(self.tick, self.body)

        if should_run_cognition(self.tick, self.cfg.cognitive_interval):
            summary = self.fitness.summarize_for_cognition(self.tick, self.body, self.world)

            # prima salva eventuale esperienza maturata
            self.adaptive.maybe_store_experience(self.tick, summary)

            self.last_intent = self.cognitive.infer(summary)
            bridged_mods = self.bridge.translate(self.last_intent)
            homeostatic_mods = self.homeostasis.adapt(summary, bridged_mods)
            self.mods = self.adaptive.choose_mods(self.tick, summary, homeostatic_mods)

            self.memory.push({
                'tick': self.tick,
                'intent': self.last_intent,
                'mods': {
                    'growth_strength': self.mods.growth_strength,
                    'storage_bias': self.mods.storage_bias,
                    'membrane_bias': self.mods.membrane_bias,
                    'compactness_bias': self.mods.compactness_bias,
                    'prune_bias': self.mods.prune_bias,
                    'metabolic_thrift': self.mods.metabolic_thrift,
                },
                'derived': summary.get('derived', {}),
                'experience_memory_size': self.experience_memory.size(),
            })

        if should_save_snapshot(self.tick, self.cfg.snapshot_interval):
            self.save_snapshot_now()

        self.tick += 1
        return not self._death_check()

    def run_headless(self, max_ticks: Optional[int] = None, verbose_every: int = 50) -> None:
        limit = max_ticks or self.cfg.max_ticks

        while self.tick < limit:
            alive = self.step()

            if self.tick % verbose_every == 0:
                print(
                    f"tick={self.tick:5d} "
                    f"mass={self.body.mass():3d} "
                    f"E={self.body.mean_energy():.3f} "
                    f"H={self.body.mean_health():.3f} "
                    f"compact={self.body.compactness():.3f} "
                    f"mods[g={self.mods.growth_strength:.2f},"
                    f"s={self.mods.storage_bias:.2f},"
                    f"m={self.mods.membrane_bias:.2f}]"
                )

            if not alive:
                print(f"Organism died at tick {self.tick}")
                return

        print(f"Run completed at tick {self.tick}")

    def debug_body_state(self) -> dict:
        summary = self.body.summarize()
        return {
            'tick': self.tick,
            'mass': summary['mass'],
            'mean_energy': summary['mean_energy'],
            'mean_health': summary['mean_health'],
            'compactness': summary['compactness'],
            'cell_type_distribution': summary['cell_type_distribution'],
            'last_intent': self.last_intent,
            'mods': {
                'growth_strength': self.mods.growth_strength,
                'storage_bias': self.mods.storage_bias,
                'membrane_bias': self.mods.membrane_bias,
                'compactness_bias': self.mods.compactness_bias,
                'prune_bias': self.mods.prune_bias,
                'metabolic_thrift': self.mods.metabolic_thrift,
            }
        }