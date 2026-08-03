import { lazy, Suspense, useState } from "react";

import type { AppView } from "./components/AppHeader";
import { FaceConsolePage } from "./pages/FaceConsolePage";

const AnalyticsPage = lazy(() =>
  import("./pages/AnalyticsPage").then((module) => ({
    default: module.AnalyticsPage,
  })),
);

export default function App() {
  const [view, setView] = useState<AppView>("console");

  return view === "analytics" ? (
    <Suspense
      fallback={
        <main className="grid min-h-screen place-items-center text-sm text-ink/45">
          Loading analytics…
        </main>
      }
    >
      <AnalyticsPage onNavigate={setView} />
    </Suspense>
  ) : (
    <FaceConsolePage onNavigate={setView} />
  );
}

