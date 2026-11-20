import React, { useRef, useState } from "react";
import { ArrowUpRight, Camera, Clock3, Image as ImageIcon, Loader2 } from "lucide-react";
import { api } from "../api";
import { InspectionSummary, SampleImage } from "../types";

interface ImageUploaderProps {
  onUpload: (file: File, category?: string) => Promise<void>;
  onSelectSample: (samplePath: string) => Promise<void>;
  onOpenInspection: (id: string) => void;
  onViewHistory: () => void;
  samples: SampleImage[];
  inspections: InspectionSummary[];
  dataLoading: boolean;
  isLoading: boolean;
}

const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;
const ACCEPTED_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/avif"]);
const CATEGORIES = ["food", "beverages", "cosmetics", "household", "other"];

export const ImageUploader: React.FC<ImageUploaderProps> = ({ onUpload, onSelectSample, onOpenInspection, onViewHistory, samples, inspections, dataLoading, isLoading }) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState("food");
  const [localError, setLocalError] = useState<string | null>(null);
  const [processingSamplePath, setProcessingSamplePath] = useState<string | null>(null);
  const dragDepth = useRef(0);

  const uploadFile = async (file?: File) => {
    if (!file) return;
    setLocalError(null);
    if (!ACCEPTED_TYPES.has(file.type)) {
      setLocalError("Choose a JPEG, PNG, WebP, or AVIF image.");
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setLocalError("This image is over the 25 MB upload limit. Choose a smaller file.");
      return;
    }
    await onUpload(file, selectedCategory);
  };

  const handleDrop = async (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    dragDepth.current = 0;
    setDragActive(false);
    if (!isLoading) await uploadFile(event.dataTransfer.files?.[0]);
  };

  const handleChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = "";
    if (!isLoading) await uploadFile(file);
  };

  const selectSample = async (samplePath: string) => {
    if (isLoading) return;
    setProcessingSamplePath(samplePath);
    try { await onSelectSample(samplePath); }
    finally { setProcessingSamplePath(null); }
  };

  return (
    <div className="mx-auto grid w-full max-w-[1400px] grid-cols-1 items-start gap-6 px-5 pb-10 pt-7 sm:px-8 sm:pt-8 xl:grid-cols-12 xl:gap-8">
      <header className="xl:col-span-12">
        <h1 className="text-[26px] font-bold tracking-tight text-ink">Check a pack</h1>
        <p className="mt-1.5 max-w-4xl text-[13px] leading-relaxed text-muted">Add a clear photo of the product label. LabelIntel reads visible text and links potential declarations to image evidence for review.</p>
      </header>

      <section className="flex flex-col gap-5 xl:col-span-5" aria-label="Upload and recent inspections">
        <div className="rounded-md border border-line bg-surface p-5">
          <div className="mb-3.5 flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-ink">Your photo</h2>
            <span className="text-[11px] text-muted">One image per check</span>
          </div>

          <div
            onDragEnter={(event) => { event.preventDefault(); dragDepth.current += 1; setDragActive(true); }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={(event) => { event.preventDefault(); dragDepth.current = Math.max(0, dragDepth.current - 1); if (dragDepth.current === 0) setDragActive(false); }}
            onDrop={handleDrop}
            aria-busy={isLoading}
            className={`rounded-sm border border-dashed px-4 py-7 text-center transition-colors focus-within:ring-2 focus-within:ring-ink/20 ${dragActive ? "border-ink bg-subtle" : "border-line bg-subtle/50 hover:bg-subtle"}`}
          >
            <input type="file" id="file-upload" className="sr-only" accept="image/jpeg,image/png,image/webp,image/avif" onChange={handleChange} disabled={isLoading} aria-label="Choose a packaging photo" />
            <p className="text-[13px] text-muted">{dragActive ? "Drop the photo to start" : "Drop a package photo here, or"}</p>
            <label htmlFor="file-upload" className={`mt-3 inline-flex h-9 cursor-pointer items-center gap-2 rounded-sm border border-line bg-surface px-3.5 text-[12px] font-medium text-ink transition hover:bg-subtle focus-within:ring-2 focus-within:ring-ink/20 ${isLoading ? "pointer-events-none opacity-60" : ""}`}>
              {isLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin text-muted" /> : <Camera className="h-3.5 w-3.5 text-muted" />}
              {isLoading ? "Inspection in progress" : "Choose a photo"}
            </label>
            <p className="mt-3 text-[10px] text-muted">JPEG, PNG, WebP, or AVIF · up to 25 MB</p>
          </div>

          <div className="mt-5">
            <h3 className="text-[13px] font-medium text-ink">Kind of commodity</h3>
            <div role="group" aria-label="Product category" className="mt-2 grid grid-cols-5 gap-1 rounded-md border border-line bg-subtle p-1">
              {CATEGORIES.map((category) => <button key={category} type="button" aria-pressed={selectedCategory === category} onClick={() => setSelectedCategory(category)} disabled={isLoading} className={`min-w-0 rounded px-1 py-1.5 text-[10px] font-medium capitalize transition-colors disabled:cursor-not-allowed ${selectedCategory === category ? "bg-surface text-ink shadow-sm" : "text-muted hover:text-ink"}`}>{category}</button>)}
            </div>
            <p className="mt-1.5 text-[10px] leading-4 text-muted">This category guides the automated screening checks.</p>
          </div>
          {localError && <p role="alert" className="mt-4 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-[11px] text-rose-900 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-200">{localError}</p>}
        </div>

        <section className="rounded-md border border-line bg-surface p-5" aria-label="Recent inspections">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-ink">Checked before</h2>
            <button type="button" onClick={onViewHistory} className="text-[11px] font-medium text-muted transition hover:text-ink">View history <span aria-hidden="true">→</span></button>
          </div>
          {dataLoading && inspections.length === 0 ? <div className="space-y-3" aria-label="Loading recent inspections">{Array.from({ length: 3 }, (_, index) => <div key={index} className="flex items-center gap-3 py-1"><span className="h-10 w-10 animate-pulse rounded bg-subtle" /><span className="flex-1 space-y-2"><span className="block h-3 w-3/4 animate-pulse rounded bg-subtle" /><span className="block h-2.5 w-1/2 animate-pulse rounded bg-subtle" /></span></div>)}</div> : inspections.length === 0 ? <div className="rounded-lg bg-subtle px-4 py-6 text-center"><Clock3 className="mx-auto h-4 w-4 text-muted" /><p className="mt-2 text-[11px] font-medium text-ink">Your recent checks will appear here</p><p className="mt-1 text-[10px] text-muted">Completed inspections are saved to this workspace.</p></div> : <div className="divide-y divide-line">
            {inspections.slice(0, 3).map((item) => <button key={item.id} type="button" onClick={() => onOpenInspection(item.id)} className="group flex w-full items-center gap-3 py-3 text-left first:pt-0 last:pb-0">
              <span className="h-10 w-10 shrink-0 overflow-hidden rounded border border-line bg-subtle"><img src={api.getImageUrl(item.image_url)} alt="" loading="lazy" className="h-full w-full object-cover transition-transform group-hover:scale-105" /></span>
              <span className="min-w-0 flex-1"><span className="block truncate text-[12px] font-semibold text-ink group-hover:underline">{item.filename}</span><span className="mt-1 block truncate text-[10px] text-muted">{formatDate(item.created_at)} · {item.category || "Uncategorized"}</span></span>
              <StatusChip value={item.overall_compliance} /><ArrowUpRight aria-hidden="true" className="h-3.5 w-3.5 shrink-0 text-muted" />
            </button>)}
          </div>}
        </section>
      </section>

      <section className="rounded-md border border-line bg-surface p-5 xl:col-span-7" aria-label="Sample package images">
        <div className="flex items-center justify-between gap-4 border-b border-line pb-4">
          <div><h2 className="text-[15px] font-semibold text-ink">Or try a sample pack</h2><p className="mt-1 text-[11px] text-muted">Run a check on a real package photo from this workspace.</p></div>
          <span className="shrink-0 font-mono text-[11px] text-muted">{samples.length} samples</span>
        </div>
        {dataLoading && samples.length === 0 ? <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4" aria-label="Loading sample photos">{Array.from({ length: 8 }, (_, index) => <div key={index}><div className="aspect-[4/5] animate-pulse rounded-md bg-subtle" /><div className="mt-2 h-3 w-4/5 animate-pulse rounded bg-subtle" /></div>)}</div> : samples.length === 0 ? <div className="py-14 text-center"><ImageIcon className="mx-auto h-5 w-5 text-muted" /><p className="mt-3 text-[12px] font-medium text-ink">No sample photos available</p><p className="mt-1 text-[10px] text-muted">You can still upload a product photo to inspect it.</p></div> : <div className="mt-5 grid grid-cols-2 gap-x-3 gap-y-5 sm:grid-cols-3 xl:grid-cols-4">
          {samples.map((sample) => <button key={sample.relative_path} type="button" onClick={() => void selectSample(sample.relative_path)} disabled={isLoading} className="group flex min-w-0 flex-col text-left disabled:cursor-not-allowed disabled:opacity-50">
            <span className="relative block aspect-[4/5] w-full overflow-hidden rounded-md border border-line bg-subtle transition group-hover:-translate-y-0.5 group-hover:shadow-md">
              <img src={api.getSampleImageUrl(sample.relative_path)} alt={`${sample.category} package sample`} loading="lazy" className="h-full w-full object-contain p-1.5 transition-transform duration-200 group-hover:scale-[1.025]" />
              <span className="absolute left-2 top-2 rounded-sm border border-black/10 bg-white/90 px-1.5 py-1 text-[8px] font-semibold uppercase tracking-wide text-gray-700 shadow-sm dark:border-white/10 dark:bg-[#14161a]/90 dark:text-gray-200">{sample.category}</span>
              {processingSamplePath === sample.relative_path && <span className="absolute inset-0 flex items-center justify-center bg-black/40 text-white"><Loader2 className="h-5 w-5 animate-spin" /></span>}
            </span>
            <span className="mt-2 line-clamp-2 text-[11px] font-medium leading-4 text-ink transition-colors group-hover:underline">{displayName(sample.filename)}</span>
            <span className="mt-0.5 text-[10px] text-muted">{(sample.size_bytes / 1024).toFixed(0)} KB · click to inspect</span>
          </button>)}
        </div>}
      </section>
    </div>
  );
};

function displayName(filename: string) {
  return filename.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value?: string | null) {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  const today = new Date();
  if (date.toDateString() === today.toDateString()) return `Today · ${new Intl.DateTimeFormat(undefined, { timeStyle: "short" }).format(date)}`;
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

function StatusChip({ value }: { value?: string }) {
  const status = (value || "unknown").toLowerCase().replace(/[ _-]+/g, " ");
  const tone = status === "compliant" ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-300" : status === "non compliant" ? "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-300" : "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-200";
  const label = status === "compliant" ? "Passes" : status === "non compliant" ? "Fails" : status === "flagged for review" ? "Review" : "Unknown";
  return <span className={`hidden shrink-0 rounded-full border px-2 py-0.5 text-[9px] font-medium sm:inline-block ${tone}`}>{label}</span>;
}
