import React, { useEffect, useRef } from "react";
import { Check, Circle, LoaderCircle } from "lucide-react";
import { InspectionStage } from "../types";

export interface ProcessingState {
  requestId: string;
  stage: InspectionStage;
  uploadPercent: number;
  filename?: string;
  resultNote?: string;
  resultMode?: "cached" | "reused_ocr" | "fresh";
}

const STEPS: { stage: InspectionStage; title: string; detail: string }[] = [
  { stage: "validation", title: "Validate image", detail: "File and image dimensions" },
  { stage: "quality", title: "Check image quality", detail: "Focus, lighting, and contrast" },
  { stage: "preprocessing", title: "Prepare image", detail: "Normalize for text recognition" },
  { stage: "ocr", title: "Read package text", detail: "Detect text and map its regions" },
  { stage: "nlp", title: "Extract declarations", detail: "Identify label fields and values" },
  { stage: "fusion", title: "Link evidence", detail: "Connect fields with image regions" },
  { stage: "compliance", title: "Run label checks", detail: "Apply configured screening rules" },
  { stage: "rendering", title: "Prepare annotations", detail: "Draw evidence on the image" },
  { stage: "persistence", title: "Save inspection", detail: "Store results in this workspace" },
];

export const InspectionProgress: React.FC<{ progress: ProcessingState; filename?: string }> = ({ progress, filename }) => {
  const dialogRef = useRef<HTMLElement>(null);
  const isCachedResult = progress.stage === "complete" && progress.resultMode === "cached";
  useEffect(() => {
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialogRef.current?.focus();
    return () => previousFocus?.focus({ preventScroll: true });
  }, []);

  const activeIndex = progress.stage === "complete" ? STEPS.length : progress.stage === "ocr_reused" ? STEPS.findIndex((step) => step.stage === "ocr") : STEPS.findIndex((step) => step.stage === progress.stage);
  const activeStep = STEPS[Math.max(activeIndex, 0)];
  const progressWidth = progress.stage === "complete"
    ? 100
    : progress.stage === "uploading"
      ? Math.max(3, progress.uploadPercent * 0.08)
      : Math.max(8, ((Math.max(activeIndex, 0) + 0.45) / STEPS.length) * 100);
  const title = progress.stage === "complete" ? (isCachedResult ? "Saved result loaded" : "Inspection complete") : progress.stage === "uploading" ? "Uploading package photo" : progress.stage === "failed" ? "Inspection stopped" : "Checking package label";

  return (
    <div className="inspection-progress-backdrop fixed inset-0 z-[100] grid place-items-center overflow-y-auto p-3 sm:p-6" role="dialog" aria-modal="true" aria-labelledby="inspection-progress-title" aria-describedby="inspection-progress-description">
      <section ref={dialogRef} tabIndex={-1} onKeyDown={(event) => { if (event.key === "Tab") { event.preventDefault(); dialogRef.current?.focus(); } }} className="inspection-progress-card my-auto w-full max-w-2xl overflow-hidden rounded-md border border-line bg-surface outline-none">
        <header className="border-b border-line px-5 py-4 sm:px-6">
          <p className="text-[9px] font-semibold uppercase tracking-[.14em] text-muted">LabelIntel / Check a pack</p>
          <div className="mt-2 flex items-start justify-between gap-4">
            <div className="min-w-0"><h1 id="inspection-progress-title" className="text-[17px] font-semibold tracking-tight text-ink">{title}</h1><p id="inspection-progress-description" className="mt-1 truncate text-[11px] text-muted">{filename || "Preparing photo"}</p></div>
            {progress.stage === "complete" ? <span className="mt-1 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200"><Check aria-hidden="true" className="h-4 w-4" /></span> : <LoaderCircle aria-hidden="true" className="mt-1 h-4 w-4 shrink-0 animate-spin text-ink" />}
          </div>
          <div className="mt-4 h-1.5 overflow-hidden rounded-sm bg-subtle" role="progressbar" aria-label="Inspection progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progressWidth)}><div className="h-full bg-[#171717] transition-[width] duration-500 dark:bg-[#f2f2f0]" style={{ width: `${progressWidth}%` }} /></div>
          <p className="mt-2 min-h-4 text-[10px] text-muted" aria-live="polite">{progress.stage === "uploading" ? `${progress.uploadPercent}% uploaded` : progress.stage === "complete" ? progress.resultNote || "All inspection operations are complete." : progress.stage === "ocr" ? "Reading text from the package. Dense labels can take longer." : progress.stage === "ocr_reused" ? "Using saved OCR regions for this bundled sample." : progress.stage === "queued" ? "Waiting for the inspection engine." : progress.stage === "checking_cache" ? "Checking for a saved result." : activeStep?.detail}</p>
        </header>

        {isCachedResult ? <div className="px-5 py-8 text-center sm:px-6"><p className="text-[13px] font-medium text-ink">This image already has a saved inspection.</p><p className="mt-1 text-[11px] text-muted">The saved OCR, image evidence, and assessment were opened without rerunning the pipeline.</p></div> : <ol className="max-h-[min(62vh,520px)] divide-y divide-line overflow-y-auto px-5 sm:px-6" aria-label="Inspection operations">
          {STEPS.map((step, index) => {
            const reused = progress.stage === "complete" && progress.resultMode === "reused_ocr" && step.stage === "ocr";
            const complete = progress.stage === "complete" || (activeIndex >= 0 && index < activeIndex);
            const active = progress.stage !== "complete" && index === activeIndex;
            return <li key={step.stage} aria-current={active ? "step" : undefined} className="flex items-center gap-3 py-2.5">
              <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${complete ? "border-[#171717] bg-[#171717] text-white dark:border-[#f2f2f0] dark:bg-[#f2f2f0] dark:text-[#171717]" : active ? "border-[#171717] text-ink dark:border-[#f2f2f0]" : "border-line text-muted"}`}>
                {complete ? <Check aria-hidden="true" className="h-3 w-3" /> : active ? <LoaderCircle aria-hidden="true" className="h-3 w-3 animate-spin" /> : <Circle aria-hidden="true" className="h-2 w-2 fill-current" />}
              </span>
              <span className="min-w-0 flex-1"><span className={`block text-[11px] ${complete || active ? "font-medium text-ink" : "text-muted"}`}>{step.title}</span><span className="mt-0.5 block text-[9px] text-muted">{step.detail}</span></span>
              {complete && <span className="text-[9px] text-muted">{reused ? "Reused" : "Done"}</span>}
              {active && <span className="text-[9px] font-medium text-ink">In progress</span>}
            </li>;
          })}
        </ol>}
      </section>
    </div>
  );
};
