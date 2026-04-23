"use client";

import { Info } from "lucide-react";

export type DashboardChartMode = "cumulative" | "delta";

export type DashboardChartPoint = {
  x: number;
  index: number;
  axisLabel: string;
  tooltipLabel: string;
  currentCount: number;
  currentDelta: number;
  compareCount: number | null;
  compareDelta: number | null;
};

export type DashboardChartAnnotation = {
  key: string;
  x: number;
  kind: "spike" | "dip" | "gain" | "loss" | "peak" | "low";
  label: string;
  value: number;
  magnitude: number;
};

type PlotPoint = {
  x: number;
  y: number;
  rawX: number;
  rawY: number;
  label: string;
};

const CHART_WIDTH = 1080;
const MARGIN = {
  top: 20,
  right: 16,
  bottom: 46,
  left: 74,
};

function formatTickLabel(value: number, spanDays: number) {
  const date = new Date(value);

  if (spanDays <= 1) {
    return new Intl.DateTimeFormat("en-US", {
      hour: "numeric",
      minute: "2-digit",
    }).format(date);
  }

  if (spanDays <= 120) {
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
    }).format(date);
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    year: "2-digit",
  }).format(date);
}

function buildLinePath(points: PlotPoint[]) {
  if (points.length === 0) return "";
  return points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
    .join(" ");
}

function buildAreaPath(points: PlotPoint[], baselineY: number) {
  if (points.length === 0) return "";

  const line = buildLinePath(points);
  const last = points[points.length - 1];
  const first = points[0];

  return `${line} L ${last.x.toFixed(2)} ${baselineY.toFixed(2)} L ${first.x.toFixed(2)} ${baselineY.toFixed(2)} Z`;
}

function buildTicks(minValue: number, maxValue: number, count = 4) {
  const step = count <= 1 ? 0 : (maxValue - minValue) / (count - 1);
  return Array.from({ length: count }, (_, index) => minValue + step * index);
}

function pickXTicks(data: DashboardChartPoint[], spanDays: number) {
  if (data.length <= 1) {
    return data.map((point) => ({ x: point.x, label: formatTickLabel(point.x, spanDays) }));
  }

  const xMin = data[0].x;
  const xMax = data[data.length - 1].x;
  const tickCount = Math.min(6, Math.max(4, spanDays > 365 ? 5 : 6));
  const ticks: Array<{ x: number; label: string }> = [];
  const usedLabels = new Set<string>();

  for (let index = 0; index < tickCount; index += 1) {
    const ratio = tickCount === 1 ? 0 : index / (tickCount - 1);
    const targetX = xMin + (xMax - xMin) * ratio;
    const label = formatTickLabel(targetX, spanDays);
    if (usedLabels.has(label)) continue;
    usedLabels.add(label);
    ticks.push({ x: targetX, label });
  }

  if (ticks.length === 0) {
    return data.map((point) => ({ x: point.x, label: formatTickLabel(point.x, spanDays) }));
  }

  return ticks;
}

export function ChartPanel({
  data,
  annotations,
  mode,
  showAnnotations,
  height = 340,
  note = null,
}: {
  data: DashboardChartPoint[];
  annotations: DashboardChartAnnotation[];
  mode: DashboardChartMode;
  showAnnotations: boolean;
  height?: number;
  note?: string | null;
}) {
  const chartHeight = height;
  const plotWidth = CHART_WIDTH - MARGIN.left - MARGIN.right;
  const plotHeight = chartHeight - MARGIN.top - MARGIN.bottom;

  const numericValues =
    mode === "cumulative"
      ? [
          ...data.map((point) => point.currentCount),
          ...data
            .map((point) => point.compareCount)
            .filter((value): value is number => value !== null),
        ]
      : [
          ...data.map((point) => point.currentDelta),
          ...data
            .map((point) => point.compareDelta)
            .filter((value): value is number => value !== null),
          0,
        ];

  const minValue = numericValues.length > 0 ? Math.min(...numericValues) : 0;
  const maxValue = numericValues.length > 0 ? Math.max(...numericValues) : 0;
  const flatRange = minValue === maxValue;
  const padding =
    mode === "cumulative"
      ? flatRange
        ? Math.max(2, Math.ceil(Math.abs(maxValue) * 0.02))
        : Math.max(2, Math.ceil((maxValue - minValue) * 0.18))
      : flatRange
        ? Math.max(1, Math.ceil(Math.abs(maxValue) || 1))
        : Math.max(1, Math.ceil((maxValue - minValue) * 0.24));

  const yMin = minValue - padding;
  const yMax = maxValue + padding;

  const xMin = data.length > 0 ? data[0].x : Date.now();
  const xMax = data.length > 1 ? data[data.length - 1].x : xMin + 1;
  const xSpan = Math.max(1, xMax - xMin);
  const ySpan = Math.max(1, yMax - yMin);
  const spanDays = data.length <= 1 ? 1 : Math.max(1, Math.ceil((xMax - xMin) / 86400000));

  const mapX = (value: number) => MARGIN.left + ((value - xMin) / xSpan) * plotWidth;
  const mapY = (value: number) => MARGIN.top + plotHeight - ((value - yMin) / ySpan) * plotHeight;

  const currentValues = data.map((point) => (mode === "cumulative" ? point.currentCount : point.currentDelta));
  const compareValues = data.map((point) => (mode === "cumulative" ? point.compareCount : point.compareDelta));
  const showComparison = compareValues.some((value) => value !== null);

  const currentPoints: PlotPoint[] = data.map((point, index) => ({
    x: mapX(point.x),
    y: mapY(currentValues[index]),
    rawX: point.x,
    rawY: currentValues[index],
    label: point.tooltipLabel,
  }));

  const comparePoints: PlotPoint[] = data
    .map((point, index) => {
      const value = compareValues[index];
      if (value === null) return null;
      return {
        x: mapX(point.x),
        y: mapY(value),
        rawX: point.x,
        rawY: value,
        label: point.tooltipLabel,
      };
    })
    .filter((point): point is PlotPoint => point !== null);

  const currentLinePath = buildLinePath(currentPoints);
  const currentAreaPath =
    mode === "cumulative" ? buildAreaPath(currentPoints, MARGIN.top + plotHeight) : "";
  const compareLinePath = showComparison ? buildLinePath(comparePoints) : "";
  const xTicks = pickXTicks(data, spanDays);
  const yTicks = buildTicks(yMin, yMax, 4);
  const zeroY = mapY(0);
  const allCountsFlat = data.every((point) => point.currentCount === data[0]?.currentCount);
  const allDeltasFlat = data.every((point) => point.currentDelta === 0);

  return (
    <div className="w-full">
      {note && (
        <div className="mb-3 flex">
          <div className="inline-flex max-w-full items-center gap-2 rounded-full border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm">
            <Info className="h-4 w-4 shrink-0 text-slate-500" />
            <span className="truncate">{note}</span>
          </div>
        </div>
      )}

      <div style={{ height }}>
        <svg
          viewBox={`0 0 ${CHART_WIDTH} ${chartHeight}`}
          className="h-full w-full"
          role="img"
          aria-label={mode === "cumulative" ? "Follower count chart" : "Follower delta chart"}
        >
        <defs>
          <linearGradient id="chartAreaFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0f766e" stopOpacity="0.24" />
            <stop offset="100%" stopColor="#0f766e" stopOpacity="0.03" />
          </linearGradient>
        </defs>

        {yTicks.map((tick, index) => {
          const y = mapY(tick);
          const label = Number.isInteger(tick) ? tick.toString() : tick.toFixed(1);

          return (
            <g key={`y-${index}`}>
              <line
                x1={MARGIN.left}
                x2={CHART_WIDTH - MARGIN.right}
                y1={y}
                y2={y}
                stroke="#e2e8f0"
                strokeDasharray="4 6"
              />
              <text
                x={MARGIN.left - 12}
                y={y}
                textAnchor="end"
                dominantBaseline="middle"
                fill="#475569"
                fontSize="14"
                fontWeight="600"
              >
                {label}
              </text>
            </g>
          );
        })}

        {mode === "delta" && (
          <line
            x1={MARGIN.left}
            x2={CHART_WIDTH - MARGIN.right}
            y1={zeroY}
            y2={zeroY}
            stroke="#94a3b8"
            strokeDasharray="4 4"
          />
        )}

        <line
          x1={MARGIN.left}
          x2={CHART_WIDTH - MARGIN.right}
          y1={MARGIN.top + plotHeight}
          y2={MARGIN.top + plotHeight}
          stroke="#cbd5e1"
        />

        {xTicks.map((tick, index) => (
          <text
            key={`x-${index}`}
            x={mapX(tick.x)}
            y={chartHeight - 10}
            textAnchor="middle"
            fill="#475569"
            fontSize="14"
            fontWeight="500"
          >
            {tick.label}
          </text>
        ))}

        {mode === "cumulative" && currentAreaPath && (
          <path d={currentAreaPath} fill="url(#chartAreaFill)" />
        )}

        {compareLinePath && (
          <path
            d={compareLinePath}
            fill="none"
            stroke="#94a3b8"
            strokeWidth="2"
            strokeDasharray="7 7"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}

        {currentLinePath && (
          <path
            d={currentLinePath}
            fill="none"
            stroke="#0f766e"
            strokeWidth={mode === "cumulative" ? (allCountsFlat ? 4 : 3) : (allDeltasFlat ? 3 : 2.5)}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}

        {mode === "delta" &&
          currentPoints.map((point, index) => (
            <line
              key={`stem-${index}`}
              x1={point.x}
              x2={point.x}
              y1={zeroY}
              y2={point.y}
              stroke={point.rawY < 0 ? "#e11d48" : "#0f766e"}
              strokeWidth="2"
              opacity={point.rawY === 0 ? 0.45 : 0.85}
            />
          ))}

        {(mode === "delta" || data.length <= 32 || allCountsFlat) &&
          currentPoints.map((point, index) => (
            <circle
              key={`point-${index}`}
              cx={point.x}
              cy={point.y}
              r={mode === "delta" ? 3.5 : 3}
              fill={mode === "delta" ? (point.rawY < 0 ? "#e11d48" : "#0f766e") : "#0f766e"}
              stroke="#fff"
              strokeWidth="1.5"
            >
              <title>{`${point.label}: ${point.rawY.toLocaleString()}`}</title>
            </circle>
          ))}

        {showAnnotations &&
          annotations.map((annotation) => (
            <circle
              key={annotation.key}
              cx={mapX(annotation.x)}
              cy={mapY(mode === "cumulative" ? annotation.value : (data.find((point) => point.x === annotation.x)?.currentDelta ?? 0))}
              r="5"
              fill={annotation.kind === "dip" || annotation.kind === "loss" ? "#e11d48" : "#0f766e"}
              stroke="#fff"
              strokeWidth="2"
            >
              <title>{`${annotation.label}: ${annotation.value.toLocaleString()}`}</title>
            </circle>
          ))}
        </svg>
      </div>
    </div>
  );
}
