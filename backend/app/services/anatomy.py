"""Deterministic relevance only. Never infer lesion coordinates or score attribution."""
import json
import re
from pathlib import Path

MAPPING = json.loads((Path(__file__).resolve().parents[2] / 'data/anatomy_mapping.json').read_text())
SYSTEMIC_TYPES = {'allergy', 'adverse_history', 'polypharmacy', 'duplicate_group',
                  'duplicate_ingredient', 'caution_accumulation'}

def organ_matches(text):
    def matches(word):
        # ASCII word boundaries prevent AST from matching 'last' or GI from 'digoxin'.
        pattern = r'(?<![A-Za-z0-9])' + re.escape(word) + r'(?![A-Za-z0-9])' if word.isascii() else re.escape(word)
        return re.search(pattern, text, re.I) is not None
    return [organ for organ, rule in MAPPING.items() if any(matches(w) for w in rule['keywords'])]

def build_anatomy(patient, alerts):
    targets, systemic = [], []
    for alert in alerts:
        evidence = alert.get('evidence', {})
        text = ' '.join([alert.get('title', ''), alert.get('reason', ''), json.dumps(evidence, ensure_ascii=False)])
        # Bleeding interactions are systemic even when GI bleeding is mentioned.
        general = alert['type'] in SYSTEMIC_TYPES or (alert['type'] == 'drug_interaction' and
                  (re.search(r'출혈|bleed', text, re.I) or {'warfarin', 'aspirin'} <= set(alert.get('drugs', []))))
        organs = [] if general else organ_matches(text)
        sources = [{'type':'alert', 'name':alert['title'], 'alert_id':alert['id'], 'source':alert['source']}]
        if evidence.get('lab'): sources.append({'type':'lab', **evidence['lab']})
        if evidence.get('condition'): sources.append({'type':'condition', 'name':evidence['condition']})
        sources += [{'type':'medication', 'name':d} for d in alert.get('drugs', [])]
        for organ in organs or ['systemic']:
            item = {'organ_id':organ, 'severity':alert['severity'], 'title':alert['title'],
                    'reason':alert['reason'], 'alert_id':alert['id'], 'sources':sources,
                    'localization':'systemic' if organ == 'systemic' else 'organ',
                    'confidence':'clinical_relevance'}
            (systemic if organ == 'systemic' else targets).append(item)
    # Conditions are informational context, not independently declared abnormalities.
    for condition in patient.conditions:
        for organ in organ_matches(condition):
            targets.append({'organ_id':organ, 'severity':'info', 'title':'기저질환 기록',
                'reason':condition, 'alert_id':None, 'sources':[{'type':'condition', 'name':condition}],
                'localization':'organ', 'confidence':'clinical_relevance'})
    return {'patient_id':patient.id, 'mapping_version':'1.0', 'targets':targets, 'systemic':systemic,
            'imaging_available':False, 'model_score_localized':False}
