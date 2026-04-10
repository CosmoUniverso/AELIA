from dataclasses import dataclass
import math


@dataclass
class GlobalModulators:
    growth_direction_x: float = 0.0
    growth_direction_y: float = 0.0
    growth_strength: float = 0.5
    repair_bias: float = 0.5
    prune_bias: float = 0.1
    metabolic_thrift: float = 0.5
    hazard_avoidance: float = 0.7
    compactness_bias: float = 0.6
    storage_bias: float = 0.5
    membrane_bias: float = 0.5


class BridgeController:
    def translate(self, intent: dict) -> GlobalModulators:
        growth_bias = intent.get('growth_bias', [0.0, 0.0])
        gx = float(growth_bias[0])
        gy = float(growth_bias[1])

        norm = math.sqrt(gx * gx + gy * gy)
        if norm > 0.15:
            gx /= norm
            gy /= norm
        else:
            gx = 0.0
            gy = 0.0

        metabolism_mode = str(intent.get('metabolism_mode', 'balanced'))
        preferred_shape = str(intent.get('preferred_shape', 'stable'))
        mass_hint = int(intent.get('mass_hint', 0))

        if metabolism_mode == 'conservative':
            thrift = 0.64
        else:
            thrift = 0.46

        if preferred_shape == 'compact':
            compactness = 0.82
        else:
            compactness = 0.62

        growth_strength = 0.42
        if mass_hint > 160:
            growth_strength = 0.30
        if mass_hint > 220:
            growth_strength = 0.18

        prune_bias = 0.28
        if mass_hint > 220:
            prune_bias = 0.38

        return GlobalModulators(
            growth_direction_x=gx,
            growth_direction_y=gy,
            growth_strength=growth_strength,
            repair_bias=float(intent.get('repair_priority', 0.5)),
            prune_bias=prune_bias,
            metabolic_thrift=thrift,
            hazard_avoidance=1.0 - float(intent.get('risk_tolerance', 0.3)),
            compactness_bias=compactness,
            storage_bias=float(intent.get('storage_bias', 0.5)),
            membrane_bias=float(intent.get('membrane_bias', 0.5)),
        )