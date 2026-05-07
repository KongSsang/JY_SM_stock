import streamlit as st
import yfinance as yf
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz
import requests
import plotly.express as px
from streamlit_lottie import st_lottie  
from bs4 import BeautifulSoup 
import calendar 

st.set_page_config(page_title="결혼 자금 포트폴리오", page_icon="💍", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Gowun+Dodum&display=swap');
    .stApp, .stMarkdown, p, h1, h2, h3, h4, h5, h6, label, .stMetric, button { font-family: 'Gowun Dodum', sans-serif !important; }
    [data-testid="stExpanderIcon"], .st-emotion-cache-1p3m0jg, i { font-family: "Source Sans Pro", sans-serif !important; }
    .stApp { background-color: #FAFAFA !important; }
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 700 !important; }
    del { color: #999; }
</style>
""", unsafe_allow_html=True)

# === 유틸리티 함수 ===
def is_us_stock(ticker):
    """영문이 포함되어 있으면 미국 주식으로 판단"""
    return any(c.isalpha() for c in str(ticker))

@st.cache_data(ttl=60)
def get_exchange_rate():
    """환율 정보 (실시간 환산용)"""
    try:
        hist = yf.Ticker("KRW=X").history(period='1d')
        return float(hist['Close'].iloc[-1])
    except: return 1350.0

# === 데이터 수집 엔진 (한국/미국 통합) ===
@st.cache_data(ttl=30) 
def fetch_realtime_price(ticker_symbol):
    """티커 종류에 따라 네이버 또는 yfinance에서 가격을 가져옵니다."""
    ticker_str = str(ticker_symbol).strip()
    
    if is_us_stock(ticker_str):
        # --- 미국 주식 (yfinance) ---
        try:
            stock = yf.Ticker(ticker_str)
            # 장중 실시간 데이터가 없을 경우를 대비해 1일치 데이터를 가져옵니다.
            hist = stock.history(period="2d")
            if len(hist) >= 1:
                curr_price = float(hist['Close'].iloc[-1])
                # 전일 대비 변동액
                price_change = curr_price - float(hist['Close'].iloc[-2]) if len(hist) >= 2 else 0.0
                return curr_price, price_change, "USD"
            return None, None, None
        except: return None, None, None
    else:
        # --- 한국 주식 (네이버 크롤링) ---
        try:
            code = ticker_str.split('.')[0]
            url = f"https://finance.naver.com/item/main.naver?code={code}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            price_tag = soup.select_one(".no_today .blind")
            if not price_tag: return None, None, None
            curr_price = int(price_tag.text.replace(',', ''))
            diff_tag = soup.select_one(".no_exday .blind")
            diff_val = int(diff_tag.text.replace(',', ''))
            em_class = soup.select_one(".no_exday em")
            if em_class and 'no_down' in em_class.get('class', []):
                diff_val = -diff_val
            return float(curr_price), float(diff_val), "KRW"
        except: return None, None, None

# ==========================================
# 🔑 구글 시트 연결
# ==========================================
SHEET_NAME = "Asset_history"
@st.cache_resource
def init_connection():
    creds_dict = json.loads(st.secrets["google_key"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

try:
    client = init_connection()
    sheet_history = client.open(SHEET_NAME).worksheet("History")
    sheet_log = client.open(SHEET_NAME).worksheet("Log")
    sheet_date_log = client.open(SHEET_NAME).worksheet("Date_Log")
    sheet_portfolio = client.open(SHEET_NAME).worksheet("Portfolio")
    sheet_cash = client.open(SHEET_NAME).worksheet("Cash") 
    sheet_savings = client.open(SHEET_NAME).worksheet("Savings") 
except Exception as e:
    st.error(f"구글 스프레드시트 연결 오류: {e}")
    st.stop()

# 데이터 로드
portfolio_records = sheet_portfolio.get_all_records()
cash_records = sheet_cash.get_all_records()
savings_records = sheet_savings.get_all_records()
df_cash = pd.DataFrame(cash_records)
curr_exch_rate = get_exchange_rate()

# 현금 잔고 계산
krw_balance = 0
usd_cash_total = 0
usd_row_indices = [] # 달러 잔고가 있는 행들
krw_row_idx = 2

if not df_cash.empty:
    # 원화
    krw_df = df_cash[df_cash['Type'] == 'KRW']
    if not krw_df.empty:
        krw_balance = float(krw_df['Amount'].iloc[0])
        krw_row_idx = int(krw_df.index[0]) + 2
    # 달러
    usd_df = df_cash[df_cash['Type'] == 'USD']
    usd_cash_total = usd_df['Amount'].sum()
    usd_row_indices = (usd_df.index + 2).tolist()

# === 🏦 적금 계산 로직 (기존 유지) ===
today_dt = pd.to_datetime(datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d'))
total_active_savings = 0
for row in savings_records:
    if row['status'] == '진행중':
        start_dt, end_dt = pd.to_datetime(row['start_date']), pd.to_datetime(row['end_date'])
        target_dt = min(end_dt, today_dt)
        # (간략화된 계산 함수 - 기존 코드 참고)
        c_year, c_month, cnt = start_dt.year, start_dt.month, 0
        while True:
            d_date = pd.Timestamp(year=c_year, month=c_month, day=min(row['deposit_day'], calendar.monthrange(c_year, c_month)[1]))
            if d_date >= end_dt or d_date > target_dt: break
            if d_date >= start_dt: cnt += 1
            c_month += 1
            if c_month > 12: c_month = 1; c_year += 1
        total_active_savings += (cnt * row['monthly_amount'])

# ==========================================
# 📊 화면 구성
# ==========================================
tab1, tab2, tab4, tab3 = st.tabs(["📊 자산 대시보드", "📝 자산 변동", "🏦 적금", "💕 데이트 비용"])

with tab1:
    with st.container(border=True):
        st.subheader("💵 현금 및 적금 자산")
        usd_in_krw = usd_cash_total * curr_exch_rate
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("보유 원화", f"₩{krw_balance:,.0f}")
        c2.metric("적금 누적액", f"₩{total_active_savings:,.0f}")
        c3.metric("보유 달러", f"${usd_cash_total:,.2f}")
        c4.metric("달러 원화 환산", f"₩{usd_in_krw:,.0f}", f"환율: {curr_exch_rate:,.1f}")

    # 주식 섹션
    total_stock_val_krw = 0
    total_invested_krw = 0
    total_daily_profit_krw = 0
    stock_list = []

    for item in portfolio_records:
        price, change, currency = fetch_realtime_price(item["ticker"])
        if price:
            # 원화 환산 로직
            multiplier = curr_exch_rate if currency == "USD" else 1.0
            
            invested = item["buy_price"] * item["quantity"] * multiplier
            current_val = price * item["quantity"] * multiplier
            daily_profit = change * item["quantity"] * multiplier
            
            total_stock_val_krw += current_val
            total_invested_krw += invested
            total_daily_profit_krw += daily_profit
            
            stock_list.append({
                "name": item["name"], "ticker": item["ticker"], "price": price, "change": change, 
                "currency": currency, "quantity": item["quantity"], "buy_price": item["buy_price"],
                "val_krw": current_val, "profit_krw": current_val - invested
            })

    with st.container(border=True):
        st.subheader("📈 주식 자산 (KRW 합산)")
        total_profit = total_stock_val_krw - total_invested_krw
        profit_rate = (total_profit / total_invested_krw * 100) if total_invested_krw > 0 else 0
        
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("총 투자 원금", f"₩{total_invested_krw:,.0f}")
        sc2.metric("총 평가액", f"₩{total_stock_val_krw:,.0f}")
        sc3.metric("누적 평가손익", f"₩{total_profit:,.0f}", f"{profit_rate:,.2f}%")
        
        with st.expander("👉 보유 종목 상세 보기", expanded=False):
            for s in stock_list:
                st.markdown(f"**🔹 {s['name']} ({s['ticker']})**")
                cc1, cc2, cc3, cc4 = st.columns(4)
                unit = "$" if s['currency'] == "USD" else "₩"
                cc1.metric("현재가", f"{unit}{s['price']:,.2f}", f"{s['change']:,.2f}")
                cc2.metric("평단가", f"{unit}{s['buy_price']:,.2f}")
                cc3.metric("보유수량", f"{s['quantity']}주")
                cc4.metric("평가액(원화)", f"₩{s['val_krw']:,.0f}")

    # 총 자산
    with st.container(border=True):
        st.subheader("💰 오늘의 총 자산")
        grand_total = krw_balance + total_active_savings + usd_in_krw + total_stock_val_krw
        tc1, tc2 = st.columns(2)
        tc1.metric("현금+적금+주식 합계", f"₩{grand_total:,.0f}")
        
        yesterday_val = total_stock_val_krw - total_daily_profit_krw
        daily_rate = (total_daily_profit_krw / yesterday_val * 100) if yesterday_val > 0 else 0
        tc2.metric("오늘의 주식 손익", f"₩{total_daily_profit_krw:,.0f}", f"{daily_rate:,.2f}%")

# ------------------------------------------
# 📝 자산 변동 (미국 주식 매수 로직 추가)
# ------------------------------------------
with tab2:
    st.subheader("📝 자산 변동 기록")
    mode = st.radio("기록 종류", ["💰 원화 입출금", "💵 달러 환전", "📈 주식 매수"], horizontal=True)
    
    if mode == "📈 주식 매수":
        with st.form("buy_stock_form", clear_on_submit=True):
            st.info("💡 티커에 영문이 포함되면(예: PLTR) 달러 잔고에서, 숫자면 원화 잔고에서 차감됩니다.")
            c1, c2 = st.columns(2)
            b_name = c1.text_input("종목명")
            b_ticker = c2.text_input("티커 (예: 005930 또는 PLTR)")
            c3, c4, c5 = st.columns(3)
            b_qty = c3.number_input("수량", min_value=1, step=1)
            b_price = c4.number_input("매수 단가 (해당 통화 기준)", min_value=0.0, step=0.1)
            b_date = c5.date_input("매수일")
            
            if st.form_submit_button("주식 매수 기록하기", use_container_width=True):
                total_cost = b_qty * b_price
                
                if is_us_stock(b_ticker):
                    # --- 미국 주식 매수 로직 ---
                    if usd_cash_total < total_cost:
                        st.error(f"달러 잔고가 부족합니다! (필요: ${total_cost:,.2f} / 보유: ${usd_cash_total:,.2f})")
                    else:
                        # 첫 번째 달러 행에서 차감 (간소화된 로직)
                        new_usd_bal = usd_cash_total - total_cost
                        sheet_cash.update_cell(usd_row_indices[0], 2, new_usd_bal)
                        sheet_portfolio.append_row([b_name, b_ticker, b_qty, b_price])
                        sheet_log.append_row([str(b_date), "주식 매수(USD)", total_cost, f"{b_name} {b_qty}주 매수"])
                        st.toast(f"달러 잔고에서 ${total_cost:,.2f} 차감 완료! 🇺🇸", icon="✅")
                        st.rerun()
                else:
                    # --- 한국 주식 매수 로직 ---
                    if krw_balance < total_cost:
                        st.error(f"원화 잔고가 부족합니다! (필요: ₩{total_cost:,.0f} / 보유: ₩{krw_balance:,.0f})")
                    else:
                        sheet_cash.update_cell(krw_row_idx, 2, krw_balance - total_cost)
                        sheet_portfolio.append_row([b_name, b_ticker, b_qty, b_price])
                        sheet_log.append_row([str(b_date), "주식 매수(KRW)", total_cost, f"{b_name} {b_qty}주 매수"])
                        st.toast(f"원화 잔고에서 ₩{total_cost:,.0f} 차감 완료! 🇰🇷", icon="✅")
                        st.rerun()
    # (원화 입출금, 달러 환전 폼은 기존과 동일)
