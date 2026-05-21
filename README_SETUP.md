# 🌍 NationVault — 국가주식 거래소

전 세계 194개국을 주식처럼 거래하는 경제 교육 게임. GitHub Pages + Firebase로 배포되며, PC·모바일 어디서나 접속하고 거래 내역이 동기화됩니다.

---

## 📂 파일 구성

| 파일 | 역할 |
|------|------|
| `index.html` | 게임 본체 (단일 파일) |
| `countries.json` | 194개국 마스터 데이터 (GDP, 티어, 국기) |
| `prices.json` | 시간별 가격 데이터 (GitHub Actions가 자동 생성) |
| `price_engine.py` | 가격 생성 스크립트 |
| `gen_countries.py` | 국가 마스터 생성 스크립트 (최초 1회용) |
| `.github/workflows/update-prices.yml` | 1시간마다 가격 갱신 자동화 |

---

## 🚀 배포 방법 (3단계)

### 1단계: GitHub 저장소에 업로드

```bash
git init
git add .
git commit -m "init: NationVault game"
git branch -M main
git remote add origin https://github.com/<사용자명>/<저장소명>.git
git push -u origin main
```

### 2단계: GitHub Pages 활성화

1. 저장소 → **Settings** → **Pages**
2. **Source**: `Deploy from a branch`
3. **Branch**: `main` / `/ (root)` 선택 → **Save**
4. 몇 분 후 `https://<사용자명>.github.io/<저장소명>/` 에서 접속 가능

### 3단계: GitHub Actions 권한 설정

1. 저장소 → **Settings** → **Actions** → **General**
2. **Workflow permissions** → `Read and write permissions` 선택 → **Save**
3. **Actions** 탭 → `Update Prices Hourly` → `Run workflow`로 첫 실행
   - 이후 매시간 자동으로 `prices.json`이 갱신됩니다

> ⚠️ GitHub Actions의 schedule은 무료 저장소에서 약간의 지연이 있을 수 있습니다 (정확히 정각이 아닐 수 있음). 정상입니다.

---

## 🔥 Firebase 설정 (사용자 데이터 동기화)

Firebase 없이도 **게스트 모드**로 플레이 가능하지만(브라우저 localStorage 저장), 구글 로그인으로 **모든 기기 동기화**를 원하면 아래를 따르세요.

### 1. Firebase 프로젝트 생성
1. https://console.firebase.google.com 접속
2. **프로젝트 추가** → 이름 입력 (예: nationvault)
3. Google Analytics는 꺼도 됨

### 2. 웹 앱 등록
1. 프로젝트 개요 → **</> (웹)** 아이콘 클릭
2. 앱 닉네임 입력 → **앱 등록**
3. 표시되는 `firebaseConfig` 객체를 복사

### 3. 인증 활성화
1. 좌측 **Authentication** → **시작하기**
2. **Sign-in method** → **Google** 활성화 → 저장

### 4. Firestore 활성화
1. 좌측 **Firestore Database** → **데이터베이스 만들기**
2. **프로덕션 모드**로 시작
3. **규칙(Rules)** 탭에서 아래로 교체:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // 사용자는 자신의 데이터만 읽기/쓰기 가능
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
  }
}
```

### 5. 승인된 도메인 추가
1. **Authentication** → **Settings** → **승인된 도메인**
2. `<사용자명>.github.io` 추가

### 6. index.html에 설정 입력
`index.html`에서 아래 부분을 찾아 복사한 값으로 교체:

```javascript
const firebaseConfig = {
  apiKey: "여기에",
  authDomain: "여기에",
  projectId: "여기에",
  storageBucket: "여기에",
  messagingSenderId: "여기에",
  appId: "여기에"
};
```

저장 후 다시 push하면 구글 로그인이 활성화됩니다.

> 🔒 **보안 안내**: Firebase 웹 apiKey는 공개되어도 안전합니다(클라이언트 식별용). 실제 데이터 보호는 위의 Firestore 규칙이 담당합니다.

---

## ⏱️ 작동 원리

### 현실시간 동기화
- 게임은 **실제 시각 기반**으로 가격을 계산합니다 (가속 없음).
- `prices.json`의 시간별 기준가 + 현재 분/초 기반 결정론적 시뮬레이션을 적용.
- 따라서 **모든 사용자가 같은 시각에 같은 가격**을 봅니다.

### 가격 변동 흐름
```
매시간 (GitHub Actions)
  → price_engine.py 실행
  → 각 국가 뉴스 평가 (결정론적)
  → 감성 점수 → 가격 변동 (-7%~+7%)
  → prices.json 커밋
      ↓
클라이언트 (브라우저)
  → prices.json의 기준가 로드
  → 현재 시각 기반 분/초 단위 미세 변동 적용
  → 1초마다 화면 갱신
```

---

## 🔧 국가 데이터 수정

`gen_countries.py`의 `GDP_DATA` 딕셔너리를 수정 후:
```bash
python gen_countries.py   # countries.json 재생성
```

---

## 🎮 다음 발전 방향

- [ ] 실제 뉴스 API + Gemini 연동 (별도 백엔드 필요)
- [x] 학습 퀴즈 모드
- [x] 수익률 랭킹보드
- [x] 배지·업적 시스템
- [x] 경제 용어 사전 + 뉴스 상세 팝업
- [ ] 캔들 차트 전환
- [ ] 푸시 알림 (PWA)

---

## 🆕 v3.0 신규 기능

### 🏆 수익률 랭킹
- 상단 메뉴 → **랭킹** 클릭
- 전체/학교/친구 탭으로 순위 확인
- **Firebase 설정 전**: AI 트레이더 18명과 경쟁 (시간 기반 결정론적 수익률)
- **Firebase 설정 후**: 실제 전 세계 플레이어와 경쟁 (아래 확장 가이드 참고)

### 🎓 경제 퀴즈
- 매일 5문제, 정답당 가상자금 $5,000 보상
- 날짜별로 같은 문제 출제 (하루 1회 응시)
- 만점 시 '퀴즈 마스터' 배지 획득

### 🎖️ 배지 시스템
- 9종 배지 (첫 거래, 분산 투자, 고수익, 세계 일주 등)
- 조건 달성 시 자동 획득 + 알림

### 📖 경제 용어 사전 + 뉴스 상세 팝업
- 뉴스 클릭 → 화면 중앙에 **요약 + 영향 해설 + 관련 용어** 팝업
- 관련 용어 칩 클릭 → 용어 설명 팝업
- 상단 메뉴 → **사전**에서 12개 핵심 경제 용어 검색

---

## 🔓 랭킹보드 실제 사용자 연동 (Firebase 확장)

현재 랭킹은 AI 트레이더와 경쟁하는 구조입니다. 실제 전 세계 사용자 랭킹을 원하면:

### 1. Firestore에 공개 랭킹 컬렉션 추가
`saveState()` 함수에서 사용자 데이터 저장 시, 별도의 공개 랭킹 문서도 갱신하도록 확장합니다. `index.html`의 `saveState`에 아래를 추가:

```javascript
// 공개 랭킹용 (수익률만 공개)
if (currentUser && window.fb) {
  await window.fb.setDoc(
    window.fb.doc(window.fb.db, 'rankings', currentUser.uid),
    { name: currentUser.displayName, return: getMyReturn(),
      trades: state.stats.totalTrades, updatedAt: Date.now() }
  );
}
```

### 2. 랭킹 읽기 (renderRanking 확장)
`getDocs`로 `rankings` 컬렉션을 불러와 봇 대신 실제 사용자를 표시합니다.

### 3. Firestore 규칙 추가
```javascript
match /rankings/{userId} {
  allow read: if true;                       // 누구나 랭킹 조회 가능
  allow write: if request.auth != null && request.auth.uid == userId;
}
```

> 이렇게 하면 게스트는 AI 트레이더와, 로그인 사용자는 실제 전 세계 플레이어와 경쟁합니다.

---

*Generated for Ryan · NationVault v3.0*
