"use client";

import Link from "next/link";
import useSWR from "swr";
import { getRankings } from "@/lib/api";
import { countryFlag } from "@/lib/flags";

function Movement({ value }: { value: number | null }) {
  if (value == null || value === 0) return <span className="text-zinc-600">—</span>;
  if (value > 0) return <span className="text-green-400">▲{value}</span>;
  return <span className="text-red-400">▼{Math.abs(value)}</span>;
}

function Skeleton() {
  return (
    <tbody>
      {Array.from({ length: 15 }).map((_, i) => (
        <tr key={i} className="border-b border-zinc-800">
          {Array.from({ length: 6 }).map((_, j) => (
            <td key={j} className="px-4 py-3">
              <div className="h-4 animate-pulse rounded bg-zinc-800" />
            </td>
          ))}
        </tr>
      ))}
    </tbody>
  );
}

export default function RankingsPage() {
  const { data, error, isLoading } = useSWR("rankings-100", () => getRankings(100));

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-3xl font-bold">ATP Rankings</h1>
      <p className="mt-1 text-sm text-zinc-400">
        {data?.[0]?.week_date ? `Last updated: ${data[0].week_date}` : " "}
      </p>
      {error && (
        <p className="mt-6 text-red-400">Failed to load rankings. Is the API running?</p>
      )}
      <div className="mt-6 overflow-x-auto rounded-xl border border-zinc-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900 text-left text-xs uppercase tracking-wide text-zinc-400">
              <th className="px-4 py-3">Rank</th>
              <th className="px-4 py-3">+/-</th>
              <th className="px-4 py-3">Player</th>
              <th className="px-4 py-3">Country</th>
              <th className="px-4 py-3 text-right">Points</th>
              <th className="px-4 py-3 text-right">YTD Wins</th>
            </tr>
          </thead>
          {isLoading ? (
            <Skeleton />
          ) : (
            <tbody>
              {data?.map((r) => (
                <tr key={r.player_id} className="border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
                  <td className="px-4 py-3 font-semibold">{r.rank}</td>
                  <td className="px-4 py-3">
                    <Movement value={r.movement} />
                  </td>
                  <td className="px-4 py-3">
                    <Link href={`/players/${r.player_id}`} className="text-blue-400 hover:underline">
                      {r.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-zinc-400">
                    {countryFlag(r.country)} {r.country ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    {r.points?.toLocaleString() ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-zinc-400">
                    {r.ytd_wins ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          )}
        </table>
      </div>
    </main>
  );
}
