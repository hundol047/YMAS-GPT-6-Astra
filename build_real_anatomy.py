"""
실제 해부학 데이터(BodyParts3D / DBCLS, CC BY-SA 2.1 Japan)로
SynexAgent의 anatomy.glb를 만드는 파이프라인.

3단계로 나뉘어 있고, 각 단계는 따로 실행 가능합니다.

    python build_real_anatomy.py --list      # 1) 어떤 메시가 잡히는지 먼저 검증 (다운로드 없음)
    python build_real_anatomy.py --fetch     # 2) 실제 OBJ 다운로드
    python build_real_anatomy.py --build     # 3) OBJ들을 합쳐서 anatomy.glb 생성
    python build_real_anatomy.py --all       # 1~3 전부

필요 패키지: pip install trimesh
필요 프로그램: git (bp3d_subset.py 저장소 클론용)

라이선스 주의:
  BodyParts3D 메시는 CC BY-SA 2.1 Japan입니다. anatomy.glb를 쓰는 화면에
  "BodyParts3D, (c) Database Center for Life Science, CC BY-SA 2.1 Japan"
  형태의 표기(스크린샷 좌상단 캡션 같은 것)를 반드시 넣어야 합니다.
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_DIR = HERE / "bp3d_repo"
RAW_DIR = REPO_DIR / "subset"
# Upstream (olivercase/body_parts_3d_api) ships the actual mesh geometry via Git LFS, and this
# session's git-lfs credential injection is scoped per-owner: it works for a fork under the same
# account as this session's already-attached repo, not for the upstream repo directly. So this
# points at a fork (hundol047/body_parts_3d_api) that was `git lfs pull`-ed once, out-of-band, into
# /home/user/body_parts_3d_api -- REPO_DIR above is a symlink to that clone, not a fresh clone target.
REPO_URL = "https://github.com/hundol047/body_parts_3d_api.git"

# organ.id (frontend/src/data/anatomyMap.js 와 반드시 일치) -> 어떤 메시를 모을지
# group: bp3d_subset.py 내장 그룹 이름 / pattern: FMA 이름에 대한 정규식(직접 지정)
# 먼저 --list로 실제 몇 개 매칭되는지, 이름이 뭔지 눈으로 확인하고 필요하면 pattern을 조정하세요.
# 아래 lung 패턴은 실제 MANIFEST.csv를 직접 --list로 확인해서 만든 것입니다.
# 이 데이터셋은 폐를 "좌/우" 단어로 안 부르는 조각이 폐당 2개씩 섞여 있음
# (우측: lateral/medial bronchopulmonary segment = 우중엽 조각, 좌측 단어 없음 /
#  좌측: superior/inferior lingular segment, apicoposterior segment = 좌상엽 조각,
#  "left" 단어 없음). 그래서 단순 "left"/"right" 정규식으로는 폐당 2조각씩 빠집니다.
# 아래는 18개 조각(우 9 + 좌 9)을 정확한 이름으로 지정한 것입니다.
_RIGHT_LUNG_SEGMENTS = [
    "parenchyma of right apical bronchopulmonary segment",
    "parenchyma of right posterior basal bronchopulmonary segment",
    "parenchyma of right posterior bronchopulmonary segment",
    "parenchyma of right anterior bronchopulmonary segment",
    "parenchyma of lateral bronchopulmonary segment",   # 우중엽 조각 (이름에 left/right 없음)
    "parenchyma of medial bronchopulmonary segment",    # 우중엽 조각 (이름에 left/right 없음)
    "parenchyma of right superior bronchopulmonary segment",
    "parenchyma of right anterior basal bronchopulmonary segment",
    "parenchyma of right lateral basal bronchopulmonary segment",
]
_LEFT_LUNG_SEGMENTS = [
    "parenchyma of apicoposterior bronchopulmonary segment",  # 좌상엽 조각 (이름에 left 없음, 2개 존재)
    "parenchyma of left posterior basal bronchopulmonary segment",
    "parenchyma of left anterior bronchopulmonary segment",
    "parenchyma of superior lingular bronchopulmonary segment",  # 좌상엽 조각 (이름에 left 없음)
    "parenchyma of inferior lingular bronchopulmonary segment",  # 좌상엽 조각 (이름에 left 없음)
    "parenchyma of left superior bronchopulmonary segment",
    "parenchyma of left anterior basal bronchopulmonary segment",
    "parenchyma of left lateral basal bronchopulmonary segment",
]
import re as _re


def _exact_name_pattern(names):
    return "(?i)^(?:" + "|".join(_re.escape(n) for n in names) + ")$"


TARGETS = {
    "brain":       {"kind": "group",   "value": "brain"},
    "rightLung":   {"kind": "pattern", "value": _exact_name_pattern(_RIGHT_LUNG_SEGMENTS)},
    "leftLung":    {"kind": "pattern", "value": _exact_name_pattern(_LEFT_LUNG_SEGMENTS)},
    "heart":       {"kind": "group",   "value": "heart"},
    # 주의: 이 데이터셋(BodyParts3D 4.3)에는 간을 통째로 나타내는 단일 메시가 없습니다.
    # FMA 이름에 "Caudate lobe of liver" 조각 1개만 존재합니다(우엽/좌엽/방형엽 메시 없음).
    # 그래서 이 패턴으로는 간의 일부(미상엽)만 잡힙니다 — 완전한 간 모양이 필요하면
    # Z-Anatomy(Z-Anatomy.com, 같은 CC BY-SA 계열, BodyParts3D를 정리·보완한 프로젝트)에서
    # liver 메시를 따로 구해서 이 자리에 넣는 걸 권장합니다.
    "liver":       {"kind": "pattern", "value": r"(?i).*liver"},
    "stomach":     {"kind": "pattern", "value": r"(?i)^stomach$"},
    "rightKidney": {"kind": "pattern", "value": r"(?i)^right kidney$"},
    "leftKidney":  {"kind": "pattern", "value": r"(?i)^left kidney$"},
    "vascular":    {"kind": "group",   "value": "blood_vessel"},
    "spine":       {"kind": "group",   "value": "spine"},
}

# --- 전신 골격 / 전신 혈관 (organ 10종과는 별도 파이프라인) -------------------
# 이 두 개는 개별 organ처럼 "각각 정규화해서 특정 위치에 배치"하는 게 아니라,
# BodyParts3D가 원래 공유하는 한 좌표계 안에서 서로 상대 위치를 유지한 채
# 하나의 큰 메시로 합쳐집니다. 화면에 맞는 전체 배율/위치는 frontend에서
# 한 번만 조정합니다 (anatomyMap.js의 extrasTransform).
EXTRAS = {
    "skeletonFull": {
        "kind": "pattern",
        "value": (
            r"(?i).*(vertebra|sacrum|coccyx|\brib\b|sternum|skull|cranium|"
            r"frontal bone|parietal bone|temporal bone|occipital bone|sphenoid|"
            r"zygomatic|nasal bone|mandible|maxilla|hip bone|ilium|ischium|pubis|"
            r"scapula|clavicle|humerus|radius|ulna|carpal|metacarpal|"
            r"phalan(x|ges)|femur|patella|tibia|fibula|tarsal|metatarsal)"
        ),
    },
    "vascularFull": {
        "kind": "pattern",
        "value": r"(?i).*(artery|vein|aorta|vena cava|trunk of|capillary|arteriole|venule)",
    },
    # Real whole-body skin surface (single mesh, FMA55665 "Skin") -- replaces the procedural
    # sphere-head/capsule-limb body shell with an actual BodyParts3D scan silhouette. Anchored
    # regex so it matches only the exact "Skin" entry, not "Skin of umbilicus" etc.
    "skinBody": {
        "kind": "pattern",
        "value": r"(?i)^skin$",
    },
}
# 실측: skeletonFull 365개 메시, vascularFull 1466개 메시, skinBody 1개 메시(전신 피부,
# 약 203k faces). vascularFull은 아주 작은 분절 혈관까지 전부 포함되어 있어서(모세혈관
# 수준은 아니지만) 파일이 커지고 브라우저에서 무거울 수 있습니다. 느리면 이 정규식에서
# "capillary|arteriole|venule" 같은 항목을 지워서 범위를 줄이세요.


def run(cmd, cwd=None):
    print(">", " ".join(cmd))
    subprocess.check_call(cmd, cwd=cwd)


def ensure_repo():
    if not REPO_DIR.exists():
        run(["git", "clone", "--depth", "1", REPO_URL, str(REPO_DIR)])
    else:
        print(f"이미 클론됨: {REPO_DIR}")


def subset_cmd(name, spec, extra):
    cmd = [sys.executable, "bp3d_subset.py"]
    if spec["kind"] == "group":
        cmd += ["--group", spec["value"]]
    else:
        cmd += ["--pattern", spec["value"], "--name", name]
    cmd += ["--out", str(RAW_DIR)]
    cmd += extra
    return cmd


def step_list():
    ensure_repo()
    print("\n=== 매칭되는 메시 미리보기 (다운로드 없음) ===")
    for name, spec in TARGETS.items():
        print(f"\n--- {name} ---")
        cmd = subset_cmd(name, spec, ["--list"])
        run(cmd, cwd=REPO_DIR)
    print(
        "\n각 그룹 아래 실제 메시 개수/이름을 확인하세요. "
        "0개거나 엉뚱한 게 잡히면 이 스크립트의 TARGETS 딕셔너리에서 "
        "해당 organ의 pattern 정규식을 조정한 뒤 다시 --list 하세요."
    )


def step_fetch():
    ensure_repo()
    # meshes/ is already fully populated (git lfs pull was run once, out-of-band, against the
    # fork -- see REPO_URL above), so this copies the selection out of that local set instead of
    # passing --download, which would hit lifesciencedb.jp directly and is blocked by this
    # session's network egress policy (confirmed via a real CONNECT attempt, not assumed).
    print("\n=== 로컬 meshes/ 에서 subset 복사 (git lfs pull 완료된 세트 사용) ===")
    for name, spec in TARGETS.items():
        cmd = subset_cmd(name, spec, [])
        run(cmd, cwd=REPO_DIR)
    print(f"\n복사 완료: {RAW_DIR}")


def step_extras_list():
    ensure_repo()
    print("\n=== 전신 골격/혈관 매칭 미리보기 (다운로드 없음) ===")
    for name, spec in EXTRAS.items():
        print(f"\n--- {name} ---")
        cmd = subset_cmd(name, spec, ["--list"])
        run(cmd, cwd=REPO_DIR)


def step_extras_fetch():
    ensure_repo()
    # Same local-copy reasoning as step_fetch() above.
    print("\n=== 전신 골격/혈관 로컬 meshes/ 에서 subset 복사 ===")
    for name, spec in EXTRAS.items():
        cmd = subset_cmd(name, spec, [])
        run(cmd, cwd=REPO_DIR)
    print(f"\n복사 완료: {RAW_DIR}")


def _folder_for(name, spec):
    # group 방식이면 폴더명 = group 이름, pattern 방식이면 --name 으로 지정한 이름
    if spec["kind"] == "group":
        return RAW_DIR / spec["value"]
    return RAW_DIR / name


def step_build(out_glb):
    try:
        import trimesh
    except ImportError:
        print("trimesh가 없습니다: pip install trimesh")
        sys.exit(1)

    scene_geo = {}
    missing = []
    for name, spec in TARGETS.items():
        folder = _folder_for(name, spec)
        objs = sorted(folder.glob("*.obj")) if folder.exists() else []
        if not objs:
            missing.append(name)
            print(f"[없음] {name}: {folder} 에 .obj가 없음")
            continue
        meshes = [trimesh.load(str(p), force="mesh") for p in objs]
        merged = trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0]
        scene_geo[name] = merged
        print(f"[OK] {name}: {len(objs)}개 obj 병합, faces={len(merged.faces)}")

    if missing:
        print(f"\n다음 organ은 메시가 없어서 anatomy.glb에서 빠집니다: {missing}")
        print("주의: 현재 프론트엔드 로더(AnatomyAssets.jsx)는 10개 organ이 전부")
        print("있어야만 GLB를 사용하고, 하나라도 없으면 전체를 절차적 모델로 되돌립니다.")
        print("먼저 --list로 패턴을 고쳐서 10개를 다 채운 뒤 다시 --build 하세요.")

    scene = trimesh.Scene(geometry=scene_geo)
    out_glb.parent.mkdir(parents=True, exist_ok=True)
    scene.export(str(out_glb))
    print(f"\n생성됨: {out_glb}")
    print("frontend/.env.local 에 아래 한 줄 추가 후 npm run build:")
    print("VITE_ANATOMY_MODEL_URL=/models/anatomy/anatomy.glb")
    print("\n화면 어딘가에 반드시 표기 (CC BY-SA 2.1 Japan 요구사항):")
    print("BodyParts3D, (c) Database Center for Life Science, CC BY-SA 2.1 Japan")


def step_build_extras(out_glb):
    """골격/혈관은 organ처럼 개별 정규화하지 않고, BodyParts3D가 공유하는
    원래 좌표계 그대로 하나로 합칩니다 (그래야 뼈들의 상대 위치가 유지됩니다).
    전체적으로 화면에 맞는 배율/위치는 frontend의 extrasTransform에서 한 번만 줍니다."""
    try:
        import trimesh
    except ImportError:
        print("trimesh가 없습니다: pip install trimesh")
        sys.exit(1)

    scene_geo = {}
    for name, spec in EXTRAS.items():
        folder = _folder_for(name, spec)
        objs = sorted(folder.glob("*.obj")) if folder.exists() else []
        if not objs:
            print(f"[없음] {name}: {folder} 에 .obj가 없음 (먼저 --extras-fetch 실행)")
            continue
        meshes = [trimesh.load(str(p), force="mesh") for p in objs]
        merged = trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0]
        scene_geo[name] = merged
        print(f"[OK] {name}: {len(objs)}개 obj 병합(원본 좌표 유지), faces={len(merged.faces)}")

    if not scene_geo:
        print("합칠 메시가 없습니다.")
        return

    scene = trimesh.Scene(geometry=scene_geo)
    out_glb.parent.mkdir(parents=True, exist_ok=True)
    scene.export(str(out_glb))
    print(f"\n생성됨: {out_glb}")
    print("frontend/.env.local 에 아래 한 줄 추가 후 npm run build:")
    print("VITE_ANATOMY_EXTRAS_URL=/models/anatomy/extras.glb")
    print("처음엔 화면에 골격/혈관이 이상한 크기·위치로 나올 수 있습니다.")
    print("frontend/src/data/anatomyMap.js 의 extrasTransform 숫자를 조정해서 맞추세요.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--extras-list", action="store_true")
    ap.add_argument("--extras-fetch", action="store_true")
    ap.add_argument("--extras-build", action="store_true")
    ap.add_argument("--all", action="store_true", help="organ 10종만 (list+fetch+build)")
    ap.add_argument("--all-extras", action="store_true", help="골격+혈관까지 전부 (list+fetch+build 6단계)")
    ap.add_argument(
        "--out",
        default=str(HERE / "anatomy.glb"),
        help="organ build 결과 glb 경로 (기본: 이 스크립트 옆 anatomy.glb)",
    )
    ap.add_argument(
        "--out-extras",
        default=str(HERE / "extras.glb"),
        help="골격/혈관 build 결과 glb 경로 (기본: 이 스크립트 옆 extras.glb)",
    )
    args = ap.parse_args()

    if not any([args.list, args.fetch, args.build, args.extras_list,
                args.extras_fetch, args.extras_build, args.all, args.all_extras]):
        ap.print_help()
        return

    if args.list or args.all or args.all_extras:
        step_list()
    if args.fetch or args.all or args.all_extras:
        step_fetch()
    if args.build or args.all or args.all_extras:
        step_build(Path(args.out))
    if args.extras_list or args.all_extras:
        step_extras_list()
    if args.extras_fetch or args.all_extras:
        step_extras_fetch()
    if args.extras_build or args.all_extras:
        step_build_extras(Path(args.out_extras))


if __name__ == "__main__":
    main()
