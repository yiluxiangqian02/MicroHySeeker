import { useState } from "react";

interface Props {
  onStop: () => Promise<void>;
  isStopping: boolean;
  stopSuccess: boolean;
  stopError: Error | null;
}

export function EmergencyStop({ onStop, isStopping, stopSuccess, stopError }: Props) {
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
          <span className="text-sm font-medium text-red-800">Confirm emergency stop?</span>
          <button
            type="button"
            onClick={handleClick}
            disabled={isStopping}
            className="rounded-md bg-red-600 px-3 py-1 text-xs font-bold text-white hover:bg-red-700 disabled:opacity-50"
          >
            {isStopping ? "Stopping…" : "Yes, Stop"}
          </button>
          <button
            type="button"
            onClick={() => setConfirming(false)}
            className="rounded-md border border-red-200 bg-white px-3 py-1 text-xs font-medium text-red-700 hover:bg-red-100"
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={handleClick}
          disabled={isStopping || stopSuccess}
          className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-bold text-white shadow-sm hover:bg-red-700 active:scale-95 disabled:opacity-50"
          aria-label="Emergency stop"
        >
          <span aria-hidden="true">⛔</span>
          {stopSuccess ? "Stopped" : "Emergency Stop"}
        </button>
      )}

      {stopError && (
        <p className="text-xs text-red-600">Stop failed: {stopError.message}</p>
      )}
      {stopSuccess && (
        <p className="text-xs font-medium text-green-700">Stop signal sent successfully.</p>
      )}
    </div>
  );
}
