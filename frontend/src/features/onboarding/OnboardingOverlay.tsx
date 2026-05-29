import { useOnboardingStore } from "@/store/onboarding";
import { authApi } from "@/api";
import { useNavigate } from "react-router-dom";

export default function OnboardingOverlay() {
  const { step, next, finish } = useOnboardingStore();
  const navigate = useNavigate();

  async function handleFinish() {
    try {
      await authApi.patchMe({ onboarded: true });
    } catch {}
    finish();
  }

  if (step === 0) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-card rounded-2xl shadow-xl p-8 max-w-md w-full mx-4">
        {step === 1 && (
          <>
            <h2 className="text-lg font-bold mb-3">Добро пожаловать!</h2>
            <p className="text-sm text-muted-foreground mb-6">
              Это твой год. Здесь ты видишь все 52 недели сразу — четыре квартала,
              каждая клетка — одна неделя. Кликни на любую, чтобы планировать.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => handleFinish()}
                className="text-sm text-muted-foreground hover:text-foreground px-3 py-1.5"
              >
                Пропустить
              </button>
              <button
                onClick={next}
                className="text-sm bg-primary text-primary-foreground px-4 py-1.5 rounded-md hover:bg-primary/90"
              >
                Далее
              </button>
            </div>
          </>
        )}
        {step === 2 && (
          <>
            <h2 className="text-lg font-bold mb-3">Куча</h2>
            <p className="text-sm text-muted-foreground mb-6">
              Сюда сбрасывай любые мысли, идеи и задачи — любым форматом.
              ИИ потом разложит их по неделям.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => handleFinish()}
                className="text-sm text-muted-foreground hover:text-foreground px-3 py-1.5"
              >
                Пропустить
              </button>
              <button
                onClick={() => {
                  handleFinish();
                  navigate("/pile");
                }}
                className="text-sm bg-primary text-primary-foreground px-4 py-1.5 rounded-md hover:bg-primary/90"
              >
                Готово
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
