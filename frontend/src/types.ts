// Mirrors the chronicler facts schema served at GET /facts.

export interface Slot {
  file: string;
  game: string | null;
  achievements_unlocked: number;
  achievements_total: number;
  dead_god: boolean;
  default: boolean;
}

export interface BestiaryEntry {
  id: number;
  variant: number;
  name: string;
  boss: boolean;
  value: number;
}

export interface BestiaryCategory {
  label: string | null;
  entries: number;
  value_sum: number;
  top: BestiaryEntry[];
}

export interface Characters {
  tracked_total: number;
  unlocked_count: number;
  unlocked: string[];
  locked: string[];
  tainted: null;
}

export interface LockedAchievement {
  id: number;
  name: string;
  unlock: string | null;
}

export interface NextGroup {
  group: string;
  label: string;
  count: number;
  examples: { name: string; unlock: string | null }[];
}

export interface Facts {
  schema: string;
  source: {
    name: string;
    game: string | null;
    size_bytes: number;
    format_verified: boolean;
  };
  completion: {
    achievements_unlocked: number;
    achievements_total: number;
    dead_god: boolean;
    dead_god_progress: number;
    characters?: Characters;
    locked: LockedAchievement[];
  };
  stats: Record<string, number | null>;
  collectibles: { total: number; seen: number };
  bestiary: {
    parsed: boolean;
    total_entries: number;
    category_labels: (string | null)[];
    categories: BestiaryCategory[];
  };
  next: { headline: string; groups: NextGroup[] };
}
