import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { authApi } from "@/api";

export default function AppLayout() {
  useLocation();
  const navigate = useNavigate();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    authApi.getMe().then(() => {
      setChecked(true);
    }).catch(() => {
      navigate("/login", { replace: true });
    });
  }, []);

  if (!checked) return null;

  return (
    <div className="h-screen flex flex-col bg-background">
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
