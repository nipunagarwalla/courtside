import Link from "next/link";

const CARDS = [
  {
    href: "/rankings",
    title: "Rankings",
    description: "Live ATP rankings with weekly movement",
    icon: "🏆",
  },
  {
    href: "/players",
    title: "Players",
    description: "Profiles, career stats and recent results",
    icon: "👤",
  },
  {
    href: "/compare",
    title: "Compare",
    description: "Head-to-head records and stat battles",
    icon: "⚔️",
  },
];

export default function Home() {
  return (
    <main className="mx-auto flex max-w-4xl flex-col items-center px-4 py-24 text-center">
      <h1 className="text-5xl font-bold tracking-tight">🎾 Courtside</h1>
      <p className="mt-4 text-lg text-zinc-400">
        Tennis analytics — 58 years of ATP data, live rankings and head-to-heads.
      </p>
      <div className="mt-12 grid w-full gap-4 sm:grid-cols-3">
        {CARDS.map((c) => (
          <Link
            key={c.href}
            href={c.href}
            className="rounded-xl border border-zinc-800 bg-zinc-900 p-6 text-left transition-colors hover:border-zinc-600"
          >
            <div className="text-3xl">{c.icon}</div>
            <div className="mt-3 text-lg font-semibold">{c.title}</div>
            <div className="mt-1 text-sm text-zinc-400">{c.description}</div>
          </Link>
        ))}
      </div>
    </main>
  );
}
