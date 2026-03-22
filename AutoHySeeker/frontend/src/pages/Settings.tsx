import { useEffect, useState, useRef, type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Settings as SettingsIcon, Bell, Palette, Database, Download, Upload } from "lucide-react";
import { useShallow } from "zustand/react/shallow";
import { DEFAULT_SETTINGS, useSettingsStore } from "@/stores/settingsStore";
import { AGENT_DEFINITIONS, useAgentStore, AVAILABLE_MODELS, type ControlAgentId, type AgentConfig } from "@/stores/agentStore";

const settingsSchema = z.object({
  apiBaseUrl: z.string().url("Please input a valid URL."),
  defaultDiagnosticsDataDir: z.string().max(1024),
  defaultContextHistoryDir: z.string().max(1024),
  pollingIntervalMs: z.coerce.number().int().min(1000).max(60000),
  requestTimeoutMs: z.coerce.number().int().min(1000).max(120000)
});

type SettingsFormValues = z.infer<typeof settingsSchema>;

type TabType = "general" | "agents" | "interface" | "notifications";

export function Settings() {
  const { t, i18n } = useTranslation();
  const [activeTab, setActiveTab] = useState<TabType>("general");
  const [notice, setNotice] = useState<string>("");
  const importRef = useRef<HTMLInputElement>(null);

  // General settings — useShallow prevents a new object reference on every render,
  // which would otherwise cause "Maximum update depth exceeded" with useSyncExternalStore.
  const settings = useSettingsStore(
    useShallow((state) => ({
      apiBaseUrl: state.apiBaseUrl,
      defaultDiagnosticsDataDir: state.defaultDiagnosticsDataDir,
      defaultContextHistoryDir: state.defaultContextHistoryDir,
      pollingIntervalMs: state.pollingIntervalMs,
      requestTimeoutMs: state.requestTimeoutMs
    }))
  );
  const setSettings = useSettingsStore((state) => state.setSettings);
  const resetSettingsStore = useSettingsStore((state) => state.resetSettings);

  // Agent settings
  const configs = useAgentStore((s) => s.configs);
  const setConfig = useAgentStore((s) => s.setConfig);
  const importConfigs = useAgentStore((s) => s.importConfigs);
  const resetAll = useAgentStore((s) => s.resetAll);

  // Interface settings
  const [theme, setTheme] = useState<"light" | "dark">(
    (localStorage.getItem("theme") as "light" | "dark") || "light"
  );
  const [fontSize, setFontSize] = useState<"small" | "medium" | "large">(
    (localStorage.getItem("fontSize") as "small" | "medium" | "large") || "medium"
  );
  const [compactMode, setCompactMode] = useState(
    localStorage.getItem("compactMode") === "true"
  );

  // Notification settings
  const [desktopNotifications, setDesktopNotifications] = useState(
    localStorage.getItem("desktopNotifications") === "true"
  );
  const [experimentCompleteNotif, setExperimentCompleteNotif] = useState(
    localStorage.getItem("experimentCompleteNotif") !== "false"
  );
  const [errorAlertNotif, setErrorAlertNotif] = useState(
    localStorage.getItem("errorAlertNotif") !== "false"
  );

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty, isSubmitting }
  } = useForm<SettingsFormValues>({
    resolver: zodResolver(settingsSchema),
    defaultValues: settings
  });

  // Init the form once on mount. The form already has defaultValues from the
  // store, but this ensures it's in sync even after hydration.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { reset(settings); }, []);

  const onSubmit = (values: SettingsFormValues) => {
    setSettings(values);
    setNotice(t("settings.saveSettings") + " ✓");
    setTimeout(() => setNotice(""), 3000);
  };

  const onResetDefaults = () => {
    resetSettingsStore();
    reset(DEFAULT_SETTINGS);
    setNotice(t("settings.resetDefaults") + " ✓");
    setTimeout(() => setNotice(""), 3000);
  };

  const handleLanguageChange = (lang: string) => {
    i18n.changeLanguage(lang);
    localStorage.setItem("language", lang);
    setNotice(t("settings.saveSettings") + " ✓");
    setTimeout(() => setNotice(""), 3000);
  };

  const handleThemeChange = (newTheme: "light" | "dark") => {
    setTheme(newTheme);
    localStorage.setItem("theme", newTheme);
    // TODO: Apply theme to document
    setNotice(t("settings.saveSettings") + " ✓");
    setTimeout(() => setNotice(""), 3000);
  };

  const handleFontSizeChange = (newSize: "small" | "medium" | "large") => {
    setFontSize(newSize);
    localStorage.setItem("fontSize", newSize);
    setNotice(t("settings.saveSettings") + " ✓");
    setTimeout(() => setNotice(""), 3000);
  };

  const handleCompactModeChange = (enabled: boolean) => {
    setCompactMode(enabled);
    localStorage.setItem("compactMode", String(enabled));
    setNotice(t("settings.saveSettings") + " ✓");
    setTimeout(() => setNotice(""), 3000);
  };

  const handleNotificationChange = (type: string, enabled: boolean) => {
    switch (type) {
      case "desktop":
        setDesktopNotifications(enabled);
        localStorage.setItem("desktopNotifications", String(enabled));
        break;
      case "experimentComplete":
        setExperimentCompleteNotif(enabled);
        localStorage.setItem("experimentCompleteNotif", String(enabled));
        break;
      case "errorAlert":
        setErrorAlertNotif(enabled);
        localStorage.setItem("errorAlertNotif", String(enabled));
        break;
    }
    setNotice(t("settings.saveSettings") + " ✓");
    setTimeout(() => setNotice(""), 3000);
  };

  const handleExportAgentConfigs = () => {
    const data = JSON.stringify(configs, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `agent-configs-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImportAgentConfigs = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const parsed = JSON.parse(event.target?.result as string) as Partial<
          Record<ControlAgentId, AgentConfig>
        >;
        importConfigs(parsed);
        setNotice(t("settings.importConfig") + " ✓");
        setTimeout(() => setNotice(""), 3000);
      } catch {
        setNotice("Invalid config file");
        setTimeout(() => setNotice(""), 3000);
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const handleResetAgentConfigs = () => {
    if (window.confirm("Reset all agent configurations to defaults?")) {
      resetAll();
      setNotice(t("settings.resetDefaults") + " ✓");
      setTimeout(() => setNotice(""), 3000);
    }
  };

  const tabs: Array<{ id: TabType; label: string; icon: any }> = [
    { id: "general", label: t("settings.general"), icon: SettingsIcon },
    { id: "agents", label: t("settings.agents"), icon: Database },
    { id: "interface", label: t("settings.interface"), icon: Palette },
    { id: "notifications", label: t("settings.notifications"), icon: Bell }
  ];

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h2 className="text-2xl font-bold text-slate-900">{t("settings.title")}</h2>
        <p className="mt-1 text-sm text-slate-500">Configure application settings and preferences</p>
      </div>

      {/* Notice banner */}
      {notice && (
        <div className="rounded-md bg-green-50 px-4 py-3 text-sm text-green-700">
          {notice}
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <div className="flex gap-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-slate-600 hover:text-slate-900"
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab content */}
      <div className="max-w-4xl">
        {/* General tab */}
        {activeTab === "general" && (
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">{t("settings.systemConfig")}</h3>
            <p className="mt-1 text-sm text-slate-600">
              Configure API base URL and request defaults. Values are persisted in local storage.
            </p>

            <form className="mt-5 space-y-4" onSubmit={handleSubmit(onSubmit)}>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">{t("settings.apiBaseUrl")}</label>
                <input
                  {...register("apiBaseUrl")}
                  type="url"
                  placeholder="http://localhost:8100"
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                />
                {errors.apiBaseUrl && (
                  <p className="mt-1 text-sm text-red-600">{errors.apiBaseUrl.message}</p>
                )}
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  {t("settings.dataDir")} (Diagnostics)
                </label>
                <input
                  {...register("defaultDiagnosticsDataDir")}
                  type="text"
                  placeholder="Optional path"
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  {t("settings.dataDir")} (Context History)
                </label>
                <input
                  {...register("defaultContextHistoryDir")}
                  type="text"
                  placeholder="Optional path"
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Polling Interval (ms)
                  </label>
                  <input
                    {...register("pollingIntervalMs")}
                    type="number"
                    min={1000}
                    max={60000}
                    step={1000}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Request Timeout (ms)
                  </label>
                  <input
                    {...register("requestTimeoutMs")}
                    type="number"
                    min={1000}
                    max={120000}
                    step={1000}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                  />
                </div>
              </div>

              <div className="flex flex-wrap gap-3">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {t("settings.saveSettings")}
                </button>
                <button
                  type="button"
                  onClick={() => reset(settings)}
                  disabled={!isDirty}
                  className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Revert Unsaved
                </button>
                <button
                  type="button"
                  onClick={onResetDefaults}
                  className="rounded-md border border-red-300 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50"
                >
                  {t("settings.resetDefaults")}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Agents tab */}
        {activeTab === "agents" && (
          <div className="space-y-4">
            <div className="flex justify-end gap-2">
              <button
                onClick={handleExportAgentConfigs}
                className="flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                <Download className="h-4 w-4" />
                {t("settings.exportConfig")}
              </button>
              <button
                onClick={() => importRef.current?.click()}
                className="flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                <Upload className="h-4 w-4" />
                {t("settings.importConfig")}
              </button>
              <input
                ref={importRef}
                type="file"
                accept=".json"
                className="hidden"
                onChange={handleImportAgentConfigs}
              />
              <button
                onClick={handleResetAgentConfigs}
                className="rounded-md border border-red-300 bg-red-50 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-100"
              >
                {t("settings.resetDefaults")}
              </button>
            </div>

            {AGENT_DEFINITIONS.map((def) => {
              const config = configs[def.id];
              return (
                <div key={def.id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-semibold text-slate-900">{def.name}</h4>
                      <p className="mt-1 text-sm text-slate-600">{def.description}</p>
                    </div>
                    <label className="flex cursor-pointer items-center gap-2">
                      <input
                        type="checkbox"
                        checked={config.enabled}
                        onChange={(e) => setConfig(def.id, { enabled: e.target.checked })}
                        className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm font-medium text-slate-700">
                        {config.enabled ? t("settings.enabled") : t("settings.disabled")}
                      </span>
                    </label>
                  </div>

                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">
                        {t("settings.model")} (Primary)
                      </label>
                      <select
                        value={config.primaryModel}
                        onChange={(e) => setConfig(def.id, { primaryModel: e.target.value })}
                        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                      >
                        {AVAILABLE_MODELS.map((model) => (
                          <option key={model.value} value={model.value}>
                            {model.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">
                        {t("settings.model")} (Fallback)
                      </label>
                      <select
                        value={config.fallbackModel}
                        onChange={(e) => setConfig(def.id, { fallbackModel: e.target.value })}
                        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                      >
                        {AVAILABLE_MODELS.map((model) => (
                          <option key={model.value} value={model.value}>
                            {model.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="mt-3">
                    <label className="mb-1 block text-sm font-medium text-slate-700">
                      {t("settings.apiKey")}
                    </label>
                    <input
                      type="password"
                      value={config.apiKey}
                      onChange={(e) => setConfig(def.id, { apiKey: e.target.value })}
                      placeholder="sk-..."
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Interface tab */}
        {activeTab === "interface" && (
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">{t("settings.interface")}</h3>
            <p className="mt-1 text-sm text-slate-600">Customize the appearance and behavior of the interface</p>

            <div className="mt-5 space-y-5">
              {/* Language */}
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">{t("settings.language")}</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleLanguageChange("zh-CN")}
                    className={`rounded-md px-4 py-2 text-sm font-medium ${
                      i18n.language === "zh-CN"
                        ? "bg-blue-600 text-white"
                        : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                    }`}
                  >
                    中文
                  </button>
                  <button
                    onClick={() => handleLanguageChange("en-US")}
                    className={`rounded-md px-4 py-2 text-sm font-medium ${
                      i18n.language === "en-US"
                        ? "bg-blue-600 text-white"
                        : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                    }`}
                  >
                    English
                  </button>
                </div>
              </div>

              {/* Theme */}
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">{t("settings.theme")}</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleThemeChange("light")}
                    className={`rounded-md px-4 py-2 text-sm font-medium ${
                      theme === "light"
                        ? "bg-blue-600 text-white"
                        : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                    }`}
                  >
                    {t("settings.themeLight")}
                  </button>
                  <button
                    onClick={() => handleThemeChange("dark")}
                    className={`rounded-md px-4 py-2 text-sm font-medium ${
                      theme === "dark"
                        ? "bg-blue-600 text-white"
                        : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                    }`}
                  >
                    {t("settings.themeDark")}
                  </button>
                </div>
              </div>

              {/* Font size */}
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">{t("settings.fontSize")}</label>
                <div className="flex gap-2">
                  {(["small", "medium", "large"] as const).map((size) => (
                    <button
                      key={size}
                      onClick={() => handleFontSizeChange(size)}
                      className={`rounded-md px-4 py-2 text-sm font-medium ${
                        fontSize === size
                          ? "bg-blue-600 text-white"
                          : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                      }`}
                    >
                      {t(`settings.fontSize${size.charAt(0).toUpperCase() + size.slice(1)}` as any)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Compact mode */}
              <div>
                <label className="flex cursor-pointer items-center gap-3">
                  <input
                    type="checkbox"
                    checked={compactMode}
                    onChange={(e) => handleCompactModeChange(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  <div>
                    <span className="text-sm font-medium text-slate-700">{t("settings.compactMode")}</span>
                    <p className="text-xs text-slate-500">Reduce spacing and padding for a more compact layout</p>
                  </div>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* Notifications tab */}
        {activeTab === "notifications" && (
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">{t("settings.notifications")}</h3>
            <p className="mt-1 text-sm text-slate-600">Configure notification preferences</p>

            <div className="mt-5 space-y-4">
              <label className="flex cursor-pointer items-center gap-3">
                <input
                  type="checkbox"
                  checked={desktopNotifications}
                  onChange={(e) => handleNotificationChange("desktop", e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="text-sm font-medium text-slate-700">{t("settings.desktopNotifications")}</span>
                  <p className="text-xs text-slate-500">Enable browser desktop notifications</p>
                </div>
              </label>

              <label className="flex cursor-pointer items-center gap-3">
                <input
                  type="checkbox"
                  checked={experimentCompleteNotif}
                  onChange={(e) => handleNotificationChange("experimentComplete", e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="text-sm font-medium text-slate-700">{t("settings.experimentCompleteNotif")}</span>
                  <p className="text-xs text-slate-500">Notify when experiments complete</p>
                </div>
              </label>

              <label className="flex cursor-pointer items-center gap-3">
                <input
                  type="checkbox"
                  checked={errorAlertNotif}
                  onChange={(e) => handleNotificationChange("errorAlert", e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="text-sm font-medium text-slate-700">{t("settings.errorAlertNotif")}</span>
                  <p className="text-xs text-slate-500">Notify when errors occur</p>
                </div>
              </label>

              <div className="mt-6 rounded-md border border-slate-200 bg-slate-50 p-4">
                <h4 className="text-sm font-semibold text-slate-700">{t("settings.emailSettings")}</h4>
                <p className="mt-1 text-xs text-slate-500">Email notifications are not yet implemented</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
