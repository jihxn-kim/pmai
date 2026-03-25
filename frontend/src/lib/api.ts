import axios from "axios";

function getApiUrl(): string {
  // Vercel env var (set at build time)
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  // Browser: if running on localhost, use local backend
  if (typeof window !== "undefined" && window.location.hostname === "localhost") {
    return "http://localhost:8000";
  }
  // Production fallback: same origin or Railway backend
  return "https://backend-production-587e.up.railway.app";
}

const API_URL = getApiUrl();

const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const token = typeof window !== "undefined" ? sessionStorage.getItem("access_token") : null;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      try {
        const { data } = await axios.post(
          `${API_URL}/api/auth/refresh`,
          {},
          { withCredentials: true }
        );
        sessionStorage.setItem("access_token", data.access_token);
        error.config.headers.Authorization = `Bearer ${data.access_token}`;
        return axios(error.config);
      } catch {
        sessionStorage.removeItem("access_token");
        if (typeof window !== "undefined") window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;
