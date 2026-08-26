import {
  api,
} from "@/lib/api";

import type {
  CashBookFilters,
  CashBookListResponse,
  CashBookSummary,
  ManualCashBookEntry,
  ManualCashBookEntryCreate,
  ManualCashBookEntryReverseRequest,
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
