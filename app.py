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

# 페이지 설정
st.set_page_config(page_title="결혼 자금 포트폴리오", page_icon="💍", layout="wide", initial_sidebar_state="collapsed")

# === [수정] 초강력하지만 안전한 CSS 주입 ===
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Gowun+Dodum&display=swap');
    
    /* 1. 실제 텍스트 요소에만 폰트 적용 (아이콘 제외) */
    .stApp, .stMarkdown, p, h1, h2, h3, h4, h5, h6, label, .stMetric, button {
        font-family: 'Gowun Dodum', sans-serif !important;
    }

    /* 2. 스트림릿 고유 아이콘 폰트 복구 (화살표 깨짐 방지) */
    [data-testid="stExpanderIcon"], .st-emotion-cache-1p3m0jg, i {
        font-family: "Source Sans Pro", sans-serif !important;
    }

    /* 3. 배경색 및 카드 디자인 */
    .stApp {
        background-color: #FAFAFA !important;
    }
    
    /* 4. 메트릭(숫자) 강조 및 가독성 */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# === 애니메이션 불러오기 ===
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200: return None
        return r.json()
    except: return None

lottie_heart = load_lottieurl("https://lottie.host/0a300676-9ceb-4f2f-87a1-4321fb9669ce/IkBGyzReWa.json")

# 상단 헤더 영역
col_header1, col_header2 = st.columns([1, 5])
with col_header1:
    if lottie_heart:
        st_lottie(lottie_heart, height=100, key="heart")
with col_header2:
    st.write("")
    st.title("💍 우리의 결혼 자금 & 데이트 관리")

# ==========================================
# 🔑 구글 시트 연결 및 데이터 로드
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
except Exception as e:
    st.error(f"시트 연결 오류: {e}")
    st.stop()

# 데이터 로드
portfolio_records = sheet_portfolio.get_all_records()
cash_records = sheet_cash.get_all_records()
df_cash = pd.DataFrame(cash_records)

# 현금 잔고 계산
krw_balance = 0
usd_purchases = []
krw_row_idx = 2 
if not df_cash.empty:
    krw_df = df_cash[df_cash['Type'] == 'KRW']
    if not krw_df.empty:
        krw_balance = float(krw_df['Amount'].iloc[0])
        krw_row_idx = int(krw_df.index[0]) + 2
    usd_df = df_cash[df_cash['Type'] == 'USD']
    for _, row in usd_df.iterrows():
        usd_purchases.append({"amount": float(row['Amount']), "buy_rate": float(row['Rate'])})

# 시장 데이터 수집 함수
@st.cache_data(ttl=60)
def get_market_data(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period='5d') 
        if len(hist) >= 2:
            curr = float(hist['Close'].iloc[-1])
            return curr, curr - float(hist['Close'].iloc[-2])
        return float(hist['Close'].iloc[0]), 0.0
    except: return None, None

@st.cache_data(ttl=60)
def get_exchange_rate():
    try:
        hist = yf.Ticker("KRW=X").history(period='5d')
        curr = float(hist['Close'].iloc[-1])
        return curr, curr - float(hist['Close'].iloc[-2])
    except: return 1350.0, 0.0

# ==========================================
# 📑 탭 구성
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 자산 대시보드", "📝 자산 변동 내역", "💕 데이트 비용"])

# 탭 1: 자산 대시보드
with tab1:
    curr_rate, rate_change = get_exchange_rate()
    total_usd = sum(p["amount"] for p in usd_purchases)
    total_usd_krw_spent = sum(p["buy_rate"] * p["amount"] for p in usd_purchases)
    avg_rate = total_usd_krw_spent / total_usd if total_usd > 0 else 0

    with st.container(border=True):
        st.subheader("💵 현금 자산")
        usd_val_krw = total_usd * curr_rate
        usd_profit = usd_val_krw - total_usd_krw_spent
        usd_return = (usd_profit / total_usd_krw_spent * 100) if total_usd_krw_spent > 0 else 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("원화 잔고", f"₩{krw_balance:,.0f}")
        c2.metric("달러 잔고", f"${total_usd:,.2f}", f"평균: ₩{avg_rate:,.0f}")
        c3.metric("달러 환산액", f"₩{usd_val_krw:,.0f}", f"환율: {curr_rate:,.1f}")
        c4.metric("달러 수익률", f"{usd_return:,.2f}%", f"₩{usd_profit:,.0f}")

    # 주식 계산
    total_stock_val = 0
    total_stock_invested = 0
    stock_list = []
    for item in portfolio_records:
        cp, diff = get_market_data(item["ticker"])
        if cp:
            inv = item["buy_price"] * item["quantity"]
            val = cp * item["quantity"]
            total_stock_val += val
            total_stock_invested += inv
            stock_list.append({"item": item, "cp": cp, "diff": diff, "val": val, "profit": val-inv})

    with st.expander(f"📈 주식 자산 (총 평가액: ₩{total_stock_val:,.0f})", expanded=False):
        for s in stock_list:
            st.write(f"**{s['item']['name']}**")
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("현재가", f"₩{s['cp']:,.0f}", f"{s['diff']:,.0f}")
            sc2.metric("평단/수량", f"{s['item']['buy_price']:,.0f} / {s['item']['quantity']}주")
            ret = (s['profit']/(s['item']['buy_price']*s['item']['quantity'])*100)
            sc3.metric("수익률", f"{ret:,.2f}%", f"₩{s['profit']:,.0f}")
            sc4.metric("평가액", f"₩{s['val']:,.0f}")

    with st.container(border=True):
        st.subheader("💰 오늘의 총 결혼 자금")
        grand_total = krw_balance + usd_val_krw + total_stock_val
        st.metric("합계 (현금 + 주식)", f"₩{grand_total:,.0f}")

    # 차트
    records = sheet_history.get_all_records()
    df_hist = pd.DataFrame(records)
    today = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d')
    if df_hist.empty or today not in df_hist['Date'].values:
        sheet_history.append_row([today, grand_total])
    else:
        sheet_history.update_cell(len(df_hist)+1, 2, float(grand_total))
    
    st.write("##### 📊 자산 성장 추이")
    df_hist['Date'] = pd.to_datetime(df_hist['Date'])
    st.line_chart(df_hist.set_index('Date')['Total_Asset'])

# 탭 2: 자산 변동 내역
with tab2:
    st.subheader("📝 자산 변동 기록")
    mode = st.radio("분류 선택", ["원화", "환전", "주식매수"], horizontal=True)
    
    with st.container(border=True):
        if mode == "원화":
            with st.form("f1", clear_on_submit=True, border=False):
                c1, c2, c3 = st.columns(3)
                d = c1.date_input("날짜")
                cat = c2.selectbox("구분", ["입금 (월급/저축)", "출금 (지출)"])
                amt = c3.number_input("금액", step=10000)
                memo = st.text_input("메모")
                if st.form_submit_button("저장"):
                    new_b = krw_balance + amt if "입금" in cat else krw_balance - amt
                    sheet_cash.update_cell(krw_row_idx, 2, new_b)
                    sheet_log.append_row([str(d), cat, amt, memo])
                    st.toast("저장되었습니다!")
                    st.rerun()
        
        elif mode == "환전":
            with st.form("f2", clear_on_submit=True, border=False):
                c1, c2, c3 = st.columns(3)
                d = c1.date_input("날짜")
                u_amt = c2.number_input("달러(USD)", step=10.0)
                rate = c3.number_input("환율", step=1.0)
                if st.form_submit_button("환전 완료"):
                    spent = u_amt * rate
                    sheet_cash.update_cell(krw_row_idx, 2, krw_balance - spent)
                    sheet_cash.append_row(['USD', u_amt, rate])
                    sheet_log.append_row([str(d), "환전", spent, f"{u_amt}$ 환전"])
                    st.toast("환전 기록 완료!")
                    st.rerun()
        
        else:
            with st.form("f3", clear_on_submit=True, border=False):
                c1, c2 = st.columns(2)
                name = c1.text_input("종목명")
                tk = c2.text_input("티커 (예: 005930.KS)")
                c3, c4 = st.columns(2)
                qty = c3.number_input("수량", step=1)
                prc = c4.number_input("단가", step=100)
                if st.form_submit_button("매수 저장"):
                    cost = qty * prc
                    df_p = pd.DataFrame(portfolio_records)
                    if not df_p.empty and tk in df_p['ticker'].values:
                        idx = df_p.index[df_p['ticker'] == tk][0]
                        o_qty, o_prc = df_p.at[idx, 'quantity'], df_p.at[idx, 'buy_price']
                        n_qty = o_qty + qty
                        n_prc = ((o_qty * o_prc) + cost) / n_qty
                        sheet_portfolio.update_cell(int(idx)+2, 3, n_qty)
                        sheet_portfolio.update_cell(int(idx)+2, 4, n_prc)
                    else:
                        sheet_portfolio.append_row([name, tk, qty, prc])
                    sheet_cash.update_cell(krw_row_idx, 2, krw_balance - cost)
                    sheet_log.append_row([str(datetime.now().date()), "주식매수", cost, f"{name} 매수"])
                    st.toast("주식 잔고 업데이트 완료!")
                    st.rerun()

    logs = sheet_log.get_all_records()
    if logs:
        st.dataframe(pd.DataFrame(logs).sort_values("날짜", ascending=False), use_container_width=True, hide_index=True)

# 탭 3: 데이트 비용
with tab3:
    st.subheader("💕 데이트 지출")
    with st.container(border=True):
        with st.form("f4", clear_on_submit=True, border=False):
            c1, c2, c3 = st.columns(3)
            d = c1.date_input("날짜", key="d_d")
            cat = c2.selectbox("카테고리", ["식비", "문화", "쇼핑", "기타"])
            amt = c3.number_input("금액", step=1000)
            memo = st.text_input("내용", placeholder="오늘의 추억은?")
            if st.form_submit_button("지출 추가"):
                sheet_date_log.append_row([str(d), cat, amt, memo])
                st.toast("기록되었습니다! 💖")
                st.rerun()
    
    d_logs = sheet_date_log.get_all_records()
    if d_logs:
        df_d = pd.DataFrame(d_logs)
        df_d['날짜'] = pd.to_datetime(df_d['날짜'])
        df_d['연월'] = df_d['날짜'].dt.strftime('%Y-%m')
        
        sel_m = st.selectbox("월별 보기", sorted(df_d['연월'].unique(), reverse=True))
        m_df = df_d[df_d['연월'] == sel_m]
        
        st.metric(f"{sel_m} 지출 합계", f"₩{m_df['금액'].sum():,.0f}")
        fig = px.pie(m_df, values='금액', names='카테고리', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig, use_container_width=True)
        
        # 주간 묶음
        m_df['주'] = m_df['날짜'] - pd.to_timedelta(m_df['날짜'].dt.weekday, unit='D')
        w_sums = m_df.groupby('주')['금액'].sum().reset_index().sort_values('주', ascending=False)
        for _, r in w_sums.iterrows():
            with st.expander(f"📅 {r['주'].strftime('%m/%d')} 주간 합계: ₩{r['금액']:,.0f}"):
                st.table(m_df[m_df['주'] == r['주']][['날짜', '카테고리', '금액', '내용']])
