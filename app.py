import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="내 자산 포트폴리오", layout="wide")
st.title("📈 나의 고정 자산 포트폴리오 대시보드")

# --- 내 자산 데이터 고정 입력 ---
krw_balance = 0  # 👈 여기에 현재 보유 중인 원화(KRW) 금액을 입력하세요 (예: 1500000)
usd_balance = 3035.17

portfolio = [
    {"name": "TIGER 200", "ticker": "102110.KS", "quantity": 6, "buy_price": 87366},
    {"name": "TIGER 미국S&P500", "ticker": "360200.KS", "quantity": 20, "buy_price": 25005},
    {"name": "TIGER 미국나스닥100", "ticker": "133690.KS", "quantity": 3, "buy_price": 164285},
]

# --- 최근 3개월 데이터 한 번에 가져오기 ---
@st.cache_data(ttl=600) # 10분마다 데이터 갱신
def fetch_historical_data():
    df = pd.DataFrame()
    
    try:
        # 환율 데이터 (원/달러)
        df['USDKRW'] = yf.Ticker("USDKRW=X").history(period="3mo")['Close']
        
        # 주식 데이터
        for item in portfolio:
            df[item['ticker']] = yf.Ticker(item['ticker']).history(period="3mo")['Close']
            
        # 휴장일(주말 등) 결측치를 이전 날짜 가격으로 채우기
        df = df.ffill().dropna()
        
        # 스트림릿 그래프 오류 방지를 위해 시간대(Timezone) 정보 제거
        df.index = df.index.tz_localize(None)
        return df
    except:
        return pd.DataFrame()

history_df = fetch_historical_data()

# --- 데이터 계산 및 화면 출력 ---
if not history_df.empty:
    # 가장 최근일과 그 전일 데이터 추출
    curr_usd = history_df['USDKRW'].iloc[-1]
    prev_usd = history_df['USDKRW'].iloc[-2]
    
    # 1. 현금 자산 출력
    st.header("💵 현금 자산")
    col1, col2, col3 = st.columns(3)
    col1.metric("보유 원화 (KRW)", f"₩{krw_balance:,.0f}")
    col2.metric("보유 달러 (USD)", f"${usd_balance:,.2f}")
    col3.metric("달러 원화 환산액", f"₩{usd_balance * curr_usd:,.0f}", f"환율: ₩{curr_usd:,.2f} ({(curr_usd - prev_usd):,.2f}원)")
    
    st.divider()
    
    # 2. 주식 자산 출력
    st.header("📊 주식 자산")
    
    total_stock_value = 0
    total_invested = 0
    
    for item in portfolio:
        ticker = item['ticker']
        curr_price = history_df[ticker].iloc[-1]
        prev_price = history_df[ticker].iloc[-2]
        
        invested = item['buy_price'] * item['quantity']
        curr_val = curr_price * item['quantity']
        profit = curr_val - invested
        ret_rate = (profit / invested) * 100 if invested > 0 else 0
        
        total_stock_value += curr_val
        total_invested += invested
        
        st.subheader(f"🔹 {item['name']}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("현재가", f"₩{curr_price:,.0f}", f"전일대비: {(curr_price - prev_price):,.0f}원")
        c2.metric("평균단가 / 수량", f"₩{item['buy_price']:,.0f} / {item['quantity']}주")
        c3.metric("수익률", f"{ret_rate:,.2f}%", f"평가손익: ₩{profit:,.0f}")
        c4.metric("현재 평가액", f"₩{curr_val:,.0f}")
        st.write("") 
        
    st.divider()
    
    # 3. 총 자산 요약
    st.header("💰 총 자산 요약")
    grand_total = krw_balance + (usd_balance * curr_usd) + total_stock_value
    total_profit = total_stock_value - total_invested
    total_return_rate = (total_profit / total_invested) * 100 if total_invested > 0 else 0
    
    col_t1, col_t2 = st.columns(2)
    col_t1.metric("총 자산 평가액 (원화+달러+주식)", f"₩{grand_total:,.0f}")
    col_t2.metric("주식 총 평가손익", f"₩{total_profit:,.0f}", f"주식 총 수익률: {total_return_rate:,.2f}%")
    
    # 4. 자산 추이 그래프 (최근 3개월)
    st.divider()
    st.header("📈 최근 3개월 총 자산 변동 추이")
    
    # 날짜별 달러 환산액 + 날짜별 주식 평가액 계산
    daily_usd_val = usd_balance * history_df['USDKRW']
    daily_stock_val = sum(history_df[item['ticker']] * item['quantity'] for item in portfolio)
    
    # DataFrame에 총 자산 컬럼 추가
    history_df['총 자산(KRW)'] = krw_balance + daily_usd_val + daily_stock_val
    
    # 그래프 출력
    st.line_chart(history_df['총 자산(KRW)'])
    
else:
    st.error("데이터를 불러오지 못했습니다. 야후 파이낸스 서버 상태를 확인해 주세요.")
