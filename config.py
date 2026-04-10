from dataclasses import dataclass


@dataclass
class Config:
    grid_w: int = 48
    grid_h: int = 48
    cell_px: int = 14
    fps: int = 30
    snapshot_interval: int = 100
    cognitive_interval: int = 20
    nutrient_diffusion: float = 0.025
    toxin_diffusion: float = 0.012
    nutrient_decay: float = 0.001
    toxin_decay: float = 0.001
    ambient_light: float = 0.09

    base_nutrient_gain = 0.038
    base_light_gain = 0.003
    base_cost_alive = 0.0024

    cost_stem = 0.0038
    cost_membrane = 0.0024
    cost_storage = 0.0022

    growth_cost = 0.026
    repair_cost = 0.010

    hazard_damage_scale = 0.035
    toxin_damage_scale = 0.040

    energy_share_rate = 0.13

    seed_x: int = 24
    seed_y: int = 24
    min_mass: int = 3
    death_energy_threshold: float = 0.02
    death_health_threshold: float = 0.02
    death_low_energy_ticks: int = 80
    death_low_health_ticks: int = 55
    max_ticks: int = 200000
    save_dir: str = 'saves'
    window_title: str = 'AEGIS Embryo v0.2'
    hud_width: int = 300
