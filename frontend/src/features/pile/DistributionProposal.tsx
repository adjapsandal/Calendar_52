import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { DistributionSuggestion } from "@/api";

interface Props {
  open: boolean;
  onClose: () => void;
  suggestions: DistributionSuggestion[];
  pileMap: Map<string, string>;
  onApply: (selected: DistributionSuggestion[]) => void;
  applying: boolean;
}

interface Group {
  pile_item_id: string;
  suggestions: DistributionSuggestion[];
  indices: number[];
}

function buildGroups(suggestions: DistributionSuggestion[]): Group[] {
  const map = new Map<string, Group>();
  suggestions.forEach((s, i) => {
    const key = s.pile_item_id;
    if (!map.has(key)) {
      map.set(key, { pile_item_id: key, suggestions: [], indices: [] });
    }
    const g = map.get(key)!;
    g.suggestions.push(s);
    g.indices.push(i);
  });
  return Array.from(map.values());
}

function typeLabel(s: DistributionSuggestion): string {
  if (s.as_mark) return "Пометка";
  if (s.day_of_week >= 0) {
    const days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
    return `Задача дня (${days[s.day_of_week] ?? s.day_of_week})`;
  }
  return "Задача недели";
}

export default function DistributionProposal({
  open,
  onClose,
  suggestions,
  pileMap,
  onApply,
  applying,
}: Props) {
  const [checked, setChecked] = useState<Set<string>>(
    () => new Set(suggestions.map((_, i) => String(i)))
  );
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const groups = buildGroups(suggestions);

  function toggleItem(index: number) {
    setChecked((prev) => {
      const next = new Set(prev);
      const key = String(index);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function isGroupChecked(group: Group): boolean {
    return group.indices.every((i) => checked.has(String(i)));
  }

  function isGroupPartial(group: Group): boolean {
    const some = group.indices.some((i) => checked.has(String(i)));
    const all = group.indices.every((i) => checked.has(String(i)));
    return some && !all;
  }

  function toggleGroup(group: Group) {
    setChecked((prev) => {
      const next = new Set(prev);
      if (isGroupChecked(group)) {
        group.indices.forEach((i) => next.delete(String(i)));
      } else {
        group.indices.forEach((i) => next.add(String(i)));
      }
      return next;
    });
  }

  function toggleExpand(pile_item_id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(pile_item_id)) next.delete(pile_item_id);
      else next.add(pile_item_id);
      return next;
    });
  }

  const selected = suggestions.filter((_, i) => checked.has(String(i)));

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-3xl w-[90vw] max-h-[92vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>ИИ-предложение: {groups.length} записей</DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-2 py-2">
          {groups.map((group) => {
            const isMulti = group.suggestions.length > 1;
            const isExp = expanded.has(group.pile_item_id);
            const allChecked = isGroupChecked(group);
            const partial = isGroupPartial(group);
            const pileContent = pileMap.get(group.pile_item_id) ?? group.suggestions[0]?.title ?? "???";
            const first = group.suggestions[0];

            return (
              <div key={group.pile_item_id} className="rounded-lg border overflow-hidden">
                {/* Group header row */}
                <label
                  className={`flex items-start gap-3 p-3 cursor-pointer transition-colors ${
                    allChecked ? "bg-primary/5 border-b-primary/20" : partial ? "bg-yellow-50/50" : "opacity-60"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={allChecked}
                    ref={(el) => { if (el) el.indeterminate = partial; }}
                    onChange={() => toggleGroup(group)}
                    className="mt-0.5 flex-shrink-0"
                  />
                  <div className="flex-1 min-w-0">
                    {pileContent !== first.title && (
                      <p className="text-xs text-muted-foreground mb-1 truncate">
                        Исходник: {pileContent}
                      </p>
                    )}
                    <p className="text-sm font-medium">{first.title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {typeLabel(first)}
                      {!isMulti && ` · ${first.reasoning}`}
                    </p>
                  </div>
                  {isMulti && (
                    <button
                      onClick={(e) => { e.preventDefault(); toggleExpand(group.pile_item_id); }}
                      className="flex-shrink-0 text-xs text-muted-foreground hover:text-primary px-2 py-0.5 rounded border border-gray-200 hover:border-primary/40 transition-colors"
                    >
                      × {group.suggestions.length} нед. {isExp ? "▴" : "▾"}
                    </button>
                  )}
                </label>

                {/* Sub-rows for recurring items */}
                {isMulti && isExp && (
                  <div className="flex flex-col divide-y">
                    {group.suggestions.map((s, localIdx) => {
                      const globalIdx = group.indices[localIdx];
                      const isCh = checked.has(String(globalIdx));
                      return (
                        <label
                          key={globalIdx}
                          className={`flex items-center gap-3 px-4 py-2 cursor-pointer transition-colors text-sm ${
                            isCh ? "bg-white" : "opacity-50 bg-gray-50"
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isCh}
                            onChange={() => toggleItem(globalIdx)}
                            className="flex-shrink-0"
                          />
                          <span className="text-xs text-muted-foreground">{s.reasoning}</span>
                        </label>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <DialogFooter className="gap-2">
          <Button variant="ghost" onClick={onClose} disabled={applying}>
            Отмена
          </Button>
          <Button
            onClick={() => onApply(selected)}
            disabled={checked.size === 0 || applying}
          >
            {applying
              ? "Применяем..."
              : checked.size === suggestions.length
              ? "Принять всё"
              : `Применить ${checked.size} из ${suggestions.length}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
