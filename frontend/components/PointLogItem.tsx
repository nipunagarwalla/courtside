import { type PointRow } from "@/lib/api";

interface PointLogItemProps {
  point: PointRow;
  active: boolean;
  winnerName: string;
  onClick: () => void;
}

export default function PointLogItem({
  point,
  active,
  winnerName,
  onClick,
}: PointLogItemProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-lg px-3 py-2 text-left transition-colors ${
        active ? "bg-blue-950 ring-1 ring-blue-500" : "hover:bg-zinc-800"
      }`}
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
        <span className="w-10 shrink-0 text-zinc-500">Pt {point.point_number}</span>
        <span className="w-28 shrink-0 tabular-nums text-zinc-300">
          {point.score_before} → {point.score_after}
        </span>
        <span className="w-24 shrink-0 truncate font-semibold">{winnerName}</span>
        <span className="text-zinc-400">{point.point_end_type ?? "—"}</span>
        <span className="text-zinc-500">
          {point.serve_speed_kmh ? `${point.serve_speed_kmh} km/h` : "—"}
        </span>
        <span className="text-zinc-500">
          {point.rally_length != null
            ? `${point.rally_length} shot${point.rally_length === 1 ? "" : "s"}`
            : "—"}
        </span>
        <span className="ml-auto flex gap-1">
          {point.is_break_point && (
            <span className="rounded bg-orange-600 px-1.5 py-0.5 text-xs font-bold">BP</span>
          )}
          {point.is_set_point && (
            <span className="rounded bg-blue-600 px-1.5 py-0.5 text-xs font-bold">SP</span>
          )}
          {point.is_match_point && (
            <span className="rounded bg-red-600 px-1.5 py-0.5 text-xs font-bold">MP</span>
          )}
        </span>
      </div>
      {point.sentence && (
        <div className="mt-0.5 text-xs text-zinc-500">{point.sentence}</div>
      )}
    </button>
  );
}
