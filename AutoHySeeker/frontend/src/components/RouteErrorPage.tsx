import { useRouteError, useNavigate } from "react-router-dom";
import { AlertCircle, ArrowLeft, RefreshCw } from "lucide-react";

export function RouteErrorPage() {
  const error = useRouteError() as Error | { status?: number; statusText?: string; message?: string };
  const navigate = useNavigate();

  const message =
    error instanceof Error
      ? error.message
      : (error as any)?.statusText ?? (error as any)?.message ?? "页面加载出错";

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-6 p-8">
      <AlertCircle className="h-16 w-16 text-red-400" />
      <h1 className="text-2xl font-bold text-slate-900">页面出错了</h1>
      <p className="max-w-lg text-center text-sm leading-6 text-slate-600">{message}</p>
      <div className="flex gap-3">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
        >
          <ArrowLeft className="h-4 w-4" />
          返回上页
        </button>
        <button
          onClick={() => window.location.reload()}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700"
        >
          <RefreshCw className="h-4 w-4" />
          刷新页面
        </button>
      </div>
    </div>
  );
}
