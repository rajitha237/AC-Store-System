import { api } from "@/lib/api";
import type {
  TokenResponse,
  UserResponse,
} from "@/types/auth";

export async function login(
  username: string,
  password: string,
): Promise<TokenResponse> {
  const body = new URLSearchParams();

  body.set("username", username);
  body.set("password", password);

  const response =
    await api.post<TokenResponse>(
      "/auth/login",
      body,
      {
        headers: {
          "Content-Type":
            "application/x-www-form-urlencoded",
        },
      },
    );

  return response.data;
}

export async function getCurrentUser():
  Promise<UserResponse> {
  const response =
    await api.get<UserResponse>(
      "/auth/me",
    );

  return response.data;
}
