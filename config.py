# config.py

# ==========================================
# ⚙️ 내 자산 데이터 입력 공간
# ==========================================
SHEET_NAME = "Asset_history"  # 연결된 구글 스프레드시트 이름

krw_balance = 766872          # 현재 보유 중인 원화(KRW)

# 💵 달러 환전 내역 (여러 번 구매한 내역을 리스트로 입력)
# buy_rate: 환전했을 때의 적용 환율, amount: 구매한 달러 수량
usd_purchases = [
    {"buy_rate": 1481.79, "amount": 3035.17}
]

# 📊 주식 포트폴리오
portfolio = [
    {"name": "TIGER 200", "ticker": "102110.KS", "quantity": 6, "buy_price": 87366},
    {"name": "TIGER 미국S&P500", "ticker": "360200.KS", "quantity": 20, "buy_price": 25005},
    {"name": "TIGER 미국나스닥100", "ticker": "133690.KS", "quantity": 3, "buy_price": 164285},
]
