import { useState, useEffect, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { useYear, useSettings, useMoveMark, useThemes } from "@/hooks/useApi";
import { useOnboardingStore } from "@/store/onboarding";
import QuarterBlock from "./QuarterBlock";
import OnboardingOverlay from "@/features/onboarding/OnboardingOverlay";
import NavBar from "@/components/NavBar";
import { Spinner } from "@/components/ui/spinner";
import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
  type DragStartEvent,
  type DragEndEvent,
} from "@dnd-kit/core";

function getCurrentDisplayPos(): number | undefined {
  const now = new Date();
  const jan1 = new Date(now.getFullYear(), 0, 1);
  const days = Math.floor((now.getTime() - jan1.getTime()) / 86400000);
  const isoWeek = Math.ceil((days + jan1.getDay() + 1) / 7);
  return isoWeek > 52 ? 52 : isoWeek;
}

export default function YearGrid() {
  const { year: yearParam } = useParams<{ year: string }>();
  const yearNum = parseInt(yearParam ?? "2026");
  const { data, isLoading, error } = useYear(yearNum);
  const { data: settings } = useSettings();
  const currentPos = getCurrentDisplayPos();
  const needsOnboarding = useOnboardingStore((s) => s.needsOnboarding);
  const onboardingDone = useOnboardingStore((s) => s.done);

  const { data: themes } = useThemes();
  const moveMark = useMoveMark();

  const [activeItem, setActiveItem] = useState<{ id: string; title: string; color: string | null } | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
  );

  const allMarks: { id: string; title: string; color: string | null; weekId: string }[] = [];
  if (data) {
    for (const q of data.quarters) {
      for (const w of q.weeks) {
        for (const m of w.marks_preview) {
          allMarks.push({ id: m.id, title: m.title, color: m.color, weekId: w.id });
        }
      }
    }
  }

  const currentQuarter = currentPos ? Math.ceil(currentPos / 13) : undefined;
  const scrolledRef = useRef(false);
  useEffect(() => {
    if (data && currentQuarter && !scrolledRef.current) {
      scrolledRef.current = true;
      setTimeout(() => {
        document.querySelector(`[data-quarter="${currentQuarter}"]`)
          ?.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 100);
    }
  }, [data, currentQuarter]);

  function handleDragStart(event: DragStartEvent) {
    const idStr = String(event.active.id);
    if (idStr.startsWith("mark-")) {
      const markId = idStr.slice(5);
      const mark = allMarks.find((m) => m.id === markId);
      if (mark) setActiveItem({ id: mark.id, title: mark.title, color: mark.color });
    }
  }

  function handleDragEnd(event: DragEndEvent) {
    const item = activeItem;
    setActiveItem(null);
    const { active, over } = event;
    if (!over || !active || !item) return;

    const targetWeekId = String(over.id);
    const sourceMark = allMarks.find((m) => m.id === item.id);
    if (!sourceMark || sourceMark.weekId === targetWeekId) return;
    moveMark.mutate({ markId: item.id, targetWeekId });
  }

  if (isLoading) return <Spinner />;
  if (error) return <div className="p-8 text-destructive">Ошибка загрузки</div>;
  if (!data) return null;

  const showOnboarding = needsOnboarding && !onboardingDone;

  const today = new Date();
  const todayDayOfWeek = today.getDay() === 0 ? 6 : today.getDay() - 1;
  const todayLabel = today.toLocaleDateString("ru-RU", { weekday: "short", day: "numeric", month: "long" });

  let currentWeekId: string | null = null;
  if (data && currentPos) {
    for (const q of data.quarters) {
      const w = q.weeks.find((w) => w.display_position === currentPos);
      if (w) { currentWeekId = w.id; break; }
    }
  }

  return (
    <>
      {showOnboarding && <OnboardingOverlay />}
      <DndContext
        sensors={sensors}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="min-h-full bg-[#F0F2F7]">
          <NavBar>
            <span className="text-lg font-bold text-gray-900">{data.year_number}</span>

            {themes && themes.length > 0 && (
              <div className="flex items-center gap-1.5 flex-wrap">
                {themes.map((t) => (
                  <div
                    key={t.id}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
                    style={{ backgroundColor: t.color + "20", color: t.color }}
                  >
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: t.color }} />
                    {t.name}
                  </div>
                ))}
              </div>
            )}

            <div className="flex-1" />

            {currentWeekId && (
              <Link
                to={`/week/${currentWeekId}/day/${todayDayOfWeek}`}
                className="flex flex-col items-center justify-center px-5 py-1.5 rounded-xl bg-rose-500 text-white hover:bg-rose-600 transition-colors shadow-sm min-w-[130px]"
              >
                <span className="text-[10px] uppercase tracking-wider opacity-80">Сегодня</span>
                <span className="text-sm font-semibold">{todayLabel}</span>
              </Link>
            )}
          </NavBar>

          <div className="px-6 py-6">
            <div className="flex flex-col gap-6">
              {data.quarters.map((q) => (
                <div key={q.quarter} data-quarter={q.quarter}>
                  <QuarterBlock
                    data={q}
                    year={data.year_number}
                    weekBudget={settings?.week_budget ?? 10}
                    currentDisplayPos={currentPos}
                    draggableMarks={allMarks}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>

        <DragOverlay>
          {activeItem && (
            <div
              className="rounded-lg border bg-card px-3 py-1.5 text-sm shadow-lg"
              style={{ color: activeItem.color ?? undefined }}
            >
              {activeItem.title}
            </div>
          )}
        </DragOverlay>
      </DndContext>
    </>
  );
}
