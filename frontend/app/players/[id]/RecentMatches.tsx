"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type RecentMatch } from "@/lib/api";
import WLBadge from "@/components/WLBadge";

export default function RecentMatches({ matches }: { matches: RecentMatch[] }) {
  const router = useRouter();
  return (
    <div className="overflow-x-auto rounded-xl border border-zinc-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900 text-left text-xs uppercase tracking-wide text-zinc-400">
            <th className="px-4 py-3">Date</th>
            <th className="px-4 py-3">Tournament</th>
            <th className="px-4 py-3">Round</th>
            <th className="px-4 py-3">Opponent</th>
            <th className="px-4 py-3">Score</th>
            <th className="px-4 py-3">W/L</th>
          </tr>
        </thead>
        <tbody>
          {matches.map((m) => (
            <tr
              key={m.match_id}
              onClick={() => router.push(`/matches/${m.match_id}`)}
              className="cursor-pointer border-b border-zinc-800 last:border-0 hover:bg-zinc-900"
            >
              <td className="px-4 py-3 text-zinc-400">{m.match_date ?? "—"}</td>
              <td className="px-4 py-3">{m.tournament ?? "—"}</td>
              <td className="px-4 py-3 text-zinc-400">{m.round ?? "—"}</td>
              <td className="px-4 py-3">
                <Link
                  href={`/players/${m.opponent_id}`}
                  onClick={(e) => e.stopPropagation()}
                  className="text-blue-400 hover:underline"
                >
                  {m.opponent_name}
                </Link>
              </td>
              <td className="px-4 py-3 text-zinc-300">{m.score ?? "—"}</td>
              <td className="px-4 py-3">
                <WLBadge result={m.result} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
