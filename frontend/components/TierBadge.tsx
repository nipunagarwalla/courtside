function tierClass(tier: string): string {
  if (tier === "Grand Slam") return "bg-yellow-500 text-black";
  if (tier === "Masters 1000") return "bg-purple-600 text-white";
  if (tier === "ATP 500") return "bg-blue-500 text-white";
  if (tier === "ATP 250") return "bg-zinc-600 text-white";
  return "bg-zinc-700 text-white";
}

export default function TierBadge({ tier }: { tier: string | null }) {
  if (!tier) return null;
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${tierClass(tier)}`}
    >
      {tier}
    </span>
  );
}
