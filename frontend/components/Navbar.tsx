"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import useSWR from "swr";
import { getLive } from "@/lib/api";

const LINKS = [
  { href: "/rankings", label: "Rankings" },
  { href: "/tournaments", label: "Tournaments" },
  { href: "/players", label: "Players" },
  { href: "/compare", label: "Compare" },
  { href: "/predictions", label: "Predictions" },
  { href: "/live", label: "Live" },
];

export default function Navbar() {
  const pathname = usePathname();
  const { data: liveMatches } = useSWR("navbar-live", getLive, {
    refreshInterval: 60_000,
    shouldRetryOnError: false,
  });
  const anyLive = (liveMatches?.length ?? 0) > 0;
  return (
    <nav className="sticky top-0 z-40 border-b border-zinc-800 bg-zinc-950/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4">
        <Link href="/" className="text-lg font-bold tracking-tight text-white">
          🎾 Courtside
        </Link>
        <div className="flex gap-1 text-sm">
          {LINKS.map(({ href, label }) => {
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                className={`relative rounded-md px-3 py-1.5 transition-colors ${
                  active
                    ? "bg-zinc-800 text-white"
                    : "text-zinc-400 hover:bg-zinc-900 hover:text-white"
                }`}
              >
                {label}
                {label === "Live" && anyLive && (
                  <span className="absolute -right-0.5 -top-0.5 h-2 w-2 animate-pulse rounded-full bg-red-500" />
                )}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
