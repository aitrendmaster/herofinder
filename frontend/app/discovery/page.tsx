"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  CHANNEL_LABELS,
  TIER_LABELS,
  formatCount,
  formatKrw,
  getCategories,
  getInfluencers,
  store,
  type Category,
  type Influencer,
} from "@/lib/api";

const TIERS = ["mega", "power", "micro", "nano"] as const;
const CHANNELS = ["youtube", "instagram", "tiktok"] as const;

export default function DiscoveryPage() {
  const router = useRouter();
  // 전체 리스트를 최초 1회만 로드 (우리 DB 조회 — 외부 스크래핑 아님).
  // 필터는 브라우저 메모리에서 즉시 처리해 클릭마다 재요청하지 않는다.
  const [all, setAll] = useState<Influencer[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [tier, setTier] = useState("");
  const [channel, setChannel] = useState("");
  const [category, setCategory] = useState("");
  const [trendingOnly, setTrendingOnly] = useState(false);

  useEffect(() => {
    Promise.all([
      getInfluencers({ page: "1", page_size: "500" }),
      getCategories().catch(() => [] as Category[]),
    ])
      .then(([data, cats]) => {
        setAll(data.items);
        setCategories(cats);
      })
      .catch((e) =>
        setError(e instanceof Error ? e.message : "불러오기 실패 — 백엔드(8000) 실행 여부를 확인하세요."),
      )
      .finally(() => setLoading(false));
  }, []);

  const influencers = useMemo(
    () =>
      all.filter(
        (i) =>
          (!tier || i.tier === tier) &&
          (!channel || i.channel === channel) &&
          (!category || i.category === category) &&
          (!trendingOnly || i.is_trending),
      ),
    [all, tier, channel, category, trendingOnly],
  );

  const toggle = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const goToBrief = () => {
    store.setSelectedIds([...selected]);
    router.push("/brief");
  };

  const filterBtn = (active: boolean) =>
    `rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
      active
        ? "border-black bg-black text-white"
        : "border-neutral-200 text-neutral-600 hover:border-neutral-400"
    }`;

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">인플루언서 탐색</h1>
          <p className="mt-2 text-sm text-neutral-500">
            자체 DB 기준 {all.length > 0 ? `${influencers.length} / ${all.length}명` : ""} · 주간
            수집 파이프라인으로 갱신 (탐색 중 외부 API 호출 없음)
          </p>
        </div>
        <button
          onClick={goToBrief}
          disabled={selected.size === 0}
          className="rounded-md bg-black px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-300"
        >
          {selected.size > 0 ? `${selected.size}명 선택 — RFP 작성` : "RFP 작성"}
        </button>
      </div>

      <div className="flex flex-col gap-3 rounded-lg border border-neutral-200 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-16 text-xs font-semibold text-neutral-400">등급</span>
          <button className={filterBtn(tier === "")} onClick={() => setTier("")}>전체</button>
          {TIERS.map((t) => (
            <button key={t} className={filterBtn(tier === t)} onClick={() => setTier(t)}>
              {TIER_LABELS[t]}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-16 text-xs font-semibold text-neutral-400">채널</span>
          <button className={filterBtn(channel === "")} onClick={() => setChannel("")}>전체</button>
          {CHANNELS.map((c) => (
            <button key={c} className={filterBtn(channel === c)} onClick={() => setChannel(c)}>
              {CHANNEL_LABELS[c]}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-16 text-xs font-semibold text-neutral-400">카테고리</span>
          <button className={filterBtn(category === "")} onClick={() => setCategory("")}>전체</button>
          {categories.map((c) => (
            <button
              key={c.id}
              className={filterBtn(category === c.name)}
              onClick={() => setCategory(c.name)}
            >
              {c.name}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-16 text-xs font-semibold text-neutral-400">활성도</span>
          <button className={filterBtn(trendingOnly)} onClick={() => setTrendingOnly(!trendingOnly)}>
            🔥 활성만 보기
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-600">
          {error}
        </div>
      )}
      {loading ? (
        <p className="py-20 text-center text-sm text-neutral-400">불러오는 중…</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {influencers.map((inf) => {
            const isSelected = selected.has(inf.id);
            return (
              <button
                key={inf.id}
                onClick={() => toggle(inf.id)}
                className={`flex flex-col gap-3 rounded-lg border p-5 text-left transition-all ${
                  isSelected ? "border-black ring-1 ring-black" : "border-neutral-200 hover:border-neutral-400"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold">{inf.name}</h3>
                    <p className="mt-0.5 text-xs text-neutral-400">
                      {CHANNEL_LABELS[inf.channel]} · {inf.country} · {inf.category ?? "-"}
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {inf.is_trending && <span className="text-sm">🔥</span>}
                    <span className="rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-semibold">
                      {TIER_LABELS[inf.tier]}
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
                  <span className="text-neutral-400">팔로워</span>
                  <span className="text-right font-medium">{formatCount(inf.followers)}</span>
                  <span className="text-neutral-400">월 조회수</span>
                  <span className="text-right font-medium">{formatCount(inf.monthly_views)}</span>
                  <span className="text-neutral-400">참여율</span>
                  <span className="text-right font-medium">{inf.engagement_rate}%</span>
                  <span className="text-neutral-400">주간 성장률</span>
                  <span className={`text-right font-medium ${inf.growth_rate >= 5 ? "text-emerald-600" : ""}`}>
                    +{inf.growth_rate}%
                  </span>
                </div>
                <div className="border-t border-neutral-100 pt-3 text-sm">
                  <span className="text-neutral-400">예상 섭외비 </span>
                  <span className="font-semibold">
                    {formatKrw(inf.cost_range_min)} ~ {formatKrw(inf.cost_range_max)}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
