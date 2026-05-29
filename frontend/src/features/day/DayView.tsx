import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useWeek, useCreateDayTask, useUpdateDayTask, useDeleteDayTask } from "@/hooks/useApi";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import NavBar from "@/components/NavBar";
import type { DayTaskRead, WeekTaskRead } from "@/api";
import { cn } from "@/lib/utils";

const DAY_NAMES = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"];
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

function InlineCreator({ onSubmit, onCancel, placeholder }: { onSubmit: (title: string) => void; onCancel: () => void; placeholder: string }) {
  const [value, setValue] = useState("");
  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && value.trim()) { e.preventDefault(); onSubmit(value.trim()); }
    if (e.key === "Escape") onCancel();
  }
  return (
    <input
      autoFocus
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onKeyDown={handleKeyDown}
      onBlur={onCancel}
      className="w-full text-sm border border-blue-300 rounded-lg px-3 py-2 outline-none focus:ring-1 focus:ring-blue-400"
      placeholder={placeholder}
    />
  );
}

function DayTaskItem({ task, onCycle, onDelete }: { task: DayTaskRead; onCycle: () => void; onDelete: () => void }) {
  return (
    <div className={cn(
      "flex items-center gap-3 rounded-lg border px-4 py-2.5 group hover:bg-accent/50 hover:shadow-sm hover:border-gray-300 transition-all",
      task.status === "done" && "opacity-50",
      task.status === "cancelled" && "opacity-30",
    )}>
      <button
        onClick={onCycle}
        className={cn(
          "w-5 h-5 rounded border flex-shrink-0 flex items-center justify-center text-xs",
          task.status === "done" && "bg-green-100 border-green-400 text-green-600",
          task.status === "cancelled" && "bg-red-50 border-red-300 text-red-400",
        )}
      >
        {task.status === "done" && "✓"}
        {task.status === "cancelled" && "×"}
      </button>
      <span className={cn("flex-1 text-sm", task.status !== "todo" && "line-through")}>{task.title}</span>
      <button
        onClick={onDelete}
        className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 text-sm px-1 transition-opacity"
      >
        ×
      </button>
    </div>
  );
}

function WeekTaskSection({
  weekTask,
  dayTasks,
  onCreateDayTask,
  onCycleDayTask,
  onDeleteDayTask,
}: {
  weekTask: WeekTaskRead;
  dayTasks: DayTaskRead[];
  onCreateDayTask: (title: string, weekTaskId: string) => void;
  onCycleDayTask: (task: DayTaskRead) => void;
  onDeleteDayTask: (id: string) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [creating, setCreating] = useState(false);
  const [hovered, setHovered] = useState(false);

  return (
    <div
      className="rounded-xl border border-gray-200 overflow-hidden"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div
        className="flex items-center gap-2.5 px-5 py-3 cursor-pointer hover:bg-gray-50 bg-gray-50/50"
        onClick={() => setCollapsed(!collapsed)}
      >
        <span className="text-xs text-gray-400">{collapsed ? "▸" : "▾"}</span>
        <span className={cn(
          "flex-1 text-base font-medium",
          weekTask.status === "done" && "line-through text-gray-400",
          weekTask.status === "cancelled" && "line-through text-gray-300",
        )}>
          {weekTask.title}
        </span>
        <span className="text-xs text-gray-400">
          {dayTasks.filter((t) => t.status === "done").length}/{dayTasks.length}
        </span>
      </div>

      {!collapsed && (
        <div className="px-4 pb-4 flex flex-col gap-2 pt-1">
          {dayTasks.map((t) => (
            <DayTaskItem key={t.id} task={t} onCycle={() => onCycleDayTask(t)} onDelete={() => onDeleteDayTask(t.id)} />
          ))}
          {creating ? (
            <InlineCreator
              onSubmit={(title) => { onCreateDayTask(title, weekTask.id); setCreating(false); }}
              onCancel={() => setCreating(false)}
              placeholder="Задача..."
            />
          ) : hovered ? (
            <button
              onClick={() => setCreating(true)}
              className="w-full text-xs text-gray-400 hover:text-blue-500 border border-dashed border-gray-200 hover:border-blue-300 rounded-lg py-2 transition-colors"
            >
              + задача
            </button>
          ) : null}
        </div>
      )}
    </div>
  );
}

export default function DayView() {
  const { weekId, day: dayStr } = useParams<{ weekId: string; day: string }>();
  const day = parseInt(dayStr ?? "0");
  const { data: week, isLoading, error } = useWeek(weekId);

  const createTask = useCreateDayTask(weekId!, week?.year_number);
  const updateTask = useUpdateDayTask(weekId!, week?.year_number);
  const deleteTask = useDeleteDayTask(weekId!, week?.year_number);

  const [miscCreating, setMiscCreating] = useState(false);
  const [miscHovered, setMiscHovered] = useState(false);
  const [miscCollapsed, setMiscCollapsed] = useState(false);

  if (isLoading) return <Spinner />;
  if (error) return <div className="p-8 text-destructive">Ошибка загрузки</div>;
  if (!week) return null;

  const weekMonday = getWeekMonday(week.year_number, week.iso_week);
  const dayDate = new Date(weekMonday);
  dayDate.setDate(weekMonday.getDate() + day);
  const dateLabel = `${dayDate.getDate()} ${MONTH_NAMES[dayDate.getMonth()]}`;

  const dayTasks = week.day_tasks.filter((t) => t.day_of_week === day);
  const linkedTasks = dayTasks.filter((t) => t.week_task_id);
  const unlinkedTasks = dayTasks.filter((t) => !t.week_task_id);

  const weekTasksWithDayTasks = week.week_tasks
    .map((wt) => ({
      weekTask: wt,
      dayTasks: linkedTasks.filter((dt) => dt.week_task_id === wt.id),
    }))
    .filter((s) => s.dayTasks.length > 0 || true);

  function cycleStatus(task: DayTaskRead) {
    const next = task.status === "todo" ? "done" : task.status === "done" ? "cancelled" : "todo";
    updateTask.mutate({ id: task.id, status: next });
  }

  function handleCreateDayTask(title: string, weekTaskId?: string) {
    createTask.mutate({ day, title, week_task_id: weekTaskId });
  }

  return (
    <div className="min-h-full bg-[#F0F2F7]">
      <NavBar>
        <Link to={`/week/${weekId}`} className="text-gray-400 hover:text-gray-600 transition-colors text-lg">
          ←
        </Link>
        <span className="text-lg font-bold text-gray-900">{DAY_NAMES[day]}</span>
        <span className="text-sm text-gray-500">{dateLabel}</span>
        {week.is_rest_week && (
          <span className="text-xs bg-amber-100 text-amber-700 px-2.5 py-1 rounded-full font-medium">Отдых</span>
        )}
      </NavBar>

      <div className="max-w-3xl mx-auto p-8">

        <div className="flex flex-col gap-4">
          {weekTasksWithDayTasks.map(({ weekTask, dayTasks: dt }) => (
            <WeekTaskSection
              key={weekTask.id}
              weekTask={weekTask}
              dayTasks={dt}
              onCreateDayTask={handleCreateDayTask}
              onCycleDayTask={cycleStatus}
              onDeleteDayTask={(id) => deleteTask.mutate(id)}
            />
          ))}

          {/* Разное section */}
          <div
            className="rounded-xl border border-dashed border-gray-300 overflow-hidden"
            onMouseEnter={() => setMiscHovered(true)}
            onMouseLeave={() => setMiscHovered(false)}
          >
            <div
              className="flex items-center gap-2.5 px-5 py-3 cursor-pointer hover:bg-gray-50"
              onClick={() => setMiscCollapsed(!miscCollapsed)}
            >
              <span className="text-xs text-gray-400">{miscCollapsed ? "▸" : "▾"}</span>
              <span className="flex-1 text-base font-medium text-gray-500">Разное</span>
              <span className="text-xs text-gray-400">{unlinkedTasks.length}</span>
            </div>

            {!miscCollapsed && (
              <div className="px-4 pb-4 flex flex-col gap-2 pt-1">
                {unlinkedTasks.map((t) => (
                  <DayTaskItem key={t.id} task={t} onCycle={() => cycleStatus(t)} onDelete={() => deleteTask.mutate(t.id)} />
                ))}
                {miscCreating ? (
                  <InlineCreator
                    onSubmit={(title) => { handleCreateDayTask(title); setMiscCreating(false); }}
                    onCancel={() => setMiscCreating(false)}
                    placeholder="Задача..."
                  />
                ) : miscHovered ? (
                  <button
                    onClick={() => setMiscCreating(true)}
                    className="w-full text-xs text-gray-400 hover:text-blue-500 border border-dashed border-gray-200 hover:border-blue-300 rounded-lg py-2 transition-colors"
                  >
                    + задача
                  </button>
                ) : null}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
