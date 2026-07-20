import { type PointRow } from "@/lib/api";

interface ScoreDisplayProps {
  point: PointRow | null;
  player1Name: string;
  player2Name: string;
  server: number | null;
}

function gameScoreParts(point: PointRow | null): [string, string] | "deuce" | null {
  const raw = point?.score_before;
  if (!raw) return null;
  const [a, b] = raw.split("-");
  if (a === "40" && b === "40") return "deuce";
  const map = (v: string) => (v === "AD" ? "Ad" : v);
  return [map(a ?? "0"), map(b ?? "0")];
}

export default function ScoreDisplay({
  point,
  player1Name,
  player2Name,
  server,
}: ScoreDisplayProps) {
  const score = gameScoreParts(point);
  const p1Sets = point?.p1_sets ?? 0;
  const p2Sets = point?.p2_sets ?? 0;
  const p1Games = point?.p1_games ?? 0;
  const p2Games = point?.p2_games ?? 0;

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
      <div className="grid grid-cols-3 items-center text-center">
        <div className="text-right text-lg font-semibold">
          {server === 1 && <span className="mr-2">🎾</span>}
          {player1Name}
        </div>
        <div>
          <div className="text-xs uppercase tracking-wide text-zinc-500">
            Sets {p1Sets} — {p2Sets} · Games {p1Games} — {p2Games}
          </div>
          <div className="mt-1 text-4xl font-bold tabular-nums">
            {score === "deuce" ? (
              "Deuce"
            ) : score ? (
              <>
                {score[0]} <span className="text-zinc-600">—</span> {score[1]}
              </>
            ) : (
              <>
                0 <span className="text-zinc-600">—</span> 0
              </>
            )}
          </div>
        </div>
        <div className="text-left text-lg font-semibold">
          {player2Name}
          {server === 2 && <span className="ml-2">🎾</span>}
        </div>
      </div>
    </div>
  );
}
