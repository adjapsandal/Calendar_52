import api from "./client";

export interface MarkPreview {
  id: string;
  title: string;
  color: string | null;
}

export interface TaskPreview {
  id: string;
  title: string;
  status: string;
  mark_id: string | null;
  theme_color: string | null;
}

export interface WeekBrief {
  id: string;
  iso_week: number;
  display_position: number;
  quarter: number;
  is_rest_week: boolean;
  cached_load: number;
  marks_preview: MarkPreview[];
  tasks_preview: TaskPreview[];
}

export interface QuarterNote {
  id: string | null;
  quarter: number;
  content: string;
}

export interface QuarterBlock {
  quarter: number;
  weeks: WeekBrief[];
  note: QuarterNote | null;
}

export interface YearData {
  id: string;
  year_number: number;
  quarters: QuarterBlock[];
}

export interface ThemeRead {
  id: string;
  name: string;
  color: string;
}

export interface SettingsRead {
  user_id: string;
  week_budget: number;
  rest_mode: string;
  hard_protection: boolean;
}

export interface DistributionSuggestion {
  pile_item_id: string;
  target_week_id: string;
  as_mark: boolean;
  title: string;
  theme_id: string | null;
  reasoning: string;
  day_of_week: number;
  item_type?: "week_task" | "day_task" | "mark";
}

export interface DistributeResponse {
  suggestions: DistributionSuggestion[];
}

export interface ReviewTaskBrief {
  id: string;
  title: string;
  status: string;
  mark_id: string | null;
}

export interface ReviewStartResponse {
  week_id: string;
  display_position: number;
  marks: { id: string; title: string }[];
  tasks: ReviewTaskBrief[];
  existing_review: {
    id: string;
    achievements: string;
    lessons: string;
    corrections: string;
  } | null;
}

export interface ReviewReflectResponse {
  achievements: string;
  lessons: string;
  corrections: string;
  tails: { task_id: string; suggested_action: "carry_over" | "drop" }[];
}

export interface PileItemRead {
  id: string;
  content: string;
  distributed: boolean;
  created_at: string;
}

export interface WeekMarkRead {
  id: string;
  theme_id: string | null;
  theme_color: string | null;
  title: string;
  description: string | null;
  position: number;
}

export interface WeekTaskRead {
  id: string;
  mark_id: string | null;
  theme_id: string | null;
  title: string;
  status: string;
  position: number;
}

export interface DayTaskRead {
  id: string;
  week_task_id: string | null;
  day_of_week: number;
  title: string;
  status: string;
  position: number;
}

export interface WeekDetail {
  id: string;
  iso_week: number;
  display_position: number;
  quarter: number;
  is_rest_week: boolean;
  cached_load: number;
  year_number: number;
  marks: WeekMarkRead[];
  week_tasks: WeekTaskRead[];
  day_tasks: DayTaskRead[];
}

export const yearApi = {
  getYear: (year: number) => api.get<YearData>(`/years/${year}`),
};

export const weekApi = {
  getWeek: (weekId: string) => api.get<WeekDetail>(`/weeks/${weekId}`),
};

export const noteApi = {
  getNote: (year: number, quarter: number) =>
    api.get<QuarterNote>(`/years/${year}/quarters/${quarter}/note`),
  putNote: (year: number, quarter: number, content: string) =>
    api.put<QuarterNote>(`/years/${year}/quarters/${quarter}/note`, { content }),
};

export const markApi = {
  create: (weekId: string, data: { title: string; theme_id?: string; description?: string }) =>
    api.post<WeekMarkRead>(`/weeks/${weekId}/marks`, data),
  update: (markId: string, data: Partial<{ title: string; theme_id: string | null; description: string | null; position: number }>) =>
    api.patch<WeekMarkRead>(`/marks/${markId}`, data),
  delete: (markId: string, cascade: string = "detach") =>
    api.delete(`/marks/${markId}`, { params: { cascade } }),
  move: (markId: string, targetWeekId: string) =>
    api.patch<WeekMarkRead>(`/marks/${markId}/move`, { target_week_id: targetWeekId }),
};

export const weekTaskApi = {
  create: (weekId: string, data: { title: string; mark_id?: string; theme_id?: string }) =>
    api.post<WeekTaskRead>(`/weeks/${weekId}/tasks`, data),
  update: (taskId: string, data: Partial<{ title: string; mark_id: string | null; theme_id: string | null; status: string; position: number }>) =>
    api.patch<WeekTaskRead>(`/week-tasks/${taskId}`, data),
  delete: (taskId: string) =>
    api.delete(`/week-tasks/${taskId}`),
  move: (taskId: string, targetWeekId: string) =>
    api.patch<WeekTaskRead>(`/week-tasks/${taskId}/move`, { target_week_id: targetWeekId }),
};

export const dayTaskApi = {
  create: (weekId: string, day: number, data: { title: string; week_task_id?: string }) =>
    api.post<DayTaskRead>(`/weeks/${weekId}/days/${day}/tasks`, data),
  update: (taskId: string, data: Partial<{ title: string; week_task_id: string | null; status: string; day_of_week: number; position: number }>) =>
    api.patch<DayTaskRead>(`/day-tasks/${taskId}`, data),
  delete: (taskId: string) =>
    api.delete(`/day-tasks/${taskId}`),
  move: (taskId: string, targetWeekId: string) =>
    api.patch<DayTaskRead>(`/day-tasks/${taskId}/move`, { target_week_id: targetWeekId }),
};

export const themeApi = {
  list: () => api.get<ThemeRead[]>("/themes"),
  create: (data: { name: string; color: string }) =>
    api.post<ThemeRead>("/themes", data),
  update: (themeId: string, data: Partial<{ name: string; color: string }>) =>
    api.patch<ThemeRead>(`/themes/${themeId}`, data),
  delete: (themeId: string) =>
    api.delete(`/themes/${themeId}`),
};

export const reviewApi = {
  start: (weekId: string) => api.post<ReviewStartResponse>(`/weeks/${weekId}/review/start`),
  reflect: (weekId: string, data: { task_statuses: { id: string; status: string }[]; raw_input?: string }) =>
    api.post<ReviewReflectResponse>(`/weeks/${weekId}/review/reflect`, data),
  complete: (weekId: string) => api.post(`/weeks/${weekId}/review/complete`),
};

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  reply: string;
  suggestions?: DistributionSuggestion[];
}

export const chatApi = {
  send: (messages: ChatMessage[], week_id?: string) =>
    api.post<ChatResponse>("/chat", { messages, week_id }),
};

export const pileApi = {
  list: () => api.get<PileItemRead[]>("/pile/items"),
  create: (content: string) => api.post<PileItemRead>("/pile/items", { content }),
  update: (itemId: string, content: string) => api.patch<PileItemRead>(`/pile/items/${itemId}`, { content }),
  delete: (itemId: string) => api.delete(`/pile/items/${itemId}`),
  distribute: (pile_item_ids?: string[]) =>
    api.post<DistributeResponse>("/pile/distribute", pile_item_ids ? { pile_item_ids } : {}),
  apply: (items: { pile_item_id: string; target_week_id: string; as_mark: boolean; title: string; theme_id?: string | null; day_of_week?: number }[]) =>
    api.post("/pile/distribute/apply", { items }),
};

export const settingsApi = {
  get: () => api.get<SettingsRead>("/settings"),
  update: (data: Partial<{ week_budget: number; rest_mode: string; hard_protection: boolean }>) =>
    api.patch<SettingsRead>("/settings", data),
};

export const authApi = {
  register: (email: string, password: string) =>
    api.post("/auth/register", { email, password }),
  login: (email: string, password: string) => {
    const params = new URLSearchParams();
    params.append("username", email);
    params.append("password", password);
    return api.post("/auth/login", params, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  },
  logout: () => api.post("/auth/logout"),
  getMe: () => api.get("/users/me"),
  patchMe: (data: { timezone?: string; onboarded?: boolean }) =>
    api.patch("/users/me", data),
};
