"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  getInfluencers,
  getMessages,
  sendMessage,
  store,
  type Influencer,
  type Message,
} from "@/lib/api";

export default function MessagesPage() {
  const [campaignId, setCampaignId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [influencers, setInfluencers] = useState<Map<number, Influencer>>(new Map());
  const [activeInfluencerId, setActiveInfluencerId] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (id: number) => {
    try {
      const [msgs, infList] = await Promise.all([
        getMessages(id),
        getInfluencers({ page: "1", page_size: "100" }),
      ]);
      setMessages(msgs);
      setInfluencers(new Map(infList.items.map((i) => [i.id, i])));
    } catch (e) {
      setError(e instanceof Error ? e.message : "불러오기 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const id = store.getCampaignId();
    setCampaignId(id);
    if (id) load(id);
    else setLoading(false);
  }, [load]);

  const threads = useMemo(() => {
    const byInfluencer = new Map<number, Message[]>();
    for (const m of messages) {
      const list = byInfluencer.get(m.influencer_id) ?? [];
      list.push(m);
      byInfluencer.set(m.influencer_id, list);
    }
    return byInfluencer;
  }, [messages]);

  const threadIds = [...threads.keys()];
  const activeId = activeInfluencerId ?? threadIds[0] ?? null;
  const activeThread = activeId != null ? (threads.get(activeId) ?? []) : [];

  const send = async () => {
    if (!campaignId || activeId == null || !draft.trim()) return;
    setSending(true);
    try {
      await sendMessage(campaignId, activeId, draft.trim());
      setDraft("");
      await load(campaignId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "발송 실패");
    } finally {
      setSending(false);
    }
  };

  if (!loading && !campaignId) {
    return (
      <div className="py-20 text-center">
        <p className="text-neutral-500">진행 중인 캠페인이 없습니다. RFP를 먼저 등록해 주세요.</p>
        <Link href="/brief" className="mt-4 inline-block rounded-md bg-black px-5 py-2.5 text-sm font-semibold text-white">
          RFP 작성하기
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">메시지함</h1>
        <p className="mt-2 text-sm text-neutral-500">
          캠페인 #{campaignId} — 인플루언서 회신이 이메일에서 자동 수신됩니다.
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-600">{error}</div>
      )}

      {loading ? (
        <p className="py-20 text-center text-sm text-neutral-400">불러오는 중…</p>
      ) : threadIds.length === 0 ? (
        <p className="py-20 text-center text-sm text-neutral-400">
          아직 메시지가 없습니다. RFP 송부 후 인플루언서 회신이 이곳에 표시됩니다.
        </p>
      ) : (
        <div className="grid min-h-96 grid-cols-1 gap-0 overflow-hidden rounded-lg border border-neutral-200 md:grid-cols-[260px_1fr]">
          <aside className="border-b border-neutral-200 md:border-b-0 md:border-r">
            {threadIds.map((id) => {
              const inf = influencers.get(id);
              const last = threads.get(id)?.at(-1);
              return (
                <button
                  key={id}
                  onClick={() => setActiveInfluencerId(id)}
                  className={`flex w-full flex-col gap-1 border-b border-neutral-100 px-4 py-3 text-left transition-colors ${
                    activeId === id ? "bg-neutral-100" : "hover:bg-neutral-50"
                  }`}
                >
                  <span className="text-sm font-semibold">{inf?.name ?? `인플루언서 #${id}`}</span>
                  <span className="truncate text-xs text-neutral-400">{last?.body ?? ""}</span>
                </button>
              );
            })}
          </aside>

          <section className="flex flex-col">
            <div className="flex flex-1 flex-col gap-3 p-5">
              {activeThread.map((m) => (
                <div
                  key={m.id}
                  className={`max-w-[75%] rounded-lg px-4 py-2.5 text-sm ${
                    m.direction === "outbound"
                      ? "self-end bg-black text-white"
                      : "self-start bg-neutral-100 text-neutral-900"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{m.body}</p>
                  <p className={`mt-1 text-[10px] ${m.direction === "outbound" ? "text-neutral-400" : "text-neutral-400"}`}>
                    {new Date(m.created_at).toLocaleString("ko-KR")}
                  </p>
                </div>
              ))}
            </div>
            <div className="flex gap-2 border-t border-neutral-200 p-4">
              <input
                className="flex-1 rounded-md border border-neutral-200 px-3 py-2.5 text-sm outline-none focus:border-black"
                placeholder="메시지를 입력하세요 (인플루언서 이메일로 발송됩니다)"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.nativeEvent.isComposing && send()}
              />
              <button
                onClick={send}
                disabled={sending || !draft.trim()}
                className="rounded-md bg-black px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 disabled:bg-neutral-300"
              >
                발송
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
