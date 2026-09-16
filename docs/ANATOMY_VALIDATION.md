# 검증 결과 — 2026-09-14

## 자동 검증

| 검증 | 결과 |
|---|---|
| npm install (추가 dependency 설치) | 성공. React/React DOM 19.2.4로 peer 호환 고정 후 완료 |
| npm ci --ignore-scripts (lockfile 재설치) | 성공 |
| npm run build | 성공, 완성 frontend/dist 포함 |
| 기존 frontend 테스트 | 3/3 통과 |
| 추가 frontend 통합 테스트 | 2/2 통과 |
| 기존 FastAPI 테스트 | 17/17 통과 |
| 추가 anatomy 테스트 | 5/5 통과 |

프런트엔드 통합 테스트는 실제 FastAPI 브리지를 통해 ONNX, 분석, 시뮬레이션, 검토 기록을 사용합니다. jsdom의 WebGL 부분만 대체하고, 별도 Chromium에서 실제 WebGL 화면을 검증했습니다.

추가 백엔드 검증: 동일 입력의 결정성, eGFR→신장, 출혈/알레르기→전신, 부분 문자열 오인 매칭 방지, 복수 장기 연결, 신호 없는 환자, anatomy API·분석 결과 일치, unknown patient 404, 시뮬레이션 전후 구분 및 원처방 보존.

## 실제 Chromium / WebGL

1600×1100 데스크톱 및 390×844 모바일 뷰포트에서 확인했습니다.

1. 3D 탭 진입 및 실제 WebGL 렌더링
2. 신장 선택·근거(eGFR)·카메라 이동
3. 3D 메시 직접 클릭 시 선택 장기가 간으로 변경됨
4. 3D → 기존 경고 모달
5. 경고 → 3D 선택 장기
6. FRONT/BACK/RESET 카메라 변경
7. clipping 전후 렌더 이미지 차이 확인
8. 단면 슬라이더 변경 시 같은 모델의 SVG 교차 단면 갱신
9. Axial/Coronal/Sagittal 전환
10. 장기 숨기기/표시
11. 환자 변경 후 3D 탭 유지, 무신호 환자에서 0개 연결 확인
12. 모바일 가로 넘침 없음, 장기 선택
13. 일반 동작 중 browser console error 및 pageerror 0건
14. WebGL context loss 시 대체 메시지 표시, 근거 패널 유지
15. 존재하지 않는 GLB URL을 설정한 개발 화면에서 기본 모델로 대체되고 경고 열기 정상 동작

스크린샷과 결과는 `docs/anatomy-validation/`에 있습니다. 자동 브라우저 검증은 소프트웨어 WebGL을 사용했습니다. 실제 모바일 기기의 터치 제스처 성능 또는 GPU별 FPS 수치를 실측한 것은 아닙니다. 카메라와 모바일 조작은 OrbitControls에 기반합니다. 정밀 GLB 실물은 제공되지 않아, 누락 asset fallback을 검증했으며 특정 외부 GLB의 품질을 검증하지 않았습니다.

## 남아 있는 비차단 경고

- Vite: 500kB 이상인 JS chunk 경고. 3D 모듈은 lazy-load하며 초기 요약 화면 진입에서 별도로 로드되지 않습니다.
- Vitest/jsdom: Three.js 복수 import 경고가 1회 표시됩니다. 실제 Chromium 일반 동작에서는 console error 0건입니다.
- FastAPI 테스트: 기존 Starlette/httpx 및 AnyIO 호환 deprecation 경고 2건.
- 의도적으로 GLB 누락을 시험할 때 로딩 실패 로그는 예상되는 결과입니다. 앱은 기본 모델로 복구됩니다.

## 재실행

프로젝트 루트에서 개발용 Python 패키지를 설치한 다음 실행하십시오.

```bash
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -q
cd frontend
npm ci
npm test
npm run build
```

테스트 브리지는 루트 `.venv`를 기본 사용합니다. 다른 Python 환경이면 `SYNEX_TEST_PYTHON`을 해당 Python 실행파일의 절대 경로로 지정하십시오.
