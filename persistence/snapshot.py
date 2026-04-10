def build_snapshot_payload(tick: int, body_summary: dict, mods: dict, last_intent, world_summary: dict) -> dict:
    return {
        'tick': tick,
        'body': body_summary,
        'global_modulators': mods,
        'last_intent': last_intent,
        'world_summary': world_summary,
    }
