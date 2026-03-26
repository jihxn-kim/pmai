import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
    const status = error.response?.status;
    const detail = error.response?.data?.detail || "";
    const isAuthError = status === 401 || (status === 403 && (detail === "Not authenticated" || detail === "Invalid or expired token"));

    if (isAuthError && !error.config._retry) {
      error.config._retry = true;
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
