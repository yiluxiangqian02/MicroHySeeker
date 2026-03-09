import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { DEFAULT_SETTINGS, useSettingsStore } from "@/stores/settingsStore";

const settingsSchema = z.object({
  apiBaseUrl: z.string().url("Please input a valid URL."),
  defaultDiagnosticsDataDir: z.string().max(1024),
  defaultContextHistoryDir: z.string().max(1024),
  pollingIntervalMs: z.coerce.number().int().min(1000).max(60000),
  requestTimeoutMs: z.coerce.number().int().min(1000).max(120000)
});

type SettingsFormValues = z.infer<typeof settingsSchema>;

export function Settings() {
  const [notice, setNotice] = useState<string>("");

  const settings = useSettingsStore((state) => ({
    apiBaseUrl: state.apiBaseUrl,
    defaultDiagnosticsDataDir: state.defaultDiagnosticsDataDir,
    defaultContextHistoryDir: state.defaultContextHistoryDir,
    pollingIntervalMs: state.pollingIntervalMs,
    requestTimeoutMs: state.requestTimeoutMs
  }));
  const setSettings = useSettingsStore((state) => state.setSettings);
  const resetSettingsStore = useSettingsStore((state) => state.resetSettings);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty, isSubmitting }
  } = useForm<SettingsFormValues>({
    resolver: zodResolver(settingsSchema),
    defaultValues: settings
  });

  useEffect(() => {
    reset(settings);
  }, [
    reset,
    settings.apiBaseUrl,
    settings.defaultContextHistoryDir,
    settings.defaultDiagnosticsDataDir,
    settings.pollingIntervalMs,
    settings.requestTimeoutMs
  ]);

  const onSubmit = (values: SettingsFormValues) => {
    setSettings(values);
    setNotice(`Settings saved at ${new Date().toLocaleTimeString()}.`);
  };

  const onResetDefaults = () => {
    resetSettingsStore();
    setNotice("Settings restored to defaults.");
  };

  return (
    <div className="max-w-3xl space-y-6">
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">Client Settings</h3>
        <p className="mt-1 text-sm text-slate-600">
          Configure API base URL and request defaults. Values are persisted in local storage.
        </p>

        <form className="mt-5 space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">API Base URL</label>
            <input
              {...register("apiBaseUrl")}
              type="url"
              placeholder="http://localhost:8100"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
            {errors.apiBaseUrl ? (
              <p className="mt-1 text-sm text-red-600">{errors.apiBaseUrl.message}</p>
            ) : null}
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Default Diagnostics Data Dir
            </label>
            <input
              {...register("defaultDiagnosticsDataDir")}
              type="text"
              placeholder="Optional path"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
            {errors.defaultDiagnosticsDataDir ? (
              <p className="mt-1 text-sm text-red-600">{errors.defaultDiagnosticsDataDir.message}</p>
            ) : null}
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Default Context History Dir
            </label>
            <input
              {...register("defaultContextHistoryDir")}
              type="text"
              placeholder="Optional path"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
            {errors.defaultContextHistoryDir ? (
              <p className="mt-1 text-sm text-red-600">{errors.defaultContextHistoryDir.message}</p>
            ) : null}
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
              {errors.pollingIntervalMs ? (
                <p className="mt-1 text-sm text-red-600">{errors.pollingIntervalMs.message}</p>
              ) : null}
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
              {errors.requestTimeoutMs ? (
                <p className="mt-1 text-sm text-red-600">{errors.requestTimeoutMs.message}</p>
              ) : null}
            </div>
          </div>

          {notice ? (
            <p className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{notice}</p>
          ) : null}

          <div className="flex flex-wrap gap-3">
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Save Settings
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
              Reset to Defaults
            </button>
          </div>
        </form>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Default Values
        </h4>
        <pre className="mt-3 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
          {JSON.stringify(DEFAULT_SETTINGS, null, 2)}
        </pre>
      </section>
    </div>
  );
}

