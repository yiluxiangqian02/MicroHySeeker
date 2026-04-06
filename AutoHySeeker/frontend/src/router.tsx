import { Navigate, createBrowserRouter } from "react-router-dom";
import { AppShell } from "@/components/AppShell";
import { RouteErrorPage } from "@/components/RouteErrorPage";
import { Dashboard } from "@/pages/Dashboard";
import { Experiments } from "@/pages/Experiments";
import { ExperimentDetail } from "@/pages/ExperimentDetail";
import { Overview } from "@/pages/Overview";
import { Settings } from "@/pages/Settings";
import { AgentControl } from "@/pages/AgentControl";
import { Templates } from "@/pages/Templates";
import { KnowledgeHub } from "@/pages/KnowledgeHub";
import { Optimization } from "@/pages/Optimization";
import { Chat } from "@/pages/Chat";
import { Diagnostics } from "@/pages/Diagnostics";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <Overview />, errorElement: <RouteErrorPage /> },
      { path: "dashboard", element: <Dashboard />, errorElement: <RouteErrorPage /> },
      { path: "experiments", element: <Experiments />, errorElement: <RouteErrorPage /> },
      { path: "optimization", element: <Optimization />, errorElement: <RouteErrorPage /> },
      { path: "chat", element: <Chat />, errorElement: <RouteErrorPage /> },
      { path: "diagnostics", element: <Diagnostics />, errorElement: <RouteErrorPage /> },
      { path: "agents", element: <AgentControl />, errorElement: <RouteErrorPage /> },
      { path: "knowledge", element: <KnowledgeHub />, errorElement: <RouteErrorPage /> },
      { path: "templates", element: <Templates />, errorElement: <RouteErrorPage /> },
      { path: "settings", element: <Settings />, errorElement: <RouteErrorPage /> },
      { path: "experiments/:id", element: <ExperimentDetail />, errorElement: <RouteErrorPage /> },
      { path: "*", element: <Navigate to="/" replace /> }
    ]
  }
]);

