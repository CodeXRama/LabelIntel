import React from "react";
import { FileText, CheckCircle2, ChevronRight, Hash } from "lucide-react";
import { FusedDeclaration } from "../types";

interface DeclarationsListProps {
  declarations: FusedDeclaration[];
  selectedDeclarationId: string | null;
  onSelectDeclaration: (id: string | null) => void;
}

const TYPE_BADGE_CLASSES: Record<string, string> = {
  mrp: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  net_quantity: "bg-sky-500/10 text-sky-400 border-sky-500/20",
  mfg_date: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  expiry_date: "bg-rose-500/10 text-rose-400 border-rose-500/20",
  best_before: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  manufacturer: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  packer: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  consumer_care: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
  fssai_license: "bg-lime-500/10 text-lime-400 border-lime-500/20",
  ingredients: "bg-teal-500/10 text-teal-400 border-teal-500/20",
  nutrition: "bg-pink-500/10 text-pink-400 border-pink-500/20",
  caution_warning: "bg-red-500/10 text-red-400 border-red-500/20",
  other: "bg-slate-500/10 text-slate-400 border-slate-500/20",
};

export const DeclarationsList: React.FC<DeclarationsListProps> = ({
  declarations,
  selectedDeclarationId,
  onSelectDeclaration,
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <FileText className="w-4 h-4 text-indigo-400" />
          <h3 className="text-sm font-semibold text-slate-200">
            Fused Packaging Declarations ({declarations.length})
          </h3>
        </div>
        <span className="text-[11px] text-slate-400">Click to locate on image</span>
      </div>

      <div className="space-y-2.5 max-h-[500px] overflow-y-auto pr-1">
        {declarations.length === 0 ? (
          <p className="text-xs text-slate-500 text-center py-6">
            No packaging declarations identified.
          </p>
        ) : (
          declarations.map((decl) => {
            const isSelected = selectedDeclarationId === decl.declaration_id;
            const badgeClass =
              TYPE_BADGE_CLASSES[decl.declaration_type] ||
              "bg-slate-800 text-slate-300 border-slate-700";

            return (
              <div
                key={decl.declaration_id}
                onClick={() =>
                  onSelectDeclaration(isSelected ? null : decl.declaration_id)
                }
                className={`p-3.5 rounded-xl border text-xs cursor-pointer transition-all ${
                  isSelected
                    ? "bg-indigo-600/10 border-indigo-500 shadow-md shadow-indigo-500/10"
                    : "bg-slate-800/40 hover:bg-slate-800/80 border-slate-800 hover:border-slate-700"
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border uppercase tracking-wider ${badgeClass}`}
                  >
                    {decl.display_title}
                  </span>
                  <div className="flex items-center space-x-2 text-[10px] text-slate-400">
                    <span className="font-mono">
                      {(decl.combined_confidence * 100).toFixed(0)}% conf
                    </span>
                    <ChevronRight
                      className={`w-3.5 h-3.5 transition-transform ${
                        isSelected ? "rotate-90 text-indigo-400" : "text-slate-600"
                      }`}
                    />
                  </div>
                </div>

                <p className="text-slate-200 font-medium text-xs break-words">
                  "{decl.raw_text}"
                </p>

                {/* Structured Normalized Data if present */}
                {decl.normalized_data && (
                  <div className="mt-2 pt-2 border-t border-slate-700/50 flex flex-wrap gap-2 text-[11px]">
                    {Object.entries(decl.normalized_data).map(([k, v]) => (
                      <span
                        key={k}
                        className="bg-slate-900/80 px-2 py-0.5 rounded text-slate-300 font-mono text-[10px]"
                      >
                        <span className="text-slate-500">{k}:</span> {String(v)}
                      </span>
                    ))}
                  </div>
                )}

                {isSelected && (
                  <div className="mt-2 text-[10px] text-indigo-300 font-mono">
                    Envelope: [x: {decl.bounding_box.x_min}..{decl.bounding_box.x_max}, y:{" "}
                    {decl.bounding_box.y_min}..{decl.bounding_box.y_max}]
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
