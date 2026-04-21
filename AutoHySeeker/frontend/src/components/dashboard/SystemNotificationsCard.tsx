import { AlertCircle, Clock, Info, AlertTriangle } from "lucide-react";
import { useTranslation } from "react-i18next";

export type NotificationType = "info" | "warning" | "error";

export interface SystemNotification {
  id: string;
  type: NotificationType;
  message: string;
  timeAgo: string;
}

const icons = {
  info: <Info className="h-5 w-5 text-blue-500" />,
  warning: <AlertTriangle className="h-5 w-5 text-orange-500" />,
  error: <AlertCircle className="h-5 w-5 text-red-500" />
};

export function SystemNotificationsCard({ notifications }: { notifications: SystemNotification[] }) {
  const { t } = useTranslation();
  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm flex flex-col h-full">
      <div className="border-b border-slate-100 px-5 py-4">
        <h3 className="font-semibold text-slate-900">{t("dashboard.system_notif")}</h3>
      </div>

      <div className="max-h-64 overflow-y-auto p-2">
        {notifications.length === 0 ? (
          <div className="flex items-center justify-center p-4 text-sm text-slate-500">
            {t("dashboard.no_notifications")}
          </div>
        ) : (
          <ul className="space-y-1">
            {notifications.map((note) => (
              <li key={note.id} className="flex items-start gap-3 rounded-xl p-3 hover:bg-slate-50 transition-colors">
                <div className="shrink-0 mt-0.5">{icons[note.type]}</div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-slate-800">{note.message}</p>
                  <p className="mt-1 flex items-center gap-1 text-xs text-slate-500">
                    <Clock className="h-3 w-3" /> {note.timeAgo}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
