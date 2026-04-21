import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import type { EchemDataPoint } from "@/api/types";

interface Props {
  data: EchemDataPoint[];
  /** Which series to display. Defaults to all three. */
  series?: Array<"voltage" | "current" | "power">;
}

interface Margin {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

interface Range {
  min: number;
  max: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function dataRange(values: number[]): Range {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = (max - min) * 0.1 || 0.1;
  return { min: min - pad, max: max + pad };
}

function scaleLinear(domain: Range, rangePixels: [number, number]) {
  return (v: number) => {
    const t = (v - domain.min) / (domain.max - domain.min || 1);
    return rangePixels[0] + t * (rangePixels[1] - rangePixels[0]);
  };
}

function buildPathD(points: Array<[number, number]>): string {
  if (points.length === 0) return "";
  return points.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
}

function niceTickCount(range: Range, targetCount = 5): number[] {
  const span = range.max - range.min || 1;
  const step = span / targetCount;
  const ticks: number[] = [];
  for (let i = 0; i <= targetCount; i++) {
    ticks.push(range.min + i * step);
  }
  return ticks;
}

// ── Series config ─────────────────────────────────────────────────────────────

type SeriesKey = "voltage" | "current" | "power";

const SERIES_CONFIG: Record<
  SeriesKey,
  { labelKey: string; unit: string; color: string }
> = {
  voltage: { labelKey: "realtimeChart.voltage", unit: "V", color: "#3b82f6" },
  current: { labelKey: "realtimeChart.current", unit: "mA", color: "#ef4444" },
  power: { labelKey: "realtimeChart.power", unit: "mW", color: "#10b981" },
};

// ── Chart SVG renderer ────────────────────────────────────────────────────────

interface ChartProps {
  data: EchemDataPoint[];
  series: SeriesKey[];
  width: number;
  height: number;
  margin: Margin;
}

function ChartSvg({ data, series, width, height, margin }: ChartProps) {
  const { t } = useTranslation();
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const tValues = data.map((d) => d.t);
  const tRange: Range =
    tValues.length >= 2
      ? { min: Math.min(...tValues), max: Math.max(...tValues) }
      : { min: 0, max: 60 };

  const xScale = scaleLinear(tRange, [0, innerW]);

  // One shared Y range across all selected series
  const allYValues = series.flatMap((key) =>
    data.map((d) => d[key] ?? NaN).filter((v) => !isNaN(v))
  );
  const yRange: Range =
    allYValues.length >= 2
      ? dataRange(allYValues)
      : { min: 0, max: 2 };
  const yScale = scaleLinear(yRange, [innerH, 0]);

  const xTicks = niceTickCount(tRange, 6);
  const yTicks = niceTickCount(yRange, 5);

  return (
    <svg
      width={width}
      height={height}
      role="img"
      aria-label={t("realtimeChart.ariaLabel")}
    >
      <g transform={`translate(${margin.left},${margin.top})`}>
        {/* Grid lines */}
        {yTicks.map((v) => (
          <line
            key={v}
            x1={0}
            x2={innerW}
            y1={yScale(v)}
            y2={yScale(v)}
            stroke="#e2e8f0"
            strokeWidth={1}
          />
        ))}
        {xTicks.map((v) => (
          <line
            key={v}
            x1={xScale(v)}
            x2={xScale(v)}
            y1={0}
            y2={innerH}
            stroke="#e2e8f0"
            strokeWidth={1}
          />
        ))}

        {/* Axes */}
        <line x1={0} x2={innerW} y1={innerH} y2={innerH} stroke="#94a3b8" strokeWidth={1.5} />
        <line x1={0} x2={0} y1={0} y2={innerH} stroke="#94a3b8" strokeWidth={1.5} />

        {/* Y axis ticks */}
        {yTicks.map((v) => (
          <g key={v}>
            <line x1={-4} x2={0} y1={yScale(v)} y2={yScale(v)} stroke="#94a3b8" />
            <text
              x={-7}
              y={yScale(v)}
              textAnchor="end"
              dominantBaseline="middle"
              fontSize={10}
              fill="#64748b"
            >
              {v.toFixed(1)}
            </text>
          </g>
        ))}

        {/* X axis ticks */}
        {xTicks.map((v) => (
          <g key={v}>
            <line x1={xScale(v)} x2={xScale(v)} y1={innerH} y2={innerH + 4} stroke="#94a3b8" />
            <text
              x={xScale(v)}
              y={innerH + 14}
              textAnchor="middle"
              fontSize={10}
              fill="#64748b"
            >
              {v.toFixed(0)}s
            </text>
          </g>
        ))}

        {/* X axis label */}
        <text
          x={innerW / 2}
          y={innerH + 28}
          textAnchor="middle"
          fontSize={11}
          fill="#94a3b8"
        >
          {t("realtimeChart.timeAxis")}
        </text>

        {/* Data lines */}
        {series.map((key) => {
          const cfg = SERIES_CONFIG[key];
          const points: Array<[number, number]> = data
            .filter((d) => d[key] !== undefined)
            .map((d) => [xScale(d.t), yScale(d[key]!)]);
          return (
            <path
              key={key}
              d={buildPathD(points)}
              fill="none"
              stroke={cfg.color}
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          );
        })}

        {/* Latest value dots */}
        {series.map((key) => {
          const last = [...data].reverse().find((d) => d[key] !== undefined);
          if (!last) return null;
          const cfg = SERIES_CONFIG[key];
          return (
            <circle
              key={key}
              cx={xScale(last.t)}
              cy={yScale(last[key]!)}
              r={4}
              fill={cfg.color}
              stroke="white"
              strokeWidth={2}
            />
          );
        })}
      </g>
    </svg>
  );
}

// ── Responsive wrapper ────────────────────────────────────────────────────────

const MARGIN: Margin = { top: 12, right: 20, bottom: 40, left: 52 };
const CHART_HEIGHT = 240;

export function RealtimeChart({ data, series = ["voltage", "current", "power"] }: Props) {
  const { t } = useTranslation();
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(600);

  const updateWidth = useCallback(() => {
    if (wrapperRef.current) {
      setWidth(wrapperRef.current.clientWidth);
    }
  }, []);

  useEffect(() => {
    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    if (wrapperRef.current) observer.observe(wrapperRef.current);
    return () => observer.disconnect();
  }, [updateWidth]);

  // Latest values for display
  const latestValues: Partial<Record<SeriesKey, number>> = {};
  for (const key of series) {
    const last = [...data].reverse().find((d) => d[key] !== undefined);
    if (last) latestValues[key] = last[key];
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      {/* Header */}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          {t("realtimeChart.title")}
        </h3>
        <div className="flex flex-wrap gap-3">
          {series.map((key) => {
            const cfg = SERIES_CONFIG[key];
            const val = latestValues[key];
            return (
              <div key={key} className="flex items-center gap-1.5">
                <span
                  className="inline-block h-2.5 w-5 rounded-sm"
                  style={{ backgroundColor: cfg.color }}
                />
                <span className="text-xs text-slate-600">
                  {t(cfg.labelKey)}
                  {val !== undefined ? (
                    <span className="ml-1 font-semibold text-slate-900">
                      {val.toFixed(key === "current" || key === "power" ? 1 : 3)} {cfg.unit}
                    </span>
                  ) : null}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Chart */}
      <div ref={wrapperRef} className="w-full overflow-hidden">
        {data.length < 2 ? (
          <div
            className="flex items-center justify-center text-sm text-slate-400"
            style={{ height: CHART_HEIGHT }}
          >
            {t("realtimeChart.collectingData")}
          </div>
        ) : (
          <ChartSvg
            data={data}
            series={series}
            width={width}
            height={CHART_HEIGHT}
            margin={MARGIN}
          />
        )}
      </div>
    </div>
  );
}
