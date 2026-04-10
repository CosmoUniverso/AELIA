def total_score(snapshot) -> float:
    survival = min(1.0, snapshot.tick / 5000.0)
    energy = snapshot.mean_energy
    health = snapshot.mean_health
    compactness = min(1.0, snapshot.compactness * 3.0)
    return 0.35 * survival + 0.25 * energy + 0.25 * health + 0.15 * compactness
