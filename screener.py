import requests
import time
from datetime import datetime, timedelta
import os
 
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
    """KRX 종목 리스트 - 정적 주요 종목 + 동적 로딩 시도"""
    print("종목 로딩 중...")
    
    # 코스피 주요 종목
    kospi = [
        ("005930","삼성전자"),("000660","SK하이닉스"),("005380","현대차"),
        ("000270","기아"),("051910","LG화학"),("006400","삼성SDI"),
        ("035420","NAVER"),("005490","POSCO홀딩스"),("028260","삼성물산"),
        ("012330","현대모비스"),("009150","삼성전기"),("011200","HMM"),
        ("032830","삼성생명"),("017670","SK텔레콤"),("030200","KT"),
        ("010950","S-Oil"),("015760","한국전력"),("096770","SK이노베이션"),
        ("034220","LG디스플레이"),("003550","LG"),("066570","LG전자"),
        ("018260","삼성SDS"),("000100","유한양행"),("068270","셀트리온"),
        ("207940","삼성바이오로직스"),("373220","LG에너지솔루션"),
        ("003490","대한항공"),("316140","우리금융"),("105560","KB금융"),
        ("055550","신한지주"),("086790","하나금융지주"),("024110","기업은행"),
        ("000810","삼성화재"),("032640","LG유플러스"),("011070","LG이노텍"),
        ("251270","넷마블"),("036570","엔씨소프트"),("035720","카카오"),
        ("323410","카카오뱅크"),("352820","하이브"),("259960","크래프톤"),
        ("007660","이수페타시스"),("003670","포스코퓨처엠"),("247540","에코프로비엠"),
        ("086520","에코프로"),("357780","솔브레인"),("000990","DB하이텍"),
        ("042700","한미반도체"),("336370","솔루엠"),("038830","화승엔터프라이즈"),
        ("100840","SNT에너지"),("140860","파크시스템스"),("00100","유한양행"),
    ]
    
    # 코스닥 주요 종목
    kosdaq = [
        ("196170","알테오젠"),("091990","셀트리온헬스케어"),("145020","휴젤"),
        ("214150","클래시스"),("086900","메디오젠"),("263750","펄어비스"),
        ("112040","위메이드"),("293490","카카오게임즈"),("357120","코람코더원리츠"),
        ("222080","씨아이에스"),("452190","한빛레이저"),("039030","이오테크닉스"),
        ("054040","에스원"),("053800","안랩"),("041510","에스엠"),
        ("035900","JYP Ent."),("122870","와이지엔터테인먼트"),("016360","삼성증권"),
        ("403870","HPSP"),("357550","석경에이티"),("950130","엑시콘"),
        ("241770","알에스오토메이션"),("317400","아이에스시"),("253450","스튜디오드래곤"),
        ("041020","폴라리스오피스"),("036800","나이스정보통신"),("104480","티씨케이"),
        ("237690","에스티팜"),("196300","애경산업"),("064760","티씨케이"),
        ("100790","미래에셋벤처투자"),("067310","하나마이크론"),("039200","오스코텍"),
        ("214180","했셀"),("383800","코렘"),("950210","프레스티지바이오파마"),
        ("145210","세토피아"),("110790","에스와이"),("064760","티씨케이"),
        ("036030","KG모빌리언스"),("119610","인터로조"),("048410","현대바이오"),
        ("200670","휴메딕스"),("237750","아이시아"),("131370","마크로젠"),
        ("060310","3S"),("950130","엑시콘"),("041830","인바디"),
        ("900290","GRT"),("302440","SK바이오사이언스"),("145720","덴티움"),
    ]
    
    tickers = []
    for code, name in kospi:
        tickers.append({"code": code, "name": name, "market": "KOSPI", "yahoo": f"{code}.KS"})
    for code, name in kosdaq:
        tickers.append({"code": code, "name": name, "market": "KOSDAQ", "yahoo": f"{code}.KQ"})
    
    print(f"{len(tickers)}개 종목 로딩 완료")
    return tickers
 
 
def get_ohlcv(yahoo_code):
    """Yahoo Finance에서 일봉 데이터 가져오기"""
    try:
        import yfinance as yf
        end = datetime.now()
        start = end - timedelta(days=90)
        df = yf.download(yahoo_code, start=start.strftime("%Y-%m-%d"),
                        end=end.strftime("%Y-%m-%d"), progress=False)
        if df is None or len(df) < LOOKBACK + 2:
            return []
        candles = []
        for date, row in df.iterrows():
            close = int(row["Close"])
            open_ = int(row["Open"])
            vol = int(row["Volume"])
            candles.append({
                "date": str(date)[:10],
                "open": open_,
                "close": close,
                "amount": vol * close
            })
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
        if i % 20 == 0:
            print(f"진행: {i}/{len(tickers)}")
        c = get_ohlcv(t["yahoo"])
        r = check(c)
        if r:
            matched.append({**t, **r})
            print(f"패턴발견: {t['name']} ({t['code']})")
        time.sleep(0.2)
 
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
