"""ETF 데이터 수집 및 CSV 저장 스케줄러 모듈.

이 모듈은 네이버 금융 ETF API에서 정기적으로 데이터를 수집하여 
CSV 파일로 저장하는 스케줄러 기능을 제공합니다.
수집 주기는 10분이며, 매 분 00초 근처에 동기화되어 동작합니다.
"""

import urllib.request
import json
import re
import csv
import os
import time
from datetime import datetime
import logging
from typing import List, Dict, Any, Optional

# 로그 및 데이터 디렉토리 생성
LOG_DIR: str = "logs"
DATA_DIR: str = "data"
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# 로그 설정
log_file: str = os.path.join(LOG_DIR, "scheduler.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

API_URL: str = "https://finance.naver.com/api/sise/etfItemList.nhn?etfType=0&targetColumn=market_sum&sortOrder=desc&_callback=window.__jindo2_callback._7957"
HEADERS: Dict[str, str] = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def fetch_etf_data() -> Optional[List[Dict[str, Any]]]:
    """네이버 금융 API로부터 ETF 시세 데이터를 요청하고 파싱합니다.

    JSONP 형식으로 반환되는 데이터를 일반 JSON 형태로 변환하여 
    ETF 종목 목록(dict의 list)을 추출합니다.

    Returns:
        Optional[List[Dict[str, Any]]]: 성공 시 ETF 종목 데이터 리스트를 반환하며, 
                                        실패 시 None을 반환합니다.

    Raises:
        ValueError: JSONP 파싱에 실패하거나 resultCode가 success가 아닐 때 발생합니다.
    """
    logging.info("네이버 금융 ETF API 호출 중...")
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
                raise ValueError("JSONP 콜백 포맷을 찾을 수 없습니다.")
            
            json_str: str = match.group(1)
            data: Dict[str, Any] = json.loads(json_str)
            
            if data.get("resultCode") != "success":
                raise ValueError(f"API 호출 실패: resultCode={data.get('resultCode')}")
                
            etf_list: List[Dict[str, Any]] = data.get("result", {}).get("etfItemList", [])
            logging.info(f"성공적으로 {len(etf_list)}개의 ETF 종목 데이터를 수집했습니다.")
            return etf_list
            
    except Exception as e:
        logging.error(f"데이터 수집 중 오류 발생: {e}")
        return None

def save_to_csv(etf_list: List[Dict[str, Any]]) -> None:
    """수집된 ETF 데이터 리스트를 CSV 파일로 저장합니다.

    파일명은 실행 시점의 타임스탬프를 포함하여 'data/etf_data_YYYYMMDD_HHMMSS.csv' 
    형식으로 생성됩니다. 엑셀에서의 한글 깨짐을 방지하기 위해 utf-8-sig로 인코딩합니다.

    Args:
        etf_list (List[Dict[str, Any]]): CSV 파일에 저장할 ETF 데이터 목록입니다.
    """
    if not etf_list:
        logging.warning("저장할 ETF 데이터가 없습니다.")
        return
    
    # 저장할 파일명 설정 (data/etf_data_YYYYMMDD_HHMMSS.csv)
    timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename: str = os.path.join(DATA_DIR, f"etf_data_{timestamp}.csv")
    
    try:
        # 첫 번째 아이템의 키값을 기준으로 CSV 헤더(fieldnames)를 설정
        fieldnames: List[str] = list(etf_list[0].keys())
        
        # 파일 작성 (UTF-8 w/ BOM으로 저장하여 엑셀에서 한글이 안 깨지도록 함)
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in etf_list:
                writer.writerow(row)
                
        logging.info(f"데이터를 {filename} 파일로 저장 완료했습니다.")
    except Exception as e:
        logging.error(f"CSV 저장 중 오류 발생: {e}")

def main() -> None:
    """스케줄러의 메인 진입 함수입니다.

    10분 주기로 네이버 API로부터 데이터를 가져와 CSV 파일에 기록합니다.
    매 수집 이후 다음 정시 00초까지의 대기 시간을 계산하여 대기합니다.
    """
    logging.info("ETF 데이터 수집 스케줄러를 시작합니다 (10분 주기).")
    
    while True:
        try:
            etf_list: Optional[List[Dict[str, Any]]] = fetch_etf_data()
            if etf_list:
                save_to_csv(etf_list)
        except Exception as e:
            logging.error(f"메인 루프 오류 발생: {e}")
            
        # 정확히 다음 10분(00초)까지 대기하여 정시 수집 수행
        now: float = time.time()
        sleep_time: float = 600 - (now % 600)
        # 만약 sleep_time이 너무 짧으면 (예: 10초 미만) 중복 수집 방지를 위해 10분을 더함
        if sleep_time < 10:
            sleep_time += 600
            
        logging.info(f"다음 수집까지 {sleep_time:.1f}초 대기합니다.")
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()
