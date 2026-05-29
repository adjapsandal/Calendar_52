import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { yearApi, weekApi, noteApi, markApi, weekTaskApi, dayTaskApi, themeApi, settingsApi, pileApi, reviewApi, type YearData, type WeekDetail, type QuarterNote, type WeekMarkRead, type WeekTaskRead, type DayTaskRead, type ThemeRead, type SettingsRead, type PileItemRead, type DistributeResponse, type ReviewStartResponse, type ReviewReflectResponse } from "../api";

export function useYear(year: number) {
  return useQuery<YearData>({
    queryKey: ["year", year],
    queryFn: async () => (await yearApi.getYear(year)).data,
  });
}

export function useWeek(weekId: string | undefined) {
  return useQuery<WeekDetail>({
    queryKey: ["week", weekId],
    queryFn: async () => (await weekApi.getWeek(weekId!)).data,
    enabled: !!weekId,
  });
}

export function useQuarterNote(year: number, quarter: number) {
  return useQuery<QuarterNote>({
    queryKey: ["note", year, quarter],
    queryFn: async () => (await noteApi.getNote(year, quarter)).data,
  });
}

export function usePutQuarterNote(year: number, quarter: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (content: string) => noteApi.putNote(year, quarter, content),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["note", year, quarter] });
      qc.invalidateQueries({ queryKey: ["year", year] });
    },
  });
}

export function useCreateMark(weekId: string, year?: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { title: string; theme_id?: string; description?: string }) =>
      markApi.create(weekId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["week", weekId] });
      if (year) qc.invalidateQueries({ queryKey: ["year", year] });
    },
  });
}

export function useUpdateMark(weekId: string, year?: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<WeekMarkRead>) =>
      markApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["week", weekId] });
      if (year) qc.invalidateQueries({ queryKey: ["year", year] });
    },
  });
}

export function useDeleteMark(weekId: string, year?: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, cascade }: { id: string; cascade?: string }) =>
      markApi.delete(id, cascade),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["week", weekId] });
      if (year) qc.invalidateQueries({ queryKey: ["year", year] });
    },
  });
}

export function useMoveMark() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ markId, targetWeekId }: { markId: string; targetWeekId: string }) =>
      markApi.move(markId, targetWeekId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["year"] });
    },
  });
}

export function useMoveWeekTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, targetWeekId }: { taskId: string; targetWeekId: string }) =>
      weekTaskApi.move(taskId, targetWeekId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["year"] });
    },
  });
}

export function useCreateWeekTask(weekId: string, year?: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { title: string; mark_id?: string; theme_id?: string }) =>
      weekTaskApi.create(weekId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["week", weekId] });
      if (year) qc.invalidateQueries({ queryKey: ["year", year] });
    },
  });
}

export function useUpdateWeekTask(weekId: string, year?: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<WeekTaskRead>) =>
      weekTaskApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["week", weekId] });
      if (year) qc.invalidateQueries({ queryKey: ["year", year] });
    },
  });
}

export function useDeleteWeekTask(weekId: string, year?: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => weekTaskApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["week", weekId] });
      if (year) qc.invalidateQueries({ queryKey: ["year", year] });
    },
  });
}

export function useCreateDayTask(weekId: string, year?: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ day, ...data }: { day: number; title: string; week_task_id?: string }) =>
      dayTaskApi.create(weekId, day, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["week", weekId] });
      if (year) qc.invalidateQueries({ queryKey: ["year", year] });
    },
  });
}

export function useUpdateDayTask(weekId: string, year?: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<DayTaskRead>) =>
      dayTaskApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["week", weekId] });
      if (year) qc.invalidateQueries({ queryKey: ["year", year] });
    },
  });
}

export function useDeleteDayTask(weekId: string, year?: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => dayTaskApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["week", weekId] });
      if (year) qc.invalidateQueries({ queryKey: ["year", year] });
    },
  });
}

export function useThemes() {
  return useQuery<ThemeRead[]>({
    queryKey: ["themes"],
    queryFn: async () => (await themeApi.list()).data,
  });
}

export function useSettings() {
  return useQuery<SettingsRead>({
    queryKey: ["settings"],
    queryFn: async () => (await settingsApi.get()).data,
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof settingsApi.update>[0]) =>
      settingsApi.update(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["settings"] });
    },
  });
}

export function usePileItems() {
  return useQuery<PileItemRead[]>({
    queryKey: ["pile"],
    queryFn: async () => (await pileApi.list()).data,
  });
}

export function useCreatePileItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (content: string) => pileApi.create(content),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pile"] });
    },
  });
}

export function useDeletePileItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => pileApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pile"] });
    },
  });
}

export function useUpdatePileItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, content }: { id: string; content: string }) => pileApi.update(id, content),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pile"] });
    },
  });
}

export function useDistribute() {
  const qc = useQueryClient();
  return useMutation<DistributeResponse, Error, string[] | undefined>({
    mutationFn: async (ids) => {
      const res = await pileApi.distribute(ids);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pile"] });
    },
  });
}

export function useApplyDistribution() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (items: Parameters<typeof pileApi.apply>[0]) => pileApi.apply(items),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pile"] });
    },
  });
}

export function useReviewStart() {
  return useMutation<ReviewStartResponse, Error, string>({
    mutationFn: async (weekId) => (await reviewApi.start(weekId)).data,
  });
}

export function useReviewReflect() {
  return useMutation<ReviewReflectResponse, Error, { weekId: string; data: Parameters<typeof reviewApi.reflect>[1] }>({
    mutationFn: async ({ weekId, data }) => (await reviewApi.reflect(weekId, data)).data,
  });
}

export function useReviewComplete() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (weekId: string) => reviewApi.complete(weekId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["year"] });
    },
  });
}
