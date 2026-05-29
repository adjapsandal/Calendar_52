import { cn } from "@/lib/utils";
import type { WeekBrief } from "@/api";
import { Link } from "react-router-dom";
import { useDroppable } from "@dnd-kit/core";

interface WeekCardProps {
  week: WeekBrief;
  weekBudget: number;
  isCurrent?: boolean;
  activeMarkId?: string | null;
}

function loadColor(load: number, budget: number): string {
  if (load === 0) return "bg-gray-100";
  const ratio = load / budget;
  if (ratio <= 0.7) return "bg-green-100 border-green-300";
  if (ratio <= 1.0) return "bg-yellow-50 border-yellow-300";
  return "bg-red-50 border-red-300";
}

export default function WeekCard({ week, weekBudget, isCurrent, activeMarkId }: WeekCardProps) {
  const isRest = week.is_rest_week;
  const { setNodeRef, isOver } = useDroppable({ id: week.id });

  return (
    <div ref={setNodeRef}>
      <Link to={`/week/${week.id}`}>
        <div
          className={cn(
            "relative flex flex-col rounded-md border p-1.5 text-xs transition-colors hover:bg-accent cursor-pointer min-h-[56px]",
            loadColor(week.cached_load, weekBudget),
            isCurrent && "ring-2 ring-primary",
            isRest && "bg-blue-50 border-blue-200 opacity-70",
            isOver && activeMarkId && "ring-2 ring-primary/50 bg-primary/5",
          )}
        >
          <span className="font-medium text-[10px] text-muted-foreground">
            {week.display_position}
          </span>

          {isRest ? (
            <span className="text-[9px] text-blue-500 mt-auto">отдых</span>
          ) : (
            <div className="mt-auto">
              {week.marks_preview.slice(0, 2).map((m) => (
                <div
                  key={m.id}
                  draggable
                  onDragStart={(e) => {
                    e.preventDefault();
                  }}
                  className="truncate text-[10px] leading-tight"
                  style={{ color: m.color ?? undefined }}
                >
                  {m.title}
                </div>
              ))}
              {week.cached_load > 0 && (
                <span className="text-[9px] text-muted-foreground">
                  {week.cached_load}/{weekBudget}
                </span>
              )}
            </div>
          )}
        </div>
      </Link>
    </div>
  );
}
