export type NexovaRole = "admin" | "manager" | "user";

export interface NexovaProfile {
  id: number;
  user_id: number;
  name: string | null;
  phone: string | null;
  address: string | null;
}

export interface NexovaUser {
  id: number;
  email: string;
  is_active: boolean;
  role: NexovaRole;
  created_at: string;
}

export interface NexovaRegistrationInput {
  email: string;
  password: string;
  name?: string;
  phone?: string;
  address?: string;
}

export interface NexovaLoginInput {
  email: string;
  password: string;
}

export interface NexovaTokenResponse {
  access_token: string;
  token_type: "bearer";
}

export interface NexovaCurrentUser {
  email: string;
  role: NexovaRole;
  profile: NexovaProfile;
}

export interface NexovaProfileUpdate {
  name?: string | null;
  phone?: string | null;
  address?: string | null;
}
