"""네이버 금융 ETF 실시간 데이터를 수집하고 CSV 파일로 저장하는 1회성 데이터 수집 모듈.

이 모듈은 네이버 금융 ETF API에서 현재 시세 데이터를 요청하여 파싱한 뒤,
프로젝트의 'data' 폴더 내에 타임스탬프 기반 파일명으로 저장합니다.
GitHub Actions 배치 작업 등 단회 실행 수동/자동 수집에 적합하도록 개발되었습니다.
"""

import urllib.request
import json
import re
import csv
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

# 데이터 저장 디렉토리 정의
DATA_DIR: str = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# 로깅 설정 (콘솔 출력용)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
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
        Optional[List[Dict[str, Any]]]: 성공 시 ETF 종목 데이터 리스트, 실패 시 None.

    Raises:
        ValueError: JSONP 파싱에 실패하거나 resultCode가 success가 아닐 때 발생합니다.
    """
    logging.info("네이버 금융 API 호출을 시작합니다...")
    try:
        req = urllib.request.Request(API_URL, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as response:
            content: bytes = response.read()
            # API 인코딩에 맞춰 cp949 혹은 utf-8 디코딩 수행
            try:
                html: str = content.decode('utf-8')
            except UnicodeDecodeError:
                html = content.decode('cp949', errors='ignore')
            
            # JSONP 콜백 래퍼 해제
            match = re.search(r'\((.*)\)', html, re.DOTALL)
            if not match:
                raise ValueError("JSONP 콜백 포맷을 감지할 수 없습니다.")
            
            json_str: str = match.group(1)
            data: Dict[str, Any] = json.loads(json_str)
            
            if data.get("resultCode") != "success":
                raise ValueError(f"API 응답 실패: resultCode={data.get('resultCode')}")
                
            etf_list: List[Dict[str, Any]] = data.get("result", {}).get("etfItemList", [])
            logging.info(f"성공적으로 {len(etf_list)}개의 ETF 종목 데이터를 수집했습니다.")
            return etf_list
            
    except Exception as e:
        logging.error(f"데이터 수집 중 오류 발생: {e}")
        return None

def save_to_csv(etf_list: List[Dict[str, Any]]) -> None:
    """수집한 ETF 데이터를 타임스탬프 기반 파일명의 CSV 파일로 저장합니다.

    파일명은 'data/etf_data_YYYYMMDD_HHMMSS.csv' 형식으로 생성되며, 
    엑셀에서의 한글 깨짐 방지를 위해 UTF-8 with BOM(utf-8-sig) 인코딩으로 저장됩니다.

    Args:
        etf_list (List[Dict[str, Any]]): 저장할 ETF 데이터 목록.
    """
    if not etf_list:
        logging.warning("저장할 데이터가 없어 작업을 스킵합니다.")
        return
        
    timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename: str = os.path.join(DATA_DIR, f"etf_data_{timestamp}.csv")
    
    try:
        # 첫 항목의 키값을 기준으로 CSV 헤더 작성
        fieldnames: List[str] = list(etf_list[0].keys())
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in etf_list:
                writer.writerow(row)
                
        logging.info(f"데이터를 성공적으로 저장했습니다: {filename}")
    except Exception as e:
        logging.error(f"CSV 저장 중 오류 발생: {e}")

def main() -> None:
    """배치용 1회성 데이터 수집기의 메인 컨트롤 함수입니다."""
    logging.info("실시간 ETF 데이터 수집 배치를 수행합니다...")
    etf_list: Optional[List[Dict[str, Any]]] = fetch_etf_data()
    if etf_list:
        save_to_csv(etf_list)
        logging.info("배치 수집 작업을 성공적으로 마쳤습니다.")
    else:
        logging.error("데이터를 수집하지 못해 배치를 종료합니다.")

if __name__ == "__main__":
    main()
