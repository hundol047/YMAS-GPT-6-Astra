"""BMI and vital-sign abnormal-flag helpers.

BMI is deliberately never stored (see VitalSigns in schemas.py) -- it is computed on demand from
height_cm/weight_kg so it can never go stale relative to them.

Abnormal-flag thresholds come from backend/data/vital_reference_ranges.json, the same
"SynexAgent prototype policy, not a clinical guideline" status as rule_engine.py's rule table and
data_quality.py's lab freshness table. A vital field with no entry in that table is never flagged
by guesswork.
"""
import json
from pathlib import Path

RANGES = json.loads((Path(__file__).resolve().parents[2] / 'data' / 'vital_reference_ranges.json').read_text(encoding='utf-8'))
POLICY_SOURCE = 'SynexAgent prototype policy; NOT a clinical guideline or institution policy'


def bmi(height_cm, weight_kg):
    if not height_cm or not weight_kg:
        return None
    h_m = height_cm / 100
    return round(weight_kg / (h_m * h_m), 1)


def flag(name, value):
    """Return 'critical'|'high'|'low'|'normal'|None (None = no policy entry, never guessed)."""
    if value is None:
        return None
    policy = RANGES.get(name)
    if not policy:
        return None
    if 'critical_low' in policy and value <= policy['critical_low']:
        return 'critical'
    if 'critical_high' in policy and value >= policy['critical_high']:
        return 'critical'
    if 'low' in policy and value < policy['low']:
        return 'low'
    if 'high' in policy and value > policy['high']:
        return 'high'
    return 'normal'


def assess(vitals) -> dict:
    """vitals: a VitalSigns-shaped object/dict. Returns per-field flags + computed BMI, all
    traceable to RANGES so the UI can show why something is flagged."""
    values = vitals if isinstance(vitals, dict) else vitals.model_dump()
    fields = ['sbp', 'dbp', 'heart_rate', 'respiratory_rate', 'temperature_c', 'spo2']
    flags = {}
    for name in fields:
        value = values.get(name)
        f = flag(name, value)
        if f is not None:
            flags[name] = {'value': value, 'status': f, 'policy': RANGES.get(name), 'policy_source': POLICY_SOURCE}
    return {'flags': flags, 'bmi': bmi(values.get('height_cm'), values.get('weight_kg'))}
