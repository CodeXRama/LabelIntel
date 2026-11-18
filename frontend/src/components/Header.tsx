import React from "react";
import { ShieldCheck, Cpu, Database, Award } from "lucide-react";

export const Header: React.FC = () => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-50 px-6 py-4">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <ShieldCheck className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold tracking-tight text-white">LabelIntel</h1>
              <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-medium">
                Packaged Commodity Vision
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Legal Metrology (2011) & FSSAI (2020) Automated Compliance Verification
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-6 text-xs text-slate-400">
          <div className="flex items-center space-x-1.5">
            <Cpu className="w-4 h-4 text-emerald-400" />
            <span>PaddleOCR PP-OCRv6 (CPU)</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <Database className="w-4 h-4 text-indigo-400" />
            <span>SQLite Persistence</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <Award className="w-4 h-4 text-amber-400" />
            <span>Evidence Fusion Engine</span>
          </div>
        </div>
      </div>
    </header>
  );
};
