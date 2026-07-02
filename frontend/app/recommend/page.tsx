"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  CHANNEL_LABELS,
  TIER_LABELS,
  aiRecommend,
  createProposal,
  dispatchRfp,
  formatCount,
  getProposalJob,
  outputUrl,
  store,
  type DispatchResult,
  type ProposalJob,
  type Recommendation,
} from "@/lib/api";

const POLL_INTERVAL = 2500;

export default function RecommendPage() {
  const [campaignId, setCampaignId] = useState<number | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [dispatching, setDispatching] = useState(false);
  const [result, setResult] = useState<DispatchResult | null>(null);
  const [proposalJob, setProposalJob] = useState<ProposalJob | null>(null);
  const [proposalLoading, setProposalLoading] = useState(false);

  const generateProposal = async () => {
    if (!campaignId) return;
    setProposalLoading(true);
    setError(null);
    try {
      const { job_id } = await createProposal(campaignId);
      let job = await getProposalJob(job_id);
      while (job.status === "pending" || job.status === "processing") {
        await new Promise((r) => setTimeout(r, POLL_INTERVAL));
        job = await getProposalJob(job_id);
      }
      setProposalJob(job);
      if (job.status === "failed") setError(job.error ?? "제안서 생성 실패");
    } catch (e) {
      setError(e instanceof Error ? e.message : "제안서 생성 실패");
    } finally {
      setProposalLoading(false);
    }
  };

  useEffect(() => {
    const id = store.getCampaignId();
    setCampaignId(id);
    if (!id) {
      setLoading(false);
      return;
    }
    aiRecommend(id)
      .then((recs) => {
        setRecommendations(recs);
        // 탐색 단계에서 선택한 인플루언서는 미리 체크
        const preselected = new Set(store.getSelectedIds());
        setSelected(new Set(recs.map((r) => r.influencer.id).filter((i) => preselected.has(i))));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "추천 실패"))
      .finally(() => setLoading(false));
  }, []);

  const toggle = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const dispatch = async () => {
    if (!campaignId) return;
    setDispatching(true);
    setError(null);
    try {
      const res = await dispatchRfp(campaignId, [...selected]);
      setResult(res);
      setConfirming(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "송부 실패");
    } finally {
      setDispatching(false);
    }
  };

  if (!loading && !campaignId) {
    return (
      <div className="py-20 text-center">
        <p className="text-neutral-500">먼저 RFP 업무요청서를 등록해 주세요.</p>
        <Link href="/brief" className="mt-4 inline-block rounded-md bg-black px-5 py-2.5 text-sm font-semibold text-white">
          RFP 작성하기
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">AI 맞춤 인플루언서 추천</h1>
          <p className="mt-2 text-sm text-neutral-500">
            캠페인 #{campaignId} — 매칭 점수와 예상 KPI를 확인하고 송부 대상을 선택하세요.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={generateProposal}
            disabled={proposalLoading || loading}
            className="rounded-md border border-black px-5 py-2.5 text-sm font-semibold transition-colors hover:bg-neutral-100 disabled:cursor-not-allowed disabled:border-neutral-300 disabled:text-neutral-300"
          >
            {proposalLoading ? "제안서 생성 중…" : "제안서 생성 (PPT+Excel)"}
          </button>
          <button
            onClick={() => setConfirming(true)}
            disabled={selected.size === 0}
            className="rounded-md bg-black px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-300"
          >
            {selected.size > 0 ? `${selected.size}명에게 RFP 송부` : "RFP 송부"}
          </button>
        </div>
      </div>

      {proposalJob?.status === "completed" && (
        <div className="flex items-center gap-4 rounded-md border border-neutral-200 bg-neutral-50 p-4 text-sm">
          <span className="font-semibold">제안서 생성 완료</span>
          {proposalJob.pptx_path && (
            <a href={outputUrl(proposalJob.pptx_path)} className="font-medium underline" download>
              캠페인 기획안 (.pptx)
            </a>
          )}
          {proposalJob.xlsx_path && (
            <a href={outputUrl(proposalJob.xlsx_path)} className="font-medium underline" download>
              인플루언서 리스트업 (.xlsx)
            </a>
          )}
          <span className="text-xs text-neutral-400">클라이언트 내부 보고용 — 개인 연락처 미포함</span>
        </div>
      )}

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-600">{error}</div>
      )}

      {loading ? (
        <p className="py-20 text-center text-sm text-neutral-400">AI 매칭 분석 중…</p>
      ) : (
        <div className="flex flex-col gap-4">
          {recommendations.map((rec) => {
            const inf = rec.influencer;
            const isSelected = selected.has(inf.id);
            return (
              <button
                key={inf.id}
                onClick={() => toggle(inf.id)}
                className={`grid grid-cols-1 gap-4 rounded-lg border p-5 text-left transition-all md:grid-cols-[1fr_auto] ${
                  isSelected ? "border-black ring-1 ring-black" : "border-neutral-200 hover:border-neutral-400"
                }`}
              >
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold">{inf.name}</h3>
                    <span className="text-xs text-neutral-400">
                      {CHANNEL_LABELS[inf.channel]} · {TIER_LABELS[inf.tier]} · 팔로워 {formatCount(inf.followers)}
                    </span>
                    {inf.is_trending && <span className="text-sm">🔥</span>}
                  </div>
                  <p className="text-sm text-neutral-600">{rec.match_reason}</p>
                  <div className="mt-1 flex flex-wrap gap-4 text-xs text-neutral-500">
                    <span>예상 도달 <b className="text-neutral-900">{formatCount(rec.estimated_kpi.expected_reach)}</b></span>
                    <span>예상 클릭 <b className="text-neutral-900">{formatCount(rec.estimated_kpi.expected_clicks)}</b></span>
                    <span>예상 전환 <b className="text-neutral-900">{formatCount(rec.estimated_kpi.expected_conversions)}</b></span>
                    <span>참여율 <b className="text-neutral-900">{rec.estimated_kpi.expected_engagement_rate}%</b></span>
                  </div>
                </div>
                <div className="flex items-center justify-end">
                  <div className="text-right">
                    <p className="text-3xl font-bold">{rec.match_score}</p>
                    <p className="text-xs text-neutral-400">매칭 점수</p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}

      {confirming && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-6">
          <div className="w-full max-w-md rounded-lg bg-white p-6">
            <h2 className="text-lg font-bold">RFP 송부 확인</h2>
            <p className="mt-2 text-sm text-neutral-500">
              선택한 {selected.size}명의 인플루언서 contact mail로 업무요청서가 발송됩니다.
            </p>
            <ul className="mt-4 max-h-40 overflow-y-auto rounded-md bg-neutral-50 p-3 text-sm">
              {recommendations
                .filter((r) => selected.has(r.influencer.id))
                .map((r) => (
                  <li key={r.influencer.id} className="py-1">
                    {r.influencer.name} <span className="text-neutral-400">(매칭 {r.match_score}점)</span>
                  </li>
                ))}
            </ul>
            <div className="mt-6 flex gap-3">
              <button
                onClick={() => setConfirming(false)}
                className="flex-1 rounded-md border border-neutral-200 px-4 py-2.5 text-sm font-medium hover:border-neutral-400"
              >
                취소
              </button>
              <button
                onClick={dispatch}
                disabled={dispatching}
                className="flex-1 rounded-md bg-black px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 disabled:bg-neutral-300"
              >
                {dispatching ? "송부 중…" : "송부하기"}
              </button>
            </div>
          </div>
        </div>
      )}

      {result && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-6">
          <div className="w-full max-w-md rounded-lg bg-white p-6 text-center">
            <p className="text-3xl">✓</p>
            <h2 className="mt-2 text-lg font-bold">송부 완료</h2>
            <p className="mt-2 text-sm text-neutral-500">
              {result.dispatched}명에게 RFP가 발송되었습니다.
            </p>
            <ul className="mt-4 rounded-md bg-neutral-50 p-3 text-sm text-neutral-600">
              {result.recipients.map((r, i) => (
                <li key={i} className="py-0.5">{r}</li>
              ))}
            </ul>
            <Link
              href="/messages"
              className="mt-6 inline-block w-full rounded-md bg-black px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800"
            >
              메시지함으로 이동
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
