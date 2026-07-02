"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import ProcessBar from "@/components/ProcessBar";
import {
  getDashboard,
  getNotifications,
  readNotification,
  type Dashboard,
  type Notification,
} from "@/lib/api";

const POLL_INTERVAL = 30_000; // 알림 30초 폴링

const STAGE_BADGES: Record<string, string> = {
  rfp: "RFP 등록",
  recommend: "AI 추천 대기",
  dispatch: "송부 대기",
  reply: "회신 대기",
  quote: "견적 협의",
  contract: "계약 단계",
  storyboard: "스토리보드",
  delivery: "제작/납품",
  review: "검수",
  settlement: "정산",
};

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [d, n] = await Promise.all([getDashboard(), getNotifications()]);
      setDashboard(d);
      setNotifications(n);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "불러오기 실패 — 백엔드(8000) 실행 여부를 확인하세요.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, POLL_INTERVAL);
    return () => clearInterval(timer);
  }, [load]);

  const markRead = async (id: number) => {
    await readNotification(id).catch(() => {});
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
  };

  const unread = notifications.filter((n) => !n.is_read);

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">업무 대시보드</h1>
          <p className="mt-2 text-sm text-neutral-500">
            캠페인별 전체 진행 과정과 현재 위치, 다음 액션을 확인하세요.
          </p>
        </div>
        <Link
          href="/brief"
          className="rounded-md bg-black px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800"
        >
          새 캠페인 (RFP)
        </Link>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-600">{error}</div>
      )}

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_340px]">
        {/* 캠페인 진행 현황 */}
        <div className="flex flex-col gap-4">
          {loading ? (
            <p className="py-20 text-center text-sm text-neutral-400">불러오는 중…</p>
          ) : !dashboard || dashboard.campaigns.length === 0 ? (
            <div className="rounded-lg border border-neutral-200 py-20 text-center text-sm text-neutral-400">
              진행 중인 캠페인이 없습니다. RFP를 등록해 시작하세요.
            </div>
          ) : (
            dashboard.campaigns.map((c) => (
              <div key={c.campaign_id} className="rounded-lg border border-neutral-200 p-5">
                <div className="mb-4 flex items-start justify-between gap-4">
                  <div>
                    <h3 className="font-semibold">{c.campaign_name}</h3>
                    <p className="mt-0.5 text-xs text-neutral-400">
                      캠페인 #{c.campaign_id} · {new Date(c.created_at).toLocaleDateString("ko-KR")}
                    </p>
                  </div>
                  <span className="whitespace-nowrap rounded-full bg-black px-3 py-1 text-xs font-semibold text-white">
                    {STAGE_BADGES[c.current_stage] ?? c.current_stage}
                  </span>
                </div>
                <ProcessBar stages={c.stages} />
                <p className="mt-3 border-t border-neutral-100 pt-3 text-sm text-neutral-500">
                  <span className="font-semibold text-neutral-900">다음 액션</span> — {c.next_action}
                </p>
              </div>
            ))
          )}
        </div>

        {/* 알림 패널 */}
        <aside className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">
              알림 {unread.length > 0 && (
                <span className="ml-1 rounded-full bg-black px-2 py-0.5 text-xs font-bold text-white">
                  {unread.length}
                </span>
              )}
            </h2>
            <span className="text-xs text-neutral-400">30초마다 자동 갱신</span>
          </div>
          <div className="flex max-h-[70vh] flex-col gap-2 overflow-y-auto rounded-lg border border-neutral-200 p-3">
            {notifications.length === 0 ? (
              <p className="py-10 text-center text-xs text-neutral-400">알림이 없습니다</p>
            ) : (
              notifications.map((n) => (
                <button
                  key={n.id}
                  onClick={() => !n.is_read && markRead(n.id)}
                  className={`rounded-md border p-3 text-left text-xs transition-colors ${
                    n.is_read
                      ? "border-neutral-100 text-neutral-400"
                      : "border-neutral-300 bg-neutral-50 text-neutral-800 hover:border-black"
                  }`}
                >
                  <div className="mb-1 flex items-center gap-1.5">
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                        n.kind === "reminder" ? "bg-amber-100 text-amber-700" : "bg-neutral-200 text-neutral-600"
                      }`}
                    >
                      {n.kind === "reminder" ? "리마인드" : "알림"}
                    </span>
                    <span className="text-[10px] text-neutral-400">
                      {new Date(n.created_at).toLocaleString("ko-KR")}
                    </span>
                    {!n.is_read && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-black" />}
                  </div>
                  {n.message}
                </button>
              ))
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
