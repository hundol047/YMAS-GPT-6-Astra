"""
build_dataset_v2.py
---------------------
YMAS 저장소 backend/build_real_dataset.py를 확장해서, Synthea CSV에
이미 들어있지만 그동안 안 쓰고 있던 컬럼들로 특성을 3개 더 뽑습니다.

기존 5개 특성(drug_conflict, comorbidity_load, age_risk, allergy_flag,
adverse_history)에 더해:

  - adverse_history (재계산): 기존에는 allergies.csv DESCRIPTION에
    "intoleran" 문자열이 있는지만 봤는데, 이 데이터셋 전체에서 단
    한 번도 True가 안 나오는 상수 버그였습니다(자세한 경위는 이
    저장소 README.md 참고). 이번엔 allergies.csv의 CATEGORY=="medication"
    (약물 알레르기/불내성)인 행들 중 SEVERITY1/SEVERITY2(MILD/MODERATE/
    SEVERE, 실제로 채워져 있는 값) 최댓값을 0~1로 정규화해서 씁니다.
  - polypharmacy_load (신규): 매칭된 약물 개수(n_drugs)를 정규화한 것.
    상호작용 규칙에 안 걸려도 "약을 많이 먹는다" 자체가 임상적으로
    잘 알려진 독립적 위험요인입니다.
  - therapy_duration_load (신규): medications.csv의 DISPENSES(처방
    조제/리필 횟수)를 매칭된 약물 평균으로 정규화한 것 -- 장기 복용
    중인 약이 많을수록 축적성 부작용(예: 디곡신 독성) 위험이 큽니다.

사용법: python3 build_dataset_v2.py --csv-dir <synthea csv 폴더>
"""

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import date

with open("drug_catalog.json", encoding="utf-8") as f:
    CATALOG = json.load(f)
with open("rules.json", encoding="utf-8") as f:
    RULES = json.load(f)

ID_TO_GROUP = {d["id"]: d["group_ko"] for d in CATALOG}

# 카탈로그에 openfda_search_term이 같은 항목이 둘 이상 있으면(예:
# ondansetron / ondansetron_peds 둘 다 "ONDANSETRON"), Synthea 처방
# DESCRIPTION만으로는 어느 쪽인지 구분할 수 없습니다. 원래는 CATALOG
# 배열 순서상 먼저 나온 쪽이 무조건 그 별칭을 차지해버려서(뒤에 나온
# 쪽은 자기 이름으로도 절대 매칭될 수 없는 죽은 항목이 됨 --
# test_build_dataset.py가 실제로 이 문제를 잡아냈습니다), "_peds"가
# 안 붙은(성인/일반) 항목을 우선하도록 정렬해서 처리합니다.
ALIAS_TO_ID = {}
for d in sorted(CATALOG, key=lambda d: d["id"].endswith("_peds")):
    tokens = {d["id"]}
    for part in re.split(r"[;,]| AND ", d["openfda_search_term"]):
        part = part.strip()
        if len(part) >= 4:
            tokens.add(part)
    for t in tokens:
        ALIAS_TO_ID.setdefault(t.upper(), d["id"])

_ALIASES_SORTED = sorted(ALIAS_TO_ID.keys(), key=len, reverse=True)
_COMBINED_RE = re.compile(r"\b(" + "|".join(re.escape(a) for a in _ALIASES_SORTED) + r")\b")


def match_drug(description):
    m = _COMBINED_RE.search(description.upper())
    return ALIAS_TO_ID[m.group(1)] if m else None


_SEVERITY_SCORE = {"MILD": 0.34, "MODERATE": 0.67, "SEVERE": 1.0}


def load_patient_data(csv_dir):
    meds = defaultdict(set)
    med_dispenses = defaultdict(list)  # patient -> [dispenses per matched drug]
    with open(f"{csv_dir}/medications.csv") as f:
        for row in csv.DictReader(f):
            drug_id = match_drug(row["DESCRIPTION"])
            if drug_id:
                meds[row["PATIENT"]].add(drug_id)
                try:
                    med_dispenses[row["PATIENT"]].append(float(row["DISPENSES"] or 0))
                except ValueError:
                    pass

    conditions = defaultdict(set)
    with open(f"{csv_dir}/conditions.csv") as f:
        for row in csv.DictReader(f):
            d = row["DESCRIPTION"]
            if "(finding)" in d or "(situation)" in d or "(morphologic abnormality)" in d:
                continue
            conditions[row["PATIENT"]].add(d.replace(" (disorder)", ""))

    allergies = defaultdict(set)
    med_allergy_severity = defaultdict(float)  # patient -> max severity score (medication category only)
    with open(f"{csv_dir}/allergies.csv") as f:
        for row in csv.DictReader(f):
            allergies[row["PATIENT"]].add(row["DESCRIPTION"])
            if row.get("CATEGORY") == "medication":
                for sev_key in ("SEVERITY1", "SEVERITY2"):
                    sev = _SEVERITY_SCORE.get(row.get(sev_key, ""), 0.0)
                    if sev > med_allergy_severity[row["PATIENT"]]:
                        med_allergy_severity[row["PATIENT"]] = sev

    patients = {}
    with open(f"{csv_dir}/patients.csv") as f:
        for row in csv.DictReader(f):
            patients[row["Id"]] = row

    return patients, meds, conditions, allergies, med_dispenses, med_allergy_severity


_INTERACTION_BY_PAIR = {}
for r in RULES["interactions"]:
    _INTERACTION_BY_PAIR[frozenset((r["a"], r["b"]))] = r["severity"]
_COMORBID_BY_DRUG = defaultdict(list)
for c in RULES["comorbid"]:
    _COMORBID_BY_DRUG[c["drug"]].append(c["condition"])


def audit(drug_ids, conditions, allergies):
    alerts = []
    ids = list(drug_ids)
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            sev = _INTERACTION_BY_PAIR.get(frozenset((a, b)))
            if sev:
                alerts.append(sev)
            if ID_TO_GROUP.get(a) and ID_TO_GROUP.get(a) == ID_TO_GROUP.get(b):
                alerts.append("주의")
    for d in ids:
        for cond in _COMORBID_BY_DRUG.get(d, []):
            if cond in conditions:
                alerts.append("주의")
    for d in ids:
        allergy_class = RULES["allergy"].get(d)
        if allergy_class and any(allergy_class in a for a in allergies):
            alerts.append("위험")
    return alerts


def age_of(birthdate, today):
    y, m, d = map(int, birthdate.split("-")[:3])
    a = today.year - y
    if (today.month, today.day) < (m, d):
        a -= 1
    return max(a, 0)


def build(csv_dir, today=date(2026, 9, 2)):
    patients, meds, conditions, allergies, med_dispenses, med_allergy_severity = load_patient_data(csv_dir)
    rows = []
    for pid, drug_ids in meds.items():
        if len(drug_ids) == 0:
            continue
        p = patients.get(pid)
        if not p:
            continue
        alerts = audit(drug_ids, conditions.get(pid, set()), allergies.get(pid, set()))
        danger_count = alerts.count("위험")
        caution_count = alerts.count("주의")

        drug_conflict = min(1.0, danger_count * 0.5 + caution_count * 0.2)
        comorbidity_load = min(1.0, len(conditions.get(pid, [])) / 5)
        age_risk = min(1.0, age_of(p["BIRTHDATE"], today) / 100)
        allergy_flag = 1.0 if allergies.get(pid) else 0.0
        adverse_history = round(med_allergy_severity.get(pid, 0.0), 3)

        n_drugs = len(drug_ids)
        polypharmacy_load = min(1.0, n_drugs / 10)
        dispenses = med_dispenses.get(pid, [])
        avg_dispenses = sum(dispenses) / len(dispenses) if dispenses else 0.0
        # DISPENSES 분포는 중앙값 1, 90th pct 12 정도로 매우 치우쳐 있음(대부분
        # 단기 처방, 소수만 장기 복용) -- 24(약 2년치 월간 리필)를 상한으로 정규화
        therapy_duration_load = round(min(1.0, avg_dispenses / 24), 3)

        label = 1 if danger_count > 0 else 0

        rows.append({
            "patient_id": pid,
            "drug_conflict": round(drug_conflict, 3),
            "comorbidity_load": round(comorbidity_load, 3),
            "age_risk": round(age_risk, 3),
            "allergy_flag": allergy_flag,
            "adverse_history": adverse_history,
            "polypharmacy_load": round(polypharmacy_load, 3),
            "therapy_duration_load": therapy_duration_load,
            "label": label,
            "n_drugs": n_drugs,
            "matched_drugs": sorted(drug_ids),
        })
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-dir", required=True, help="Synthea csv 폴더 경로 (patients/medications/conditions/allergies.csv)")
    parser.add_argument("--out", default="data/risk_training_data_v2.json")
    args = parser.parse_args()

    rows = build(args.csv_dir)
    n_pos = sum(r["label"] for r in rows)
    n_adv = sum(1 for r in rows if r["adverse_history"] > 0)
    print(f"총 {len(rows)}명 (약물 매칭 1개 이상), 고위험 라벨 {n_pos}명 ({n_pos/len(rows)*100:.1f}%)")
    print(f"adverse_history > 0 인 환자: {n_adv}명 ({n_adv/len(rows)*100:.2f}%) -- v7/v7deep은 이게 항상 0명이었음")
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"저장: {args.out}")
