# GrowthStacker Auto Blog Pipeline

**100% 무료** | Gemini API + GitHub Actions + Blogger API

growthstacker.blogspot.com에 매일 자동으로 SEO 최적화 포스팅을 업로드하는 파이프라인입니다.

---

## 🏗️ 아키텍처

```
GitHub Actions (Cron) → Gemini 2.0 Flash → SEO 처리 → Blogger API v3
         ↓
  rotation_state.json 자동 업데이트 (AI → Review → Tutorial → 반복)
```

## ✅ 사용 툴 (전부 무료)

| 툴 | 용도 | 무료 한도 |
|---|---|---|
| GitHub Actions | 스케줄러 + 호스팅 | 월 2,000분 (충분) |
| Gemini 2.0 Flash | 콘텐츠 생성 | 15 RPM, 1M TPM |
| Blogger API v3 | 자동 포스팅 | 무제한 |
| Cloudflare Worker | API 프록시 | 10만 req/일 |

---

## 🚀 설정 가이드 (Step by Step)

### Step 1: Google Cloud 프로젝트 설정

1. [console.cloud.google.com](https://console.cloud.google.com) 접속
2. 새 프로젝트 생성 (예: `growthstacker-blog`)
3. **API 및 서비스 → 라이브러리** 검색:
   - `Blogger API v3` → 사용 설정
4. **사용자 인증 정보 → 만들기 → OAuth 2.0 클라이언트 ID**
   - 애플리케이션 유형: **데스크톱 앱**
   - 이름: `GrowthStacker Bot`
   - 생성 후 **클라이언트 ID**, **클라이언트 보안 비밀** 복사

### Step 2: Gemini API Key 발급

1. [aistudio.google.com](https://aistudio.google.com) 접속
2. **Get API Key** → 새 API 키 생성
3. 키 복사 (한 번만 보임)

### Step 3: Blogger Blog ID 확인

1. [blogger.com](https://blogger.com) → growthstacker.blogspot.com 선택
2. URL에서 숫자 ID 복사: `blogger.com/blog/posts/XXXXXXXXXX` → `XXXXXXXXXX`가 Blog ID

### Step 4: OAuth Refresh Token 발급 (1회만 실행)

```bash
# 로컬에서 실행
git clone https://github.com/YOUR_USERNAME/growthstacker-auto
cd growthstacker-auto
pip install requests
python3 scripts/setup_oauth.py
```

브라우저에서 구글 로그인 → 승인 → 터미널에 토큰 출력됨

### Step 5: GitHub Secrets 등록

GitHub 리포지토리 → **Settings → Secrets and variables → Actions**

| Secret 이름 | 값 |
|---|---|
| `GOOGLE_CLIENT_ID` | Step 1에서 복사한 클라이언트 ID |
| `GOOGLE_CLIENT_SECRET` | Step 1에서 복사한 클라이언트 보안 비밀 |
| `GOOGLE_REFRESH_TOKEN` | Step 4 스크립트 출력값 |
| `BLOGGER_BLOG_ID` | Step 3에서 확인한 Blog ID |
| `GEMINI_API_KEY` | Step 2에서 발급한 API 키 |

### Step 6: 리포지토리 Push & 활성화

```bash
git add .
git commit -m "initial setup"
git push origin main
```

GitHub → Actions 탭 → `Auto Blog Publisher` 워크플로우 확인

### Step 7: 첫 테스트 실행 (선택)

GitHub Actions 탭 → `Auto Blog Publisher` → **Run workflow** 클릭

---

## 📅 스케줄

- **실행 시간**: 매일 09:00 UTC (한국시간 오후 6시, 미국 동부 오전 5시)
- **포스팅 순서**: AI/수익화 → 제품 리뷰 → 테크 튜토리얼 → 반복
- **주제 순환**: 10개 시드 토픽 소진 후 자동 재시작

---

## 🔒 보안 설계

- 모든 API 키는 GitHub Secrets (AES-256 암호화)에만 저장
- `.env.local`은 로컬 전용, `.gitignore`로 커밋 방지
- Access Token은 매 실행마다 Refresh Token으로 새로 발급 (만료 방지)
- 로그 파일은 민감 정보(콘텐츠, 토큰) 제외하고 저장
- Cloudflare Worker 사용 시 X-Worker-Secret 헤더로 추가 인증

---

## 📁 디렉토리 구조

```
growthstacker-auto/
├── .github/
│   └── workflows/
│       └── auto-publish.yml     # GitHub Actions 워크플로우
├── scripts/
│   ├── generate_post.py         # 메인 생성 스크립트
│   ├── setup_oauth.py           # 1회용 OAuth 설정
│   ├── test_local.py            # 로컬 테스트
│   └── cloudflare-worker.js     # CF Worker (선택)
├── config/
│   ├── topics.json              # 주제 + 키워드 전략
│   └── rotation_state.json      # 현재 순환 위치 (자동 업데이트)
├── logs/                        # 발행 로그 (날짜별)
├── wrangler.toml                # Cloudflare 설정 (선택)
├── .gitignore
└── README.md
```

---

## ❓ 문제해결

**Q: "No candidates in response" 오류**
→ Gemini API 무료 한도 초과. 다음 날 다시 시도.

**Q: "401 Unauthorized" from Blogger**
→ Refresh Token 만료. `setup_oauth.py` 재실행 후 GitHub Secret 업데이트.

**Q: rotation_state.json 커밋 실패**
→ GitHub Actions에 `contents: write` 권한 있는지 확인.

**Q: 포스팅이 초안으로 저장됨**
→ `payload`의 `"status": "LIVE"` 확인. Blogger API 권한 재확인.

---

## 📈 예상 수익 타임라인

| 기간 | 포스트 수 | 예상 월간 방문자 | AdSense 예상 |
|---|---|---|---|
| 1개월 | 30개 | 100-500 | 심사 중 |
| 3개월 | 90개 | 1,000-5,000 | $5-30 |
| 6개월 | 180개 | 5,000-20,000 | $30-150 |
| 12개월 | 360개 | 20,000+ | $100-500+ |

*실제 수치는 키워드 경쟁도, 콘텐츠 품질에 따라 크게 다를 수 있습니다.*
