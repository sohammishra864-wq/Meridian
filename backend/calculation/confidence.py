def compute_metric_confidence(
    source_tier: int,
    freshness_days: int,
    xbrl_validated: bool,
    cross_ref_flag: bool,
    is_estimated: bool,
) -> float:
    """Universal confidence formula."""
    tier_weight = {1: 1.0, 2: 0.9, 3: 0.75, 4: 0.6, 5: 0.4}[source_tier]
    freshness = 1.0 if freshness_days <= 90 else max(0.5, 1.0 - (freshness_days - 90) / 550)
    xbrl_penalty = 1.0 if xbrl_validated else 0.75
    crossref_pen = 0.90 if cross_ref_flag else 1.0
    estimate_pen = 0.70 if is_estimated else 1.0
    return round(min(tier_weight * freshness * xbrl_penalty * crossref_pen * estimate_pen, 1.0), 4)
