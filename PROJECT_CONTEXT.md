# 🌐 NationRise — 프로젝트 컨텍스트 (AI 인수인계용)

> **이 파일을 먼저 읽으세요.** 이 문서는 AI(Claude)가 새 대화에서 전체 코드를 처음부터 분석하지 않고도
> 즉시 작업에 착수할 수 있도록 작성된 아키텍처 맵입니다. 코드 전수 분석 전에 이 문서로 구조를 파악하세요.

---

## 1. 한 줄 요약

**NationRise**는 플레이어가 가상의 국가를 건국해 GDP를 키우고, 전 세계 플레이어/AI와 랭킹을 겨루는
**브라우저 기반 경제 시뮬레이션 게임**이다. (자녀 경제교육 목적 포함, 한국어 UI)

- **배포:** GitHub Pages (정적 호스팅) — 예: `https://multilife21c-sketch.github.io/global-eco-trader/`
- **백엔드:** Firebase (Authentication = 구글 로그인, Firestore = 저장/랭킹)
- **언어/스택:** 순수 Vanilla JS + HTML + CSS (프레임워크 없음). 단일 `index.html`에 전부 인라인.

---

## 2. 파일 구조

| 파일 | 역할 | 비고 |
|------|------|------|
| `index.html` | **게임 본체 전부** (HTML+CSS+JS 인라인, 약 3,600줄) | 작업의 99%는 여기서 일어남 |
| `countries.json` | 195개국 데이터 (code, name, flag, tier, gdp, basePrice, volatility) | 정적 데이터, 거의 안 건드림 |
| `prices.json` | 국가별 가격 시계열 데이터 | 정적 데이터 |
| `glossary.json` | 경제 용어 사전 12개 + 퀴즈(참고용). ⚠️ 실제 게임 퀴즈는 `index.html`의 `QUIZ_DATA`(210문제)를 사용 | 교육 콘텐츠 |
| `price_engine.py` | 가격 데이터 생성용 파이썬 스크립트 (오프라인 전처리용, 런타임 무관) | 게임 실행과 무관 |

> ⚠️ **데이터 파일(`countries/prices/glossary.json`)은 분석할 필요가 거의 없다.** 구조는 위 표로 충분.
> 작업 요청은 대부분 `index.html`의 게임 로직/UI에 관한 것이다.

---

## 3. 핵심 상태 객체 `state` (index.html 상단 `let state = {...}`)

게임의 모든 런타임 데이터는 전역 `state` 객체에 들어있다. 저장/복원도 이 객체 기준.

```
state = {
  myNation,      // 내 국가 {name, flag, gdp, startGdp, ap, maxAp, health, tier,
                 //          treasury(국고), debt(부채), debtSources{bond,interest,repay}(부채발생내역),
                 //          creditRating(신용 0~10), stocks(보유주식 {code:{shares,avgPrice}}),
                 //          alias(랭킹표시별칭), createdAt, cdMap(쿨다운)}
  worldGdp,      // code -> 현재 GDP (시간에 따라 변동)
  selectedCode,  // 차트에 표시 중인 국가 코드
  badges,        // 획득 배지 id 배열
  quizLog,       // 날짜별 퀴즈 완료 기록
  stats,         // 누적 통계 {actionsUsed, newsRead, quizzesCompleted, stockTrades,
                 //            stockProfit, missionsClaimed, crisisResolved}
  history,       // code -> [{t, gdp}] GDP 시계열 (성장 그래프용)
  worldNews,     // 현재 뉴스 목록

  // ===== 확장 기능 상태 =====
  missions,      // 일일 미션 {date, list:[...]}
  checkin,       // 출석 {lastDate, streak, claimedToday}
  alliances,     // 동맹국 코드 배열
  tradeDeals,    // 무역협정국 코드 배열
  challenges,    // 시나리오 챌린지 달성 {id:{claimed}}
  rival,         // AI 라이벌 {name, flag, gdp, growthBias}
  season,        // 시즌 {id, startGdp, settled}
  lastCrisis,    // 마지막 위기 이벤트 시각

  // ===== 신규 확장 기능 상태 (중앙은행/건설/경제레벨) =====
  interestRate,  // 🏦 기준금리 % (0.5~5.0, 기본 2.5). Lv.5+면 하한 0.25%
  inflation,     // 🏦 현재 인플레이션 % (금리에 따른 목표치로 매 틱 수렴)
  lastRateChange,// 🏦 마지막 금리 변경 시각 (30초 쿨다운용)
  inflCrisisSince,// 🏦 인플레 위기(7%↑) 지속 시작 시각 (신용 강등 판정)
  buildings,     // 🏗️ 건설 완료 시설 {bId:true} (industry/port/airport/semicon/space)
  econLevel,     // 🎓 경제 지식 레벨 (1~10)
  econXP,        // 🎓 누적 경제 지식 경험치 (퀴즈 정답 1개=+10XP)
  miniGame,      // 🎮 미니게임 일일 기록 {date, plays, bestScore} (하루 3회 제한)
}
```

---

## 4. 게임 루프 & 핵심 엔진

- **`worldTick()`** (≈1459줄) — 게임의 심장. 3초마다 실행. GDP 성장/감소, 국고 세수, 부채 이자,
  동맹 보너스, 무역 수입, 라이벌 성장, 위기 이벤트 발생, 시즌 정산을 모두 처리.
  **신규:** 성장률(`totalRate`)에 금리 보정(`rateGrowthAdj`)·인플레 과열 제동(`inflationGrowthAdj`)·
  건설 성장보너스(`buildGrowthBonus`)를 합산하고, 국고 수입에 건설 수입(`buildIncomeBonus`)을 합산.
  매 틱 `inflationTick()`으로 인플레를 목표치에 수렴시키고 초인플레(7%↑) 시 health/신용 패널티 적용.
- **`apRegen()`** — 30초마다 행동포인트(AP) +1 충전.
- **`seededRand()` / `hashStr()`** — 결정론적 난수(날짜 시드 기반 미션 등에 사용).
- **`fmtGDP()` / `fmtGDPShort()`** — GDP 숫자 포맷팅 (예: $27.4T).

---

## 5. 기능별 함수 맵 (수정 시 여기를 먼저 보라)

| 기능 | 핵심 함수 | 모달 ID |
|------|-----------|---------|
| **인증/로그인** | `signInWithGoogle`(모바일=redirect/PC=popup), `onAuthChange`, `playAsGuest`, `proceedAfterLogin`, `setAuthLoading`. Firebase 초기화 시 `getRedirectResult`+`onAuthStateChanged`로 리다이렉트 복귀 처리 | — |
| **건국/시작** | `createMyNation`, `startGame`, `buildFlagSelector` | `onboardModal` |
| **내 계정/프로필** | `openAccount`, `profileStat`, `renderGrowthChart`, `saveAlias` | `accountModal` |
| **세계지도** | `drawMap`, `initMapCanvas`, `lonLatToXY`, `mapHover/Click` | — (canvas) |
| **국가 목록/차트** | `renderCountryList`, `selectCountry`(→차트+퀵트레이드), `drawChart`, `buildChartHistory`, `renderQuickTrade`, `buyStockFromQuick`, `sellStockFromQuick`, `qtUpdateCost` | — (차트 상단 `#quickTrade`) |
| **정책 실행** | `renderPolicies`, `confirmAction`, `executeAction`, `switchPol` | `actionModal` |
| **🎮 경제 미니게임** ⭐NEW | `openMiniGame`, `renderMiniGameIntro`, `startMiniGame`, `miniGameTick`, `miniGameTap`, `endMiniGame`, `closeMiniGame`, `miniGamePlaysToday` | `miniGameModal` |
| **주식시장** | `openStockMarket`, `renderStockMarket`, `buyStock(code,qty)`, `sellStock(code,qty)`, `stepQty`, `setQty`, `clampQty`, `updateBuyCost` | `stockModal` |
| **뉴스** | `generateNews`, `renderNews`, `openNews`, `renderTickerTape` | `newsModal` |
| **랭킹** | `openRanking`, `renderRanking`, `loadPlayerRanking`, `renderWorldRanking` | `rankingModal` |
| **퀴즈** | `openQuiz`(QUIZ_DATA 210문제 풀에서 날짜시드로 5문제 결정론 출제), `renderQuiz`, `answerQuiz`, `finishQuiz` | `quizModal` |
| **💰 국가부채 설명** ⭐NEW | `openDebtInfo`, `recordDebt`(bond/interest/repay 누적 추적) | `debtInfoModal` |
| **배지** | `checkBadges`, `openBadges` (BADGE_DEFS 배열) | `badgeModal` |
| **용어사전** | `openGlossary`, `renderGlossary`, `openTerm` | `glossaryModal` |
| **일일 미션** ⭐ | `ensureMissions`, `bumpMission`, `claimMission`, `renderMissions` (MISSION_POOL) | `missionModal` |
| **시나리오 챌린지** ⭐ | `renderChallenges`, `claimChallenge` (CHALLENGE_DEFS) | `missionModal`(탭) |
| **출석 보상** ⭐ | `checkDailyLogin`, `openCheckin`, `claimCheckin` (CHECKIN_REWARDS) | `checkinModal` |
| **외교/동맹** ⭐ | `openDiplomacy`, `formAlliance`, `formTradeDeal`, `allianceBonus`, `tradeBonus` | `diploModal` |
| **위기 선택지** ⭐ | `maybeTriggerCrisisChoice`, `openCrisis`, `resolveCrisis` (CRISIS_EVENTS) | `crisisModal` |
| **AI 라이벌** ⭐ | `ensureRival`, `rivalTick`, `rivalStatusHtml` (RIVAL_NAMES) | (외교 화면 내 표시) |
| **시즌제** ⭐ | `ensureSeason`, `openSeason`, `currentSeasonId`, `seasonDaysLeft` | `seasonModal` |
| **🏦 중앙은행(금리)** ⭐NEW | `openCentralBank`, `renderCentralBank`, `applyRate`, `previewRate`, `rateEffectHtml`, `inflationTarget`, `rateGrowthAdj`, `inflationGrowthAdj`, `inflationTick`, `rateMinAllowed` | `centralBankModal` |
| **🏗️ 국가 건설 트리** ⭐NEW | `openBuildings`, `renderBuildings`, `buildFacility`, `buildGrowthBonus`, `buildIncomeBonus`, `buildingMap` (BUILDINGS 배열) | `buildingModal` |
| **🎓 경제 지식 레벨** ⭐NEW | `addEconXP`, `econLevelFromXP`, `econPolicyMultiplier`, `econLevelBarHtml` (finishQuiz·openAccount 연동) | (퀴즈/프로필 내 표시) |
| **신규 기능 보정** ⭐NEW | `ensureEconomyFeatures` (startGame에서 구버전 세이브 기본값 보정) | — |
| **저장/동기화** | `saveState`, `loadStateFromCloud`, `applyLoadedData`, `scheduleSave` | — |

> ⭐ = 최근 추가된 확장 기능. 정의 데이터 배열(MISSION_POOL, CHALLENGE_DEFS 등)은 각 기능 함수 바로 위에 있다.

---

## 6. Firebase 구조 (중요)

**Firebase 프로젝트:** `infinity-universe`

### Firestore 컬렉션
| 컬렉션 | 용도 | 공개 여부 |
|--------|------|-----------|
| `nationrise_saves` | 플레이어 개인 저장 데이터 (전체 진행상황) | **본인만** (UID 문서) |
| `nationrise_players` | 공개 랭킹용 데이터 | **공개 읽기** |
| `rankings` / `users` | (구버전 잔재 가능성 — 확인 필요) | — |

### 🔒 개인정보 보호 규칙 (반드시 지킬 것)
**구글 닉네임(`displayName`)과 이메일은 절대 공개 컬렉션(`nationrise_players`)에 저장하지 않는다.**
- 공개 문서에 들어가는 필드: `uid, name(국가명), flag, gdp, startGdp, tier, actionsUsed, alias(선택)`
- 닉네임/이메일은 **내 계정 화면(`openAccount`)에서 본인에게만** 표시.
- 랭킹 표시는 `alias`(본인이 정한 별칭) > `name`(국가명) 순. 절대 구글 계정 정보 사용 안 함.
- ⚠️ 과거 `owner` 필드(닉네임)가 있었으나 제거됨. 이 패턴을 되살리지 말 것.

### 권장 보안 규칙 (Firestore Rules)
```
match /nationrise_players/{uid} {
  allow read: if true;
  allow write: if request.auth != null && request.auth.uid == uid;
}
match /nationrise_saves/{uid} {
  allow read, write: if request.auth != null && request.auth.uid == uid;
}
```

---

## 7. 비용/인프라 메모

- **GitHub Pages:** public 저장소면 사실상 영구 무료 (1GB 저장 / 월 100GB 대역폭).
- **Firebase Spark(무료):** Firestore 하루 읽기 5만/쓰기 2만, 저장 1GB, Auth 월 5만 MAU 무료.
  현재 소규모(플레이어 수 명)에서는 무료 한도에 한참 못 미침.
- ⚠️ **Blaze(종량제)로 올리면 지출 상한이 없음** → 반드시 예산 알림 설정. 소규모는 Spark 유지 권장.

---

## 8. 작업 시 지켜야 할 컨벤션

- **프레임워크 금지:** Vanilla JS만. 빌드 과정 없음. `index.html` 하나로 완결.
- **UI 톤:** 다크 테마 + 앰버(#ffb547)/시아닉 네온. CSS 변수(`--amber, --cyan, --green, --red, --bg2, --txt2` 등) 사용.
- **모달 패턴:** `<div class="modal-bd" id="xxxModal">` → `.classList.add('active')`로 열고 `closeModal('xxxModal')`로 닫음.
- **저장:** 상태 변경 후 `scheduleSave()` 호출 (디바운스됨). 직접 `saveState()` 남발 금지.
- **저장 필드 추가 시:** `saveState()`의 data 객체 + `applyLoadedData()` 복원 + `resetGameState()` 초기화 **3곳 모두** 수정.
- **새 기능 추가 시:** ① state에 필드 → ② 함수 작성 → ③ 모달 HTML → ④ 네비 버튼 → ⑤ worldTick/startGame 연동 → ⑥ 저장 3곳 → ⑦ 검증.
- **한국어 UI**, 사용자(개발자)는 **"Ryan"(라이언님)** 으로 호칭.

---

## 9. 검증 방법 (수정 후 필수)

```bash
# 1) JS 문법 검사: index.html에서 일반 <script> 추출 후
node --check extracted.js

# 2) 함수 참조 무결성: onclick에서 호출하는 함수가 모두 정의됐는지 확인
# 3) jsdom 통합 테스트 가능 (단, canvas/ResizeObserver는 jsdom 미구현 → 스텁 필요)
#    - Firebase module 스크립트는 제거하고 게스트 모드로 테스트
```

---

## 10. 알려진 환경 한계

- `canvas.getContext` 와 `ResizeObserver` 는 jsdom에서 미구현 → 자동 테스트 시 스텁 주입 필요 (실제 브라우저는 정상).
- Firebase는 `<script type="module">` 로 로드되어 jsdom에서 직접 import 불가 → 테스트 시 게스트 모드로 우회.

---

## 11. 변경 이력 — 🏦🏗️🎓 3기능 추가 (2026-05)

> 한 번에 통합 구현. 세 기능이 `worldTick` 성장식·국고·`executeAction`에 동시에 영향을 주고 서로 연계되어
> (레벨→시설 해금, 레벨→금리폭 확대) 단계 분할보다 통합 구현이 정합성·회귀 안전성에서 유리했음.

### 🏦 중앙은행 (금리 ↔ 인플레이션)
- 기준금리 **0.5~5.0%**(기본 2.5%, 0.25 단위). 경제 **Lv.5+면 하한 0.25%로 확대**.
- 목표 인플레 = `(2.5 − rate)×1.2 + 2.0` → 매 틱 5%씩 수렴(`inflationTick`).
- 성장 보정: `rateGrowthAdj = (2.5 − rate)×0.004 %/틱` (저금리=성장↑).
- 인플레 과열(4%↑) → 성장 `−0.006%/틱`. 위기(7%↑) → 매 틱 `health −0.4`, 45초 지속 시 `creditRating −0.5`.
- 금리 변경: **AP 2 소모 + 30초 쿨다운**. 모달 `centralBankModal`(슬라이더+실시간 효과 미리보기).

### 🏗️ 국가 건설 트리 (5단계 테크트리, `BUILDINGS` 배열)
| 단계 | id | 선행 | 비용($B) | 효과 |
|------|----|----|---------|------|
| 1 | industry 🏗️ | — | 30 | 성장 +0.004%/틱 |
| 2 | port ⚓ | industry | 70 | 국고 +0.30/틱 |
| 3 | airport ✈️ | port | 150 | 성장 +0.008%/틱 |
| 4 | semicon 🔬 | airport | 320 | 성장 +0.006%/틱 · 국고 +0.80/틱 |
| 5 | space 🚀 | semicon **+ Lv.7** | 650 | 성장 +0.015%/틱 |
- `buildGrowthBonus()`/`buildIncomeBonus()`가 worldTick에서 동맹·무역 보너스와 **합산**. 영구 효과.

### 🎓 경제 지식 레벨 (Lv.1~10)
- 퀴즈 **정답 1개 = +10 XP**(`addEconXP`, finishQuiz 연동). 레벨업 곡선 = `Lv×100`(누적).
- 정책 효과 배수 `econPolicyMultiplier = 1 + (Lv−1)×0.03` → **Lv.10이면 +27%**(`executeAction`의 gdpBoost에 적용).
- 연계 해금: **Lv.5** 금리 하한 0.25% 확대 / **Lv.7** 우주센터 해금.
- 레벨/경험치 바(`econLevelBarHtml`)는 프로필(`openAccount`)·퀴즈 결과(`finishQuiz`)에 표시.

### 저장 3곳 반영 (필드 추가 규칙 준수)
- **추가 필드:** `interestRate, inflation, lastRateChange, inflCrisisSince, buildings, econLevel, econXP`
- `saveState()` data 객체 + `applyLoadedData()` 복원·백필 + `resetGameState()` 초기화 **3곳 모두** 반영 완료.
- 🔒 **닉네임 보호:** 신규 필드는 게임 데이터이므로 개인 저장(`nationrise_saves`)에만 저장.
  공개 랭킹 문서(`publicDoc`)에는 **일절 추가하지 않음**(회귀 테스트로 누출 0 확인).

### 신규 배지 7종
`central_banker`(🏦), `price_keeper`(🎯), `builder`(🏗️), `space_nation`(🚀), `econ_lv5`(🎓), `econ_lv10`(🧠) 등.

### 검증 결과
- `node --check` 문법 통과 / 인라인 핸들러 함수 참조 무결성 통과(미정의 0) / 신규 핵심 함수 21개 정의 확인.
- jsdom 통합 테스트 **70/70 통과**. 레벨 배수 실측 **1.270배**(Lv.1 +1.5% → Lv.10 +1.905%) 확인.

---

## 12. 변경 이력 — 📱 UX 개선 4종 (2026-05)

### 🎓 퀴즈 200문제 풀 확장
- `QUIZ_DATA`를 10 → **210문제**로 확장(기초경제·금융·무역·거시지표·생활경제·게임연계 등 카테고리 균형).
- `openQuiz` 출제를 **날짜 시드 기반 결정론적 셔플**로 변경: 하루 5문제 고정, 매일 다른 문제.
  - `const seed = hashStr('quiz-'+today); pool.sort(seededRand(seed+i*97))` 방식.
- 같은 날 재진입해도 동일 5문제(교육 일관성). 다음 날 자동 교체.

### 💹 주식 매수/매도 수량 선택
- `buyStock(code, qty)` / `sellStock(code, qty)`로 시그니처 변경(qty 생략 시 입력란에서 읽음).
  - 매수 기본 5주, 매도 부분 매도 지원(전량 시 보유 자동 정리).
- UI: 종목별 −/입력/+ 스테퍼 + ½·최대 빠른버튼 + 매수비용 실시간 표시.
- 헬퍼: `stepQty`, `setQty`, `clampQty`, `updateBuyCost`. 과다 매도는 보유량까지만, 국고 부족 시 매수 차단.

### 💰 국가부채 설명 팝업
- 상단 부채 표시(`#mnsDebt`)에 `onclick="openDebtInfo()"` + `.clickable` 스타일(점선밑줄+ⓘ).
- `myNation.debtSources = {bond, interest, repay}`로 부채 발생 원인 누적 추적.
  - `recordDebt(kind, amount)`: 국채발행(executeAction)·이자(worldTick)·상환에서 호출.
- `debtInfoModal`: 현재 부채/GDP 비율 단계(안정/주의/위험) + 원인 분해 + 줄이는 법 안내(교육용).
- 저장: myNation에 포함되어 자동 저장 / `createMyNation` 초기화 / `applyLoadedData` 백필 3곳 반영.

### 📱 모바일 최적화
- 모달을 모바일에서 **하단 시트**(align-items:flex-end, 100%폭, 상단 라운드)로 전환.
- iOS 입력 자동 줌 방지(입력 폰트 16px), `env(safe-area-inset)` 대응(노치/홈바).
- 상단 네비 가로 스크롤(버튼 넘침 대응), 거래 행 줄바꿈, 슬라이더/버튼 터치 영역 확대.
- `dvh`(동적 뷰포트) 사용, 가로모드(max-height:520px) 대응.

### 검증 결과
- `node --check` 문법 통과 / 함수 참조 무결성 통과 / 신규 함수(stepQty·setQty·clampQty·updateBuyCost·recordDebt·openDebtInfo) 정의 확인.
- jsdom 통합 테스트 **105/105 통과**(기존 70 + 신규 35). 퀴즈 210문제·중복0·결정론 출제, 주식 부분매도, 부채 원인추적, 모바일 CSS 모두 검증.

---

## 13. 버그 수정 — 📱 모바일 구글 로그인 리다이렉트 복귀 (2026-05)

### 증상
모바일에서 구글 로그인(`signInWithRedirect`) 후 페이지가 다시 로드되며 돌아오는데,
**로그인이 됐는데도 첫 로그인 화면이 다시 표시**되어 게임으로 진입하지 못함.

### 원인 (타이밍 경쟁)
- 리다이렉트 복귀 시 `DOMContentLoaded` → `init()`이 먼저 실행되어 **로그인 카드를 무조건 표시**.
- 그 직후 Firebase가 초기화되고 `getRedirectResult`/`onAuthStateChanged`로 user가 도착하지만,
  init이 인증 도착 여부와 무관하게 로그인 화면을 띄워 둔 상태라 사용자에겐 첫 화면으로 보임.
- `onAuthStateChanged` 콜백이 `window.onAuthChange` 정의보다 먼저 올 수 있는 순서 문제도 존재.

### 해결
- **인증 대기 상태** 개념 도입: `sessionStorage('nr_redirecting')` + `window._authResolved` 플래그로
  "리다이렉트 복귀/인증 응답 대기 중"이면 로그인 버튼 대신 **"로그인 처리 중…" 스피너**(`#authLoading`) 표시.
- `init()`이 보류된 인증 결과(`window._pendingAuthUser`)가 있으면 즉시 처리(콜백이 init보다 먼저 온 경우).
- `getRedirectResult(auth)`를 명시적으로 처리하고 성공/실패 모두 플래그 정리.
- `onAuthChange(user)`: 인증 확정 시 타이머/플래그 정리, user 있으면 `proceedAfterLogin`,
  user=null이면 로그인 화면 복귀. `setAuthLoading(bool)`로 화면 전환 일원화.
- 안전장치: 일정 시간(리다이렉트 8s / 일반 3.5s) 내 인증 결과가 없으면 로그인 화면으로 자동 복귀.
- `signInWithGoogle`/`playAsGuest`도 처리중 표시·플래그를 올바르게 set/clear.

### 검증
- jsdom 인증 흐름 테스트(`test_auth.js`) **17/17 통과**: 리다이렉트 복귀→생성화면, 인증 선도착 보관처리,
  기존 국가 유저 즉시 게임진입, user=null 확정 시 로그인화면 복귀 4시나리오 검증.
- 기존 기능 테스트 **105/105 통과**(회귀 없음).
- ⚠️ 실기기 최종 확인 필요: Firebase 콘솔의 **승인된 도메인(Authorized domains)**에 GitHub Pages
  도메인이 등록돼 있어야 리다이렉트 로그인이 완료됨(코드가 아닌 콘솔 설정 사항).

---

*최종 업데이트: 2026-05 (📱 모바일 구글 로그인 리다이렉트 복귀 버그 수정) / 작성: Claude (Ryan의 NationRise 프로젝트 작업 중)*

---

## 14. 변경 이력 — 🎮 밸런스/UX 4종 (2026-05)

### ⚖️ 경제 체력/GDP 하락 완화 (방치 패널티 대폭 축소)
- **체력 감소량**: 틱당 `-1.2` → **`-0.0025`** (약 480배 완화). 방치해도 사실상 안전.
- **GDP 하락 제거**: 체력이 낮아도 baseRate가 음수가 되지 않게 변경(최악 시 0=성장 정체).
  - 기존: health<40에서 -0.005~-0.06%/틱(하락) → 변경: 0.008/0.002/0%(정체까지만).
- **방치 시 절대 하락 없음 보장**: worldTick 성장식을 재구성.
  - `passiveRate = max(0, baseRate + allyBonus + rateAdj + buildAdj + noise)` (noise도 양수만 적용).
  - `activePenalty = min(0, debtDrag + inflAdj)` — 부채·인플레 과열은 능동적 선택의 패널티라 유지.
  - `totalRate = passiveRate + activePenalty`. 즉 **방치만으로는 안 줄고, 과다 부채/초인플레는 성장 둔화**.
- UI 문구 변경: "방치 시 GDP 하락!" → "높을수록 빠른 성장!".

### 💹 좌측 국가 리스트 → 퀵 트레이드 (PC)
- 좌측 리스트에서 국가 선택(`selectCountry`) 시 차트 상단 `#quickTrade` 바에 즉시 매수/매도 UI 노출.
- `renderQuickTrade(code)`: 가격·보유·평가손익 표시 + 수량 스테퍼(−/+)·½·최대 + 매수/매도 버튼.
- 내 나라 선택 시 자동 숨김. 기존 `buyStock/sellStock(code,qty)` 재사용(`buyStockFromQuick`/`sellStockFromQuick`).

### 🎮 경제 미니게임 — "물가 안정 작전"
- 좌우로 움직이는 물가 지표를 **안정 구간(녹색)**에서 [안정화] 탭 → 점수. 20초 내 8회 성공 시 목표 달성.
- 보상: 점수 비례 국고 + 목표 달성 시 국고 +$15B·AP +3·체력 +10. **하루 3회 제한**(`state.miniGame`).
- 인플레이션=물가 관리라는 경제 개념을 체감하는 교육 효과. 배지 `inflation_fighter`(🎮) 추가.
- 저장 3곳(state 정의/resetGameState/saveState·applyLoadedData) 반영.

### 📱 모바일 글자 겹침 방지
- 차트 헤더: `ch-left`에 `min-width:0`+`flex:1`, `ch-name` 말줄임(ellipsis) → 긴 국가명이 GDP와 겹침 방지.
- 퀵 트레이드: 모바일에서 매수/매도 컬럼을 세로 배치(`flex-direction:column`).
- 국가 리스트: `c-info min-width:0`, `c-name` 말줄임. 내 나라 상태값(`mns-val`) 말줄임.
- 차트 도구 줄바꿈 허용, 상단 네비 가로 스크롤(미니게임 버튼 추가로 항목 증가).

### 검증
- `node --check` 문법 통과 / 인라인 핸들러 참조 무결성 통과 / 신규 함수 12개 정의 확인.
- jsdom 통합 테스트 **33/33 통과**: 체력 완화(틱당 0.0025), 체력0 방치 시 GDP 무하락,
  과다부채 성장 둔화, 퀵트레이드 매수/부분매도, 미니게임 점수·보상·일일제한, miniGame 저장복원, 모바일 CSS.
- 🔒 닉네임 보호: `publicDoc`에 miniGame 등 신규 필드 누출 없음 확인.

---

*최종 업데이트: 2026-05 (🎮 체력완화·퀵트레이드·미니게임·모바일 겹침수정 4종) / 작성: Claude (Ryan의 NationRise 프로젝트 작업 중)*
