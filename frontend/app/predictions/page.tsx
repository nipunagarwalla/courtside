"use client";

import Link from "next/link";
import useSWR from "swr";
import { getUpcomingPredictions, type UpcomingPrediction } from "@/lib/api";
import { countryFlag } from "@/lib/flags";
import SurfaceBadge from "@/components/SurfaceBadge";
import TierBadge from "@/components/TierBadge";
import Disclaimer from "@/components/Disclaimer";

const CONFIDENCE_CLASS: Record<string, string> = {
  High: "bg-green-600 text-white",
  Moderate: "bg-yellow-500 text-black",
  "Toss-up": "bg-zinc-600 text-white",
};

function MatchCard({ m }: { m: UpcomingPrediction }) {
  const p1Pct = Math.round(m.prediction.p1_win_probability * 100);
  return (
    <Link
      href={`/compare/${m.p1.id}/${m.p2.id}`}
      className="block rounded-xl border border-zinc-800 bg-zinc-900 p-5 transition-colors hover:border-zinc-600"
    >
      <div className="flex flex-wrap items-center gap-2 text-sm text-zinc-400">
        <span>{m.tournament ?? "—"}</span>
        <TierBadge tier={m.tier} />
        <SurfaceBadge surface={m.surface} />
        <span>· {m.round ?? ""}</span>
      </div>
      <div className="mt-3 flex items-center justify-between gap-4">
        <span className="font-semibold">
          {countryFlag(m.p1.country)} {m.p1.name}
          {m.p1.current_rank != null && (
            <span className="ml-1 text-xs text-zinc-500">#{m.p1.current_rank}</span>
          )}
        </span>
        <span className="text-zinc-600">vs</span>
        <span className="font-semibold">
          {countryFlag(m.p2.country)} {m.p2.name}
          {m.p2.current_rank != null && (
            <span className="ml-1 text-xs text-zinc-500">#{m.p2.current_rank}</span>
          )}
        </span>
      </div>
      <div className="mt-3 flex items-center gap-3">
        <span className="text-sm font-bold tabular-nums">{p1Pct}%</span>
        <div className="flex h-3 flex-1 overflow-hidden rounded-full bg-zinc-800">
          <div className="bg-blue-500" style={{ width: `${p1Pct}%` }} />
          <div className="bg-orange-500" style={{ width: `${100 - p1Pct}%` }} />
        </div>
        <span className="text-sm font-bold tabular-nums">{100 - p1Pct}%</span>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span
          className={`rounded px-2 py-0.5 text-xs font-bold ${CONFIDENCE_CLASS[m.prediction.confidence]}`}
        >
          {m.prediction.confidence}
        </span>
        {m.prediction.key_factors.slice(0, 2).map((f) => (
          <span key={f.factor} className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-300">
            {f.factor}
          </span>
        ))}
      </div>
    </Link>
  );
}

export default function PredictionsPage() {
  const { data, error, isLoading } = useSWR(
    "upcoming-predictions",
    getUpcomingPredictions,
    { shouldRetryOnError: false }
  );
  const notTrained = error?.message?.startsWith("503");

  const byDate = new Map<string, UpcomingPrediction[]>();
  for (const m of data ?? []) {
    const key = m.match_date ?? "TBD";
    if (!byDate.has(key)) byDate.set(key, []);
    byDate.get(key)!.push(m);
  }

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-3xl font-bold">Upcoming Matches</h1>
      <p className="mt-1 text-zinc-400">
        {new Date().toLocaleDateString("en-US", {
          weekday: "long", year: "numeric", month: "long", day: "numeric",
        })}
      </p>

      {isLoading && (
        <div className="mt-6 space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-36 animate-pulse rounded-xl bg-zinc-900" />
          ))}
        </div>
      )}

      {notTrained && (
        <p className="mt-10 rounded-xl border border-zinc-800 bg-zinc-900 p-10 text-center text-zinc-400">
          Predictions unavailable — model needs training.
        </p>
      )}

      {data && data.length === 0 && (
        <p className="mt-10 rounded-xl border border-zinc-800 bg-zinc-900 p-10 text-center text-zinc-400">
          No matches scheduled in the next 7 days.
        </p>
      )}

      {[...byDate.entries()].map(([d, ms]) => (
        <section key={d} className="mt-8">
          <h2 className="mb-3 text-lg font-semibold text-zinc-300">{d}</h2>
          <div className="space-y-4">
            {ms.map((m) => (
              <MatchCard key={m.match_id} m={m} />
            ))}
          </div>
        </section>
      ))}

      <Disclaimer />
    </main>
  );
}
