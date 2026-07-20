"use client";

import { useState } from "react";
import useSWR from "swr";
import { getPredict } from "@/lib/api";
import Disclaimer from "@/components/Disclaimer";

const SURFACES = ["Hard", "Clay", "Grass"];
const TIERS = ["Grand Slam", "Masters 1000", "ATP 500", "ATP 250"];
const ROUNDS = ["F", "SF", "QF", "R16"];

const CONFIDENCE_CLASS: Record<string, string> = {
  High: "bg-green-600 text-white",
  Moderate: "bg-yellow-500 text-black",
  "Toss-up": "bg-zinc-600 text-white",
};

function SelectorRow({
  options,
  value,
  onChange,
}: {
  options: string[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex overflow-hidden rounded-lg border border-zinc-800">
      {options.map((o) => (
        <button
          key={o}
          onClick={() => onChange(o)}
          className={`px-3 py-1.5 text-sm transition-colors ${
            o === value ? "bg-blue-600 text-white" : "bg-zinc-900 text-zinc-400 hover:text-white"
          }`}
        >
          {o}
        </button>
      ))}
    </div>
  );
}

function FactorDots({ importance, max }: { importance: number; max: number }) {
  const filled = max > 0 ? Math.round((importance / max) * 5) : 0;
  return (
    <span className="tracking-widest text-blue-400">
      {"●".repeat(Math.max(filled, 1))}
      <span className="text-zinc-700">{"○".repeat(5 - Math.max(filled, 1))}</span>
    </span>
  );
}

export default function PredictionSection({
  p1,
  p2,
  p1Name,
  p2Name,
  defaultSurface = "Hard",
}: {
  p1: string;
  p2: string;
  p1Name: string;
  p2Name: string;
  defaultSurface?: string;
}) {
  const [surface, setSurface] = useState(defaultSurface);
  const [tier, setTier] = useState("Masters 1000");
  const [round, setRound] = useState("SF");

  const { data, error, isLoading } = useSWR(
    `predict-${p1}-${p2}-${surface}-${tier}-${round}`,
    () => getPredict(p1, p2, surface, tier, round),
    { shouldRetryOnError: false }
  );

  const notTrained = error?.message?.startsWith("503");
  const shortName = (n: string) => n.split(" ").at(-1) ?? n;
  const prob = data?.prediction.p1_win_probability ?? 0.5;
  const p1Pct = Math.round(prob * 100);
  const maxImportance = Math.max(
    ...(data?.prediction.key_factors.map((f) => f.importance) ?? [0]),
    0.0001
  );

  return (
    <section className="mt-8 rounded-xl border border-zinc-800 bg-zinc-900 p-6">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-zinc-400">
        Match Prediction
      </h2>

      <div className="flex flex-wrap gap-3">
        <SelectorRow options={SURFACES} value={surface} onChange={setSurface} />
        <SelectorRow options={TIERS} value={tier} onChange={setTier} />
        <SelectorRow options={ROUNDS} value={round} onChange={setRound} />
      </div>

      {notTrained && (
        <p className="mt-6 rounded-lg bg-zinc-800 p-4 text-center text-sm text-zinc-400">
          Train the model first: <code className="text-zinc-300">python -m ml.train</code>
        </p>
      )}
      {error && !notTrained && (
        <p className="mt-6 text-center text-sm text-red-400">Prediction failed.</p>
      )}
      {isLoading && (
        <div className="mt-6 h-20 animate-pulse rounded-lg bg-zinc-800" />
      )}

      {data && (
        <div className="mt-6">
          <div className="flex items-center gap-3">
            <span className="w-24 truncate text-right font-semibold">
              {shortName(p1Name)}
            </span>
            <span className="w-12 text-right text-lg font-bold tabular-nums">
              {p1Pct}%
            </span>
            <div className="flex h-4 flex-1 overflow-hidden rounded-full bg-zinc-800">
              <div className="bg-blue-500" style={{ width: `${p1Pct}%` }} />
              <div className="bg-orange-500" style={{ width: `${100 - p1Pct}%` }} />
            </div>
            <span className="w-12 text-lg font-bold tabular-nums">{100 - p1Pct}%</span>
            <span className="w-24 truncate font-semibold">{shortName(p2Name)}</span>
          </div>

          <div className="mt-3 text-center">
            <span
              className={`rounded px-2 py-0.5 text-xs font-bold ${CONFIDENCE_CLASS[data.prediction.confidence]}`}
            >
              {data.prediction.confidence}
              {data.prediction.confidence !== "Toss-up" && " confidence"}
            </span>
          </div>

          {data.prediction.key_factors.length > 0 && (
            <div className="mx-auto mt-4 max-w-xs space-y-1">
              {data.prediction.key_factors.map((f) => (
                <div key={f.factor} className="flex items-center justify-between gap-4 text-sm">
                  <span className="text-zinc-400">{f.factor}</span>
                  <FactorDots importance={f.importance} max={maxImportance} />
                </div>
              ))}
            </div>
          )}
          <Disclaimer />
        </div>
      )}
    </section>
  );
}
