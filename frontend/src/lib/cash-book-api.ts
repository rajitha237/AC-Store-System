import {
  api,
} from "@/lib/api";

import type {
  CashBookDailyApproval,
  CashBookDailyApprovalStatus,
  CashBookFilters,
  CashBookListResponse,
  CashBookSummary,
  ManualCashBookEntry,
  ManualCashBookEntryCreate,
  ManualCashBookEntryReverseRequest,
  ManualCashBookEntryUpdate,
  ManualChequeClearRequest,
} from "@/types/cash-book";


function cashBookParams(
  filters: CashBookFilters = {},
) {
  return {
    page:
      filters.page,
    page_size:
      filters.pageSize,
    branch_id:
      filters.branchId,
    date_from:
      filters.dateFrom,
    date_to:
      filters.dateTo,
  };
}


export async function getCashBook(
  filters: CashBookFilters = {},
): Promise<CashBookListResponse> {
  const response =
    await api.get<CashBookListResponse>(
      "/cash-book",
      {
        params:
          cashBookParams(
            filters,
          ),
      },
    );

  return response.data;
}


export async function getCashBookSummary(
  filters: Omit<
    CashBookFilters,
    "page" | "pageSize"
  > = {},
): Promise<CashBookSummary> {
  const response =
    await api.get<CashBookSummary>(
      "/cash-book/summary",
      {
        params: {
          branch_id:
            filters.branchId,
          date_from:
            filters.dateFrom,
          date_to:
            filters.dateTo,
        },
      },
    );

  return response.data;
}


export async function createManualCashBookEntry(
  payload: ManualCashBookEntryCreate,
): Promise<ManualCashBookEntry> {
  const response =
    await api.post<ManualCashBookEntry>(
      "/cash-book/manual",
      payload,
    );

  return response.data;
}


export async function updateManualCashBookEntry(
  entryId: number,
  payload: ManualCashBookEntryUpdate,
): Promise<ManualCashBookEntry> {
  const response =
    await api.patch<ManualCashBookEntry>(
      `/cash-book/manual/${entryId}`,
      payload,
    );

  return response.data;
}


export async function confirmManualCashBookCheque(
  entryId: number,
  payload: ManualChequeClearRequest = {},
): Promise<ManualCashBookEntry> {
  const response =
    await api.post<ManualCashBookEntry>(
      `/cash-book/manual/${entryId}/confirm-cheque`,
      payload,
    );

  return response.data;
}


export async function deleteManualCashBookEntry(
  entryId: number,
): Promise<ManualCashBookEntry> {
  const response =
    await api.delete<ManualCashBookEntry>(
      `/cash-book/manual/${entryId}`,
    );

  return response.data;
}


export async function reverseManualCashBookEntry(
  entryId: number,
  payload: ManualCashBookEntryReverseRequest,
): Promise<ManualCashBookEntry> {
  const response =
    await api.post<ManualCashBookEntry>(
      `/cash-book/manual/${entryId}/reverse`,
      payload,
    );

  return response.data;
}


export type CustomerPaymentUpdateRequest = {
  payment_date: string;
  amount: string;
  payment_method: string;
  reference_number: string | null;
  cheque_date: string | null;
  notes: string | null;
};

export async function updateCustomerPayment(
  paymentId: number,
  payload: CustomerPaymentUpdateRequest,
): Promise<void> {
  await api.patch(
    `/payments/${paymentId}`,
    payload,
  );
}

export async function reverseCustomerPayment(
  paymentId: number,
  reason: string,
): Promise<void> {
  await api.post(
    `/payments/${paymentId}/reverse`,
    {
      reason,
    },
  );
}



export async function getCashBookDailyApproval(
  businessDate: string,
): Promise<CashBookDailyApprovalStatus> {
  const response =
    await api.get<CashBookDailyApprovalStatus>(
      `/cash-book/approvals/${businessDate}`,
    );

  return response.data;
}


export async function approveCashBookDay(
  businessDate: string,
  notes: string | null = null,
): Promise<CashBookDailyApproval> {
  const response =
    await api.post<CashBookDailyApproval>(
      "/cash-book/approvals",
      {
        business_date: businessDate,
        notes,
      },
    );

  return response.data;
}


export async function downloadCashBookPdf(
  dateFrom: string,
  dateTo: string,
): Promise<Blob> {
  const response =
    await api.get<Blob>(
      "/cash-book/report.pdf",
      {
        params: {
          date_from: dateFrom,
          date_to: dateTo,
        },
        responseType: "blob",
      },
    );

  return response.data;
}
