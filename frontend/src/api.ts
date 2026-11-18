import axios from "axios";
import { InspectionData, SampleImage } from "./types";

const API_BASE = "http://127.0.0.1:8001";

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
