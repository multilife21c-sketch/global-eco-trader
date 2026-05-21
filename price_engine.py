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
# (제목, 강도, 요약, 영향해설, 관련용어리스트)
NEWS_POOL = {
    "positive": [
        ("{c} GDP 예상치 상회, 경제 호조세", 0.8,
         "{c}의 분기 GDP가 시장 예상을 뛰어넘으며 경제가 견조한 성장세를 보였습니다.",
         "GDP 성장은 국가의 생산력이 커졌음을 의미하며, 투자 매력도를 높여 가치 상승 요인이 됩니다.",
         ["GDP", "GDP성장률"]),
        ("{c} 중앙은행 금리 인하, 시장 환영", 0.7,
         "{c} 중앙은행이 기준금리를 인하하면서 기업 투자와 소비 진작 기대가 커졌습니다.",
         "금리 인하는 대출 부담을 줄여 경제를 활성화시키므로 단기적으로 자산 가치에 긍정적입니다.",
         ["금리", "중앙은행"]),
        ("{c} 대규모 인프라 투자 계획 발표", 0.6,
         "{c} 정부가 도로·항만·통신 등 사회기반시설에 대규모 투자 계획을 발표했습니다.",
         "인프라 투자는 일자리를 만들고 장기 성장 기반을 다져 국가 경쟁력을 끌어올립니다.",
         ["GDP성장률"]),
        ("{c} 수출 사상 최대, 무역수지 개선", 0.9,
         "{c}의 수출이 사상 최대치를 기록하며 무역수지가 큰 폭으로 개선되었습니다.",
         "수출 증가는 외화를 벌어들여 경제를 튼튼하게 만들고 화폐 가치를 안정시킵니다.",
         ["무역수지", "환율"]),
        ("{c} 신기술 분야 선도, 외국인 투자 급증", 1.0,
         "{c}가 반도체·AI 등 첨단 기술 분야를 선도하며 외국인 직접투자가 몰리고 있습니다.",
         "첨단 산업 경쟁력은 미래 성장 동력으로, 외국 자본 유입은 국가 가치를 크게 높입니다.",
         ["GDP성장률"]),
        ("{c} 실업률 역대 최저치 갱신", 0.7,
         "{c}의 실업률이 역대 최저 수준으로 떨어지며 고용 시장이 활기를 띠고 있습니다.",
         "낮은 실업률은 소비 여력을 키워 내수 경제를 살리는 긍정적 신호입니다.",
         ["GDP성장률"]),
        ("{c} 신용등급 상향 조정", 1.1,
         "국제 신용평가사가 {c}의 국가 신용등급을 한 단계 상향 조정했습니다.",
         "신용등급 상승은 낮은 비용으로 자금을 조달할 수 있게 해 투자자 신뢰를 높입니다.",
         ["신용등급"]),
        ("{c} 글로벌 정상회의 개최, 외교 입지 강화", 0.5,
         "{c}가 주요국 정상회의를 성공적으로 개최하며 국제 무대에서 위상을 높였습니다.",
         "외교 입지 강화는 무역 협상과 투자 유치에 유리해 경제에 간접적 호재로 작용합니다.",
         []),
        ("{c} 친환경 에너지 전환 가속", 0.6,
         "{c}가 태양광·풍력 등 재생에너지로의 전환을 빠르게 추진하고 있습니다.",
         "친환경 전환은 미래 산업 주도권과 에너지 자립도를 높이는 장기 성장 전략입니다.",
         []),
        ("{c} 관광 산업 회복, 외화 유입 증가", 0.6,
         "{c}의 관광 산업이 빠르게 회복되며 외국인 관광객 소비가 늘고 있습니다.",
         "관광 수입은 외화를 벌어들여 무역수지와 내수에 모두 도움이 됩니다.",
         ["무역수지"]),
    ],
    "negative": [
        ("{c} 인플레이션 우려 확대, 물가 급등", 0.8,
         "{c}의 소비자물가가 급등하며 인플레이션 우려가 커지고 있습니다.",
         "과도한 물가 상승은 화폐 가치를 떨어뜨리고 소비를 위축시켜 경제에 부담을 줍니다.",
         ["인플레이션", "금리"]),
        ("{c} 정치 불안 심화, 의회 충돌", 1.0,
         "{c}의 정치적 갈등이 격화되며 정책 운영에 불확실성이 커지고 있습니다.",
         "정치 불안은 투자자에게 가장 큰 위험 요소로, 자본 이탈과 가치 하락을 부릅니다.",
         ["변동성"]),
        ("{c} 자연재해 발생, 경제 피해 확대", 1.2,
         "{c}에서 대규모 자연재해가 발생해 경제적 피해가 확산되고 있습니다.",
         "재해는 생산 시설과 인프라를 파괴해 단기적으로 경제 활동을 크게 위축시킵니다.",
         []),
        ("{c} 주요 수출 품목 단가 하락", 0.6,
         "{c}의 핵심 수출 품목 가격이 국제 시장에서 하락하고 있습니다.",
         "수출 단가 하락은 무역수지를 악화시켜 외화 수입 감소로 이어집니다.",
         ["무역수지"]),
        ("{c} 무역 분쟁 격화, 관세 우려", 0.9,
         "{c}와 주요 교역국 간 무역 분쟁이 격화되며 관세 인상 우려가 커집니다.",
         "관세 장벽은 수출을 어렵게 만들어 무역 의존도가 높은 경제에 타격을 줍니다.",
         ["무역수지"]),
        ("{c} 대형 은행 부실 우려, 금융 충격", 1.3,
         "{c}의 주요 은행에서 부실 우려가 제기되며 금융 시장이 흔들리고 있습니다.",
         "금융 시스템 불안은 경제 전반으로 위기가 번질 수 있는 심각한 악재입니다.",
         ["변동성"]),
        ("{c} 신용등급 강등 위기", 1.1,
         "국제 신용평가사가 {c}의 신용등급에 부정적 전망을 제시했습니다.",
         "신용등급 강등은 자금 조달 비용을 높이고 외국 투자자 이탈을 가속화합니다.",
         ["신용등급"]),
        ("{c} 정부 부채 한계, 국채 발행 난항", 1.0,
         "{c} 정부의 부채가 한계에 다다라 국채 발행에 어려움을 겪고 있습니다.",
         "과도한 국가 부채는 재정 위기로 번질 수 있어 국가 가치를 떨어뜨립니다.",
         ["신용등급"]),
        ("{c} 대규모 파업, 산업 생산 차질", 0.7,
         "{c}에서 대규모 파업이 발생해 주요 산업의 생산이 멈췄습니다.",
         "생산 차질은 수출과 GDP에 직접적인 손실을 주는 단기 악재입니다.",
         ["GDP"]),
        ("{c} 통화 약세, 자본 유출 심화", 0.9,
         "{c}의 통화 가치가 급락하며 외국 자본이 빠져나가고 있습니다.",
         "통화 약세와 자본 유출은 서로를 악화시키는 악순환을 만들 수 있습니다.",
         ["환율"]),
    ],
    "neutral": [
        ("{c} 정부 신규 정책 발표, 영향 분석 중", 0.3,
         "{c} 정부가 새로운 경제 정책을 발표했으며 시장이 영향을 분석 중입니다.",
         "정책의 방향에 따라 호재나 악재가 될 수 있어 시장은 관망세를 보입니다.",
         []),
        ("{c} 분기 경제지표 발표 예정", 0.2,
         "{c}의 주요 분기 경제지표 발표가 예정되어 투자자들이 주목하고 있습니다.",
         "지표 발표 전에는 불확실성으로 가격 변동이 제한적인 경우가 많습니다.",
         ["GDP"]),
        ("{c} 중앙은행 회의 결과 예상치 부합", 0.3,
         "{c} 중앙은행의 통화정책 회의 결과가 시장 예상과 일치했습니다.",
         "예상에 부합하는 결정은 시장에 큰 충격을 주지 않아 안정적으로 흡수됩니다.",
         ["중앙은행", "금리"]),
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
    title, strength, summary, impact, terms = pool[idx]
    return {"category": category, "title": title, "strength": strength,
            "summary": summary, "impact": impact, "terms": terms}

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
                "summary": news["summary"].replace("{c}", c["name"]),
                "impact": news["impact"],
                "terms": news["terms"],
                "change_pct": round(change_pct, 2),
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
