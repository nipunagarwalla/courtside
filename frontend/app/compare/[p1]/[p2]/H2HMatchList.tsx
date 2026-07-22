"use client";

import { useRouter } from "next/navigation";
import { type ComparePlayer, type H2HMatch } from "@/lib/api";
import SurfaceBadge from "@/components/SurfaceBadge";
import TierBadge from "@/components/TierBadge";

export default function H2HMatchList({
  matches,
  player1,
  player2,
}: {
  matches: H2HMatch[];
  player1: ComparePlayer;
  player2: ComparePlayer;
}) {
  const router = useRouter();
  return (
    <div className="max-h-96 overflow-y-auto">
      <table className="w-full text-sm">
        <tbody>
          {matches.map((m) => {
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
  );
}
