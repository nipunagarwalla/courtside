"use client";

import Link from "next/link";
import { useState } from "react";
import useSWR from "swr";
import { getTournaments } from "@/lib/api";
import SurfaceBadge from "@/components/SurfaceBadge";
import TierBadge from "@/components/TierBadge";

const CURRENT_YEAR = new Date().getFullYear();
const YEARS = Array.from({ length: CURRENT_YEAR - 1967 }, (_, i) => CURRENT_YEAR - i);
const SURFACES = ["All", "Hard", "Clay", "Grass"];

function StatusBadge({ status }: { status: string | null }) {
  if (status === "upcoming")
    return <span className="rounded bg-blue-600 px-2 py-0.5 text-xs font-semibold">UPCOMING</span>;
  if (status === "in_progress")
    return (
      <span className="animate-pulse rounded bg-green-600 px-2 py-0.5 text-xs font-semibold">
        IN PROGRESS
      </span>
    );
  if (status === "completed")
    return <span className="rounded bg-zinc-700 px-2 py-0.5 text-xs font-semibold text-zinc-300">COMPLETED</span>;
  return null;
}

export default function TournamentsPage() {
  const [year, setYear] = useState(CURRENT_YEAR);
  const [surface, setSurface] = useState("All");

  const params = `year=${year}${surface !== "All" ? `&surface=${surface}` : ""}&limit=100`;
  const { data, error, isLoading } = useSWR(`tournaments-${params}`, () =>
    getTournaments(params)
  );

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-3xl font-bold">Tournaments</h1>
      <div className="mt-6 flex flex-wrap gap-3">
        <select
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          className="rounded-lg border border-zinc-800 bg-zinc-800 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
        >
          {YEARS.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
        <div className="flex overflow-hidden rounded-lg border border-zinc-800">
          {SURFACES.map((s) => (
            <button
              key={s}
              onClick={() => setSurface(s)}
              className={`px-4 py-2 text-sm transition-colors ${
                surface === s
                  ? "bg-zinc-700 text-white"
                  : "bg-zinc-900 text-zinc-400 hover:text-white"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="mt-6 text-red-400">Failed to load tournaments.</p>}
      {isLoading && (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="h-36 animate-pulse rounded-xl bg-zinc-900" />
          ))}
        </div>
      )}
      {data && data.length === 0 && (
        <p className="mt-6 text-zinc-400">No tournaments found.</p>
      )}
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data?.map((t) => (
          <Link
            key={t.id}
            href={`/tournaments/${t.id}`}
            className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 transition-colors hover:border-zinc-600"
          >
            <div className="flex items-start justify-between gap-2">
              <span className="font-bold">{t.name}</span>
              <StatusBadge status={t.status} />
            </div>
            <div className="mt-1 text-sm text-zinc-400">
              {t.start_date ?? "TBD"}
              {t.end_date ? ` → ${t.end_date}` : ""}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <SurfaceBadge surface={t.surface} />
              <TierBadge tier={t.tier} />
            </div>
            <div className="mt-2 text-sm text-zinc-500">
              {[t.city, t.country].filter(Boolean).join(", ") || " "}
            </div>
          </Link>
        ))}
      </div>
    </main>
  );
}
