import React from "react";
import { MapPin } from "lucide-react";
import { FusedDeclaration, OverallComplianceReport } from "../types";

interface ComplianceCardProps {
  report: OverallComplianceReport;
  declarations: FusedDeclaration[];
  selectedDeclarationId: string | null;
  onSelectDeclaration: (id: string | null) => void;
}

type Status = "compliant" | "non_compliant" | "flagged_for_review" | "not_applicable";
const STATUS_LABELS: Record<Status, string> = {
  compliant: "Passes",
  non_compliant: "Fails",
  flagged_for_review: "Review",
  not_applicable: "N/A",
};
const STATUS_CLASSES: Record<Status, string> = {
  compliant: "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200",
  non_compliant: "bg-rose-100 text-rose-900 dark:bg-rose-950 dark:text-rose-200",
  flagged_for_review: "bg-amber-100 text-amber-950 dark:bg-amber-950 dark:text-amber-200",
  not_applicable: "bg-subtle text-muted",
};

function getStatus(value: string): Status | null {
  const normalized = value.toLowerCase().replace(/[ -]+/g, "_");
  return normalized in STATUS_LABELS ? normalized as Status : null;
}

function StatusPill({ status }: { status: string }) {
  const normalized = getStatus(status);
  if (!normalized) return <span className="rounded-full bg-subtle px-2 py-0.5 text-[9px] font-medium text-muted">Unknown</span>;
  return <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-[9px] font-medium ${STATUS_CLASSES[normalized]}`}>{STATUS_LABELS[normalized]}</span>;
}

export const ComplianceCard: React.FC<ComplianceCardProps> = ({ report, declarations, selectedDeclarationId, onSelectDeclaration }) => (
  <section className="overflow-hidden rounded-md border border-line bg-surface" aria-labelledby="assessment-heading">
    <header className="flex items-start justify-between gap-3 border-b border-line px-4 py-4 sm:px-5">
      <div><h2 id="assessment-heading" className="text-[14px] font-semibold text-ink">What the label declares</h2><p className="mt-1 text-[10px] text-muted">Automated checks against visible label evidence</p></div>
      <div className="shrink-0 text-right text-[10px] leading-4 text-muted"><div><strong className="font-semibold text-rose-700 dark:text-rose-300">{report.non_compliant_count} failing</strong><span> · {report.total_rules_evaluated} checks</span></div>{report.flagged_count > 0 && <div>{report.flagged_count} need review</div>}</div>
    </header>

    <div className="divide-y divide-line px-4 sm:px-5">
      {report.assessments.length === 0 ? <p className="py-10 text-center text-[12px] text-muted">No applicable checks were returned for this inspection.</p> : report.assessments.map((item, index) => {
        const linkedDeclaration = item.evidence_declaration_id && declarations.some((declaration) => declaration.declaration_id === item.evidence_declaration_id);
        const selected = Boolean(item.evidence_declaration_id && selectedDeclarationId === item.evidence_declaration_id);
        const detail = item.findings[0] || item.cautions_and_recommendations[0] || item.rule.summary;
        return <article key={item.assessment_id} className={`relative flex gap-3 py-3.5 ${selected ? "-mx-2 bg-subtle px-2" : ""}`}>
          <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#171717] font-mono text-[9px] font-semibold text-white dark:bg-[#f2f2f0] dark:text-[#171717]">{index + 1}</span>
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2.5">
              <div className="min-w-0"><div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5"><h3 className="text-[12px] font-medium leading-4 text-ink">{item.rule.title}</h3>{item.rule.rule_reference && <span className="text-[9px] text-muted">{item.rule.rule_reference}</span>}</div>{detail && <p className="mt-1 text-[11px] leading-[1.45] text-muted">{detail}</p>}</div>
              <StatusPill status={item.status} />
            </div>
            {item.cautions_and_recommendations.length > 0 && item.status !== "compliant" && <p className="mt-1.5 text-[10px] leading-[1.45] text-muted">{item.cautions_and_recommendations[0]}</p>}
            {linkedDeclaration && <button type="button" onClick={() => onSelectDeclaration(selected ? null : item.evidence_declaration_id!)} className="mt-2 inline-flex items-center gap-1 text-[10px] font-medium text-ink underline decoration-line underline-offset-2 hover:decoration-ink"><MapPin aria-hidden="true" className="h-3 w-3" />{selected ? "Evidence selected" : "Locate evidence"}</button>}
          </div>
        </article>;
      })}
    </div>

    <details className="border-t border-line px-4 py-3 text-[10px] text-muted sm:px-5">
      <summary className="cursor-pointer font-medium text-ink">Automated screening notice</summary>
      <p className="mt-2 leading-4">{report.legal_disclaimer}</p>
    </details>
  </section>
);
