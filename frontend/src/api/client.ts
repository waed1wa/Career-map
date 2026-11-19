// Тонкий клиент к нашему API. Все запросы идут на /api — дальше их проксирует Vite или nginx.

export type Health = {
  status: "ok" | "degraded";
  database: boolean;
  redis: boolean;
  environment: string;
};

export type StepStatus = "done" | "current" | "todo";

export type MapStep = {
  order: number;
  skill: string;
  title: string;
  status: StepStatus;
  why: string;
};

export type CareerMap = {
  profession_id: string;
  steps_left: number;
  steps: MapStep[];
};

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`);
  if (!response.ok) throw new Error(`${path}: ${response.status}`);
  return (await response.json()) as T;
}

export const getHealth = () => get<Health>("/health");
export const getDemoMap = () => get<CareerMap>("/career-map/demo");
