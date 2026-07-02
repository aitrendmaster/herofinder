import Link from "next/link";

const STEPS = [
  { no: "01", title: "인플루언서 탐색", desc: "등급·채널·카테고리·활성도 필터로 후보 탐색", href: "/discovery" },
  { no: "02", title: "RFP 작성", desc: "예산·기간·콘텐츠·광고 타입 업무요청서 등록", href: "/brief" },
  { no: "03", title: "AI 맞춤 추천", desc: "매칭 점수 + 예상 KPI 기반 선별", href: "/recommend" },
  { no: "04", title: "송부 & 커뮤니케이션", desc: "RFP 자동 송부, 회신은 메시지함으로", href: "/messages" },
];

export default function Home() {
  return (
    <div className="flex flex-col gap-16 py-10">
      <section className="flex flex-col gap-6">
        <p className="text-sm font-semibold tracking-widest text-neutral-400">
          B2B INFLUENCER MATCHING PLATFORM
        </p>
        <h1 className="max-w-2xl text-5xl font-bold leading-tight tracking-tight">
          브랜드에 맞는 히어로를
          <br />
          데이터로 찾다
        </h1>
        <p className="max-w-xl text-lg text-neutral-500">
          YouTube · Instagram · TikTok 인플루언서를 주간 활성 데이터로 탐색하고, RFP 한 번으로
          섭외부터 성과 측정까지.
        </p>
        <div>
          <Link
            href="/discovery"
            className="inline-block rounded-md bg-black px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-neutral-800"
          >
            탐색 시작하기
          </Link>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-4">
        {STEPS.map((s) => (
          <Link
            key={s.no}
            href={s.href}
            className="group rounded-lg border border-neutral-200 p-6 transition-colors hover:border-black"
          >
            <p className="text-xs font-bold text-neutral-300 group-hover:text-black">{s.no}</p>
            <h3 className="mt-3 font-semibold">{s.title}</h3>
            <p className="mt-2 text-sm text-neutral-500">{s.desc}</p>
          </Link>
        ))}
      </section>
    </div>
  );
}
