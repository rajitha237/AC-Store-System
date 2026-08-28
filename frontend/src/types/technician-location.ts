export type TechnicianTrackingState =
  | "active"
  | "stopped";


export interface TechnicianLocationUpdateRequest {
  latitude: number;
  longitude: number;
  accuracy_meters?: number | null;
  service_job_id?: number | null;
  client_recorded_at?: string | null;
  tracking_state?: TechnicianTrackingState;
}


export interface TechnicianLocationResponse {
  id: number;
  technician_id: number;
  service_job_id?: number | null;
  latitude: number;
  longitude: number;
  accuracy_meters?: number | null;
  tracking_state: string;
  recorded_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export type TechnicianLocationPresenceStatus =
  | "live"
  | "stale"
  | "offline";


export interface TechnicianLocationAdminResponse
  extends TechnicianLocationResponse {
  technician_name: string;
  service_job_number?: string | null;
  presence_status: TechnicianLocationPresenceStatus;
  age_seconds: number;
}
