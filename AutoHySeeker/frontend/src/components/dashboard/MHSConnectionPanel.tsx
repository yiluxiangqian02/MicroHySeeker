/**
 * MHS 连接控制面板 — 在 Dashboard MHS 横幅中展开：
 * 1. MHS 离线时：显示"启动 MHS"按钮
 * 2. MHS 在线但 RS485 未连接时：显示 COM 端口选择 + 连接按钮
 * 3. RS485 已连接时：显示端口信息 + 断开按钮
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSystemConfigStore } from "@/stores/systemConfigStore";
import {
  Power,
  Plug,
  Unplug,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Loader2,
} from "lucide-react";
import toast from "react-hot-toast";

export function MHSConnectionPanel() {
  const { t } = useTranslation();
  const {
    mhsStatus,
    fetchMHSStatus,
    fetchPorts,
    connectRS485,
    disconnectRS485,
    launchMHS,
  } = useSystemConfigStore();

  const [expanded, setExpanded] = useState(false);
  const [ports, setPorts] = useState<string[]>([]);
  const [preferredPort, setPreferredPort] = useState("");
  const [baudrate, setBaudrate] = useState(38400);
  const [selectedPort, setSelectedPort] = useState("");
  const [busy, setBusy] = useState(false);

  // Load ports when panel expands
  const refreshPorts = useCallback(async () => {
    const result = await fetchPorts();
    setPorts(result.ports);
    setPreferredPort(result.preferred_port);
    setBaudrate(result.baudrate);
    // Auto-select preferred port or first available
    if (result.preferred_port && result.ports.includes(result.preferred_port)) {
      setSelectedPort(result.preferred_port);
    } else if (result.ports.length > 0) {
      setSelectedPort(result.ports[0]);
    }
  }, [fetchPorts]);

  useEffect(() => {
    if (expanded && mhsStatus.online) {
      refreshPorts();
    }
  }, [expanded, mhsStatus.online, refreshPorts]);

  const handleLaunchMHS = async () => {
    setBusy(true);
    const ok = await launchMHS();
    setBusy(false);
    if (ok) {
      toast.success(t("dashboard.mhsPanel.launchSuccess"));
      refreshPorts();
    } else {
      toast.error(t("dashboard.mhsPanel.launchFailed"));
    }
  };

  const handleConnect = async () => {
    if (!selectedPort) return;
    setBusy(true);
    const ok = await connectRS485(selectedPort, baudrate);
    setBusy(false);
    if (ok) {
      toast.success(t("dashboard.mhsPanel.connectSuccess", { port: selectedPort }));
    } else {
      toast.error(t("dashboard.mhsPanel.connectFailed", { port: selectedPort }));
    }
  };

  const handleDisconnect = async () => {
    setBusy(true);
    const ok = await disconnectRS485();
    setBusy(false);
    if (ok) {
      toast.success(t("dashboard.mhsPanel.disconnected"));
    } else {
      toast.error(t("dashboard.mhsPanel.disconnectFailed"));
    }
  };

  return (
    <div>
      {/* Toggle bar */}
      <div
        className={`flex items-center gap-3 rounded-xl border px-4 py-2.5 text-sm shadow-sm cursor-pointer select-none transition ${
          mhsStatus.online
            ? mhsStatus.connected
              ? "border-green-200 bg-green-50 text-green-800 hover:bg-green-100"
              : "border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100"
            : "border-red-200 bg-red-50 text-red-800 hover:bg-red-100"
        }`}
        onClick={() => setExpanded((v) => !v)}
      >
        <span
          className={`inline-block h-2.5 w-2.5 rounded-full ${
            mhsStatus.online
              ? mhsStatus.connected
                ? "bg-green-500"
                : "bg-amber-500 animate-pulse"
              : "bg-red-500"
          }`}
        />
        <span className="font-medium">MHS</span>
        <span>
          {mhsStatus.online
            ? t("dashboard.mhsBanner.online")
            : t("dashboard.mhsBanner.offline")}
        </span>
        {mhsStatus.online && (
          <>
            <span className="text-slate-300">|</span>
            <span>
              RS485:{" "}
              {mhsStatus.connected
                ? t("dashboard.mhsBanner.connected")
                : t("dashboard.mhsBanner.disconnected")}
            </span>
            {mhsStatus.port && (
              <>
                <span className="text-slate-300">|</span>
                <span className="font-mono font-semibold">{mhsStatus.port}</span>
              </>
            )}
            {mhsStatus.mock_mode && (
              <>
                <span className="text-slate-300">|</span>
                <span className="rounded bg-amber-200 px-1.5 py-0.5 text-xs font-medium">
                  {t("dashboard.mhsBanner.mockMode")}
                </span>
              </>
            )}
          </>
        )}
        <span className="ml-auto">
          {expanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </span>
      </div>

      {/* Expanded control panel */}
      {expanded && (
        <div className="mt-2 rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-3">
          {/* MHS offline → Launch button */}
          {!mhsStatus.online && (
            <div className="flex items-center gap-3">
              <span className="text-sm text-slate-600">
                {t("dashboard.mhsPanel.offlineHint")}
              </span>
              <button
                onClick={handleLaunchMHS}
                disabled={busy}
                className="ml-auto flex items-center gap-2 rounded-lg bg-blue-600 text-white px-4 py-2 text-sm font-medium hover:bg-blue-700 transition disabled:opacity-50"
              >
                {busy ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Power className="h-4 w-4" />
                )}
                {t("dashboard.mhsPanel.launch")}
              </button>
            </div>
          )}

          {/* MHS online, RS485 not connected → Port selector + Connect */}
          {mhsStatus.online && !mhsStatus.connected && (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-slate-700 shrink-0">
                  {t("dashboard.mhsPanel.selectPort")}
                </label>
                <select
                  value={selectedPort}
                  onChange={(e) => setSelectedPort(e.target.value)}
                  className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                >
                  {ports.length === 0 && (
                    <option value="">{t("dashboard.mhsPanel.noPorts")}</option>
                  )}
                  {ports.map((p) => (
                    <option key={p} value={p}>
                      {p}
                      {p === preferredPort ? ` (${t("dashboard.mhsPanel.configured")})` : ""}
                    </option>
                  ))}
                </select>
                <button
                  onClick={refreshPorts}
                  className="rounded-lg border border-slate-200 p-1.5 text-slate-500 hover:bg-slate-100 transition"
                  title={t("common.refresh")}
                >
                  <RefreshCw className="h-4 w-4" />
                </button>
              </div>

              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-slate-700 shrink-0">
                  {t("dashboard.mhsPanel.baudrate")}
                </label>
                <select
                  value={baudrate}
                  onChange={(e) => setBaudrate(Number(e.target.value))}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm"
                >
                  {[9600, 19200, 38400, 57600, 115200].map((b) => (
                    <option key={b} value={b}>
                      {b}
                    </option>
                  ))}
                </select>

                <button
                  onClick={handleConnect}
                  disabled={busy || !selectedPort}
                  className="ml-auto flex items-center gap-2 rounded-lg bg-green-600 text-white px-4 py-2 text-sm font-medium hover:bg-green-700 transition disabled:opacity-50"
                >
                  {busy ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Plug className="h-4 w-4" />
                  )}
                  {t("dashboard.mhsPanel.connect")}
                </button>
              </div>
            </div>
          )}

          {/* MHS online, RS485 connected → Disconnect */}
          {mhsStatus.online && mhsStatus.connected && (
            <div className="flex items-center gap-3">
              <span className="text-sm text-slate-600">
                RS485 {t("dashboard.mhsBanner.connected")}:{" "}
                <span className="font-mono font-semibold">{mhsStatus.port}</span>
              </span>
              <button
                onClick={handleDisconnect}
                disabled={busy}
                className="ml-auto flex items-center gap-2 rounded-lg bg-red-50 text-red-700 px-4 py-2 text-sm font-medium border border-red-200 hover:bg-red-100 transition disabled:opacity-50"
              >
                {busy ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Unplug className="h-4 w-4" />
                )}
                {t("dashboard.mhsPanel.disconnect")}
              </button>
            </div>
          )}

          {/* Refresh status */}
          <div className="flex justify-end">
            <button
              onClick={() => { fetchMHSStatus(); if (mhsStatus.online) refreshPorts(); }}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium"
            >
              {t("dashboard.refresh_now")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
