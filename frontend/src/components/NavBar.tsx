import { Link, useLocation, useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { authApi } from "@/api";

const CURRENT_YEAR = new Date().getFullYear();

export default function NavBar({ children }: { children?: React.ReactNode }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();

  async function handleLogout() {
    try { await authApi.logout(); } catch {}
    navigate("/login", { replace: true });
  }

  return (
    <div className="sticky top-0 z-20 bg-white/95 backdrop-blur border-b border-gray-200 px-6 py-3">
      <div className="flex items-center gap-4">
        <Link to={`/year/${CURRENT_YEAR}`} className="flex items-center gap-2 flex-shrink-0">
          <div className="w-7 h-7 bg-primary rounded-lg flex items-center justify-center">
            <span className="text-primary-foreground text-[11px] font-bold">52</span>
          </div>
        </Link>

        <nav className="flex items-center gap-1 flex-shrink-0">
          <NavLink to={`/year/${CURRENT_YEAR}`} label="Год" active={pathname.startsWith("/year")} />
          <NavLink to="/pile" label="Куча" active={pathname === "/pile"} />
          <NavLink to="/chat" label="Чат" active={pathname === "/chat"} />
          <NavLink to="/settings" label="Настройки" active={pathname === "/settings"} />
        </nav>

        {children && (
          <>
            <div className="h-5 w-px bg-gray-200" />
            {children}
          </>
        )}

        <div className="ml-auto">
          <button
            onClick={handleLogout}
            className="text-sm px-3 py-1.5 rounded-lg text-muted-foreground hover:bg-red-50 hover:text-red-500 transition-colors"
          >
            Выйти
          </button>
        </div>
      </div>
    </div>
  );
}

function NavLink({ to, label, active }: { to: string; label: string; active: boolean }) {
  return (
    <Link
      to={to}
      className={cn(
        "text-sm px-3 py-1.5 rounded-lg transition-colors",
        active ? "bg-primary/10 text-primary font-medium" : "text-muted-foreground hover:bg-accent"
      )}
    >
      {label}
    </Link>
  );
}
