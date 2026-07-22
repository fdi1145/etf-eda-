# GitHub Actions 기반 실시간 ETF 데이터 자동 수집 파이프라인 구현 계획

GitHub Actions 워크플로우를 생성하여 정기적으로 네이버 금융 ETF 데이터를 수집하고, 수집된 CSV 파일을 원격 저장소의 `data/` 폴더에 커밋 및 푸시하여 이력이 자동으로 기록되도록 구성합니다.

## User Review Required

> [!IMPORTANT]
> **GitHub Actions의 주기 제한 (매 1분 주기 제약)**
> GitHub Actions의 `on.schedule` (cron) 기능은 플랫폼 정책상 **최소 실행 주기가 5분**으로 제한되어 있습니다. `* * * * *` (1분 주기)로 작성하더라도 GitHub 스케줄러가 이를 강제로 5분~15분 주기로 조절하여 실행합니다. 
> 
> 또한, 매 1분마다 원격 저장소에 커밋과 푸시를 반복하면 저장소 용량 초과와 잦은 푸시 충돌(Push Conflict)이 유발될 수 있습니다. 
> 따라서 본 계획에서는 **매 5분 주기(`*/5 * * * *`) 스케줄**로 자동 실행되도록 워크플로우를 생성하되, 필요 시 사용자가 즉시 수동으로 실행(`workflow_dispatch`)할 수 있는 버튼을 추가하는 방안을 제안합니다.

> [!NOTE]
> **1회성 수집용 스크립트 필요**
> 기존 `src/etf_scheduler.py`는 `while True` 무한 루프 구조로 짜여있어 GitHub Actions에서 실행 시 종료되지 않고 타임아웃 에러를 발생시킵니다. 따라서 1회만 단독 실행되어 데이터를 수집/저장하고 정상 종료되는 `src/etf_collector.py`를 신규 작성합니다.

## Proposed Changes

---

### [NEW] 자동 수집 리소스

#### [NEW] [src/etf_collector.py](file:///c:/Users/student/Documents/etf-eda/src/etf_collector.py)
- 네이버 금융 ETF API에 요청을 보내 1회 시세 데이터를 받아옵니다.
- 데이터를 정제한 후 `data/etf_data_YYYYMMDD_HHMMSS.csv` 형태로 저장하고 종료됩니다.
- 구글 파이썬 스타일 가이드(타입 히트, 상세 Docstring)를 엄격히 준수하여 신규 작성합니다.

#### [NEW] [.github/workflows/data-collector.yml](file:///c:/Users/student/Documents/etf-eda/.github/workflows/data-collector.yml)
- GitHub Actions 워크플로우 정의 파일입니다.
- 매 5분 주기 스케줄링(`*/5 * * * *`) 및 수동 트리거(`workflow_dispatch`)를 활성화합니다.
- 가상환경(Python 3.11) 구축 및 `src/etf_collector.py`를 구동합니다.
- 새로 수집되어 생성된 CSV 파일을 감지하여 Git에 추가(`git add data/`)하고, 사용자 `fdi1145` (이메일: `fdi1145@naver.com`) 명의로 커밋하여 푸시합니다.
- 토큰 권한 오류 방지를 위해 `permissions: contents: write` 설정을 추가합니다.

---

### [MODIFY] 보고 문서

#### [MODIFY] [docs/walkthrough.md](file:///c:/Users/student/Documents/etf-eda/docs/walkthrough.md)
- GitHub Actions 자동 데이터 수집 결과 및 워크플로우 적용 사항을 추가 기술합니다.

## Verification Plan

### 수동 및 Actions 검증
1. **로컬 실행 테스트**: 로컬 환경에서 `python src/etf_collector.py`를 구동해 `data/` 밑에 새로운 CSV 파일이 오류 없이 정상 생성되는지 검증합니다.
2. **GitHub Actions 수동 트리거**: 코드를 푸시한 후 GitHub 저장소의 Actions 탭으로 이동하여 `ETF Data Auto Collector` 워크플로우를 수동 실행(`Run workflow`)해 봅니다.
3. **자동 커밋 & 푸시 확인**: Actions 작업이 성공적으로 끝난 뒤, 실제로 `data/` 디렉토리에 타임스탬프가 적용된 CSV 파일이 커밋되어 푸시되었는지 커밋 히스토리를 대조합니다.
