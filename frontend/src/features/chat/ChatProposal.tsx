import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { ChatOperation } from "@/api";

interface Props {
  open: boolean;
  onClose: () => void;
  operations: ChatOperation[];
  onApply: (selected: ChatOperation[]) => void;
  applying: boolean;
}

const ACTION_CONFIG: Record<string, { label: string; badge: string; color: string }> = {
  move: { label: "Перенести", badge: "->", color: "bg-blue-100 text-blue-700" },
  delete: { label: "Удалить", badge: "x", color: "bg-red-100 text-red-700" },
  create: { label: "Создать", badge: "+", color: "bg-green-100 text-green-700" },
  update_status: { label: "Статус", badge: "~", color: "bg-amber-100 text-amber-700" },
};

const ITEM_TYPE_LABEL: Record<string, string> = {
  week_task: "Задача недели",
  day_task: "Задача дня",
  mark: "Пометка",
};

const STATUS_LABEL: Record<string, string> = {
  done: "Выполнено",
  cancelled: "Отменено",
  todo: "К выполнению",
};

export default function ChatProposal({
  open,
  onClose,
  operations,
  onApply,
  applying,
}: Props) {
  const [checked, setChecked] = useState<Set<number>>(
    () => new Set(operations.map((_, i) => i))
  );

  function toggle(index: number) {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  function toggleAll() {
    if (checked.size === operations.length) {
      setChecked(new Set());
    } else {
      setChecked(new Set(operations.map((_, i) => i)));
    }
  }

  const selected = operations.filter((_, i) => checked.has(i));

  function describeOp(op: ChatOperation): string {
    const type = ITEM_TYPE_LABEL[op.item_type] || op.item_type;
    switch (op.action) {
      case "delete":
        return `${type}`;
      case "move":
        return `${type}`;
      case "create":
        return `${type}`;
      case "update_status":
        return `${type} -> ${STATUS_LABEL[op.new_status ?? ""] ?? op.new_status}`;
      default:
        return type;
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-2xl w-[90vw] max-h-[92vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            ИИ предлагает {operations.length}{" "}
            {operations.length === 1 ? "операцию" : operations.length < 5 ? "операции" : "операций"}
          </DialogTitle>
        </DialogHeader>

        <div className="flex items-center justify-between py-1 px-1">
          <button
            onClick={toggleAll}
            className="text-xs text-muted-foreground hover:text-primary transition-colors"
          >
            {checked.size === operations.length ? "Снять все" : "Выбрать все"}
          </button>
          <span className="text-xs text-muted-foreground">
            Выбрано: {checked.size} из {operations.length}
          </span>
        </div>

        <div className="flex flex-col gap-2 py-1">
          {operations.map((op, i) => {
            const cfg = ACTION_CONFIG[op.action] ?? ACTION_CONFIG.move;
            const isChecked = checked.has(i);

            return (
              <label
                key={i}
                className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  isChecked ? "bg-white border-gray-200" : "opacity-50 bg-gray-50 border-gray-100"
                }`}
              >
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => toggle(i)}
                  className="mt-1 flex-shrink-0"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded ${cfg.color}`}>
                      {cfg.badge} {cfg.label}
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      {describeOp(op)}
                    </span>
                  </div>
                  <p className="text-sm font-medium">{op.item_title}</p>
                  {op.reasoning && (
                    <p className="text-xs text-muted-foreground mt-0.5">{op.reasoning}</p>
                  )}
                </div>
              </label>
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
              : checked.size === operations.length
              ? "Принять все"
              : `Применить ${checked.size} из ${operations.length}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
