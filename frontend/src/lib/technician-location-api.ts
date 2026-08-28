import {
  api,
} from "@/lib/api";

import type {
  TechnicianLocationAdminResponse,
  TechnicianLocationResponse,
  TechnicianLocationUpdateRequest,
} from "@/types/technician-location";


export async function writeTechnicianLocation(
  payload: TechnicianLocationUpdateRequest,
): Promise<TechnicianLocationResponse> {
  const response =
    await api.post<TechnicianLocationResponse>(
      "/service/technician/location",
      payload,
    );

  return response.data;
}


export async function getTechnicianLocations():
  Promise<TechnicianLocationAdminResponse[]> {
  const response =
    await api.get<TechnicianLocationAdminResponse[]>(
      "/service/technicians/locations",
    );

  return response.data;
}
