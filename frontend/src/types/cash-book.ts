export type CashBookEntryType =
  | "cash_in"
  | "cash_out";


export type CashBookSummary = {
  opening_balance: string;
  cash_in: string;
  cash_out: string;
  closing_balance: string;
  transaction_count: number;
};


export type CashBookTransaction = {
  source_type: string;
  source_id: number;
  source_reference: string | null;

  direction: CashBookEntryType;

  transaction_date: string;
  amount: string;
  payment_method: string;

  category: string;
  description: string;

  reference_number: string | null;
  notes: string | null;

  branch_id: number | null;

  status: string;

  cheque_date: string | null;
  cheque_status: string | null;
  cheque_cleared_at: string | null;

  can_edit: boolean;
  can_delete: boolean;
  can_confirm_cheque: boolean;

  running_balance: string | null;
};


export type CashBookListResponse = {
  items: CashBookTransaction[];
  total: number;
  page: number;
  page_size: number;
  pages: number;

  summary: CashBookSummary;
};


export type ManualCashBookEntryCreate = {
  entry_type: CashBookEntryType;
  entry_date?: string | null;
  amount: string;
  payment_method?: string;
  category: string;
  description: string;
  reference_number?: string | null;
  cheque_date?: string | null;
  notes?: string | null;
};


export type ManualCashBookEntryUpdate = {
  entry_type: CashBookEntryType;
  entry_date: string;
  amount: string;
  payment_method?: string;
  category: string;
  description: string;
  reference_number?: string | null;
  cheque_date?: string | null;
  notes?: string | null;
};


export type ManualChequeClearRequest = {
  notes?: string | null;
};


export type ManualCashBookEntryReverseRequest = {
  reason: string;
  notes?: string | null;
};


export type ManualCashBookEntry = {
  id: number;
  company_id: number;
  branch_id: number;

  entry_number: string;
  entry_type: string;
  entry_date: string;

  amount: string;
  payment_method: string;

  category: string;
  description: string;

  reference_number: string | null;

  cheque_date: string | null;
  cheque_status: string | null;
  cheque_cleared_at: string | null;
  cheque_cleared_by_id: number | null;

  notes: string | null;

  created_by_id: number;

  reversed_at: string | null;
  reversed_by_id: number | null;
  reversal_reason: string | null;

  created_at: string;
  updated_at: string;
};


export type CashBookFilters = {
  page?: number;
  pageSize?: number;
  branchId?: number;
  dateFrom?: string;
  dateTo?: string;
};
