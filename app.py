import streamlit as st
import yfinance as yf

# --- 📱 모바일 UI 최적화 설정 ---
st.set_page_config(page_title="내 자산 포트폴리오", page_icon="💸", layout="centered")

# 커스텀 CSS 적용 (앱 느낌의 카드 디자인 및 여백 조정)
st.markdown("""
<style>
    /* 전체 배경과 폰트 최적화 */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
        max-width: 600px; /* 모바일/태블릿에 맞춘 최대 너비 */
    }
    
    /* 카드 디자인 */
    .asset-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border: 1px solid #f0f2f6;
    }
    
    /* 제목 스타일 */
    .main-title {
        text-align: center;
        font-weight: 800;
        color: #1e1e1e;
        margin-bottom: 20px;
    }
    
    /* 수익률 텍스트 색상 규칙을 위한 꼼수 (Streamlit metric 기본 의존) */
</style>
""", unsafe_allow_html=True)

st.markdown('<h2 class="main-title">📈 나의 자산 대시보드</h2>', unsafe_allow_html=True)

# --- 자산 데이터 고정 입력 ---
usd_balance = 3035.17

portfolio = [
    {"name": "TIGER 200", "ticker": "102110.KS", "quantity": 6, "buy_price": 87366},
    {"name": "TIGER 미국S&P500", "ticker": "360200.KS", "quantity": 20, "buy_price": 25005},
    {"name": "TIGER 미국나스닥100", "ticker": "133690.KS", "quantity": 3, "buy_price": 164285},
]

# --- 데이터 가져오기 함수 ---
@st.cache_data(ttl=60)
def get_market_data(ticker_symbol):
    try:
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

# --- 데이터 계산 및 렌더링 ---
current_usd_krw, usd_krw_change = get_market_data("USDKRW=X")
if current_usd_krw is None:
    current_usd_krw, usd_krw_change = 1350.0, 0.0

total_stock_value = 0
total_invested = 0

# --- 1. 총 자산 요약 (맨 위로 배치하여 한눈에 보이게) ---
st.markdown("### 💰 총 자산 요약")
summary_container = st.container()

# 개별 주식 계산 (총합을 먼저 구하기 위해 루프를 미리 돕니다)
stock_results = []
for item in portfolio:
    current_price, price_change = get_market_data(item["ticker"])
    if current_price is not None:
        invested = item["buy_price"] * item["quantity"]
        current_value = current_price * item["quantity"]
        profit = current_value - invested
        return_rate = (profit / invested) * 100 if invested > 0 else 0
        
        total_stock_value += current_value
        total_invested += invested
        
        stock_results.append({
            "name": item["name"],
            "current_price": current_price,
            "price_change": price_change,
            "buy_price": item["buy_price"],
            "quantity": item["quantity"],
            "profit": profit,
            "return_rate": return_rate,
            "current_value": current_value
        })

# 총합 계산
usd_krw_value = usd_balance * current_usd_krw
grand_total = usd_krw_value + total_stock_value
total_profit = total_stock_value - total_invested
total_return_rate = (total_profit / total_invested) * 100 if total_invested > 0 else 0

with summary_container:
    st.markdown('<div class="asset-card">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("총 자산 평가액", f"₩{grand_total:,.0f}")
    c2.metric("주식 총 손익", f"₩{total_profit:,.0f}", f"{total_return_rate:,.2f}%")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 2. 주식 상세 내역 ---
st.markdown("### 📊 보유 주식")
for res in stock_results:
    st.markdown('<div class="asset-card">', unsafe_allow_html=True)
    st.markdown(f"**{res['name']}**")
    
    # 모바일에선 2단 컬럼이 가장 깔끔합니다
    col1, col2 = st.columns(2)
    with col1:
        st.metric("현재가", f"₩{res['current_price']:,.0f}", f"전일대비 {res['price_change']:,.0f}원")
    with col2:
        st.metric("평가액 (수익률)", f"₩{res['current_value']:,.0f}", f"{res['return_rate']:,.2f}% ({res['profit']:,.0f}원)")
        
    st.caption(f"평균단가: ₩{res['buy_price']:,.0f} | 보유수량: {res['quantity']}주")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 3. 외화(달러) 내역 ---
st.markdown("### 💵 외화 자산 (USD)")
st.markdown('<div class="asset-card">', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.metric("보유 달러", f"${usd_balance:,.2f}")
with col2:
    st.metric("원화 환산액", f"₩{usd_krw_value:,.0f}", f"환율 {current_usd_krw:,.2f}원")
st.markdown('</div>', unsafe_allow_html=True)
