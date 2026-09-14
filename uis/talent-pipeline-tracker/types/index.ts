export const STATUSES = ["received", "in_progress", "discarded"] as const;
export const STAGES = [
  "pending",
  "review",
  "personal_interview",
  "technical_interview",
] as const;

export type Status = (typeof STATUSES)[number];
export type Stage = (typeof STAGES)[number];

export interface Note {
  id: string;
  record_id: string;
  content: string;
  created_at: string;
}

export interface Candidate {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string | null;
  cv_url: string | null;
  status: Status;
  stage: Stage;
  experience_years: number;
  applied_at: string;
  updated_at: string;
  notes?: Note[];
  notes_count: number;
}

export interface CandidateInput {
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url?: string;
  cv_url?: string;
  experience_years: number;
}

export interface CandidateStatusUpdate {
  status?: Status;
  stage?: Stage;
}

export interface NoteInput {
  content: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  page: number;
  limit: number;
  total: number;
}

export interface NotesResponse {
  data: Note[];
  meta: {
    total: number;
  };
}

export interface CandidatesQuery {
  page?: number;
  limit?: number;
  status?: Status;
  stage?: Stage;
  search?: string;
}