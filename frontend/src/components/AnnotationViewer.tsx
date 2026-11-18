import React, { useState } from "react";
import { Eye, Layers, Maximize2, RotateCcw } from "lucide-react";
import { FusedDeclaration } from "../types";

interface AnnotationViewerProps {
  rawImageUrl: string;
  annotatedImageUrl: string;
  declarations: FusedDeclaration[];
  selectedDeclarationId: string | null;
  onSelectDeclaration: (id: string | null) => void;
  width: number;
  height: number;
}

const TYPE_COLORS: Record<string, string> = {
  mrp: "#22c55e",             // Green
  net_quantity: "#38bdf8",    // Sky blue
  mfg_date: "#f97316",        // Orange
  expiry_date: "#ef4444",     // Red
  best_before: "#eab308",     // Yellow
  manufacturer: "#c084fc",    // Purple
  packer: "#c084fc",
  consumer_care: "#06b6d4",   // Cyan
  fssai_license: "#84cc16",   // Lime
  ingredients: "#14b8a6",     // Teal
  nutrition: "#f43f5e",       // Rose
  caution_warning: "#dc2626", // Dark red
  other: "#94a3b8",           // Slate
};

export const AnnotationViewer: React.FC<AnnotationViewerProps> = ({
  rawImageUrl,
  annotatedImageUrl,
  declarations,
  selectedDeclarationId,
  onSelectDeclaration,
  width,
  height,
}) => {
  const [viewMode, setViewMode] = useState<"interactive" | "rendered">("interactive");
  const [zoomLevel, setZoomLevel] = useState<number>(1);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col">
      {/* Viewer Header Controls */}
      <div className="px-4 py-3 bg-slate-800/60 border-b border-slate-800 flex items-center justify-between text-xs">
        <div className="flex items-center space-x-3">
          <span className="font-semibold text-slate-200">Packaging Visual Evidence</span>
          <span className="text-slate-500">&bull;</span>
          <span className="text-slate-400 font-mono">
            {width} &times; {height} px
          </span>
        </div>

        <div className="flex items-center space-x-2">
          {/* Toggle between Interactive SVG and Burned-in OpenCV */}
          <div className="bg-slate-900 p-0.5 rounded-lg border border-slate-700/60 flex items-center">
            <button
              onClick={() => setViewMode("interactive")}
              className={`px-2.5 py-1 rounded-md transition-all flex items-center space-x-1.5 ${
                viewMode === "interactive"
                  ? "bg-indigo-600 text-white font-medium shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Interactive Polygons</span>
            </button>
            <button
              onClick={() => setViewMode("rendered")}
              className={`px-2.5 py-1 rounded-md transition-all flex items-center space-x-1.5 ${
                viewMode === "rendered"
                  ? "bg-indigo-600 text-white font-medium shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>CV Annotated Overlay</span>
            </button>
          </div>

          <button
            onClick={() => setZoomLevel((z) => (z === 1 ? 1.5 : 1))}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
            title="Toggle Zoom"
          >
            {zoomLevel === 1 ? <Maximize2 className="w-3.5 h-3.5" /> : <RotateCcw className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Main Visual Display */}
      <div className="relative overflow-auto max-h-[640px] flex items-center justify-center p-4 bg-slate-950/60">
        <div
          className="relative inline-block transition-transform duration-200 origin-top-left"
          style={{ transform: `scale(${zoomLevel})` }}
        >
          {viewMode === "rendered" ? (
            <img
              src={annotatedImageUrl}
              alt="Annotated Inspection Overlay"
              className="max-w-full rounded-lg shadow-2xl block object-contain"
            />
          ) : (
            <div className="relative inline-block">
              <img
                src={rawImageUrl}
                alt="Source Commodity Packaging"
                className="max-w-full rounded-lg shadow-2xl block object-contain select-none"
              />

              {/* Interactive SVG Bounding Overlays */}
              <svg
                viewBox={`0 0 ${width} ${height}`}
                className="absolute inset-0 w-full h-full pointer-events-auto"
                preserveAspectRatio="none"
              >
                {declarations.map((decl) => {
                  const isSelected = selectedDeclarationId === decl.declaration_id;
                  const color = TYPE_COLORS[decl.declaration_type] || "#94a3b8";

                  // Build SVG polygon points attribute string "x1,y1 x2,y2 ..."
                  const pointsStr = decl.polygon.map((p) => `${p.x},${p.y}`).join(" ");

                  return (
                    <g key={decl.declaration_id}>
                      <polygon
                        points={pointsStr}
                        fill={color}
                        fillOpacity={isSelected ? 0.35 : 0.15}
                        stroke={color}
                        strokeWidth={isSelected ? 4 : 2}
                        strokeDasharray={isSelected ? "none" : "none"}
                        className="cursor-pointer transition-all hover:fill-opacity-40"
                        onClick={() =>
                          onSelectDeclaration(isSelected ? null : decl.declaration_id)
                        }
                      >
                        <title>{`${decl.display_title}: ${decl.raw_text} (${(decl.combined_confidence * 100).toFixed(0)}%)`}</title>
                      </polygon>

                      {/* Tag pill above polygon */}
                      {isSelected && (
                        <foreignObject
                          x={decl.bounding_box.x_min}
                          y={Math.max(10, decl.bounding_box.y_min - 32)}
                          width={Math.max(200, decl.bounding_box.x_max - decl.bounding_box.x_min + 60)}
                          height={30}
                        >
                          <div
                            style={{ backgroundColor: color }}
                            className="text-white text-[11px] font-bold px-2 py-0.5 rounded shadow-lg truncate inline-block border border-white/20"
                          >
                            {decl.display_title}
                          </div>
                        </foreignObject>
                      )}
                    </g>
                  );
                })}
              </svg>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
