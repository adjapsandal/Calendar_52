import { useState } from "react";
import type { QuarterBlock as QuarterBlockType } from "@/api";
import { usePutQuarterNote, useCreateMark } from "@/hooks/useApi";
import { Textarea } from "@/components/ui/textarea";
import { useDraggable, useDroppable } from "@dnd-kit/core";
import { cn } from "@/lib/utils";
import { Link } from "react-router-dom";

const SHORT_MONTHS = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];

function weekDateRange(year: number, isoWeek: number): string {
  const jan4 = new Date(year, 0, 4);
  const dow = jan4.getDay() || 7;
  const mon1 = new Date(jan4);
  mon1.setDate(jan4.getDate() - (dow - 1));
  const monday = new Date(mon1);
  monday.setDate(mon1.getDate() + (isoWeek - 1) * 7);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  const d1 = monday.getDate();
  const m1 = SHORT_MONTHS[monday.getMonth()];
  const d2 = sunday.getDate();
  const m2 = SHORT_MONTHS[sunday.getMonth()];
  return m1 === m2 ? `${d1}–${d2} ${m1}` : `${d1} ${m1} – ${d2} ${m2}`;
}

interface MarkDraggable {
  id: string;
  title: string;
  color: string | null;
  weekId: string;
}

interface QuarterBlockProps {
  data: QuarterBlockType;
  year: number;
  weekBudget: number;
  currentDisplayPos?: number;
  draggableMarks?: MarkDraggable[];
}

function DraggableMark({ mark }: { mark: MarkDraggable }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: `mark-${mark.id}` });
  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      className="flex items-center gap-1.5 min-w-0 cursor-grab active:cursor-grabbing rounded-lg px-2 py-1 border border-transparent hover:border-gray-200 hover:bg-gray-100 hover:shadow-sm transition-all shrink-0"
      style={{ opacity: isDragging ? 0.4 : 1 }}
    >
      {mark.color && (
        <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: mark.color }} />
      )}
      <span className="text-xs leading-tight font-medium break-words" style={{ color: mark.color ?? undefined }}>
        {mark.title}
      </span>
    </div>
  );
}

function InlineMarkCreator({ weekId, year, onDone }: { weekId: string; year: number; onDone: () => void }) {
  const [value, setValue] = useState("");
  const create = useCreateMark(weekId, year);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && value.trim()) {
      e.preventDefault();
      create.mutate({ title: value.trim() });
      onDone();
    }
    if (e.key === "Escape") onDone();
  }

  return (
    <input
      autoFocus
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onKeyDown={handleKeyDown}
      onBlur={onDone}
      className="w-full text-xs leading-tight border border-blue-300 rounded-lg px-2 py-1 outline-none focus:ring-1 focus:ring-blue-400"
      placeholder="Пометка..."
    />
  );
}

function DroppableWeekCard({
  week,
  weekBudget,
  isCurrent,
  marks,
  year,
  dateRange,
}: {
  week: QuarterBlockType["weeks"][0];
  weekBudget: number;
  isCurrent?: boolean;
  marks: MarkDraggable[];
  year: number;
  dateRange: string;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: week.id });
  const [creating, setCreating] = useState(false);
  const [hovered, setHovered] = useState(false);

  return (
    <div ref={setNodeRef} onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)} className="h-full">
      <Link to={`/week/${week.id}`} className="block h-full">
        <div
          className={cn(
            "relative flex flex-col rounded-xl border cursor-pointer transition-all duration-150 select-none min-h-[180px] h-full hover:shadow-sm",
            week.is_rest_week
              ? "bg-amber-50 border-amber-200 hover:border-amber-400"
              : week.cached_load === 0
              ? "bg-white border-gray-200 hover:border-blue-300"
              : week.cached_load / weekBudget <= 0.7
              ? "bg-white border-gray-200 hover:border-blue-300"
              : week.cached_load / weekBudget <= 1.0
              ? "bg-yellow-50 border-yellow-300"
              : "bg-rose-50 border-rose-200 hover:border-rose-400",
            isCurrent && "ring-2 ring-blue-400/25 border-blue-400 bg-blue-50",
            isOver && "ring-2 ring-primary/50 bg-primary/5",
          )}
        >
          {!week.is_rest_week && marks.length > 0 && (
            <div className="flex h-1.5 rounded-t-xl overflow-hidden">
              {marks.slice(0, 4).map((m) => (
                <div
                  key={m.id}
                  className="flex-1"
                  style={{ backgroundColor: m.color ?? "#94a3b8" }}
                />
              ))}
            </div>
          )}

          <div className="flex-1 flex flex-col px-3 pt-2 pb-3 gap-1">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className={cn(
                  "text-sm font-semibold",
                  isCurrent ? "text-blue-600" : week.is_rest_week ? "text-amber-700" : "text-gray-700"
                )}>
                  {week.display_position}
                </span>
                {isCurrent && (
                  <div className="w-2 h-2 rounded-full bg-blue-500" />
                )}
              </div>
              <span className="text-[11px] text-gray-400">{dateRange}</span>
            </div>

            {week.is_rest_week ? (
              <span className="text-xs text-amber-600 font-medium mt-auto">Отдых</span>
            ) : (
              <div className="flex flex-col gap-1 mt-1">
                <div
                  className="flex flex-col gap-1 scrollbar-thin"
                  style={marks.length > 4 ? { maxHeight: 120, overflowY: "auto" as const } : undefined}
                >
                  {marks.map((m) => (
                    <DraggableMark key={m.id} mark={m} />
                  ))}
                </div>
                {hovered && !creating && (
                  <button
                    onClick={(e) => { e.preventDefault(); e.stopPropagation(); setCreating(true); }}
                    className="w-full flex items-center justify-center rounded-lg border border-dashed border-gray-300 hover:border-blue-400 hover:bg-blue-50 text-gray-400 hover:text-blue-500 text-xs py-1 transition-colors"
                  >
                    +
                  </button>
                )}
                {creating && (
                  <div onClick={(e) => { e.preventDefault(); e.stopPropagation(); }}>
                    <InlineMarkCreator weekId={week.id} year={year} onDone={() => setCreating(false)} />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </Link>
    </div>
  );
}

export default function QuarterBlock({ data, year, weekBudget, currentDisplayPos, draggableMarks = [] }: QuarterBlockProps) {
  const [noteContent, setNoteContent] = useState(data.note?.content ?? "");
  const putNote = usePutQuarterNote(year, data.quarter);

  const working = data.weeks.filter((w) => !w.is_rest_week);
  const restWeek = data.weeks.find((w) => w.is_rest_week);
  const row1 = working.slice(0, 6);
  const row2 = working.slice(6, 12);

  function saveNote() {
    if (noteContent !== (data.note?.content ?? "")) {
      putNote.mutate(noteContent);
    }
  }

  const marksByWeek = new Map<string, MarkDraggable[]>();
  for (const m of draggableMarks) {
    const list = marksByWeek.get(m.weekId) ?? [];
    list.push(m);
    marksByWeek.set(m.weekId, list);
  }

  const QUARTER_LABELS = ["I квартал", "II квартал", "III квартал", "IV квартал"];
  const QUARTER_MONTHS = ["Январь — Март", "Апрель — Июнь", "Июль — Сентябрь", "Октябрь — Декабрь"];

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
      <div className="flex items-center justify-between mb-5">
        <span className="text-base font-semibold text-gray-400 uppercase tracking-wider">
          {QUARTER_LABELS[data.quarter - 1]}
        </span>
        <span className="text-sm text-gray-400 w-[240px] shrink-0">
          {QUARTER_MONTHS[data.quarter - 1]}
        </span>
      </div>

      <div className="flex gap-5">
        <div className="flex-1 flex flex-col gap-3">
          <div className="grid grid-cols-7 gap-3">
            {row1.map((w) => (
              <DroppableWeekCard
                key={w.id}
                week={w}
                weekBudget={weekBudget}
                isCurrent={w.display_position === currentDisplayPos}
                marks={marksByWeek.get(w.id) ?? []}
                year={year}
                dateRange={weekDateRange(year, w.iso_week)}
              />
            ))}
            <div />
          </div>

          <div className="grid grid-cols-7 gap-3">
            {row2.map((w) => (
              <DroppableWeekCard
                key={w.id}
                week={w}
                weekBudget={weekBudget}
                isCurrent={w.display_position === currentDisplayPos}
                marks={marksByWeek.get(w.id) ?? []}
                year={year}
                dateRange={weekDateRange(year, w.iso_week)}
              />
            ))}
            {restWeek && (
              <DroppableWeekCard
                week={restWeek}
                weekBudget={weekBudget}
                isCurrent={restWeek.display_position === currentDisplayPos}
                marks={marksByWeek.get(restWeek.id) ?? []}
                year={year}
                dateRange={weekDateRange(year, restWeek.iso_week)}
              />
            )}
          </div>
        </div>

        <div className="w-[240px] shrink-0">
          <div className="h-full border border-dashed border-gray-300 rounded-xl px-4 py-4 bg-gray-50/50 hover:bg-gray-50 transition-colors">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block mb-2">
              Заметки квартала
            </span>
            <Textarea
              value={noteContent}
              onChange={(e) => setNoteContent(e.target.value)}
              onBlur={saveNote}
              placeholder={`Фокус Q${data.quarter}...`}
              className="h-[200px] text-sm resize-none border-0 p-0 bg-transparent focus-visible:ring-0 shadow-none"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
