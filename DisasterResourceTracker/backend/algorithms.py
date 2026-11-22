"""
Heuristic Algorithms for Disaster Resource Tracker.

NOTE ON METHODOLOGY:
The algorithms implemented here are project-specific heuristics developed for
academic evaluation and operational modeling. They are based on standard
multi-criteria decision analysis (MCDA) principles used in disaster management,
combining official empirical vulnerability indices (such as DFSI) with
historical casualty records and flood inundation metrics.
"""

def min_max_normalize(values, target_min=0.0, target_max=100.0):
    """
    Linearly scales a list or pandas Series of numerical values to [target_min, target_max].
    Handles zero-variance safely by returning the midpoint.
    """
    val_min = min(values)
    val_max = max(values)
    if val_max == val_min:
        return [50.0 for _ in values]
    
    scale = (target_max - target_min) / (val_max - val_min)
    return [round(target_min + (v - val_min) * scale, 2) for v in values]


def calculate_district_risk_scores(districts_df):
    """
    Computes a composite vulnerability Risk Score (0 - 100) and assigns a Risk Tier
    ('High', 'Moderate', 'Low') for each district.

    Heuristic Formula:
        RiskScore = (w1 * Norm_DFSI) + (w2 * Norm_FloodedArea) +
                    (w3 * Norm_CasualtyRate) + (w4 * Norm_Duration)

    Weights:
        - w1 = 0.35 (DFSI: District Flood Susceptibility Index from satellite/meteorological modeling)
        - w2 = 0.30 (Corrected Percent Flooded Area: Physical extent of inundation)
        - w3 = 0.20 (Casualty Rate per 100k population: Human vulnerability)
        - w4 = 0.15 (Mean Flood Duration in days: Disaster persistence)

    Risk Tiers:
        - RiskScore >= 60.0 -> 'High'
        - 30.0 <= RiskScore < 60.0 -> 'Moderate'
        - RiskScore < 30.0 -> 'Low'
    """
    df = districts_df.copy()

    # 1. Fill missing values defensively
    df['dfsi_score'] = df['dfsi_score'].fillna(df['dfsi_score'].median())
    df['corrected_flooded_area'] = df['corrected_flooded_area'].fillna(0.0)
    df['mean_flood_duration_days'] = df['mean_flood_duration_days'].fillna(
        df['mean_flood_duration_days'].median()
    )

    # 2. Compute Casualty Rate per 100,000 population
    # Guard against zero/missing population by defaulting to minimum 1,000
    safe_pop = df['population'].apply(lambda p: max(p, 1000) if p and p > 0 else 100000)
    casualty_rate = ((df['human_fatality_total'] + 0.5 * df['human_injured_total']) / safe_pop) * 100000

    # 3. Min-Max Normalization (0 to 100)
    norm_dfsi = min_max_normalize(df['dfsi_score'].tolist())
    norm_area = min_max_normalize(df['corrected_flooded_area'].tolist())
    norm_cas = min_max_normalize(casualty_rate.tolist())
    norm_dur = min_max_normalize(df['mean_flood_duration_days'].tolist())

    # 4. Weighted Combination
    scores = []
    tiers = []
    for i in range(len(df)):
        score = (
            0.35 * norm_dfsi[i] +
            0.30 * norm_area[i] +
            0.20 * norm_cas[i] +
            0.15 * norm_dur[i]
        )
        score = round(score, 2)
        scores.append(score)

        if score >= 60.0:
            tiers.append("High")
        elif score >= 30.0:
            tiers.append("Moderate")
        else:
            tiers.append("Low")

    df['risk_score'] = scores
    df['risk_tier'] = tiers
    return df


def calculate_request_priority_score(urgency_level, district_risk_tier, quantity_requested, available_quantity):
    """
    Heuristic algorithm to compute the dispatch priority of a relief resource request.
    Produces a score from 0 to 100 to sort requests in the relief coordinator queue.

    Components:
    1. Base Urgency Weight (Max 40 points):
       - 'Critical': 40
       - 'High': 30
       - 'Medium': 20
       - 'Low': 10

    2. District Vulnerability Weight (Max 30 points):
       - 'High': 30
       - 'Moderate': 15
       - 'Low': 5

    3. Supply-to-Demand Feasibility Ratio (Max 30 points):
       - Prioritizes requests where stock exists and can satisfy critical demand
    """
    urgency_map = {"Critical": 40.0, "High": 30.0, "Medium": 20.0, "Low": 10.0}
    tier_map = {"High": 30.0, "Moderate": 15.0, "Low": 5.0}

    u_score = urgency_map.get(urgency_level, 10.0)
    d_score = tier_map.get(district_risk_tier, 5.0)

    # Feasibility: If stock is available to satisfy at least part of request
    if available_quantity <= 0:
        f_score = 5.0  # Stock depleted, still queued but marked low feasibility
    elif available_quantity >= quantity_requested:
        f_score = 30.0  # Can fulfill immediately
    else:
        f_score = round(30.0 * (available_quantity / quantity_requested), 2)

    total_priority = min(100.0, round(u_score + d_score + f_score, 2))
    return total_priority
