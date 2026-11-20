import React from "react";
import { Check, Clock3, LayoutDashboard, Moon, PackageCheck, Sun } from "lucide-react";

export type InspectorSection = "dashboard" | "new" | "history" | "inspection";
export type ThemeMode = "light" | "dark";

interface InspectorLayoutProps {
  active: InspectorSection;
  onNavigate: (section: InspectorSection) => void;
  health: "online" | "offline" | "checking";
  theme: ThemeMode;
  onToggleTheme: () => void;
  children: React.ReactNode;
}

const navigation: { id: InspectorSection; label: string; icon: React.ElementType }[] = [
  { id: "dashboard", label: "Overview", icon: LayoutDashboard },
  { id: "new", label: "Check a pack", icon: PackageCheck },
  { id: "history", label: "Inspection history", icon: Clock3 },
];

export const InspectorLayout: React.FC<InspectorLayoutProps> = ({ active, onNavigate, health, theme, onToggleTheme, children }) => (
  <div className="inspector-app min-h-screen text-ink">
    <aside className="inspector-sidebar fixed inset-y-0 left-0 z-40 flex w-16 flex-col justify-between border-r md:w-60" aria-label="Primary navigation">
      <div>
        <div className="px-3 pb-5 pt-5 md:px-5">
          <div className="mb-5 flex items-center justify-center gap-2.5 md:justify-start">
            <div className="inspector-brand-mark flex h-7 w-7 shrink-0 items-center justify-center rounded-md shadow-sm"><Check aria-hidden="true" className="h-4 w-4" strokeWidth={2.5} /></div>
            <span className="hidden text-[17px] font-bold tracking-tight md:inline">LabelIntel</span>
          </div>
          <div className="hidden pl-0.5 md:block">
            <p className="text-[12px] font-semibold leading-snug text-ink">Packaged commodity inspection</p>
            <p className="mt-0.5 text-[11px] text-muted">Local review workspace</p>
          </div>
          <div title={`API ${health}`} className="mt-4 flex items-center justify-center gap-2 rounded-md px-2 py-1.5 text-[10px] text-muted md:justify-start md:px-0">
            <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${health === "online" ? "bg-emerald-600 dark:bg-emerald-400" : health === "offline" ? "bg-rose-600 dark:bg-rose-400" : "bg-amber-500"}`} />
            <span className="hidden md:inline">API {health === "online" ? "connected" : health === "offline" ? "unavailable" : "connecting"}</span>
          </div>
        </div>

        <nav className="space-y-1 px-2 md:px-3" aria-label="Workspace">
          {navigation.map(({ id, label, icon: Icon }) => {
            const selected = active === id || (active === "inspection" && id === "new");
            return <button key={id} type="button" title={label} aria-label={label} onClick={() => onNavigate(id)} aria-current={selected ? "page" : undefined}
              className={`inspector-nav-item flex min-h-10 w-full items-center justify-center gap-3 rounded-sm px-2 py-2 text-left text-[13px] transition-colors md:justify-start md:px-3 ${selected ? "inspector-nav-active font-medium" : "text-muted hover:bg-[rgb(var(--sidebar-hover-rgb))] hover:text-ink"}`}>
              <Icon aria-hidden="true" className="h-4 w-4 shrink-0" /><span className="hidden md:inline">{label}</span>
            </button>;
          })}
        </nav>
      </div>

      <div className="inspector-sidebar-footer space-y-3 border-t p-3 md:p-4">
        <button type="button" onClick={onToggleTheme} aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`} title={`Theme: ${theme}`} className="flex min-h-9 w-full items-center justify-center gap-2 rounded-md px-2 text-[12px] text-muted transition-colors hover:bg-[rgb(var(--sidebar-hover-rgb))] hover:text-ink md:justify-start">
          {theme === "light" ? <Moon aria-hidden="true" className="h-4 w-4 shrink-0" /> : <Sun aria-hidden="true" className="h-4 w-4 shrink-0" />}
          <span className="hidden md:inline">Theme: {theme}</span>
        </button>
        <div className="flex items-center justify-center gap-2.5 border-t border-line pt-3 md:justify-start">
          <div className="inspector-avatar flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold">LI</div>
          <div className="hidden min-w-0 md:block"><p className="truncate text-[12px] font-semibold leading-tight text-ink">Inspection workspace</p><p className="mt-0.5 text-[11px] text-muted">Local session</p></div>
        </div>
      </div>
    </aside>

    <main className="inspector-canvas min-h-screen pl-16 md:pl-60">{children}</main>
  </div>
);
