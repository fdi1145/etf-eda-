# 정적 페이지 기반 실시간 ETF EDA 대시보드 구현 계획

프로젝트 루트에 `index.html`을 배치하고, `src/app.js`와 `src/style.css`를 구축하여 별도의 서버나 빌드 환경 없이 브라우저에서 직접 실시간 데이터를 호출해 시각화하는 대시보드를 생성합니다. 완성된 코드는 GitHub Pages를 통해 즉시 웹상에 배포하여 누구나 브라우저로 분석할 수 있도록 구성합니다.

## User Review Required

> [!IMPORTANT]
> **API 호출 방식 (CORS 우회)**
> 네이버 금융 API는 브라우저 보안 정책(CORS)으로 인해 일반적인 `fetch` API 호출 시 요청이 차단됩니다. 이를 우회하기 위해 API가 제공하는 **JSONP(JSON with Padding)** 호출 포맷을 활용하여 `<script>` 태그를 동적으로 삽입하고 데이터를 전역 콜백으로 수신하는 방식을 채택합니다.
>
> **차트 성능 및 라이브러리**
> Plotly.js CDN을 연동하여 Streamlit에서 보여준 것과 동일한 수준의 고기능 인터랙티브 차트(툴팁, 줌, 필터링 등)를 구현합니다.

## Proposed Changes

정적 대시보드를 구동하기 위해 신규 파일을 생성하고, 기존 프로젝트 구조와 조화롭게 배치합니다.

---

### [NEW] 정적 대시보드 리소스

#### [NEW] [index.html](file:///c:/Users/student/Documents/etf-eda/index.html)
- 대시보드의 뼈대가 되는 HTML5 파일입니다.
- Google Fonts(Inter/Outfit) 및 Tailwind CSS(혹은 Vanilla CSS용 기본 레이아웃 구성), Plotly.js CDN 링크를 포함합니다.
- 사이드바 필터 영역, KPI 요약 영역, 인터랙티브 차트 영역, 데이터 테이블 영역을 구조화합니다.

#### [NEW] [src/style.css](file:///c:/Users/student/Documents/etf-eda/src/style.css)
- 고급스러운 Glassmorphism 및 다크 테마 디자인 시스템을 구축합니다.
- 투명 보더, 백드롭 블러(`backdrop-filter: blur()`), 세련된 그라데이션 카드를 정의합니다.

#### [NEW] [src/app.js](file:///c:/Users/student/Documents/etf-eda/src/app.js)
- JSONP를 이용한 실시간 네이버 ETF 데이터 수집 엔진을 탑재합니다.
- 데이터 전처리 로직 (API 오타 `amonut` 처리, 운용사 및 테마 분류)을 구현합니다.
- 사용자의 필터링 조건(검색어, 운용사, 테마, 시가총액 범위) 변화를 감지하여 차트 및 테이블을 동적으로 갱신합니다.
- Plotly.js를 사용하여 다음 4가지 인터랙티브 차트를 렌더링합니다:
  1. **운용사별 시가총액 점유율 트리맵**
  2. **ETF 등락률 분포 히스토그램**
  3. **시가총액 상위 10개 ETF 바 차트**
  4. **당일 거래대금 상위 10개 ETF 바 차트**
- 데이터 테이블(검색 및 정렬 기능 포함)을 구축합니다.

---

### [NEW] 배포 및 가이드 문서

#### [NEW] [docs/GITHUB_PAGES.md](file:///c:/Users/student/Documents/etf-eda/docs/GITHUB_PAGES.md)
- 완성된 정적 페이지를 GitHub Pages로 배포하고 확인하는 단계별 가이드를 수록합니다.

## Verification Plan

### 수동 검증 및 동작 테스트
1. **로컬 브라우저 구동 테스트**: `index.html` 파일을 브라우저로 직접 열어 데이터가 정상적으로 수집되고 차트가 렌더링되는지 확인합니다.
2. **필터링 연동 검증**: 검색어 입력, 운용사 선택, 테마 선택, 시가총액 슬라이더 조작 시 실시간으로 데이터 테이블과 Plotly 차트들이 즉시 리렌더링되는지 확인합니다.
3. **CORS 에러 발생 여부**: 브라우저 콘솔을 열어 네트워크 에러나 CORS 관련 경고가 없는지 점검합니다.
