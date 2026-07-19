"use client";

import Link from "next/link";
import { use } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { getCompare, type H2HBucket } from "@/lib/api";
import { countryFlag } from "@/lib/flags";
import SurfaceBadge from "@/components/SurfaceBadge";
import TierBadge from "@/components/TierBadge";
import FormPills from "@/components/FormPills";
import StatBar from "@/components/StatBar";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-8 rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-zinc-400">
        {title}
      </h2>
      {children}
    </section>
  );
}

function BucketRow({
  label,
  bucket,
  badge,
}: {
  label: string;
  bucket: H2HBucket | undefined;
  badge?: React.ReactNode;
}) {
  const b = bucket ?? { total: 0, p1_wins: 0, p2_wins: 0 };
  return (
    <div className="flex items-center justify-between border-b border-zinc-800 py-2 last:border-0">
      <span className="flex items-center gap-2 text-sm text-zinc-300">
        {badge ?? label}
      </span>
      {b.total === 0 ? (
        <span className="text-sm text-zinc-600">No meetings</span>
      ) : (
        <span className="text-sm tabular-nums">
          <span className="font-semibold">{b.p1_wins}</span>
          <span className="text-zinc-500"> – </span>
          <span className="font-semibold">{b.p2_wins}</span>
          <span className="ml-2 text-zinc-500">({b.total})</span>
        </span>
      )}
    </div>
  );
}

export default function CompareResultPage({
  params,
}: {
  params: Promise<{ p1: string; p2: string }>;
}) {
  const { p1, p2 } = use(params);
  const router = useRouter();
  const { data, error, isLoading } = useSWR(`compare-${p1}-${p2}`, () =>
    getCompare(p1, p2)
  );

  if (error)
    return (
      <main className="mx-auto max-w-4xl px-4 py-10">
        <p className="text-red-400">
          Could not load comparison — one or both players were not found.
        </p>
        <Link href="/compare" className="mt-4 inline-block text-blue-400 hover:underline">
          ← Back to compare
        </Link>
      </main>
    );

  if (isLoading || !data)
    return (
      <main className="mx-auto max-w-4xl px-4 py-10">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="mt-6 h-40 animate-pulse rounded-xl bg-zinc-900" />
        ))}
      </main>
    );

  const { player1, player2, h2h } = data;
  const p1Pct = h2h.total_matches ? (h2h.p1_wins / h2h.total_matches) * 100 : 50;
  const p1Higher =
    player1.current_rank != null &&
    (player2.current_rank == null || player1.current_rank < player2.current_rank);
  const p2Higher =
    player2.current_rank != null &&
    (player1.current_rank == null || player2.current_rank < player1.current_rank);

  const serve1 = data.serve_stats.p1;
  const serve2 = data.serve_stats.p2;
  const rates1 = data.surface_win_rates.p1;
  const rates2 = data.surface_win_rates.p2;
  const pctFmt = (v: number) => `${v.toFixed(1)}%`;
  const rateFmt = (v: number) => `${(v * 100).toFixed(1)}%`;

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      {/* 1 — Player headers */}
      <div className="grid grid-cols-2 gap-4">
        {[
          { p: player1, higher: p1Higher },
          { p: player2, higher: p2Higher },
        ].map(({ p, higher }, i) => (
          <Link
            key={p.id}
            href={`/players/${p.id}`}
            className={`rounded-xl border p-6 transition-colors hover:border-zinc-500 ${
              higher ? "border-green-600 bg-green-950/40" : "border-zinc-800 bg-zinc-900"
            } ${i === 1 ? "text-right" : ""}`}
          >
            <div className="text-2xl font-bold">{p.name}</div>
            <div className="mt-1 text-zinc-400">
              {countryFlag(p.country)} {p.country ?? ""}
            </div>
            <div className={`mt-2 text-lg font-semibold ${higher ? "text-green-400" : "text-zinc-300"}`}>
              {p.current_rank != null ? `#${p.current_rank}` : "Unranked"}
              {p.current_points != null && (
                <span className="ml-2 text-sm font-normal text-zinc-500">
                  {p.current_points.toLocaleString()} pts
                </span>
              )}
            </div>
          </Link>
        ))}
      </div>

      {/* 2 — H2H scoreboard */}
      <Section title="Head to Head">
        <div className="flex items-center justify-center gap-6 text-center">
          <span className="text-lg font-semibold">{player1.name}</span>
          <span className="text-5xl font-bold tabular-nums">
            {h2h.p1_wins}
            <span className="mx-3 text-zinc-600">—</span>
            {h2h.p2_wins}
          </span>
          <span className="text-lg font-semibold">{player2.name}</span>
        </div>
        <p className="mt-2 text-center text-sm text-zinc-500">
          {h2h.total_matches} matches total
        </p>
        {h2h.total_matches > 0 && (
          <div className="mx-auto mt-4 max-w-md">
            <div className="flex h-3 overflow-hidden rounded-full bg-zinc-800">
              <div className="bg-blue-500" style={{ width: `${p1Pct}%` }} />
              <div className="bg-orange-500" style={{ width: `${100 - p1Pct}%` }} />
            </div>
            <div className="mt-1 flex justify-between text-xs text-zinc-500">
              <span>{p1Pct.toFixed(0)}%</span>
              <span>{(100 - p1Pct).toFixed(0)}%</span>
            </div>
          </div>
        )}
      </Section>

      {/* 3 — Surface breakdown */}
      <Section title="By Surface">
        {(["hard", "clay", "grass"] as const).map((s) => (
          <BucketRow
            key={s}
            label={s}
            bucket={data.h2h_by_surface[s]}
            badge={<SurfaceBadge surface={s[0].toUpperCase() + s.slice(1)} />}
          />
        ))}
      </Section>

      {/* 4 — Round + tier tables */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Section title="By Round">
          {["F", "SF", "QF", "R16"].map((r) => (
            <BucketRow key={r} label={r} bucket={data.h2h_by_round[r]} />
          ))}
        </Section>
        <Section title="By Tier">
          {["Grand Slam", "Masters 1000", "ATP 500", "ATP 250"].map((t) => (
            <BucketRow
              key={t}
              label={t}
              bucket={data.h2h_by_tier[t]}
              badge={<TierBadge tier={t} />}
            />
          ))}
        </Section>
      </div>

      {/* 5 — Recent form */}
      <Section title="Recent Form (last 10, most recent right)">
        <div className="space-y-4">
          {[
            { name: player1.name, form: data.recent_form.p1_last10, pct: data.recent_form.p1_last10_pct },
            { name: player2.name, form: data.recent_form.p2_last10, pct: data.recent_form.p2_last10_pct },
          ].map(({ name, form, pct }) => (
            <div key={name} className="flex flex-wrap items-center gap-4">
              <span className="w-40 truncate text-sm font-semibold">{name}</span>
              <FormPills results={form} />
              <span className="text-sm text-zinc-400">
                {pct != null ? `${pct.toFixed(0)}% wins` : "—"}
              </span>
            </div>
          ))}
        </div>
      </Section>

      {/* 6 — Stats bars */}
      <Section title="Stat Battle">
        <div className="mb-4 flex justify-between text-sm font-semibold">
          <span>{player1.name}</span>
          <span>{player2.name}</span>
        </div>
        <div className="space-y-5">
          <StatBar label="Career titles" p1name={player1.name} p2name={player2.name}
            p1value={data.career_stats.p1.titles} p2value={data.career_stats.p2.titles} />
          <StatBar label="Overall win %" p1name={player1.name} p2name={player2.name}
            p1value={rates1.overall} p2value={rates2.overall} format={rateFmt} />
          <StatBar label="Hard win %" p1name={player1.name} p2name={player2.name}
            p1value={rates1.hard} p2value={rates2.hard} format={rateFmt} />
          <StatBar label="Clay win %" p1name={player1.name} p2name={player2.name}
            p1value={rates1.clay} p2value={rates2.clay} format={rateFmt} />
          <StatBar label="Grass win %" p1name={player1.name} p2name={player2.name}
            p1value={rates1.grass} p2value={rates2.grass} format={rateFmt} />
          <StatBar label="Avg aces / match" p1name={player1.name} p2name={player2.name}
            p1value={serve1.avg_aces_per_match} p2value={serve2.avg_aces_per_match} />
          <StatBar label="Avg DFs / match" p1name={player1.name} p2name={player2.name}
            p1value={serve1.avg_dfs_per_match} p2value={serve2.avg_dfs_per_match} invertBetter />
          <StatBar label="1st serve %" p1name={player1.name} p2name={player2.name}
            p1value={serve1.first_serve_pct} p2value={serve2.first_serve_pct} format={pctFmt} />
          <StatBar label="BP saved %" p1name={player1.name} p2name={player2.name}
            p1value={serve1.bp_save_pct} p2value={serve2.bp_save_pct} format={pctFmt} />
        </div>
      </Section>

      {/* 7 — H2H match list */}
      <Section title={`All Meetings (${data.h2h_matches.length})`}>
        <div className="max-h-96 overflow-y-auto">
          <table className="w-full text-sm">
            <tbody>
              {data.h2h_matches.map((m) => {
                const winner = m.p1_won ? player1 : player2;
                const loser = m.p1_won ? player2 : player1;
                return (
                  <tr
                    key={m.match_id}
                    onClick={() => router.push(`/matches/${m.match_id}`)}
                    className="cursor-pointer border-b border-zinc-800 last:border-0 hover:bg-zinc-800"
                  >
                    <td className="px-2 py-3 text-zinc-400">{m.match_date ?? "—"}</td>
                    <td className="px-2 py-3">
                      <span className="mr-2">{m.tournament_name ?? "—"}</span>
                      <TierBadge tier={m.tier} />
                    </td>
                    <td className="px-2 py-3">
                      <SurfaceBadge surface={m.surface} />
                    </td>
                    <td className="px-2 py-3 text-zinc-400">{m.round ?? "—"}</td>
                    <td className="px-2 py-3 text-zinc-300">{m.score ?? "—"}</td>
                    <td className="px-2 py-3">
                      <span className="font-bold">{winner.name}</span>
                      <span className="text-zinc-500"> d. {loser.name}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Section>
    </main>
  );
}
