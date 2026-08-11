import {
  api,
} from "@/lib/api";

import type {
  ServiceApprovalRequest,
  ServiceJobCreate,
  ServiceJobDetailResponse,
  ServiceJobListParams,
  ServiceJobListResponse,
  ServiceJobUpdate,
  ServiceLabourCreate,
  ServicePartCreate,
  ServiceStatusChangeRequest,
} from "@/types/service-jobs";


export async function getServiceJobs(
  params:
    ServiceJobListParams = {},
): Promise<
  ServiceJobListResponse
> {
  const response =
    await api.get<
      ServiceJobListResponse
    >(
      "/service/jobs",
      {
        params: {
          page:
            params.page ?? 1,

          page_size:
            params.pageSize
            ?? 20,

          search:
            params.search
            || undefined,

          job_status:
            params.jobStatus
            || undefined,

          service_type:
            params.serviceType
            || undefined,

          priority:
            params.priority
            || undefined,

          technician_id:
            params.technicianId,

          customer_id:
            params.customerId,

          warranty_only:
            params.warrantyOnly
            || undefined,
        },
      },
    );

  return response.data;
}


export async function getServiceJob(
  jobId:
    number,
): Promise<
  ServiceJobDetailResponse
> {
  const response =
    await api.get<
      ServiceJobDetailResponse
    >(
      `/service/jobs/${jobId}`,
    );

  return response.data;
}


export async function createServiceJob(
  payload:
    ServiceJobCreate,
): Promise<
  ServiceJobDetailResponse
> {
  const response =
    await api.post<
      ServiceJobDetailResponse
    >(
      "/service/jobs",
      payload,
    );

  return response.data;
}


export async function updateServiceJob(
  jobId:
    number,

  payload:
    ServiceJobUpdate,
): Promise<
  ServiceJobDetailResponse
> {
  const response =
    await api.patch<
      ServiceJobDetailResponse
    >(
      `/service/jobs/${jobId}`,
      payload,
    );

  return response.data;
}


export async function updateServiceStatus(
  jobId:
    number,

  payload:
    ServiceStatusChangeRequest,
): Promise<
  ServiceJobDetailResponse
> {
  const response =
    await api.post<
      ServiceJobDetailResponse
    >(
      `/service/jobs/${jobId}/status`,
      payload,
    );

  return response.data;
}


export async function updateServiceApproval(
  jobId:
    number,

  payload:
    ServiceApprovalRequest,
): Promise<
  ServiceJobDetailResponse
> {
  const response =
    await api.post<
      ServiceJobDetailResponse
    >(
      `/service/jobs/${jobId}/approval`,
      payload,
    );

  return response.data;
}


export async function addServiceLabour(
  jobId:
    number,

  payload:
    ServiceLabourCreate,
): Promise<
  ServiceJobDetailResponse
> {
  const response =
    await api.post<
      ServiceJobDetailResponse
    >(
      `/service/jobs/${jobId}/labour`,
      payload,
    );

  return response.data;
}


export async function addServicePart(
  jobId:
    number,

  payload:
    ServicePartCreate,
): Promise<
  ServiceJobDetailResponse
> {
  const response =
    await api.post<
      ServiceJobDetailResponse
    >(
      `/service/jobs/${jobId}/parts`,
      payload,
    );

  return response.data;
}


export async function createServiceInvoice(
  jobId:
    number,
): Promise<unknown> {
  const response =
    await api.post(
      `/service/jobs/${jobId}/invoice`,
    );

  return response.data;
}
