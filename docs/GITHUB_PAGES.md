# 🚀 GitHub Pages를 활용한 실시간 ETF EDA 대시보드 배포 가이드

본 프로젝트는 서버 측 연동이 필요 없는 **순수 정적 페이지(Static Web Page)** 구조로 설계되었습니다. 따라서 GitHub Pages를 사용하면 별도의 서버 호스팅 비용 없이 무료로 웹에 대시보드를 즉시 배포할 수 있습니다.

---

## 🛠️ GitHub Pages 배포 단계

### 1. 변경 사항 푸시 (GitHub 저장소 반영)
현재 작성된 `index.html`, `src/app.js`, `src/style.css` 코드가 원격 GitHub 저장소에 푸시되어 있어야 합니다. (아래 명령어로 푸시합니다.)
```bash
git add index.html src/style.css src/app.js docs/GITHUB_PAGES.md
git commit -m "Add static ETF dashboard for GitHub Pages deployment"
git push origin main
```

### 2. GitHub 저장소 설정 변경
1. 본인의 **GitHub 저장소(Repository)** 페이지로 이동합니다. (`https://github.com/fdi1145/etf-eda-`)
2. 상단 탭에서 **Settings** (설정) 아이콘을 클릭합니다.
3. 좌측 사이드바 메뉴의 **Code and automation** 섹션 하위에 있는 **Pages** 메뉴를 선택합니다.
4. **Build and deployment** 섹션의 설정 값을 다음과 같이 지정합니다:
   - **Source**: `Deploy from a branch` 선택 (기본값)
   - **Branch**: `main` 브랜치 선택 후, 그 옆의 폴더 드롭다운을 `/ (root)`로 지정합니다.
     *(이미 `index.html`이 프로젝트의 루트 경로에 있으므로 root 폴더를 설정하면 됩니다.)*
5. 우측의 **Save** 버튼을 클릭하여 설정을 저장합니다.

### 3. 배포 확인 및 접속
1. 저장을 마치면 GitHub Actions가 작동하여 자동으로 배포 파이프라인을 빌드합니다. (약 1~2분 소요)
2. **Settings -> Pages** 페이지 상단에 배포 상태 메시지와 함께 웹사이트 URL이 표시됩니다.
   - 예시 URL 형태: `https://fdi1145.github.io/etf-eda-/`
3. 해당 URL로 접속하여 실시간 ETF EDA 대시보드가 정상 구동되는지 확인합니다.

---

## 💡 정적 페이지 아키텍처의 장점

1. **CORS 우회 실시간 통신 (JSONP)**
   - 일반 브라우저에서 `https://finance.naver.com` API를 `fetch`나 `axios`로 직접 호출하면 CORS 정책에 의해 차단됩니다.
   - 본 대시보드는 네이버 금융 API의 **JSONP 콜백 지원 규격**을 활용하여, 동적으로 `<script>` 태그를 삽입하고 콜백 함수(`window.__jindo2_callback._7957`)로 결과 데이터를 받아오는 방식을 도입함으로써 완벽한 CORS 우회를 실현했습니다.

2. **서버리스(Serverless) 무료 호스팅**
   - 별도의 Python 실행 환경(Streamlit Cloud, Heroku 등)이나 Node.js 서버가 필요하지 않아 GitHub Pages를 통해 반영구적으로 안정적인 무료 대시보드 호스팅이 가능합니다.

3. **Plotly.js를 활용한 풍부한 인터랙티브 기능**
   - Streamlit의 Plotly 차트와 동일하게 드래그 앤 드롭 줌, 툴팁 표시, 다운로드 기능 등이 브라우저 내에서 100% 동작합니다.
