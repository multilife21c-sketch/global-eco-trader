#!/usr/bin/env python3
"""
NationVault 가격 엔진 — GitHub Actions에서 1시간마다 실행
- countries.json의 기준가에 시간 경과 + 결정론적 뉴스 이벤트를 적용
- 모든 사용자가 동일 시각에 동일 가격을 보도록 시드 고정
- 결과를 prices.json으로 출력 → GitHub Pages가 서빙
"""
import json, hashlib, math, random, datetime, os

BASE = os.path.dirname(os.path.abspath(__file__))

def load_countries():
    with open(os.path.join(BASE, 'countries.json'), encoding='utf-8') as f:
        return json.load(f)

def load_prev_prices():
    path = os.path.join(BASE, 'prices.json')
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return None

# 뉴스 템플릿 (결정론적 선택용)
NEWS_POOL = {
    "positive": [
        ("{c} GDP 예상치 상회, 경제 호조세", 0.8),
        ("{c} 중앙은행 금리 인하, 시장 환영", 0.7),
        ("{c} 대규모 인프라 투자 계획 발표", 0.6),
        ("{c} 수출 사상 최대, 무역수지 개선", 0.9),
        ("{c} 신기술 분야 선도, 외국인 투자 급증", 1.0),
        ("{c} 실업률 역대 최저치 갱신", 0.7),
        ("{c} 신용등급 상향 조정", 1.1),
        ("{c} 글로벌 정상회의 개최, 외교 입지 강화", 0.5),
        ("{c} 친환경 에너지 전환 가속", 0.6),
        ("{c} 관광 산업 회복, 외화 유입 증가", 0.6),
    ],
    "negative": [
        ("{c} 인플레이션 우려 확대, 물가 급등", 0.8),
        ("{c} 정치 불안 심화, 의회 충돌", 1.0),
        ("{c} 자연재해 발생, 경제 피해 확대", 1.2),
        ("{c} 주요 수출 품목 단가 하락", 0.6),
        ("{c} 무역 분쟁 격화, 관세 우려", 0.9),
        ("{c} 대형 은행 부실 우려, 금융 충격", 1.3),
        ("{c} 신용등급 강등 위기", 1.1),
        ("{c} 정부 부채 한계, 국채 발행 난항", 1.0),
        ("{c} 대규모 파업, 산업 생산 차질", 0.7),
        ("{c} 통화 약세, 자본 유출 심화", 0.9),
    ],
    "neutral": [
        ("{c} 정부 신규 정책 발표, 영향 분석 중", 0.3),
        ("{c} 분기 경제지표 발표 예정", 0.2),
        ("{c} 중앙은행 회의 결과 예상치 부합", 0.3),
    ],
}

def deterministic_news(code, hour_seed):
    """국가코드 + 시간시드로 결정론적 뉴스 생성"""
    h = int(hashlib.md5(f"{code}_{hour_seed}".encode()).hexdigest(), 16)
    roll = (h % 1000) / 1000.0
    # 60% 확률로 뉴스 없음
    if roll < 0.6:
        return None
    # 뉴스 발생
    if roll < 0.76:
        category = "positive"
    elif roll < 0.92:
        category = "negative"
    else:
        category = "neutral"
    pool = NEWS_POOL[category]
    idx = (h // 1000) % len(pool)
    title, strength = pool[idx]
    return {"category": category, "title": title, "strength": strength}

def main():
    countries = load_countries()
    prev = load_prev_prices()
    now = datetime.datetime.now(datetime.timezone.utc)
    hour_seed = now.strftime("%Y%m%d%H")  # 시간 단위 시드

    out = {
        "generated_at": now.isoformat(),
        "hour_seed": hour_seed,
        "countries": {},
        "news": [],
    }

    all_news = []
    for c in countries:
        code = c["code"]
        # 직전 가격 (없으면 기준가)
        if prev and code in prev.get("countries", {}):
            prev_price = prev["countries"][code]["price"]
            prev_sentiment = prev["countries"][code].get("sentiment", 0)
        else:
            prev_price = c["basePrice"]
            prev_sentiment = 0

        # 시간별 뉴스 평가 (결정론적)
        news = deterministic_news(code, hour_seed)
        sentiment = prev_sentiment * 0.85  # 감성 감쇠
        change_pct = 0.0

        if news:
            delta = news["strength"] * 30
            if news["category"] == "negative":
                delta = -delta
            elif news["category"] == "neutral":
                delta = delta * 0.2
            sentiment += delta
            sentiment = max(-100, min(100, sentiment))
            # 가격 변동 (티어 보정)
            tier_damp = {"S": 0.5, "A": 0.7, "B": 0.9, "C": 1.0, "D": 1.1}[c["tier"]]
            change_pct = (delta * 0.05) * tier_damp
            change_pct = max(-7, min(7, change_pct))

            all_news.append({
                "code": code,
                "name": c["name"],
                "flag": c["flag"],
                "title": news["title"].replace("{c}", c["name"]),
                "category": news["category"],
                "time": now.isoformat(),
            })

        # 기준 변동 (감성 기반 드리프트)
        drift = sentiment * 0.0008
        new_price = prev_price * (1 + change_pct / 100 + drift)
        new_price = max(0.5, round(new_price, 2))

        out["countries"][code] = {
            "price": new_price,
            "seed_price": new_price,  # 클라이언트 마이크로틱의 기준점
            "prev_price": prev_price,
            "change_pct": round((new_price - prev_price) / prev_price * 100, 2) if prev_price else 0,
            "sentiment": round(sentiment, 1),
            "volatility": c["volatility"],
        }

    # 뉴스 최신순, 최대 40개
    out["news"] = all_news[:40]

    with open(os.path.join(BASE, 'prices.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"✅ prices.json 생성 ({len(out['countries'])}개국, 뉴스 {len(out['news'])}건)")
    print(f"   시드: {hour_seed}")
    # 상위 5개 출력
    for c in countries[:5]:
        cd = out["countries"][c["code"]]
        print(f"   {c['flag']} {c['code']}: ${cd['price']} ({cd['change_pct']:+.2f}%) 감성{cd['sentiment']:+.0f}")

if __name__ == "__main__":
    main()
