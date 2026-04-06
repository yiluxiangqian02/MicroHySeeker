import { useTranslation } from "react-i18next";

interface Props {
  isHealthy: boolean;
  isLoading: boolean;
  hardwareAvailable?: boolean;
}

export function HardwareStatusBadge({ isHealthy, isLoading, hardwareAvailable }: Props) {
  const { t } = useTranslation();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-500">
          <span className="h-2 w-2 rounded-full bg-slate-300 animate-pulse" />
          {t("common.loading")}
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      {/* Backend API status */}
      <span
        className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${
          isHealthy
            ? "border-green-200 bg-green-50 text-green-700"
            : "border-red-200 bg-red-50 text-red-700"
        }`}
      >
        <span className={`h-2 w-2 rounded-full ${isHealthy ? "bg-green-500" : "bg-red-500"}`} />
        {t("overview.autohyseeker")} {isHealthy ? t("overview.online") : t("overview.offline")}
      </span>

      {/* MicroHySeeker hardware status */}
      <span
        className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${
          hardwareAvailable
            ? "border-green-200 bg-green-50 text-green-700"
            : "border-amber-200 bg-amber-50 text-amber-700"
        }`}
        title={hardwareAvailable
          ? t("overview.microhyseeker") + " " + t("overview.connected")
          : t("dashboard.mhsOfflineHint")}
      >
        <span className={`h-2 w-2 rounded-full ${hardwareAvailable ? "bg-green-500" : "bg-amber-500"}`} />
        {t("overview.microhyseeker")} {hardwareAvailable ? t("overview.connected") : t("overview.disconnected")}
      </span>
    </div>
  );
}
