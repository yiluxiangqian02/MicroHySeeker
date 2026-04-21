import { useState } from "react";
import { useTranslation } from "react-i18next";

interface Props {
  onStop: () => Promise<void>;
  isStopping: boolean;
  stopSuccess: boolean;
  stopError: Error | null;
}

export function EmergencyStop({ onStop, isStopping, stopSuccess, stopError }: Props) {
  const { t } = useTranslation();
  const [confirming, setConfirming] = useState(false);

  function handleClick() {
    if (!confirming) {
      setConfirming(true);
      return;
    }
    setConfirming(false);
    void onStop();
  }

  return (
    <div className="flex flex-col items-end gap-2">
      {confirming ? (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2">
          <span className="text-sm font-medium text-red-800">{t("emergencyStop.confirmPrompt")}</span>
          <button
            type="button"
            onClick={handleClick}
            disabled={isStopping}
            className="rounded-md bg-red-600 px-3 py-1 text-xs font-bold text-white hover:bg-red-700 disabled:opacity-50"
          >
            {isStopping ? t("emergencyStop.stopping") : t("emergencyStop.yesStop")}
          </button>
          <button
            type="button"
            onClick={() => setConfirming(false)}
            className="rounded-md border border-red-200 bg-white px-3 py-1 text-xs font-medium text-red-700 hover:bg-red-100"
          >
            {t("emergencyStop.cancel")}
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={handleClick}
          disabled={isStopping || stopSuccess}
          className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-bold text-white shadow-sm hover:bg-red-700 active:scale-95 disabled:opacity-50"
          aria-label={t("emergencyStop.ariaLabel")}
        >
          <span aria-hidden="true">⛔</span>
          {stopSuccess ? t("emergencyStop.stopped") : t("emergencyStop.label")}
        </button>
      )}

      {stopError && (
        <p className="text-xs text-red-600">{t("emergencyStop.failedMsg", { msg: stopError.message })}</p>
      )}
      {stopSuccess && (
        <p className="text-xs font-medium text-green-700">{t("emergencyStop.successMsg")}</p>
      )}
    </div>
  );
}
