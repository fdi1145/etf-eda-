"""네이버 금융 실시간 ETF 데이터를 수집하고 다각도로 탐색하는 종합 EDA 대시보드.

이 모듈은 네이버 금융 ETF API로부터 실시간으로 ETF 데이터를 가져와,
시가총액, 등락률, 자산운용사별 점유율 등을 인터랙티브한 대시보드 형태로 시각화 및 분석하여 제공합니다.
"""

import urllib.request
import json
import re
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# Streamlit 페이지 설정 (반드시 최상단에 위치)
st.set_page_config(
    page_title="실시간 네이버 ETF 종합 EDA 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API 정보 설정
API_URL: str = "https://finance.naver.com/api/sise/etfItemList.nhn?etfType=0&targetColumn=market_sum&sortOrder=desc&_callback=window.__jindo2_callback._7957"
HEADERS: Dict[str, str] = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# 자산운용사 브랜드명 매핑 사전
BRAND_TO_COMPANY: Dict[str, str] = {
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
}

@st.cache_data(ttl=60)  # API 부하 감소를 위해 60초 캐싱 적용
def fetch_etf_data() -> Optional[List[Dict[str, Any]]]:
    """네이버 금융 API로부터 ETF 시세 데이터를 요청하고 파싱합니다.

    JSONP 형식으로 반환되는 데이터를 일반 JSON 형태로 변환하여 
    ETF 종목 목록을 추출합니다.

    Returns:
        Optional[List[Dict[str, Any]]]: 성공 시 ETF 종목 데이터 리스트, 실패 시 None.
    """
    try:
        req = urllib.request.Request(API_URL, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as response:
            content: bytes = response.read()
            # 네이버 금융 API의 인코딩을 감안하여 utf-8 디코딩 시도 (실패 시 cp949 적용)
            try:
                html: str = content.decode('utf-8')
            except UnicodeDecodeError:
                html = content.decode('cp949', errors='ignore')
            
            # JSONP 콜백 함수 래핑 해제 (window.__jindo2_callback._7957(...) -> ...)
            match = re.search(r'\((.*)\)', html, re.DOTALL)
            if not match:
                st.error("JSONP 콜백 포맷을 찾을 수 없습니다.")
                return None
            
            json_str: str = match.group(1)
            data: Dict[str, Any] = json.loads(json_str)
            
            if data.get("resultCode") != "success":
                st.error(f"API 호출 실패: resultCode={data.get('resultCode')}")
                return None
                
            return data.get("result", {}).get("etfItemList", [])
            
    except Exception as e:
        st.error(f"데이터 수집 중 오류 발생: {e}")
        return None

def process_data(etf_list: List[Dict[str, Any]]) -> pd.DataFrame:
    """원시 ETF 데이터 목록을 정리하여 분석에 적합한 Pandas DataFrame으로 변환합니다.

    컬럼명 변경, 데이터 타입 변환, 운용사 분류 및 테마 태깅 등을 수행합니다.

    Args:
        etf_list (List[Dict[str, Any]]): API로부터 수집된 ETF 종목 데이터 리스트.

    Returns:
        pd.DataFrame: 전처리된 ETF 데이터프레임.
    """
    df = pd.DataFrame(etf_list)
    
    # 1. 컬럼 매핑 및 정제
    column_mapping = {
        'itemcode': '종목코드',
        'itemname': '종목명',
        'nowVal': '현재가',
        'changeVal': '전일대비',
        'changeRate': '등락률',
        'nav': 'NAV',
        'threeMonthEarnRate': '3개월수익률',
        'quant': '거래량',
        'amount': '거래대금(백만)',
        'marketSum': '시가총액(억)'
    }
    
    # 존재하는 컬럼만 매핑하여 선택
    existing_cols = {k: v for k, v in column_mapping.items() if k in df.columns}
    df = df[list(existing_cols.keys())].rename(columns=existing_cols)
    
    # 2. 결측치 및 타입 변환
    numeric_cols = ['현재가', '전일대비', '등락률', 'NAV', '3개월수익률', '거래량', '거래대금(백만)', '시가총액(억)']
    for col in numeric_cols:
        if col in df.columns:
            # 수치형 변환 과정에서 생기는 오류 방지
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 3. 자산운용사 분류 로직 적용
    def get_company(item_name: str) -> str:
        first_word = item_name.split(' ')[0]
        # 대표적인 브랜드명 앞부분 매칭 검증
        for brand, company in BRAND_TO_COMPANY.items():
            if first_word.upper().startswith(brand):
                return company
        return "기타운용사"
        
    df['운용사'] = df['종목명'].apply(get_company)
    df['브랜드'] = df['종목명'].apply(lambda x: x.split(' ')[0])

    # 4. 키워드 기반 간이 테마/유형 분류
    def classify_theme(item_name: str) -> str:
        name = item_name.lower()
        if '레버리지' in name or '2x' in name:
            return '레버리지'
        elif '인버스' in name or '곱버스' in name or '하락' in name:
            return '인버스'
        elif '채권' in name or '국고채' in name or '통안채' in name or '액티브채권' in name or 'bond' in name:
            return '채권'
        elif '배당' in name or '배당성장' in name or '고배당' in name or 'divid' in name:
            return '배당/인컴'
        elif '반도체' in name or 'semicon' in name:
            return '반도체 테마'
        elif 'ai' in name or '인공지능' in name or '빅테크' in name or 'tech' in name:
            return 'AI/빅테크 테마'
        elif '나스닥' in name or 's&p500' in name or '미국' in name or 'us' in name:
            return '미국 주식'
        elif '코스피' in name or '코스닥' in name or 'kospi' in name or 'kosdaq' in name:
            return '국내 주식'
        elif '금' in name or '원유' in name or '구리' in name or '원자재' in name:
            return '원자재'
        elif '리츠' in name or 'reits' in name:
            return '부동산/리츠'
        else:
            return '기타 테마'

    df['테마분류'] = df['종목명'].apply(classify_theme)
    
    return df

def main() -> None:
    """Streamlit EDA 대시보드의 레이아웃과 데이터 렌더링을 제어하는 메인 함수입니다."""
    
    # 타이틀 영역 디자인 (고급스러운 헤더 레이아웃)
    st.markdown("""
        <div style="background-color:#1e293b;padding:20px;border-radius:10px;margin-bottom:20px;text-align:center;color:white;">
            <h1 style="margin:0;font-size:2.5rem;font-weight:700;letter-spacing:-1px;">📈 Naver ETF 실시간 종합 EDA 대시보드</h1>
            <p style="margin:5px 0 0 0;font-size:1.1rem;color:#94a3b8;">네이버 금융 실시간 시세 데이터를 기반으로 한 인터랙티브 시각화 분석 플랫폼</p>
        </div>
    """, unsafe_allow_html=True)
    
    # 1. 데이터 가져오기
    raw_data = fetch_etf_data()
    if not raw_data:
        st.warning("데이터를 가져오는 중이거나 일시적으로 API 연결이 원활하지 않습니다. 새로고침을 시도해 보세요.")
        return
        
    df = process_data(raw_data)
    
    # 데이터 최종 업데이트 시간
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 사이드바 레이아웃 및 검색/필터링 설정
    st.sidebar.header("🔍 대시보드 필터 컨트롤러")
    
    # 검색 필터
    search_query = st.sidebar.text_input("종목명 검색", "")
    
    # 자산운용사 필터
    all_companies = sorted(list(df['운용사'].unique()))
    selected_companies = st.sidebar.multiselect(
        "자산운용사 선택",
        options=all_companies,
        default=[]
    )
    
    # 테마 필터
    all_themes = sorted(list(df['테마분류'].unique()))
    selected_themes = st.sidebar.multiselect(
        "테마/유형 선택",
        options=all_themes,
        default=[]
    )
    
    # 시가총액 슬라이더 필터
    min_mcap = int(df['시가총액(억)'].min())
    max_mcap = int(df['시가총액(억)'].max())
    mcap_range = st.sidebar.slider(
        "시가총액 범위 (억 원)",
        min_value=min_mcap,
        max_value=max_mcap,
        value=(min_mcap, max_mcap)
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"🔄 **실시간 갱신 시간**:\n{current_time}")
    
    if st.sidebar.button("데이터 즉시 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # 데이터 필터링 적용
    filtered_df = df.copy()
    if search_query:
        filtered_df = filtered_df[filtered_df['종목명'].str.contains(search_query, case=False)]
    if selected_companies:
        filtered_df = filtered_df[filtered_df['운용사'].isin(selected_companies)]
    if selected_themes:
        filtered_df = filtered_df[filtered_df['테마분류'].isin(selected_themes)]
        
    filtered_df = filtered_df[
        (filtered_df['시가총액(억)'] >= mcap_range[0]) & 
        (filtered_df['시가총액(억)'] <= mcap_range[1])
    ]

    # 2. 주요 KPI 지표 요약 영역 (st.columns 활용)
    total_etf = len(filtered_df)
    total_mcap_trillions = filtered_df['시가총액(억)'].sum() / 10000  # 억 단위를 조 단위로 변환
    
    # 등락 현황 분석
    up_count = len(filtered_df[filtered_df['등락률'] > 0])
    down_count = len(filtered_df[filtered_df['등락률'] < 0])
    flat_count = len(filtered_df[filtered_df['등락률'] == 0])
    
    # 가중 평균 등락률 (시가총액 가중치 적용)
    if filtered_df['시가총액(억)'].sum() > 0:
        weighted_avg_return = (filtered_df['등락률'] * filtered_df['시가총액(억)']).sum() / filtered_df['시가총액(억)'].sum()
    else:
        weighted_avg_return = 0.0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="📊 총 ETF 종목 수",
            value=f"{total_etf:,} 개",
            help="필터링 조건에 부합하는 ETF 종목의 총 개수입니다."
        )
    with col2:
        st.metric(
            label="💰 총 시가총액 합계",
            value=f"{total_mcap_trillions:.2f} 조 원",
            help="분석 대상 종목들의 시가총액 총합입니다."
        )
    with col3:
        st.metric(
            label="📈 상승 / 하락 종목",
            value=f"{up_count:,} ▲ / {down_count:,} ▼",
            delta=f"보합 {flat_count}개",
            delta_color="off"
        )
    with col4:
        st.metric(
            label="⚖️ 시가총액 가중평균 등락률",
            value=f"{weighted_avg_return:.2f}%",
            delta=f"{weighted_avg_return:.2f}%",
            delta_color="normal" if weighted_avg_return >= 0 else "inverse"
        )

    st.markdown("---")

    # 3. 탭 구성 레이아웃
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏢 운용사 & 테마 점유율", 
        "📉 등락률 및 분포 분석", 
        "🏆 시가총액 & 거래 분석", 
        "📋 ETF 상세 데이터 시트"
    ])
    
    # --- Tab 1: 운용사 & 테마 점유율 ---
    with tab1:
        col1_1, col1_2 = st.columns(2)
        
        with col1_1:
            st.subheader("🏢 자산운용사별 시가총액 점유율 (상위 10개)")
            company_mcap = filtered_df.groupby('운용사')['시가총액(억)'].sum().reset_index()
            company_mcap = company_mcap.sort_values(by='시가총액(억)', ascending=False).head(10)
            
            fig_company = px.pie(
                company_mcap, 
                values='시가총액(억)', 
                names='운용사',
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel,
                labels={'시가총액(억)': '시가총액 (억 원)'}
            )
            fig_company.update_layout(margin=dict(t=30, b=10, l=10, r=10), height=400)
            st.plotly_chart(fig_company, use_container_width=True)
            
        with col1_2:
            st.subheader("🏷️ ETF 테마/자산유형별 점유율 (시가총액 기준)")
            theme_mcap = filtered_df.groupby('테마분류')['시가총액(억)'].sum().reset_index()
            theme_mcap = theme_mcap.sort_values(by='시가총액(억)', ascending=False)
            
            fig_theme = px.treemap(
                theme_mcap, 
                path=['테마분류'], 
                values='시가총액(억)',
                color='시가총액(억)',
                color_continuous_scale='Blues',
                labels={'시가총액(억)': '시가총액 (억 원)'}
            )
            fig_theme.update_layout(margin=dict(t=30, b=10, l=10, r=10), height=400)
            st.plotly_chart(fig_theme, use_container_width=True)
            
        # 운용사별 종목 수 및 평균 수익률 서브 테이블
        st.markdown("### 📊 운용사별 주요 요약 지표")
        company_stats = filtered_df.groupby('운용사').agg(
            종목수=('종목명', 'count'),
            총시가총액_억=('시가총액(억)', 'sum'),
            평균등락률=('등락률', 'mean'),
            평균수익률_3M=('3개월수익률', 'mean')
        ).reset_index()
        company_stats = company_stats.sort_values(by='총시가총액_억', ascending=False)
        company_stats['총시가총액(조)'] = company_stats['총시가총액_억'] / 10000
        company_stats = company_stats.drop(columns=['총시가총액_억'])
        
        # 포맷팅 적용
        company_stats['평균등락률'] = company_stats['평균등락률'].map('{:.2f}%'.format)
        company_stats['평균수익률_3M'] = company_stats['평균수익률_3M'].map('{:.2f}%'.format)
        company_stats['총시가총액(조)'] = company_stats['총시가총액(조)'].map('{:.2f}조 원'.format)
        
        st.dataframe(company_stats, use_container_width=True, hide_index=True)

    # --- Tab 2: 등락률 및 분포 분석 ---
    with tab2:
        col2_1, col2_2 = st.columns(2)
        
        with col2_1:
            st.subheader("📊 등락률 분포 (히스토그램)")
            fig_hist = px.histogram(
                filtered_df, 
                x='등락률',
                nbins=50,
                color_discrete_sequence=['#475569'],
                labels={'등락률': '등락률 (%)'},
                marginal="box"
            )
            fig_hist.update_layout(
                yaxis_title="ETF 종목 수",
                margin=dict(t=30, b=10, l=10, r=10),
                height=400
            )
            st.plotly_chart(fig_hist, use_container_width=True)
            
        with col2_2:
            st.subheader("💡 현재가 vs NAV 괴리율 분석")
            # 현재가와 NAV의 괴리율 계산 (NAV가 0인 종목 제외)
            nav_df = filtered_df[filtered_df['NAV'] > 0].copy()
            nav_df['괴리율(%)'] = ((nav_df['현재가'] - nav_df['NAV']) / nav_df['NAV']) * 100
            
            fig_scatter = px.scatter(
                nav_df,
                x='NAV',
                y='현재가',
                size='시가총액(억)',
                color='괴리율(%)',
                color_continuous_scale='RdBu_r',
                hover_name='종목명',
                labels={'NAV': '순자산가치 (NAV)', '현재가': '현재가 (원)'}
            )
            fig_scatter.update_layout(margin=dict(t=30, b=10, l=10, r=10), height=400)
            st.plotly_chart(fig_scatter, use_container_width=True)

        col2_3, col2_4 = st.columns(2)
        with col2_3:
            st.success("🔺 **등락률 상위 10개 ETF**")
            top_performers = filtered_df.sort_values(by='등락률', ascending=False).head(10)
            st.dataframe(
                top_performers[['종목명', '현재가', '등락률', '운용사']], 
                use_container_width=True, 
                hide_index=True
            )
        with col2_4:
            st.error("🔻 **등락률 하위 10개 ETF**")
            worst_performers = filtered_df.sort_values(by='등락률', ascending=True).head(10)
            st.dataframe(
                worst_performers[['종목명', '현재가', '등락률', '운용사']], 
                use_container_width=True, 
                hide_index=True
            )

    # --- Tab 3: 시가총액 & 거래 분석 ---
    with tab3:
        col3_1, col3_2 = st.columns(2)
        
        with col3_1:
            st.subheader("🏆 시가총액 상위 10개 ETF")
            top_mcap = filtered_df.sort_values(by='시가총액(억)', ascending=False).head(10)
            
            fig_mcap_bar = px.bar(
                top_mcap,
                x='시가총액(억)',
                y='종목명',
                orientation='h',
                color='시가총액(억)',
                color_continuous_scale='Viridis',
                labels={'시가총액(억)': '시가총액 (억 원)', '종목명': '종목명'},
                text_auto=True
            )
            fig_mcap_bar.update_layout(
                yaxis={'categoryorder':'total ascending'},
                margin=dict(t=30, b=10, l=10, r=10),
                height=450
            )
            st.plotly_chart(fig_mcap_bar, use_container_width=True)
            
        with col3_2:
            st.subheader("🔥 당일 거래대금 상위 10개 ETF")
            top_amount = filtered_df.sort_values(by='거래대금(백만)', ascending=False).head(10)
            
            fig_amount_bar = px.bar(
                top_amount,
                x='거래대금(백만)',
                y='종목명',
                orientation='h',
                color='거래대금(백만)',
                color_continuous_scale='Cividis',
                labels={'거래대금(백만)': '거래대금 (백만 원)', '종목명': '종목명'},
                text_auto=True
            )
            fig_amount_bar.update_layout(
                yaxis={'categoryorder':'total ascending'},
                margin=dict(t=30, b=10, l=10, r=10),
                height=450
            )
            st.plotly_chart(fig_amount_bar, use_container_width=True)

    # --- Tab 4: ETF 상세 데이터 시트 ---
    with tab4:
        st.subheader("📋 전체/필터링된 ETF 리스트")
        
        # 데이터프레임 다운로드용 CSV 포맷 변환
        csv_data = filtered_df.to_csv(index=False, encoding='utf-8-sig')
        
        st.download_button(
            label="📥 현재 필터링된 데이터 CSV 다운로드",
            data=csv_data,
            file_name=f"naver_etf_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        # 컬럼 순서 재조정 및 테이블 출력
        display_cols = [
            '종목코드', '종목명', '운용사', '테마분류', 
            '현재가', '전일대비', '등락률', 'NAV', 
            '3개월수익률', '거래량', '거래대금(백만)', '시가총액(억)'
        ]
        
        st.dataframe(
            filtered_df[display_cols].sort_values(by='시가총액(억)', ascending=False),
            use_container_width=True,
            hide_index=True
        )

if __name__ == "__main__":
    main()
