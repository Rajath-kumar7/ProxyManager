from .config import config

WEIGHTS = config.get("scoring_weights")


def calculate_score(latency_ms: int, download_mbps: float, is_working: bool) -> float:
    """Calculates a score for a proxy based on its performance metrics."""
    if not is_working:
        return 0.0

    # Normalize latency (lower is better). Assume max acceptable latency is 5000ms.
    # Score is 1 for 0ms, 0 for 5000ms or more.
    latency_score = max(0, 1 - (latency_ms / 5000))

    # Normalize speed (higher is better). Assume max expected speed is 10 Mbps.
    # Score is 1 for 10Mbps or more, 0 for 0 Mbps.
    speed_score = min(1, download_mbps / 10)

    # For v1, stability is just 1.0 if it works.
    stability_score = 1.0

    # Calculate weighted score
    final_score = (
            latency_score * WEIGHTS['latency'] +
            speed_score * WEIGHTS['speed'] +
            stability_score * WEIGHTS['stability']
    )

    return round(final_score, 4)
