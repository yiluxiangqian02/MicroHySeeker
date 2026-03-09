import { useState, type FC } from "react";

interface Props {
  value: string;
  onChange: (value: string) => void;
  id?: string;
}

export const ApiKeyInput: FC<Props> = ({ value, onChange, id }) => {
  const [visible, setVisible] = useState(false);

  const preview =
    value.length > 8
      ? value.slice(0, 8) + "••••••••••••••••"
      : value || "未配置";

  return (
    <div>
      <label
        htmlFor={id}
        className="mb-1 block text-xs font-medium text-slate-600"
      >
        API Key
      </label>
      <div className="flex gap-1.5">
        <input
          id={id}
          type={visible ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="sk-… (留空使用环境变量)"
          className="flex-1 rounded-md border border-slate-300 px-2.5 py-1.5 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="shrink-0 rounded-md border border-slate-300 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
        >
          {visible ? "隐藏" : "显示"}
        </button>
      </div>
      {value && (
        <p className="mt-1 font-mono text-xs text-slate-400">
          前8位：<span className="text-slate-600">{preview}</span>
        </p>
      )}
    </div>
  );
};
