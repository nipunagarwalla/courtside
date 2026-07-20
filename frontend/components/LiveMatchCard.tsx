import Link from "next/link";
import { type LiveMatch } from "@/lib/api";
import SurfaceBadge from "@/components/SurfaceBadge";

export default function LiveMatchCard({ match }: { match: LiveMatch }) {
  const s = match.score;
  return (
    <Link
      href={`/live/${match.match_id}`}
      className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 transition-colors hover:border-zinc-600"
    >
      <div className="flex items-center justify-between">
        <span className="text-sm text-zinc-400">
          {match.tournament ?? ""} {match.round ? `· ${match.round}` : ""}
        </span>
        <span className="flex items-center gap-2">
          <SurfaceBadge surface={match.surface} />
          <span className="animate-pulse rounded bg-red-600 px-2 py-0.5 text-xs font-bold">
            LIVE
          </span>
        </span>
      </div>
      <div className="mt-3 space-y-1">
        {[
          { name: match.p1_name, server: s?.server === 1, sets: s?.p1_sets, games: s?.p1_games },
          { name: match.p2_name, server: s?.server === 2, sets: s?.p2_sets, games: s?.p2_games },
        ].map((p, i) => (
          <div key={i} className="flex items-center justify-between">
            <span className="font-semibold">
              {p.name} {p.server && "🎾"}
            </span>
            <span className="tabular-nums text-zinc-300">
              {p.sets ?? 0} sets · {p.games ?? 0} games
            </span>
          </div>
        ))}
      </div>
      {s?.score_after && (
        <p className="mt-2 text-sm text-zinc-500">Current game: {s.score_after}</p>
      )}
    </Link>
  );
}
