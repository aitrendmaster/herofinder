# Hero Finder — 프로젝트 인수인계 문서 (CLAUDE.md)

> 이 문서는 claude.ai에서 진행한 기획/프로토타이핑 내용을 VS Code + Claude Code 환경으로 인계하기 위한 문서입니다.
> 프로젝트 루트에 `CLAUDE.md`로 저장하면 Claude Code가 자동으로 컨텍스트로 참조합니다.
> 작성일: 2026-07-02

---

## 1. 프로젝트 개요

- **서비스명**: Hero Finder (구 명칭: 인플루언서 허브)
- **운영 주체**: PTK (대행사) — 플랫폼 주최/오너십 보유, 인플루언서 관리, 성과 데이터 관리, 삼성전자 등 광고주 연결
- **서비스 정의**: 대기업 광고주(클라이언트)가 유튜브·인스타그램·틱톡 인플루언서를 탐색하고, RFP 업무요청서를 통해 섭외하며, 캠페인 성과를 측정하는 B2B 인플루언서 매칭 플랫폼
- **벤치마킹**: revu.net (응모형/섭외형), biz.revu.net (결과보고), pt-korea.com (디자인)
- **디자인 컨셉**: 블랙/그레이/화이트 미니멀 톤, 모던 타이포그래피, 반응형 (PT KOREA 스타일)

## 2. 핵심 워크플로우 (V2 — 현재 프로토타입 기준)

```
① 인플루언서 탐색 (필터: 등급/채널/카테고리/활성도)
   ↓ 인플루언서 선택
② 업무 요청서(RFP) 작성
   - 캠페인 예산, 기간, 콘텐츠 주요 내용
   - 광고 타입: PPL / 브랜디드 콘텐츠 (+ 오프라인 활동, IP 라이센스 옵션)
   - 예상 납품 기한, 기대 효과
   ↓ 등록
③ AI 맞춤 인플루언서 추천 (매칭 점수 + 예상 KPI + ROI 효율)
   ↓ 클라이언트 선별 선택
④ 선택된 인플루언서 contact mail로 RFP 자동 송부
   ↓
⑤ 인플루언서 회신 → 클라이언트 계정 메시지함 수신 → 양방향 커뮤니케이션
```

## 3. 도메인 규칙

### 인플루언서 등급 (팔로워/구독자 기준)
| 등급 | 범위 |
|---|---|
| 메가 (mega) | 100만 이상 |
| 파워 (power) | 10만 ~ 99.99만 |
| 마이크로 (micro) | 1만 ~ 9.99만 |
| 나노 (nano) | 2천 ~ 1만 |

### 채널 (Phase 1)
- **YouTube**: 한국만
- **Instagram**: 한국만
- **TikTok**: 한국, 미국, 동남아 주요국 (인도네시아, 베트남, 태국, 필리핀, 말레이시아)
- ⚠️ 중국은 틱톡 미서비스 — 더우인(抖音)은 별도 생태계, **Phase 2로 분리 결정됨**

### 콘텐츠 카테고리
건강, 뷰티, IT & Tech, V log, 여행, 재테크 & 금융, 문화, 교양, 푸드, 패션, 엔터, 라이프스타일
(확장 가능한 마스터 테이블로 관리할 것)

### 활성 인플루언서 리스트
- **주간 단위 자동 업데이트** (기획 초기 월간 → 주간으로 변경됨)
- 기준: 구독/팔로워 증가, 조회수, 참여율(engagement) 활성 지표
- 주간 스냅샷 누적 저장 → 성장률/순위변동 자체 산출이 핵심 차별화

### KPI 정의
노출수(도달), 클릭, 구매전환, 공유, ROI, CPI, CPC, 참여율

## 4. 기술 아키텍처 (확정 방향)

```
[Frontend]  Vercel
  - Next.js (권장: App Router) + Tailwind CSS
  - 현재 프로토타입: 단일 파일 React (Hero Finder V2) → 페이지/컴포넌트 분리 필요

[Backend]  Render
  - Node.js (Express/NestJS) 또는 Python (FastAPI) — 미확정, 데이터 파이프라인 고려 시 FastAPI 유력
  - PostgreSQL (Render Managed) — 주간 스냅샷 시계열 저장
  - Cron Job (Render Cron) — 주간 수집 스케줄러 (매주 월 04:00 KST 제안)
  - 이메일 발송: SendGrid 또는 AWS SES (RFP 자동 송부 + 회신 수신 웹훅)

[AI]
  - 매칭/추천, 콘텐츠 가이드 생성, 인사이트 리포트: Anthropic API (Claude) 연동 예정
```

### 데이터 수집 전략 (하이브리드 — 논의 확정)
| 플랫폼 | Phase 1 소스 | 비고 |
|---|---|---|
| YouTube (KR) | **YouTube Data API v3 (공식)** | 합법·저렴. regionCode=KR. 일 쿼터 10,000 유닛 → 시드 리스트 관리 |
| Instagram (KR) | **ScrapeCreators API** 또는 Modash/HypeAuditor | 공식 API로 임의 탐색 불가. 벤더 3곳 견적 비교 후 결정 |
| TikTok (KR/US/SEA) | **ScrapeCreators로 즉시 시작** + TTCM Open API 파트너 신청 병행 | 승인 시 공식 전환. 승인 2~4개월 소요 예상 |

- Apify는 Phase 2 보완용으로 보류 결정
- ⚠️ **법무 검토 필수**: Instagram 데이터 재판매 가능 여부, 한국 개인정보보호법(이메일 등 연락처 수집·저장), 벤더 약관의 sub-licensing 조항
- 데이터 소스 이중화 원칙: 벤더 중단 대비 최소 2개 소스 또는 백업 계획

### 주간 파이프라인 구조
```
[Cron: 매주 월 04:00 KST]
  ├─ YouTube Collector (Data API v3, KR)
  ├─ Instagram Collector (ScrapeCreators)
  └─ TikTok Collector (ScrapeCreators → TTCM API 전환 예정)
      ↓
[정규화 & 중복제거] → 등급 자동 분류 (mega/power/micro/nano)
      ↓
[활성도 스코어링] → 전주 대비 변화율 (구독·조회·참여율)
      ↓
[DB 스냅샷 저장] → "🔥 활성" 리스트 갱신 + 순위 변동 기록
```

## 5. DB 스키마 초안

```sql
-- 인플루언서 마스터
influencers (
  id BIGSERIAL PK,
  name VARCHAR, channel ENUM('youtube','instagram','tiktok'),
  channel_id VARCHAR,           -- 플랫폼 고유 ID
  country VARCHAR(2),           -- KR, US, ID, VN, TH, PH, MY
  category_id FK → categories,
  tier ENUM('mega','power','micro','nano'),  -- 최신 스냅샷 기준 자동 갱신
  contact_email VARCHAR,        -- ⚠️ 개인정보: 암호화 저장, 접근 로그
  cost_range_min INT, cost_range_max INT,
  created_at, updated_at
)

-- 주간 스냅샷 (시계열 핵심 테이블)
influencer_snapshots (
  id BIGSERIAL PK,
  influencer_id FK,
  week_start DATE,              -- 주차 키
  followers INT, monthly_views BIGINT,
  engagement_rate DECIMAL, growth_rate DECIMAL,
  is_trending BOOLEAN,          -- 활성 스코어 임계값 통과 여부
  UNIQUE(influencer_id, week_start)
)

categories ( id, name, sort_order )

-- 클라이언트 & 캠페인
clients ( id, company_name, contact_email, ... )
campaigns ( id, client_id FK, name, budget_range, period_start, period_end,
  content_detail TEXT, ad_type ENUM('ppl','branded'),
  include_offline BOOL, need_ip_license BOOL,
  deadline DATE, expectation TEXT, status, created_at )

-- RFP 발송 & 상태
rfp_dispatches ( id, campaign_id FK, influencer_id FK,
  sent_at, status ENUM('sent','opened','replied','accepted','declined'),
  match_score INT, estimated_kpi JSONB )

-- 메시지 (이메일 회신 연동)
messages ( id, campaign_id FK, influencer_id FK,
  direction ENUM('inbound','outbound'), body TEXT,
  email_message_id VARCHAR,     -- 이메일 스레딩용
  created_at )
```

## 6. API 엔드포인트 초안

```
GET  /api/influencers?tier=&channel=&category=&trending=&country=&page=
GET  /api/influencers/:id
GET  /api/influencers/:id/snapshots        # 주간 추이
GET  /api/categories

POST /api/campaigns                         # 브리프(RFP) 등록
GET  /api/campaigns/:id
POST /api/campaigns/:id/ai-recommend        # AI 매칭 추천
POST /api/campaigns/:id/dispatch            # 선택 인플루언서에 RFP 이메일 송부

GET  /api/campaigns/:id/messages
POST /api/campaigns/:id/messages            # 아웃바운드 (이메일 발송)
POST /api/webhooks/email-inbound            # 인플루언서 회신 수신 (SendGrid Inbound Parse)

# 관리자
POST /api/admin/pipeline/run                # 수동 수집 트리거
GET  /api/admin/pipeline/status             # 플랫폼별 수집 상태/성공률/크레딧
```

## 7. 환경변수 (.env 초안)

```
# Backend (Render)
DATABASE_URL=
YOUTUBE_API_KEY=
SCRAPECREATORS_API_KEY=
TIKTOK_TTCM_CLIENT_ID=          # 파트너 승인 후
TIKTOK_TTCM_CLIENT_SECRET=
SENDGRID_API_KEY=
ANTHROPIC_API_KEY=              # AI 매칭/가이드 생성
JWT_SECRET=

# Frontend (Vercel)
NEXT_PUBLIC_API_BASE_URL=       # Render 백엔드 URL
```

## 8. 현재 프로토타입 상태

**최신 아티팩트**: "Hero Finder - Influencer Hub Prototype" (단일 파일 React, Tailwind, 상태 기반 네비게이션)

구현 완료 (목업 데이터 기준):
- ✅ 인플루언서 탐색: 등급/채널/카테고리/활성도 필터, 카드 UI (팔로워·월조회·참여율·성장률·예상 섭외비)
- ✅ RFP 브리프 폼: 예산, 기간, 콘텐츠 내용, PPL/브랜디드 선택, 오프라인/IP 라이센스 옵션, 납품기한, 기대효과
- ✅ AI 추천 화면: 매칭 점수(현재 규칙 기반 시뮬레이션), 예상 KPI, 선택 → 송부
- ✅ RFP 송부 확인 모달 (수신자 이메일 목록)
- ✅ 메시지함: 인플루언서 회신 목업, 양방향 채팅 UI

참고용 이전 산출물 (V1, 대화 히스토리에 있음):
- 전체 IA / 사이트맵 / 메뉴트리 (홈, 캠페인, 인플루언서, 브랜드, 분석, 메시징, 관리자, 설정, 모바일)
- 응모형 캠페인 상세 페이지 (revu 스타일: 캠페인 정보/신청현황 탭, 10명 모집 200명 신청)
- 브랜드 대시보드 (recharts 바/파이 차트, 클릭 시 캠페인별 상세)
- 분석 리포트 (AI 인사이트: 데이터 해석 + 개선 제안 + 맞춤 질문)
- 관리자 대시보드 (사용자/캠페인/AI 모델 관리)
- 로고/키비주얼 SVG

## 9. TODO (우선순위 순)

### Phase 1 — MVP
- [ ] 모노레포 or 프론트/백 분리 레포 세팅 결정
- [ ] Next.js 프로젝트 생성, 프로토타입을 페이지/컴포넌트로 분리 (`/discovery`, `/brief`, `/recommend`, `/messages`)
- [ ] FastAPI(또는 NestJS) 백엔드 스캐폴딩 + PostgreSQL 스키마 마이그레이션 (위 5번 참조)
- [ ] YouTube Data API 수집기 구현 (KR 시드 리스트 → 주간 스냅샷)
- [ ] ScrapeCreators 연동 (Instagram KR, TikTok KR/US/SEA) — 계약/견적 선행
- [ ] Render Cron 주간 파이프라인 + 활성도 스코어링 로직
- [ ] RFP 이메일 발송 (SendGrid) + Inbound Parse 웹훅으로 회신 수신
- [ ] AI 매칭: 규칙 기반 → Claude API 기반 매칭 사유 생성으로 고도화
- [ ] 클라이언트 인증 (이메일 로그인, JWT)
- [ ] 관리자: 파이프라인 상태 대시보드

### 병행 트랙
- [ ] TikTok TTCM Open API 파트너 신청 (TikTok Korea 컨택 → 소개서 제출, 2~4개월 소요 예상)
- [ ] 법무 검토: Instagram 데이터 재판매, 개인정보(이메일) 수집·저장, 벤더 약관
- [ ] Instagram 데이터 벤더 3곳 견적 비교 (ScrapeCreators / Modash / HypeAuditor)

### Phase 2 (보류 항목)
- [ ] 더우인(중국) 연동
- [ ] Apify 보완 수집
- [ ] 응모형(공개 모집) 캠페인 모듈 — V1 기획 참조
- [ ] 결과보고 페이지 (biz.revu.net 벤치마크) + AI 인사이트 리포트
- [ ] 인플루언서용 콘텐츠 스크립트 생성 (블로그/인스타/유튜브별)
- [ ] 모바일 앱 연동

## 10. 주요 의사결정 이력

| 결정 | 내용 |
|---|---|
| 서비스명 | 인플루언서 허브 → **Hero Finder** |
| 업데이트 주기 | 월간 → **주간** |
| 중국 시장 | 틱톡 미서비스 확인, 더우인은 Phase 2 분리 |
| 데이터 수집 | 하이브리드: YouTube 공식 API + ScrapeCreators + TTCM 파트너 병행 |
| Apify | Phase 1 제외, Phase 2 보완용 |
| 배포 | Frontend **Vercel** / Backend **Render** |
| 후속 개발 | VS Code + Claude Code |

## 11. Claude Code 작업 시 참고

- 디자인 톤: 블랙(#000)/그레이/화이트 유지, 액센트 최소화. Tailwind 사용
- 프로토타입 코드의 `INFLUENCERS` 목업 배열이 곧 API 응답 스키마의 기준 — 백엔드 응답을 이 형태에 맞추면 프론트 전환 비용 최소화
- `matchScore` 산식(현재): `60 + engagement*2 + growth*0.5 + (trending ? 8 : 0)`, 상한 98 — 추후 Claude API 기반으로 교체 예정이나 폴백 로직으로 유지 권장
- 개인정보(contact_email)는 목록 API 응답에서 제외하고 RFP 송부 시점에만 서버 측에서 사용할 것
