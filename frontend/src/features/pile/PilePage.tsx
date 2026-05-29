import { useState } from "react";
import {
  usePileItems,
  useCreatePileItem,
  useDeletePileItem,
  useUpdatePileItem,
  useDistribute,
  useApplyDistribution,
} from "@/hooks/useApi";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import NavBar from "@/components/NavBar";
import type { DistributionSuggestion } from "@/api";
import DistributionProposal from "./DistributionProposal";

export default function PilePage() {
  const { data: items, isLoading } = usePileItems();
  const create = useCreatePileItem();
  const remove = useDeletePileItem();
  const distribute = useDistribute();
  const applyDistribution = useApplyDistribution();

  const [text, setText] = useState("");
  const [suggestions, setSuggestions] = useState<DistributionSuggestion[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [applying, setApplying] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState("");
  const update = useUpdatePileItem();

  const pileMap = new Map(items?.map((i) => [i.id, i.content]) ?? []);

  function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    create.mutate(text.trim());
    setText("");
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      handleAdd(e);
    }
  }

  function startEdit(id: string, content: string) {
    setEditingId(id);
    setEditingText(content);
  }

  function saveEdit(id: string) {
    if (editingText.trim() && editingText !== items?.find((i) => i.id === id)?.content) {
      update.mutate({ id, content: editingText.trim() });
    }
    setEditingId(null);
  }

  function handleEditKeyDown(e: React.KeyboardEvent, id: string) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      saveEdit(id);
    }
    if (e.key === "Escape") setEditingId(null);
  }

  async function handleDistribute() {
    try {
      const result = await distribute.mutateAsync(undefined);
      if (result.suggestions.length > 0) {
        setSuggestions(result.suggestions);
        setModalOpen(true);
      }
    } catch (e: any) {
      alert(e?.response?.data?.detail || "ИИ временно недоступен");
    }
  }

  async function handleApply(selected: DistributionSuggestion[]) {
    setApplying(true);
    try {
      await applyDistribution.mutateAsync(
        selected.map((s) => ({
          pile_item_id: s.pile_item_id,
          target_week_id: s.target_week_id,
          as_mark: s.as_mark,
          title: s.title,
          theme_id: s.theme_id,
          day_of_week: s.day_of_week,
        }))
      );
      setModalOpen(false);
      setSuggestions([]);
    } catch {
      alert("Ошибка применения");
    } finally {
      setApplying(false);
    }
  }

  return (
    <div className="min-h-full bg-[#F0F2F7]">
      <NavBar>
        <span className="text-lg font-bold text-gray-900">Куча</span>
      </NavBar>
      <div className="max-w-2xl mx-auto p-6">
      {items && items.length > 0 && (
        <div className="mb-4 text-sm text-muted-foreground">{items.length} записей</div>
      )}

      <form onSubmit={handleAdd} className="mb-6">
        <div className="rounded-xl border bg-white overflow-hidden focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary/40 transition-all">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Запишите мысль, идею или задачу — любым форматом..."
            rows={3}
            className="w-full px-4 pt-3 pb-1 text-sm bg-transparent outline-none resize-none"
          />
          <div className="flex items-center justify-between px-3 pb-2">
            <span className="text-[10px] text-muted-foreground">Ctrl+Enter — добавить</span>
            <Button type="submit" size="sm" disabled={!text.trim()}>
              Добавить
            </Button>
          </div>
        </div>
      </form>

      {isLoading ? (
        <Spinner />
      ) : items && items.length > 0 ? (
        <>
          <div className="flex flex-col gap-2">
            {items.map((item) => (
              <div
                key={item.id}
                className="group rounded-xl border px-4 py-3 hover:border-gray-300 hover:shadow-sm transition-all"
              >
                <div className="flex items-start gap-2">
                  {editingId === item.id ? (
                    <textarea
                      autoFocus
                      value={editingText}
                      onChange={(e) => setEditingText(e.target.value)}
                      onKeyDown={(e) => handleEditKeyDown(e, item.id)}
                      onBlur={() => saveEdit(item.id)}
                      rows={2}
                      className="flex-1 text-sm leading-relaxed resize-none border border-blue-300 rounded-lg px-2 py-1 outline-none focus:ring-1 focus:ring-blue-400"
                    />
                  ) : (
                    <p
                      className="flex-1 text-sm leading-relaxed cursor-text"
                      onClick={() => startEdit(item.id, item.content)}
                      title="Нажмите для редактирования"
                    >
                      {item.content}
                    </p>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="opacity-0 group-hover:opacity-100 h-6 px-1 text-muted-foreground hover:text-destructive"
                    onClick={() => remove.mutate(item.id)}
                  >
                    ×
                  </Button>
                </div>
                <div className="mt-1.5 text-[10px] text-muted-foreground">
                  {new Date(item.created_at).toLocaleDateString("ru-RU", {
                    day: "numeric", month: "short",
                  })}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6">
            <Button
              onClick={handleDistribute}
              disabled={distribute.isPending}
              className="w-full"
            >
              {distribute.isPending ? "ИИ анализирует..." : "Распределить по плану"}
            </Button>
            <p className="text-[10px] text-muted-foreground text-center mt-2">
              ИИ проанализирует Кучу и предложит распределение
            </p>
          </div>
        </>
      ) : (
        <div className="text-center py-16">
          <p className="text-muted-foreground text-sm">Куча пуста</p>
          <p className="text-xs text-muted-foreground mt-1">Добавьте любую мысль — без структуры</p>
        </div>
      )}

      <DistributionProposal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        suggestions={suggestions}
        pileMap={pileMap}
        onApply={handleApply}
        applying={applying}
      />
      </div>
    </div>
  );
}
