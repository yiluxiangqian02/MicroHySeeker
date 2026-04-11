import { useEffect } from "react";
import { RouterProvider } from "react-router-dom";
import { router } from "@/router";
import { useSystemConfigStore } from "@/stores/systemConfigStore";

export default function App() {
  const init = useSystemConfigStore((s) => s.init);
  useEffect(() => { init(); }, [init]);
  return <RouterProvider router={router} />;
}

