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

# 페이지 여백을 줄이고 더 넓게 쓰기 위한 설정 추가
st.set_page_config(page_title="결혼 자금 포트폴리오", page_icon="💍", layout="wide", initial_sidebar_state="collapsed")
st.title("💍 우리의 결혼 자금 & 데이트 관리")
st.markdown("""
<style>
    /* 폰트 불러오기 */
    @import url('https://fonts.googleapis.com/css2?family=Gowun+Dodum&display=swap');
    
    /* 앱 내의 모든 글씨(제목, 본문, 숫자 등)에 강제로 폰트 적용 */
    html, body, [class*="css"], h1, h2, h3, h4, h5, h6, p, div, span, label, li {
        font-family: 'Gowun Dodum', sans-serif !important;
    }
</style>
""", unsafe_allow_html=True)

# === 애니메이션 불러오기 및 출력 ===
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# 귀여운 하트 애니메이션 (URL은 언제든 다른 Lottie 이미지 주소로 바꿀 수 있습니다)
lottie_heart = load_lottieurl("https://lottie.host/9e414c62-1b12-4217-bfbe-d40bafb43bc0/l5V6kU2bJ4.json")

# 제목과 애니메이션을 나란히 배치하기
col1, col2 = st.columns([1, 4])
with col1:
    if lottie_heart:
        st_lottie(lottie_heart, height=100, key="heart")
with col2:
    st.write("") # 위치를 살짝 내리기 위한 빈 줄
    st.title("💍 우리의 결혼 자금 & 데이트 관리")
# ==========================================
# ⚙️ 설정 영역
# ==========================================
SHEET_NAME = "Asset_history" 

# ==========================================
# 📡 데이터 수집
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
    sheet_history = client.open(SHEET_NAME).worksheet("History")
    sheet_log = client.open(SHEET_NAME).worksheet("Log")
    sheet_date_log = client.open(SHEET_NAME).worksheet("Date_Log")
    sheet_portfolio = client.open(SHEET_NAME).worksheet("Portfolio")
    sheet_cash = client.open(SHEET_NAME).worksheet("Cash") 
except Exception as e:
    st.error(f"구글 스프레드시트 연결 오류: {e}")
    st.stop()

portfolio_records = sheet_portfolio.get_all_records()
cash_records = sheet_cash.get_all_records()
df_cash = pd.DataFrame(cash_records)

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

# ==========================================
# 📑 탭(Tab) 생성
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 자산 대시보드", "📝 자산 변동 내역", "💕 데이트 비용"])

# ------------------------------------------
# 탭 1: 자산 대시보드
# ------------------------------------------
with tab1:
    current_usd_krw, usd_krw_change = get_exchange_rate()
    total_usd_amount = sum(p["amount"] for p in usd_purchases)
    total_krw_invested_for_usd = sum(p["buy_rate"] * p["amount"] for p in usd_purchases)
    avg_usd_buy_rate = total_krw_invested_for_usd / total_usd_amount if total_usd_amount > 0 else 0

    # UI 최적화: 카드형 컨테이너 적용
    with st.container(border=True):
        st.subheader("💵 현금 자산 (USD & KRW)")
        usd_current_krw = total_usd_amount * current_usd_krw
        usd_profit = usd_current_krw - total_krw_invested_for_usd
        usd_return_rate = (usd_profit / total_krw_invested_for_usd) * 100 if total_krw_invested_for_usd > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("보유 원화 (KRW)", f"₩{krw_balance:,.0f}")
        col2.metric("보유 달러 (USD)", f"${total_usd_amount:,.2f}", f"평균 환전가: ₩{avg_usd_buy_rate:,.0f}")
        col3.metric("달러 원화 환산액", f"₩{usd_current_krw:,.0f}", f"현재 환율: ₩{current_usd_krw:,.2f}")
        col4.metric("달러 환차익 수익률", f"{usd_return_rate:,.2f}%", f"₩{usd_profit:,.0f}")

    total_stock_value = 0
    total_invested = 0
    stock_render_data = []

    for item in portfolio_records:
        current_price, price_change = get_market_data(item["ticker"])
        if current_price is not None:
            invested = item["buy_price"] * item["quantity"]
            current_value = current_price * item["quantity"]
            profit = current_value - invested
            return_rate = (profit / invested) * 100 if invested > 0 else 0
            
            total_stock_value += current_value
            total_invested += invested
            
            stock_render_data.append({
                "item": item, "current_price": current_price, "price_change": price_change,
                "profit": profit, "return_rate": return_rate, "current_value": current_value, "error": False
            })
        else:
            stock_render_data.append({"item": item, "error": True})

    # UI 최적화: 아코디언 메뉴 깔끔하게 다듬기
    expander_title = f"📈 주식 자산 (총 평가액: ₩{total_stock_value:,.0f})"
    with st.expander(expander_title, expanded=False):
        for data in stock_render_data:
            if data["error"]:
                st.error(f"{data['item']['name']} 데이터를 불러올 수 없습니다.")
            else:
                item = data["item"]
                st.markdown(f"**🔹 {item['name']}**")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("현재가", f"₩{data['current_price']:,.0f}", f"{data['price_change']:,.0f}원")
                c2.metric("평단가 / 수량", f"₩{item['buy_price']:,.0f} / {item['quantity']}주")
                c3.metric("수익률", f"{data['return_rate']:,.2f}%", f"₩{data['profit']:,.0f}")
                c4.metric("현재 평가액", f"₩{data['current_value']:,.0f}")
                st.write("") 

    st.write("") # 간격 띄우기
    
    with st.container(border=True):
        st.subheader("💰 오늘의 총 자산")
        grand_total = krw_balance + usd_current_krw + total_stock_value
        total_profit = total_stock_value - total_invested
        total_return_rate = (total_profit / total_invested) * 100 if total_invested > 0 else 0

        col_t1, col_t2 = st.columns(2)
        col_t1.metric("총 자산 평가액 (현금 + 주식)", f"₩{grand_total:,.0f}")
        col_t2.metric("주식 총 평가손익", f"₩{total_profit:,.0f}", f"주식 수익률: {total_return_rate:,.2f}%")

    # 자산 추이 기록 및 차트
    kst = pytz.timezone('Asia/Seoul')
    today_str = datetime.now(kst).strftime('%Y-%m-%d')
    records = sheet_history.get_all_records()
    df_history = pd.DataFrame(records)

    if df_history.empty or today_str not in df_history['Date'].values:
        sheet_history.append_row([today_str, grand_total])
        records = sheet_history.get_all_records()
        df_history = pd.DataFrame(records)
    else:
        row_idx = len(records) + 1
        sheet_history.update_cell(row_idx, 2, float(grand_total))
        df_history.at[len(df_history)-1, 'Total_Asset'] = float(grand_total)

    if not df_history.empty:
        st.write("##### 📊 총 자산 변동 추이")
        df_history['Date'] = pd.to_datetime(df_history['Date'])
        df_history.set_index('Date', inplace=True)
        st.line_chart(df_history['Total_Asset'], use_container_width=True)

# ------------------------------------------
# 탭 2: 자산 변동 내역
# ------------------------------------------
with tab2:
    st.subheader("📝 우리의 자산 변동 기록장")
    form_type = st.radio("어떤 내역을 기록할까요?", ["💰 원화 입출금", "💵 달러 환전", "📈 주식 매수"], horizontal=True)
    st.write("")

    with st.container(border=True):
        if form_type == "💰 원화 입출금":
            with st.form("krw_log_form", clear_on_submit=True, border=False):
                c1, c2 = st.columns(2)
                log_date = c1.date_input("날짜", datetime.now(pytz.timezone('Asia/Seoul')), key="k_date")
                inout_type = c2.selectbox("분류", ["입금 (저축/월급 등)", "출금 (지출)"], key="k_cat")
                c3, c4 = st.columns(2)
                log_amount = c3.number_input("금액 (원)", step=10000, key="k_amt")
                log_memo = c4.text_input("메모", placeholder="예: 이번 달 결혼 자금 저축", key="k_memo")
                
                if st.form_submit_button("기록 저장하기", use_container_width=True):
                    new_krw = krw_balance + log_amount if "입금" in inout_type else krw_balance - log_amount
                    sheet_cash.update_cell(krw_row_idx, 2, new_krw)
                    sheet_log.append_row([str(log_date), inout_type, log_amount, log_memo])
                    # UI 최적화: 트렌디한 토스트 알림
                    st.toast('내역이 성공적으로 저장되었습니다! 💾', icon='✅')
                    st.rerun()

        elif form_type == "💵 달러 환전":
            with st.form("usd_log_form", clear_on_submit=True, border=False):
                st.caption("💡 원화 잔고에서 자동으로 차감됩니다.")
                c1, c2 = st.columns(2)
                usd_date = c1.date_input("날짜", datetime.now(pytz.timezone('Asia/Seoul')), key="u_date")
                usd_amount = c2.number_input("환전 달러 (USD)", step=100.0, format="%.2f", key="u_amt")
                c3, c4 = st.columns(2)
                exch_rate = c3.number_input("적용 환율 (원/달러)", step=1.0, format="%.2f", key="u_rate")
                usd_memo = c4.text_input("메모", placeholder="예: 신혼여행 대비 환전", key="u_memo")
                
                if st.form_submit_button("환전 기록하기", use_container_width=True):
                    krw_spent = usd_amount * exch_rate
                    sheet_cash.update_cell(krw_row_idx, 2, krw_balance - krw_spent)
                    sheet_cash.append_row(['USD', usd_amount, exch_rate])
                    sheet_log.append_row([str(usd_date), "달러 환전", krw_spent, f"{usd_amount}달러 환전 (@{exch_rate:,.2f}) - {usd_memo}"])
                    st.toast('환전 기록이 반영되었습니다! ✈️', icon='✅')
                    st.rerun()

        else: 
            with st.form("stock_buy_form", clear_on_submit=True, border=False):
                st.caption("💡 원화 잔고에서 매수 금액이 자동으로 차감됩니다.")
                c1, c2 = st.columns(2)
                buy_date = c1.date_input("날짜", datetime.now(pytz.timezone('Asia/Seoul')), key="s_date")
                buy_name = c2.text_input("종목명", placeholder="예: TIGER 미국S&P500", key="s_name")
                c3, c4 = st.columns(2)
                buy_ticker = c3.text_input("티커", placeholder="예: 360200.KS", key="s_ticker")
                buy_qty = c4.number_input("수량 (주)", min_value=1, step=1, key="s_qty")
                c5, c6 = st.columns(2)
                buy_price = c5.number_input("매수 단가 (원)", min_value=0, step=100, key="s_price")
                buy_memo = c6.text_input("메모", placeholder="적립식 매수", key="s_memo")
                
                if st.form_submit_button("주식 매수 기록하기", use_container_width=True):
                    if not buy_name or not buy_ticker:
                        st.error("종목명과 티커를 입력해 주세요!")
                    else:
                        total_buy_amount = buy_qty * buy_price
                        df_port = pd.DataFrame(portfolio_records)
                        
                        if not df_port.empty and buy_ticker in df_port['ticker'].values:
                            idx = df_port.index[df_port['ticker'] == buy_ticker].tolist()[0]
                            old_qty, old_price = float(df_port.at[idx, 'quantity']), float(df_port.at[idx, 'buy_price'])
                            new_qty = old_qty + buy_qty
                            new_avg_price = ((old_qty * old_price) + (buy_qty * buy_price)) / new_qty
                            sheet_portfolio.update_cell(int(idx) + 2, 3, new_qty)
                            sheet_portfolio.update_cell(int(idx) + 2, 4, new_avg_price)
                        else:
                            sheet_portfolio.append_row([buy_name, buy_ticker, buy_qty, buy_price])
                        
                        sheet_cash.update_cell(krw_row_idx, 2, krw_balance - total_buy_amount)
                        sheet_log.append_row([str(buy_date), "주식 매수", total_buy_amount, f"[{buy_name}] {buy_qty}주 매수 (@{buy_price:,.0f}원) {buy_memo}"])
                        st.toast('주식 매수 기록이 성공적으로 반영되었습니다! 📈', icon='✅')
                        st.rerun()

    st.write("")
    log_records = sheet_log.get_all_records()
    
    if log_records:
        df_log = pd.DataFrame(log_records).sort_values(by='날짜', ascending=False)
        # UI 최적화: 데이터프레임 컬럼 서식 지정 (금액에 ₩ 표시)
        st.dataframe(
            df_log, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "금액": st.column_config.NumberColumn("금액", format="₩ %d")
            }
        )
    else:
        st.info("아직 기록된 내역이 없습니다.")


# ------------------------------------------
# 탭 3: 데이트 비용 통계 및 기록
# ------------------------------------------
with tab3:
    st.subheader("💕 우리의 데이트 비용")
    
    with st.container(border=True):
        with st.form("date_form", clear_on_submit=True, border=False):
            c1, c2 = st.columns(2)
            date_log_date = c1.date_input("날짜", datetime.now(pytz.timezone('Asia/Seoul')), key="date_log_date")
            date_category = c2.selectbox("분류", ["식비 (식당/카페)", "문화생활 (영화/전시)", "교통/숙박", "쇼핑/선물", "기타"], key="date_cat")
            c3, c4 = st.columns(2)
            date_amount = c3.number_input("지출 금액 (원)", step=1000, key="date_amt")
            date_memo = c4.text_input("어떤 데이트였나요?", placeholder="예: 맛있는 샤브샤브 먹은 날 🍲", key="date_memo")
            
            if st.form_submit_button("데이트 지출 기록하기", use_container_width=True):
                sheet_date_log.append_row([str(date_log_date), date_category, date_amount, date_memo])
                st.toast('즐거운 데이트 기록이 추가되었습니다! 💖', icon='💑')
                st.rerun()

    st.write("")
    date_log_records = sheet_date_log.get_all_records()
    
    if date_log_records:
        df_date_log = pd.DataFrame(date_log_records)
        df_date_log['날짜'] = pd.to_datetime(df_date_log['날짜'])
        df_date_log['금액'] = pd.to_numeric(df_date_log['금액'])
        df_date_log = df_date_log[df_date_log['분류'] != "데이트 통장 입금"]
        
        if not df_date_log.empty:
            df_date_log['연월'] = df_date_log['날짜'].dt.strftime('%Y-%m') 
            df_date_log['주_시작일'] = df_date_log['날짜'] - pd.to_timedelta(df_date_log['날짜'].dt.weekday, unit='D')
            df_date_log['주_종료일'] = df_date_log['주_시작일'] + pd.Timedelta(days=6)
            df_date_log['주간_표시'] = df_date_log['주_시작일'].dt.strftime('%m/%d') + " ~ " + df_date_log['주_종료일'].dt.strftime('%m/%d')
            
            month_list = sorted(df_date_log['연월'].unique(), reverse=True)
            selected_month = st.selectbox("조회할 월을 선택하세요", month_list)
            
            monthly_df = df_date_log[df_date_log['연월'] == selected_month]
            total_expense = monthly_df['금액'].sum()
            
            st.metric(f"{selected_month} 총 지출액", f"₩{total_expense:,.0f}")
            
            if not monthly_df.empty:
                expense_summary = monthly_df.groupby('분류')['금액'].sum().reset_index()
                fig = px.pie(
                    expense_summary, values='금액', names='분류', hole=0.4, 
                    color_discrete_sequence=px.colors.qualitative.Pastel # 차트 색상을 부드러운 파스텔톤으로 변경
                )
                fig.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#ffffff', width=2)))
                fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
                
            st.write("##### 🗓️ 주차별 상세 내역")
            weekly_summary = monthly_df.groupby(['주_시작일', '주간_표시'])['금액'].sum().reset_index().sort_values(by='주_시작일', ascending=False)
            
            for _, row in weekly_summary.iterrows():
                week_label = row['주간_표시']
                week_total = row['금액']
                with st.expander(f"📅 {week_label} 지출 합계: ₩{week_total:,.0f}", expanded=True):
                    week_data = monthly_df[monthly_df['주간_표시'] == week_label].sort_values(by='날짜', ascending=False)
                    display_week_df = week_data[['날짜', '분류', '금액', '내용']].copy()
                    display_week_df['날짜'] = display_week_df['날짜'].dt.strftime('%Y-%m-%d')
                    st.dataframe(
                        display_week_df, 
                        use_container_width=True, hide_index=True,
                        column_config={"금액": st.column_config.NumberColumn("금액", format="₩ %d")}
                    )
        else:
            st.info("지출 내역이 없습니다.")
    else:
        st.info("아직 첫 데이트 기록이 없네요! 폼을 작성해 볼까요? ✨")
