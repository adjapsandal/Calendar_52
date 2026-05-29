import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "@/api";
import { useOnboardingStore } from "@/store/onboarding";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function LoginPage() {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const startOnboarding = useOnboardingStore((s) => s.startOnboarding);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      if (isRegister) {
        try {
          await authApi.register(email, password);
        } catch (regErr: any) {
          const detail = regErr?.response?.data?.detail;
          if (detail === "REGISTER_USER_ALREADY_EXISTS") {
            setError("Пользователь с таким email уже существует");
          } else {
            setError("Ошибка регистрации");
          }
          return;
        }
        await authApi.login(email, password);
        startOnboarding();
        navigate("/year/2026");
      } else {
        await authApi.login(email, password);
        navigate("/year/2026");
      }
    } catch {
      setError(isRegister ? "Ошибка регистрации" : "Неверный email или пароль");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-center">Календарь 52</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <Input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <Input
              type="password"
              placeholder="Пароль"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
            />
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit">{isRegister ? "Зарегистрироваться" : "Войти"}</Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => { setIsRegister(!isRegister); setError(""); }}
            >
              {isRegister ? "Уже есть аккаунт — Войти" : "Нет аккаунта — Регистрация"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
