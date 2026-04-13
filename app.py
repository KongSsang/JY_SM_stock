import streamlit as st
import yfinance as yf
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz
import requests
import plotly.express as px  # 👈 예쁜 그래프를 그리기 위한 라이브러리 추가됨

import config 

st.set_page_config(page_title="결혼 자금 포트폴리오", layout="wide")
st.title("💍 결혼 자금 관리 현황")

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
    sheet_history = client.open(config.SHEET_NAME).worksheet("History")
    sheet_log = client.open(config.SHEET_NAME).worksheet("Log")
    sheet_date_log = client.open(config.SHEET_NAME).worksheet("Date_Log")
except Exception as e:
    st.error(f"구글 스프레드시트 연결 오류: {e}")
    st.stop()


# ==========================================
# 📑 탭(Tab) 생성 (3개)
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 자산 대시보드", "📝 자산 변동 내역", "💕 데이트 비용"])

# ------------------------------------------
# 탭 1: 자산 대시보드
# ------------------------------------------
with tab1:
    current_usd_krw, usd_krw_change = get_exchange_rate()

    total_usd_amount = 0
    total_krw_invested_for_usd = 0

    for purchase in config.usd_purchases:
        total_usd_amount += purchase["amount"]
        total_krw_invested_for_usd += (purchase["buy_rate"] * purchase["amount"])

    avg_usd_buy_rate = total_krw_invested_for_usd / total_usd_amount if total_usd_amount > 0 else 0

    st.header("💵 현금 자산 (USD & KRW)")

    usd_current_krw = total_usd_amount * current_usd_krw
    usd_profit = usd_current_krw - total_krw_invested_for_usd
    usd_return_rate = (usd_profit / total_krw_invested_for_usd) * 100 if total_krw_invested_for_usd > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("보유 원화 (KRW)", f"₩{config.krw_balance:,.0f}")
    col2.metric("보유 달러 (USD)", f"${total_usd_amount:,.2f}", f"평균 환전가: ₩{avg_usd_buy_rate:,.0f}")
    col3.metric("달러 원화 환산액", f"₩{usd_current_krw:,.0f}", f"환율: ₩{current_usd_krw:,.2f} (전일대비 {usd_krw_change:,.2f}원)")
    col4.metric("달러 환차익 수익률", f"{usd_return_rate:,.2f}%", f"평가손익: ₩{usd_profit:,.0f}")

    st.divider()

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

    st.header("💰 오늘의 총 자산")
    grand_total = config.krw_balance + usd_current_krw + total_stock_value
    total_profit = total_stock_value - total_invested
    total_return_rate = (total_profit / total_invested) * 100 if total_invested > 0 else 0

    col_t1, col_t2 = st.columns(2)
    col_t1.metric("총 자산 평가액 (현금 + 주식)", f"₩{grand_total:,.0f}")
    col_t2.metric("주식 총 평가손익", f"₩{total_profit:,.0f}", f"주식 총 수익률: {total_return_rate:,.2f}%")

    st.divider()
    st.header("📈 나의 실제 총 자산 변동 추이")

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
        df_history['Date'] = pd.to_datetime(df_history['Date'])
        df_history.set_index('Date', inplace=True)
        st.line_chart(df_history['Total_Asset'])

# ------------------------------------------
# 탭 2: 자산 변동 내역 
# ------------------------------------------
with tab2:
    st.header("📝 우리 자산 변동 내역")
    st.markdown("월급, 저축, 지출 등 자산이 변동된 내역을 직접 기록하고 함께 확인할 수 있는 공간입니다.")
    
    with st.form("log_form", clear_on_submit=True):
        st.subheader("새로운 자산 내역 추가하기")
        
        c1, c2 = st.columns(2)
        log_date = c1.date_input("날짜", datetime.now(pytz.timezone('Asia/Seoul')), key="log_date")
        log_category = c2.selectbox("분류", ["입금 (저축/월급)", "출금 (지출)", "주식 매수/매도", "달러 환전", "기타"], key="log_cat")
        
        c3, c4 = st.columns(2)
        log_amount = c3.number_input("변동 금액 (원/달러 등)", step=10000, key="log_amt")
        log_memo = c4.text_input("상세 내용", placeholder="예: 4월 월급 입금, ETF 추가 매수 등", key="log_memo")
        
        submitted = st.form_submit_button("자산 기록 추가하기")
        if submitted:
            sheet_log.append_row([str(log_date), log_category, log_amount, log_memo])
            st.success("내역이 성공적으로 기록되었습니다!")
            st.rerun()

    st.divider()
    
    st.subheader("📋 전체 자산 변동 내역")
    log_records = sheet_log.get_all_records()
    
    if log_records:
        df_log = pd.DataFrame(log_records)
        st.dataframe(df_log, use_container_width=True, hide_index=True)
    else:
        st.info("아직 기록된 내역이 없습니다. 위의 폼에서 첫 기록을 남겨보세요!")

# ------------------------------------------
# 탭 3: 데이트 비용 통계 및 기록
# ------------------------------------------
with tab3:
    st.header("💕 우리 데이트 비용 기록 및 통계")
    
    # 👇 여기서부터 with st.form 안쪽은 스페이스바 4칸이 더 들어가야 합니다!
    with st.form("date_form", clear_on_submit=True):
        st.subheader("새로운 데이트 비용 추가하기")
        
        c1, c2 = st.columns(2)
        date_log_date = c1.date_input("날짜", datetime.now(pytz.timezone('Asia/Seoul')), key="date_log_date")
        date_category = c2.selectbox("분류", ["식비 (식당/카페)", "문화생활 (영화/전시)", "교통/숙박", "쇼핑/선물", "데이트 통장 입금", "기타"], key="date_cat")
        
        c3, c4 = st.columns(2)
        date_amount = c3.number_input("금액 (원)", step=10000, key="date_amt")
        date_memo = c4.text_input("상세 내용", placeholder="예: 샤브샤브용 소고기 구입, 영화 예매 등", key="date_memo")
        
        # 👇 이 버튼 코드가 반드시 with st.form 안쪽으로 들여쓰기 되어야 에러가 안 납니다!
        submitted_date = st.form_submit_button("데이트 기록 추가하기")
        if submitted_date:
            sheet_date_log.append_row([str(date_log_date), date_category, date_amount, date_memo])
            st.success("데이트 비용 내역이 성공적으로 기록되었습니다!")
            st.rerun()

    st.divider()
    
    # === 데이트 비용 통계 및 그래프 ===
    date_log_records = sheet_date_log.get_all_records()
    
    if date_log_records:
        df_date_log = pd.DataFrame(date_log_records)
        df_date_log['날짜'] = pd.to_datetime(df_date_log['날짜'])
        df_date_log['금액'] = pd.to_numeric(df_date_log['금액'])
        df_date_log['연월'] = df_date_log['날짜'].dt.strftime('%Y-%m') # 연-월 컬럼 생성
        
        st.subheader("📊 월별 데이트 지출 통계")
        
        # 월 선택 드롭다운 (가장 최근 달이 기본값)
        month_list = sorted(df_date_log['연월'].unique(), reverse=True)
        selected_month = st.selectbox("조회할 월을 선택하세요", month_list)
        
        # 선택한 월의 데이터만 필터링
        monthly_df = df_date_log[df_date_log['연월'] == selected_month]
        
        # 입금과 지출 분리 계산
        income_df = monthly_df[monthly_df['분류'] == "데이트 통장 입금"]
        expense_df = monthly_df[monthly_df['분류'] != "데이트 통장 입금"]
        
        total_income = income_df['금액'].sum()
        total_expense = expense_df['금액'].sum()
        
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric(f"{selected_month} 총 입금액", f"₩{total_income:,.0f}")
        col_s2.metric(f"{selected_month} 총 지출액", f"₩{total_expense:,.0f}")
        col_s3.metric("해당 월 잔액 증감", f"₩{(total_income - total_expense):,.0f}")
        
        # 지출 내역이 있을 경우에만 도넛 차트(파이 차트) 출력
        if not expense_df.empty:
            expense_summary = expense_df.groupby('분류')['금액'].sum().reset_index()
            fig = px.pie(
                expense_summary, 
                values='금액', 
                names='분류', 
                hole=0.4, # 가운데가 뚫린 도넛 모양으로 설정
                title=f"{selected_month} 카테고리별 지출 비율"
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
            
        st.divider()
        
        # 전체 리스트 보여주기 (보기 좋게 문자열 변환)
        st.subheader("📋 전체 데이트 비용 내역")
        display_df = df_date_log.copy()
        display_df['날짜'] = display_df['날짜'].dt.strftime('%Y-%m-%d')
        st.dataframe(display_df[['날짜', '분류', '금액', '내용']], use_container_width=True, hide_index=True)
        
    else:
        st.info("아직 기록된 내역이 없습니다. 위의 폼에서 첫 데이트 기록을 남겨보세요!")
