export type InstallmentFrequency =
  | "weekly"
  | "biweekly"
  | "monthly";

export type InstallmentPaymentMethod =
  | "cash"
  | "card"
  | "bank_transfer"
  | "cheque"
  | "other";

export interface InstallmentScheduleItem {
  id?: number;
  installment_number?: number;
  due_date?: string;
  amount?: number | string;
  paid_amount?: number | string;
  outstanding_amount?: number | string;
  status?: string;
}

export interface InstallmentPlanCreate {
  invoice_id: number;
  frequency: InstallmentFrequency;
  installment_count: number;
  first_due_date: string;
  grace_days: number;
  interest_rate: number;
  notes?: string | null;
}

export interface InstallmentPlan {
  id: number;
  agreement_number: string;
  invoice_id: number;
  invoice_number: string;
  customer_id: number;
  customer_name: string;
  principal_amount: number | string;
  interest_rate: number | string;
  interest_amount: number | string;
  financed_amount: number | string;
  installment_count: number;
  frequency: string;
  first_due_date: string;
  start_date: string;
  grace_days: number;
  scheduled_installment_amount: number | string;
  total_paid: number | string;
  outstanding_amount: number | string;
  overdue_amount: number | string;
  overdue_installment_count: number;
  next_due_date?: string | null;
  next_due_amount?: number | string | null;
  status: string;
  notes?: string | null;
  created_at: string;
  schedules: InstallmentScheduleItem[];
}

export interface InstallmentPaymentCreate {
  amount: number;
  payment_method: InstallmentPaymentMethod;
  reference_number?: string | null;
  notes?: string | null;
}

export interface InstallmentPaymentResponse {
  payment_id: number;
  receipt_number: string;
  amount: number | string;
  principal_amount: number | string;
  interest_amount: number | string;
  payment_method: string;
  plan_id: number;
  agreement_number: string;
  customer_id: number;
  customer_balance: number | string;
  invoice_id: number;
  invoice_number: string;
  invoice_paid_amount: number | string;
  invoice_balance_amount: number | string;
  plan_total_paid: number | string;
  plan_outstanding_amount: number | string;
  message: string;
  allocations: unknown[];
}

export interface LedgerEntry {
  [key: string]: unknown;
}

export interface CustomerLedger {
  customer_id: number;
  customer_name: string;
  customer_number: string;
  date_from?: string | null;
  date_to?: string | null;
  opening_balance: number | string;
  total_debits: number | string;
  total_credits: number | string;
  closing_balance: number | string;
  entries: LedgerEntry[];
}

export interface CustomerStatement
  extends CustomerLedger {
  generated_at: string;
}

// PHASE7C9D_INSTALLMENT_LIST_CONTRACT
export interface InstallmentPlanListResponse {
  items: InstallmentPlan[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface InstallmentPlanListParams {
  page?: number;
  page_size?: number;
  status?: string;
  customer_id?: number;
  invoice_id?: number;
}
