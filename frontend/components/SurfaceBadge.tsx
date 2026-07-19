const COLORS: Record<string, string> = {
  hard: "bg-blue-600 text-white",
  clay: "bg-orange-600 text-white",
  grass: "bg-green-600 text-white",
  carpet: "bg-zinc-500 text-white",
};

export default function SurfaceBadge({ surface }: { surface: string | null }) {
  if (!surface) return null;
  const cls = COLORS[surface.toLowerCase()] ?? "bg-zinc-600 text-white";
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${cls}`}>
      {surface}
    </span>
  );
}
