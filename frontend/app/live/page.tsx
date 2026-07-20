"use client";

import useSWR from "swr";
import { getLive } from "@/lib/api";
import LiveMatchCard from "@/components/LiveMatchCard";

export default function LivePage() {
  const { data, isLoading } = useSWR("live-matches", getLive, {
    refreshInterval: 30_000,
  });

  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="flex items-center gap-3 text-3xl font-bold">
        Live Matches
        {data && data.length > 0 && (
          <span className="animate-pulse rounded bg-red-600 px-2 py-1 text-sm font-bold">
            {data.length} LIVE
          </span>
        )}
      </h1>

      {isLoading && (
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="h-32 animate-pulse rounded-xl bg-zinc-900" />
          ))}
        </div>
      )}

      {data && data.length === 0 && (
        <div className="mt-10 rounded-xl border border-zinc-800 bg-zinc-900 p-10 text-center">
          <p className="text-lg text-zinc-300">No live matches right now.</p>
          <p className="mt-2 text-zinc-500">Next: US Open starts Aug 24, 2026.</p>
        </div>
      )}

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {data?.map((m) => (
          <LiveMatchCard key={m.match_id} match={m} />
        ))}
      </div>
    </main>
  );
}
