import { Link } from "react-router-dom";
import { HttpError } from "@/api/client";
import type { ExperimentListItem } from "@/api/types";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { DataTable, type DataTableColumn } from "@/components/DataTable";
import { StatusPill } from "@/components/StatusPill";
import { useExperimentsQuery } from "@/hooks/useExperimentsQuery";
import { useHealthQuery } from "@/hooks/useHealthQuery";
import { useLatestExperimentQuery } from "@/hooks/useLatestExperimentQuery";

const EXPERIMENT_COLUMNS: Array<DataTableColumn<ExperimentListItem>> = [
  {
    key: "name",
    header: "Name",
    cell: (row) => row.name || "N/A"
  },
  {
    key: "day",
    header: "Day",
    cell: (row) => row.day || "N/A"
  },
  {
    key: "csv_count",
    header: "CSV",
    cell: (row) => row.csv_count,
    cellClassName: "font-semibold"
  },
  {
    key: "has_echem_dir",
    header: "EChem Dir",
    cell: (row) => (row.has_echem_dir ? "Yes" : "No")
  },
  {
    key: "run_dir",
    header: "Run Directory",
    cell: (row) => <span className="font-mono text-xs text-slate-600">{row.run_dir}</span>
  }
];

const asPrettyJson = (value: unknown) => JSON.stringify(value, null, 2);

export function Overview() {
  const healthQuery = useHealthQuery();
  const experimentsQuery = useExperimentsQuery(10);
  const latestQuery = useLatestExperimentQuery();

  const latestNotFound =
    latestQuery.error instanceof HttpError && latestQuery.error.status === 404;
  const latestRunDir =
    latestQuery.data?.latest.run_dir ?? experimentsQuery.data?.items[0]?.run_dir ?? "";

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-3">
        <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Service Health
          </h3>
          <div className="mt-3">
            {healthQuery.isLoading ? (
              <p className="text-sm text-slate-500">Loading health status...</p>
            ) : healthQuery.error ? (
              <ApiErrorBanner
                error={healthQuery.error}
                title="Health check failed"
                onRetry={() => healthQuery.refetch()}
              />
            ) : (
              <div className="space-y-2">
                <StatusPill status={healthQuery.data?.status} />
                <p className="text-sm text-slate-700">{healthQuery.data?.service}</p>
              </div>
            )}
          </div>
        </article>

        <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Recent Experiments
          </h3>
          <div className="mt-3">
            {experimentsQuery.isLoading ? (
              <p className="text-sm text-slate-500">Loading recent runs...</p>
            ) : experimentsQuery.error ? (
              <ApiErrorBanner
                error={experimentsQuery.error}
                title="Unable to load experiments"
                onRetry={() => experimentsQuery.refetch()}
              />
            ) : (
              <p className="text-3xl font-semibold text-slate-900">{experimentsQuery.data?.count ?? 0}</p>
            )}
          </div>
        </article>

        <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Latest Run
          </h3>
          <div className="mt-3">
            {latestQuery.isLoading ? (
              <p className="text-sm text-slate-500">Loading latest run...</p>
            ) : latestNotFound ? (
              <p className="text-sm text-slate-500">No experiment found yet.</p>
            ) : latestQuery.error ? (
              <ApiErrorBanner
                error={latestQuery.error}
                title="Unable to load latest run"
                onRetry={() => latestQuery.refetch()}
              />
            ) : (
              <div className="space-y-1">
                <p className="text-base font-semibold text-slate-900">
                  {latestQuery.data?.latest.name || "Unnamed run"}
                </p>
                <p className="text-sm text-slate-600">{latestQuery.data?.latest.day}</p>
              </div>
            )}
          </div>
        </article>
      </section>

      <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">Recent Runs Table</h3>
        {experimentsQuery.error ? (
          <ApiErrorBanner
            error={experimentsQuery.error}
            title="Failed to load recent runs"
            onRetry={() => experimentsQuery.refetch()}
          />
        ) : null}
        <DataTable
          columns={EXPERIMENT_COLUMNS}
          rows={experimentsQuery.data?.items ?? []}
          rowKey={(row) => row.run_dir}
          isLoading={experimentsQuery.isLoading}
          emptyMessage="No experiments found."
        />
      </section>

      <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">Latest Run Detail</h3>
        {latestQuery.isLoading ? (
          <p className="text-sm text-slate-500">Loading latest experiment detail...</p>
        ) : latestNotFound ? (
          <p className="text-sm text-slate-500">
            Latest experiment is unavailable (API returned 404).
          </p>
        ) : latestQuery.error ? (
          <ApiErrorBanner
            error={latestQuery.error}
            title="Failed to load latest experiment detail"
            onRetry={() => latestQuery.refetch()}
          />
        ) : latestQuery.data ? (
          <div className="space-y-3">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-xs uppercase tracking-wide text-slate-500">Run Name</p>
                <p className="text-sm font-medium text-slate-800">{latestQuery.data.latest.name}</p>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-xs uppercase tracking-wide text-slate-500">Run Directory</p>
                <p className="truncate font-mono text-xs text-slate-700">
                  {latestQuery.data.latest.run_dir}
                </p>
              </div>
            </div>
            <pre className="max-h-96 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
              {asPrettyJson(latestQuery.data.details)}
            </pre>
          </div>
        ) : (
          <p className="text-sm text-slate-500">No detail available.</p>
        )}
      </section>

      <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">Quick Actions</h3>
        <div className="grid gap-3 md:grid-cols-3">
          <button
            type="button"
            disabled
            className="rounded-lg border border-slate-200 bg-slate-100 px-3 py-2 text-sm font-medium text-slate-500"
          >
            Contextualize Latest (Phase 2)
          </button>
          <button
            type="button"
            disabled
            className="rounded-lg border border-slate-200 bg-slate-100 px-3 py-2 text-sm font-medium text-slate-500"
          >
            Diagnose Latest (Phase 2)
          </button>
          <button
            type="button"
            disabled
            className="rounded-lg border border-slate-200 bg-slate-100 px-3 py-2 text-sm font-medium text-slate-500"
          >
            Suggest Next (Phase 2)
          </button>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-blue-50 p-3">
          <p className="text-sm text-blue-900">
            Configure API endpoint and runtime defaults from Settings.
          </p>
          <Link
            to="/settings"
            className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            Open Settings
          </Link>
        </div>
        {latestRunDir ? (
          <p className="text-xs text-slate-500">
            Latest run detected: <code>{latestRunDir}</code>
          </p>
        ) : null}
      </section>
    </div>
  );
}

