"use client";

import { useEffect, useRef, useState } from "react";
import { searchPlayers, type Player } from "@/lib/api";
import { countryFlag } from "@/lib/flags";

interface PlayerSearchInputProps {
  onSelect: (player: Player) => void;
  placeholder?: string;
}

export default function PlayerSearchInput({
  onSelect,
  placeholder = "Search players…",
}: PlayerSearchInputProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Player[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      setOpen(false);
      return;
    }
    setLoading(true);
    const t = setTimeout(async () => {
      try {
        const players = await searchPlayers(query.trim());
        setResults(players);
        setOpen(true);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div ref={containerRef} className="relative">
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => results.length > 0 && setOpen(true)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-zinc-800 bg-zinc-800 px-4 py-2.5 text-white placeholder-zinc-500 outline-none focus:border-blue-500"
      />
      {loading && (
        <span className="absolute right-3 top-3 text-xs text-zinc-500">…</span>
      )}
      {open && (
        <ul className="absolute z-30 mt-1 w-full overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900 shadow-xl">
          {results.length === 0 && (
            <li className="px-4 py-3 text-sm text-zinc-500">No players found</li>
          )}
          {results.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                onClick={() => {
                  onSelect(p);
                  setQuery("");
                  setOpen(false);
                }}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-zinc-800"
              >
                <span className="inline-flex min-w-10 justify-center rounded bg-zinc-800 px-1.5 py-0.5 text-xs font-semibold text-zinc-300">
                  {p.current_rank != null ? `#${p.current_rank}` : "—"}
                </span>
                <span className="flex-1 text-sm text-white">{p.name}</span>
                <span className="text-sm text-zinc-400">
                  {countryFlag(p.country)} {p.country ?? ""}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
