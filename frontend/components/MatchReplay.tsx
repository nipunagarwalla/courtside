"use client";

import { useEffect, useState } from "react";
import { type MatchPoints, type PointsSet } from "@/lib/api";
import ScoreDisplay from "@/components/ScoreDisplay";
import PointLog from "@/components/PointLog";
import ReplayControls from "@/components/ReplayControls";

interface MatchReplayProps {
  matchId: string;
  player1Name: string; // match winner (always P1 in point_events)
  player2Name: string; // match loser
  data: MatchPoints;
}

interface GameRef {
  set: number;
  game: number;
}

function flatGames(data: MatchPoints): GameRef[] {
  return data.sets.flatMap((s) =>
    s.games.map((g) => ({ set: s.set_number, game: g.game_number }))
  );
}

function getNextGame(data: MatchPoints, set: number, game: number): GameRef | null {
  const all = flatGames(data);
  const i = all.findIndex((g) => g.set === set && g.game === game);
  return i >= 0 && i < all.length - 1 ? all[i + 1] : null;
}

function getPrevGame(data: MatchPoints, set: number, game: number): GameRef | null {
  const all = flatGames(data);
  const i = all.findIndex((g) => g.set === set && g.game === game);
  return i > 0 ? all[i - 1] : null;
}

export default function MatchReplay({
  player1Name,
  player2Name,
  data,
}: MatchReplayProps) {
  const firstSet = data.sets[0];
  const [currentSet, setCurrentSet] = useState(firstSet?.set_number ?? 1);
  const [currentGame, setCurrentGame] = useState(
    firstSet?.games[0]?.game_number ?? 1
  );
  const [currentPoint, setCurrentPoint] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);

  const setData: PointsSet | undefined = data.sets.find(
    (s) => s.set_number === currentSet
  );
  const currentGameData = setData?.games.find((g) => g.game_number === currentGame);
  const points = currentGameData?.points ?? [];
  const activePoint = points[currentPoint] ?? null;

  const nextGame = getNextGame(data, currentSet, currentGame);
  const prevGame = getPrevGame(data, currentSet, currentGame);

  const jumpToGame = (set: number, game: number) => {
    setCurrentSet(set);
    setCurrentGame(game);
    setCurrentPoint(0);
    setPlaying(false);
  };

  useEffect(() => {
    if (!playing) return;
    const interval = setInterval(() => {
      if (currentPoint < points.length - 1) {
        setCurrentPoint((p) => p + 1);
      } else if (nextGame) {
        setCurrentSet(nextGame.set);
        setCurrentGame(nextGame.game);
        setCurrentPoint(0);
      } else {
        setPlaying(false); // end of match
      }
    }, 1000 / speed);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, speed, currentPoint, currentSet, currentGame, points.length]);

  const shortName = (n: string) => n.split(" ").at(-1) ?? n;

  return (
    <div className="mt-6 space-y-4 rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">
        Match Replay
      </h2>

      {/* Summary panel — full match scoreboard */}
      <div className="overflow-x-auto">
        <table className="text-sm tabular-nums">
          <thead>
            <tr className="text-xs uppercase text-zinc-500">
              <th className="pr-4 text-left"> </th>
              {data.sets.map((s) => (
                <th key={s.set_number} className="px-3 text-center">
                  S{s.set_number}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[1, 2].map((player) => (
              <tr key={player}>
                <td className="pr-4 font-semibold">
                  {player === 1 ? `${shortName(player1Name)} (W)` : `${shortName(player2Name)} (L)`}
                </td>
                {data.sets.map((s) => (
                  <td key={s.set_number} className="px-1 text-center">
                    <button
                      onClick={() => jumpToGame(s.set_number, s.games[0]?.game_number ?? 1)}
                      className={`w-9 rounded py-0.5 font-semibold transition-colors hover:bg-zinc-700 ${
                        s.set_number === currentSet ? "bg-zinc-700" : "bg-zinc-800"
                      }`}
                    >
                      {player === 1 ? s.p1_games : s.p2_games}
                      {s.set_number === currentSet && player === 1 ? "*" : ""}
                    </button>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 1 — live score */}
      <ScoreDisplay
        point={activePoint}
        player1Name={player1Name}
        player2Name={player2Name}
        server={activePoint?.server ?? null}
      />

      {/* 2 — set tabs + game buttons */}
      <div className="flex flex-wrap gap-2">
        {data.sets.map((s) => (
          <button
            key={s.set_number}
            onClick={() => jumpToGame(s.set_number, s.games[0]?.game_number ?? 1)}
            className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors ${
              s.set_number === currentSet
                ? "bg-blue-600 text-white"
                : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
            }`}
          >
            Set {s.set_number}{" "}
            <span className="tabular-nums">
              {s.p1_games}-{s.p2_games}
            </span>
          </button>
        ))}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {setData?.games.map((g) => (
          <button
            key={g.game_number}
            onClick={() => jumpToGame(currentSet, g.game_number)}
            title={`Game ${g.game_number}`}
            className={`h-8 w-8 rounded text-sm font-semibold text-white transition-transform hover:scale-110 ${
              g.winner === 1 ? "bg-blue-600" : g.winner === 2 ? "bg-red-600" : "bg-zinc-700"
            } ${g.game_number === currentGame ? "ring-2 ring-white" : ""}`}
          >
            {g.game_number}
          </button>
        ))}
      </div>

      {/* 3 — controls */}
      <ReplayControls
        playing={playing}
        speed={speed}
        canPrevGame={prevGame !== null}
        canNextGame={nextGame !== null}
        canPrevPoint={currentPoint > 0}
        canNextPoint={currentPoint < points.length - 1}
        onPrevGame={() => prevGame && jumpToGame(prevGame.set, prevGame.game)}
        onNextGame={() => nextGame && jumpToGame(nextGame.set, nextGame.game)}
        onPrevPoint={() => setCurrentPoint((p) => Math.max(0, p - 1))}
        onNextPoint={() => setCurrentPoint((p) => Math.min(points.length - 1, p + 1))}
        onTogglePlay={() => setPlaying((p) => !p)}
        onSpeed={setSpeed}
      />

      {/* 4 — point log */}
      <PointLog
        points={points}
        currentPoint={currentPoint}
        player1Name={player1Name}
        player2Name={player2Name}
        onSelect={(i) => {
          setCurrentPoint(i);
          setPlaying(false);
        }}
      />
    </div>
  );
}
