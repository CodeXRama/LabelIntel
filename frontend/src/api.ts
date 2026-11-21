import axios from "axios";
import { InspectionAnalytics, InspectionData, InspectionProgress, InspectionSummary, SampleImage } from "./types";

// Same-origin requests work in both the Vite dev server (via its /api proxy)
// and a production deployment. An explicit URL remains available for a
// separately hosted API through VITE_API_BASE_URL.
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

export const api = {
  async getHealth() {
    const res = await axios.get(`${API_BASE}/api/health`);
    return res.data;
  },

  async getSamples(): Promise<SampleImage[]> {
    const res = await axios.get(`${API_BASE}/api/samples`);
    return res.data;
  },

  getSampleImageUrl(samplePath: string) {
    return `${API_BASE}/api/samples/image?sample_path=${encodeURIComponent(samplePath)}`;
  },

  async uploadAndInspect(
    file: File,
    category: string | undefined,
    progressId: string,
    onUploadProgress: (percent: number) => void,
  ): Promise<InspectionData> {
    const formData = new FormData();
    formData.append("file", file);
    const url = category
      ? `${API_BASE}/api/inspections/upload?category=${encodeURIComponent(category)}`
      : `${API_BASE}/api/inspections/upload`;
    const res = await axios.post(url, formData, {
      headers: { "Content-Type": "multipart/form-data", "X-Inspection-Progress-ID": progressId },
      onUploadProgress: (event) => {
        if (event.total) onUploadProgress(Math.min(100, Math.round((event.loaded / event.total) * 100)));
      },
    });
    return res.data;
  },

  async runDemoSample(samplePath: string, progressId: string): Promise<InspectionData> {
    const res = await axios.post(
      `${API_BASE}/api/inspections/demo?sample_path=${encodeURIComponent(samplePath)}&progress_id=${encodeURIComponent(progressId)}`,
      undefined,
    );
    return res.data;
  },

  async getInspectionProgress(progressId: string, signal: AbortSignal): Promise<InspectionProgress> {
    const res = await axios.get(`${API_BASE}/api/inspection-progress/${encodeURIComponent(progressId)}`, { signal });
    return res.data;
  },

  async getInspections(): Promise<InspectionSummary[]> {
    const res = await axios.get(`${API_BASE}/api/inspections`);
    return res.data;
  },

  async getInspectionAnalytics(): Promise<InspectionAnalytics> {
    const res = await axios.get(`${API_BASE}/api/inspection-analytics`);
    return res.data;
  },

  async exportFindings(): Promise<Blob> {
    const res = await axios.get(`${API_BASE}/api/inspections/export.csv`, { responseType: "blob" });
    return res.data;
  },

  async getInspection(id: string): Promise<InspectionData> {
    const res = await axios.get(`${API_BASE}/api/inspections/${id}`);
    return res.data;
  },

  getImageUrl(path: string) {
    if (path.startsWith("http")) return path;
    return `${API_BASE}${path}`;
  },
};
