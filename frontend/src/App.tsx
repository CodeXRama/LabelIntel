import React, { useEffect, useState } from "react";
import { Header } from "./components/Header";
import { ImageUploader } from "./components/ImageUploader";
import { AnnotationViewer } from "./components/AnnotationViewer";
import { QualityCard } from "./components/QualityCard";
import { DeclarationsList } from "./components/DeclarationsList";
import { ComplianceCard } from "./components/ComplianceCard";
import { api } from "./api";
import { InspectionData, SampleImage } from "./types";
import { ArrowLeft, RefreshCw, AlertCircle } from "lucide-react";

export const App: React.FC = () => {
  const [samples, setSamples] = useState<SampleImage[]>([]);
  const [inspection, setInspection] = useState<InspectionData | null>(null);
  const [selectedDeclarationId, setSelectedDeclarationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    loadSamples();
  }, []);

  const loadSamples = async () => {
    try {
      const data = await api.getSamples();
      setSamples(data);
    } catch (err) {
      console.error("Failed to load sample packaging list:", err);
    }
  };

  const handleUpload = async (file: File, category?: string) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await api.uploadAndInspect(file, category);
      setInspection(data);
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
      const data = await api.runDemoSample(samplePath);
      setInspection(data);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Failed to run sample inspection.";
      setErrorMessage(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setInspection(null);
    setSelectedDeclarationId(null);
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        {errorMessage && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-slate-400 hover:text-white"
            >
              &times;
            </button>
          </div>
        )}

        {!inspection ? (
          <div className="max-w-3xl mx-auto py-8">
            <div className="text-center space-y-2 mb-8">
              <h2 className="text-2xl font-bold tracking-tight text-white">
                Packaged Commodity Verification
              </h2>
              <p className="text-sm text-slate-400 max-w-lg mx-auto">
                Upload commodity packaging to run Stage 1-4 Computer Vision, textline extraction,
                OCR-to-field evidence fusion, and Legal Metrology compliance checks.
              </p>
            </div>

            <ImageUploader
              onUpload={handleUpload}
              onSelectSample={handleSelectSample}
              samples={samples}
              isLoading={isLoading}
            />
          </div>
        ) : (
          <div className="space-y-6">
            {/* Top Action Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-4 rounded-2xl shadow">
              <div className="flex items-center space-x-3">
                <button
                  onClick={handleReset}
                  className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition flex items-center space-x-1.5 text-xs"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back to Upload</span>
                </button>
                <div>
                  <h2 className="text-sm font-semibold text-white truncate max-w-md">
                    {inspection.filename}
                  </h2>
                  <p className="text-[11px] text-slate-400">
                    Inspection ID: <span className="font-mono text-indigo-400">{inspection.id}</span> &bull; Pipeline duration:{" "}
                    <span className="font-mono text-emerald-400">{inspection.timing_ms.total_pipeline_ms} ms</span>
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-300">
                  Detected: <strong className="text-white">{inspection.ocr_summary.total_blocks}</strong> textlines
                </span>
                <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-300">
                  Avg OCR: <strong className="text-emerald-400">{(inspection.ocr_summary.average_confidence * 100).toFixed(1)}%</strong>
                </span>
              </div>
            </div>

            {/* Inspection Workspace Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Column: Visual Image & SVG Polygon Overlay (7 cols) */}
              <div className="lg:col-span-7 space-y-6">
                <AnnotationViewer
                  rawImageUrl={api.getImageUrl(inspection.image_url)}
                  annotatedImageUrl={api.getImageUrl(inspection.annotated_url)}
                  declarations={inspection.fused_declarations}
                  selectedDeclarationId={selectedDeclarationId}
                  onSelectDeclaration={setSelectedDeclarationId}
                  width={inspection.metadata.width}
                  height={inspection.metadata.height}
                />

                <QualityCard quality={inspection.quality} />
              </div>

              {/* Right Column: Compliance & Fused Declarations (5 cols) */}
              <div className="lg:col-span-5 space-y-6">
                <ComplianceCard report={inspection.compliance_report} />

                <DeclarationsList
                  declarations={inspection.fused_declarations}
                  selectedDeclarationId={selectedDeclarationId}
                  onSelectDeclaration={setSelectedDeclarationId}
                />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
