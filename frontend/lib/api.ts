const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json();
}

export interface Ranking {
  rank: number;
  player_id: string;
  name: string;
  country: string | null;
  points: number | null;
  movement: number | null;
  week_date: string | null;
  ytd_wins: number | null;
}

export interface Player {
  id: string;
  name: string;
  country: string | null;
  tour: string;
  current_rank: number | null;
  current_points: number | null;
}

export interface RecentMatch {
  match_id: string;
  match_date: string | null;
  score: string | null;
  round: string | null;
  surface: string | null;
  tournament: string | null;
  result: "W" | "L";
  opponent_id: string;
  opponent_name: string;
}

export interface PlayerDetail extends Player {
  first_name: string | null;
  last_name: string | null;
  dob: string | null;
  turned_pro: number | null;
  height_cm: number | null;
  hand: string | null;
  coach: string | null;
  weight_kg: number | null;
  career_prize: string | null;
  hi_rank: number | null;
  hi_rank_date: string | null;
  ytd_wins: number | null;
  ytd_losses: number | null;
  ytd_titles: number | null;
  career_wins: number | null;
  career_losses: number | null;
  career_titles: number | null;
  win_rate_overall: number | null;
  win_rate_hard: number | null;
  win_rate_clay: number | null;
  win_rate_grass: number | null;
  recent_matches: RecentMatch[];
  atp_profile_url: string;
}

export interface Tournament {
  id: string;
  name: string;
  year: number;
  surface: string | null;
  tier: string | null;
  country: string | null;
  city: string | null;
  start_date: string | null;
  end_date: string | null;
  draw_size: number | null;
  status: "upcoming" | "in_progress" | "completed" | null;
}

export interface TournamentMatch {
  id: string;
  round: string | null;
  winner_id: string | null;
  winner_name: string | null;
  loser_id: string | null;
  loser_name: string | null;
  score: string | null;
  match_date: string | null;
  minutes: number | null;
}

export interface TournamentDetail extends Tournament {
  tour: string;
  prize_money: number | null;
  matches: TournamentMatch[];
}

export interface Match {
  id: string;
  tournament_name: string | null;
  surface: string | null;
  round: string | null;
  winner_name: string | null;
  loser_name: string | null;
  score: string | null;
  match_date: string | null;
  minutes: number | null;
}

export interface MatchDetail extends Match {
  tournament_id: string | null;
  tournament_tier: string | null;
  tour: string;
  year: number | null;
  winner_id: string | null;
  loser_id: string | null;
  winner_sets: number | null;
  loser_sets: number | null;
  w_aces: number | null;
  w_dfs: number | null;
  w_svpt: number | null;
  w_1stin: number | null;
  w_1stwon: number | null;
  w_2ndwon: number | null;
  w_bpfaced: number | null;
  w_bpsaved: number | null;
  l_aces: number | null;
  l_dfs: number | null;
  l_svpt: number | null;
  l_1stin: number | null;
  l_1stwon: number | null;
  l_2ndwon: number | null;
  l_bpfaced: number | null;
  l_bpsaved: number | null;
  winner_ranking_points: number | null;
  loser_ranking_points: number | null;
}

export interface MatchPoints {
  match_id: string;
  has_data: boolean;
  sets: { set_number: number; points: Record<string, unknown>[] }[];
}

export interface H2HBucket {
  total: number;
  p1_wins: number;
  p2_wins: number;
}

export interface ComparePlayer {
  id: string;
  name: string;
  country: string | null;
  current_rank: number | null;
  current_points: number | null;
}

export interface CompareCareer {
  titles: number | null;
  wins: number | null;
  losses: number | null;
  slam_titles: number;
  masters_titles: number;
}

export interface CompareServe {
  avg_aces_per_match: number | null;
  avg_dfs_per_match: number | null;
  first_serve_pct: number | null;
  first_serve_win_pct: number | null;
  bp_save_pct: number | null;
}

export interface SurfaceRates {
  overall: number | null;
  hard: number | null;
  clay: number | null;
  grass: number | null;
}

export interface H2HMatch {
  match_id: string;
  tournament_name: string | null;
  surface: string | null;
  tier: string | null;
  round: string | null;
  match_date: string | null;
  winner_id: string;
  score: string | null;
  p1_won: boolean;
}

export interface CompareResult {
  player1: ComparePlayer;
  player2: ComparePlayer;
  h2h: {
    total_matches: number;
    p1_wins: number;
    p2_wins: number;
    p1_win_pct: number | null;
  };
  h2h_by_surface: Record<"hard" | "clay" | "grass", H2HBucket>;
  h2h_by_tier: Record<string, H2HBucket>;
  h2h_by_round: Record<string, H2HBucket>;
  recent_form: {
    p1_last10: ("W" | "L")[];
    p2_last10: ("W" | "L")[];
    p1_last10_pct: number | null;
    p2_last10_pct: number | null;
  };
  surface_win_rates: { p1: SurfaceRates; p2: SurfaceRates };
  career_stats: { p1: CompareCareer; p2: CompareCareer };
  serve_stats: { p1: CompareServe; p2: CompareServe };
  h2h_matches: H2HMatch[];
}

export const getRankings = (limit = 100) =>
  get<Ranking[]>(`/api/rankings?limit=${limit}`);

export const searchPlayers = (q: string) =>
  get<Player[]>(`/api/players?search=${encodeURIComponent(q)}&limit=8`);

export const getTopPlayers = (limit = 20) =>
  get<Player[]>(`/api/players?limit=${limit}`);

export const getPlayer = (id: string) => get<PlayerDetail>(`/api/players/${id}`);

export const getTournaments = (params = "") =>
  get<Tournament[]>(`/api/tournaments${params ? `?${params}` : ""}`);

export const getTournament = (id: string) =>
  get<TournamentDetail>(`/api/tournaments/${id}`);

export const getMatches = (params: string) => get<Match[]>(`/api/matches?${params}`);

export const getMatch = (id: string) => get<MatchDetail>(`/api/matches/${id}`);

export const getMatchPoints = (id: string) =>
  get<MatchPoints>(`/api/matches/${id}/points`);

export const getCompare = (p1: string, p2: string) =>
  get<CompareResult>(`/api/compare?p1=${encodeURIComponent(p1)}&p2=${encodeURIComponent(p2)}`);
