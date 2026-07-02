import type { Stage } from "@/lib/api";

/** 전체 업무 프로세스 라인바 — 완료=검정 채움, 현재=링 강조, 미도래=회색 */
export default function ProcessBar({ stages, compact = false }: { stages: Stage[]; compact?: boolean }) {
  return (
    <div className="w-full">
      <div className="flex items-center">
        {stages.map((stage, i) => (
          <div key={stage.key} className="flex flex-1 items-center last:flex-none">
            <div className="flex flex-col items-center">
              <div
                className={`flex items-center justify-center rounded-full border-2 transition-colors ${
                  compact ? "h-4 w-4" : "h-6 w-6"
                } ${
                  stage.done
                    ? "border-black bg-black"
                    : stage.current
                      ? "border-black bg-white ring-2 ring-black/20"
                      : "border-neutral-300 bg-white"
                }`}
              >
                {stage.done && (
                  <svg viewBox="0 0 12 12" className={compact ? "h-2 w-2" : "h-3 w-3"} fill="none">
                    <path d="M2 6l3 3 5-6" stroke="white" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                )}
                {stage.current && !stage.done && (
                  <span className={`rounded-full bg-black ${compact ? "h-1.5 w-1.5" : "h-2 w-2"}`} />
                )}
              </div>
            </div>
            {i < stages.length - 1 && (
              <div className={`mx-0.5 h-0.5 flex-1 ${stage.done ? "bg-black" : "bg-neutral-200"}`} />
            )}
          </div>
        ))}
      </div>
      {!compact && (
        <div className="mt-1.5 flex">
          {stages.map((stage) => (
            <div key={stage.key} className="flex-1 last:flex-none">
              <span
                className={`block text-[10px] leading-tight ${
                  stage.current
                    ? "font-bold text-black"
                    : stage.done
                      ? "text-neutral-600"
                      : "text-neutral-300"
                }`}
              >
                {stage.label}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
