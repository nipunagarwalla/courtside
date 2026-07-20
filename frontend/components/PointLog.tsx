"use client";

import { useEffect, useRef } from "react";
import { type PointRow } from "@/lib/api";
import PointLogItem from "@/components/PointLogItem";

interface PointLogProps {
  points: PointRow[];
  currentPoint: number;
  player1Name: string;
  player2Name: string;
  onSelect: (index: number) => void;
}

export default function PointLog({
  points,
  currentPoint,
  player1Name,
  player2Name,
  onSelect,
}: PointLogProps) {
  const activeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [currentPoint]);

  const shortName = (n: string) => n.split(" ").at(-1) ?? n;

  return (
    <div className="max-h-80 space-y-1 overflow-y-auto rounded-lg border border-zinc-800 bg-zinc-950 p-2">
      {points.length === 0 && (
        <p className="p-3 text-sm text-zinc-500">No points recorded for this game.</p>
      )}
      {points.map((p, i) => (
        <div key={p.point_number} ref={i === currentPoint ? activeRef : undefined}>
          <PointLogItem
            point={p}
            active={i === currentPoint}
            winnerName={
              p.winner === 1 ? shortName(player1Name) : p.winner === 2 ? shortName(player2Name) : "—"
            }
            onClick={() => onSelect(i)}
          />
        </div>
      ))}
    </div>
  );
}
