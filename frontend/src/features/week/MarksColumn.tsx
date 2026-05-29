import { useState } from "react";
import type { WeekMarkRead, WeekTaskRead, ThemeRead } from "@/api";
import { useCreateMark, useDeleteMark, useCreateWeekTask, useDeleteWeekTask, useUpdateWeekTask, useUpdateMark, useThemes } from "@/hooks/useApi";
import { cn } from "@/lib/utils";

interface MarksColumnProps {
  weekId: string;
  marks: WeekMarkRead[];
  tasks: WeekTaskRead[];
  year?: number;
}

function TaskItem({
  task,
  onCycleStatus,
  onDelete,
}: {
  task: WeekTaskRead;
  onCycleStatus: () => void;
  onDelete: () => void;
}) {
  return (
    <div className={cn(
      "flex items-center gap-2.5 rounded-lg border px-3 py-2 text-sm group hover:bg-accent/50 hover:shadow-sm hover:border-gray-300 transition-all",
      task.status === "done" && "opacity-50",
      task.status === "cancelled" && "opacity-30",
    )}>
      <button
        onClick={onCycleStatus}
        className={cn(
          "w-5 h-5 rounded border flex-shrink-0 flex items-center justify-center text-xs",
          task.status === "done" && "bg-green-100 border-green-400 text-green-600",
          task.status === "cancelled" && "bg-red-50 border-red-300 text-red-400",
        )}
      >
        {task.status === "done" && "✓"}
        {task.status === "cancelled" && "×"}
      </button>
      <span className={cn("flex-1 text-sm", task.status !== "todo" && "line-through")}>
        {task.title}
      </span>
      <button
        onClick={onDelete}
        className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 text-sm px-1 transition-opacity"
      >
        ×
      </button>
    </div>
  );
}

function InlineTaskCreator({ onSubmit, onCancel }: { onSubmit: (title: string) => void; onCancel: () => void }) {
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
      className="w-full text-sm border border-blue-300 rounded-lg px-3 py-1.5 outline-none focus:ring-1 focus:ring-blue-400"
      placeholder="Задача..."
    />
  );
}

function MarkSection({
  mark,
  tasks,
  weekId,
  year,
  themes,
  onDeleteMark,
}: {
  mark: WeekMarkRead;
  tasks: WeekTaskRead[];
  weekId: string;
  year?: number;
  themes: ThemeRead[];
  onDeleteMark: () => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [creating, setCreating] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [editingTheme, setEditingTheme] = useState(false);
  const createTask = useCreateWeekTask(weekId, year);
  const updateTask = useUpdateWeekTask(weekId, year);
  const deleteTask = useDeleteWeekTask(weekId, year);
  const updateMark = useUpdateMark(weekId, year);

  function cycleStatus(task: WeekTaskRead) {
    const next = task.status === "todo" ? "done" : task.status === "done" ? "cancelled" : "todo";
    updateTask.mutate({ id: task.id, status: next });
  }

  function handleThemeChange(themeId: string) {
    updateMark.mutate({ id: mark.id, theme_id: themeId || null } as any);
    setEditingTheme(false);
  }

  return (
    <div
      className="rounded-xl border border-gray-200 overflow-hidden"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div
        className="flex items-center gap-2.5 px-4 py-2.5 cursor-pointer hover:bg-gray-50"
        onClick={() => !editingTheme && setCollapsed(!collapsed)}
      >
        <span className="text-[11px] text-gray-400">{collapsed ? "▸" : "▾"}</span>
        {editingTheme ? (
          <select
            autoFocus
            defaultValue={mark.theme_id ?? ""}
            onChange={(e) => handleThemeChange(e.target.value)}
            onBlur={() => setEditingTheme(false)}
            onClick={(e) => e.stopPropagation()}
            className="flex-1 text-xs border border-blue-300 rounded px-1 py-0.5 outline-none bg-white"
          >
            <option value="">Без категории</option>
            {themes.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        ) : (
          <>
            {mark.theme_color && (
              <div
                className="w-2.5 h-2.5 rounded-full flex-shrink-0 cursor-pointer hover:ring-2 hover:ring-offset-1 hover:ring-blue-300"
                style={{ backgroundColor: mark.theme_color }}
                onClick={(e) => { e.stopPropagation(); setEditingTheme(true); }}
                title="Изменить категорию"
              />
            )}
            {!mark.theme_color && hovered && (
              <div
                className="w-2.5 h-2.5 rounded-full flex-shrink-0 border-2 border-dashed border-gray-300 hover:border-blue-400 cursor-pointer"
                onClick={(e) => { e.stopPropagation(); setEditingTheme(true); }}
                title="Добавить категорию"
              />
            )}
            <span className="flex-1 text-sm font-medium">{mark.title}</span>
          </>
        )}
        <span className="text-xs text-gray-400">{tasks.length}</span>
        <button
          onClick={(e) => { e.stopPropagation(); onDeleteMark(); }}
          className="text-gray-400 hover:text-red-500 text-xs px-1"
          style={{ opacity: hovered ? 1 : 0 }}
        >
          ×
        </button>
      </div>

      {!collapsed && (
        <div className="px-3 pb-3 flex flex-col gap-1.5">
          {tasks.map((t) => (
            <TaskItem
              key={t.id}
              task={t}
              onCycleStatus={() => cycleStatus(t)}
              onDelete={() => deleteTask.mutate(t.id)}
            />
          ))}
          {creating ? (
            <InlineTaskCreator
              onSubmit={(title) => { createTask.mutate({ title, mark_id: mark.id }); setCreating(false); }}
              onCancel={() => setCreating(false)}
            />
          ) : hovered ? (
            <button
              onClick={() => setCreating(true)}
              className="w-full text-xs text-gray-400 hover:text-blue-500 border border-dashed border-gray-200 hover:border-blue-300 rounded-lg py-1.5 transition-colors"
            >
              + задача
            </button>
          ) : null}
        </div>
      )}
    </div>
  );
}

export default function MarksColumn({ weekId, marks, tasks, year }: MarksColumnProps) {
  const [creatingMark, setCreatingMark] = useState(false);
  const [markTitle, setMarkTitle] = useState("");
  const [markThemeId, setMarkThemeId] = useState<string>("");
  const { data: themes } = useThemes();
  const createMark = useCreateMark(weekId, year);
  const deleteMark = useDeleteMark(weekId, year);
  const createTask = useCreateWeekTask(weekId, year);
  const updateTask = useUpdateWeekTask(weekId, year);
  const deleteTask = useDeleteWeekTask(weekId, year);

  const unlinkedTasks = tasks.filter((t) => !t.mark_id);
  const [unlinkedCollapsed, setUnlinkedCollapsed] = useState(false);
  const [creatingUnlinked, setCreatingUnlinked] = useState(false);
  const [unlinkedHovered, setUnlinkedHovered] = useState(false);

  function cycleStatus(task: WeekTaskRead) {
    const next = task.status === "todo" ? "done" : task.status === "done" ? "cancelled" : "todo";
    updateTask.mutate({ id: task.id, status: next });
  }

  function handleCreateMark(e: React.KeyboardEvent) {
    if (e.key === "Enter" && markTitle.trim()) {
      createMark.mutate({ title: markTitle.trim(), theme_id: markThemeId || undefined });
      setMarkTitle("");
      setMarkThemeId("");
      setCreatingMark(false);
    }
    if (e.key === "Escape") { setCreatingMark(false); setMarkTitle(""); setMarkThemeId(""); }
  }

  return (
    <div className="flex flex-col gap-2.5">
      <h3 className="text-base font-semibold text-muted-foreground">Пометки</h3>

      {marks.map((mark) => (
        <MarkSection
          key={mark.id}
          mark={mark}
          tasks={tasks.filter((t) => t.mark_id === mark.id)}
          weekId={weekId}
          year={year}
          themes={themes ?? []}
          onDeleteMark={() => deleteMark.mutate({ id: mark.id })}
        />
      ))}

      {/* Без привязки section */}
      <div
        className="rounded-xl border border-dashed border-gray-200 overflow-hidden"
        onMouseEnter={() => setUnlinkedHovered(true)}
        onMouseLeave={() => setUnlinkedHovered(false)}
      >
        <div
          className="flex items-center gap-2.5 px-4 py-2.5 cursor-pointer hover:bg-gray-50"
          onClick={() => setUnlinkedCollapsed(!unlinkedCollapsed)}
        >
          <span className="text-[11px] text-gray-400">{unlinkedCollapsed ? "▸" : "▾"}</span>
          <span className="flex-1 text-sm font-medium text-gray-500">Без привязки</span>
          <span className="text-xs text-gray-400">{unlinkedTasks.length}</span>
        </div>
        {!unlinkedCollapsed && (
          <div className="px-3 pb-3 flex flex-col gap-1.5">
            {unlinkedTasks.map((t) => (
              <TaskItem
                key={t.id}
                task={t}
                onCycleStatus={() => cycleStatus(t)}
                onDelete={() => deleteTask.mutate(t.id)}
              />
            ))}
            {creatingUnlinked ? (
              <InlineTaskCreator
                onSubmit={(title) => { createTask.mutate({ title }); setCreatingUnlinked(false); }}
                onCancel={() => setCreatingUnlinked(false)}
              />
            ) : unlinkedHovered ? (
              <button
                onClick={() => setCreatingUnlinked(true)}
                className="w-full text-xs text-gray-400 hover:text-blue-500 border border-dashed border-gray-200 hover:border-blue-300 rounded-lg py-1.5 transition-colors"
              >
                + задача
              </button>
            ) : null}
          </div>
        )}
      </div>

      {/* Add mark button */}
      {creatingMark ? (
        <div className="flex flex-col gap-2 border border-blue-300 rounded-xl px-3 py-2.5">
          <input
            autoFocus
            value={markTitle}
            onChange={(e) => setMarkTitle(e.target.value)}
            onKeyDown={handleCreateMark}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 outline-none focus:ring-1 focus:ring-blue-400"
            placeholder="Название пометки..."
          />
          <select
            value={markThemeId}
            onChange={(e) => setMarkThemeId(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 outline-none focus:ring-1 focus:ring-blue-400 bg-white"
          >
            <option value="">Без категории</option>
            {themes?.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
          <div className="flex gap-2">
            <button
              onClick={() => {
                if (markTitle.trim()) {
                  createMark.mutate({ title: markTitle.trim(), theme_id: markThemeId || undefined });
                  setMarkTitle("");
                  setMarkThemeId("");
                  setCreatingMark(false);
                }
              }}
              className="flex-1 text-xs bg-blue-500 hover:bg-blue-600 text-white rounded-lg py-1.5 transition-colors"
            >
              Создать
            </button>
            <button
              onClick={() => { setCreatingMark(false); setMarkTitle(""); setMarkThemeId(""); }}
              className="flex-1 text-xs text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg py-1.5 transition-colors"
            >
              Отмена
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setCreatingMark(true)}
          className="text-xs text-gray-400 hover:text-blue-500 border border-dashed border-gray-200 hover:border-blue-300 rounded-xl py-2.5 transition-colors"
        >
          + Пометка
        </button>
      )}
    </div>
  );
}
