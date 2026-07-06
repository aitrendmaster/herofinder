"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ProcessBar from "@/components/ProcessBar";
import {
  GOOGLE_CLIENT_ID,
  creatorGoogleLogin,
  creatorLogin,
  creatorMessages,
  creatorNotifications,
  creatorReadNotification,
  creatorRfps,
  creatorSendMessage,
  creatorSignup,
  creatorStore,
  creatorSubmitQuote,
  getCreatorSettings,
  updateCreatorSettings,
  type CreatorRfp,
  type CreatorSession,
  type CreatorSettings,
  type Message,
  type Notification,
  type QuoteInput,
} from "@/lib/api";

const POLL_INTERVAL = 30_000;
const inputCls =
  "w-full rounded-md border border-neutral-200 px-3 py-2.5 text-sm outline-none focus:border-black";

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
    <CreatorAuth
      onLogin={(s) => {
        creatorStore.setSession(s);
        setSession(s);
      }}
    />
  );
}

/* ---------- 인증 (로그인 / 신규 가입 / 구글) ---------- */

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: object) => void;
          renderButton: (el: HTMLElement, config: object) => void;
        };
      };
    };
  }
}

function CreatorAuth({ onLogin }: { onLogin: (s: CreatorSession) => void }) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // 로그인 폼
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");

  // 가입 폼
  const [name, setName] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [channel, setChannel] = useState<"youtube" | "instagram" | "tiktok">("instagram");
  const [handle, setHandle] = useState("");
  const [googleSub, setGoogleSub] = useState<string | undefined>(undefined);
  const [issuedCode, setIssuedCode] = useState<string | null>(null);
  const [pendingSession, setPendingSession] = useState<CreatorSession | null>(null);
  const googleBtnRef = useRef<HTMLDivElement>(null);

  // Google Identity Services 버튼 (클라이언트 ID 설정 시에만)
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || issuedCode) return;
    const setup = () => {
      if (!window.google || !googleBtnRef.current) return;
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async (res: { credential: string }) => {
          setError(null);
          try {
            const r = await creatorGoogleLogin(res.credential);
            if (r.status === "ok" && r.session) {
              onLogin(r.session);
            } else {
              // 미가입 → 가입 폼으로 전환 (이메일 프리필 + 구글 연동 유지)
              setMode("signup");
              setSignupEmail(r.email ?? "");
              setGoogleSub(r.google_sub ?? undefined);
            }
          } catch (e) {
            setError(e instanceof Error ? e.message : "구글 로그인 실패");
          }
        },
      });
      window.google.accounts.id.renderButton(googleBtnRef.current, {
        theme: "outline",
        size: "large",
        width: 320,
        text: "continue_with",
      });
    };
    if (window.google) {
      setup();
      return;
    }
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = setup;
    document.head.appendChild(script);
  }, [issuedCode, mode, onLogin]);

  const doLogin = async (e: React.FormEvent) => {
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

  const doSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const r = await creatorSignup({
        name: name.trim(),
        email: signupEmail.trim(),
        channel,
        handle: handle.trim(),
        google_sub: googleSub,
      });
      // 접속 코드를 최초 1회 안내 후 입장
      setIssuedCode(r.access_code);
      setPendingSession(r.session);
    } catch (e) {
      setError(e instanceof Error ? e.message : "가입 실패");
    } finally {
      setLoading(false);
    }
  };

  if (issuedCode && pendingSession) {
    return (
      <div className="mx-auto flex max-w-md flex-col gap-6 py-16 text-center">
        <h1 className="text-2xl font-bold">가입 완료 🎉</h1>
        <p className="text-sm text-neutral-500">
          아래 <b>접속 코드</b>는 로그인에 사용됩니다. 지금 꼭 보관해 주세요.
          {googleSub ? " (구글 로그인으로도 접속할 수 있습니다)" : ""}
        </p>
        <div className="rounded-lg border-2 border-black bg-neutral-50 p-4 font-mono text-lg font-bold tracking-wider">
          {issuedCode}
        </div>
        <button
          onClick={() => onLogin(pendingSession)}
          className="rounded-md bg-black px-4 py-3 text-sm font-semibold text-white hover:bg-neutral-800"
        >
          포털 시작하기
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-sm flex-col gap-6 py-16">
      <div className="text-center">
        <h1 className="text-2xl font-bold tracking-tight">크리에이터 포털</h1>
        <p className="mt-2 text-sm text-neutral-500">
          {mode === "login"
            ? "RFP 이메일의 접속 코드 또는 구글 계정으로 로그인하세요."
            : "채널 정보를 등록하면 클라이언트 제안을 받을 수 있습니다."}
        </p>
      </div>

      {mode === "login" ? (
        <form onSubmit={doLogin} className="flex flex-col gap-3">
          <input className={inputCls} placeholder="이메일" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          <input className={inputCls} placeholder="접속 코드" required value={code} onChange={(e) => setCode(e.target.value)} />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="submit" disabled={loading} className="rounded-md bg-black px-4 py-3 text-sm font-semibold text-white hover:bg-neutral-800 disabled:bg-neutral-300">
            {loading ? "로그인 중…" : "로그인"}
          </button>
        </form>
      ) : (
        <form onSubmit={doSignup} className="flex flex-col gap-3">
          <input className={inputCls} placeholder="활동명 (채널명)" required value={name} onChange={(e) => setName(e.target.value)} />
          <input className={inputCls} placeholder="컨택 이메일" type="email" required value={signupEmail} onChange={(e) => setSignupEmail(e.target.value)} />
          <div className="grid grid-cols-3 gap-2">
            {(["youtube", "instagram", "tiktok"] as const).map((c) => (
              <button key={c} type="button" onClick={() => setChannel(c)}
                className={`rounded-md border px-2 py-2.5 text-xs font-medium ${channel === c ? "border-black bg-black text-white" : "border-neutral-200 hover:border-neutral-400"}`}>
                {c === "youtube" ? "YouTube" : c === "instagram" ? "Instagram" : "TikTok"}
              </button>
            ))}
          </div>
          <input className={inputCls} placeholder="채널 핸들 (@ 제외)" required value={handle} onChange={(e) => setHandle(e.target.value)} />
          <p className="text-xs text-neutral-400">
            이미 Hero Finder에 등록된 채널이면 자동으로 내 프로필로 연결됩니다.
          </p>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="submit" disabled={loading} className="rounded-md bg-black px-4 py-3 text-sm font-semibold text-white hover:bg-neutral-800 disabled:bg-neutral-300">
            {loading ? "가입 중…" : "가입하기"}
          </button>
        </form>
      )}

      {GOOGLE_CLIENT_ID ? (
        <div className="flex flex-col items-center gap-2">
          <div className="flex w-full items-center gap-3 text-xs text-neutral-300">
            <span className="h-px flex-1 bg-neutral-200" /> 또는 <span className="h-px flex-1 bg-neutral-200" />
          </div>
          <div ref={googleBtnRef} />
        </div>
      ) : (
        <p className="text-center text-xs text-neutral-300">구글 로그인은 준비 중입니다</p>
      )}

      <button
        onClick={() => { setMode(mode === "login" ? "signup" : "login"); setError(null); }}
        className="text-center text-sm text-neutral-500 underline hover:text-black"
      >
        {mode === "login" ? "처음이신가요? 신규 가입" : "이미 계정이 있어요 — 로그인"}
      </button>
    </div>
  );
}

/* ---------- 설정 탭 (기획 설정) ---------- */

function SettingsTab({ token }: { token: string }) {
  const [settings, setSettings] = useState<CreatorSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCreatorSettings(token)
      .then(setSettings)
      .catch(() => setError("설정을 불러오지 못했습니다."));
  }, [token]);

  if (error) return <p className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-600">{error}</p>;
  if (!settings) return <p className="py-10 text-center text-sm text-neutral-400">불러오는 중…</p>;

  const set = <K extends keyof CreatorSettings>(k: K, v: CreatorSettings[K]) => {
    setSettings({ ...settings, [k]: v });
    setSaved(false);
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const r = await updateCreatorSettings(token, {
        contact_email: settings.contact_email ?? "",
        bio: settings.bio ?? "",
        preferred_format: settings.preferred_format ?? "",
        preferred_length_minutes: settings.preferred_length_minutes ?? undefined,
        cost_range_min: settings.cost_range_min ?? undefined,
        cost_range_max: settings.cost_range_max ?? undefined,
        available: settings.available,
      });
      setSettings(r);
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "저장 실패");
    } finally {
      setSaving(false);
    }
  };

  const label = "text-sm font-semibold";
  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <div className="rounded-lg border border-neutral-200 p-5">
        <h3 className="font-semibold">내 채널</h3>
        <p className="mt-2 text-sm text-neutral-500">
          {settings.channel} · @{settings.handle} · {settings.name}
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <label className={label}>컨택 이메일</label>
        <input
          className={inputCls}
          type="email"
          value={settings.contact_email ?? ""}
          onChange={(e) => set("contact_email", e.target.value)}
          placeholder="RFP·계약 관련 연락을 받을 이메일"
        />
        <p className="text-xs text-neutral-400">클라이언트에게는 공개되지 않으며, RFP 송부 시에만 서버에서 사용됩니다.</p>
      </div>

      <div className="flex flex-col gap-2">
        <label className={label}>소개 / 주요 콘텐츠 방향</label>
        <textarea
          className={`${inputCls} min-h-24 resize-y`}
          value={settings.bio ?? ""}
          onChange={(e) => set("bio", e.target.value)}
          placeholder="예: 20대 타깃 뷰티 튜토리얼 중심, 제품 리뷰·비교 콘텐츠 강점"
        />
      </div>

      <div className="flex flex-col gap-2">
        <label className={label}>선호 콘텐츠 형식</label>
        <div className="grid grid-cols-3 gap-3">
          {([["shortform", "숏폼"], ["longform", "롱폼"], ["package", "패키지"]] as const).map(([v, t]) => (
            <button key={v} type="button"
              onClick={() => set("preferred_format", settings.preferred_format === v ? null : v)}
              className={`rounded-md border px-4 py-3 text-sm font-medium ${settings.preferred_format === v ? "border-black bg-black text-white" : "border-neutral-200 hover:border-neutral-400"}`}>
              {t}
            </button>
          ))}
        </div>
        <div className="mt-1 flex items-center gap-2">
          <span className="text-xs font-semibold text-neutral-400">기본 길이(분)</span>
          <input
            className="w-24 rounded-md border border-neutral-200 px-3 py-1.5 text-sm outline-none focus:border-black"
            type="number"
            value={settings.preferred_length_minutes ?? ""}
            onChange={(e) => set("preferred_length_minutes", e.target.value ? Number(e.target.value) : null)}
          />
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <label className={label}>희망 단가 범위 (원)</label>
        <div className="grid grid-cols-2 gap-3">
          <input className={inputCls} type="number" placeholder="최소 (예: 1000000)"
            value={settings.cost_range_min ?? ""}
            onChange={(e) => set("cost_range_min", e.target.value ? Number(e.target.value) : null)} />
          <input className={inputCls} type="number" placeholder="최대 (예: 3000000)"
            value={settings.cost_range_max ?? ""}
            onChange={(e) => set("cost_range_max", e.target.value ? Number(e.target.value) : null)} />
        </div>
        <p className="text-xs text-neutral-400">클라이언트 탐색 화면의 &lsquo;예상 섭외비&rsquo;로 표시됩니다.</p>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" className="h-4 w-4 accent-black" checked={settings.available}
          onChange={(e) => set("available", e.target.checked)} />
        현재 협업 제안을 받고 있어요
      </label>

      {error && <p className="text-sm text-red-600">{error}</p>}
      <button onClick={save} disabled={saving}
        className="rounded-md bg-black px-6 py-3 text-sm font-semibold text-white hover:bg-neutral-800 disabled:bg-neutral-300">
        {saving ? "저장 중…" : saved ? "저장됨 ✓" : "설정 저장"}
      </button>
    </div>
  );
}

/* ---------- 포털 본체 ---------- */

function CreatorPortal({ session, onLogout }: { session: CreatorSession; onLogout: () => void }) {
  const [tab, setTab] = useState<"rfps" | "settings">("rfps");
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
  const tabBtn = (active: boolean) =>
    `rounded-md px-4 py-2 text-sm font-semibold transition-colors ${active ? "bg-black text-white" : "text-neutral-500 hover:bg-neutral-100"}`;

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">크리에이터 포털</h1>
          <p className="mt-2 text-sm text-neutral-500">
            {session.name} 님 ({session.channel}) — 받은 RFP에 견적을 제출하고 클라이언트와 소통하세요.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <nav className="flex gap-1 rounded-lg border border-neutral-200 p-1">
            <button className={tabBtn(tab === "rfps")} onClick={() => setTab("rfps")}>받은 RFP</button>
            <button className={tabBtn(tab === "settings")} onClick={() => setTab("settings")}>설정</button>
          </nav>
          <button onClick={onLogout} className="rounded-md border border-neutral-200 px-4 py-2 text-sm hover:border-black">
            로그아웃
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-600">{error}</div>
      )}

      {tab === "settings" ? (
        <SettingsTab token={session.token} />
      ) : (
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[300px_1fr_300px]">
        <aside className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold">받은 업무 요청 (RFP)</h2>
          {rfps.length === 0 && (
            <p className="rounded-md border border-neutral-200 p-4 text-xs text-neutral-400">
              아직 받은 RFP가 없습니다. 설정 탭에서 컨택 이메일·단가를 등록해 두면 매칭 확률이 올라갑니다.
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

        <section className="flex flex-col gap-6">
          {active ? (
            <>
              <div className="rounded-lg border border-neutral-200 p-5">
                <h3 className="font-semibold">{active.campaign_name}</h3>
                <div className="mt-3">
                  <ProcessBar stages={active.stages} />
                </div>
                <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 border-t border-neutral-100 pt-4 text-sm">
                  <dt className="text-neutral-400">보수</dt>
                  <dd>견적 제안 후 개별 협의</dd>
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

              <div className="rounded-lg border border-neutral-200 p-5">
                <h3 className="font-semibold">1차 견적 제출</h3>
                {quoteSent ? (
                  <p className="mt-3 rounded-md bg-neutral-50 p-4 text-sm text-neutral-600">
                    견적이 제출되었습니다. 클라이언트 검토 후 알림으로 결과를 받게 됩니다.
                  </p>
                ) : (
                  <div className="mt-3 flex flex-col gap-3">
                    <textarea
                      className={`${inputCls} min-h-20 resize-y`}
                      placeholder="콘텐츠 기획 방향 (어떤 방향·형식으로 제작할지)"
                      value={quote.content_plan ?? ""}
                      onChange={(e) => setQuote({ ...quote, content_plan: e.target.value })}
                    />
                    <div className="grid grid-cols-3 gap-3">
                      <select
                        className={inputCls}
                        value={quote.content_format ?? ""}
                        onChange={(e) => setQuote({ ...quote, content_format: e.target.value || undefined })}
                      >
                        <option value="">형식 선택</option>
                        <option value="shortform">숏폼</option>
                        <option value="longform">롱폼</option>
                        <option value="package">패키지</option>
                      </select>
                      <input
                        className={inputCls}
                        type="number"
                        placeholder="길이(분)"
                        value={quote.length_minutes ?? ""}
                        onChange={(e) =>
                          setQuote({ ...quote, length_minutes: e.target.value ? Number(e.target.value) : undefined })
                        }
                      />
                      <input
                        className={inputCls}
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
                        m.direction === "inbound" ? "self-end bg-black text-white" : "self-start bg-neutral-100"
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
                    className={inputCls}
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
      )}
    </div>
  );
}
