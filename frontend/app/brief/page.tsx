"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createCampaign, store, type CampaignInput } from "@/lib/api";

export default function BriefPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<CampaignInput>({
    name: "",
    budget_range: "",
    period_start: "",
    period_end: "",
    content_detail: "",
    ad_type: "ppl",
    include_offline: false,
    need_ip_license: false,
    deadline: "",
    expectation: "",
    content_format: undefined,
    longform_minutes: undefined,
    shortform_minutes: undefined,
    additional_rewards: "",
    provided_resources: "",
    must_include: "",
  });

  const set = <K extends keyof CampaignInput>(key: K, value: CampaignInput[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const payload: CampaignInput = {
        ...form,
        period_start: form.period_start || undefined,
        period_end: form.period_end || undefined,
        deadline: form.deadline || undefined,
      };
      const campaign = await createCampaign(payload);
      store.setCampaignId(campaign.id);
      router.push("/recommend");
    } catch (e) {
      setError(e instanceof Error ? e.message : "등록 실패");
      setSubmitting(false);
    }
  };

  const label = "text-sm font-semibold";
  const input =
    "w-full rounded-md border border-neutral-200 px-3 py-2.5 text-sm outline-none transition-colors focus:border-black";

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">업무 요청서 (RFP) 작성</h1>
        <p className="mt-2 text-sm text-neutral-500">
          등록하면 AI가 캠페인에 맞는 인플루언서를 추천합니다.
        </p>
      </div>

      <form onSubmit={submit} className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <label className={label}>캠페인명 *</label>
          <input
            className={input}
            required
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            placeholder="예: 2026 여름 신제품 런칭 캠페인"
          />
        </div>

        <div className="flex flex-col gap-2">
          <label className={label}>캠페인 예산</label>
          <input
            className={input}
            value={form.budget_range}
            onChange={(e) => set("budget_range", e.target.value)}
            placeholder="예: 3,000만원 ~ 5,000만원"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-2">
            <label className={label}>캠페인 시작일</label>
            <input
              type="date"
              className={input}
              value={form.period_start}
              onChange={(e) => set("period_start", e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className={label}>캠페인 종료일</label>
            <input
              type="date"
              className={input}
              value={form.period_end}
              onChange={(e) => set("period_end", e.target.value)}
            />
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <label className={label}>콘텐츠 주요 내용</label>
          <textarea
            className={`${input} min-h-28 resize-y`}
            value={form.content_detail}
            onChange={(e) => set("content_detail", e.target.value)}
            placeholder="제품 소개, 필수 메시지, 톤앤매너 등"
          />
        </div>

        <div className="flex flex-col gap-2">
          <label className={label}>광고 타입 *</label>
          <div className="grid grid-cols-2 gap-3">
            {(["ppl", "branded"] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => set("ad_type", t)}
                className={`rounded-md border px-4 py-3 text-sm font-medium transition-colors ${
                  form.ad_type === t
                    ? "border-black bg-black text-white"
                    : "border-neutral-200 hover:border-neutral-400"
                }`}
              >
                {t === "ppl" ? "PPL" : "브랜디드 콘텐츠"}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <label className={label}>콘텐츠 규격 (업무 범위에 따라 크리에이터 견적이 달라집니다)</label>
          <div className="grid grid-cols-3 gap-3">
            {(
              [
                ["shortform", "숏폼"],
                ["longform", "롱폼"],
                ["package", "롱폼+숏폼 패키지"],
              ] as const
            ).map(([value, text]) => (
              <button
                key={value}
                type="button"
                onClick={() => set("content_format", form.content_format === value ? undefined : value)}
                className={`rounded-md border px-4 py-3 text-sm font-medium transition-colors ${
                  form.content_format === value
                    ? "border-black bg-black text-white"
                    : "border-neutral-200 hover:border-neutral-400"
                }`}
              >
                {text}
              </button>
            ))}
          </div>
          {(form.content_format === "longform" || form.content_format === "package") && (
            <div className="mt-2 flex items-center gap-2">
              <span className="w-24 text-xs font-semibold text-neutral-400">롱폼 길이</span>
              {[5, 10, 15, 20].map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => set("longform_minutes", form.longform_minutes === m ? undefined : m)}
                  className={`rounded-full border px-3 py-1.5 text-xs font-medium ${
                    form.longform_minutes === m
                      ? "border-black bg-black text-white"
                      : "border-neutral-200 hover:border-neutral-400"
                  }`}
                >
                  {m === 20 ? "20분 이상" : `${m}분`}
                </button>
              ))}
            </div>
          )}
          {(form.content_format === "shortform" || form.content_format === "package") && (
            <div className="mt-2 flex items-center gap-2">
              <span className="w-24 text-xs font-semibold text-neutral-400">숏폼 길이</span>
              {[1, 2, 3].map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => set("shortform_minutes", form.shortform_minutes === m ? undefined : m)}
                  className={`rounded-full border px-3 py-1.5 text-xs font-medium ${
                    form.shortform_minutes === m
                      ? "border-black bg-black text-white"
                      : "border-neutral-200 hover:border-neutral-400"
                  }`}
                >
                  {m}분
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <label className={label}>추가 보상</label>
          <textarea
            className={`${input} min-h-20 resize-y`}
            value={form.additional_rewards}
            onChange={(e) => set("additional_rewards", e.target.value)}
            placeholder="예: 좋아요 구간별 크레딧 리워드, 튜토리얼 포함 시 1.5배 보너스, 연간 이용권 등"
          />
        </div>

        <div className="flex flex-col gap-2">
          <label className={label}>클라이언트 제공 재원·소재</label>
          <textarea
            className={`${input} min-h-20 resize-y`}
            value={form.provided_resources}
            onChange={(e) => set("provided_resources", e.target.value)}
            placeholder="예: 제품 샘플, 서비스 크레딧, 촬영 소스, 계정 권한 등"
          />
        </div>

        <div className="flex flex-col gap-2">
          <label className={label}>다뤘으면 하는 내용 (필수 가이드)</label>
          <textarea
            className={`${input} min-h-20 resize-y`}
            value={form.must_include}
            onChange={(e) => set("must_include", e.target.value)}
            placeholder="예: 필수 해시태그·공식 계정 멘션·워터마크 표기, 참여 방법 안내, 제출 기한 등"
          />
        </div>

        <div className="flex gap-6">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="h-4 w-4 accent-black"
              checked={form.include_offline}
              onChange={(e) => set("include_offline", e.target.checked)}
            />
            오프라인 활동 포함
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="h-4 w-4 accent-black"
              checked={form.need_ip_license}
              onChange={(e) => set("need_ip_license", e.target.checked)}
            />
            IP 라이센스 필요
          </label>
        </div>

        <div className="flex flex-col gap-2">
          <label className={label}>예상 납품 기한</label>
          <input
            type="date"
            className={input}
            value={form.deadline}
            onChange={(e) => set("deadline", e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-2">
          <label className={label}>기대 효과</label>
          <textarea
            className={`${input} min-h-20 resize-y`}
            value={form.expectation}
            onChange={(e) => set("expectation", e.target.value)}
            placeholder="예: 신제품 인지도 상승, 2030 여성 타깃 도달 100만"
          />
        </div>

        {error && (
          <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-600">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-black px-6 py-3.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:bg-neutral-300"
        >
          {submitting ? "등록 중…" : "등록하고 AI 추천 받기"}
        </button>
      </form>
    </div>
  );
}
