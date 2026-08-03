import { BarChart3, ScanFace, ShieldCheck, Sparkles } from "lucide-react";

export type AppView = "console" | "analytics";

interface AppHeaderProps {
  currentView: AppView;
  onNavigate: (view: AppView) => void;
}

export function AppHeader({ currentView, onNavigate }: AppHeaderProps) {
  const views: Array<{
    id: AppView;
    label: string;
    icon: typeof ScanFace;
  }> = [
    { id: "console", label: "Console", icon: ScanFace },
    { id: "analytics", label: "Analytics", icon: BarChart3 },
  ];

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 py-3">
      <div className="flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-2xl bg-ink text-lime">
          <Sparkles className="h-5 w-5" />
        </div>
        <div>
          <p className="font-display text-lg font-bold leading-none text-ink">
            VirtualPresence
          </p>
          <p className="mt-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-fern">
            Recognition platform
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <nav
          className="flex rounded-full border border-ink/8 bg-white/70 p-1 shadow-sm backdrop-blur"
          aria-label="Primary navigation"
        >
          {views.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => onNavigate(id)}
              aria-current={currentView === id ? "page" : undefined}
              className={`flex items-center gap-2 rounded-full px-3.5 py-2 text-xs font-semibold transition sm:px-4 ${
                currentView === id
                  ? "bg-ink text-white shadow-sm"
                  : "text-ink/50 hover:text-ink"
              }`}
            >
              <Icon
                className={`h-3.5 w-3.5 ${
                  currentView === id ? "text-lime" : ""
                }`}
              />
              {label}
            </button>
          ))}
        </nav>
        <span className="hidden items-center gap-2 rounded-full border border-ink/10 bg-white/60 px-4 py-2 text-xs font-medium text-ink/60 lg:flex">
          <ShieldCheck className="h-4 w-4 text-fern" />
          Local analytics
        </span>
      </div>
    </header>
  );
}
