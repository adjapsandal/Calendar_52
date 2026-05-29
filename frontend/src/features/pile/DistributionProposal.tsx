import { useState, useMemo } from "react";
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
  weekMap?: Map<string, number>; // week_id → display_position
  onApply: (selected: DistributionSuggestion[]) => void;
  applying: boolean;
}

interface SuggestionNode extends DistributionSuggestion {
  children: SuggestionNode[];
}

function buildTree(suggestions: DistributionSuggestion[]): SuggestionNode[] {
  const nodeMap = new Map<number, SuggestionNode>();
  const roots: SuggestionNode[] = [];

  for (const s of suggestions) {
    nodeMap.set(s.index, { ...s, children: [] });
  }

  for (const s of suggestions) {
    const node = nodeMap.get(s.index)!;
    if (s.parent_index === -1 || s.parent_index === undefined) {
      roots.push(node);
    } else {
      const parent = nodeMap.get(s.parent_index);
      if (parent) {
        parent.children.push(node);
      } else {
        roots.push(node);
      }
    }
  }

  return roots;
}

const TYPE_CONFIG: Record<string, { icon: string; label: string }> = {
  mark: { icon: "🏷️", label: "Пометка" },
  week_task: { icon: "📋", label: "Задача недели" },
  day_task: { icon: "📌", label: "Задача дня" },
};

const DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

function collectIndices(node: SuggestionNode): number[] {
  const result = [node.index];
  for (const child of node.children) {
    result.push(...collectIndices(child));
  }
  return result;
}

export default function DistributionProposal({
  open,
  onClose,
  suggestions,
  pileMap,
  weekMap,
  onApply,
  applying,
}: Props) {
  const [checked, setChecked] = useState<Set<number>>(
    () => new Set(suggestions.map((s) => s.index))
  );

  const tree = useMemo(() => buildTree(suggestions), [suggestions]);

  // Группируем корневые по pile_item_id
  const groups = useMemo(() => {
    const map = new Map<string, SuggestionNode[]>();
    for (const root of tree) {
      const key = root.pile_item_id;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(root);
    }
    return Array.from(map.entries());
  }, [tree]);

  function toggleNode(node: SuggestionNode) {
    const indices = collectIndices(node);
    setChecked((prev) => {
      const next = new Set(prev);
      const allChecked = indices.every((i) => next.has(i));
      if (allChecked) {
        indices.forEach((i) => next.delete(i));
      } else {
        indices.forEach((i) => next.add(i));
      }
      return next;
    });
  }

  function toggleSingle(index: number) {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  const selected = suggestions.filter((s) => checked.has(s.index));

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-3xl w-[90vw] max-h-[92vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>ИИ-предложение: {suggestions.length} элементов</DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-3 py-2">
          {groups.map(([pileId, roots]) => {
            const pileContent = pileMap.get(pileId) ?? "???";
            return (
              <div key={pileId} className="rounded-lg border overflow-hidden">
                <div className="px-3 py-2 bg-gray-50 border-b">
                  <p className="text-xs text-muted-foreground truncate">
                    Из Кучи: {pileContent}
                  </p>
                </div>
                <div className="flex flex-col">
                  {roots.map((root) => (
                    <NodeRow
                      key={root.index}
                      node={root}
                      depth={0}
                      checked={checked}
                      weekMap={weekMap}
                      onToggleNode={toggleNode}
                      onToggleSingle={toggleSingle}
                    />
                  ))}
                </div>
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
              ? "Принять все"
              : `Применить ${checked.size} из ${suggestions.length}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function NodeRow({
  node,
  depth,
  checked,
  weekMap,
  onToggleNode,
  onToggleSingle,
}: {
  node: SuggestionNode;
  depth: number;
  checked: Set<number>;
  weekMap?: Map<string, number>;
  onToggleNode: (node: SuggestionNode) => void;
  onToggleSingle: (index: number) => void;
}) {
  const cfg = TYPE_CONFIG[node.item_type] ?? TYPE_CONFIG.week_task;
  const isChecked = checked.has(node.index);
  const hasChildren = node.children.length > 0;
  const allChildrenChecked = hasChildren && collectIndices(node).every((i) => checked.has(i));
  const someChildrenChecked = hasChildren && collectIndices(node).some((i) => checked.has(i));
  const isPartial = someChildrenChecked && !allChildrenChecked;

  const weekNum = weekMap?.get(node.target_week_id);

  const paddingLeft = depth * 24;

  return (
    <>
      <label
        style={{ paddingLeft: paddingLeft + 12 }}
        className={`flex items-start gap-2 py-2 pr-3 cursor-pointer transition-colors ${
          isChecked ? "bg-white" : "opacity-50 bg-gray-50"
        } ${depth === 0 ? "border-b last:border-b-0" : ""}`}
      >
        <input
          type="checkbox"
          checked={hasChildren ? allChildrenChecked : isChecked}
          ref={(el) => { if (el && hasChildren) el.indeterminate = isPartial; }}
          onChange={() => hasChildren ? onToggleNode(node) : onToggleSingle(node.index)}
          className="mt-0.5 flex-shrink-0"
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-xs">{cfg.icon}</span>
            <span className="text-sm font-medium">{node.title}</span>
            {weekNum != null && (
              <span className="text-[10px] text-blue-600 bg-blue-50 px-1 rounded">
                Н{weekNum}
              </span>
            )}
            {node.item_type === "day_task" && node.day_of_week >= 0 && (
              <span className="text-[10px] text-muted-foreground bg-gray-100 px-1 rounded">
                {DAY_NAMES[node.day_of_week]}
              </span>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {cfg.label} {node.reasoning && `· ${node.reasoning}`}
          </p>
        </div>
      </label>
      {node.children.map((child) => (
        <NodeRow
          key={child.index}
          node={child}
          depth={depth + 1}
          checked={checked}
          weekMap={weekMap}
          onToggleNode={onToggleNode}
          onToggleSingle={onToggleSingle}
        />
      ))}
    </>
  );
}
