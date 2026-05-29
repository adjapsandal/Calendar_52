import { Link } from "react-router-dom";
import type { DayTaskRead, WeekMarkRead, WeekTaskRead } from "@/api";
import { useUpdateDayTask } from "@/hooks/useApi";
import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
  useDraggable,
  DragOverlay,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { useState } from "react";
import { cn } from "@/lib/utils";

const DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
const MONTH_NAMES = [
  "января", "февраля", "марта", "апреля", "мая", "июня",
  "июля", "августа", "сентября", "октября", "ноября", "декабря",
];

function getWeekMonday(year: number, isoWeek: number): Date {
  const jan4 = new Date(year, 0, 4);
  const dayOfWeek = jan4.getDay() || 7;
  const monday1 = new Date(jan4);
  monday1.setDate(jan4.getDate() - (dayOfWeek - 1));
  const result = new Date(monday1);
  result.setDate(monday1.getDate() + (isoWeek - 1) * 7);
  return result;
}

function getDayDate(weekMonday: Date, dayIndex: number): Date {
  const d = new Date(weekMonday);
  d.setDate(weekMonday.getDate() + dayIndex);
  return d;
}

function formatDayDate(date: Date): string {
  return `${date.getDate()} ${MONTH_NAMES[date.getMonth()]}`;
}

function isSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

interface DaysStripProps {
  weekId: string;
  dayTasks: DayTaskRead[];
  year?: number;
  isoWeek: number;
  yearNumber: number;
  marks: WeekMarkRead[];
  weekTasks: WeekTaskRead[];
}

function DraggableTask({ task, markName, markColor }: { task: DayTaskRead; markName?: string; markColor?: string }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: task.id });
  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      className={cn(
        "mt-1.5 w-full rounded-lg border cursor-grab active:cursor-grabbing overflow-hidden hover:shadow-sm hover:border-gray-300 transition-all shrink-0",
        isDragging && "opacity-40",
      )}
    >
      {markName && (
        <div
          className="text-[10px] font-medium px-2 py-0.5 truncate"
          style={{ backgroundColor: (markColor ?? "#94a3b8") + "20", color: markColor ?? "#94a3b8" }}
        >
          {markName}
        </div>
      )}
      <div className="text-xs truncate px-2 py-1 bg-gray-50 text-gray-800">{task.title}</div>
    </div>
  );
}

function DroppableDay({
  dayIndex,
  label,
  dateStr,
  tasks,
  weekId,
  isOver,
  isToday,
  getMarkInfo,
}: {
  dayIndex: number;
  label: string;
  dateStr: string;
  tasks: DayTaskRead[];
  weekId: string;
  isOver: boolean;
  isToday: boolean;
  getMarkInfo: (dt: DayTaskRead) => { name: string; color: string } | undefined;
}) {
  const { setNodeRef } = useDroppable({ id: dayIndex });

  const MAX_VISIBLE = 5;
  const TASK_HEIGHT = 48;
  const scrollMaxHeight = MAX_VISIBLE * TASK_HEIGHT;

  return (
    <Link to={`/week/${weekId}/day/${dayIndex}`} className="block">
      <div
        ref={setNodeRef}
        className={cn(
          "flex flex-col rounded-xl border p-4 transition-all hover:shadow-sm min-h-[130px]",
          isToday
            ? "bg-blue-600 border-blue-600 text-white"
            : "bg-white border-gray-200 hover:border-blue-300",
          isOver && "ring-2 ring-primary/50",
        )}
      >
        <div className={cn(
          "text-xs font-semibold uppercase tracking-wider mb-0.5",
          isToday ? "text-blue-200" : "text-gray-400"
        )}>
          {label}
        </div>
        <div className={cn(
          "text-base font-semibold",
          isToday ? "text-white" : "text-gray-800"
        )}>
          {dateStr}
        </div>
        {tasks.length > 0 && (
          <div className={cn(
            "mt-1.5 text-xs font-medium",
            isToday ? "text-blue-100" : "text-blue-600"
          )}>
            {tasks.length} задач
          </div>
        )}
        <div
          className="flex flex-col gap-0.5 mt-1 scrollbar-thin"
          style={tasks.length > MAX_VISIBLE ? { maxHeight: scrollMaxHeight, overflowY: "auto" as const } : undefined}
        >
          {tasks.map((t) => {
            const mi = getMarkInfo(t);
            return <DraggableTask key={t.id} task={t} markName={mi?.name} markColor={mi?.color} />;
          })}
        </div>
      </div>
    </Link>
  );
}

export default function DaysStrip({ weekId, dayTasks, year, isoWeek, yearNumber, marks, weekTasks }: DaysStripProps) {
  const updateTask = useUpdateDayTask(weekId, year);
  const [activeTask, setActiveTask] = useState<DayTaskRead | null>(null);
  const [overDay, setOverDay] = useState<number | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
  );

  const weekMonday = getWeekMonday(yearNumber, isoWeek);
  const today = new Date();

  const markById = new Map(marks.map((m) => [m.id, m]));
  const weekTaskById = new Map(weekTasks.map((wt) => [wt.id, wt]));

  function getMarkForDayTask(dt: DayTaskRead): { name: string; color: string } | undefined {
    if (!dt.week_task_id) return undefined;
    const wt = weekTaskById.get(dt.week_task_id);
    if (!wt?.mark_id) return undefined;
    const mark = markById.get(wt.mark_id);
    if (!mark) return undefined;
    return { name: mark.title, color: mark.theme_color ?? "#94a3b8" };
  }

  const tasksByDay = new Map<number, DayTaskRead[]>();
  for (const t of dayTasks) {
    const list = tasksByDay.get(t.day_of_week) ?? [];
    list.push(t);
    tasksByDay.set(t.day_of_week, list);
  }

  function handleDragStart(event: DragStartEvent) {
    const task = dayTasks.find((t) => t.id === event.active.id);
    if (task) setActiveTask(task);
  }

  function handleDragOver(event: { over: { id: unknown } | null }) {
    if (event.over) {
      setOverDay(parseInt(String(event.over.id)));
    } else {
      setOverDay(null);
    }
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveTask(null);
    setOverDay(null);
    const { active, over } = event;
    if (!over || !active) return;
    const taskId = String(active.id);
    const targetDay = parseInt(String(over.id));
    if (isNaN(targetDay)) return;
    const task = dayTasks.find((t) => t.id === taskId);
    if (!task || task.day_of_week === targetDay) return;
    updateTask.mutate({ id: task.id, day_of_week: targetDay });
  }

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="grid grid-cols-2 gap-3">
        {[0, 3, 1, 4, 2, 5].map((dayIndex) => {
          const date = getDayDate(weekMonday, dayIndex);
          return (
            <DroppableDay
              key={dayIndex}
              dayIndex={dayIndex}
              label={DAY_NAMES[dayIndex]}
              dateStr={formatDayDate(date)}
              tasks={tasksByDay.get(dayIndex) ?? []}
              weekId={weekId}
              isOver={overDay === dayIndex}
              isToday={isSameDay(date, today)}
              getMarkInfo={getMarkForDayTask}
            />
          );
        })}
      </div>
      {(() => {
        const sunDate = getDayDate(weekMonday, 6);
        return (
          <div className="mt-3">
            <DroppableDay
              dayIndex={6}
              label={DAY_NAMES[6]}
              dateStr={formatDayDate(sunDate)}
              tasks={tasksByDay.get(6) ?? []}
              weekId={weekId}
              isOver={overDay === 6}
              isToday={isSameDay(sunDate, today)}
              getMarkInfo={getMarkForDayTask}
            />
          </div>
        );
      })()}
      <DragOverlay>
        {activeTask && (
          <div className="rounded-lg border bg-card px-3 py-1.5 text-sm shadow-lg">
            {activeTask.title}
          </div>
        )}
      </DragOverlay>
    </DndContext>
  );
}
