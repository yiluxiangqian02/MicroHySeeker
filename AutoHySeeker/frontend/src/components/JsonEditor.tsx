import { useEffect, useMemo, useState } from "react";

type JsonValue = Record<string, unknown> | Array<unknown>;

interface JsonEditorProps {
  value: JsonValue;
  onChange: (next: JsonValue) => void;
  label?: string;
  rows?: number;
  disabled?: boolean;
}

export function JsonEditor({
  value,
  onChange,
  label = "JSON",
  rows = 10,
  disabled = false
}: JsonEditorProps) {
  const formattedValue = useMemo(() => JSON.stringify(value, null, 2), [value]);
  const [text, setText] = useState<string>(formattedValue);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    setText(formattedValue);
  }, [formattedValue]);

  const handleChange = (nextText: string) => {
    setText(nextText);
    try {
      const parsed = JSON.parse(nextText) as JsonValue;
      onChange(parsed);
      setError("");
    } catch {
      setError("Invalid JSON format.");
    }
  };

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-slate-700">{label}</label>
      <textarea
        value={text}
        onChange={(event) => handleChange(event.target.value)}
        rows={rows}
        disabled={disabled}
        className="w-full rounded-md border border-slate-300 bg-white p-3 font-mono text-sm leading-6 text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200 disabled:cursor-not-allowed disabled:bg-slate-50"
      />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </div>
  );
}

