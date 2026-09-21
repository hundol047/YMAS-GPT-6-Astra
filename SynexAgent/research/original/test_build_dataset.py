"""
test_build_dataset.py
------------------------
build_dataset_v2.py/v3.py의 핵심 로직(약물명 매칭, 알레르기 중증도 점수)은
실제로 라벨/특성 값에 직접 영향을 주는 부분이라 잘못되면 조용히 데이터가
틀어집니다. pytest 없이 바로 돌아가는 최소한의 검증 테스트입니다.

사용법: python3 test_build_dataset.py   (전부 통과하면 "OK" 출력, 실패하면
예외로 즉시 중단)
"""

from build_dataset_v2 import match_drug, _SEVERITY_SCORE, CATALOG, ALIAS_TO_ID


def test_match_drug_real_synthea_descriptions():
    cases = {
        "Clopidogrel 75 MG Oral Tablet": "clopidogrel",
        "Simvastatin 20 MG Oral Tablet": "simvastatin",
        "Amoxicillin 250 MG / Clavulanate 125 MG Oral Tablet": "amoxicillin",
        "Warfarin Sodium 5 MG Oral Tablet": "warfarin",
        "Acetaminophen 325 MG Oral Tablet": "acetaminophen",
        "NDA020800 200 ACTUAT Albuterol 0.09 MG/ACTUAT Metered Dose Inhaler": "albuterol",
        "24 HR Metformin hydrochloride 500 MG Extended Release Oral Tablet": "metformin",
        "Lisinopril 10 MG Oral Tablet": "lisinopril",
    }
    for desc, expected in cases.items():
        got = match_drug(desc)
        assert got == expected, f"{desc!r} -> {got!r} (expected {expected!r})"


def test_match_drug_no_false_positive_on_unrelated_text():
    # 카탈로그에 없는 항목은 None이어야 함 (우연히 다른 약물로 오매칭되면 안 됨)
    for desc in ["Influenza Vaccine", "3 ML Talimogene Injection", "Tetanus and Diphtheria Toxoid"]:
        assert match_drug(desc) is None, f"{desc!r} matched unexpectedly: {match_drug(desc)}"


def test_catalog_ids_unique_and_nonempty():
    ids = [d["id"] for d in CATALOG]
    assert len(ids) == len(set(ids)), "drug_catalog.json에 중복 id가 있습니다"
    assert len(ids) > 0


def test_alias_lookup_covers_every_catalog_drug():
    # 모든 카탈로그 약물이 최소 자기 자신의 id로는 매칭되어야 함
    catalog_ids = {d["id"] for d in CATALOG}
    aliased_ids = set(ALIAS_TO_ID.values())
    missing = catalog_ids - aliased_ids
    assert not missing, f"별칭이 전혀 없어 절대 매칭 안 되는 약물: {missing}"


def test_severity_score_monotonic():
    assert _SEVERITY_SCORE["MILD"] < _SEVERITY_SCORE["MODERATE"] < _SEVERITY_SCORE["SEVERE"]
    assert _SEVERITY_SCORE["SEVERE"] == 1.0


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"OK  {t.__name__}")
    print(f"\n전체 {len(tests)}개 테스트 통과")
