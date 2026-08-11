import axios from "axios";

import {
  clearAuthSession,
  getAccessToken,
} from "@/lib/auth";

const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL;

if (!apiBaseUrl) {
  throw new Error(
    "NEXT_PUBLIC_API_BASE_URL is not configured",
  );
}

export const AUTH_UNAUTHORIZED_EVENT =
  "ac-store:unauthorized";

export const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 15000,
  headers: {
    Accept: "application/json",
  },
});

api.interceptors.request.use(
  (config) => {
    const token = getAccessToken();

    if (token) {
      config.headers.Authorization =
        `Bearer ${token}`;
    }

    return config;
  },
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      typeof window !== "undefined"
      && error.response?.status === 401
    ) {
      clearAuthSession();

      window.dispatchEvent(
        new Event(
          AUTH_UNAUTHORIZED_EVENT,
        ),
      );
    }

    return Promise.reject(error);
  },
);
