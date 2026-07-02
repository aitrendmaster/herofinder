# Hero Finder

B2B 인플루언서 매칭 플랫폼 — 대기업 광고주가 YouTube·Instagram·TikTok 인플루언서를 탐색하고, RFP로 섭외하며, 캠페인 성과를 측정합니다.

> 상세 기획/아키텍처: [CLAUDE.md](CLAUDE.md) 참조

## 구조

```
hero finder/
├── CLAUDE.md            프로젝트 가이드 (기획 인수인계 문서)
├── backend/             FastAPI + SQLAlchemy (개발: SQLite / 프로덕션: PostgreSQL @ Render)
└── frontend/            Next.js App Router + Tailwind (배포: Vercel)
```

## 개발 서버 실행

### Backend (포트 8000)
```powershell
cd backend
.\.venv\Scripts\Activate.ps1        # 최초 1회: python -m venv .venv; pip install -r requirements.txt
python -m app.seed                  # 목업 데이터 시드 (최초 1회)
python -m uvicorn app.main:app --reload --port 8000
```
API 문서: http://localhost:8000/docs

### Frontend (포트 3000)
```powershell
cd frontend
npm run dev
```
앱: http://localhost:3000

## 환경변수

`backend/.env` (커밋 금지 — `.env.example` 참조):
- `SCRAPECREATORS_API_KEY` — Instagram/TikTok 수집 (설정됨)
- `YOUTUBE_API_KEY`, `SENDGRID_API_KEY`, `ANTHROPIC_API_KEY` — 미발급 시 해당 기능은 폴백/시뮬레이션 동작

`frontend/.env.local`:
- `NEXT_PUBLIC_API_BASE_URL` — 백엔드 URL (기본 http://localhost:8000)
