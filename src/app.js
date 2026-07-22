/**
 * Naver Finance 실시간 ETF 데이터를 수집하고 다각도로 탐색하는 종합 EDA 대시보드 (JS Frontend)
 * 
 * 이 스크립트는 네이버 금융 API(JSONP)로부터 실시간 ETF 데이터를 수집하여,
 * 전처리 과정을 거친 뒤 Plotly.js 차트 및 데이터 테이블을 렌더링하고, 
 * 다중 필터(검색, 운용사, 테마, 시가총액 범위)를 실시간 연동 처리합니다.
 */

// ==========================================================================
// Config & Constants
// ==========================================================================
const API_URL = "https://finance.naver.com/api/sise/etfItemList.nhn?etfType=0&targetColumn=market_sum&sortOrder=desc&_callback=window.__jindo2_callback._7957";

const BRAND_TO_COMPANY = {
    'KODEX': '삼성자산운용',
    'TIGER': '미래에셋자산운용',
    'KBSTAR': 'KB자산운용',
    'RISE': 'KB자산운용',
    'ACE': '한국투자신탁운용',
    'SOL': '신한자산운용',
    'KOSEF': '키움투자자산운용',
    'HANARO': 'NH-Amundi자산운용',
    'ARIRANG': '한화자산운용',
    'PLUS': '한화자산운용',
    'WOORI': '우리자산운용',
    'WON': '우리자산운용',
    'HI': '하이자산운용',
    'UNICORN': '현대자산운용',
    'KAP': '한국자산평가',
    'MASTER': '마스턴투자운용',
    'TIMEFOLIO': '타임폴리오자산운용',
    'TRUSTON': '트러스톤자산운용',
    'MIND': '에스피자산운용',
    'FOCUS': '브레인자산운용',
    'CAPITAL': '캡스톤자산운용'
};

// Common Layout styles for Plotly charts (Dark mode / Transparent background)
const PLOTLY_THEME = {
    paper_bgcolor: 'rgba(0, 0, 0, 0)',
    plot_bgcolor: 'rgba(0, 0, 0, 0)',
    font: {
        family: "'Outfit', 'Inter', sans-serif",
        color: '#f3f4f6', // --text-primary
        size: 11
    },
    margin: { t: 40, b: 40, l: 60, r: 20 },
    colorway: ['#3b82f6', '#14b8a6', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899', '#374151']
};

// ==========================================================================
// Application State
// ==========================================================================
let appState = {
    rawData: [],
    processedData: [],
    filteredData: [],
    filters: {
        search: "",
        companies: [],
        themes: [],
        minMcap: 0,
        maxMcap: 100000 // Placeholder, will set dynamically
    },
    sort: {
        column: "시가총액(억)",
        ascending: false
    },
    limits: {
        minMcap: 0,
        maxMcap: 100000
    }
};

// ==========================================================================
// Initialization & Data Fetching (JSONP wrapper)
// ==========================================================================
document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

function initApp() {
    setupTabListeners();
    setupDropdownListeners();
    setupFilterListeners();
    fetchRealtimeETFData();
}

/**
 * 네이버 API (JSONP) 호출을 통해 실시간 데이터를 수신합니다.
 */
function fetchRealtimeETFData() {
    showLoading(true);
    
    // JSONP 글로벌 콜백 함수 정의
    window.__jindo2_callback = window.__jindo2_callback || {};
    window.__jindo2_callback._7957 = function(response) {
        if (response && response.resultCode === "success" && response.result) {
            const etfItemList = response.result.etfItemList || [];
            handleDataResponse(etfItemList);
        } else {
            alert("데이터를 가져오는 데 실패했습니다.");
            showLoading(false);
        }
    };
    
    // 동적 스크립트 노드 추가 (CORS 회피)
    const script = document.createElement("script");
    // 캐싱 방지용 쿼리 스트링 추가
    script.src = `${API_URL}&t=${new Date().getTime()}`;
    script.id = "jsonp-etf-script";
    
    // 기존 스크립트 제거 후 등록
    const oldScript = document.getElementById("jsonp-etf-script");
    if (oldScript) {
        oldScript.remove();
    }
    
    document.body.appendChild(script);
    
    // 로드 후 청소
    script.onload = () => {
        script.remove();
    };
    script.onerror = () => {
        alert("네이버 API 연결 오류가 발생했습니다.");
        showLoading(false);
    };
}

/**
 * API에서 받은 원시 데이터를 전처리 및 정제합니다.
 */
function handleDataResponse(rawDataList) {
    appState.rawData = rawDataList;
    
    // 데이터 전처리 수행
    appState.processedData = rawDataList.map(item => {
        const nowVal = parseFloat(item.nowVal) || 0;
        const changeVal = parseFloat(item.changeVal) || 0;
        const changeRate = parseFloat(item.changeRate) || 0;
        const nav = parseFloat(item.nav) || 0;
        const threeMonthEarnRate = parseFloat(item.threeMonthEarnRate) || 0;
        const quant = parseInt(item.quant) || 0;
        const amount = parseInt(item.amonut) || 0; // API 오타 amonut 대응
        const marketSum = parseInt(item.marketSum) || 0;
        
        const itemname = item.itemname || "";
        const brand = itemname.split(' ')[0] || "";
        
        // 자산운용사 브랜드명 매핑
        let company = "기타운용사";
        for (const [key, val] of Object.entries(BRAND_TO_COMPANY)) {
            if (brand.toUpperCase().startsWith(key)) {
                company = val;
                break;
            }
        }
        
        // 테마 분류
        const theme = classifyTheme(itemname);
        
        return {
            "종목코드": item.itemcode || "",
            "종목명": itemname,
            "현재가": nowVal,
            "전일대비": changeVal,
            "등락률": changeRate,
            "NAV": nav,
            "3개월수익률": threeMonthEarnRate,
            "거래량": quant,
            "거래대금(백만)": amount,
            "시가총액(억)": marketSum,
            "운용사": company,
            "브랜드": brand,
            "테마분류": theme
        };
    });
    
    // 시가총액 슬라이더 범위 동적 설정
    const mcaps = appState.processedData.map(d => d["시가총액(억)"]);
    appState.limits.minMcap = Math.min(...mcaps);
    appState.limits.maxMcap = Math.max(...mcaps);
    
    appState.filters.minMcap = appState.limits.minMcap;
    appState.filters.maxMcap = appState.limits.maxMcap;
    
    // 필터 컴포넌트(운용사, 테마) 옵션 빌드
    populateFilterOptions();
    initDoubleRangeSlider();
    
    // 필터링 및 대시보드 갱신
    applyFiltersAndRefresh();
    updateTimestamp();
    showLoading(false);
}

/**
 * ETF 종목명 키워드 기반 간이 테마/유형 분류
 */
function classifyTheme(itemname) {
    const name = itemname.toLowerCase();
    if (name.includes('레버리지') || name.includes('2x')) return '레버리지';
    if (name.includes('인버스') || name.includes('곱버스') || name.includes('하락')) return '인버스';
    if (name.includes('채권') || name.includes('국고채') || name.includes('통안채') || name.includes('액티브채권') || name.includes('bond')) return '채권';
    if (name.includes('배당') || name.includes('배당성장') || name.includes('고배당') || name.includes('divid')) return '배당/인컴';
    if (name.includes('반도체') || name.includes('semicon')) return '반도체 테마';
    if (name.includes('ai') || name.includes('인공지능') || name.includes('빅테크') || name.includes('tech')) return 'AI/빅테크 테마';
    if (name.includes('나스닥') || name.includes('s&p500') || name.includes('미국') || name.includes('us')) return '미국 주식';
    if (name.includes('코스피') || name.includes('코스닥') || name.includes('kospi') || name.includes('kosdaq')) return '국내 주식';
    if (name.includes('금') || name.includes('원유') || name.includes('구리') || name.includes('원자재')) return '원자재';
    if (name.includes('리츠') || name.includes('reits')) return '부동산/리츠';
    return '기타 테마';
}

// ==========================================================================
// Setup Filter Components & Listeners
// ==========================================================================

function populateFilterOptions() {
    const companies = [...new Set(appState.processedData.map(d => d["운용사"]))].sort();
    const themes = [...new Set(appState.processedData.map(d => d["테마분류"]))].sort();
    
    const companyOptionsContainer = document.getElementById("company-options");
    const themeOptionsContainer = document.getElementById("theme-options");
    
    companyOptionsContainer.innerHTML = companies.map(c => `
        <div class="multi-option">
            <input type="checkbox" id="company-${c}" value="${c}" class="filter-company-cb">
            <label for="company-${c}">${c}</label>
        </div>
    `).join("");
    
    themeOptionsContainer.innerHTML = themes.map(t => `
        <div class="multi-option">
            <input type="checkbox" id="theme-${t}" value="${t}" class="filter-theme-cb">
            <label for="theme-${t}">${t}</label>
        </div>
    `).join("");
}

function initDoubleRangeSlider() {
    const minInput = document.getElementById("slider-min");
    const maxInput = document.getElementById("slider-max");
    const track = document.getElementById("slider-track");
    const labelMin = document.getElementById("val-min");
    const labelMax = document.getElementById("val-max");
    
    const minLimit = appState.limits.minMcap;
    const maxLimit = appState.limits.maxMcap;
    
    minInput.min = minLimit;
    minInput.max = maxLimit;
    minInput.value = minLimit;
    
    maxInput.min = minLimit;
    maxInput.max = maxLimit;
    maxInput.value = maxLimit;
    
    function updateSliderUI() {
        const val1 = parseInt(minInput.value);
        const val2 = parseInt(maxInput.value);
        
        // 크로스오버 방지
        if (val1 > val2) {
            minInput.value = val2;
        }
        
        const minVal = parseInt(minInput.value);
        const maxVal = parseInt(maxInput.value);
        
        // 트랙바 채우기 비율 계산
        const percentMin = ((minVal - minLimit) / (maxLimit - minLimit)) * 100;
        const percentMax = ((maxVal - minLimit) / (maxLimit - minLimit)) * 100;
        
        track.style.left = percentMin + "%";
        track.style.width = (percentMax - percentMin) + "%";
        
        labelMin.textContent = minVal.toLocaleString();
        labelMax.textContent = maxVal.toLocaleString();
        
        appState.filters.minMcap = minVal;
        appState.filters.maxMcap = maxVal;
    }
    
    minInput.oninput = () => {
        updateSliderUI();
        applyFiltersAndRefresh();
    };
    maxInput.oninput = () => {
        updateSliderUI();
        applyFiltersAndRefresh();
    };
    
    updateSliderUI();
}

function setupFilterListeners() {
    // 검색창 입력 이벤트
    const searchInput = document.getElementById("search-query");
    searchInput.addEventListener("input", (e) => {
        appState.filters.search = e.target.value.trim();
        applyFiltersAndRefresh();
    });
    
    // 새로고침 버튼
    const refreshBtn = document.getElementById("btn-refresh");
    refreshBtn.addEventListener("click", () => {
        fetchRealtimeETFData();
    });
}

function setupDropdownListeners() {
    // 자산운용사 멀티셀렉트
    const compTrigger = document.getElementById("company-trigger");
    const compOptions = document.getElementById("company-options");
    compTrigger.addEventListener("click", (e) => {
        e.stopPropagation();
        compOptions.classList.toggle("open");
        document.getElementById("theme-options").classList.remove("open");
    });
    
    // 테마 멀티셀렉트
    const themeTrigger = document.getElementById("theme-trigger");
    const themeOptions = document.getElementById("theme-options");
    themeTrigger.addEventListener("click", (e) => {
        e.stopPropagation();
        themeOptions.classList.toggle("open");
        compOptions.classList.remove("open");
    });
    
    // 외부 클릭 시 닫기
    document.addEventListener("click", () => {
        compOptions.classList.remove("open");
        themeOptions.classList.remove("open");
    });
    
    // 체크박스 클릭 연동
    document.getElementById("company-options").addEventListener("change", () => {
        const checked = Array.from(document.querySelectorAll(".filter-company-cb:checked")).map(cb => cb.value);
        appState.filters.companies = checked;
        document.getElementById("comp-selected-text").textContent = checked.length > 0 ? `${checked.length}개 선택됨` : "자산운용사 선택";
        applyFiltersAndRefresh();
    });
    
    document.getElementById("theme-options").addEventListener("change", () => {
        const checked = Array.from(document.querySelectorAll(".filter-theme-cb:checked")).map(cb => cb.value);
        appState.filters.themes = checked;
        document.getElementById("theme-selected-text").textContent = checked.length > 0 ? `${checked.length}개 선택됨` : "테마/유형 선택";
        applyFiltersAndRefresh();
    });
}

function setupTabListeners() {
    const headers = document.querySelectorAll(".tab-header");
    const contents = document.querySelectorAll(".tab-content");
    
    headers.forEach(header => {
        header.addEventListener("click", () => {
            const tabId = header.getAttribute("data-tab");
            
            headers.forEach(h => h.classList.remove("active"));
            contents.forEach(c => c.classList.remove("active"));
            
            header.classList.add("active");
            document.getElementById(tabId).classList.add("active");
            
            // 탭 전환 시 Plotly 반응형 크기 재조정을 위한 윈도우 resize 트리거
            window.dispatchEvent(new Event('resize'));
        });
    });
}

// ==========================================================================
// Filtering Logic & KPI Summary Calculations
// ==========================================================================

function applyFiltersAndRefresh() {
    const f = appState.filters;
    
    appState.filteredData = appState.processedData.filter(item => {
        // 검색 필터
        if (f.search && !item["종목명"].toLowerCase().includes(f.search.toLowerCase())) {
            return false;
        }
        // 운용사 필터
        if (f.companies.length > 0 && !f.companies.includes(item["운용사"])) {
            return false;
        }
        // 테마 필터
        if (f.themes.length > 0 && !f.themes.includes(item["테마분류"])) {
            return false;
        }
        // 시가총액 범위 필터
        if (item["시가총액(억)"] < f.minMcap || item["시가총액(억)"] > f.maxMcap) {
            return false;
        }
        return true;
    });
    
    updateKPIs();
    renderCharts();
    renderDataTable();
}

/**
 * 주요 지표 요약 (KPI) 계산 및 출력
 */
function updateKPIs() {
    const count = appState.filteredData.length;
    
    // 총 시가총액 합계 (억 단위를 조 단위로 변환)
    const mcapSum = appState.filteredData.reduce((acc, item) => acc + item["시가총액(억)"], 0);
    const mcapTrillions = mcapSum / 10000;
    
    // 상승, 하락, 보합 종목 카운트
    const upCount = appState.filteredData.filter(item => item["등락률"] > 0).length;
    const downCount = appState.filteredData.filter(item => item["등락률"] < 0).length;
    const flatCount = appState.filteredData.filter(item => item["등락률"] === 0).length;
    
    // 시가총액 가중평균 등락률 계산
    let weightedAvg = 0;
    if (mcapSum > 0) {
        const weightedSum = appState.filteredData.reduce((acc, item) => acc + (item["등락률"] * item["시가총액(억)"]), 0);
        weightedAvg = weightedSum / mcapSum;
    }
    
    // DOM 업데이트
    document.getElementById("kpi-count").textContent = count.toLocaleString() + " 개";
    document.getElementById("kpi-mcap").textContent = mcapTrillions.toFixed(2) + " 조 원";
    document.getElementById("kpi-up-down").innerHTML = `${upCount.toLocaleString()} ▲ <span style="font-size:0.9rem;color:var(--text-secondary)">/</span> ${downCount.toLocaleString()} ▼`;
    document.getElementById("kpi-up-down-delta").textContent = `보합 ${flatCount}개`;
    
    const kpiWeighted = document.getElementById("kpi-weighted");
    kpiWeighted.textContent = weightedAvg.toFixed(2) + "%";
    
    const kpiWeightedDelta = document.getElementById("kpi-weighted-delta");
    kpiWeightedDelta.className = "kpi-delta " + (weightedAvg >= 0 ? "delta-up" : "delta-down");
    kpiWeightedDelta.textContent = (weightedAvg >= 0 ? "▲ " : "▼ ") + Math.abs(weightedAvg).toFixed(2) + "%";
}

// ==========================================================================
// Chart Rendering (Plotly.js)
// ==========================================================================

function renderCharts() {
    renderCompanyBar();
    renderThemeBar();
    renderHistogram();
    renderMcapBar();
    renderAmountBar();
    renderTreeMap();
}

/**
 * 🏢 운용사별 시가총액 점유율 막대 그래프
 */
function renderCompanyBar() {
    const data = appState.filteredData;
    if (data.length === 0) {
        Plotly.purge("chart-company-bar");
        return;
    }
    
    // 운용사별 시가총액 합계 구하기
    const mcapByCompany = {};
    data.forEach(item => {
        const comp = item["운용사"];
        mcapByCompany[comp] = (mcapByCompany[comp] || 0) + item["시가총액(억)"];
    });
    
    const sorted = Object.entries(mcapByCompany)
        .sort((a, b) => a[1] - b[1]); // 오름차순 (수평 바 차트 정렬 최적화)
        
    const plotData = [{
        y: sorted.map(c => c[0]),
        x: sorted.map(c => c[1]),
        type: "bar",
        orientation: "h",
        marker: {
            color: sorted.map(c => c[1]),
            colorscale: "Viridis"
        },
        text: sorted.map(c => (c[1] / 10000).toFixed(2) + " 조 원"),
        textposition: 'auto'
    }];
    
    const layout = {
        ...PLOTLY_THEME,
        title: "<b>🏢 자산운용사별 시가총액 합계 (막대 그래프)</b>",
        xaxis: { 
            title: "시가총액 (억 원)",
            gridcolor: 'rgba(255, 255, 255, 0.05)'
        },
        yaxis: {
            automargin: true
        }
    };
    
    Plotly.newPlot("chart-company-bar", plotData, layout, { responsive: true, displayModeBar: false });
}

/**
 * 🏷️ 테마별 시가총액 점유율 막대 그래프
 */
function renderThemeBar() {
    const data = appState.filteredData;
    if (data.length === 0) {
        Plotly.purge("chart-theme-bar");
        return;
    }
    
    // 테마별 시가총액 합계 구하기
    const mcapByTheme = {};
    data.forEach(item => {
        const theme = item["테마분류"];
        mcapByTheme[theme] = (mcapByTheme[theme] || 0) + item["시가총액(억)"];
    });
    
    const sorted = Object.entries(mcapByTheme)
        .sort((a, b) => a[1] - b[1]);
        
    const plotData = [{
        y: sorted.map(t => t[0]),
        x: sorted.map(t => t[1]),
        type: "bar",
        orientation: "h",
        marker: {
            color: sorted.map(t => t[1]),
            colorscale: "Cividis"
        },
        text: sorted.map(t => t[1].toLocaleString() + " 억"),
        textposition: 'auto'
    }];
    
    const layout = {
        ...PLOTLY_THEME,
        title: "<b>🏷️ 테마별 시가총액 합계 (막대 그래프)</b>",
        xaxis: { 
            title: "시가총액 (억 원)",
            gridcolor: 'rgba(255, 255, 255, 0.05)'
        },
        yaxis: {
            automargin: true
        }
    };
    
    Plotly.newPlot("chart-theme-bar", plotData, layout, { responsive: true, displayModeBar: false });
}

/**
 * 🌳 운용사별 시가총액 점유율 트리맵 (신규 탭 연동)
 */
function renderTreeMap() {
    const data = appState.filteredData;
    if (data.length === 0) {
        Plotly.purge("chart-treemap");
        return;
    }
    
    const mcapByCompany = {};
    data.forEach(item => {
        const comp = item["운용사"];
        mcapByCompany[comp] = (mcapByCompany[comp] || 0) + item["시가총액(억)"];
    });
    
    const labels = ["전체 ETF"];
    const parents = [""];
    const values = [data.reduce((acc, d) => acc + d["시가총액(억)"], 0)];
    
    for (const [comp, mcap] of Object.entries(mcapByCompany)) {
        labels.push(comp);
        parents.push("전체 ETF");
        values.push(mcap);
    }
    
    // 시가총액 상위 100개 종목을 매핑하여 상세도 높임
    const sortedETF = [...data].sort((a, b) => b["시가총액(억)"] - a["시가총액(억)"]).slice(0, 100);
    sortedETF.forEach(item => {
        labels.push(item["종목명"]);
        parents.push(item["운용사"]);
        values.push(item["시가총액(억)"]);
    });
    
    const plotData = [{
        type: "treemap",
        labels: labels,
        parents: parents,
        values: values,
        textinfo: "label+value+percent parent",
        branchvalues: "total",
        hoverinfo: "label+value+percent parent",
        marker: {
            colorscale: "Viridis"
        }
    }];
    
    const layout = {
        ...PLOTLY_THEME,
        title: "<b>🌳 운용사별 종목 시가총액 점유율 (상위 100개 ETF 트리맵)</b>",
        margin: { t: 50, b: 10, l: 10, r: 10 }
    };
    
    Plotly.newPlot("chart-treemap", plotData, layout, { responsive: true, displayModeBar: false });
}

/**
 * 📉 ETF 등락률 분포 (구간별 빈도 막대 그래프)
 */
function renderHistogram() {
    const data = appState.filteredData;
    if (data.length === 0) {
        Plotly.purge("chart-histogram");
        return;
    }
    
    // 등락률 구간 정의 (Binning)
    const bins = {
        '~ -5.0%': 0,
        '-5.0% ~ -3.0%': 0,
        '-3.0% ~ -1.0%': 0,
        '-1.0% ~ +1.0%': 0,
        '+1.0% ~ +3.0%': 0,
        '+3.0% ~ +5.0%': 0,
        '+5.0% ~': 0
    };
    
    data.forEach(item => {
        const rate = item["등락률"];
        if (rate <= -5) bins['~ -5.0%']++;
        else if (rate > -5 && rate <= -3) bins['-5.0% ~ -3.0%']++;
        else if (rate > -3 && rate <= -1) bins['-3.0% ~ -1.0%']++;
        else if (rate > -1 && rate < 1) bins['-1.0% ~ +1.0%']++;
        else if (rate >= 1 && rate < 3) bins['+1.0% ~ +3.0%']++;
        else if (rate >= 3 && rate < 5) bins['+3.0% ~ +5.0%']++;
        else bins['+5.0% ~']++;
    });
    
    const plotData = [{
        x: Object.keys(bins),
        y: Object.values(bins),
        type: "bar",
        marker: {
            color: '#8b5cf6', // --accent-purple
            line: {
                color: 'rgba(255, 255, 255, 0.2)',
                width: 1
            }
        },
        text: Object.values(bins).map(v => v > 0 ? v + "개" : ""),
        textposition: 'auto'
    }];
    
    const layout = {
        ...PLOTLY_THEME,
        title: "<b>📉 ETF 등락률 구간별 빈도 (막대 그래프)</b>",
        xaxis: { 
            title: "등락률 구간",
            gridcolor: 'rgba(255, 255, 255, 0.05)'
        },
        yaxis: { 
            title: "종목 빈도수 (개)",
            gridcolor: 'rgba(255, 255, 255, 0.05)'
        }
    };
    
    Plotly.newPlot("chart-histogram", plotData, layout, { responsive: true, displayModeBar: false });
}

/**
 * 🏆 시가총액 상위 10개 ETF 바 차트
 */
function renderMcapBar() {
    const data = [...appState.filteredData]
        .sort((a, b) => b["시가총액(억)"] - a["시가총액(억)"])
        .slice(0, 10)
        .reverse(); // 차트 위쪽에 1등이 배치되도록 역순 정렬
        
    if (data.length === 0) {
        Plotly.purge("chart-mcap-bar");
        return;
    }
    
    const plotData = [{
        y: data.map(d => d["종목명"]),
        x: data.map(d => d["시가총액(억)"]),
        type: "bar",
        orientation: "h",
        marker: {
            color: data.map(d => d["시가총액(억)"]),
            colorscale: "Viridis"
        },
        text: data.map(d => d["시가총액(억)"].toLocaleString() + " 억"),
        textposition: 'auto'
    }];
    
    const layout = {
        ...PLOTLY_THEME,
        title: "<b>🏆 시가총액 상위 10개 ETF</b>",
        xaxis: { 
            title: "시가총액 (억 원)",
            gridcolor: 'rgba(255, 255, 255, 0.05)'
        },
        yaxis: {
            automargin: true
        }
    };
    
    Plotly.newPlot("chart-mcap-bar", plotData, layout, { responsive: true, displayModeBar: false });
}

/**
 * 🔥 당일 거래대금 상위 10개 ETF 바 차트
 */
function renderAmountBar() {
    const data = [...appState.filteredData]
        .sort((a, b) => b["거래대금(백만)"] - a["거래대금(백만)"])
        .slice(0, 10)
        .reverse();
        
    if (data.length === 0) {
        Plotly.purge("chart-amount-bar");
        return;
    }
    
    const plotData = [{
        y: data.map(d => d["종목명"]),
        x: data.map(d => d["거래대금(백만)"]),
        type: "bar",
        orientation: "h",
        marker: {
            color: data.map(d => d["거래대금(백만)"]),
            colorscale: "Cividis"
        },
        text: data.map(d => d["거래대금(백만)"].toLocaleString() + " 백만"),
        textposition: 'auto'
    }];
    
    const layout = {
        ...PLOTLY_THEME,
        title: "<b>🔥 당일 거래대금 상위 10개 ETF</b>",
        xaxis: { 
            title: "거래대금 (백만 원)",
            gridcolor: 'rgba(255, 255, 255, 0.05)'
        },
        yaxis: {
            automargin: true
        }
    };
    
    Plotly.newPlot("chart-amount-bar", plotData, layout, { responsive: true, displayModeBar: false });
}

// ==========================================================================
// Data Table Rendering & Controls (Sort, CSV Download)
// ==========================================================================

function renderDataTable() {
    const tableBody = document.getElementById("table-body");
    
    // 데이터 정렬
    const sorted = [...appState.filteredData].sort((a, b) => {
        let valA = a[appState.sort.column];
        let valB = b[appState.sort.column];
        
        // 문자열 비교 지원
        if (typeof valA === "string") {
            return appState.sort.ascending 
                ? valA.localeCompare(valB) 
                : valB.localeCompare(valA);
        }
        
        // 수치형 비교
        return appState.sort.ascending ? valA - valB : valB - valA;
    });
    
    tableBody.innerHTML = sorted.map(item => {
        const rateColor = item["등락률"] > 0 ? "delta-up" : item["등락률"] < 0 ? "delta-down" : "delta-neutral";
        const sign = item["등락률"] > 0 ? "+" : "";
        
        return `
            <tr>
                <td><code>${item["종목코드"]}</code></td>
                <td style="font-weight:600;">${item["종목명"]}</td>
                <td><span class="badge ${getCompanyBadgeClass(item["운용사"])}">${item["운용사"]}</span></td>
                <td><span class="badge badge-gray">${item["테마분류"]}</span></td>
                <td style="text-align:right; font-weight:700;">${item["현재가"].toLocaleString()}원</td>
                <td style="text-align:right;" class="${rateColor}">${sign}${item["전일대비"].toLocaleString()}원</td>
                <td style="text-align:right; font-weight:700;" class="${rateColor}">${sign}${item["등락률"].toFixed(2)}%</td>
                <td style="text-align:right;">${item["NAV"].toLocaleString()}원</td>
                <td style="text-align:right;" class="${item["3개월수익률"] > 0 ? 'delta-up' : item["3개월수익률"] < 0 ? 'delta-down' : ''}">${item["3개월수익률"].toFixed(2)}%</td>
                <td style="text-align:right;">${item["거래량"].toLocaleString()}</td>
                <td style="text-align:right; font-weight:600;">${item["거래대금(백만)"].toLocaleString()}백만</td>
                <td style="text-align:right; font-weight:700; color:#60a5fa;">${item["시가총액(억)"].toLocaleString()}억</td>
            </tr>
        `;
    }).join("");
    
    // 테이블 정렬 헤더 이벤트 및 화살표 업데이트
    setupTableHeaderSort();
}

function getCompanyBadgeClass(company) {
    if (company === "삼성자산운용") return "badge-blue";
    if (company === "미래에셋자산운용") return "badge-teal";
    if (company === "KB자산운용") return "badge-purple";
    return "badge-gray";
}

function setupTableHeaderSort() {
    const headers = document.querySelectorAll("table.data-table th[data-col]");
    headers.forEach(th => {
        const colName = th.getAttribute("data-col");
        
        // 기존 화살표 제거
        th.innerHTML = th.textContent.replace(/ [▲▼]$/, "");
        
        if (colName === appState.sort.column) {
            th.innerHTML += appState.sort.ascending ? " ▲" : " ▼";
        }
        
        // 한 번만 등록되도록 이벤트 핸들러 초기화 후 바인딩
        th.onclick = null;
        th.onclick = () => {
            if (appState.sort.column === colName) {
                appState.sort.ascending = !appState.sort.ascending;
            } else {
                appState.sort.column = colName;
                appState.sort.ascending = false;
            }
            renderDataTable();
        };
    });
}

/**
 * 현재 필터링된 데이터를 CSV 포맷으로 다운로드
 */
function downloadCSV() {
    const data = appState.filteredData;
    if (data.length === 0) {
        alert("다운로드할 데이터가 없습니다.");
        return;
    }
    
    const headers = [
        "종목코드", "종목명", "운용사", "테마분류", 
        "현재가", "전일대비", "등락률", "NAV", 
        "3개월수익률", "거래량", "거래대금(백만)", "시가총액(억)"
    ];
    
    const csvRows = [];
    csvRows.push(headers.join(","));
    
    data.forEach(item => {
        const values = headers.map(header => {
            const val = item[header];
            // 쉼표가 들어있는 문자열 처리
            if (typeof val === "string" && val.includes(",")) {
                return `"${val}"`;
            }
            return val;
        });
        csvRows.push(values.join(","));
    });
    
    const csvContent = "\uFEFF" + csvRows.join("\n"); // Excel 한글 깨짐 방지용 BOM 추가
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement("a");
    link.setAttribute("href", url);
    const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
    const timeStr = new Date().toTimeString().slice(0, 8).replace(/:/g, "");
    link.setAttribute("download", `naver_etf_filtered_${dateStr}_${timeStr}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// ==========================================================================
// Helper UI Functions
// ==========================================================================

function showLoading(isLoading) {
    const loader = document.getElementById("loader");
    if (loader) {
        loader.style.display = isLoading ? "flex" : "none";
    }
}

function updateTimestamp() {
    const now = new Date();
    const timeStr = now.toLocaleDateString() + " " + now.toLocaleTimeString();
    document.getElementById("timestamp").textContent = timeStr;
}
