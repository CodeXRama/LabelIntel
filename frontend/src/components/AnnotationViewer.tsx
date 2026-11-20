import React, { useEffect, useState } from "react";
import { Eye, Layers, Maximize2, RotateCcw, ScanText } from "lucide-react";
import { FusedDeclaration, OCRTextBlock } from "../types";

interface AnnotationViewerProps {
  rawImageUrl: string;
  annotatedImageUrl: string;
  declarations: FusedDeclaration[];
  ocrBlocks: OCRTextBlock[];
  selectedDeclarationId: string | null;
  onSelectDeclaration: (id: string | null) => void;
  width: number;
  height: number;
}

type ViewMode = "declarations" | "ocr" | "rendered";

export const AnnotationViewer: React.FC<AnnotationViewerProps> = ({
  rawImageUrl, annotatedImageUrl, declarations, ocrBlocks, selectedDeclarationId,
  onSelectDeclaration, width, height,
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>(declarations.length ? "declarations" : "ocr");
  const [zoomed, setZoomed] = useState(false);
  useEffect(() => {
    if (selectedDeclarationId) setViewMode("declarations");
  }, [selectedDeclarationId]);
  const sourceAlt = "Source commodity packaging with image-grounded detection overlays";

  return (
    <section className="overflow-hidden rounded-md border border-line bg-surface" aria-label="Image evidence viewer">
      <div className="flex flex-col gap-3 border-b border-line px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0"><h2 className="text-xs font-semibold text-ink">Image evidence</h2><p className="mt-0.5 text-[10px] text-muted">{ocrBlocks.length} OCR regions · {declarations.length} linked declarations · {width} × {height} px</p></div>
        <div className="flex flex-wrap items-center gap-0.5 rounded-md border border-line bg-subtle p-0.5" role="group" aria-label="Overlay view">
          <ViewButton active={viewMode === "declarations"} onClick={() => setViewMode("declarations")} icon={<Layers className="h-3.5 w-3.5" />} label="Fields" count={declarations.length} />
          <ViewButton active={viewMode === "ocr"} onClick={() => setViewMode("ocr")} icon={<ScanText className="h-3.5 w-3.5" />} label="OCR" count={ocrBlocks.length} />
          <ViewButton active={viewMode === "rendered"} onClick={() => setViewMode("rendered")} icon={<Eye className="h-3.5 w-3.5" />} label="Rendered" />
          <button type="button" onClick={() => setZoomed((current) => !current)} className="ml-1 inline-flex h-8 w-8 items-center justify-center rounded-md text-muted transition hover:bg-surface hover:text-ink" title={zoomed ? "Fit image" : "Zoom image"} aria-label={zoomed ? "Fit image" : "Zoom image"}>
            {zoomed ? <RotateCcw className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      <div className="relative flex max-h-[72vh] min-h-64 items-center justify-center overflow-auto bg-[#f5f4f2] p-2 dark:bg-[#111110] sm:p-4">
        <div className={`relative inline-block max-w-full origin-center transition-transform duration-200 ${zoomed ? "scale-[1.5]" : "scale-100"}`}>
          {viewMode === "rendered" ? (
            <img src={annotatedImageUrl} alt="Computer-vision annotated package image" className="block max-h-[68vh] max-w-full rounded-lg object-contain shadow-sm" />
          ) : (
            <div className="relative inline-block max-w-full">
              <img src={rawImageUrl} alt={sourceAlt} className="block max-h-[68vh] max-w-full select-none rounded-lg object-contain shadow-sm" />
              <svg viewBox={`0 0 ${width} ${height}`} className="pointer-events-none absolute inset-0 h-full w-full text-[#171717] dark:text-[#f2f2f0]" preserveAspectRatio="none" role="img" aria-label={viewMode === "ocr" ? "All detected OCR text regions" : "Detected package declaration fields"}>
                {viewMode === "ocr" && ocrBlocks.map((block) => {
                  const points = block.polygon.map((point) => `${point.x},${point.y}`).join(" ");
                  return <polygon key={block.block_id} points={points} fill="currentColor" fillOpacity="0.04" stroke="currentColor" strokeOpacity={block.confidence >= 0.85 ? 0.9 : 0.52} strokeWidth={Math.max(width / 1000, 1.5)} vectorEffect="non-scaling-stroke"><title>{`${block.text} (${(block.confidence * 100).toFixed(0)}% confidence)`}</title></polygon>;
                })}
                {viewMode === "declarations" && declarations.map((declaration, index) => {
                  const selected = selectedDeclarationId === declaration.declaration_id;
                  const points = declaration.polygon.map((point) => `${point.x},${point.y}`).join(" ");
                  const markerRadius = Math.max(8, Math.min(width, height) * 0.012);
                  return <g key={declaration.declaration_id} className="pointer-events-auto">
                    <polygon points={points} fill="currentColor" fillOpacity={selected ? 0.14 : 0.025} stroke="currentColor" strokeWidth={selected ? 3 : 1.5} vectorEffect="non-scaling-stroke" className="cursor-pointer transition-[fill-opacity] hover:fill-opacity-20" tabIndex={0} role="button" aria-label={`${declaration.display_title}: ${declaration.raw_text}`} onClick={() => onSelectDeclaration(selected ? null : declaration.declaration_id)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelectDeclaration(selected ? null : declaration.declaration_id); } }}>
                      <title>{`${declaration.display_title}: ${declaration.raw_text} (${(declaration.combined_confidence * 100).toFixed(0)}% confidence)`}</title>
                    </polygon>
                    <circle cx={declaration.bounding_box.x_min} cy={declaration.bounding_box.y_min} r={markerRadius} fill="currentColor" stroke="rgb(var(--surface-rgb))" strokeWidth={1.5} vectorEffect="non-scaling-stroke" pointerEvents="none" />
                    <text x={declaration.bounding_box.x_min} y={declaration.bounding_box.y_min + markerRadius * 0.34} textAnchor="middle" fontSize={markerRadius * 1.05} fontWeight="700" fill="rgb(var(--surface-rgb))" aria-hidden="true" pointerEvents="none">{index + 1}</text>
                    {selected && <foreignObject x={Math.max(0, Math.min(declaration.bounding_box.x_min, width - 220))} y={Math.max(0, declaration.bounding_box.y_min - 28)} width={220} height={26} className="pointer-events-none"><div style={{ background: "rgb(var(--ink-rgb))", color: "rgb(var(--surface-rgb))" }} className="truncate rounded-sm px-2 py-1 text-[10px] font-medium">{declaration.display_title}: {declaration.raw_text}</div></foreignObject>}
                  </g>;
                })}
              </svg>
            </div>
          )}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-line px-4 py-2.5 text-[9px] text-muted" aria-label="Overlay legend">
        <span>{viewMode === "ocr" ? "Text regions; stronger outlines indicate higher OCR confidence." : viewMode === "declarations" ? "Numbered outlines correspond to the linked declarations." : "Rendered image annotation."}</span>
        <span className="ml-auto">Select an outline or declaration to inspect its evidence.</span>
      </div>
    </section>
  );
};

function ViewButton({ active, onClick, icon, label, count }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string; count?: number }) {
  return <button type="button" onClick={onClick} aria-pressed={active} className={`inline-flex h-7 items-center gap-1.5 rounded-[3px] px-2 text-[10px] font-medium transition-colors ${active ? "bg-[#171717] text-white dark:bg-[#f2f2f0] dark:text-[#171717]" : "text-muted hover:bg-surface hover:text-ink"}`}>{icon}<span>{label}</span>{count !== undefined && <span className="font-mono opacity-70">{count}</span>}</button>;
}
