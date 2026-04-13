import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="내 자산 포트폴리오", layout="wide")
st.title("📈 나의 고정 자산 포트폴리오 대시보드")

# --- 내 자산 데이터 고정 입력 ---
usd_balance = 3035.17

portfolio = [
    {"name": "TIGER 200", "ticker": "102110.KS", "quantity": 6, "buy_price": 87366},
    {"name": "TIGER 미국S&P500", "ticker": "360200.KS", "quantity": 20, "buy_price": 25005},
    {"name": "TIGER 미국나스닥100", "ticker": "133690.KS", "quantity": 3, "buy_price": 164285},
]

# --- 데이터 가져오기 함수 (전일 대비 변동폭 포함) ---
@st.cache_data(ttl=60)
def get_market_data(ticker_symbol):
    try:
        # 주말이나 휴장을 고려해 최근 5일치 데이터를 불러와서 최신 2일을 비교
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period='5d') 
        if len(hist) >= 2:
            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2]
            return current_price, current_price - prev_price
        elif len(hist) == 1:
            return hist['Close'].iloc[0], 0
        return None, None
    except:
        return None, None

# --- 1. 현금(달러) 자산 출력 ---
current_usd_krw, usd_krw_change = get_market_data("USDKRW=X")
if current_usd_krw is None:
    current_usd_krw, usd_krw_change = 1350.0, 0.0

st.header("💵 현금 자산 (USD)")
usd_krw_value = usd_balance * current_usd_krw
col1, col2 = st.columns(2)
col1.metric("보유 달러", f"${usd_balance:,.2f}")
col2.metric(
    "원화 환산액", 
    f"₩{usd_krw_value:,.0f}", 
    f"적용 환율: ₩{current_usd_krw:,.2f} (전일대비 {usd_krw_change:,.2f}원)"
)

st.divider()

# --- 2. 주식 자산 출력 ---
st.header("📊 주식 자산")

total_stock_value = 0
total_invested = 0

for item in portfolio:
    current_price, price_change = get_market_data(item["ticker"])
    
    if current_price is not None:
        # 수익률 및 평가액 계산
        invested = item["buy_price"] * item["quantity"]
        current_value = current_price * item["quantity"]
        profit = current_value - invested
        return_rate = (profit / invested) * 100 if invested > 0 else 0
        
        total_stock_value += current_value
        total_invested += invested

        # 개별 주식 지표 출력
        st.subheader(f"🔹 {item['name']}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("현재가", f"₩{current_price:,.0f}", f"전일대비: {price_change:,.0f}원")
        c2.metric("평균단가 / 수량", f"₩{item['buy_price']:,.0f} / {item['quantity']}주")
        c3.metric("수익률", f"{return_rate:,.2f}%", f"평가손익: ₩{profit:,.0f}")
        c4.metric("현재 평가액", f"₩{current_value:,.0f}")
        st.write("") # 간격 띄우기
    else:
        st.error(f"{item['name']} 데이터를 불러올 수 없습니다.")

st.divider()

# --- 3. 총 자산 요약 ---
st.header("💰 총 자산 요약")
grand_total = usd_krw_value + total_stock_value
total_profit = total_stock_value - total_invested
total_return_rate = (total_profit / total_invested) * 100 if total_invested > 0 else 0

col_t1, col_t2 = st.columns(2)
col_t1.metric("총 자산 평가액 (현금 + 주식)", f"₩{grand_total:,.0f}")
col_t2.metric(
    "주식 총 평가손익", 
    f"₩{total_profit:,.0f}", 
    f"주식 총 수익률: {total_return_rate:,.2f}%"
)
