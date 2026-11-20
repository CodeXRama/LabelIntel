import React, { useCallback, useEffect, useState } from "react";
import { AlertCircle, ArrowLeft, Loader2 } from "lucide-react";
import { AnnotationViewer } from "./components/AnnotationViewer";
import { ComplianceCard } from "./components/ComplianceCard";
import { DeclarationsList } from "./components/DeclarationsList";
import { ImageUploader } from "./components/ImageUploader";
import { InspectionDashboard } from "./components/InspectionDashboard";
import { InspectorLayout, InspectorSection, ThemeMode } from "./components/InspectorLayout";
import { InspectionProgress, ProcessingState } from "./components/InspectionProgress";
import { QualityCard } from "./components/QualityCard";
import { api } from "./api";
import { InspectionAnalytics, InspectionData, InspectionSummary, SampleImage } from "./types";

function getLocationRoute(): { section: InspectorSection; inspectionId?: string } {
  let route = window.location.hash.replace(/^#\/?/, "");
  try { route = decodeURIComponent(route); } catch { /* Ignore malformed fragments and use the dashboard route. */ }
  if (route.startsWith("inspection/")) return { section: "inspection", inspectionId: route.slice("inspection/".length) };
  if (route === "new" || route === "history") return { section: route };
  return { section: "dashboard" };
}

function getInitialTheme(): ThemeMode {
  try {
    const saved = localStorage.getItem("labelintel-theme");
    if (saved === "light" || saved === "dark") return saved;
  } catch { /* Fall back to the OS preference when storage is disabled. */ }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export const App: React.FC = () => {
  const [theme, setTheme] = useState<ThemeMode>(getInitialTheme);
  const [samples, setSamples] = useState<SampleImage[]>([]);
  const [inspections, setInspections] = useState<InspectionSummary[]>([]);
  const [analytics, setAnalytics] = useState<InspectionAnalytics | null>(null);
  const [inspection, setInspection] = useState<InspectionData | null>(null);
  const [selectedDeclarationId, setSelectedDeclarationId] = useState<string | null>(null);
  const [section, setSection] = useState<InspectorSection>(() => getLocationRoute().section);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [processing, setProcessing] = useState<ProcessingState | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [health, setHealth] = useState<"online" | "offline" | "checking">("checking");

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "dark" ? "#111110" : "#f4f4f2");
    try { localStorage.setItem("labelintel-theme", theme); } catch { /* Keep the selected mode for this session. */ }
  }, [theme]);

  const refreshDashboard = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const [, records, imageSamples, inspectionAnalytics] = await Promise.all([api.getHealth(), api.getInspections(), api.getSamples(), api.getInspectionAnalytics()]);
      setInspections(records);
      setSamples(imageSamples);
      setAnalytics(inspectionAnalytics);
      setHealth("online");
      setErrorMessage(null);
    } catch (err) {
      console.error("Unable to refresh LabelIntel dashboard:", err);
      setHealth("offline");
      setErrorMessage("LabelIntel could not reach the API. Check that the backend is running, then retry.");
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  const openSavedInspection = useCallback(async (id: string, addHistory = true) => {
    setIsLoading(true);
    setErrorMessage(null);
    setInspection(null);
    setSection("inspection");
    if (addHistory) window.history.pushState(null, "", `#inspection/${encodeURIComponent(id)}`);
    try {
      const data = await api.getInspection(id);
      setInspection(data);
      setSelectedDeclarationId(null);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Could not open this inspection.";
      setErrorMessage(typeof msg === "string" ? msg : JSON.stringify(msg));
      setSection("history");
      window.history.replaceState(null, "", "#history");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const runWithProgress = async (
    filename: string,
    initialStage: ProcessingState["stage"],
    operation: (requestId: string, onUploadProgress: (percent: number) => void) => Promise<InspectionData>,
  ) => {
    const requestId = window.crypto?.randomUUID?.() || `li-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const controller = new AbortController();
    setProcessing({ requestId, stage: initialStage, uploadPercent: 0, filename });

    const watchProgress = async () => {
      while (!controller.signal.aborted) {
        try {
          const result = await api.getInspectionProgress(requestId, controller.signal);
          // The response payload tells us whether this was a fresh run or a cache hit.
          // Keep the stage animation open until that metadata is available so a cache
          // hit never flashes every pipeline operation as if it had just run.
          if (result.stage !== "waiting" && result.stage !== "complete") {
            setProcessing((current) => current?.requestId === requestId && current.stage !== "complete"
              ? { ...current, stage: result.stage }
              : current);
          }
        } catch {
          if (controller.signal.aborted) break;
        }
        await new Promise((resolve) => window.setTimeout(resolve, 320));
      }
    };
    const watcher = watchProgress();

    try {
      const data = await operation(requestId, (percent) => {
        setProcessing((current) => current?.requestId === requestId ? { ...current, uploadPercent: percent } : current);
      });
      setProcessing((current) => current?.requestId === requestId ? {
        ...current,
        stage: "complete",
        uploadPercent: 100,
        resultMode: data.reused_existing ? "cached" : data.ocr_reused ? "reused_ocr" : "fresh",
        resultNote: data.reused_existing ? "Loaded the saved inspection result." : data.ocr_reused ? "Inspection complete using the saved sample OCR evaluation." : "All inspection operations are complete.",
      } : current);
      await new Promise((resolve) => window.setTimeout(resolve, 650));
      return data;
    } finally {
      controller.abort();
      await watcher;
      setProcessing((current) => current?.requestId === requestId ? null : current);
    }
  };

  useEffect(() => {
    void refreshDashboard();
    const initialRoute = getLocationRoute();
    if (initialRoute.inspectionId) void openSavedInspection(initialRoute.inspectionId, false);
    else if (initialRoute.section === "new" || initialRoute.section === "history") setSection(initialRoute.section);

    const handleLocationChange = () => {
      const route = getLocationRoute();
      if (route.inspectionId) {
        void openSavedInspection(route.inspectionId, false);
        return;
      }
      setInspection(null);
      setSection(route.section);
      setErrorMessage(null);
      if (route.section === "dashboard" || route.section === "history") void refreshDashboard();
    };
    window.addEventListener("hashchange", handleLocationChange);
    return () => {
      window.removeEventListener("hashchange", handleLocationChange);
    };
  }, [openSavedInspection, refreshDashboard]);

  const handleUpload = async (file: File, category?: string) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await runWithProgress(file.name, "uploading", (requestId, onUploadProgress) => api.uploadAndInspect(file, category, requestId, onUploadProgress));
      setInspection(data);
      setSelectedDeclarationId(null);
      setSection("inspection");
      window.history.pushState(null, "", `#inspection/${encodeURIComponent(data.id)}`);
      void refreshDashboard();
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Failed to inspect image.";
      setErrorMessage(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectSample = async (samplePath: string) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await runWithProgress(samplePath.split("/").pop() || "Sample image", "checking_cache", (requestId) => api.runDemoSample(samplePath, requestId));
      setInspection(data);
      setSelectedDeclarationId(null);
      setSection("inspection");
      window.history.pushState(null, "", `#inspection/${encodeURIComponent(data.id)}`);
      void refreshDashboard();
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Failed to run sample inspection.";
      setErrorMessage(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportFindings = async () => {
    try {
      const blob = await api.exportFindings();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "labelintel-findings.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || "Could not export inspection findings.";
      setErrorMessage(typeof message === "string" ? message : JSON.stringify(message));
    }
  };

  const navigate = (next: InspectorSection) => {
    setErrorMessage(null);
    if (next !== "inspection") setInspection(null);
    setSection(next);
    window.history.pushState(null, "", `#${next}`);
    if (next === "dashboard" || next === "history") void refreshDashboard();
  };

  const activeSection = section;

  return (
    <InspectorLayout
      active={activeSection}
      onNavigate={navigate}
      health={health}
      theme={theme}
      onToggleTheme={() => setTheme((current) => current === "light" ? "dark" : "light")}
    >
      {errorMessage && <div role="alert" className="mx-4 mt-4 flex items-center justify-between gap-3 rounded-md border border-rose-300 bg-rose-50 px-4 py-3 text-xs text-rose-900 dark:border-rose-900/70 dark:bg-rose-950/50 dark:text-rose-200 sm:mx-5 lg:mx-8"><div className="flex items-center gap-2"><AlertCircle className="h-4 w-4 shrink-0" /><span>{errorMessage}</span></div><button type="button" onClick={() => setErrorMessage(null)} className="text-lg leading-none text-rose-500 hover:text-rose-800 dark:hover:text-rose-200" aria-label="Dismiss error">×</button></div>}

      {processing && <InspectionProgress progress={processing} filename={processing.filename} />}

      {(section === "dashboard" || section === "history") && <InspectionDashboard
        inspections={inspections}
        analytics={analytics}
        loading={isRefreshing && inspections.length === 0 && health === "checking"}
        refreshing={isRefreshing}
        health={health}
        historyMode={section === "history"}
        onRefresh={refreshDashboard}
        onOpenInspection={openSavedInspection}
        onNewInspection={() => navigate("new")}
        onExportFindings={handleExportFindings}
        onViewHistory={() => navigate("history")}
      />}

      {section === "new" && <ImageUploader
        onUpload={handleUpload}
        onSelectSample={handleSelectSample}
        onOpenInspection={(id) => void openSavedInspection(id)}
        onViewHistory={() => navigate("history")}
        samples={samples}
        inspections={inspections}
        dataLoading={isRefreshing && samples.length === 0 && inspections.length === 0}
        isLoading={isLoading}
      />}

      {section === "inspection" && (inspection ? <div className="mx-auto max-w-[1400px] space-y-3 px-4 py-5 sm:px-7 sm:py-6">
        <div className="text-[11px] text-muted">Check a pack <span className="px-1">/</span> <span className="text-ink">{inspection.filename}</span></div>
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-md border border-line bg-surface px-4 py-3 sm:px-5">
          <div className="flex min-w-0 items-center gap-3">
            <img src={api.getImageUrl(inspection.image_url)} alt="" className="h-12 w-12 shrink-0 rounded-sm border border-line object-cover" />
            <div className="min-w-0"><h1 className="truncate text-[15px] font-semibold tracking-tight text-ink">{inspection.filename}</h1><p className="mt-1 truncate text-[10px] text-muted">{inspection.category || "Package"} / {inspection.metadata.width} x {inspection.metadata.height} px / {inspection.ocr_summary.total_blocks} text regions / {inspection.reused_existing ? "Saved result" : inspection.ocr_reused ? "Sample OCR reused" : `${inspection.timing_ms.total_pipeline_ms.toFixed(0)} ms`}</p></div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <OverallStatus status={inspection.compliance_report.overall_status} />
            <button type="button" onClick={() => navigate("history")} className="hidden h-9 items-center gap-1.5 rounded-md border border-line px-3 text-[11px] font-medium text-ink transition hover:bg-subtle sm:inline-flex"><ArrowLeft aria-hidden="true" className="h-3.5 w-3.5" /> History</button>
            <button type="button" onClick={() => navigate("new")} className="h-9 rounded-md bg-[#171717] px-3.5 text-[11px] font-medium text-white transition hover:bg-black dark:bg-[#f2f2f0] dark:text-[#171717] dark:hover:bg-white">Check another</button>
          </div>
        </div>
        {!!inspection.processing_warnings?.length && <div className="border-l-2 border-amber-500 bg-amber-50 px-3 py-2 text-[11px] leading-4 text-amber-950 dark:bg-[#281f12] dark:text-amber-100">{inspection.processing_warnings.map((warning, index) => <p key={index}>{warning}</p>)}</div>}
        <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-12">
          <div className="space-y-4 lg:col-span-7"><AnnotationViewer rawImageUrl={api.getImageUrl(inspection.image_url)} annotatedImageUrl={api.getImageUrl(inspection.annotated_url)} declarations={inspection.fused_declarations} ocrBlocks={inspection.ocr_blocks || []} selectedDeclarationId={selectedDeclarationId} onSelectDeclaration={setSelectedDeclarationId} width={inspection.metadata.width} height={inspection.metadata.height} /><DeclarationsList declarations={inspection.fused_declarations} selectedDeclarationId={selectedDeclarationId} onSelectDeclaration={setSelectedDeclarationId} /><QualityCard quality={inspection.quality} /></div>
          <div className="lg:col-span-5"><ComplianceCard report={inspection.compliance_report} declarations={inspection.fused_declarations} selectedDeclarationId={selectedDeclarationId} onSelectDeclaration={setSelectedDeclarationId} /></div>
        </div>
      </div> : <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3 text-muted"><Loader2 className="h-5 w-5 animate-spin" /><p className="text-xs">Loading saved inspection...</p><button type="button" onClick={() => navigate("history")} className="text-xs font-medium text-ink underline underline-offset-2">Back to inspection history</button></div>)}
    </InspectorLayout>
  );
};


function OverallStatus({ status }: { status: string }) {
  const normalized = status.toLowerCase().replace(/[ -]+/g, "_");
  const config = normalized === "compliant"
    ? { label: "Passes", classes: "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200" }
    : normalized === "non_compliant"
      ? { label: "Fails", classes: "bg-rose-100 text-rose-900 dark:bg-rose-950 dark:text-rose-200" }
      : normalized === "flagged_for_review"
        ? { label: "Review", classes: "bg-amber-100 text-amber-950 dark:bg-amber-950 dark:text-amber-200" }
        : { label: "N/A", classes: "bg-subtle text-muted" };
  return <span className={`whitespace-nowrap rounded-full px-2.5 py-1 text-[10px] font-medium ${config.classes}`}>{config.label}</span>;
}
