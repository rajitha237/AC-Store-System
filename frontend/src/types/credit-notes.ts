export type CreditNoteStatus =
  | "draft"
  | "approved"
  | "posted"
  | "reversed"
  | string;


export type RefundStatus =
  | "pending"
  | "posted"
  | "reversed"
  | string;


export type RefundMethod =
  | "cash"
  | "card"
  | "bank_transfer"
  | "mobile_payment"
  | "cheque"
  | string;


export type FinancialReversalRequest = {
  reason: string;
};


export type CreditNoteCreate = {
  return_id: number;

  notes?:
    string | null;
};


export type CreditNoteApprovalRequest = {
  notes?:
    string | null;
};


export type RefundCreate = {
  credit_note_id:
    number;

  amount:
    string;

  refund_method?:
    RefundMethod;

  reference_number?:
    string | null;

  notes?:
    string | null;
};


export type CustomerRefundResponse = {
  id:
    number;

  company_id:
    number;

  branch_id:
    number;

  refund_number:
    string;

  credit_note_id:
    number;

  return_id:
    number;

  invoice_id:
    number;

  customer_id:
    number;

  amount:
    string;

  refund_method:
    string;

  status:
    string;

  reference_number:
    string | null;

  notes:
    string | null;

  posted_by_id:
    number | null;

  posted_at:
    string | null;

  is_reversed:
    boolean;

  reversed_by_id:
    number | null;

  reversed_at:
    string | null;

  reversal_reason:
    string | null;

  created_by_id:
    number;

  created_at:
    string;
};


export type CreditNoteDetailResponse = {
  id:
    number;

  company_id:
    number;

  branch_id:
    number;

  credit_note_number:
    string;

  invoice_id:
    number;

  return_id:
    number;

  customer_id:
    number;

  amount:
    string;

  status:
    string;

  reason:
    string;

  notes:
    string | null;

  approved_by_id:
    number | null;

  approved_at:
    string | null;

  posted_by_id:
    number | null;

  posted_at:
    string | null;

  is_reversed:
    boolean;

  reversed_by_id:
    number | null;

  reversed_at:
    string | null;

  reversal_reason:
    string | null;

  created_by_id:
    number;

  created_at:
    string;

  updated_at:
    string;

  invoice_number:
    string;

  return_number:
    string;

  customer_name:
    string;

  customer_phone:
    string;

  invoice_grand_total:
    string;

  invoice_paid_amount:
    string;

  invoice_balance_amount:
    string;

  active_refund_total:
    string;

  refundable_overpayment:
    string;

  refunds:
    CustomerRefundResponse[];
};


export type CreditNoteListResult = {
  items:
    CreditNoteDetailResponse[];

  total:
    number;

  page:
    number;

  page_size:
    number;

  total_pages:
    number;
};


export type CreditNoteListParams = {
  page?:
    number;

  pageSize?:
    number;

  search?:
    string;

  status?:
    string;
};
