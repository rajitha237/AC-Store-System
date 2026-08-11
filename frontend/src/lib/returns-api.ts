import {
  api,
} from "@/lib/api";

import type {
  ReplacementItemRequest,
  ReturnApprovalRequest,
  ReturnInspectionRequest,
  ReturnStatusChangeRequest,
  SalesReturnCreate,
  SalesReturnDetailResponse,
  SalesReturnListParams,
  SalesReturnListResponse,
} from "@/types/returns";


export async function getReturns(
  params:
    SalesReturnListParams = {},
): Promise<
  SalesReturnListResponse
> {
  const response =
    await api.get<
      SalesReturnListResponse
    >(
      "/returns",
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

          return_status:
            params.returnStatus
            || undefined,

          return_type:
            params.returnType
            || undefined,

          resolution:
            params.resolution
            || undefined,
        },
      },
    );

  return response.data;
}


export async function getReturn(
  returnId: number,
): Promise<
  SalesReturnDetailResponse
> {
  const response =
    await api.get<
      SalesReturnDetailResponse
    >(
      `/returns/${returnId}`,
    );

  return response.data;
}


export async function createReturn(
  payload:
    SalesReturnCreate,
): Promise<
  SalesReturnDetailResponse
> {
  const response =
    await api.post<
      SalesReturnDetailResponse
    >(
      "/returns",
      payload,
    );

  return response.data;
}


export async function inspectReturn(
  returnId: number,

  payload:
    ReturnInspectionRequest,
): Promise<
  SalesReturnDetailResponse
> {
  const response =
    await api.post<
      SalesReturnDetailResponse
    >(
      `/returns/${returnId}/inspect`,
      payload,
    );

  return response.data;
}


export async function approveReturn(
  returnId: number,

  payload:
    ReturnApprovalRequest,
): Promise<
  SalesReturnDetailResponse
> {
  const response =
    await api.post<
      SalesReturnDetailResponse
    >(
      `/returns/${returnId}/approval`,
      payload,
    );

  return response.data;
}


export async function processReturn(
  returnId: number,
): Promise<
  SalesReturnDetailResponse
> {
  const response =
    await api.post<
      SalesReturnDetailResponse
    >(
      `/returns/${returnId}/process`,
    );

  return response.data;
}


export async function setReplacementItem(
  returnId: number,

  payload:
    ReplacementItemRequest,
): Promise<
  SalesReturnDetailResponse
> {
  const response =
    await api.post<
      SalesReturnDetailResponse
    >(
      `/returns/${returnId}/replacement`,
      payload,
    );

  return response.data;
}


export async function changeReturnStatus(
  returnId: number,

  payload:
    ReturnStatusChangeRequest,
): Promise<
  SalesReturnDetailResponse
> {
  const response =
    await api.post<
      SalesReturnDetailResponse
    >(
      `/returns/${returnId}/status`,
      payload,
    );

  return response.data;
}
