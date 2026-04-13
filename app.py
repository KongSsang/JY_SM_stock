import streamlit as st
import yfinance as yf
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz

st.set_page_config(page_title="내 자산 포트폴리오", layout="wide")
st.title("📈 결혼 자금 관리 현황")

# ==========================================
# ⚙️ 설정 영역 (내 자산 및 시트 정보)
# ==========================================
SHEET_NAME = "Asset_history"  # 👈 본인이 만든 구글 스프레드시트 이름으로 꼭 변경해 주세요!

krw_balance = 766872           # 👈 현재 보유 중인 원화(KRW)
usd_balance = 3035.17     # 👈 현재 보유 중인 달러(USD)

portfolio = [
    {"name": "TIGER 200", "ticker": "102110.KS", "quantity": 6, "buy_price": 87366},
    {"name": "TIGER 미국S&P500", "ticker": "360200.KS", "quantity": 20, "buy_price": 25005},
    {"name": "TIGER 미국나스닥100", "ticker": "133690.KS", "quantity": 3, "buy_price": 164285},
]

# ==========================================
# 📡 데이터 수집 및 구글 시트 연결
# ==========================================
@st.cache_data(ttl=60)
def get_market_data(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period='5d') 
        if len(hist) >= 2:
            current_price = float(hist['Close'].iloc[-1])
            prev_price = float(hist['Close'].iloc[-2])
            return current_price, current_price - prev_price
        elif len(hist) == 1:
            return float(hist['Close'].iloc[0]), 0.0
        return None, None
    except:
        return None, None

@st.cache_resource
def init_connection():
    # Streamlit Secrets에 저장한 구글 키 불러오기
    creds_dict = json.loads(st.secrets["google_key"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

try:
    client = init_connection()
    sheet = client.open(SHEET_NAME).worksheet("History")
except Exception as e:
    st.error(f"구글 스프레드시트 연결 오류: {e}")
    st.stop()

# ==========================================
# 💵 자산 계산 및 화면 출력
# ==========================================
# 1. 현금 자산
current_usd_krw, usd_krw_change = get_market_data("USDKRW=X")
if current_usd_krw is None:
    current_usd_krw, usd_krw_change = 1350.0, 0.0

st.header("💵 현금 자산 (USD & KRW)")
usd_krw_value = usd_balance * current_usd_krw
col1, col2, col3 = st.columns(3)
col1.metric("보유 원화 (KRW)", f"₩{krw_balance:,.0f}")
col2.metric("보유 달러 (USD)", f"${usd_balance:,.2f}")
col3.metric("달러 원화 환산액", f"₩{usd_krw_value:,.0f}", f"환율: ₩{current_usd_krw:,.2f} ({(usd_krw_change):,.2f}원)")

st.divider()

# 2. 주식 자산
st.header("📊 주식 자산")
total_stock_value = 0
total_invested = 0

for item in portfolio:
    current_price, price_change = get_market_data(item["ticker"])
    
    if current_price is not None:
        invested = item["buy_price"] * item["quantity"]
        current_value = current_price * item["quantity"]
        profit = current_value - invested
        return_rate = (profit / invested) * 100 if invested > 0 else 0
        
        total_stock_value += current_value
        total_invested += invested

        st.subheader(f"🔹 {item['name']}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("현재가", f"₩{current_price:,.0f}", f"전일대비: {price_change:,.0f}원")
        c2.metric("평균단가 / 수량", f"₩{item['buy_price']:,.0f} / {item['quantity']}주")
        c3.metric("수익률", f"{return_rate:,.2f}%", f"평가손익: ₩{profit:,.0f}")
        c4.metric("현재 평가액", f"₩{current_value:,.0f}")
        st.write("") 
    else:
        st.error(f"{item['name']} 데이터를 불러올 수 없습니다.")

st.divider()

# 3. 총 자산 요약
st.header("💰 오늘의 총 자산")
grand_total = krw_balance + usd_krw_value + total_stock_value
total_profit = total_stock_value - total_invested
total_return_rate = (total_profit / total_invested) * 100 if total_invested > 0 else 0

col_t1, col_t2 = st.columns(2)
col_t1.metric("총 자산 평가액 (현금 + 주식)", f"₩{grand_total:,.0f}")
col_t2.metric("주식 총 평가손익", f"₩{total_profit:,.0f}", f"주식 총 수익률: {total_return_rate:,.2f}%")

# ==========================================
# 💾 데이터베이스(시트) 기록 및 그래프 출력
# ==========================================
st.divider()
st.header("📈 나의 실제 총 자산 변동 추이")

# 한국 시간 기준으로 오늘 날짜 구하기
kst = pytz.timezone('Asia/Seoul')
today_str = datetime.now(kst).strftime('%Y-%m-%d')

# 구글 시트에서 전체 데이터 불러오기
records = sheet.get_all_records()
df_history = pd.DataFrame(records)

# 오늘 날짜 기록이 없으면 새 줄 추가, 있으면 덮어쓰기 (실시간 반영)
if df_history.empty or today_str not in df_history['Date'].values:
    sheet.append_row([today_str, grand_total])
    # 추가 후 데이터 프레임 갱신
    records = sheet.get_all_records()
    df_history = pd.DataFrame(records)
else:
    # 이미 오늘 날짜가 있다면 현재 총액으로 값만 덮어쓰기 (주가 변동 반영)
    row_idx = len(records) + 1  # 1번 행은 헤더이므로 +1
    sheet.update_cell(row_idx, 2, float(grand_total))
    df_history.at[len(df_history)-1, 'Total_Asset'] = float(grand_total)

# 그래프 그리기
if not df_history.empty:
    df_history['Date'] = pd.to_datetime(df_history['Date'])
    df_history.set_index('Date', inplace=True)
    st.line_chart(df_history['Total_Asset'])
