"use client";

import Link from "next/link";
import { use, useState } from "react";
import useSWR from "swr";
import {
  getMatch,
  getMatchPoints,
  type MatchDetail,
  type MatchPoints,
} from "@/lib/api";
import SurfaceBadge from "@/components/SurfaceBadge";
import TierBadge from "@/components/TierBadge";
import MatchReplay from "@/components/MatchReplay";

type PointsState = "idle" | "loading" | "loaded" | "unavailable";

function PointsSection({
  matchId,
  winnerName,
  loserName,
}: {
  matchId: string;
  winnerName: string | null;
  loserName: string | null;
}) {
  const [pointsState, setPointsState] = useState<PointsState>("idle");
  const [points, setPoints] = useState<MatchPoints | null>(null);

  const loadPoints = async () => {
    setPointsState("loading");
    try {
      const data = await getMatchPoints(matchId);
      if (data.has_data) {
        setPoints(data);
        setPointsState("loaded");
      } else {
        setPointsState("unavailable");
      }
    } catch {
      setPointsState("unavailable");
    }
  };

  return (
    <section className="mt-6 rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-zinc-400">
        Point-by-Point Replay
      </h2>

      {pointsState === "idle" && (
        <div className="text-center">
          <button
            onClick={loadPoints}
            className="rounded-lg bg-blue-600 px-6 py-2.5 font-semibold text-white transition-colors hover:bg-blue-500"
          >
            Load point-by-point replay
          </button>
        </div>
      )}

      {pointsState === "loading" && (
        <div className="flex items-center justify-center gap-3 py-4 text-zinc-400">
          <span className="h-5 w-5 animate-spin rounded-full border-2 border-zinc-600 border-t-blue-500" />
          Fetching point data… (first load may take a few seconds)
        </div>
      )}

      {pointsState === "unavailable" && (
        <p className="py-2 text-center text-zinc-400">
          Point-by-point data not available for this match
        </p>
      )}

      {pointsState === "loaded" && points && (
        <MatchReplay
          matchId={matchId}
          player1Name={winnerName ?? "Player 1"}
          player2Name={loserName ?? "Player 2"}
          data={points}
        />
      )}
    </section>
  );
}

function pct(num: number | null, den: number | null): string {
  if (num == null || !den) return "—";
  return `${((num / den) * 100).toFixed(1)}%`;
}

function statRows(m: MatchDetail) {
  return [
    { label: "Aces", w: m.w_aces, l: m.l_aces },
    { label: "Double Faults", w: m.w_dfs, l: m.l_dfs },
    { label: "1st Serve In", w: pct(m.w_1stin, m.w_svpt), l: pct(m.l_1stin, m.l_svpt) },
    { label: "1st Serve Won", w: pct(m.w_1stwon, m.w_1stin), l: pct(m.l_1stwon, m.l_1stin) },
    { label: "2nd Serve Won", w: m.w_2ndwon, l: m.l_2ndwon },
    {
      label: "Break Points Saved",
      w: m.w_bpfaced != null ? `${m.w_bpsaved ?? 0}/${m.w_bpfaced}` : null,
      l: m.l_bpfaced != null ? `${m.l_bpsaved ?? 0}/${m.l_bpfaced}` : null,
    },
  ];
}

export default function MatchPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: match, error, isLoading } = useSWR(`match-${id}`, () => getMatch(id));

  if (error)
    return (
      <main className="mx-auto max-w-3xl px-4 py-10">
        <p className="text-red-400">Match not found.</p>
        <Link href="/" className="mt-4 inline-block text-blue-400 hover:underline">
          ← Home
        </Link>
      </main>
    );

  if (isLoading || !match)
    return (
      <main className="mx-auto max-w-3xl px-4 py-10">
        <div className="h-40 animate-pulse rounded-xl bg-zinc-900" />
        <div className="mt-6 h-64 animate-pulse rounded-xl bg-zinc-900" />
      </main>
    );

  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <header className="rounded-xl border border-zinc-800 bg-zinc-900 p-6 text-center">
        <div className="flex flex-wrap items-center justify-center gap-2 text-sm text-zinc-400">
          {match.tournament_id ? (
            <Link href={`/tournaments/${match.tournament_id}`} className="text-blue-400 hover:underline">
              {match.tournament_name}
            </Link>
          ) : (
            <span>{match.tournament_name}</span>
          )}
          <TierBadge tier={match.tournament_tier} />
          <SurfaceBadge surface={match.surface} />
          <span>· {match.round ?? ""}</span>
          <span>· {match.match_date ?? ""}</span>
        </div>
        <h1 className="mt-4 text-2xl font-bold">
          {match.winner_id ? (
            <Link href={`/players/${match.winner_id}`} className="hover:underline">
              {match.winner_name}
            </Link>
          ) : (
            match.winner_name
          )}
          <span className="mx-3 text-zinc-500">vs</span>
          {match.loser_id ? (
            <Link href={`/players/${match.loser_id}`} className="hover:underline">
              {match.loser_name}
            </Link>
          ) : (
            match.loser_name
          )}
        </h1>
        <p className="mt-2 text-xl tabular-nums text-zinc-300">{match.score ?? ""}</p>
        {match.minutes != null && (
          <p className="mt-1 text-sm text-zinc-500">
            {Math.floor(match.minutes / 60)}h {match.minutes % 60}m
          </p>
        )}
      </header>

      <section className="mt-6 overflow-x-auto rounded-xl border border-zinc-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900 text-xs uppercase tracking-wide text-zinc-400">
              <th className="px-4 py-3 text-left">{match.winner_name}</th>
              <th className="px-4 py-3 text-center">Stat</th>
              <th className="px-4 py-3 text-right">{match.loser_name}</th>
            </tr>
          </thead>
          <tbody>
            {statRows(match).map((row) => (
              <tr key={row.label} className="border-b border-zinc-800 last:border-0">
                <td className="px-4 py-3 text-left font-semibold tabular-nums">
                  {row.w ?? "—"}
                </td>
                <td className="px-4 py-3 text-center text-zinc-400">{row.label}</td>
                <td className="px-4 py-3 text-right font-semibold tabular-nums">
                  {row.l ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <PointsSection
        matchId={id}
        winnerName={match.winner_name}
        loserName={match.loser_name}
      />
    </main>
  );
}
