import axios from "axios";

const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
});

export const loadDemo = () => api.get("/api/demo");

export const loadDatasetSample = datasetId =>
  api.get(`/api/datasets/${datasetId}/sample`);

export const uploadCsv = file => {
  const formData = new FormData();
  formData.append("file", file);

  return api.post("/api/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

export const savePassport = payload =>
  api.post("/api/passports", payload);

export const optimize = payload =>
  api.post("/api/optimize", payload);

export const downloadReport = payload =>
  api.post("/api/report", payload, {
    responseType: "blob",
  });

export const getModelStatus = () =>
  api.get("/api/models/status");

export const getDatasetCatalog = () =>
  api.get("/api/datasets");

export default api;