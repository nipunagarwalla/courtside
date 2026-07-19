"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { getTopPlayers } from "@/lib/api";
import { countryFlag } from "@/lib/flags";
import PlayerSearchInput from "@/components/PlayerSearchInput";

export default function PlayersPage() {
  const router = useRouter();
  const { data: top20, isLoading } = useSWR("top-20-players", () => getTopPlayers(20));

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-3xl font-bold">Players</h1>
      <div className="mt-6 max-w-xl">
        <PlayerSearchInput
          placeholder="Search players — try “sinner”…"
          onSelect={(p) => router.push(`/players/${p.id}`)}
        />
      </div>

      <h2 className="mt-12 mb-4 text-lg font-semibold text-zinc-300">Top 20</h2>
      {isLoading && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 20 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-zinc-900" />
          ))}
        </div>
      )}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {top20?.map((p) => (
          <Link
            key={p.id}
            href={`/players/${p.id}`}
            className="flex items-center gap-3 rounded-xl border border-zinc-800 bg-zinc-900 p-4 transition-colors hover:border-zinc-600"
          >
            <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-zinc-800 text-sm font-bold">
              {p.current_rank ?? "—"}
            </span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-semibold">{p.name}</span>
              <span className="block text-xs text-zinc-400">
                {countryFlag(p.country)} {p.country ?? ""}
              </span>
            </span>
          </Link>
        ))}
      </div>
    </main>
  );
}
