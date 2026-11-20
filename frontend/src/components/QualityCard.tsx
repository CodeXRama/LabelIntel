import React from "react";
import { AlertTriangle, CheckCircle2, SlidersHorizontal, ShieldAlert, Sun } from "lucide-react";
import { ImageQualityMetrics } from "../types";

interface QualityCardProps { quality: ImageQualityMetrics; }

export const QualityCard: React.FC<QualityCardProps> = ({ quality }) => {
  const warnings = quality.quality_warnings || [];
  const hasWarnings = warnings.length > 0;
  return (
    <section className="space-y-4 rounded-md border border-line bg-surface p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2"><SlidersHorizontal aria-hidden="true" className="h-4 w-4 text-muted" /><h2 className="text-xs font-semibold text-ink">Image quality</h2></div>
        <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[9px] font-semibold ${hasWarnings ? "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200" : "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300"}`}>
          {hasWarnings ? <AlertTriangle aria-hidden="true" className="h-3.5 w-3.5" /> : <CheckCircle2 aria-hidden="true" className="h-3.5 w-3.5" />}{hasWarnings ? "Review image quality" : "No quality warnings"}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Metric label="Sharpness" value={quality.blur_laplacian_variance.toFixed(1)} detail={quality.is_blurry ? "Blur detected" : "No blur flag"} tone={quality.is_blurry ? "amber" : "green"} />
        <Metric label="Brightness" value={`${quality.brightness_mean.toFixed(1)} / 255`} detail={quality.is_under_exposed ? "Under exposed" : quality.is_over_exposed ? "Over exposed" : "Exposure range"} tone={quality.is_under_exposed || quality.is_over_exposed ? "amber" : "neutral"} icon={<Sun aria-hidden="true" className="h-3.5 w-3.5" />} />
        <Metric label="Contrast" value={quality.contrast_std.toFixed(1)} detail="Standard deviation" tone="neutral" />
        <Metric label="Clipped highlights" value={`${(quality.clipping_high_pct * 100).toFixed(1)}%`} detail={`Dark clipping ${(quality.clipping_low_pct * 100).toFixed(1)}%`} tone={quality.clipping_high_pct > 0.05 ? "amber" : "neutral"} />
      </div>
      {hasWarnings && <ul className="space-y-1.5 rounded-xl border border-amber-200 bg-amber-50/70 p-3 dark:border-amber-900 dark:bg-amber-950/30">{warnings.map((warning, index) => <li key={index} className="flex items-start gap-2 text-[10px] leading-4 text-amber-900 dark:text-amber-200"><ShieldAlert aria-hidden="true" className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600 dark:text-amber-400" />{warning}</li>)}</ul>}
    </section>
  );
};

function Metric({ label, value, detail, tone, icon }: { label: string; value: string; detail: string; tone: "green" | "amber" | "neutral"; icon?: React.ReactNode }) {
  const toneClass = tone === "green" ? "text-emerald-700 dark:text-emerald-300" : tone === "amber" ? "text-amber-700 dark:text-amber-300" : "text-ink";
  return <div className="min-w-0 rounded-sm border border-line bg-subtle/70 p-3"><span className="flex items-center gap-1 text-[9px] font-medium text-muted">{icon}{label}</span><span className={`mt-1 block truncate font-mono text-sm font-bold ${toneClass}`}>{value}</span><span className="mt-0.5 block truncate text-[9px] text-muted">{detail}</span></div>;
}
