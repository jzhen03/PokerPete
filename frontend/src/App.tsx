import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, unwrap } from "./api/client";
import { EquityPanel } from "./components/EquityPanel/EquityPanel";
import { RangeExplorer } from "./components/RangeExplorer/RangeExplorer";
import { Trainer } from "./components/Trainer/Trainer";

const TABS = [
  { id: "ranges", label: "Range Explorer" },
  { id: "equity", label: "Equity" },
  { id: "trainer", label: "Push/Fold Trainer" },
] as const;

type TabId = (typeof TABS)[number]["id"];

function App() {
  const [tab, setTab] = useState<TabId>("ranges");

  const health = useQuery({
    queryKey: ["health"],
    queryFn: async () => unwrap(await api.GET("/health")),
  });

  return (
    <main className="app">
      <div className="app-header">
        <h1>PokerPete</h1>
        <span className="backend-status">
          backend: {health.isLoading ? "checking…" : health.isError ? "unreachable" : "ok"}
        </span>
      </div>

      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            className="tab"
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "ranges" && <RangeExplorer />}
      {tab === "equity" && <EquityPanel />}
      {tab === "trainer" && <Trainer />}
    </main>
  );
}

export default App;
