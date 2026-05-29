import { useSettings, useUpdateSettings, useThemes } from "@/hooks/useApi";
import { Spinner } from "@/components/ui/spinner";
import { Input } from "@/components/ui/input";
import NavBar from "@/components/NavBar";

export default function SettingsPage() {
  const { data: settings, isLoading } = useSettings();
  const update = useUpdateSettings();

  if (isLoading) return <Spinner />;
  if (!settings) return null;

  return (
    <div className="min-h-full bg-[#F0F2F7]">
      <NavBar>
        <span className="text-lg font-bold text-gray-900">Настройки</span>
      </NavBar>

      <div className="max-w-xl mx-auto p-6">
        <section className="mb-8">
          <h2 className="text-sm font-semibold text-muted-foreground mb-3">Нагрузка</h2>
          <div className="flex items-center gap-3">
            <label className="text-sm">Бюджет задач на неделю:</label>
            <Input
              type="number"
              className="w-20 h-8 text-sm"
              defaultValue={settings.week_budget}
              onBlur={(e) => {
                const v = parseInt(e.target.value);
                if (v > 0 && v !== settings.week_budget) {
                  update.mutate({ week_budget: v });
                }
              }}
            />
          </div>
        </section>

        <section className="mb-8">
          <h2 className="text-sm font-semibold text-muted-foreground mb-3">Темы</h2>
          <ThemesList />
        </section>
      </div>
    </div>
  );
}

function ThemesList() {
  const { data: themes, isLoading } = useThemes();
  if (isLoading) return <Spinner />;
  if (!themes) return null;

  return (
    <div className="flex flex-col gap-2">
      {themes.map((t) => (
        <div key={t.id} className="flex items-center gap-3 rounded-md border px-3 py-2">
          <div className="w-4 h-4 rounded-full flex-shrink-0" style={{ backgroundColor: t.color }} />
          <span className="flex-1 text-sm">{t.name}</span>
          <span className="text-xs text-muted-foreground">{t.color}</span>
        </div>
      ))}
    </div>
  );
}
