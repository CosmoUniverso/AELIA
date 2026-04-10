class CognitiveCore:
    """
    Stub euristico per la v0.2.
    Più avanti puoi sostituirlo con un vero LLM che produce lo stesso schema dict/JSON.
    """

    def infer(self, summary: dict) -> dict:
        body = summary['body']
        env = summary['environment']

        mass = int(body['mass'])
        mean_energy = float(body['mean_energy'])
        mean_health = float(body['mean_health'])
        compactness = float(body['compactness'])

        nutrient_gradient = env['nutrient_gradient']
        toxin_gradient = env['toxin_gradient']
        hazard_proximity = int(env['hazard_proximity'])

        repair_priority = 0.85 if mean_health < 0.58 else 0.48
        metabolism_mode = 'conservative' if mean_energy < 0.18 else 'balanced'
        preferred_shape = 'compact' if compactness < 0.48 else 'stable'

        growth_bias = [
            float(nutrient_gradient[0]) - 0.95 * float(toxin_gradient[0]),
            float(nutrient_gradient[1]) - 0.95 * float(toxin_gradient[1]),
        ]

        # Storage meno estremo
        if mean_energy < 0.25:
            storage_bias = 0.58
        elif mean_energy < 0.40:
            storage_bias = 0.50
        else:
            storage_bias = 0.38

        # Più membrana se pericolo vicino o corpo troppo grande
        if hazard_proximity < 4:
            membrane_bias = 0.68
        else:
            membrane_bias = 0.46

        if mass > 180:
            membrane_bias = max(membrane_bias, 0.66)
            storage_bias *= 0.72

        return {
            'intent': 'seek_energy_preserve_integrity',
            'risk_tolerance': 0.10 if mean_health < 0.45 else 0.26,
            'growth_bias': growth_bias,
            'repair_priority': repair_priority,
            'exploration_weight': 0.18,
            'metabolism_mode': metabolism_mode,
            'preferred_shape': preferred_shape,
            'storage_bias': storage_bias,
            'membrane_bias': membrane_bias,
            'mass_hint': mass,
        }