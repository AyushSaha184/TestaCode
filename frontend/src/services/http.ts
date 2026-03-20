import axios from "axios";
import { sessionId } from "@/session/session";

const timeout = Number(import.meta.env.VITE_API_TIMEOUT_MS || 30000);
const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL,
  timeout,
});

apiClient.interceptors.request.use((config) => {
  config.headers = config.headers ?? {};
  config.headers["X-Session-Id"] = sessionId;
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error?.response?.data?.detail;
    const message = typeof detail === "string" ? detail : error?.message || "Request failed";
    return Promise.reject(new Error(message));
  },
);
