import React from "react";
import {
  ShieldAlert,
  ShieldCheck,
  HelpCircle,
  XCircle,
  Scale,
  ExternalLink,
  Info,
} from "lucide-react";
import { OverallComplianceReport } from "../types";

interface ComplianceCardProps {
  report: OverallComplianceReport;
}

export const ComplianceCard: React.FC<ComplianceCardProps> = ({ report }) => {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "compliant":
        return (
          <span className="flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>COMPLIANT</span>
          </span>
        );
      case "non_compliant":
        return (
          <span className="flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3.5 h-3.5" />
            <span>NON-COMPLIANT</span>
          </span>
        );
      case "flagged_for_review":
        return (
          <span className="flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <HelpCircle className="w-3.5 h-3.5" />
            <span>FLAGGED FOR REVIEW</span>
          </span>
        );
      default:
        return (
          <span className="flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">
            <span>NOT APPLICABLE</span>
          </span>
        );
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-5">
      {/* Overall Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div className="flex items-center space-x-2.5">
          <Scale className="w-5 h-5 text-indigo-400" />
          <div>
            <h3 className="text-sm font-semibold text-white">
              Statutory Compliance Assessment
            </h3>
            <p className="text-xs text-slate-400">
              Legal Metrology (Packaged Commodities) Rules, 2011 & FSSAI Guidelines
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="text-right text-xs">
            <span className="text-slate-400 block">Overall Status:</span>
          </div>
          {getStatusBadge(report.overall_status)}
        </div>
      </div>

      {/* Rules Breakdown Cards */}
      <div className="space-y-3">
        {report.assessments.map((item) => (
          <div
            key={item.assessment_id}
            className="p-4 rounded-xl border border-slate-800/80 bg-slate-800/30 space-y-2 text-xs"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-semibold text-slate-200">
                    {item.rule.title}
                  </span>
                  <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-indigo-400 border border-slate-700">
                    {item.rule.rule_reference}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  {item.rule.statute_name}
                </p>
              </div>
              <div>{getStatusBadge(item.status)}</div>
            </div>

            {/* Findings */}
            {item.findings.length > 0 && (
              <div className="space-y-1 pt-1">
                {item.findings.map((f, idx) => (
                  <p key={idx} className="text-slate-300">
                    &bull; {f}
                  </p>
                ))}
              </div>
            )}

            {/* Cautions and Recommendations */}
            {item.cautions_and_recommendations.length > 0 && (
              <div className="bg-amber-500/5 border border-amber-500/20 rounded-lg p-2.5 mt-2 space-y-1">
                {item.cautions_and_recommendations.map((rec, idx) => (
                  <div key={idx} className="flex items-start space-x-1.5 text-amber-300 text-[11px]">
                    <ShieldAlert className="w-3.5 h-3.5 mt-0.5 shrink-0 text-amber-400" />
                    <span>{rec}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Prominent Legal Disclaimer */}
      <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 flex items-start space-x-2.5 text-[11px] text-slate-400">
        <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <strong className="text-slate-300">Statutory Notice & Disclaimer:</strong>{" "}
          {report.legal_disclaimer}
        </p>
      </div>
    </div>
  );
};
