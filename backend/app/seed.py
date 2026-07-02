"""개발용 목업 데이터 시드.

실행: backend 디렉토리에서 `python -m app.seed`
프로토타입 INFLUENCERS 목업 배열 형태를 기준으로 한 샘플 데이터.
"""

import asyncio
from datetime import date, timedelta

from loguru import logger
from sqlalchemy import delete, select

from .database import async_session, init_db
from .models.orm_models import Category, Influencer, InfluencerSnapshot
from .services.scoring import classify_tier, is_trending

CATEGORIES = [
    "건강", "뷰티", "IT & Tech", "V log", "여행", "재테크 & 금융",
    "문화", "교양", "푸드", "패션", "엔터", "라이프스타일",
]

# (name, channel, channel_id, country, category, followers, monthly_views,
#  engagement%, growth%, cost_min, cost_max, contact_email)
INFLUENCERS = [
    ("테크리뷰 준", "youtube", "UC_tech_jun", "KR", "IT & Tech", 1_250_000, 8_400_000, 4.2, 2.1, 8_000_000, 15_000_000, "tech.jun@example.com"),
    ("뷰티다이어리 소라", "youtube", "UC_sora_beauty", "KR", "뷰티", 480_000, 3_100_000, 6.8, 4.5, 4_000_000, 7_000_000, "sora.beauty@example.com"),
    ("살림의 여왕", "youtube", "UC_living_queen", "KR", "라이프스타일", 85_000, 620_000, 5.1, 1.8, 1_200_000, 2_500_000, "living.q@example.com"),
    ("먹방여행 민수", "youtube", "UC_minsu_food", "KR", "푸드", 2_300_000, 15_000_000, 3.9, 1.2, 12_000_000, 20_000_000, "minsu.food@example.com"),
    ("패션위크 지은", "instagram", "ig_jieun_fw", "KR", "패션", 320_000, 1_800_000, 7.2, 5.8, 3_000_000, 6_000_000, "jieun.fw@example.com"),
    ("데일리메이크업 하나", "instagram", "ig_hana_makeup", "KR", "뷰티", 145_000, 900_000, 8.1, 6.2, 1_800_000, 3_500_000, "hana.mk@example.com"),
    ("홈트레이닝 코치 빈", "instagram", "ig_bin_fit", "KR", "건강", 68_000, 410_000, 6.4, 3.1, 900_000, 1_800_000, "bin.fit@example.com"),
    ("여행에미치다 준호", "instagram", "ig_junho_travel", "KR", "여행", 890_000, 4_200_000, 5.5, 2.9, 6_000_000, 11_000_000, "junho.tr@example.com"),
    ("댄스챌린지 유나", "tiktok", "tt_yuna_dance", "KR", "엔터", 1_800_000, 22_000_000, 9.3, 8.4, 7_000_000, 13_000_000, "yuna.dc@example.com"),
    ("쿠킹해커 레오", "tiktok", "tt_leo_cook", "KR", "푸드", 540_000, 6_800_000, 7.8, 6.9, 2_500_000, 5_000_000, "leo.ck@example.com"),
    ("TechTok Mia", "tiktok", "tt_mia_tech", "US", "IT & Tech", 950_000, 11_000_000, 6.7, 5.2, 5_000_000, 9_000_000, "mia.tech@example.com"),
    ("Jakarta Vibes Rina", "tiktok", "tt_rina_jkt", "ID", "V log", 420_000, 5_100_000, 8.9, 7.6, 1_500_000, 3_000_000, "rina.jkt@example.com"),
    ("Saigon Foodie Anh", "tiktok", "tt_anh_food", "VN", "푸드", 280_000, 3_400_000, 7.1, 4.8, 1_000_000, 2_200_000, "anh.food@example.com"),
    ("재테크읽어주는 남자", "youtube", "UC_fin_man", "KR", "재테크 & 금융", 210_000, 1_400_000, 4.8, 3.3, 2_000_000, 4_000_000, "fin.man@example.com"),
    ("북튜버 서연", "youtube", "UC_seoyeon_book", "KR", "교양", 9_500, 48_000, 4.1, 1.5, 300_000, 700_000, "seoyeon.bk@example.com"),
    ("캠핑브이로그 도윤", "instagram", "ig_doyun_camp", "KR", "여행", 5_200, 31_000, 6.9, 9.1, 200_000, 500_000, "doyun.camp@example.com"),
]

WEEKS = 4  # 최근 4주치 스냅샷 생성


def _week_start(offset_weeks: int) -> date:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday - timedelta(weeks=offset_weeks)


async def seed() -> None:
    await init_db()
    async with async_session() as db:
        existing = (await db.execute(select(Category.id).limit(1))).first()
        if existing:
            logger.info("기존 데이터 초기화 후 재시드")
            await db.execute(delete(InfluencerSnapshot))
            await db.execute(delete(Influencer))
            await db.execute(delete(Category))
            await db.commit()

        cat_map: dict[str, Category] = {}
        for i, name in enumerate(CATEGORIES):
            cat = Category(name=name, sort_order=i)
            db.add(cat)
            cat_map[name] = cat
        await db.flush()

        for row in INFLUENCERS:
            (name, channel, channel_id, country, category, followers, monthly_views,
             engagement, growth, cost_min, cost_max, email) = row
            inf = Influencer(
                name=name,
                channel=channel,
                channel_id=channel_id,
                country=country,
                category_id=cat_map[category].id,
                tier=classify_tier(followers),
                contact_email=email,
                cost_range_min=cost_min,
                cost_range_max=cost_max,
            )
            db.add(inf)
            await db.flush()

            # 과거 주차로 갈수록 팔로워를 성장률만큼 역산해 시계열 생성
            for w in range(WEEKS - 1, -1, -1):
                factor = (1 - growth / 100) ** w
                db.add(
                    InfluencerSnapshot(
                        influencer_id=inf.id,
                        week_start=_week_start(w),
                        followers=round(followers * factor),
                        monthly_views=round(monthly_views * factor),
                        engagement_rate=engagement,
                        growth_rate=growth,
                        is_trending=is_trending(growth, engagement),
                    )
                )

        await db.commit()
    logger.info(f"시드 완료: 카테고리 {len(CATEGORIES)}개, 인플루언서 {len(INFLUENCERS)}명, 주간 스냅샷 {WEEKS}주치")


if __name__ == "__main__":
    asyncio.run(seed())
