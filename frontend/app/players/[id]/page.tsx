import { notFound } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Player = {
  id: string;
  name: string;
  country: string | null;
  hand: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  coach: string | null;
  career_prize: string | null;
  hi_rank: number | null;
  hi_rank_date: string | null;
  ytd_wins: number | null;
  ytd_losses: number | null;
  ytd_titles: number | null;
  career_wins: number | null;
  career_losses: number | null;
  career_titles: number | null;
  current_rank: number | null;
  rank_date: string | null;
};

async function getPlayer(id: string): Promise<Player | null> {
  const res = await fetch(`${API_URL}/api/players/${id}`, { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-black/10 dark:border-white/15 p-4">
      <div className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
        {label}
      </div>
      <div className="mt-1 text-lg font-semibold">{value ?? "—"}</div>
    </div>
  );
}

export default async function PlayerPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const player = await getPlayer(id);
  if (!player) notFound();

  const record = (w: number | null, l: number | null) =>
    w == null && l == null ? null : `${w ?? 0}–${l ?? 0}`;

  return (
    <main className="mx-auto max-w-3xl p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold">{player.name}</h1>
        <p className="mt-1 text-gray-500 dark:text-gray-400">
          {[player.country, player.hand ? `${player.hand}-handed` : null]
            .filter(Boolean)
            .join(" · ")}
        </p>
        {player.current_rank != null && (
          <p className="mt-2 inline-block rounded-full bg-emerald-600 px-3 py-1 text-sm font-medium text-white">
            ATP Rank #{player.current_rank}
          </p>
        )}
      </header>

      <section className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Stat label="Coach" value={player.coach} />
        <Stat label="Career Prize Money" value={player.career_prize} />
        <Stat
          label="Career High Rank"
          value={
            player.hi_rank != null
              ? `#${player.hi_rank}${player.hi_rank_date ? ` (${player.hi_rank_date})` : ""}`
              : null
          }
        />
        <Stat
          label="YTD Record"
          value={record(player.ytd_wins, player.ytd_losses)}
        />
        <Stat label="YTD Titles" value={player.ytd_titles} />
        <Stat
          label="Career Record"
          value={record(player.career_wins, player.career_losses)}
        />
        <Stat label="Career Titles" value={player.career_titles} />
        <Stat
          label="Height / Weight"
          value={
            player.height_cm || player.weight_kg
              ? `${player.height_cm ?? "?"} cm / ${player.weight_kg ?? "?"} kg`
              : null
          }
        />
      </section>
    </main>
  );
}
