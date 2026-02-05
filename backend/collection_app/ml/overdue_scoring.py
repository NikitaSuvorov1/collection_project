"""Stub for overdue scoring model.

Replace the contents of `score_client` with a real model inference.
"""

def score_client(client_data: dict) -> float:
    """Return probability of becoming overdue between 0 and 1.

    client_data is a dict containing client features. This stub returns a
    simple heuristic based on absent phone/email.
    """
    score = 0.05
    if not client_data.get('phone'):
        score += 0.2
    if not client_data.get('email'):
        score += 0.1
    return min(max(score, 0.0), 1.0)
