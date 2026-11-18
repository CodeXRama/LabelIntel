import React, { useState } from "react";
import { Upload, Image as ImageIcon, Sparkles, Loader2, CheckCircle2 } from "lucide-react";
import { SampleImage } from "../types";

interface ImageUploaderProps {
  onUpload: (file: File, category?: string) => Promise<void>;
  onSelectSample: (samplePath: string) => Promise<void>;
  samples: SampleImage[];
  isLoading: boolean;
}

export const ImageUploader: React.FC<ImageUploaderProps> = ({
  onUpload,
  onSelectSample,
  samples,
  isLoading,
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>("food");

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await onUpload(e.dataTransfer.files[0], selectedCategory);
    }
  };

  const handleChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      await onUpload(e.target.files[0], selectedCategory);
    }
  };

  return (
    <div className="space-y-6">
      {/* Category selector */}
      <div className="flex items-center justify-between bg-slate-800/40 border border-slate-700/60 p-3 rounded-xl">
        <span className="text-xs font-medium text-slate-300">Package Commodity Category:</span>
        <div className="flex space-x-2">
          {["food", "beverages", "cosmetics", "household", "other"].map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`text-xs px-3 py-1.5 rounded-lg capitalize transition-all ${
                selectedCategory === cat
                  ? "bg-indigo-600 text-white font-medium shadow-md shadow-indigo-600/30"
                  : "bg-slate-800 text-slate-400 hover:text-slate-200"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Main Drag-and-Drop Area */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-2xl p-8 text-center transition-all ${
          dragActive
            ? "border-indigo-500 bg-indigo-500/10 scale-[1.01]"
            : "border-slate-700 hover:border-slate-600 bg-slate-800/30"
        }`}
      >
        <input
          type="file"
          id="file-upload"
          className="hidden"
          accept="image/jpeg,image/png,image/webp,image/avif"
          onChange={handleChange}
          disabled={isLoading}
        />

        <div className="flex flex-col items-center justify-center space-y-3">
          <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center border border-indigo-500/20">
            {isLoading ? (
              <Loader2 className="w-7 h-7 animate-spin text-indigo-400" />
            ) : (
              <Upload className="w-7 h-7" />
            )}
          </div>
          <div>
            <label
              htmlFor="file-upload"
              className="cursor-pointer text-sm font-semibold text-indigo-400 hover:text-indigo-300"
            >
              Click to upload packaging image
            </label>
            <span className="text-sm text-slate-400"> or drag and drop</span>
            <p className="text-xs text-slate-500 mt-1">
              Supports JPEG, PNG, WebP, AVIF photographs up to 25MB
            </p>
          </div>
        </div>

        {isLoading && (
          <div className="absolute inset-0 bg-slate-900/80 backdrop-blur-sm rounded-2xl flex flex-col items-center justify-center space-y-3 z-10">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
            <div className="text-center">
              <p className="text-sm font-medium text-white">Preparing inspection results...</p>
              <p className="text-xs text-slate-400">
                Saved samples load quickly. New uploads run validation, PaddleOCR, evidence fusion, and compliance checks and may take up to two minutes on CPU.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Discovered Real Samples Quick-Selector */}
      {samples.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center space-x-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
            <Sparkles className="w-4 h-4 text-amber-400" />
            <span>Or test with genuine packaging photograph samples</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {samples.map((s) => (
              <button
                key={s.relative_path}
                onClick={() => onSelectSample(s.relative_path)}
                disabled={isLoading}
                className="group p-3 rounded-xl bg-slate-800/50 hover:bg-slate-800 border border-slate-700/60 hover:border-indigo-500/50 text-left transition-all"
              >
                <div className="flex items-center space-x-2">
                  <ImageIcon className="w-4 h-4 text-slate-400 group-hover:text-indigo-400 shrink-0" />
                  <span className="text-xs font-medium text-slate-200 truncate">{s.filename}</span>
                </div>
                <div className="flex items-center justify-between mt-2 text-[10px] text-slate-500">
                  <span className="capitalize px-1.5 py-0.5 rounded bg-slate-700/50 text-slate-300">
                    {s.category}
                  </span>
                  <span>{(s.size_bytes / 1024).toFixed(0)} KB</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
