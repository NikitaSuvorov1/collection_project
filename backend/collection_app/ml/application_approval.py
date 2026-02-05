"""Stub for credit application approval model.

This model should accept application data and return approval probability.
It expects to receive scoring results (probability of overdue) as an input.
"""

def score_application(application_data: dict) -> float:
    """Return probability of approval between 0 and 1.

    application_data may include 'overdue_probability' computed by the
    overdue scoring model.
    """
    base = 0.5
    overdue = application_data.get('overdue_probability', 0.0)
    # simple rule: higher overdue reduces approval
    return min(max(base - overdue * 0.8, 0.0), 1.0)
