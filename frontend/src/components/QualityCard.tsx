import React from "react";
import { AlertTriangle, CheckCircle2, Sliders, Sun, ShieldAlert } from "lucide-react";
import { ImageQualityMetrics } from "../types";

interface QualityCardProps {
  quality: ImageQualityMetrics;
}

export const QualityCard: React.FC<QualityCardProps> = ({ quality }) => {
  const hasWarnings = quality.quality_warnings && quality.quality_warnings.length > 0;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Sliders className="w-4 h-4 text-indigo-400" />
          <h3 className="text-sm font-semibold text-slate-200">Image Quality Assessment</h3>
        </div>
        {hasWarnings ? (
          <span className="flex items-center space-x-1 text-xs px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Quality Alerts</span>
          </span>
        ) : (
          <span className="flex items-center space-x-1 text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Optimal Fidelity</span>
          </span>
        )}
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
          <span className="text-slate-400 block mb-1">Sharpness (Laplacian)</span>
          <span className="text-base font-bold text-white font-mono">
            {quality.blur_laplacian_variance.toFixed(1)}
          </span>
          <span className={`block text-[10px] mt-0.5 ${quality.is_blurry ? "text-red-400" : "text-emerald-400"}`}>
            {quality.is_blurry ? "Degraded / Blurry" : "Sharp focus"}
          </span>
        </div>

        <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
          <span className="text-slate-400 block mb-1">Mean Luminance</span>
          <span className="text-base font-bold text-white font-mono">
            {quality.brightness_mean.toFixed(1)}
            <span className="text-xs text-slate-500 font-normal"> / 255</span>
          </span>
          <span className="block text-[10px] mt-0.5 text-slate-400">
            {quality.brightness_mean < 80 ? "Dim lighting" : quality.brightness_mean > 190 ? "Bright lighting" : "Even lighting"}
          </span>
        </div>

        <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
          <span className="text-slate-400 block mb-1">Contrast Std Dev</span>
          <span className="text-base font-bold text-white font-mono">
            {quality.contrast_std.toFixed(1)}
          </span>
          <span className="block text-[10px] mt-0.5 text-slate-400">Dynamic range</span>
        </div>

        <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
          <span className="text-slate-400 block mb-1">Highlight Saturated</span>
          <span className="text-base font-bold text-white font-mono">
            {(quality.clipping_high_pct * 100).toFixed(1)}%
          </span>
          <span className={`block text-[10px] mt-0.5 ${quality.clipping_high_pct > 0.05 ? "text-amber-400" : "text-slate-400"}`}>
            {quality.clipping_high_pct > 0.05 ? "Specular flash glare" : "Negligible glare"}
          </span>
        </div>
      </div>

      {/* Warnings List */}
      {hasWarnings && (
        <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-3 space-y-1.5">
          {quality.quality_warnings.map((w, idx) => (
            <div key={idx} className="flex items-start space-x-2 text-xs text-amber-300">
              <ShieldAlert className="w-3.5 h-3.5 mt-0.5 shrink-0 text-amber-400" />
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
