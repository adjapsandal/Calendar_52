import { useState, useRef, useEffect } from "react";
import NavBar from "@/components/NavBar";
import { Button } from "@/components/ui/button";
import { chatApi, weekTaskApi, dayTaskApi, markApi, type ChatMessage, type DistributionSuggestion } from "@/api";
import DistributionProposal from "@/features/pile/DistributionProposal";

interface Message {
  role: "user" | "assistant";
  content: string;
  suggestions?: DistributionSuggestion[];
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Привет! Я помогу тебе с планированием. Можешь спросить о стратегии на неделю, попросить совета или попросить перенести задачи." },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [modalSuggestions, setModalSuggestions] = useState<DistributionSuggestion[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [applying, setApplying] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send() {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");

    const userMsg: Message = { role: "user", content: text };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setLoading(true);

    try {
      const apiMessages: ChatMessage[] = nextMessages
        .filter((m) => m.role === "user" || m.role === "assistant")
        .map((m) => ({ role: m.role, content: m.content }));

      const { data } = await chatApi.send(apiMessages);
      const assistantMsg: Message = {
        role: "assistant",
        content: data.reply,
        suggestions: data.suggestions,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Извини, произошла ошибка. Попробуй ещё раз." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  function openSuggestions(suggestions: DistributionSuggestion[]) {
    setModalSuggestions(suggestions);
    setModalOpen(true);
  }

  async function handleApply(selected: DistributionSuggestion[]) {
    setApplying(true);
    try {
      await Promise.all(
        selected.map((s) => {
          if (s.item_type === "mark") return markApi.move(s.pile_item_id, s.target_week_id);
          if (s.item_type === "day_task") return dayTaskApi.move(s.pile_item_id, s.target_week_id);
          return weekTaskApi.move(s.pile_item_id, s.target_week_id);
        })
      );
      setModalOpen(false);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Готово! Задачи перенесены." },
      ]);
    } catch {
      alert("Ошибка при переносе задач");
    } finally {
      setApplying(false);
    }
  }

  return (
    <div className="min-h-full bg-[#F0F2F7] flex flex-col">
      <NavBar>
        <span className="text-lg font-bold text-gray-900">Чат с ИИ</span>
      </NavBar>

      <div className="flex-1 max-w-2xl w-full mx-auto flex flex-col px-4 py-4 gap-3">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                m.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-white border border-gray-200 text-gray-800"
              }`}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>
              {m.suggestions && m.suggestions.length > 0 && (
                <Button
                  size="sm"
                  variant="outline"
                  className="mt-2 text-xs"
                  onClick={() => openSuggestions(m.suggestions!)}
                >
                  Просмотреть предложения ({m.suggestions.length})
                </Button>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3 text-sm text-muted-foreground">
              <span className="animate-pulse">ИИ думает...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="sticky bottom-0 bg-[#F0F2F7] border-t border-gray-200 px-4 py-3">
        <div className="max-w-2xl mx-auto">
          <div className="rounded-xl border bg-white overflow-hidden focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary/40 transition-all">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Напиши вопрос или задачу... (Enter — отправить)"
              rows={2}
              className="w-full px-4 pt-3 pb-1 text-sm bg-transparent outline-none resize-none"
            />
            <div className="flex items-center justify-between px-3 pb-2">
              <span className="text-[10px] text-muted-foreground">Shift+Enter — перенос строки</span>
              <Button size="sm" onClick={send} disabled={!input.trim() || loading}>
                Отправить
              </Button>
            </div>
          </div>
        </div>
      </div>

      <DistributionProposal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        suggestions={modalSuggestions}
        pileMap={new Map(modalSuggestions.map((s) => [s.pile_item_id, s.title]))}
        onApply={handleApply}
        applying={applying}
      />
    </div>
  );
}
