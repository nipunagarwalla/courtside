"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { type Player } from "@/lib/api";
import { countryFlag } from "@/lib/flags";
import PlayerSearchInput from "@/components/PlayerSearchInput";

function SelectedPlayer({ player }: { player: Player | null }) {
  if (!player) return <p className="mt-3 text-sm text-zinc-500">No player selected</p>;
  return (
    <p className="mt-3 flex items-center gap-2 text-sm">
      <span className="rounded bg-zinc-800 px-2 py-0.5 text-xs font-semibold">
        {player.current_rank != null ? `#${player.current_rank}` : "unranked"}
      </span>
      <span className="font-semibold">{player.name}</span>
      <span className="text-zinc-400">{countryFlag(player.country)}</span>
    </p>
  );
}

export default function ComparePage() {
  const router = useRouter();
  const [p1, setP1] = useState<Player | null>(null);
  const [p2, setP2] = useState<Player | null>(null);

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-3xl font-bold">Compare Players</h1>
      <p className="mt-1 text-zinc-400">Pick two players to see their head-to-head.</p>

      <div className="mt-8 grid gap-6 sm:grid-cols-2">
        <div>
          <label className="mb-2 block text-sm font-medium text-zinc-300">Player 1</label>
          <PlayerSearchInput placeholder="Search player 1…" onSelect={setP1} />
          <SelectedPlayer player={p1} />
        </div>
        <div>
          <label className="mb-2 block text-sm font-medium text-zinc-300">Player 2</label>
          <PlayerSearchInput placeholder="Search player 2…" onSelect={setP2} />
          <SelectedPlayer player={p2} />
        </div>
      </div>

      <button
        disabled={!p1 || !p2}
        onClick={() => p1 && p2 && router.push(`/compare/${p1.id}/${p2.id}`)}
        className="mt-8 rounded-lg bg-blue-600 px-6 py-2.5 font-semibold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-500"
      >
        Compare
      </button>
    </main>
  );
}
