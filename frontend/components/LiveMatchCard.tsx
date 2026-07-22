import Link from "next/link";
import { type LiveMatch } from "@/lib/api";
import { countryFlag } from "@/lib/flags";
import SurfaceBadge from "@/components/SurfaceBadge";

export default function LiveMatchCard({ match }: { match: LiveMatch }) {
  const s = match.score;
  const setScores = s?.set_scores ?? [];
  // ATP live matches have no point stream — link to the tournament instead of
  // the (empty) SSE feed. IBM matches keep their live feed link.
  const href = match.match_id.startsWith("atp-") && match.tournament_id
    ? `/tournaments/${match.tournament_id}`
    : `/live/${match.match_id}`;

  const rows = [
    {
      name: match.p1_name,
      country: match.p1_country,
      server: s?.server === 1,
      sets: s?.p1_sets ?? 0,
      games: s?.p1_games ?? 0,
      game: s?.p1_game,
      setScores: setScores.map((x) => x[0]),
    },
    {
      name: match.p2_name,
      country: match.p2_country,
      server: s?.server === 2,
      sets: s?.p2_sets ?? 0,
      games: s?.p2_games ?? 0,
      game: s?.p2_game,
      setScores: setScores.map((x) => x[1]),
    },
  ];

  return (
    <Link
      href={href}
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
        {rows.map((p, i) => (
          <div key={i} className="flex items-center justify-between gap-3">
            <span className="font-semibold">
              {countryFlag(p.country)} {p.name} {p.server && "🎾"}
            </span>
            <span className="flex items-center gap-2 tabular-nums text-zinc-300">
              {p.setScores.length > 0 ? (
                p.setScores.map((g, j) => (
                  <span key={j} className="w-4 text-center">
                    {g}
                  </span>
                ))
              ) : (
                <span className="text-zinc-500">
                  {p.sets} sets · {p.games} games
                </span>
              )}
              {p.game && (
                <span className="ml-1 w-6 rounded bg-zinc-800 text-center text-sm">
                  {p.game}
                </span>
              )}
            </span>
          </div>
        ))}
      </div>
    </Link>
  );
}
