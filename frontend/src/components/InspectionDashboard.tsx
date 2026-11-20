import React, { useMemo, useState } from "react";
import { ArrowUpRight, Check, ChevronLeft, ChevronRight, Download, FilePlus2, RefreshCw, Search } from "lucide-react";
import { api } from "../api";
import { InspectionAnalytics, InspectionSummary } from "../types";

type ApiHealth = "online" | "offline" | "checking";
interface InspectionDashboardProps {
  inspections: InspectionSummary[];
  analytics: InspectionAnalytics | null;
  loading: boolean;
  refreshing: boolean;
  health: ApiHealth;
  historyMode?: boolean;
  onRefresh: () => void;
  onOpenInspection: (id: string) => void;
  onNewInspection: () => void;
  onExportFindings: () => void;
  onViewHistory: () => void;
}

const normalizeStatus = (value?: string) => (value || "unknown").toLowerCase().replace(/[ _-]+/g, " ");
const isCompliant = (value?: string) => normalizeStatus(value) === "compliant";
const isFlagged = (value?: string) => normalizeStatus(value) === "flagged for review";
const isNonCompliant = (value?: string) => normalizeStatus(value) === "non compliant";

function formatDate(value?: string | null) {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export const InspectionDashboard: React.FC<InspectionDashboardProps> = ({
  inspections, analytics, loading, refreshing, health, historyMode,
  onRefresh, onOpenInspection, onNewInspection, onExportFindings, onViewHistory,
}) => {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const pageSize = 8;
  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return inspections;
    return inspections.filter((item) => `${item.filename} ${item.id} ${item.category || ""} ${item.overall_compliance}`.toLowerCase().includes(term));
  }, [inspections, query]);
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const currentPage = Math.min(page, totalPages - 1);
  const rows = filtered.slice(currentPage * pageSize, (currentPage + 1) * pageSize);
  const counts = analytics?.overall_counts || {
    compliant: inspections.filter((item) => isCompliant(item.overall_compliance)).length,
    flagged_for_review: inspections.filter((item) => isFlagged(item.overall_compliance)).length,
    non_compliant: inspections.filter((item) => isNonCompliant(item.overall_compliance)).length,
    other: 0,
  };
  const analyzed = analytics?.records_analyzed ?? inspections.length;
  const flaggedRules = (analytics?.rule_counts || []).filter((rule) => rule.fail_count + rule.review_count > 0);
  const maxFlags = Math.max(1, ...flaggedRules.map((rule) => rule.fail_count + rule.review_count));

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-5 px-5 py-7 sm:px-8 sm:py-8">
      <header className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
        <div>
          <p className="mb-2 text-[11px] font-medium text-muted">LabelIntel / Workspace</p>
          <h1 className="text-[27px] font-semibold tracking-tight text-ink">{historyMode ? "Inspection history" : "Overview"}</h1>
          <p className="mt-1.5 text-[13px] text-muted">{historyMode ? "Search and reopen saved package inspections." : `${analyzed} recent inspections checked against the configured label rules.`}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" onClick={onExportFindings} className="inline-flex h-9 items-center gap-2 rounded-md border border-line bg-surface px-3 text-[12px] font-medium text-ink transition hover:bg-subtle focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink">
            <Download aria-hidden="true" className="h-3.5 w-3.5" /> Export findings
          </button>
          <button type="button" onClick={onNewInspection} className="inline-flex h-9 items-center gap-2 rounded-md bg-[#171717] px-3.5 text-[12px] font-medium text-white transition hover:bg-black focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink dark:bg-[#f2f2f0] dark:text-[#171717] dark:hover:bg-white">
            <FilePlus2 aria-hidden="true" className="h-3.5 w-3.5" /> Check a pack
          </button>
        </div>
      </header>

      {health === "offline" && <div role="status" className="flex items-center justify-between gap-3 border-y border-rose-300 bg-rose-50 px-3 py-2.5 text-[12px] text-rose-900 dark:border-rose-900 dark:bg-[#29191a] dark:text-rose-200"><span>The inspection API is unavailable.</span><button type="button" onClick={onRefresh} disabled={refreshing} className="inline-flex items-center gap-1.5 font-medium underline underline-offset-2 disabled:opacity-60"><RefreshCw className={`h-3 w-3 ${refreshing ? "animate-spin" : ""}`} /> Retry</button></div>}

      {!historyMode && <>
        <section aria-label="Inspection outcomes" className="grid grid-cols-2 divide-x divide-y divide-line overflow-hidden rounded-md border border-line bg-surface sm:grid-cols-4 sm:divide-y-0">
          <Metric label="Inspections checked" value={analyzed} note="Recent completed records" />
          <Metric label="Compliant" value={counts.compliant} note="No rule flags returned" tone="pass" />
          <Metric label="Needs review" value={counts.flagged_for_review} note="Human verification advised" tone="review" />
          <Metric label="Possible issues" value={counts.non_compliant} note="Automated screening flags" tone="fail" />
        </section>

        <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-12">
          <section className="rounded-md border border-line bg-surface p-4 sm:p-5 xl:col-span-7" aria-labelledby="rules-summary-heading">
            <div className="flex items-start justify-between gap-3 border-b border-line pb-3">
              <div><h2 id="rules-summary-heading" className="text-[14px] font-semibold text-ink">Checks needing attention</h2><p className="mt-1 text-[11px] text-muted">Failed and review outcomes across {analyzed} recent inspections.</p></div>
              <span className="whitespace-nowrap font-mono text-[10px] text-muted">Top rules</span>
            </div>
            {loading ? <div className="space-y-4 py-5">{Array.from({ length: 5 }, (_, index) => <div key={index} className="h-7 animate-pulse rounded bg-subtle" />)}</div> : flaggedRules.length === 0 ? <p className="py-10 text-center text-[12px] text-muted">No failed or review outcomes in the saved assessments.</p> : <div className="space-y-4 py-4">
              {flaggedRules.map((rule) => {
                const totalFlags = rule.fail_count + rule.review_count;
                const width = Math.max(4, totalFlags / maxFlags * 100);
                const failShare = totalFlags ? rule.fail_count / totalFlags * 100 : 0;
                return <div key={rule.rule_id} className="grid grid-cols-[minmax(120px,1.1fr)_minmax(90px,2fr)_28px] items-center gap-3">
                  <div className="min-w-0"><p className="truncate text-[11px] font-medium text-ink" title={rule.title}>{rule.title}</p><p className="mt-0.5 text-[9px] text-muted">{rule.rule_reference || "Rule reference unavailable"}</p></div>
                  <div className="h-2 overflow-hidden rounded-sm bg-subtle" aria-label={`${rule.fail_count} possible issues and ${rule.review_count} review flags`}><div className="flex h-full overflow-hidden rounded-sm" style={{ width: `${width}%` }}><span className="h-full bg-rose-600 dark:bg-rose-400" style={{ width: `${failShare}%` }} /><span className="h-full flex-1 bg-amber-500 dark:bg-amber-300" /></div></div>
                  <span className="text-right font-mono text-[11px] text-muted">{totalFlags}</span>
                </div>;
              })}
            </div>}
            <div className="flex items-center gap-4 border-t border-line pt-3 text-[10px] text-muted"><span className="inline-flex items-center gap-1.5"><i className="h-2 w-2 rounded-sm bg-rose-600 dark:bg-rose-400" /> Possible issue</span><span className="inline-flex items-center gap-1.5"><i className="h-2 w-2 rounded-sm bg-amber-500 dark:bg-amber-300" /> Review</span></div>
          </section>

          <section className="rounded-md border border-line bg-surface p-4 sm:p-5 xl:col-span-5" aria-labelledby="recent-checks-heading">
            <div className="flex items-center justify-between gap-3 border-b border-line pb-3"><div><h2 id="recent-checks-heading" className="text-[14px] font-semibold text-ink">Recent checks</h2><p className="mt-1 text-[11px] text-muted">Latest saved package inspections.</p></div><button type="button" onClick={onRefresh} disabled={refreshing} title="Refresh inspections" aria-label="Refresh inspections" className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-line text-muted transition hover:bg-subtle hover:text-ink disabled:opacity-50"><RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} /></button></div>
            {loading ? <div className="space-y-3 py-4">{Array.from({ length: 4 }, (_, index) => <div key={index} className="h-12 animate-pulse rounded bg-subtle" />)}</div> : inspections.length === 0 ? <p className="py-10 text-center text-[12px] text-muted">No inspections saved yet.</p> : <div className="divide-y divide-line">
              {inspections.slice(0, 6).map((item) => <button key={item.id} type="button" onClick={() => onOpenInspection(item.id)} className="group flex w-full items-center gap-2.5 py-3 text-left first:pt-3 last:pb-0">
                <span className="h-9 w-9 shrink-0 overflow-hidden rounded-sm border border-line bg-subtle"><img src={api.getImageUrl(item.image_url)} alt="" loading="lazy" className="h-full w-full object-cover" /></span>
                <span className="min-w-0 flex-1"><span className="block truncate text-[11px] font-medium text-ink group-hover:underline">{item.filename}</span><span className="mt-1 block truncate text-[9px] text-muted">{item.category || "Uncategorized"} · {formatShortDate(item.created_at)}</span></span>
                <StatusPill value={item.overall_compliance} /><ArrowUpRight aria-hidden="true" className="h-3 w-3 shrink-0 text-muted" />
              </button>)}
            </div>}
            <button type="button" onClick={onViewHistory} className="mt-3 w-full border-t border-line pt-3 text-left text-[11px] font-medium text-muted transition hover:text-ink">View all inspections <span aria-hidden="true">→</span></button>
          </section>
        </div>
      </>}

      {historyMode && <section className="overflow-hidden rounded-md border border-line bg-surface" aria-label="Inspection history">
        <div className="flex flex-col justify-between gap-3 border-b border-line px-4 py-3 sm:flex-row sm:items-center sm:px-5">
          <div><h2 className="text-[14px] font-semibold text-ink">Saved inspections</h2><p className="mt-1 text-[11px] text-muted">Open a record to review its image and assessment.</p></div>
          <label className="relative block w-full sm:w-72"><Search aria-hidden="true" className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" /><input type="search" value={query} onChange={(event) => { setQuery(event.target.value); setPage(0); }} placeholder="Search filename, ID, or category" aria-label="Search inspections" className="h-9 w-full rounded-md border border-line bg-surface pl-9 pr-3 text-[11px] text-ink outline-none focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 dark:focus:border-neutral-400" /></label>
        </div>
        <div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left">
          <thead className="border-b border-line bg-subtle text-[9px] font-semibold uppercase tracking-wide text-muted"><tr><th scope="col" className="px-4 py-3 sm:px-5">Package</th><th scope="col" className="px-3 py-3">Category</th><th scope="col" className="px-3 py-3">Image size</th><th scope="col" className="px-3 py-3">Checked</th><th scope="col" className="px-3 py-3">Result</th><th scope="col" className="px-4 py-3 text-right">Open</th></tr></thead>
          <tbody className="divide-y divide-line">
            {loading && Array.from({ length: 4 }, (_, index) => <tr key={`skeleton-${index}`}><td colSpan={6} className="px-5 py-4"><div className="h-8 animate-pulse rounded bg-subtle" /></td></tr>)}
            {!loading && rows.length === 0 && <tr><td colSpan={6} className="px-5 py-14 text-center text-[12px] text-muted">{query ? "No matching inspections." : health === "offline" ? "Inspection records are unavailable." : "No inspections saved yet."}</td></tr>}
            {!loading && rows.map((item) => <tr key={item.id} className="transition-colors hover:bg-subtle">
              <td className="px-4 py-3 sm:px-5"><button type="button" onClick={() => onOpenInspection(item.id)} className="flex min-w-0 items-center gap-3 text-left"><span className="h-9 w-9 shrink-0 overflow-hidden rounded-sm border border-line bg-subtle"><img src={api.getImageUrl(item.image_url)} alt="" loading="lazy" className="h-full w-full object-cover" /></span><span className="min-w-0"><span className="block max-w-[300px] truncate text-[11px] font-medium text-ink">{item.filename}</span><span className="mt-1 block truncate font-mono text-[9px] text-muted">{item.id}</span></span></button></td>
              <td className="px-3 py-3 text-[10px] capitalize text-muted">{item.category || "Uncategorized"}</td>
              <td className="px-3 py-3 font-mono text-[10px] text-muted">{item.width && item.height ? `${item.width} × ${item.height} px` : "—"}</td>
              <td className="whitespace-nowrap px-3 py-3 text-[10px] text-muted">{formatDate(item.created_at)}</td>
              <td className="px-3 py-3"><StatusPill value={item.overall_compliance} /></td>
              <td className="px-4 py-3 text-right"><button type="button" aria-label={`Open ${item.filename}`} onClick={() => onOpenInspection(item.id)} className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-line text-muted hover:bg-subtle hover:text-ink"><ArrowUpRight aria-hidden="true" className="h-3.5 w-3.5" /></button></td>
            </tr>)}
          </tbody>
        </table></div>
        <div className="flex items-center justify-between border-t border-line px-4 py-3 text-[10px] text-muted sm:px-5"><span>{filtered.length ? `${currentPage * pageSize + 1}–${Math.min((currentPage + 1) * pageSize, filtered.length)} of ${filtered.length}` : "0 results"}</span><div className="flex items-center gap-2"><button type="button" aria-label="Previous page" disabled={currentPage === 0} onClick={() => setPage((value) => Math.max(0, value - 1))} className="rounded border border-line p-1.5 disabled:opacity-40"><ChevronLeft className="h-3.5 w-3.5" /></button><span className="font-mono">{currentPage + 1} / {totalPages}</span><button type="button" aria-label="Next page" disabled={currentPage + 1 >= totalPages} onClick={() => setPage((value) => Math.min(totalPages - 1, value + 1))} className="rounded border border-line p-1.5 disabled:opacity-40"><ChevronRight className="h-3.5 w-3.5" /></button></div></div>
      </section>}
    </div>
  );
};

function Metric({ label, value, note, tone = "neutral" }: { label: string; value: number; note: string; tone?: "neutral" | "pass" | "review" | "fail" }) {
  const toneClass = tone === "pass" ? "text-emerald-700 dark:text-emerald-300" : tone === "review" ? "text-amber-700 dark:text-amber-300" : tone === "fail" ? "text-rose-700 dark:text-rose-300" : "text-ink";
  return <div className="min-h-[96px] px-4 py-3 sm:px-5"><p className="text-[10px] text-muted">{label}</p><p className={`mt-1 text-[26px] font-semibold leading-none tabular-nums ${toneClass}`}>{value}</p><p className="mt-1.5 text-[9px] text-muted">{note}</p></div>;
}

function StatusPill({ value }: { value?: string }) {
  const status = normalizeStatus(value);
  const style = status === "compliant" ? "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200" : status === "non compliant" ? "bg-rose-100 text-rose-900 dark:bg-rose-950 dark:text-rose-200" : status === "flagged for review" ? "bg-amber-100 text-amber-950 dark:bg-amber-950 dark:text-amber-200" : "bg-subtle text-muted";
  const label = status === "compliant" ? "Passes" : status === "non compliant" ? "Fails" : status === "flagged for review" ? "Review" : status === "not applicable" ? "N/A" : "Unknown";
  return <span className={`inline-flex whitespace-nowrap rounded-full px-2 py-0.5 text-[9px] font-medium ${style}`}>{label}</span>;
}

function formatShortDate(value?: string | null) {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}
