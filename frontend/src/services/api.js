import axios from "axios";

const apiBaseUrl = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

const api = axios.create({ baseURL: apiBaseUrl, timeout: 90000 });

export const loadDemo = () => api.get("/api/demo");
export const uploadCsv = (file) => {
  const body = new FormData();
  body.append("file", file);
  return api.post("/api/upload", body);
};
export const optimize = (payload) => api.post("/api/optimize", payload);
export const savePassport = (payload) => api.post("/api/passports", payload);
export const downloadReport = (payload) =>
  api.post("/api/report", payload, { responseType: "blob" });
export default api;
