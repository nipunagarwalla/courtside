"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { API_URL, type PointRow } from "@/lib/api";

export default function LiveMatchPage({
  params,
}: {
  params: Promise<{ match_id: string }>;
}) {
  const { match_id } = use(params);
  const [points, setPoints] = useState<PointRow[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const es = new EventSource(`${API_URL}/api/matches/${match_id}/live-stream`);
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.onmessage = (e) => {
      const point = JSON.parse(e.data) as PointRow;
      setPoints((prev) => [point, ...prev]); // newest at top
    };
    return () => es.close();
  }, [match_id]);

  const matchOver = points[0]?.is_match_point && points[0]?.is_game_winner;

  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Live Feed</h1>
        <span
          className={`rounded px-2 py-1 text-xs font-bold ${
            connected ? "animate-pulse bg-red-600" : "bg-zinc-700"
          }`}
        >
          {connected ? "LIVE" : "CONNECTING…"}
        </span>
      </div>
      <p className="mt-1 text-sm text-zinc-500">{match_id}</p>

      {matchOver && (
        <Link
          href={`/matches/${match_id}`}
          className="mt-6 block rounded-xl bg-green-700 p-4 text-center font-semibold hover:bg-green-600"
        >
          Match complete — view full replay →
        </Link>
      )}

      <div className="mt-6 space-y-2">
        {points.length === 0 && (
          <p className="rounded-xl border border-zinc-800 bg-zinc-900 p-8 text-center text-zinc-400">
            Waiting for points… new points appear here as they are played.
          </p>
        )}
        {points.map((p, i) => (
          <div
            key={`${p.point_number}-${i}`}
            className="rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-3"
          >
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <span className="font-semibold tabular-nums">
                {p.score_before} → {p.score_after}
              </span>
              <span className="text-zinc-400">{p.point_end_type ?? ""}</span>
              {p.serve_speed_kmh && (
                <span className="text-zinc-500">{p.serve_speed_kmh} km/h</span>
              )}
              <span className="ml-auto flex gap-1">
                {p.is_break_point && (
                  <span className="rounded bg-orange-600 px-1.5 py-0.5 text-xs font-bold">BP</span>
                )}
                {p.is_set_point && (
                  <span className="rounded bg-blue-600 px-1.5 py-0.5 text-xs font-bold">SP</span>
                )}
                {p.is_match_point && (
                  <span className="rounded bg-red-600 px-1.5 py-0.5 text-xs font-bold">MP</span>
                )}
              </span>
            </div>
            {p.sentence && (
              <p className="mt-1 text-xs text-zinc-500">{p.sentence}</p>
            )}
          </div>
        ))}
      </div>
    </main>
  );
}
