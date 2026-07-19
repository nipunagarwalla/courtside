interface StatBarProps {
  label: string;
  p1value: number | null;
  p2value: number | null;
  p1name: string;
  p2name: string;
  invertBetter?: boolean; // when true, the SMALLER value is better (e.g. double faults)
  format?: (v: number) => string;
}

export default function StatBar({
  label,
  p1value,
  p2value,
  p1name,
  p2name,
  invertBetter = false,
  format = (v) => String(v),
}: StatBarProps) {
  const v1 = p1value ?? 0;
  const v2 = p2value ?? 0;
  const total = v1 + v2;
  const w1 = total > 0 ? (v1 / total) * 100 : 50;
  const w2 = total > 0 ? (v2 / total) * 100 : 50;
  const p1Better = invertBetter ? v1 < v2 : v1 > v2;
  const p2Better = invertBetter ? v2 < v1 : v2 > v1;

  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between text-sm">
        <span className={p1Better ? "font-semibold text-green-400" : "text-zinc-300"}>
          {p1value != null ? format(p1value) : "—"}
        </span>
        <span className="text-xs uppercase tracking-wide text-zinc-400">{label}</span>
        <span className={p2Better ? "font-semibold text-green-400" : "text-zinc-300"}>
          {p2value != null ? format(p2value) : "—"}
        </span>
      </div>
      <div className="flex h-2 gap-1">
        <div className="flex flex-1 justify-end overflow-hidden rounded-l bg-zinc-800">
          <div
            className={`h-full rounded-l ${p1Better ? "bg-green-600" : "bg-zinc-600"}`}
            style={{ width: `${w1}%` }}
            title={p1name}
          />
        </div>
        <div className="flex flex-1 overflow-hidden rounded-r bg-zinc-800">
          <div
            className={`h-full rounded-r ${p2Better ? "bg-green-600" : "bg-zinc-600"}`}
            style={{ width: `${w2}%` }}
            title={p2name}
          />
        </div>
      </div>
    </div>
  );
}
