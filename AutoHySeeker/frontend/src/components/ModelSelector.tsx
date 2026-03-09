import type { FC } from "react";
import { AVAILABLE_MODELS } from "@/stores/agentStore";

interface Props {
  label: string;
  value: string;
  onChange: (value: string) => void;
  id?: string;
}

export const ModelSelector: FC<Props> = ({ label, value, onChange, id }) => {
  return (
    <div>
      <label
        htmlFor={id}
        className="mb-1 block text-xs font-medium text-slate-600"
      >
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
      >
        {AVAILABLE_MODELS.map((m) => (
          <option key={m.value} value={m.value}>
            {m.label}
          </option>
        ))}
      </select>
    </div>
  );
};
