export type SessionLog = {
  id: string;
  startedAt: number;
  endedAt: number;
  durationSec: number;
  exerciseTotals: Record<string, number>;
  notes?: string;
};

const STORAGE_KEY = "ai-workout-tracker:sessions";

export function loadSessions(): SessionLog[] {
  if (typeof window === "undefined") {
    return [];
  }
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return [];
  }
  try {
    const data = JSON.parse(raw);
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

export function saveSession(session: SessionLog): void {
  const sessions = loadSessions();
  sessions.unshift(session);
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions.slice(0, 25)));
}

export function clearSessions(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(STORAGE_KEY);
  }
}

export function exportSessionsCsv(sessions: SessionLog[]): string {
  const rows = [
    ["id", "startedAt", "endedAt", "durationSec", "exerciseTotals"].join(",")
  ];
  sessions.forEach((session) => {
    const totals = JSON.stringify(session.exerciseTotals).replace(/"/g, '""');
    rows.push(
      [session.id, session.startedAt, session.endedAt, session.durationSec.toFixed(1), `"${totals}"`].join(",")
    );
  });
  return rows.join("\n");
}

