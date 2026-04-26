import requests
import time
from datetime import datetime
import os
import re

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT = "8598053920"

MIN_BODY = 0.05
MIN_VOL = 2.0
MIN_GAP = 0.01
LOOKBACK = 20


def telegram(msg):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": msg},
            timeout=10
        )
        if r.status_code == 200:
            print("텔레그램 전송 성공")
        else:
            print(f"텔레그램 실패: {r.text}")
    except Exception as e:
        print(f"텔레그램 오류: {e}")


def get_tickers():
    print("종목 로딩 중...")
    tickers = []
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}
    for market in [0, 1]:
        for page in range(1, 60):
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={market}&page={page}"
            try:
                res = requests.get(url, headers=headers, timeout=10)
                items = re.findall(r'href="/item/main\.naver\?code=(\d{6})">([^<]+)</a>', res.text)
                if not items:
                    break
                mkt = "KOSPI" if market == 0 else "KOSDAQ"
                for code, name in items:
                    tickers.append({"code": code, "name": name.strip(), "market": mkt})
                time.sleep(0.1)
            except:
                break
    seen = set()
    result = []
    for t in tickers:
        if t["code"] not in seen:
            seen.add(t["code"])
            result.append(t)
    print(f"{len(result)}개 종목 로딩 완료")
    return result


def get_ohlcv(code):
    url = f"https://api.finance.naver.com/siseJson.naver?symbol={code}&requestType=1&count=30&timeframe=day"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        data = res.json()
        candles = []
        for row in data:
            if len(row) >= 7 and row[0] and row[0] != "날짜":
                try:
                    candles.append({
                        "date": str(row[0]).replace(".", "-"),
                        "open": int(str(row[1]).replace(",", "")),
                        "close": int(str(row[4]).replace(",", "")),
                        "amount": int(str(row[6]).replace(",", ""))
                    })
                except:
                    continue
        candles.sort(key=lambda x: x["date"])
        return candles
    except:
        return []


def check(candles):
    if len(candles) < LOOKBACK + 2:
        return None
    d1 = candles[-2]
    d2 = candles[-1]
    past = candles[-(LOOKBACK + 2):-2]
    avg = sum(c["amount"] for c in past) / len(past) if past else 0
    if avg == 0:
        return None
    if d1["close"] <= d1["open"]:
        return None
    body = (d1["close"] - d1["open"]) / d1["open"]
    if body < MIN_BODY:
        return None
    vol_x = d1["amount"] / avg
    if vol_x < MIN_VOL:
        return None
    gap = (d2["open"] - d1["close"]) / d1["close"]
    if gap < MIN_GAP:
        return None
    if d2["amount"] < d1["amount"]:
        return None
    if d2["close"] <= d1["close"]:
        return None
    return {
        "d1": d1["date"], "d2": d2["date"],
        "body": round(body * 100, 1),
        "gap": round(gap * 100, 1),
        "vol_x": round(vol_x, 1),
        "price": d2["close"],
        "amt1": d1["amount"],
        "amt2": d2["amount"],
    }


def fmt(a):
    if a >= 100_000_000:
        return f"{a//100_000_000:,}억"
    return f"{a//10_000:,}만"


def main():
    now = datetime.now().strftime("%Y/%m/%d %H:%M")
    print(f"스크리너 시작: {now}")

    tickers = get_tickers()
    matched = []

    for i, t in enumerate(tickers):
        if i % 200 == 0:
            print(f"진행: {i}/{len(tickers)}")
        c = get_ohlcv(t["code"])
        r = check(c)
        if r:
            matched.append({**t, **r})
            print(f"패턴발견: {t['name']} ({t['code']})")
        time.sleep(0.05)

    if not matched:
        msg = f"📊 [{now}]\n스캔완료 - 조건충족 종목없음"
    else:
        matched.sort(key=lambda x: x["amt2"], reverse=True)
        lines = [f"🚨 [{now}] 패턴포착! {len(matched)}종목\n"]
        for m in matched[:10]:
            lines.append(
                f"📌 {m['name']} ({m['code']}) {m['market']}\n"
                f"1일({m['d1']}): +{m['body']}% {m['vol_x']}배\n"
                f"2일({m['d2']}): 갭+{m['gap']}% {m['price']:,}원\n"
                f"거래대금: {fmt(m['amt1'])}→{fmt(m['amt2'])}\n"
            )
        if len(matched) > 10:
            lines.append(f"외 {len(matched)-10}종목")
        msg = "\n".join(lines)

    print(msg)
    telegram(msg)
    print("완료")


if __name__ == "__main__":
    main()
