import { Navigate, createBrowserRouter } from "react-router-dom";
import { AppShell } from "@/components/AppShell";
import { Dashboard } from "@/pages/Dashboard";
import { ExperimentDetail } from "@/pages/ExperimentDetail";
import { Overview } from "@/pages/Overview";
import { Settings } from "@/pages/Settings";
import { AgentControl } from "@/pages/AgentControl";
import { Templates } from "@/pages/Templates";
import { KnowledgeHub } from "@/pages/KnowledgeHub";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <Overview /> },
      { path: "dashboard", element: <Dashboard /> },
      { path: "agents", element: <AgentControl /> },
      { path: "knowledge", element: <KnowledgeHub /> },
      { path: "templates", element: <Templates /> },
      { path: "settings", element: <Settings /> },
      { path: "experiments/:id", element: <ExperimentDetail /> },
      { path: "*", element: <Navigate to="/" replace /> }
    ]
  }
]);

