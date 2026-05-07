"""
Log 시트 금액 컬럼 일회성 마이그레이션 스크립트
=================================================

목적:
  Log 시트의 '금액' 컬럼은 옛날 코드(단위 포함 문자열, 예: "3035.17달러", "524200원")와
  현재 코드(순수 숫자) 데이터가 섞여 있어 합계·통계가 부정확하다.
  이 스크립트는 모든 금액을 KRW 정수로 통일하고, 원래 통화 정보는 '내용' 컬럼에 보존한다.

사용법:
  1) 메인 app.py 와 같은 폴더에 두기 (.streamlit/secrets.toml 공유)
  2) streamlit run migrate_log.py
  3) "1단계: 백업 만들기" 클릭 → 시트가 자동 복제됨
  4) "2단계: 미리보기" 영역에서 모든 변환 결과 확인
  5) "3단계: 실제 적용" 클릭 (되돌릴 수 없음, 단 백업으로 복구 가능)
  6) 완료 후 이 파일을 삭제하거나 보관

주의:
  USD 환산은 해당 날짜의 USD/KRW 종가를 사용하지만, 정확한 매수/환전 시점 환율과
  다를 수 있다. 정확도가 중요하면 적용 전 미리보기에서 직접 확인 후 진행.
"""

import streamlit as st
import pandas as pd
import json
import gspread
import yfinance as yf
import gspread.utils
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(page_title="Log 마이그레이션", page_icon="🔄", layout="wide")

st.title("🔄 Log 시트 금액 컬럼 마이그레이션")
st.caption("일회성 데이터 정리 도구 — 사용 후 파일을 삭제하셔도 됩니다.")

SHEET_NAME = "Asset_history"
DEFAULT_RATE_FALLBACK = 1350.0


# ============================================================
# 시트 연결
# ============================================================
@st.cache_resource
def init_connection():
    creds_dict = json.loads(st.secrets["google_key"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)


try:
    client = init_connection()
    spreadsheet = client.open(SHEET_NAME)
    sheet_log = spreadsheet.worksheet("Log")
except Exception as e:
    st.error(f"구글 스프레드시트 연결 오류: {e}")
    st.stop()


# ============================================================
# 환율 조회
# ============================================================
@st.cache_data(ttl=3600)
def get_historical_krw_rate(date_str: str):
    """주어진 날짜의 USD/KRW 종가. 휴일이면 가장 가까운 직전 영업일."""
    try:
        d = pd.to_datetime(date_str)
        start = (d - pd.Timedelta(days=5)).strftime('%Y-%m-%d')
        end = (d + pd.Timedelta(days=2)).strftime('%Y-%m-%d')
        hist = yf.Ticker("KRW=X").history(start=start, end=end)
        if hist.empty:
            return None
        hist.index = hist.index.tz_localize(None)
        on_or_before = hist[hist.index <= d]
        if not on_or_before.empty:
            return float(on_or_before['Close'].iloc[-1])
        return float(hist['Close'].iloc[0])
    except Exception:
        return None


# ============================================================
# 금액 파싱
# ============================================================
def parse_amount(val):
    """반환: (number, currency, is_already_clean)
        currency: 'KRW' | 'USD' | None
        is_already_clean: True 이면 변경 불필요"""
    if pd.isna(val) or val == '' or val is None:
        return 0.0, None, True
    if isinstance(val, (int, float)):
        return float(val), 'KRW', True
    s = str(val).strip()
    # 순수 숫자 문자열 (예: "1,500,000")
    try:
        return float(s.replace(',', '')), 'KRW', True
    except ValueError:
        pass
    # 단위 포함
    digits = ''.join(c for c in s if c.isdigit() or c == '.')
    if not digits:
        return 0.0, None, True
    try:
        num = float(digits)
    except ValueError:
        return 0.0, None, True
    if '달러' in s or '$' in s or 'USD' in s.upper():
        return num, 'USD', False
    if '원' in s or '₩' in s or 'KRW' in s.upper():
        return num, 'KRW', False
    return num, None, True


# ============================================================
# 미리보기 데이터 생성
# ============================================================
def build_preview():
    log_records = sheet_log.get_all_records()
    df = pd.DataFrame(log_records)
    rows = []
    for idx, row in df.iterrows():
        amount = row.get('금액', '')
        date = str(row.get('날짜', ''))
        memo = str(row.get('내용', ''))

        num, currency, is_clean = parse_amount(amount)

        if is_clean:
            new_amount = int(num) if num else num
            new_memo = memo
            rate = None
            action = "변경 없음"
            needs_update = False
        elif currency == 'KRW':
            new_amount = int(num)
            new_memo = memo
            rate = None
            action = f"단위 제거"
            needs_update = True
        elif currency == 'USD':
            rate = get_historical_krw_rate(date) or DEFAULT_RATE_FALLBACK
            new_amount = int(round(num * rate))
            usd_tag = f"[원래 ${num:,.2f} @ {rate:,.2f}]"
            new_memo = f"{memo} {usd_tag}".strip() if memo else usd_tag
            action = f"USD 환산"
            needs_update = True
        else:
            new_amount = amount
            new_memo = memo
            rate = None
            action = "⚠️ 식별 불가, 유지"
            needs_update = False

        rows.append({
            '행': idx + 2,
            '날짜': date,
            '원본 금액': amount,
            '새 금액 (KRW)': new_amount,
            '환율': f"{rate:,.2f}" if rate else "-",
            '원본 내용': memo,
            '새 내용': new_memo,
            '동작': action,
            '_needs_update': needs_update,
        })
    return rows


# ============================================================
# UI: 1단계 — 백업
# ============================================================
st.divider()
st.subheader("1단계: 백업 만들기")
st.write("실제 적용 전에 Log 시트 사본을 만듭니다. 문제 발생 시 이 사본으로 복원할 수 있습니다.")

if st.button("📦 Log 시트 백업 생성", use_container_width=True):
    try:
        backup_name = f"Log_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        spreadsheet.duplicate_sheet(
            source_sheet_id=sheet_log.id,
            new_sheet_name=backup_name,
        )
        st.success(f"✅ 백업 완료: 시트 이름 **`{backup_name}`** 으로 복제됨")
    except Exception as e:
        st.error(f"백업 실패: {e}")


# ============================================================
# UI: 2단계 — 미리보기
# ============================================================
st.divider()
st.subheader("2단계: 변환 미리보기")
st.write("아래는 적용될 변환 내역입니다. **아직 시트는 변경되지 않았습니다.**")

if st.button("🔍 미리보기 생성/새로고침", use_container_width=True):
    with st.spinner("Log 시트 읽는 중 + 환율 조회 중..."):
        preview = build_preview()
        st.session_state['preview'] = preview

if 'preview' in st.session_state:
    preview = st.session_state['preview']
    df_preview = pd.DataFrame(preview).drop(columns=['_needs_update'])

    needs_count = sum(1 for r in preview if r['_needs_update'])
    st.info(f"총 **{len(preview)}행** 중 **{needs_count}행** 업데이트 예정")

    st.dataframe(df_preview, use_container_width=True, hide_index=True)

    # ============================================================
    # UI: 3단계 — 실제 적용
    # ============================================================
    st.divider()
    st.subheader("3단계: 실제 적용")
    st.warning(
        "⚠️ 이 작업은 시트의 데이터를 직접 수정합니다. "
        "되돌리려면 1단계에서 만든 백업 시트의 내용을 Log 시트로 복사해야 합니다."
    )
    confirm = st.checkbox("백업을 만들었고, 미리보기를 확인했습니다.")

    if st.button("🚀 실제 적용 실행",
                 use_container_width=True,
                 disabled=not confirm,
                 type="primary"):
        # 컬럼 위치: 날짜=1, 분류=2, 금액=3, 내용=4
        AMOUNT_COL = 3
        MEMO_COL = 4

        batch_data = []
        for r in preview:
            if not r['_needs_update']:
                continue
            batch_data.append({
                'range': gspread.utils.rowcol_to_a1(r['행'], AMOUNT_COL),
                'values': [[r['새 금액 (KRW)']]],
            })
            batch_data.append({
                'range': gspread.utils.rowcol_to_a1(r['행'], MEMO_COL),
                'values': [[r['새 내용']]],
            })

        if not batch_data:
            st.info("업데이트할 행이 없습니다.")
        else:
            try:
                with st.spinner(f"{len(batch_data) // 2}개 행 업데이트 중..."):
                    sheet_log.batch_update(batch_data)
                st.success(
                    f"✅ {len(batch_data) // 2}개 행 업데이트 완료! "
                    "메인 앱에서 새로고침해 결과를 확인해주세요."
                )
                st.balloons()
                # 캐시 무효화
                st.cache_data.clear()
                del st.session_state['preview']
            except Exception as e:
                st.error(f"업데이트 실패: {e}")
                st.info(
                    "백업 시트로부터 복원하려면, 백업 시트 내용을 복사해 Log 시트에 덮어쓰면 됩니다."
                )
else:
    st.caption("위 '미리보기 생성' 버튼을 눌러 시작하세요.")
