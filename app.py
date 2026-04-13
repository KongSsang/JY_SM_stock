import streamlit as st
import yfinance as yf
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz
import requests

import config 

st.set_page_config(page_title="결혼 자금 포트폴리오", layout="wide")
st.title("📈 결혼 자금 관리 현황")

# ==========================================
# 📡 데이터 수집 (환율 이중화 처리)
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

@st.cache_data(ttl=60)
def get_exchange_rate():
    try:
        hist = yf.Ticker("KRW=X").history(period='5d')
        if len(hist) >= 2:
            curr = float(hist['Close'].iloc[-1])
            prev = float(hist['Close'].iloc[-2])
            return curr, curr - prev
    except:
        pass
    
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        data = requests.get(url).json()
        return float(data['rates']['KRW']), 0.0
    except:
        return 1350.0, 0.0 

# ==========================================
# 🔑 구글 시트 연결
# ==========================================
@st.cache_resource
def init_connection():
    creds_dict = json.loads(st.secrets["google_key"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

try:
    client = init_connection()
    sheet = client.open(config.SHEET_NAME).worksheet("History")
except Exception as e:
    st.error(f"구글 스프레드시트 연결 오류: {e}")
    st.stop()

# ==========================================
# 💵 자산 계산 및 화면 출력
# ==========================================
# 1. 현금 자산 (여러 번 구매한 달러 계산 로직 추가)
current_usd_krw, usd_krw_change = get_exchange_rate()

# 총 보유 달러와 환전에 들어간 총 원화 계산
total_usd_amount = 0
total_krw_invested_for_usd = 0

for purchase in config.usd_purchases:
    total_usd_amount += purchase["amount"]
    total_krw_invested_for_usd += (purchase["buy_rate"] * purchase["amount"])

# 평균 환전가 계산 (가중 평균)
avg_usd_buy_rate = total_krw_invested_for_usd / total_usd_amount if total_usd_amount > 0 else 0

st.header("💵 현금 자산 (USD & KRW)")

# 달러 환차익 계산 
usd_current_krw = total_usd_amount * current_usd_krw
usd_profit = usd_current_krw - total_krw_invested_for_usd
usd_return_rate = (usd_profit / total_krw_invested_for_usd) * 100 if total_krw_invested_for_usd > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("보유 원화 (KRW)", f"₩{config.krw_balance:,.0f}")
col2.metric("보유 달러 (USD)", f"${total_usd_amount:,.2f}", f"평균 환전가: ₩{avg_usd_buy_rate:,.0f}")
col3.metric("달러 원화 환산액", f"₩{usd_current_krw:,.0f}", f"환율: ₩{current_usd_krw:,.2f} (전일대비 {usd_krw_change:,.2f}원)")
col4.metric("달러 환차익 수익률", f"{usd_return_rate:,.2f}%", f"평가손익: ₩{usd_profit:,.0f}")

st.divider()

# 2. 주식 자산 
total_stock_value = 0
total_invested = 0
stock_render_data = []

for item in config.portfolio:
    current_price, price_change = get_market_data(item["ticker"])
    
    if current_price is not None:
        invested = item["buy_price"] * item["quantity"]
        current_value = current_price * item["quantity"]
        profit = current_value - invested
        return_rate = (profit / invested) * 100 if invested > 0 else 0
        
        total_stock_value += current_value
        total_invested += invested
        
        stock_render_data.append({
            "item": item,
            "current_price": current_price,
            "price_change": price_change,
            "profit": profit,
            "return_rate": return_rate,
            "current_value": current_value,
            "error": False
        })
    else:
        stock_render_data.append({"item": item, "error": True})

expander_title = f"📊 주식 자산 (총 평가액: ₩{total_stock_value:,.0f})"

with st.expander(expander_title, expanded=False):
    for data in stock_render_data:
        if data["error"]:
            st.error(f"{data['item']['name']} 데이터를 불러올 수 없습니다.")
        else:
            item = data["item"]
            st.subheader(f"🔹 {item['name']}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("현재가", f"₩{data['current_price']:,.0f}", f"전일대비: {data['price_change']:,.0f}원")
            c2.metric("평균단가 / 수량", f"₩{item['buy_price']:,.0f} / {item['quantity']}주")
            c3.metric("수익률", f"{data['return_rate']:,.2f}%", f"평가손익: ₩{data['profit']:,.0f}")
            c4.metric("현재 평가액", f"₩{data['current_value']:,.0f}")
            st.write("") 

st.divider()

# 3. 총 자산 요약
st.header("💰 오늘의 총 자산")
grand_total = config.krw_balance + usd_current_krw + total_stock_value
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

kst = pytz.timezone('Asia/Seoul')
today_str = datetime.now(kst).strftime('%Y-%m-%d')

records = sheet.get_all_records()
df_history = pd.DataFrame(records)

if df_history.empty or today_str not in df_history['Date'].values:
    sheet.append_row([today_str, grand_total])
    records = sheet.get_all_records()
    df_history = pd.DataFrame(records)
else:
    row_idx = len(records) + 1
    sheet.update_cell(row_idx, 2, float(grand_total))
    df_history.at[len(df_history)-1, 'Total_Asset'] = float(grand_total)

if not df_history.empty:
    df_history['Date'] = pd.to_datetime(df_history['Date'])
    df_history.set_index('Date', inplace=True)
    st.line_chart(df_history['Total_Asset'])
