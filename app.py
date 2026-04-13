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
    sheet_portfolio = client.open(config.SHEET_NAME).worksheet("Portfolio") # 👈 포트폴리오 시트 연결
except Exception as e:
    st.error(f"구글 스프레드시트 연결 오류: {e}")
    st.stop()

# 포트폴리오 데이터 불러오기
portfolio_records = sheet_portfolio.get_all_records()

# ==========================================
# 📑 탭(Tab) 생성
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

    # 👈 config.py가 아닌 스프레드시트에서 가져온 포트폴리오 사용
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
# 탭 2: 자산 변동 내역 (주식 매수 기능 통합)
# ------------------------------------------
with tab2:
    st.header("📝 우리 자산 변동 내역")
    
    # 입력 폼 종류 선택
    form_type = st.radio("기록할 내역의 종류를 선택하세요:", ["💰 일반 자산 변동 (입출금/환전 등)", "📈 주식 매수"], horizontal=True)
    st.write("")

    if form_type == "💰 일반 자산 변동 (입출금/환전 등)":
        with st.form("general_log_form", clear_on_submit=True):
            st.subheader("새로운 자산 내역 추가하기")
            
            c1, c2 = st.columns(2)
            log_date = c1.date_input("날짜", datetime.now(pytz.timezone('Asia/Seoul')), key="g_date")
            log_category = c2.selectbox("분류", ["입금 (저축/월급)", "출금 (지출)", "주식 매도", "달러 환전", "기타"], key="g_cat")
            
            c3, c4 = st.columns(2)
            log_amount = c3.number_input("변동 금액 (원/달러 등)", step=10000, key="g_amt")
            log_memo = c4.text_input("상세 내용", placeholder="예: 4월 월급 입금", key="g_memo")
            
            submitted = st.form_submit_button("자산 기록 추가하기")
            if submitted:
                sheet_log.append_row([str(log_date), log_category, log_amount, log_memo])
                st.success("내역이 성공적으로 기록되었습니다!")
                st.rerun()

    else: # 주식 매수 선택 시
        with st.form("stock_buy_form", clear_on_submit=True):
            st.subheader("새로운 주식 매수 기록하기")
            st.markdown("💡 *이미 보유 중인 종목의 티커를 입력하면, 기존 수량과 합산되어 평단가가 자동으로 재계산됩니다.*")
            
            c1, c2 = st.columns(2)
            buy_date = c1.date_input("매수 날짜", datetime.now(pytz.timezone('Asia/Seoul')), key="s_date")
            buy_name = c2.text_input("종목명", placeholder="예: TIGER 200", key="s_name")
            
            c3, c4 = st.columns(2)
            buy_ticker = c3.text_input("티커 (Yahoo Finance 기준)", placeholder="예: 102110.KS", key="s_ticker")
            buy_qty = c4.number_input("매수 수량 (주)", min_value=1, step=1, key="s_qty")
            
            c5, c6 = st.columns(2)
            buy_price = c5.number_input("매수 단가 (1주당 ₩)", min_value=0, step=100, key="s_price")
            buy_memo = c6.text_input("상세 내용 (선택)", placeholder="예: 매달 적립식 매수", key="s_memo")
            
            submit_stock = st.form_submit_button("주식 매수 기록 반영하기")
            
            if submit_stock:
                if not buy_name or not buy_ticker:
                    st.error("종목명과 티커를 모두 입력해 주세요!")
                else:
                    df_port = pd.DataFrame(portfolio_records)
                    
                    # 1. 포트폴리오 시트 업데이트 로직
                    if not df_port.empty and buy_ticker in df_port['ticker'].values:
                        # 기존 보유 종목인 경우 -> 평단가, 수량 재계산 후 덮어쓰기
                        idx = df_port.index[df_port['ticker'] == buy_ticker].tolist()[0]
                        row_num = int(idx) + 2 # 0-index 기반 보정 및 헤더(1행) 포함
                        
                        old_qty = float(df_port.at[idx, 'quantity'])
                        old_price = float(df_port.at[idx, 'buy_price'])
                        
                        new_qty = old_qty + buy_qty
                        new_avg_price = ((old_qty * old_price) + (buy_qty * buy_price)) / new_qty
                        
                        sheet_portfolio.update_cell(row_num, 3, new_qty)
                        sheet_portfolio.update_cell(row_num, 4, new_avg_price)
                        action_msg = f"기존 {buy_name} 종목에 추가 매수되어 평단가가 업데이트되었습니다."
                    else:
                        # 신규 종목인 경우 -> 포트폴리오 맨 아래에 새 줄 추가
                        sheet_portfolio.append_row([buy_name, buy_ticker, buy_qty, buy_price])
                        action_msg = f"신규 종목 {buy_name}이(가) 포트폴리오에 추가되었습니다."
                    
                    # 2. 일반 Log 시트에도 매수 기록 남기기 (총 매수 금액)
                    total_buy_amount = buy_qty * buy_price
                    log_memo_text = f"[{buy_name}] {buy_qty}주 매수 (@{buy_price:,.0f}원) {buy_memo}"
                    sheet_log.append_row([str(buy_date), "주식 매수", total_buy_amount, log_memo_text])
                    
                    st.success(f"성공! {action_msg}")
                    st.rerun()

    st.divider()
    
    st.subheader("📋 전체 자산 변동 내역")
    log_records = sheet_log.get_all_records()
    
    if log_records:
        df_log = pd.DataFrame(log_records)
        st.dataframe(df_log, use_container_width=True, hide_index=True)
    else:
        st.info("아직 기록된 내역이 없습니다.")


# ------------------------------------------
# 탭 3: 데이트 비용 통계 및 기록
# ------------------------------------------
with tab3:
    st.header("💕 우리 데이트 비용 기록 및 통계")
    
    with st.form("date_form", clear_on_submit=True):
        st.subheader("새로운 데이트 지출 추가하기")
        
        c1, c2 = st.columns(2)
        date_log_date = c1.date_input("날짜", datetime.now(pytz.timezone('Asia/Seoul')), key="date_log_date")
        date_category = c2.selectbox("분류", ["식비 (식당/카페)", "문화생활 (영화/전시)", "교통/숙박", "쇼핑/선물", "기타"], key="date_cat")
        
        c3, c4 = st.columns(2)
        date_amount = c3.number_input("지출 금액 (원)", step=1000, key="date_amt")
        date_memo = c4.text_input("상세 내용", placeholder="예: 샤브샤브용 소고기 구입, 영화 예매 등", key="date_memo")
        
        submitted_date = st.form_submit_button("지출 기록 추가하기")
        if submitted_date:
            sheet_date_log.append_row([str(date_log_date), date_category, date_amount, date_memo])
            st.success("데이트 지출 내역이 성공적으로 기록되었습니다!")
            st.rerun()

    st.divider()
    
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
            
            st.subheader("📊 데이트 지출 통계")
            
            month_list = sorted(df_date_log['연월'].unique(), reverse=True)
            selected_month = st.selectbox("조회할 월을 선택하세요", month_list)
            
            monthly_df = df_date_log[df_date_log['연월'] == selected_month]
            total_expense = monthly_df['금액'].sum()
            
            st.metric(f"{selected_month} 총 지출액", f"₩{total_expense:,.0f}")
            
            if not monthly_df.empty:
                expense_summary = monthly_df.groupby('분류')['금액'].sum().reset_index()
                fig = px.pie(
                    expense_summary, 
                    values='금액', 
                    names='분류', 
                    hole=0.4, 
                    title=f"{selected_month} 카테고리별 지출 비율"
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
                
            st.divider()
            
            st.subheader(f"🗓️ {selected_month} 주차별 상세 내역")
            
            weekly_summary = monthly_df.groupby(['주_시작일', '주간_표시'])['금액'].sum().reset_index()
            weekly_summary = weekly_summary.sort_values(by='주_시작일', ascending=False)
            
            for _, row in weekly_summary.iterrows():
                week_label = row['주간_표시']
                week_total = row['금액']
                
                with st.expander(f"📅 {week_label} 지출 합계: ₩{week_total:,.0f}", expanded=True):
                    week_data = monthly_df[monthly_df['주간_표시'] == week_label].sort_values(by='날짜', ascending=False)
                    display_week_df = week_data[['날짜', '분류', '금액', '내용']].copy()
                    display_week_df['날짜'] = display_week_df['날짜'].dt.strftime('%Y-%m-%d')
                    st.dataframe(display_week_df, use_container_width=True, hide_index=True)
                    
        else:
            st.info("지출 내역이 없습니다.")
    else:
        st.info("아직 기록된 내역이 없습니다. 위의 폼에서 첫 데이트 기록을 남겨보세요!")
