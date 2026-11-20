import React from "react";
import { ChevronDown, FileText, MapPin } from "lucide-react";
import { FusedDeclaration } from "../types";

interface DeclarationsListProps {
  declarations: FusedDeclaration[];
  selectedDeclarationId: string | null;
  onSelectDeclaration: (id: string | null) => void;
}

const TYPE_BADGE_CLASSES: Record<string, string> = {
  mrp: "bg-subtle text-ink border-line",
  net_quantity: "bg-subtle text-ink border-line",
  mfg_date: "bg-subtle text-ink border-line",
  expiry_date: "bg-subtle text-ink border-line",
  best_before: "bg-subtle text-ink border-line",
  manufacturer: "bg-subtle text-ink border-line",
  packer: "bg-subtle text-ink border-line",
  consumer_care: "bg-subtle text-ink border-line",
  fssai_license: "bg-subtle text-ink border-line",
  ingredients: "bg-subtle text-ink border-line",
  nutrition: "bg-subtle text-ink border-line",
  caution_warning: "bg-subtle text-ink border-line",
  other: "bg-subtle text-muted border-line",
};

export const DeclarationsList: React.FC<DeclarationsListProps> = ({ declarations, selectedDeclarationId, onSelectDeclaration }) => (
  <section className="rounded-md border border-line bg-surface p-4 sm:p-5">
    <div className="flex items-center justify-between gap-3 border-b border-line pb-3">
      <div className="flex items-center gap-2"><FileText aria-hidden="true" className="h-4 w-4 text-muted" /><h2 className="text-xs font-semibold text-ink">Fused declarations <span className="ml-1 font-mono text-muted">{declarations.length}</span></h2></div>
      <span className="text-[9px] text-muted">Select to locate evidence</span>
    </div>
    <div className="mt-3 max-h-[560px] space-y-2 overflow-y-auto pr-1">
      {declarations.length === 0 ? <p className="py-8 text-center text-xs text-muted">No packaging declarations were linked in this image.</p> : declarations.map((declaration) => {
        const selected = selectedDeclarationId === declaration.declaration_id;
        const badge = TYPE_BADGE_CLASSES[declaration.declaration_type] || TYPE_BADGE_CLASSES.other;
        return <button key={declaration.declaration_id} type="button" aria-expanded={selected} onClick={() => onSelectDeclaration(selected ? null : declaration.declaration_id)} className={`block w-full rounded-sm border p-3 text-left transition focus-visible:outline-ink ${selected ? "border-ink bg-subtle" : "border-line bg-surface hover:bg-subtle"}`}>
          <span className="flex items-center justify-between gap-3"><span className={`rounded-sm border px-2 py-1 text-[9px] font-semibold uppercase tracking-wide ${badge}`}>{declaration.display_title}</span><span className="flex shrink-0 items-center gap-2 text-[9px] text-muted"><span className="font-mono">{(declaration.combined_confidence * 100).toFixed(0)}%</span><ChevronDown aria-hidden="true" className={`h-3.5 w-3.5 transition-transform ${selected ? "rotate-180 text-ink" : ""}`} /></span></span>
          <span className="mt-2 block break-words text-xs font-medium leading-5 text-ink">{declaration.raw_text ? `“${declaration.raw_text}”` : "No OCR text attached"}</span>
          {declaration.normalized_data && Object.keys(declaration.normalized_data).length > 0 && <span className="mt-2 flex flex-wrap gap-1.5 border-t border-line pt-2">{Object.entries(declaration.normalized_data).map(([key, value]) => <span key={key} className="rounded-md bg-subtle px-2 py-1 font-mono text-[9px] text-muted"><span className="text-ink">{key}:</span> {String(value ?? "—")}</span>)}</span>}
          {selected && <span className="mt-2 flex items-center gap-1.5 border-t border-line pt-2 font-mono text-[9px] text-muted"><MapPin aria-hidden="true" className="h-3 w-3 text-ink" />Region: x {Math.round(declaration.bounding_box.x_min)}–{Math.round(declaration.bounding_box.x_max)}, y {Math.round(declaration.bounding_box.y_min)}–{Math.round(declaration.bounding_box.y_max)}</span>}
          {selected && declaration.provenance_notes?.length > 0 && <span className="mt-2 block space-y-1 border-t border-line pt-2 text-[10px] leading-4 text-muted">{declaration.provenance_notes.map((note, index) => <span key={index} className="block">{note}</span>)}</span>}
        </button>;
      })}
    </div>
  </section>
);
