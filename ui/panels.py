def build_lines(runtime) -> list[str]:
    body = runtime.body
    intent = runtime.last_intent['intent'] if runtime.last_intent else 'boot'
    return [
        f'Tick: {runtime.tick}',
        f'Mass: {body.mass()}',
        f'Mean energy: {body.mean_energy():.3f}',
        f'Mean health: {body.mean_health():.3f}',
        f'Compactness: {body.compactness():.3f}',
        f'Resources: {body.total_resources_collected:.2f}',
        f'Damage: {body.total_damage_taken:.2f}',
        f'Intent: {intent}',
        'Controls:',
        'SPACE pause',
        'R reset',
        'S snapshot',
        'Left click nutrient',
        'Right click toxin',
    ]
