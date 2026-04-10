def build_summary(tick: int, body_summary: dict, env_summary: dict) -> dict:
    return {
        'tick': tick,
        'body': body_summary,
        'environment': env_summary,
    }
