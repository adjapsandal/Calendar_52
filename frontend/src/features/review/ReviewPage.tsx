import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useReviewStart, useReviewReflect, useReviewComplete } from "@/hooks/useApi";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import NavBar from "@/components/NavBar";
import { cn } from "@/lib/utils";
import type { ReviewStartResponse, ReviewReflectResponse } from "@/api";

const STATUS_CYCLE = ["todo", "done", "cancelled"] as const;
const STATUS_LABELS: Record<string, string> = { todo: "Не сделано", done: "Сделано", cancelled: "Отменено" };

export default function ReviewPage() {
  const { weekId } = useParams<{ weekId: string }>();
  const navigate = useNavigate();

  const startReview = useReviewStart();
  const reflectReview = useReviewReflect();
  const completeReview = useReviewComplete();

  const [step, setStep] = useState(0);
  const [reviewData, setReviewData] = useState<ReviewStartResponse | null>(null);
  const [taskStatuses, setTaskStatuses] = useState<Map<string, string>>(new Map());
  const [rawInput, setRawInput] = useState("");
  const [aiResult, setAiResult] = useState<ReviewReflectResponse | null>(null);

  async function handleStart() {
    if (!weekId) return;
    try {
      const data = await startReview.mutateAsync(weekId);
      setReviewData(data);
      const map = new Map<string, string>();
      data.tasks.forEach((t) => map.set(t.id, t.status));
      setTaskStatuses(map);
      setStep(1);
    } catch {
      alert("Ошибка запуска ритуала");
    }
  }

  function cycleStatus(taskId: string) {
    setTaskStatuses((prev) => {
      const next = new Map(prev);
      const cur = next.get(taskId) ?? "todo";
      const idx = STATUS_CYCLE.indexOf(cur as any);
      next.set(taskId, STATUS_CYCLE[(idx + 1) % 3]);
      return next;
    });
  }

  async function handleReflect() {
    if (!weekId) return;
    try {
      const result = await reflectReview.mutateAsync({
        weekId,
        data: {
          task_statuses: Array.from(taskStatuses.entries()).map(([id, status]) => ({ id, status })),
          raw_input: rawInput || undefined,
        },
      });
      setAiResult(result);
      setStep(3);
    } catch {
      alert("Ошибка ИИ-рефлексии");
    }
  }

  async function handleComplete() {
    if (!weekId) return;
    try {
      await completeReview.mutateAsync(weekId);
      navigate(`/year/${new Date().getFullYear()}`);
    } catch {
      alert("Ошибка завершения");
    }
  }

  if (step === 0) {
    return (
      <div className="min-h-full bg-[#F0F2F7]">
        <NavBar>
          <Link to={`/week/${weekId}`} className="text-gray-400 hover:text-gray-600 transition-colors text-lg">
            ←
          </Link>
          <span className="text-lg font-bold text-gray-900">Ритуал закрытия</span>
        </NavBar>
        <div className="max-w-lg mx-auto p-6 text-center">
        <h1 className="text-xl font-bold mb-3">Ритуал закрытия недели</h1>
        <p className="text-sm text-muted-foreground mb-6">
          4 шага: статусы задач → рефлексия → ИИ-сводка → хвосты
        </p>
        <Button onClick={handleStart} disabled={startReview.isPending}>
          {startReview.isPending ? "Загрузка..." : "Начать"}
        </Button>
      </div>
      </div>
    );
  }

  if (!reviewData) return <Spinner />;

  const steps = ["Статусы", "Рефлексия", "ИИ-сводка", "Хвосты"];

  return (
    <div className="max-w-lg mx-auto p-6">
      <div className="flex gap-1 mb-6">
        {steps.map((label, i) => (
          <div
            key={i}
            className={cn(
              "flex-1 text-center text-[10px] py-1 rounded transition-colors",
              i + 1 <= step ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
            )}
          >
            {label}
          </div>
        ))}
      </div>

      <h2 className="text-lg font-bold mb-4">Неделя {reviewData.display_position}</h2>

      {step === 1 && (
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground mb-3">
            Отметьте статус каждой задачи
          </h3>
          <div className="flex flex-col gap-1.5 mb-6">
            {reviewData.tasks.map((t) => (
              <div key={t.id} className="flex items-center gap-3 rounded-md border px-3 py-2">
                <span className="flex-1 text-sm">{t.title}</span>
                <button
                  onClick={() => cycleStatus(t.id)}
                  className={cn(
                    "text-xs px-2 py-0.5 rounded-full border",
                    taskStatuses.get(t.id) === "done" && "bg-green-100 text-green-700 border-green-300",
                    taskStatuses.get(t.id) === "cancelled" && "bg-red-50 text-red-500 border-red-200",
                    taskStatuses.get(t.id) === "todo" && "bg-gray-100 text-gray-500 border-gray-200",
                  )}
                >
                  {STATUS_LABELS[taskStatuses.get(t.id) ?? "todo"]}
                </button>
              </div>
            ))}
          </div>
          <Button onClick={() => setStep(2)}>Далее</Button>
        </div>
      )}

      {step === 2 && (
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground mb-3">
            Что получилось? Что не вышло?
          </h3>
          <textarea
            value={rawInput}
            onChange={(e) => setRawInput(e.target.value)}
            placeholder="Напишите рефлексию (можно пропустить)..."
            rows={5}
            className="w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/20 mb-4 resize-none"
          />
          <div className="flex gap-2">
            <Button variant="ghost" onClick={() => setStep(1)}>Назад</Button>
            <Button onClick={handleReflect} disabled={reflectReview.isPending}>
              {reflectReview.isPending ? "ИИ анализирует..." : "Получить ИИ-сводку"}
            </Button>
            <Button variant="ghost" onClick={handleComplete} disabled={completeReview.isPending}>
              Пропустить ИИ
            </Button>
          </div>
        </div>
      )}

      {step === 3 && aiResult && (
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground mb-3">ИИ-сводка</h3>

          <div className="space-y-3 mb-6">
            <div className="rounded-lg border p-3">
              <h4 className="text-xs font-semibold text-muted-foreground mb-1">Достижения</h4>
              <p className="text-sm">{aiResult.achievements}</p>
            </div>
            <div className="rounded-lg border p-3">
              <h4 className="text-xs font-semibold text-muted-foreground mb-1">Уроки</h4>
              <p className="text-sm">{aiResult.lessons}</p>
            </div>
            <div className="rounded-lg border p-3">
              <h4 className="text-xs font-semibold text-muted-foreground mb-1">Корректировки</h4>
              <p className="text-sm">{aiResult.corrections}</p>
            </div>
          </div>

          {aiResult.tails.length > 0 && (
            <div className="mb-6">
              <h4 className="text-xs font-semibold text-muted-foreground mb-2">Незакрытые задачи</h4>
              {aiResult.tails.map((tail) => {
                const task = reviewData.tasks.find((t) => t.id === tail.task_id);
                return (
                  <div key={tail.task_id} className="text-xs text-muted-foreground mb-1">
                    {task?.title ?? "..."} → {tail.suggested_action === "carry_over" ? "перенести" : "удалить"}
                  </div>
                );
              })}
            </div>
          )}

          <Button onClick={handleComplete} disabled={completeReview.isPending}>
            {completeReview.isPending ? "Завершаем..." : "Закрыть неделю"}
          </Button>
        </div>
      )}
    </div>
  );
}
