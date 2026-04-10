def should_run_cognition(tick: int, interval: int) -> bool:
    return tick % interval == 0


def should_save_snapshot(tick: int, interval: int) -> bool:
    return tick % interval == 0
