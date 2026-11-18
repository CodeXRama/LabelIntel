import axios from "axios";
import { InspectionData, SampleImage } from "./types";

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

  async uploadAndInspect(file: File, category?: string): Promise<InspectionData> {
    const formData = new FormData();
    formData.append("file", file);
    const url = category
      ? `${API_BASE}/api/inspections/upload?category=${encodeURIComponent(category)}`
      : `${API_BASE}/api/inspections/upload`;
    const res = await axios.post(url, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return res.data;
  },

  async runDemoSample(samplePath: string): Promise<InspectionData> {
    const res = await axios.post(
      `${API_BASE}/api/inspections/demo?sample_path=${encodeURIComponent(samplePath)}`
    );
    return res.data;
  },

  async getInspections() {
    const res = await axios.get(`${API_BASE}/api/inspections`);
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
