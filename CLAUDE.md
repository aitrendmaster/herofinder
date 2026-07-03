# Hero Finder — 프로젝트 인수인계 문서 (CLAUDE.md)

> 이 문서는 claude.ai에서 진행한 기획/프로토타이핑 내용을 VS Code + Claude Code 환경으로 인계하기 위한 문서입니다.
> 프로젝트 루트에 `CLAUDE.md`로 저장하면 Claude Code가 자동으로 컨텍스트로 참조합니다.
> 작성일: 2026-07-02

---

## 0. 미션 & 운영 원칙 (2026-07-02, YJ 확정)

- **목표**: 인플루언서 섭외 + 소통 운영 + 콘텐츠 제작 점검을 아우르는 **통합 에이전트 솔루션**
- **주요 고객**: 인플루언서 섭외·마케팅 협업이 필요한 클라이언트 — 대기업 ~ 중소기업·소규모 사업자, 그리고 **광고대행사(에이전시)**
- **핵심 가치**: ① 크리에이터 풀 큐레이션 품질 ② 정보 데이터 정확도 ③ KPI·ROI 측정
- **절대 제약**: 외부 API·외부 솔루션 연결이 필요하면 **반드시 YJ 승인을 먼저 받는다**
- 리드: Fable (메인 세션) — 오케스트레이션 규칙은 워크스페이스 루트 CLAUDE.md §0 참조

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
- [x] 모노레포 세팅 (frontend Next.js + backend FastAPI, repo: aitrendmaster/herofinder)
- [x] Next.js 프로젝트 생성 (`/dashboard`, `/discovery`, `/brief`, `/recommend`, `/messages`, `/creator`) — Vercel 배포: herofinder-ebon.vercel.app
- [x] FastAPI 백엔드 + PostgreSQL — Render 배포: herofinder.onrender.com (srv-d93hgn4vikkc73a9osng)
- [x] YouTube Data API 수집기 (시드: `app/data/seed_channels.json` — PTK 리스트업 실채널 13개, 2026-07-03 프로덕션 반영)
- [ ] ScrapeCreators 연동 (Instagram KR, TikTok KR/US/SEA) — 시드 계정 리스트 필요
- [ ] Render Cron 주간 파이프라인 등록 (현재 수동 트리거: POST /api/admin/pipeline/run)
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

## 11. 확장 워크플로우 V3 (2026-07-02 확정 — 계약·납품·정산·리스크)

V2 워크플로우(①탐색→⑤메시지) 이후 단계를 포함한 전체 수명주기:

```
① 탐색 → ② RFP 작성(확장) → ③ AI 추천 + 제안 리스트/제안서 생성 → ④ RFP 송부
   ↓
⑤ 크리에이터 회신·논의 → ⑥ 크리에이터 콘텐츠 기획 방향 + 1차 견적 (Quote)
   ↓ 견적·업무 스콥 합의
⑦ 가계약 (Contract: provisional) → 클라이언트가 브랜드 가이드 전달 (BrandGuideline)
   ↓
⑧ 스토리보드/기획안/가안 영상 제출 (Storyboard) → 클라이언트 내부 보고·법무 검토 → confirm
   ↓
⑨ 최종 콘텐츠 제작 → 일부공개/비공개 URL 납품 (Deliverable) → 클라이언트 검수 → public 공개
   ↓
⑩ 정산 (Settlement: 세금계산서/현금입금/플랫폼 간편정산 옵션)
```

### 11-1. RFP 확장 필드 (①번 요구사항)

업무 범위에 따라 크리에이터 견적이 달라지므로 RFP에 반드시 포함:

| 필드 | 값 | 설명 |
|---|---|---|
| `content_format` | `shortform` / `longform` / `package` | 숏폼·롱폼·셋트 패키지 |
| `longform_minutes` | 5 / 10 / 15 / 20+ | 롱폼 길이 구간 |
| `shortform_minutes` | 1 / 2 / 3 | 숏폼 길이 구간 |
| `additional_rewards` | TEXT | 클라이언트 제공 추가 보상 (예: 크레딧, 등급별 리워드, 튜토리얼 보너스 배수) |
| `provided_resources` | TEXT | 클라이언트 제공 재원·소재 (제품, 계정, 크레딧 등) |
| `must_include` | TEXT | 다뤘으면 하는 내용·필수 가이드 (해시태그, 멘션, 워터마크, UID 제출 등) |

참고: Kling AI Dance Challenge류 캠페인 메일이 일반 요청 형태 — 보상 티어표, 필수 해시태그/멘션/워터마크, 제출 기한, T&C가 함께 온다.

### 11-2. 제안 리스트 & 제안서 (②번 요구사항)

- RFP는 Hero Finder AI가 정리 → 채널별 인플루언서를 **목적성 + reason why**와 연결한 제안 리스트 제공
- 산출물 2종 (참고: `refer/` 폴더의 PTK 실제 문서 — 구조만 차용, 브랜드명 비노출):
  - **리스트업 Excel**: 채널별 시트, 13컬럼 (No./카테고리[병합]/채널명/구독자수/평균조회수/URL/진행가능여부/일정/비용/비고/레퍼런스/추천사유/썸네일)
  - **제안서 PPT** (클라이언트 내부 보고용): 표지 → 운영 개요 → 큐레이션 전략(유형 3개) → 유형별 상세 → 리스트 테이블 → E.O.D
- 템플릿 정의: `.claude/skills/herofinder-proposal/SKILL.md` (범용, 브랜드 가변 처리)
- 구현: `backend/app/services/proposal_service.py`

### 11-3. 계약 단계 (③번 요구사항)

- 크리에이터 accept 후: 콘텐츠 기획 방향(방향/형식/길이) + 업무범위 기준 **1차 견적(Quote)** 제출
- 견적·스콥 합의 → **가계약(provisional)** → 실질 계약 성립(active)
- 가계약 후 클라이언트는 **브랜드 가이드(BrandGuideline)** 전달: 톤앤매너, 브랜드 정책, Do & Don't
  - 영업자료·제품자료 등 기밀 포함 가능 → `is_confidential` 플래그 + 열람 로그 (보안 옵션)

### 11-4. 스토리보드 검토 (④번 요구사항)

- 크리에이터 제출물 유형: 스토리보드/기획안 문서, 유사 레퍼런스 영상, 1차 가안 영상 중 택1 이상
- 클라이언트는 내부 보고·**법무 검토 필수** → confirm 후 최종 제작 진행
- 상태: `submitted → reviewing → confirmed | rejected(피드백 포함)`

### 11-5. 납품·검수·정산 (⑤번 요구사항)

- 납품: 채널 형식에 맞춰 **일부공개(unlisted)/비공개 URL**로 납품일 전까지 제출
- 클라이언트 검수 통과 → public 공개 결정
- 정산: `tax_invoice`(세금계산서) / `cash_transfer`(현금입금) / `platform`(Hero Finder 간편정산 — 옵션 기능)

### 11-6. 리스크 방지 — 블랙리스트 정책 (⑥번 요구사항)

플랫폼 우회(직거래) 방지:

| 대상 | 위반 | 페널티 |
|---|---|---|
| 크리에이터 | 클라이언트와 직접 계약 | 블랙 경고 → AI 추천 제외 또는 최후순위 강등 |
| 클라이언트 | 직접 정산 몰래 진행 | 블랙 마킹 → 이후 서비스 이용 시 추가 과금, find 기능 제약, 재계약 차단 |

- AI 추천(`ai-recommend`)은 블랙리스트 크리에이터를 제외(`exclude`)하거나 최후순위(`deprioritize`)로 처리
- 테이블: `blacklist_entries (entity_type, entity_id, reason, penalty, note, created_at)`

### 11-7. V3 추가 API

```
POST /content? — 기존 V2 API에 추가:
POST /api/campaigns/{id}/proposal              제안서 생성 Job (xlsx + pptx)
GET  /api/proposal-jobs/{job_id}               Job 상태 + 다운로드 경로
POST /api/campaigns/{id}/quotes                크리에이터 1차 견적 등록
PATCH /api/quotes/{id}                         견적 상태 변경 (negotiating/agreed)
POST /api/campaigns/{id}/contracts             가계약 생성 (quote 합의 시)
PATCH /api/contracts/{id}                      계약 상태 전환 (provisional→active→completed)
POST /api/contracts/{id}/guidelines            브랜드 가이드 전달 (기밀 플래그)
GET  /api/contracts/{id}/guidelines            가이드 열람 (기밀은 열람 로그)
POST /api/contracts/{id}/storyboards           스토리보드/가안 제출
PATCH /api/storyboards/{id}                    검토 상태 변경 (confirm/reject + 피드백)
POST /api/contracts/{id}/deliverables          최종안 URL 납품
PATCH /api/deliverables/{id}                   검수 (approve → published)
POST /api/contracts/{id}/settlements           정산 생성 (방식 선택)
POST /api/admin/blacklist                      블랙리스트 등록
GET  /api/admin/blacklist                      블랙리스트 조회

# 대시보드·알림 (클라이언트)
GET  /api/dashboard                            전체 캠페인 + 진행 단계 + 미확인 알림 수
GET  /api/campaigns/{id}/progress              10단계 프로세스 라인바 데이터
GET  /api/notifications                        클라이언트 알림 (?unread_only=)
PATCH /api/notifications/{id}/read             읽음 처리
POST /api/admin/reminders/run                  리마인드 스윕 수동 트리거 (자동 6h 주기)

# 크리에이터 포털 (X-Creator-Token 헤더 인증)
POST /api/auth/creator/login                   이메일 + 접속 코드 로그인
GET  /api/creator/me                           내 세션 정보
GET  /api/creator/rfps                         받은 RFP 목록 (+진행 단계)
POST /api/creator/campaigns/{id}/quotes        견적 제출 (influencer_id는 토큰 기준 강제)
GET/POST /api/creator/campaigns/{id}/messages  클라이언트와 메시지
GET  /api/creator/notifications                내 알림 (+/{id}/read)
```

### 11-8. 크리에이터 계정 & 알림 규칙

- **계정 자동 발급**: RFP 송부(`dispatch`) 시 `creator_accounts`에 자동 생성 — 접속 코드(uuid)가 RFP 이메일에 포함됨. 포털: `/creator` (정식 JWT는 Phase 2-4)
- **진행 단계 10단계** (`services/progress.py`): RFP 등록→AI 추천→RFP 송부→크리에이터 회신→견적 합의→가계약→스토리보드 확정→납품→검수/공개→정산 완료. DB 실제 상태로 판정(별도 상태 필드 동기화 불필요)
- **알림 2종** (`services/notification_service.py`):
  - `event` — 상태 전환 시 즉시 (송부·견적·계약·가이드·스토리보드·납품·검수·정산 전 지점에 훅)
  - `reminder` — 미처리 업무 스윕 (6시간 주기 백그라운드 + 수동 트리거, 동일 대상·사유 24h 중복 방지)
- 크리에이터 알림은 이메일 발송도 시도 (SendGrid 미설정 시 시뮬레이션 로그)

### 11-9. 기밀 정보 노출 금지 규칙 (반드시 준수)

| 정보 | 규칙 |
|---|---|
| **전체 캠페인 예산 (`budget_range`)** | **크리에이터에게 절대 비노출** — 인플루언서별 단가가 제각각이라 공유 금지. 크리에이터 API 응답·RFP 이메일·포털 화면 어디에도 포함 금지. 크리에이터는 본인 견적만 제시하고 개별 협의 |
| 개인 연락처 (`contact_email`) | 목록/상세 API·제안서 산출물에서 제외, RFP 송부 시점 서버 측 사용만 |
| 타 크리에이터의 견적·정산 금액 | 크리에이터 엔드포인트는 본인(`influencer_id`) 데이터만 반환 |
| 기밀 브랜드 가이드 (`is_confidential`) | 열람 로그 기록 필수 |

새 크리에이터-facing API/화면을 추가할 때는 이 표를 기준으로 응답 필드를 검수한다.

---

## 12. Claude Code 작업 시 참고

- 디자인 톤: 블랙(#000)/그레이/화이트 유지, 액센트 최소화. Tailwind 사용
- 프로토타입 코드의 `INFLUENCERS` 목업 배열이 곧 API 응답 스키마의 기준 — 백엔드 응답을 이 형태에 맞추면 프론트 전환 비용 최소화
- `matchScore` 산식(현재): `60 + engagement*2 + growth*0.5 + (trending ? 8 : 0)`, 상한 98 — 추후 Claude API 기반으로 교체 예정이나 폴백 로직으로 유지 권장
- 개인정보(contact_email)는 목록 API 응답에서 제외하고 RFP 송부 시점에만 서버 측에서 사용할 것
