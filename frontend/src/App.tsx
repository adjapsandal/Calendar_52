import { Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "./AppLayout";
import YearGrid from "@/features/year/YearGrid";
import WeekView from "@/features/week/WeekView";
import DayView from "@/features/day/DayView";
import LoginPage from "@/features/auth/LoginPage";
import SettingsPage from "@/features/settings/SettingsPage";
import PilePage from "@/features/pile/PilePage";
import ReviewPage from "@/features/review/ReviewPage";
import ChatPage from "@/features/chat/ChatPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AppLayout />}>
        <Route path="/" element={<Navigate to={`/year/${new Date().getFullYear()}`} replace />} />
        <Route path="/year/:year" element={<YearGrid />} />
        <Route path="/week/:weekId" element={<WeekView />} />
        <Route path="/week/:weekId/day/:day" element={<DayView />} />
        <Route path="/review/:weekId" element={<ReviewPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/pile" element={<PilePage />} />
        <Route path="/chat" element={<ChatPage />} />
      </Route>
    </Routes>
  );
}
