import { useState, useEffect } from "react";
import type { WeekMarkRead, WeekTaskRead } from "@/api";
import { useCreateWeekTask, useDeleteWeekTask, useUpdateWeekTask } from "@/hooks/useApi";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

interface TasksColumnProps {
  weekId: string;
  tasks: WeekTaskRead[];
  marks: WeekMarkRead[];
  year?: number;
}

const STATUS_COLORS: Record<string, string> = {
  todo: "bg-gray-100 text-gray-700",
  done: "bg-green-100 text-green-700 line-through",
  cancelled: "bg-red-50 text-red-500 line-through",
};

function SortableTask({
  task,
  markMap,
  onCycleStatus,
  onDelete,
}: {
  task: WeekTaskRead;
  markMap: Map<string, WeekMarkRead>;
  onCycleStatus: () => void;
  onDelete: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: task.id,
  });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        "flex items-center gap-2 rounded-md border p-2 text-sm group cursor-grab active:cursor-grabbing",
        STATUS_COLORS[task.status] ?? "",
      )}
      {...attributes}
      {...listeners}
    >
      <button
        onClick={(e) => { e.stopPropagation(); onCycleStatus(); }}
        className="w-4 h-4 rounded border flex-shrink-0"
      />
      <span className="flex-1">{task.title}</span>
      {task.mark_id && markMap.get(task.mark_id) && (
        <span
          className="text-xs px-1.5 py-0.5 rounded"
          style={{
            backgroundColor: (markMap.get(task.mark_id)!.theme_color ?? "#e5e7eb") + "20",
            color: markMap.get(task.mark_id)!.theme_color ?? undefined,
          }}
        >
          {markMap.get(task.mark_id)!.title}
        </span>
      )}
      <Button
        variant="ghost"
        size="sm"
        className="opacity-0 group-hover:opacity-100 h-6 px-1"
        onClick={(e) => { e.stopPropagation(); onDelete(); }}
      >
        ×
      </Button>
    </div>
  );
}

export default function TasksColumn({ weekId, tasks, marks, year }: TasksColumnProps) {
  const [newTitle, setNewTitle] = useState("");
  const [newMarkId, setNewMarkId] = useState<string>("");
  const [localTasks, setLocalTasks] = useState(() => tasks.map((t) => t.id));
  const create = useCreateWeekTask(weekId, year);
  const update = useUpdateWeekTask(weekId, year);
  const remove = useDeleteWeekTask(weekId, year);

  const serverIds = tasks.map((t) => t.id).join(",");
  useEffect(() => {
    setLocalTasks(tasks.map((t) => t.id));
  }, [serverIds]);

  const taskMap = new Map(tasks.map((t) => [t.id, t]));
  const markMap = new Map(marks.map((m) => [m.id, m]));

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    setLocalTasks((prev) => {
      const oldIndex = prev.indexOf(String(active.id));
      const newIndex = prev.indexOf(String(over.id));
      const next = arrayMove(prev, oldIndex, newIndex);
      next.forEach((id, pos) => {
        update.mutate({ id, position: pos });
      });
      return next;
    });
  }

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newTitle.trim()) return;
    create.mutate(
      { title: newTitle.trim(), mark_id: newMarkId || undefined },
      {
        onSuccess: (res) => {
          setLocalTasks((prev) => [...prev, res.data.id]);
        },
      },
    );
    setNewTitle("");
    setNewMarkId("");
  }

  function cycleStatus(task: WeekTaskRead) {
    const next = task.status === "todo" ? "done" : task.status === "done" ? "cancelled" : "todo";
    update.mutate({ id: task.id, status: next });
  }

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold text-muted-foreground">Задачи недели</h3>

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={localTasks} strategy={verticalListSortingStrategy}>
          {localTasks.map((id) => {
            const task = taskMap.get(id);
            if (!task) return null;
            return (
              <SortableTask
                key={task.id}
                task={task}
                markMap={markMap}
                onCycleStatus={() => cycleStatus(task)}
                onDelete={() => remove.mutate(task.id)}
              />
            );
          })}
        </SortableContext>
      </DndContext>

      <form onSubmit={handleCreate} className="flex gap-1">
        <Input
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          placeholder="+ Задача"
          className="h-8 text-sm"
        />
        <select
          value={newMarkId}
          onChange={(e) => setNewMarkId(e.target.value)}
          className="h-8 text-xs border rounded px-1 bg-background"
        >
          <option value="">—</option>
          {marks.map((m) => (
            <option key={m.id} value={m.id}>{m.title}</option>
          ))}
        </select>
        <Button type="submit" size="sm" disabled={!newTitle.trim()}>+</Button>
      </form>
    </div>
  );
}
