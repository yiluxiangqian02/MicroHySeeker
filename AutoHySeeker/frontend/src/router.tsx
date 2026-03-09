import { Navigate, createBrowserRouter } from "react-router-dom";
import { AppShell } from "@/components/AppShell";
import { Dashboard } from "@/pages/Dashboard";
import { Overview } from "@/pages/Overview";
import { Settings } from "@/pages/Settings";
import { AgentControl } from "@/pages/AgentControl";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <Overview /> },
      { path: "dashboard", element: <Dashboard /> },
      { path: "agents", element: <AgentControl /> },
      { path: "settings", element: <Settings /> },
      { path: "*", element: <Navigate to="/" replace /> }
    ]
  }
]);


