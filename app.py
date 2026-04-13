import streamlit as st
import yfinance as yf
import pandas as pd

# 페이지 기본 설정
st.set_page_config(page_title="내 자산 포트폴리오", layout="wide")
st.title("📈 나의 자산 포트폴리오 대시보드")

# --- 데이터 가져오기 함수 (캐싱 적용으로 속도 향상) ---
@st.cache_data(ttl=60) # 1분마다 데이터 갱신
def get_current_price(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        todays_data = ticker.history(period='1d')
        return todays_data['Close'].iloc[0]
    except:
        return None

@st.cache_data(ttl=60)
def get_exchange_rate():
    try:
        # 야후 파이낸스에서 원/달러 환율 가져오기
        rate_data = yf.Ticker("USDKRW=X").history(period='1d')
        return rate_data['Close'].iloc[0]
    except:
        return 1350.0 # API 통신 오류 시 임시 기본값

# --- 사이드바: 내 자산 및 주식 정보 입력 ---
st.sidebar.header("💰 자산 정보 입력")
krw_balance = st.sidebar.number_input("원화 보유액 (KRW)", value=1000000, step=10000)
usd_balance = st.sidebar.number_input("달러 보유액 (USD)", value=1000.0, step=10.0)

st.sidebar.divider()
st.sidebar.subheader("📊 주식 정보")
ticker = st.sidebar.text_input("주식 티커 (예: AAPL, MSFT)", value="AAPL").upper()
buy_price = st.sidebar.number_input("평균 구매가 (USD)", value=150.0, step=1.0)
quantity = st.sidebar.number_input("보유 수량", value=10.0, step=1.0)

# --- 메인 화면: 계산 및 출력 로직 ---
if ticker:
    current_price = get_current_price(ticker)
    exchange_rate = get_exchange_rate()

    if current_price is not None:
        # 수익률 및 평가액 계산
        invested_usd = buy_price * quantity
        current_stock_usd = current_price * quantity
        profit_usd = current_stock_usd - invested_usd
        return_rate = (profit_usd / invested_usd) * 100 if invested_usd > 0 else 0

        # 총 자산 계산
        total_usd_asset = usd_balance + current_stock_usd
        total_krw_converted = total_usd_asset * exchange_rate
        grand_total_krw = krw_balance + total_krw_converted

        # 1. 환율 정보
        st.subheader(f"현재 환율: ₩{exchange_rate:,.2f} / USD")
        
        # 2. 주식 수익률 요약 (컬럼 레이아웃)
        col1, col2, col3 = st.columns(3)
        col1.metric(
            label=f"{ticker} 현재가", 
            value=f"${current_price:,.2f}", 
            delta=f"평단가 대비: ${(current_price - buy_price):,.2f}"
        )
        col2.metric(
            label="주식 수익률", 
            value=f"{return_rate:,.2f}%", 
            delta=f"${profit_usd:,.2f}"
        )
        col3.metric(
            label="현재 주식 평가액", 
            value=f"${current_stock_usd:,.2f}"
        )

        st.divider()

        # 3. 총 잔고 요약
        st.subheader("총 자산 요약")
        c1, c2 = st.columns(2)
        c1.metric(label="총 달러 자산 (현금 + 주식)", value=f"${total_usd_asset:,.2f}")
        c2.metric(label="총 자산 원화 환산액 (기존 원화 포함)", value=f"₩{grand_total_krw:,.0f}")
        
        # 4. 데이터 시각화: 최근 1개월 주가 추이 그래프
        st.divider()
        st.subheader(f"최근 1개월 {ticker} 주가 추이")
        history = yf.Ticker(ticker).history(period="1mo")
        if not history.empty:
            st.line_chart(history['Close'])

    else:
        st.error("해당 주식 티커를 찾을 수 없거나 야후 파이낸스에서 데이터를 불러오지 못했습니다. 티커명을 확인해 주세요.")
