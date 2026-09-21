import { AxiosError } from "axios";

/** Текст ошибки из поля `detail` ответа FastAPI, если он там есть. */
export function apiErrorDetail(error: unknown): string | undefined {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return undefined;
}

/** Текст ошибки для показа пользователю: `detail` или переданная заглушка. */
export function apiErrorMessage(error: unknown, fallback: string): string {
  return apiErrorDetail(error) ?? fallback;
}
