"use client";

import { useCallback, useEffect, useState } from "react";
import ProcessBar from "@/components/ProcessBar";
import {
  creatorLogin,
  creatorMessages,
  creatorNotifications,
  creatorReadNotification,
  creatorRfps,
  creatorSendMessage,
  creatorStore,
  creatorSubmitQuote,
  type CreatorRfp,
  type CreatorSession,
  type Message,
  type Notification,
  type QuoteInput,
} from "@/lib/api";

const POLL_INTERVAL = 30_000;

export default function CreatorPage() {
  const [session, setSession] = useState<CreatorSession | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setSession(creatorStore.getSession());
    setReady(true);
  }, []);

  if (!ready) return null;
  return session ? (
    <CreatorPortal
      session={session}
      onLogout={() => {
        creatorStore.setSession(null);
        setSession(null);
      }}
    />
  ) : (
    <CreatorLogin
      onLogin={(s) => {
        creatorStore.setSession(s);
        setSession(s);
      }}
    />
  );
}

function CreatorLogin({ onLogin }: { onLogin: (s: CreatorSession) => void }) {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      onLogin(await creatorLogin(email.trim(), code.trim()));
    } catch {
      setError("이메일 또는 접속 코드가 올바르지 않습니다.");
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-sm flex-col gap-6 py-16">
      <div className="text-center">
        <h1 className="text-2xl font-bold tracking-tight">크리에이터 포털</h1>
        <p className="mt-2 text-sm text-neutral-500">
          RFP 이메일에 포함된 접속 코드로 로그인하세요.
        </p>
      </div>
      <form onSubmit={submit} className="flex flex-col gap-3">
        <input
          className="rounded-md border border-neutral-200 px-3 py-2.5 text-sm outline-none focus:border-black"
          placeholder="이메일"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="rounded-md border border-neutral-200 px-3 py-2.5 text-sm outline-none focus:border-black"
          placeholder="접속 코드"
          required
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-black px-4 py-3 text-sm font-semibold text-white hover:bg-neutral-800 disabled:bg-neutral-300"
        >
          {loading ? "로그인 중…" : "로그인"}
        </button>
      </form>
    </div>
  );
}

function CreatorPortal({ session, onLogout }: { session: CreatorSession; onLogout: () => void }) {
  const [rfps, setRfps] = useState<CreatorRfp[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [activeCampaign, setActiveCampaign] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [quote, setQuote] = useState<QuoteInput>({});
  const [quoteSent, setQuoteSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [r, n] = await Promise.all([
        creatorRfps(session.token),
        creatorNotifications(session.token),
      ]);
      setRfps(r);
      setNotifications(n);
      setError(null);
    } catch {
      setError("데이터를 불러오지 못했습니다. 접속 코드가 만료되었을 수 있습니다.");
    }
  }, [session.token]);

  useEffect(() => {
    load();
    const timer = setInterval(load, POLL_INTERVAL);
    return () => clearInterval(timer);
  }, [load]);

  const loadMessages = useCallback(
    async (campaignId: number) => {
      setMessages(await creatorMessages(session.token, campaignId).catch(() => []));
    },
    [session.token],
  );

  useEffect(() => {
    if (activeCampaign == null && rfps.length > 0) setActiveCampaign(rfps[0].campaign_id);
  }, [rfps, activeCampaign]);

  useEffect(() => {
    if (activeCampaign != null) loadMessages(activeCampaign);
  }, [activeCampaign, loadMessages]);

  const submitQuote = async () => {
    if (activeCampaign == null) return;
    try {
      await creatorSubmitQuote(session.token, activeCampaign, quote);
      setQuoteSent(true);
      setQuote({});
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "견적 제출 실패");
    }
  };

  const send = async () => {
    if (activeCampaign == null || !draft.trim()) return;
    await creatorSendMessage(session.token, activeCampaign, draft.trim()).catch(() => {});
    setDraft("");
    await loadMessages(activeCampaign);
  };

  const active = rfps.find((r) => r.campaign_id === activeCampaign);
  const unread = notifications.filter((n) => !n.is_read);
  const input =
    "w-full rounded-md border border-neutral-200 px-3 py-2.5 text-sm outline-none focus:border-black";

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">크리에이터 포털</h1>
          <p className="mt-2 text-sm text-neutral-500">
            {session.name} 님 ({session.channel}) — 받은 RFP에 견적을 제출하고 클라이언트와 소통하세요.
          </p>
        </div>
        <button onClick={onLogout} className="rounded-md border border-neutral-200 px-4 py-2 text-sm hover:border-black">
          로그아웃
        </button>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-600">{error}</div>
      )}

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[300px_1fr_300px]">
        {/* 받은 RFP 목록 */}
        <aside className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold">받은 업무 요청 (RFP)</h2>
          {rfps.length === 0 && (
            <p className="rounded-md border border-neutral-200 p-4 text-xs text-neutral-400">
              아직 받은 RFP가 없습니다.
            </p>
          )}
          {rfps.map((r) => (
            <button
              key={r.campaign_id}
              onClick={() => setActiveCampaign(r.campaign_id)}
              className={`rounded-md border p-3 text-left text-sm transition-colors ${
                activeCampaign === r.campaign_id ? "border-black ring-1 ring-black" : "border-neutral-200 hover:border-neutral-400"
              }`}
            >
              <p className="font-semibold">{r.campaign_name}</p>
              <p className="mt-0.5 text-xs text-neutral-400">
                {r.ad_type === "ppl" ? "PPL" : "브랜디드"} · {r.dispatch_status} ·{" "}
                {new Date(r.sent_at).toLocaleDateString("ko-KR")}
              </p>
            </button>
          ))}
        </aside>

        {/* 캠페인 상세 + 견적 + 메시지 */}
        <section className="flex flex-col gap-6">
          {active ? (
            <>
              <div className="rounded-lg border border-neutral-200 p-5">
                <h3 className="font-semibold">{active.campaign_name}</h3>
                <div className="mt-3">
                  <ProcessBar stages={active.stages} />
                </div>
                <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 border-t border-neutral-100 pt-4 text-sm">
                  <dt className="text-neutral-400">예산</dt>
                  <dd>{active.budget_range ?? "협의"}</dd>
                  <dt className="text-neutral-400">콘텐츠 규격</dt>
                  <dd>
                    {active.content_format === "package"
                      ? "롱폼+숏폼 패키지"
                      : active.content_format === "longform"
                        ? "롱폼"
                        : active.content_format === "shortform"
                          ? "숏폼"
                          : "협의"}
                    {active.longform_minutes ? ` · 롱폼 ${active.longform_minutes}분` : ""}
                    {active.shortform_minutes ? ` · 숏폼 ${active.shortform_minutes}분` : ""}
                  </dd>
                  <dt className="text-neutral-400">납품 기한</dt>
                  <dd>{active.deadline ?? "협의"}</dd>
                  {active.additional_rewards && (
                    <>
                      <dt className="text-neutral-400">추가 보상</dt>
                      <dd>{active.additional_rewards}</dd>
                    </>
                  )}
                  {active.provided_resources && (
                    <>
                      <dt className="text-neutral-400">제공 재원·소재</dt>
                      <dd>{active.provided_resources}</dd>
                    </>
                  )}
                  {active.must_include && (
                    <>
                      <dt className="text-neutral-400">필수 포함</dt>
                      <dd>{active.must_include}</dd>
                    </>
                  )}
                </dl>
              </div>

              {/* 견적 제출 */}
              <div className="rounded-lg border border-neutral-200 p-5">
                <h3 className="font-semibold">1차 견적 제출</h3>
                {quoteSent ? (
                  <p className="mt-3 rounded-md bg-neutral-50 p-4 text-sm text-neutral-600">
                    견적이 제출되었습니다. 클라이언트 검토 후 알림으로 결과를 받게 됩니다.
                  </p>
                ) : (
                  <div className="mt-3 flex flex-col gap-3">
                    <textarea
                      className={`${input} min-h-20 resize-y`}
                      placeholder="콘텐츠 기획 방향 (어떤 방향·형식으로 제작할지)"
                      value={quote.content_plan ?? ""}
                      onChange={(e) => setQuote({ ...quote, content_plan: e.target.value })}
                    />
                    <div className="grid grid-cols-3 gap-3">
                      <select
                        className={input}
                        value={quote.content_format ?? ""}
                        onChange={(e) => setQuote({ ...quote, content_format: e.target.value || undefined })}
                      >
                        <option value="">형식 선택</option>
                        <option value="shortform">숏폼</option>
                        <option value="longform">롱폼</option>
                        <option value="package">패키지</option>
                      </select>
                      <input
                        className={input}
                        type="number"
                        placeholder="길이(분)"
                        value={quote.length_minutes ?? ""}
                        onChange={(e) =>
                          setQuote({ ...quote, length_minutes: e.target.value ? Number(e.target.value) : undefined })
                        }
                      />
                      <input
                        className={input}
                        type="number"
                        placeholder="견적 금액(원)"
                        value={quote.amount ?? ""}
                        onChange={(e) =>
                          setQuote({ ...quote, amount: e.target.value ? Number(e.target.value) : undefined })
                        }
                      />
                    </div>
                    <button
                      onClick={submitQuote}
                      className="rounded-md bg-black px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800"
                    >
                      견적 제출
                    </button>
                  </div>
                )}
              </div>

              {/* 메시지 */}
              <div className="flex flex-col rounded-lg border border-neutral-200">
                <h3 className="border-b border-neutral-100 p-4 font-semibold">클라이언트와 메시지</h3>
                <div className="flex max-h-72 flex-1 flex-col gap-3 overflow-y-auto p-4">
                  {messages.length === 0 && (
                    <p className="py-6 text-center text-xs text-neutral-400">메시지가 없습니다</p>
                  )}
                  {messages.map((m) => (
                    <div
                      key={m.id}
                      className={`max-w-[75%] rounded-lg px-4 py-2.5 text-sm ${
                        m.direction === "inbound"
                          ? "self-end bg-black text-white" // 크리에이터 본인 발신
                          : "self-start bg-neutral-100"
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{m.body}</p>
                      <p className="mt-1 text-[10px] text-neutral-400">
                        {new Date(m.created_at).toLocaleString("ko-KR")}
                      </p>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2 border-t border-neutral-100 p-3">
                  <input
                    className={input}
                    placeholder="메시지 입력"
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && !e.nativeEvent.isComposing && send()}
                  />
                  <button
                    onClick={send}
                    disabled={!draft.trim()}
                    className="rounded-md bg-black px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:bg-neutral-300"
                  >
                    발송
                  </button>
                </div>
              </div>
            </>
          ) : (
            <p className="py-20 text-center text-sm text-neutral-400">RFP를 선택하세요</p>
          )}
        </section>

        {/* 내 알림 */}
        <aside className="flex flex-col gap-3">
          <h2 className="text-sm font-semibold">
            내 알림{" "}
            {unread.length > 0 && (
              <span className="ml-1 rounded-full bg-black px-2 py-0.5 text-xs font-bold text-white">
                {unread.length}
              </span>
            )}
          </h2>
          <div className="flex max-h-[70vh] flex-col gap-2 overflow-y-auto rounded-lg border border-neutral-200 p-3">
            {notifications.length === 0 ? (
              <p className="py-10 text-center text-xs text-neutral-400">알림이 없습니다</p>
            ) : (
              notifications.map((n) => (
                <button
                  key={n.id}
                  onClick={async () => {
                    if (!n.is_read) {
                      await creatorReadNotification(session.token, n.id).catch(() => {});
                      setNotifications((prev) =>
                        prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)),
                      );
                    }
                  }}
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
