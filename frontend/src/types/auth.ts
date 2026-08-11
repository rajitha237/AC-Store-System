export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};

export type UserResponse = {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_superuser: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
};
