"use client";

import Link from "next/link";
import { use } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { getPlayer } from "@/lib/api";
import { countryFlag } from "@/lib/flags";
import WLBadge from "@/components/WLBadge";

function pct(v: number | null): string {
  return v != null ? `${(v * 100).toFixed(1)}%` : "—";
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
      <div className="text-xs uppercase tracking-wide text-zinc-400">{label}</div>
      <div className="mt-1 text-lg font-semibold">{value ?? "—"}</div>
    </div>
  );
}

export default function PlayerPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const { data: player, error, isLoading } = useSWR(`player-${id}`, () => getPlayer(id));

  if (error)
    return (
      <main className="mx-auto max-w-4xl px-4 py-10">
        <p className="text-red-400">Player not found.</p>
        <Link href="/players" className="mt-4 inline-block text-blue-400 hover:underline">
          ← Back to players
        </Link>
      </main>
    );

  if (isLoading || !player)
    return (
      <main className="mx-auto max-w-4xl px-4 py-10">
        <div className="h-10 w-72 animate-pulse rounded bg-zinc-800" />
        <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-lg bg-zinc-900" />
          ))}
        </div>
      </main>
    );

  const record = (w: number | null, l: number | null) =>
    w == null && l == null ? null : `${w ?? 0}–${l ?? 0}`;

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold">{player.name}</h1>
          <p className="mt-1 text-lg text-zinc-400">
            {countryFlag(player.country)} {player.country ?? ""}
            {player.hand ? ` · ${player.hand}-handed` : ""}
          </p>
          <a
            href={player.atp_profile_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 inline-block text-sm text-blue-400 hover:underline"
          >
            Official ATP profile ↗
          </a>
        </div>
        {player.current_rank != null && (
          <div className="rounded-xl bg-green-700 px-5 py-3 text-center">
            <div className="text-xs font-medium uppercase tracking-wide text-green-200">
              ATP Rank
            </div>
            <div className="text-3xl font-bold">#{player.current_rank}</div>
            {player.current_points != null && (
              <div className="text-xs text-green-200">
                {player.current_points.toLocaleString()} pts
              </div>
            )}
          </div>
        )}
      </header>

      <section className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Stat label="Overall Win Rate" value={pct(player.win_rate_overall)} />
        <Stat label="Hard Win Rate" value={pct(player.win_rate_hard)} />
        <Stat label="Clay Win Rate" value={pct(player.win_rate_clay)} />
        <Stat label="Grass Win Rate" value={pct(player.win_rate_grass)} />
      </section>

      <section className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Stat label="Career Titles" value={player.career_titles} />
        <Stat
          label="Career W/L"
          value={record(player.career_wins, player.career_losses)}
        />
        <Stat label="Career Prize Money" value={player.career_prize} />
        <Stat label="YTD Titles" value={player.ytd_titles} />
        <Stat label="YTD W/L" value={record(player.ytd_wins, player.ytd_losses)} />
        <Stat
          label="Career High Rank"
          value={
            player.hi_rank != null
              ? `#${player.hi_rank}${player.hi_rank_date ? ` (${player.hi_rank_date})` : ""}`
              : null
          }
        />
        <Stat label="Coach" value={player.coach} />
        <Stat
          label="Height / Weight / Plays"
          value={
            player.height_cm || player.weight_kg || player.hand
              ? `${player.height_cm ?? "?"} cm / ${player.weight_kg ?? "?"} kg / ${player.hand ?? "?"}`
              : null
          }
        />
        <Stat label="Turned Pro" value={player.turned_pro} />
      </section>

      <section className="mt-10">
        <h2 className="mb-3 text-lg font-semibold text-zinc-300">Recent Matches</h2>
        <div className="overflow-x-auto rounded-xl border border-zinc-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-900 text-left text-xs uppercase tracking-wide text-zinc-400">
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Tournament</th>
                <th className="px-4 py-3">Round</th>
                <th className="px-4 py-3">Opponent</th>
                <th className="px-4 py-3">Score</th>
                <th className="px-4 py-3">W/L</th>
              </tr>
            </thead>
            <tbody>
              {player.recent_matches.map((m) => (
                <tr
                  key={m.match_id}
                  onClick={() => router.push(`/matches/${m.match_id}`)}
                  className="cursor-pointer border-b border-zinc-800 last:border-0 hover:bg-zinc-900"
                >
                  <td className="px-4 py-3 text-zinc-400">{m.match_date ?? "—"}</td>
                  <td className="px-4 py-3">{m.tournament ?? "—"}</td>
                  <td className="px-4 py-3 text-zinc-400">{m.round ?? "—"}</td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/players/${m.opponent_id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="text-blue-400 hover:underline"
                    >
                      {m.opponent_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-zinc-300">{m.score ?? "—"}</td>
                  <td className="px-4 py-3">
                    <WLBadge result={m.result} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
