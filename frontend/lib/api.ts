const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface Influencer {
  id: number;
  name: string;
  channel: "youtube" | "instagram" | "tiktok";
  country: string;
  tier: "mega" | "power" | "micro" | "nano";
  category: string | null;
  cost_range_min: number | null;
  cost_range_max: number | null;
  followers: number;
  monthly_views: number;
  engagement_rate: number;
  growth_rate: number;
  is_trending: boolean;
}

export interface InfluencerList {
  total: number;
  page: number;
  page_size: number;
  items: Influencer[];
}

export interface Category {
  id: number;
  name: string;
  sort_order: number;
}

export interface CampaignInput {
  name: string;
  budget_range?: string;
  period_start?: string;
  period_end?: string;
  content_detail?: string;
  ad_type: "ppl" | "branded";
  include_offline: boolean;
  need_ip_license: boolean;
  deadline?: string;
  expectation?: string;
  // V3 — 콘텐츠 규격·추가 보상 (업무 범위에 따라 크리에이터 견적이 달라짐)
  content_format?: "shortform" | "longform" | "package";
  longform_minutes?: number;
  shortform_minutes?: number;
  additional_rewards?: string;
  provided_resources?: string;
  must_include?: string;
}

export interface Campaign extends CampaignInput {
  id: number;
  status: string;
  created_at: string;
}

export interface Recommendation {
  influencer: Influencer;
  match_score: number;
  match_reason: string;
  estimated_kpi: {
    expected_reach: number;
    expected_clicks: number;
    expected_conversions: number;
    expected_engagement_rate: number;
  };
}

export interface DispatchResult {
  campaign_id: number;
  dispatched: number;
  recipients: string[];
}

export interface Message {
  id: number;
  campaign_id: number;
  influencer_id: number;
  direction: "inbound" | "outbound";
  body: string;
  created_at: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${detail || path}`);
  }
  return res.json() as Promise<T>;
}

export const getInfluencers = (params: Record<string, string>) =>
  request<InfluencerList>(`/api/influencers?${new URLSearchParams(params)}`);

export const getCategories = () => request<Category[]>("/api/categories");

export const createCampaign = (payload: CampaignInput) =>
  request<Campaign>("/api/campaigns", { method: "POST", body: JSON.stringify(payload) });

export const getCampaign = (id: number) => request<Campaign>(`/api/campaigns/${id}`);

export const aiRecommend = (campaignId: number) =>
  request<Recommendation[]>(`/api/campaigns/${campaignId}/ai-recommend`, { method: "POST" });

export const dispatchRfp = (campaignId: number, influencerIds: number[]) =>
  request<DispatchResult>(`/api/campaigns/${campaignId}/dispatch`, {
    method: "POST",
    body: JSON.stringify({ influencer_ids: influencerIds }),
  });

export interface ProposalJob {
  job_id: string;
  campaign_id: number;
  status: "pending" | "processing" | "completed" | "failed";
  xlsx_path?: string | null;
  pptx_path?: string | null;
  error?: string;
}

export const createProposal = (campaignId: number) =>
  request<{ job_id: string; status: string }>(`/api/campaigns/${campaignId}/proposal`, {
    method: "POST",
  });

export const getProposalJob = (jobId: string) =>
  request<ProposalJob>(`/api/proposal-jobs/${jobId}`);

export const outputUrl = (path: string) => `${API_BASE}${path}`;

export const getMessages = (campaignId: number) =>
  request<Message[]>(`/api/campaigns/${campaignId}/messages`);

export const sendMessage = (campaignId: number, influencerId: number, body: string) =>
  request<Message>(`/api/campaigns/${campaignId}/messages`, {
    method: "POST",
    body: JSON.stringify({ influencer_id: influencerId, body }),
  });

// 페이지 간 상태 전달 (선택 인플루언서 / 현재 캠페인)
export const store = {
  getSelectedIds(): number[] {
    if (typeof window === "undefined") return [];
    try {
      return JSON.parse(localStorage.getItem("hf_selected") ?? "[]");
    } catch {
      return [];
    }
  },
  setSelectedIds(ids: number[]) {
    localStorage.setItem("hf_selected", JSON.stringify(ids));
  },
  getCampaignId(): number | null {
    if (typeof window === "undefined") return null;
    const v = localStorage.getItem("hf_campaign");
    return v ? Number(v) : null;
  },
  setCampaignId(id: number) {
    localStorage.setItem("hf_campaign", String(id));
  },
};

export const TIER_LABELS: Record<string, string> = {
  mega: "메가",
  power: "파워",
  micro: "마이크로",
  nano: "나노",
};

export const CHANNEL_LABELS: Record<string, string> = {
  youtube: "YouTube",
  instagram: "Instagram",
  tiktok: "TikTok",
};

export const formatCount = (n: number): string => {
  if (n >= 100_000_000) return `${(n / 100_000_000).toFixed(1)}억`;
  if (n >= 10_000) return `${(n / 10_000).toFixed(1)}만`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}천`;
  return String(n);
};

export const formatKrw = (n: number | null): string =>
  n == null ? "-" : `${(n / 10_000).toLocaleString()}만원`;
