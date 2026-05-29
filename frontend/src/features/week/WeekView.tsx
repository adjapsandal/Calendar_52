import { useParams, Link } from "react-router-dom";
import { useWeek, useSettings } from "@/hooks/useApi";
import { Spinner } from "@/components/ui/spinner";
import MarksColumn from "./MarksColumn";
import DaysStrip from "./DaysStrip";
import NavBar from "@/components/NavBar";
import { Button } from "@/components/ui/button";

export default function WeekView() {
  const { weekId } = useParams<{ weekId: string }>();
  const { data, isLoading, error } = useWeek(weekId);
  const { data: settings } = useSettings();

  if (isLoading) return <Spinner />;
  if (error) return <div className="p-8 text-destructive">Ошибка загрузки</div>;
  if (!data) return null;

  const budget = settings?.week_budget ?? 10;
  const overloaded = data.cached_load > budget;
  const doneTasks = data.week_tasks.filter((t) => t.status === "done").length;
  const totalTasks = data.week_tasks.length;
  const progressPct = totalTasks > 0 ? Math.round((doneTasks / totalTasks) * 100) : 0;

  return (
    <div className="min-h-full flex flex-col bg-[#F0F2F7]">
      <NavBar>
        <Link to={`/year/${data.year_number}`} className="text-gray-400 hover:text-gray-600 transition-colors text-lg">
          ←
        </Link>
        <span className="text-lg font-bold text-gray-900">Неделя {data.display_position}</span>
        <span className="text-sm text-gray-500">Q{Math.ceil(data.display_position / 13)}</span>
        {data.is_rest_week && (
          <span className="text-xs font-semibold px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full">
            Отдых
          </span>
        )}
        <span className={`text-xs ${overloaded ? "text-rose-600 font-medium" : "text-gray-500"}`}>
          Нагрузка: {data.cached_load}/{budget}
        </span>
        {overloaded && (
          <span className="text-[11px] text-rose-600 bg-rose-50 px-2 py-0.5 rounded-full">
            Бюджет превышён
          </span>
        )}

        <div className="flex-1" />

        {totalTasks > 0 && (
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-500">{doneTasks} из {totalTasks}</span>
            <div className="w-24 h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>
        )}
        <Link to={`/review/${data.id}`}>
          <Button variant="outline" size="sm">Закрыть неделю</Button>
        </Link>
      </NavBar>

      {/* Content: sidebar + diary */}
      <div className="flex-1 px-6 py-4">
        <div className="max-w-6xl mx-auto flex gap-6">
          <div className="w-[300px] shrink-0">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <MarksColumn weekId={data.id} marks={data.marks} tasks={data.week_tasks} year={data.year_number} />
            </div>
          </div>

          <div className="flex-1">
            <DaysStrip weekId={data.id} dayTasks={data.day_tasks} year={data.year_number} isoWeek={data.iso_week} yearNumber={data.year_number} marks={data.marks} weekTasks={data.week_tasks} />
          </div>
        </div>
      </div>
    </div>
  );
}
