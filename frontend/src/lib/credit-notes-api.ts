import {
  api,
} from "@/lib/api";

import type {
  CreditNoteApprovalRequest,
  CreditNoteCreate,
  CreditNoteDetailResponse,
  CreditNoteListParams,
  CreditNoteListResult,
  CustomerRefundResponse,
  FinancialReversalRequest,
  RefundCreate,
} from "@/types/credit-notes";


type UnknownRecord =
  Record<string, unknown>;


function record(
  value: unknown,
): UnknownRecord {
  if (
    value !== null
    && typeof value === "object"
    && !Array.isArray(value)
  ) {
    return value as UnknownRecord;
  }

  return {};
}


function normalizeList(
  value: unknown,
  requestedPage: number,
  pageSize: number,
): CreditNoteListResult {
  if (Array.isArray(value)) {
    return {
      items:
        value as CreditNoteDetailResponse[],

      total:
        value.length,

      page:
        requestedPage,

      page_size:
        pageSize,

      total_pages:
        value.length > 0
          ? 1
          : 0,
    };
  }

  const data =
    record(value);

  const rawItems =
    Array.isArray(data.items)
      ? data.items
      : Array.isArray(data.results)
        ? data.results
        : [];

  const total =
    Number(
      data.total
      ?? rawItems.length,
    );

  const page =
    Number(
      data.page
      ?? requestedPage,
    );

  const size =
    Number(
      data.page_size
      ?? data.pageSize
      ?? pageSize,
    );

  const pages =
    Number(
      data.total_pages
      ?? data.pages
      ?? (
        size > 0
          ? Math.ceil(
              total / size,
            )
          : 0
      ),
    );

  return {
    items:
      rawItems as CreditNoteDetailResponse[],

    total:
      Number.isFinite(total)
        ? total
        : rawItems.length,

    page:
      Number.isFinite(page)
        ? page
        : requestedPage,

    page_size:
      Number.isFinite(size)
        ? size
        : pageSize,

    total_pages:
      Number.isFinite(pages)
        ? pages
        : 0,
  };
}


export async function getCreditNotes(
  params:
    CreditNoteListParams = {},
): Promise<
  CreditNoteListResult
> {
  const page =
    params.page ?? 1;

  const pageSize =
    params.pageSize ?? 20;

  const response =
    await api.get<unknown>(
      "/credit-notes",
      {
        params: {
          page,

          page_size:
            pageSize,

          search:
            params.search
            || undefined,

          credit_note_status:
            params.status
            || undefined,
        },
      },
    );

  return normalizeList(
    response.data,
    page,
    pageSize,
  );
}


export async function getCreditNote(
  creditNoteId:
    number,
): Promise<
  CreditNoteDetailResponse
> {
  const response =
    await api.get<
      CreditNoteDetailResponse
    >(
      `/credit-notes/${creditNoteId}`,
    );

  return response.data;
}


export async function createCreditNote(
  payload:
    CreditNoteCreate,
): Promise<
  CreditNoteDetailResponse
> {
  const response =
    await api.post<
      CreditNoteDetailResponse
    >(
      "/credit-notes",
      payload,
    );

  return response.data;
}


export async function approveCreditNote(
  creditNoteId:
    number,

  payload:
    CreditNoteApprovalRequest,
): Promise<
  CreditNoteDetailResponse
> {
  const response =
    await api.post<
      CreditNoteDetailResponse
    >(
      `/credit-notes/${creditNoteId}/approval`,
      payload,
    );

  return response.data;
}


export async function postCreditNote(
  creditNoteId:
    number,
): Promise<
  CreditNoteDetailResponse
> {
  const response =
    await api.post<
      CreditNoteDetailResponse
    >(
      `/credit-notes/${creditNoteId}/post`,
    );

  return response.data;
}


export async function reverseCreditNote(
  creditNoteId:
    number,

  payload:
    FinancialReversalRequest,
): Promise<
  CreditNoteDetailResponse
> {
  const response =
    await api.post<
      CreditNoteDetailResponse
    >(
      `/credit-notes/${creditNoteId}/reverse`,
      payload,
    );

  return response.data;
}


export async function createRefund(
  payload:
    RefundCreate,
): Promise<
  CustomerRefundResponse
> {
  const response =
    await api.post<
      CustomerRefundResponse
    >(
      "/credit-notes/refunds",
      payload,
    );

  return response.data;
}


export async function postRefund(
  refundId:
    number,
): Promise<
  CustomerRefundResponse
> {
  const response =
    await api.post<
      CustomerRefundResponse
    >(
      `/credit-notes/refunds/${refundId}/post`,
    );

  return response.data;
}


export async function reverseRefund(
  refundId:
    number,

  payload:
    FinancialReversalRequest,
): Promise<
  CustomerRefundResponse
> {
  const response =
    await api.post<
      CustomerRefundResponse
    >(
      `/credit-notes/refunds/${refundId}/reverse`,
      payload,
    );

  return response.data;
}
