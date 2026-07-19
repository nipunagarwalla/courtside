"use client";

import Link from "next/link";
import { use } from "react";
import useSWR from "swr";
import { getTournament, type TournamentMatch } from "@/lib/api";
import SurfaceBadge from "@/components/SurfaceBadge";
import TierBadge from "@/components/TierBadge";

const ROUND_ORDER = ["F", "BR", "SF", "QF", "R16", "R32", "R64", "R128", "RR"];
const ROUND_LABELS: Record<string, string> = {
  F: "Final",
  BR: "Bronze Match",
  SF: "Semifinals",
  QF: "Quarterfinals",
  R16: "Round of 16",
  R32: "Round of 32",
  R64: "Round of 64",
  R128: "Round of 128",
  RR: "Round Robin",
};

function duration(minutes: number | null): string {
  if (minutes == null) return "—";
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

function groupByRound(matches: TournamentMatch[]) {
  const groups = new Map<string, TournamentMatch[]>();
  for (const m of matches) {
    const key = m.round ?? "Other";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(m);
  }
  return [...groups.entries()].sort(([a], [b]) => {
    const ia = ROUND_ORDER.indexOf(a);
    const ib = ROUND_ORDER.indexOf(b);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });
}

export default function TournamentPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: t, error, isLoading } = useSWR(`tournament-${id}`, () =>
    getTournament(id)
  );

  if (error)
    return (
      <main className="mx-auto max-w-4xl px-4 py-10">
        <p className="text-red-400">Tournament not found.</p>
        <Link href="/tournaments" className="mt-4 inline-block text-blue-400 hover:underline">
          ← Back to tournaments
        </Link>
      </main>
    );

  if (isLoading || !t)
    return (
      <main className="mx-auto max-w-4xl px-4 py-10">
        <div className="h-8 w-64 animate-pulse rounded bg-zinc-800" />
        <div className="mt-6 h-96 animate-pulse rounded-xl bg-zinc-900" />
      </main>
    );

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <header className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold">{t.name}</h1>
          <SurfaceBadge surface={t.surface} />
          <TierBadge tier={t.tier} />
        </div>
        <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm text-zinc-400">
          <span>
            {t.start_date ?? "TBD"}
            {t.end_date ? ` → ${t.end_date}` : ""} · {t.year}
          </span>
          {t.prize_money != null && (
            <span>Prize money: ${t.prize_money.toLocaleString()}</span>
          )}
          {t.draw_size != null && <span>Draw: {t.draw_size}</span>}
        </div>
      </header>

      {groupByRound(t.matches).map(([round, matches]) => (
        <section key={round} className="mt-8">
          <h2 className="mb-3 text-lg font-semibold text-zinc-300">
            {ROUND_LABELS[round] ?? round}
          </h2>
          <div className="overflow-x-auto rounded-xl border border-zinc-800">
            <table className="w-full text-sm">
              <tbody>
                {matches.map((m) => (
                  <tr key={m.id} className="border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
                    <td className="px-4 py-3">
                      {m.winner_id ? (
                        <Link href={`/players/${m.winner_id}`} className="font-semibold text-blue-400 hover:underline">
                          {m.winner_name}
                        </Link>
                      ) : (
                        <span className="font-semibold">{m.winner_name ?? "—"}</span>
                      )}
                      <span className="mx-2 text-zinc-600">d.</span>
                      {m.loser_id ? (
                        <Link href={`/players/${m.loser_id}`} className="text-blue-400 hover:underline">
                          {m.loser_name}
                        </Link>
                      ) : (
                        <span>{m.loser_name ?? "—"}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-zinc-300">
                      <Link href={`/matches/${m.id}`} className="hover:underline">
                        {m.score ?? "—"}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-right text-zinc-500">
                      {duration(m.minutes)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </main>
  );
}
