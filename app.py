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

# ============================================================
# 페이지 기본 설정 & 글로벌 스타일
# ============================================================
st.set_page_config(
    page_title="우리의 결혼 자금 포트폴리오",
    page_icon="💍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Gowun+Dodum&family=Noto+Sans+KR:wght@400;500;700&display=swap');

    /* ---- 기본 폰트 ---- */
    html, body, .stApp, .stMarkdown, p, h1, h2, h3, h4, h5, h6,
    label, .stMetric, button, input, textarea, select {
        font-family: 'Gowun Dodum', 'Noto Sans KR', sans-serif !important;
    }
    [data-testid="stExpanderIcon"], i {
        font-family: "Source Sans Pro", sans-serif !important;
    }

    /* ---- 전체 배경: 따뜻한 크림+핑크 그라데이션 ---- */
    .stApp {
        background:
            radial-gradient(circle at 0% 0%, #FFE5EC 0%, transparent 40%),
            radial-gradient(circle at 100% 0%, #E0E7FF 0%, transparent 40%),
            #FFF8FA !important;
    }

    /* ---- 메인 컨테이너 폭 정리 ---- */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 4rem !important;
        max-width: 1200px;
    }

    /* ---- 히어로 헤더 ---- */
    .hero-card {
        background: linear-gradient(135deg, #FF6B9D 0%, #C44569 50%, #786FA6 100%);
        padding: 2rem 2.5rem;
        border-radius: 20px;
        color: white;
        box-shadow: 0 10px 30px rgba(196, 69, 105, 0.25);
        margin-bottom: 1.5rem;
    }
    .hero-card h1 {
        color: white !important;
        font-size: 2rem !important;
        margin: 0 !important;
        font-weight: 700 !important;
    }
    .hero-card p {
        color: rgba(255, 255, 255, 0.9) !important;
        margin: 0.4rem 0 0 0 !important;
        font-size: 0.95rem;
    }

    /* ---- 카드형 컨테이너 ---- */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: white;
        border-radius: 16px !important;
        border: 1px solid #F3E8EE !important;
        box-shadow: 0 4px 12px rgba(196, 69, 105, 0.06);
        padding: 0.5rem 0.25rem;
    }

    /* ---- 메트릭 ---- */
    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        color: #2D3436 !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #6B6B6B !important;
        font-weight: 500 !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.8rem !important;
    }

    /* ---- 탭 스타일 ---- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: rgba(255, 255, 255, 0.6);
        padding: 6px;
        border-radius: 14px;
        border: 1px solid #F3E8EE;
    }
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        padding: 0 18px;
        background: transparent;
        border-radius: 10px;
        font-weight: 600;
        color: #6B6B6B;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(196, 69, 105, 0.06);
        color: #C44569;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #FF6B9D, #C44569) !important;
        color: white !important;
        box-shadow: 0 4px 10px rgba(196, 69, 105, 0.25);
    }

    /* ---- 버튼 ---- */
    .stButton > button, .stFormSubmitButton > button {
        background: linear-gradient(135deg, #FF6B9D, #C44569);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.2s ease;
        box-shadow: 0 2px 6px rgba(196, 69, 105, 0.2);
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(196, 69, 105, 0.3);
        color: white;
    }

    /* ---- 입력 필드 ---- */
    [data-baseweb="input"], [data-baseweb="select"] {
        border-radius: 10px !important;
    }

    /* ---- 종목 카드 ---- */
    .stock-card {
        background: linear-gradient(135deg, #ffffff 0%, #FDF7FA 100%);
        border: 1px solid #F3E8EE;
        border-radius: 14px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 2px 6px rgba(196, 69, 105, 0.05);
    }
    .stock-card-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #2D3436;
        margin-bottom: 0.3rem;
    }
    .stock-card-ticker {
        font-size: 0.78rem;
        color: #999;
        font-weight: 500;
    }
    .profit-up { color: #E84393 !important; font-weight: 600; }
    .profit-down { color: #0984E3 !important; font-weight: 600; }

    /* ---- 적금 진행 바 컨테이너 ---- */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #FF6B9D, #C44569) !important;
    }

    /* ---- 만기 완료 (취소선) ---- */
    del { color: #BBB; }

    /* ---- 데이터프레임 ---- */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 유틸 함수
# ============================================================
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def is_us_stock(ticker):
    base_ticker = str(ticker).split('.')[0]
    return any(c.isalpha() for c in base_ticker)


@st.cache_data(ttl=60)
def get_exchange_rate():
    try:
        hist = yf.Ticker("KRW=X").history(period='1d')
        return float(hist['Close'].iloc[-1])
    except Exception:
        return 1350.0


@st.cache_data(ttl=30)
def fetch_realtime_price(ticker_symbol):
    ticker_str = str(ticker_symbol).strip()

    if is_us_stock(ticker_str):
        try:
            stock = yf.Ticker(ticker_str)
            hist = stock.history(period="2d")
            if len(hist) >= 1:
                curr_price = float(hist['Close'].iloc[-1])
                price_change = curr_price - float(hist['Close'].iloc[-2]) if len(hist) >= 2 else 0.0
                return curr_price, price_change, "USD"
            return None, None, None
        except Exception:
            return None, None, None
    else:
        try:
            code = ticker_str.split('.')[0]
            url = f"https://finance.naver.com/item/main.naver?code={code}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            price_tag = soup.select_one(".no_today .blind")
            if not price_tag:
                return None, None, None
            curr_price = int(price_tag.text.replace(',', ''))
            diff_tag = soup.select_one(".no_exday .blind")
            diff_val = int(diff_tag.text.replace(',', ''))
            em_class = soup.select_one(".no_exday em")
            if em_class and 'no_down' in em_class.get('class', []):
                diff_val = -diff_val
            return float(curr_price), float(diff_val), "KRW"
        except Exception:
            return None, None, None


@st.cache_resource
def init_connection():
    creds_dict = json.loads(st.secrets["google_key"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)


def format_log_amount(val):
    if pd.isna(val) or val == '' or val is None:
        return ""
    if isinstance(val, (int, float)):
        return f"₩{val:,.0f}"
    s = str(val).strip()
    try:
        num = float(s.replace(',', ''))
        return f"₩{num:,.0f}"
    except ValueError:
        pass
    digits = ''.join(c for c in s if c.isdigit() or c == '.')
    if not digits:
        return s
    try:
        num = float(digits)
    except ValueError:
        return s
    if '달러' in s or '$' in s or 'USD' in s.upper():
        return f"${num:,.2f}"
    if '원' in s or '₩' in s or 'KRW' in s.upper():
        return f"₩{num:,.0f}"
    return s


def update_usd_cash_total(sheet_cash, usd_row_indices, new_total, latest_rate=None):
    if usd_row_indices:
        sheet_cash.update_cell(usd_row_indices[0], 2, float(new_total))
        if latest_rate is not None:
            sheet_cash.update_cell(usd_row_indices[0], 3, float(latest_rate))
        for r_idx in usd_row_indices[1:]:
            sheet_cash.update_cell(r_idx, 2, 0)
    else:
        sheet_cash.append_row(['USD', float(new_total), float(latest_rate or 0)])


# ============================================================
# 헤더 (히어로 섹션)
# ============================================================
lottie_heart = load_lottieurl("https://lottie.host/0a300676-9ceb-4f2f-87a1-4321fb9669ce/IkBGyzReWa.json")

st.markdown(
    """
    <div class="hero-card">
        <h1>💍 우리의 결혼 자금 & 데이트 관리</h1>
        <p>함께 모으고, 함께 쓰고, 함께 그려가는 우리의 자산 이야기</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 시트 연결
# ============================================================
SHEET_NAME = "Asset_history"

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

portfolio_records = sheet_portfolio.get_all_records()
cash_records = sheet_cash.get_all_records()
savings_records = sheet_savings.get_all_records()

df_cash = pd.DataFrame(cash_records)
curr_exch_rate = get_exchange_rate()

krw_balance = 0.0
usd_cash_total = 0.0
usd_row_indices = []
krw_row_idx = 2

if not df_cash.empty:
    df_cash['Amount'] = pd.to_numeric(df_cash['Amount'], errors='coerce').fillna(0)

    krw_df = df_cash[df_cash['Type'] == 'KRW']
    if not krw_df.empty:
        krw_balance = float(krw_df['Amount'].iloc[0])
        krw_row_idx = int(krw_df.index[0]) + 2

    usd_df = df_cash[df_cash['Type'] == 'USD']
    usd_cash_total = float(usd_df['Amount'].sum())
    usd_row_indices = (usd_df.index + 2).tolist()


# ============================================================
# 적금 계산
# ============================================================
today_dt = pd.to_datetime(datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d'))
total_active_savings = 0
savings_render_data = []


def count_deposits(start_dt, target_dt, end_dt, day):
    c_year, c_month = start_dt.year, start_dt.month
    cnt = 0
    while True:
        last_day = calendar.monthrange(c_year, c_month)[1]
        d_day = min(day, last_day)
        d_date = pd.Timestamp(year=c_year, month=c_month, day=d_day)

        if d_date >= end_dt:
            break
        if d_date > target_dt:
            break
        if d_date >= start_dt:
            cnt += 1

        c_month += 1
        if c_month > 12:
            c_month = 1
            c_year += 1
    return cnt


for idx, row in enumerate(savings_records):
    start_dt = pd.to_datetime(row['start_date'])
    end_dt = pd.to_datetime(row['end_date'])

    if row['status'] == '진행중':
        target_dt = min(end_dt, today_dt)
        passed_deposits = count_deposits(start_dt, target_dt, end_dt, row['deposit_day'])
        total_expected_deposits = count_deposits(start_dt, end_dt, end_dt, row['deposit_day'])

        accumulated_amt = passed_deposits * row['monthly_amount']
        total_active_savings += accumulated_amt
        is_matured = today_dt >= end_dt

        savings_render_data.append({
            "row_idx": idx + 2, "item": row, "accumulated": accumulated_amt,
            "passed_deposits": passed_deposits, "total_expected": total_expected_deposits,
            "is_matured": is_matured
        })
    else:
        savings_render_data.append({
            "row_idx": idx + 2, "item": row, "accumulated": 0, "is_matured": True
        })


# ============================================================
# 탭 구성
# ============================================================
tab1, tab2, tab4, tab3 = st.tabs([
    "📊 자산 대시보드", "📝 자산 변동", "🏦 적금", "💕 데이트 비용"
])


# ============================================================
# Tab 1: 자산 대시보드
# ============================================================
with tab1:
    with st.container(border=True):
        st.subheader("💵 현금 및 적금 자산")
        usd_in_krw = usd_cash_total * curr_exch_rate
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("보유 원화", f"₩{krw_balance:,.0f}")
        c2.metric("적금 누적액", f"₩{total_active_savings:,.0f}")
        c3.metric("보유 달러", f"${usd_cash_total:,.2f}")
        c4.metric("달러 원화 환산", f"₩{usd_in_krw:,.0f}", f"환율: {curr_exch_rate:,.1f}")

    total_stock_val_krw = 0
    total_invested_krw = 0
    total_daily_profit_krw = 0
    stock_list = []
    failed_tickers = []

    for item in portfolio_records:
        price, change, currency = fetch_realtime_price(item["ticker"])
        if price:
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
                "val_krw": current_val, "profit_krw": current_val - invested,
                "profit_rate": ((current_val - invested) / invested * 100) if invested > 0 else 0
            })
        else:
            failed_tickers.append(f"{item.get('name', '')}({item.get('ticker', '')})")

    with st.container(border=True):
        st.subheader("📈 주식 자산 (KRW 합산)")

        if failed_tickers:
            st.warning(f"⚠️ 가격 조회 실패: {', '.join(failed_tickers)} — 잠시 후 다시 시도해주세요.")

        total_profit = total_stock_val_krw - total_invested_krw
        profit_rate = (total_profit / total_invested_krw * 100) if total_invested_krw > 0 else 0

        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("총 투자 원금", f"₩{total_invested_krw:,.0f}")
        sc2.metric("총 평가액", f"₩{total_stock_val_krw:,.0f}")
        sc3.metric("누적 평가손익", f"₩{total_profit:,.0f}", f"{profit_rate:,.2f}%")

        with st.expander("👉 보유 종목 상세 보기", expanded=False):
            if not stock_list:
                st.caption("보유 중인 종목이 없습니다.")
            else:
                for i in range(0, len(stock_list), 2):
                    cols = st.columns(2)
                    for j, col in enumerate(cols):
                        if i + j < len(stock_list):
                            s = stock_list[i + j]
                            unit = "$" if s['currency'] == "USD" else "₩"
                            change_class = "profit-up" if s['change'] >= 0 else "profit-down"
                            change_arrow = "▲" if s['change'] >= 0 else "▼"
                            profit_class = "profit-up" if s['profit_krw'] >= 0 else "profit-down"

                            with col:
                                st.markdown(f"""
                                <div class="stock-card">
                                    <div class="stock-card-title">🔹 {s['name']}</div>
                                    <div class="stock-card-ticker">{s['ticker']} · {s['quantity']}주</div>
                                    <div style="display:flex; justify-content:space-between; margin-top:0.6rem;">
                                        <div>
                                            <div style="font-size:0.75rem; color:#999;">현재가</div>
                                            <div style="font-size:1.1rem; font-weight:700;">{unit}{s['price']:,.2f}</div>
                                            <div class="{change_class}" style="font-size:0.85rem;">
                                                {change_arrow} {abs(s['change']):,.2f}
                                            </div>
                                        </div>
                                        <div style="text-align:right;">
                                            <div style="font-size:0.75rem; color:#999;">평가액 (₩)</div>
                                            <div style="font-size:1.1rem; font-weight:700;">₩{s['val_krw']:,.0f}</div>
                                            <div class="{profit_class}" style="font-size:0.85rem;">
                                                {s['profit_rate']:+.2f}%
                                            </div>
                                        </div>
                                    </div>
                                    <div style="border-top:1px dashed #F3E8EE; margin-top:0.6rem; padding-top:0.4rem;
                                                font-size:0.78rem; color:#888;">
                                        평단가 {unit}{s['buy_price']:,.2f}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

    with st.container(border=True):
        st.subheader("💰 오늘의 총 자산")
        grand_total = krw_balance + total_active_savings + usd_in_krw + total_stock_val_krw
        tc1, tc2 = st.columns(2)
        tc1.metric("현금+적금+주식 합계", f"₩{grand_total:,.0f}")
        yesterday_val = total_stock_val_krw - total_daily_profit_krw
        daily_rate = (total_daily_profit_krw / yesterday_val * 100) if yesterday_val > 0 else 0
        tc2.metric("오늘의 주식 손익", f"₩{total_daily_profit_krw:,.0f}", f"{daily_rate:,.2f}%")

    kst = pytz.timezone('Asia/Seoul')
    today_str = datetime.now(kst).strftime('%Y-%m-%d')
    records = sheet_history.get_all_records()
    df_history = pd.DataFrame(records)

    if df_history.empty or today_str not in df_history['Date'].astype(str).values:
        sheet_history.append_row([today_str, float(grand_total)])
        records = sheet_history.get_all_records()
        df_history = pd.DataFrame(records)
    else:
        match = df_history.index[df_history['Date'].astype(str) == today_str]
        if len(match) > 0:
            today_idx = int(match[0])
            row_idx = today_idx + 2
            sheet_history.update_cell(row_idx, 2, float(grand_total))
            df_history.at[today_idx, 'Total_Asset'] = float(grand_total)

    if not df_history.empty:
        st.markdown("##### 📊 총 자산 변동 추이")
        df_history['Date'] = pd.to_datetime(df_history['Date'])
        df_history['Total_Asset'] = pd.to_numeric(df_history['Total_Asset'], errors='coerce')
        df_history = df_history.dropna(subset=['Total_Asset']).sort_values('Date')

        y_min = float(df_history['Total_Asset'].min())
        y_max = float(df_history['Total_Asset'].max())
        y_range = y_max - y_min
        if y_range == 0:
            y_pad = max(y_max * 0.05, 1)
        else:
            y_pad = y_range * 0.15
        yaxis_range = [y_min - y_pad, y_max + y_pad]

        fig_history = px.area(
            df_history, x='Date', y='Total_Asset',
            color_discrete_sequence=['#C44569']
        )
        fig_history.update_traces(
            fill='tozeroy',
            fillcolor='rgba(196, 69, 105, 0.15)',
            line=dict(width=2.5),
            mode='lines+markers',
            marker=dict(size=6, color='#C44569'),
            hovertemplate='%{x|%Y-%m-%d}<br>₩%{y:,.0f}<extra></extra>',
        )
        fig_history.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            xaxis_title=None, yaxis_title=None,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            height=300,
            yaxis=dict(
                gridcolor='#F3E8EE',
                tickformat=',.0f',
                range=yaxis_range,
            ),
            xaxis=dict(gridcolor='#F3E8EE'),
        )
        st.plotly_chart(fig_history, use_container_width=True)


# ============================================================
# Tab 2: 자산 변동 기록
# ============================================================
with tab2:
    st.subheader("📝 자산 변동 기록")
    mode = st.radio(
        "기록 종류",
        # 🌟 여기에 '주식 매도' 항목이 새롭게 추가되었습니다!
        ["💰 원화 입출금", "💵 달러 환전", "📈 주식 매수", "📉 주식 매도"],
        horizontal=True
    )

    if mode == "💰 원화 입출금":
        with st.form("krw_log_form", clear_on_submit=True, border=True):
            c1, c2 = st.columns(2)
            log_date = c1.date_input("날짜", datetime.now(pytz.timezone('Asia/Seoul')), key="k_date")
            inout_type = c2.selectbox("분류", ["입금 (저축/월급 등)", "출금 (지출)"], key="k_cat")
            c3, c4 = st.columns(2)
            log_amount = c3.number_input("금액 (원)", step=10000, key="k_amt")
            log_memo = c4.text_input("메모", placeholder="예: 이번 달 결혼 자금 저축", key="k_memo")

            if st.form_submit_button("💾 기록 저장하기", use_container_width=True):
                new_krw = krw_balance + log_amount if "입금" in inout_type else krw_balance - log_amount
                sheet_cash.update_cell(krw_row_idx, 2, new_krw)
                sheet_log.append_row([str(log_date), inout_type, log_amount, log_memo])
                st.toast('내역이 성공적으로 저장되었습니다! 💾', icon='✅')
                st.rerun()

    elif mode == "💵 달러 환전":
        with st.form("usd_log_form", clear_on_submit=True, border=True):
            c1, c2 = st.columns(2)
            usd_date = c1.date_input("날짜", datetime.now(pytz.timezone('Asia/Seoul')), key="u_date")
            usd_amount = c2.number_input("환전 달러 (USD)", step=100.0, format="%.2f", key="u_amt")
            c3, c4 = st.columns(2)
            exch_rate = c3.number_input("적용 환율 (원/달러)", step=1.0, format="%.2f", key="u_rate")
            usd_memo = c4.text_input("메모", placeholder="예: 신혼여행 대비 환전", key="u_memo")

            if st.form_submit_button("✈️ 환전 기록하기", use_container_width=True):
                krw_spent = usd_amount * exch_rate
                sheet_cash.update_cell(krw_row_idx, 2, krw_balance - krw_spent)

                new_usd_total = usd_cash_total + usd_amount
                update_usd_cash_total(sheet_cash, usd_row_indices, new_usd_total, latest_rate=exch_rate)

                sheet_log.append_row([
                    str(usd_date), "달러 환전", krw_spent,
                    f"{usd_amount}달러 환전 (@{exch_rate:,.2f}) - {usd_memo}"
                ])
                st.toast('환전 기록이 반영되었습니다! ✈️', icon='✅')
                st.rerun()

    elif mode == "📈 주식 매수":
        with st.form("buy_stock_form", clear_on_submit=True, border=True):
            st.info("💡 티커에 영문이 포함되면(예: PLTR) 달러 잔고에서, 숫자면 원화 잔고에서 차감됩니다.")
            c1, c2 = st.columns(2)
            b_name = c1.text_input("종목명")
            b_ticker = c2.text_input("티커 (예: 005930 또는 PLTR)")
            c3, c4, c5 = st.columns(3)
            b_qty = c3.number_input("수량", min_value=1, step=1)
            b_price = c4.number_input("매수 단가 (해당 통화 기준)", min_value=0.0, step=0.1)
            b_date = c5.date_input("매수일")

            if st.form_submit_button("📊 주식 매수 기록하기", use_container_width=True):
                total_cost = b_qty * b_price
                if is_us_stock(b_ticker):
                    if usd_cash_total < total_cost:
                        st.error(f"달러 잔고가 부족합니다! (필요: ${total_cost:,.2f} / 보유: ${usd_cash_total:,.2f})")
                    else:
                        new_usd_total = usd_cash_total - total_cost
                        update_usd_cash_total(sheet_cash, usd_row_indices, new_usd_total)

                        sheet_portfolio.append_row([b_name, b_ticker, b_qty, b_price])

                        krw_converted_cost = int(total_cost * curr_exch_rate)
                        sheet_log.append_row([
                            str(b_date), "주식 매수(USD)", krw_converted_cost,
                            f"{b_name} {b_qty}주 매수 (${total_cost:,.2f} 차감)"
                        ])

                        st.toast(f"달러 잔고에서 ${total_cost:,.2f} 차감 완료! 🇺🇸", icon="✅")
                        st.rerun()
                else:
                    if krw_balance < total_cost:
                        st.error(f"원화 잔고가 부족합니다! (필요: ₩{total_cost:,.0f} / 보유: ₩{krw_balance:,.0f})")
                    else:
                        sheet_cash.update_cell(krw_row_idx, 2, krw_balance - total_cost)
                        sheet_portfolio.append_row([b_name, b_ticker, b_qty, b_price])
                        sheet_log.append_row([str(b_date), "주식 매수(KRW)", total_cost, f"{b_name} {b_qty}주 매수"])
                        st.toast(f"원화 잔고에서 ₩{total_cost:,.0f} 차감 완료! 🇰🇷", icon="✅")
                        st.rerun()

    # 🌟 새롭게 추가 및 개선된 '주식 매도' 영역 (수수료 적용, 수량 버그 방지)
    elif mode == "📉 주식 매도":
        if not portfolio_records:
            st.info("현재 보유 중인 주식이 없습니다.")
        else:
            with st.form("sell_stock_form", clear_on_submit=True, border=True):
                st.info("💡 매도 금액은 수수료를 뺀 실제 수익금이 달러/원화 잔고에 입금됩니다.")

                # 고유 식별을 위해 행 번호(idx+2)를 활용하여 드롭다운 옵션 생성
                stock_options = {
                    f"{p['name']} ({p['ticker']}) | {p['quantity']}주 보유 | 평단: {p['buy_price']}": (idx + 2, p)
                    for idx, p in enumerate(portfolio_records)
                }

                c1, c2 = st.columns(2)
                selected_stock_label = c1.selectbox("매도할 종목 선택", list(stock_options.keys()))
                s_date = c2.date_input("매도일", datetime.now(pytz.timezone('Asia/Seoul')))

                row_idx, selected_stock = stock_options[selected_stock_label]
                max_qty = selected_stock['quantity']

                # 수수료 입력칸 추가 & 수량 기본값을 '전량'으로 세팅하여 1개로 넘어가는 실수 방지
                c3, c4, c5 = st.columns(3)
                s_qty = c3.number_input("매도 수량", min_value=1, max_value=int(max_qty), value=int(max_qty), step=1)
                s_price = c4.number_input("매도 단가 (해당 통화)", min_value=0.0, step=0.1)
                s_fee = c5.number_input("수수료 (해당 통화)", min_value=0.0, step=0.01)

                if st.form_submit_button("📉 주식 매도 기록하기", use_container_width=True):
                    ticker = selected_stock['ticker']
                    name = selected_stock['name']
                    buy_price = selected_stock['buy_price']

                    # 수수료를 차감하여 최종 입금액과 순이익 계산
                    total_revenue = (s_qty * s_price) - s_fee
                    realized_profit = ((s_price - buy_price) * s_qty) - s_fee

                    # 1. 포트폴리오 시트 업데이트 (전량 매도 시 행 삭제, 일부 매도 시 수량 변경)
                    if s_qty == max_qty:
                        sheet_portfolio.delete_rows(row_idx)
                    else:
                        new_qty = max_qty - s_qty
                        sheet_portfolio.update_cell(row_idx, 3, new_qty)

                    # 2. 현금 잔고 및 로그 업데이트
                    if is_us_stock(ticker):
                        new_usd_total = usd_cash_total + total_revenue
                        update_usd_cash_total(sheet_cash, usd_row_indices, new_usd_total)

                        krw_converted_revenue = int(total_revenue * curr_exch_rate)
                        sheet_log.append_row([
                            str(s_date), "주식 매도(USD)", krw_converted_revenue,
                            f"{name} {s_qty}주 매도 (${total_revenue:,.2f} 입금, 수수료 ${s_fee:,.2f} 차감) / 차익: ${realized_profit:,.2f}"
                        ])
                        st.toast(f"달러 잔고에 ${total_revenue:,.2f} 입금 완료! 🇺🇸", icon="✅")
                    else:
                        new_krw = krw_balance + total_revenue
                        sheet_cash.update_cell(krw_row_idx, 2, new_krw)
                        sheet_log.append_row([
                            str(s_date), "주식 매도(KRW)", total_revenue,
                            f"{name} {s_qty}주 매도 (수수료 ₩{s_fee:,.0f} 차감) / 차익: ₩{realized_profit:,.0f}"
                        ])
                        st.toast(f"원화 잔고에 ₩{total_revenue:,.0f} 입금 완료! 🇰🇷", icon="✅")

                    st.rerun()
    st.write("")
    st.markdown("##### 📋 최근 기록")
    log_records = sheet_log.get_all_records()
    if log_records:
        df_log = pd.DataFrame(log_records)
        if '금액' in df_log.columns:
            df_log['금액'] = df_log['금액'].apply(format_log_amount)
        df_log = df_log.sort_values(by='날짜', ascending=False)
        st.dataframe(df_log, use_container_width=True, hide_index=True)
    else:
        st.caption("아직 기록된 자산 변동 내역이 없습니다.")


# ============================================================
# Tab 3 (적금)
# ============================================================
with tab4:
    st.subheader("🏦 우리의 적금 현황")

    with st.expander("➕ 새로운 적금 추가하기", expanded=False):
        with st.form("add_savings_form", clear_on_submit=True):
            s_name = st.text_input("적금 이름", placeholder="예: 신혼여행 적금")
            c1, c2 = st.columns(2)
            s_start = c1.date_input("적금 가입일 (첫 입금일)")
            s_end = c2.date_input("적금 만기일")
            c3, c4 = st.columns(2)
            s_amt = c3.number_input("매월 납입액 (원)", min_value=0, step=100000)
            s_day = c4.number_input("매월 이체일 (며칠?)", min_value=1, max_value=31, step=1)

            if st.form_submit_button("🏦 적금 등록", use_container_width=True):
                if not s_name:
                    st.error("적금 이름을 입력해주세요.")
                else:
                    sheet_savings.append_row([s_name, str(s_start), str(s_end), s_day, s_amt, '진행중'])
                    st.toast("적금이 등록되었습니다!", icon='🏦')
                    st.rerun()

    st.divider()

    if not savings_render_data:
        st.info("현재 등록된 적금이 없습니다. 위의 버튼을 눌러 추가해보세요! ✨")
    else:
        for data in savings_render_data:
            item = data['item']

            if item['status'] == '진행중':
                if data['is_matured']:
                    with st.container(border=True):
                        st.markdown(f"### 🎉 {item['name']} (만기 도래!)")
                        st.write(
                            f"그동안 고생 많으셨습니다! 총 **{data['total_expected']}회** 납입 완료. "
                            f"(납입 원금: ₩{data['accumulated']:,.0f})"
                        )
                        with st.form(f"mature_form_{data['row_idx']}"):
                            rec_amt = st.number_input(
                                "만기 수령액 (원금+이자)",
                                value=data['accumulated'], step=10000
                            )
                            if st.form_submit_button("💰 수령하여 현금에 합산하기"):
                                sheet_cash.update_cell(krw_row_idx, 2, krw_balance + rec_amt)
                                sheet_savings.update_cell(data['row_idx'], 6, '만기완료')
                                sheet_log.append_row([
                                    str(today_dt.date()), "적금 만기", rec_amt,
                                    f"[{item['name']}] 만기 수령"
                                ])
                                st.toast("만기액이 현금 자산에 합산되었습니다.", icon='🎉')
                                st.rerun()
                else:
                    with st.container(border=True):
                        st.markdown(f"### ⏳ {item['name']}")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("납입 횟수", f"{data['passed_deposits']} / {data['total_expected']} 회")
                        c2.metric("현재 누적액", f"₩{data['accumulated']:,.0f}")
                        c3.metric(
                            "매월 납입액",
                            f"₩{item['monthly_amount']:,.0f}",
                            f"매월 {item['deposit_day']}일 외부 이체"
                        )

                        progress = (data['passed_deposits'] / data['total_expected']) if data['total_expected'] else 0
                        st.progress(min(progress, 1.0), text=f"진행률 {progress*100:.1f}%")
                        st.caption(f"📅 만기일: {item['end_date']}")
            else:
                st.markdown(
                    f"#### <del>{item['name']} (만기 완료)</del>",
                    unsafe_allow_html=True,
                )


# ============================================================
# Tab 4 (데이트 비용)
# ============================================================
with tab3:
    st.subheader("💕 우리의 데이트 비용")

    with st.container(border=True):
        with st.form("date_form", clear_on_submit=True, border=False):
            c1, c2 = st.columns(2)
            date_log_date = c1.date_input(
                "날짜", datetime.now(pytz.timezone('Asia/Seoul')), key="date_log_date"
            )
            date_category = c2.selectbox(
                "분류",
                ["식비 (식당/카페)", "문화생활 (영화/전시)", "교통/숙박", "쇼핑/선물", "기타"],
                key="date_cat",
            )
            c3, c4 = st.columns(2)
            date_amount = c3.number_input("지출 금액 (원)", step=1000, key="date_amt")
            date_memo = c4.text_input(
                "어떤 데이트였나요?", placeholder="예: 맛있는 샤브샤브 먹은 날 🍲", key="date_memo"
            )
            if st.form_submit_button("💖 데이트 지출 기록하기", use_container_width=True):
                sheet_date_log.append_row([str(date_log_date), date_category, date_amount, date_memo])
                st.toast('즐거운 데이트 기록이 추가되었습니다! 💖', icon='💑')
                st.rerun()

    st.write("")
    date_log_records = sheet_date_log.get_all_records()

    if not date_log_records:
        st.info("아직 데이트 기록이 없네요. 첫 데이트를 기록해보세요! 💕")
    else:
        df_date_log = pd.DataFrame(date_log_records)
        df_date_log['날짜'] = pd.to_datetime(df_date_log['날짜'])
        df_date_log['금액'] = pd.to_numeric(df_date_log['금액'], errors='coerce').fillna(0)
        df_date_log = df_date_log[df_date_log['분류'] != "데이트 통장 입금"]

        if df_date_log.empty:
            st.info("표시할 데이트 기록이 없습니다.")
        else:
            df_date_log['연월'] = df_date_log['날짜'].dt.strftime('%Y-%m')
            df_date_log['주_시작일'] = df_date_log['날짜'] - pd.to_timedelta(df_date_log['날짜'].dt.weekday, unit='D')
            df_date_log['주_종료일'] = df_date_log['주_시작일'] + pd.Timedelta(days=6)
            df_date_log['주간_표시'] = (
                df_date_log['주_시작일'].dt.strftime('%m/%d')
                + " ~ "
                + df_date_log['주_종료일'].dt.strftime('%m/%d')
            )

            month_list = sorted(df_date_log['연월'].unique(), reverse=True)
            selected_month = st.selectbox("📅 조회할 월을 선택하세요", month_list)

            monthly_df = df_date_log[df_date_log['연월'] == selected_month]
            total_expense = monthly_df['금액'].sum()

            mc1, mc2 = st.columns(2)
            mc1.metric(f"{selected_month} 총 지출", f"₩{total_expense:,.0f}")
            mc2.metric(
                "평균 데이트 비용",
                f"₩{monthly_df['금액'].mean():,.0f}" if not monthly_df.empty else "₩0",
                f"총 {len(monthly_df)}건"
            )

            if not monthly_df.empty:
                expense_summary = monthly_df.groupby('분류')['금액'].sum().reset_index()
                wedding_colors = ['#FF6B9D', '#C44569', '#786FA6', '#F8B195', '#F67280']
                fig = px.pie(
                    expense_summary, values='금액', names='분류', hole=0.55,
                    color_discrete_sequence=wedding_colors,
                )
                fig.update_traces(
                    textposition='outside',
                    textinfo='percent+label',
                    marker=dict(line=dict(color='#ffffff', width=3)),
                )
                fig.update_layout(
                    showlegend=False,
                    margin=dict(t=20, b=20, l=20, r=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                )
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("##### 🗓️ 주차별 상세 내역")
            weekly_summary = (
                monthly_df.groupby(['주_시작일', '주간_표시'])['금액']
                .sum().reset_index()
                .sort_values(by='주_시작일', ascending=False)
            )
            for _, row in weekly_summary.iterrows():
                week_label = row['주간_표시']
                week_total = row['금액']
                with st.expander(f"📅 {week_label} · 합계 ₩{week_total:,.0f}", expanded=True):
                    week_data = monthly_df[monthly_df['주간_표시'] == week_label].sort_values(by='날짜', ascending=False)
                    display_week_df = week_data[['날짜', '분류', '금액', '내용']].copy()
                    display_week_df['날짜'] = display_week_df['날짜'].dt.strftime('%Y-%m-%d')
                    st.dataframe(
                        display_week_df, use_container_width=True, hide_index=True,
                        column_config={"금액": st.column_config.NumberColumn("금액", format="₩ %d")}
                    )
