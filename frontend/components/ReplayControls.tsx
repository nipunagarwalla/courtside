"use client";

interface ReplayControlsProps {
  playing: boolean;
  speed: number;
  canPrevGame: boolean;
  canNextGame: boolean;
  canPrevPoint: boolean;
  canNextPoint: boolean;
  onPrevGame: () => void;
  onNextGame: () => void;
  onPrevPoint: () => void;
  onNextPoint: () => void;
  onTogglePlay: () => void;
  onSpeed: (s: number) => void;
}

const BTN =
  "rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm font-medium " +
  "transition-colors hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-40";

export default function ReplayControls({
  playing,
  speed,
  canPrevGame,
  canNextGame,
  canPrevPoint,
  canNextPoint,
  onPrevGame,
  onNextGame,
  onPrevPoint,
  onNextPoint,
  onTogglePlay,
  onSpeed,
}: ReplayControlsProps) {
  return (
    <div className="flex flex-wrap items-center justify-center gap-2">
      <button className={BTN} disabled={!canPrevGame} onClick={onPrevGame}>
        ◀◀ Prev Game
      </button>
      <button className={BTN} disabled={!canPrevPoint} onClick={onPrevPoint}>
        ◀ Prev Point
      </button>
      <button
        className={`${BTN} min-w-24 border-blue-600 bg-blue-600 hover:bg-blue-500`}
        onClick={onTogglePlay}
      >
        {playing ? "⏸ Pause" : "▶ Play"}
      </button>
      <button className={BTN} disabled={!canNextPoint} onClick={onNextPoint}>
        Next Point ▶
      </button>
      <button className={BTN} disabled={!canNextGame} onClick={onNextGame}>
        Next Game ▶▶
      </button>
      <span className="ml-3 flex items-center gap-1 text-sm text-zinc-400">
        Speed:
        {[1, 2, 4].map((s) => (
          <button
            key={s}
            onClick={() => s !== speed && onSpeed(s)}
            className={`rounded px-2 py-1 text-sm font-semibold transition-colors ${
              s === speed ? "bg-blue-600 text-white" : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
            }`}
          >
            {s}×
          </button>
        ))}
      </span>
    </div>
  );
}
