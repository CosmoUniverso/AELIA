def is_dead(cfg, body, low_energy_ticks: int, low_health_ticks: int) -> bool:
    if body.mass() < cfg.min_mass:
        return True
    if low_energy_ticks >= cfg.death_low_energy_ticks:
        return True
    if low_health_ticks >= cfg.death_low_health_ticks:
        return True
    return False
