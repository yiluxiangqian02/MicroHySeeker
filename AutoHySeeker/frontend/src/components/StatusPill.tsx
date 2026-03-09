interface StatusPillProps {
  status?: string | null;
}

const STATUS_STYLE_MAP: Record<string, string> = {
  ok: "bg-status-ok/15 text-status-ok border-status-ok/40",
  warning: "bg-status-warning/15 text-status-warning border-status-warning/40",
  error: "bg-status-error/15 text-status-error border-status-error/40",
  unknown: "bg-status-unknown/15 text-status-unknown border-status-unknown/40"
};

export function StatusPill({ status }: StatusPillProps) {
  const normalizedStatus = (status ?? "unknown").toLowerCase();
  const style = STATUS_STYLE_MAP[normalizedStatus] ?? STATUS_STYLE_MAP.unknown;

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${style}`}
    >
      {normalizedStatus}
    </span>
  );
}

