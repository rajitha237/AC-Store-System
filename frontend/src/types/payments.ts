export type PaymentMethod =
  | "cash"
  | "card"
  | "bank_transfer"
  | "mobile_payment"
  | "cheque"
  | string;

export type PaymentStatus =
  | "active"
  | "reversed"
  | string;

export type PaymentResponse = {
  id: number;
  company_id?: number;
  branch_id?: number;
  customer_id: number;
  invoice_id: number | null;

  receipt_number: string;

  payment_date: string;
  amount: string;
  payment_method: string;

  reference_number?: string | null;
  notes?: string | null;

  status?: string;

  reversed_at?: string | null;
  reversal_reason?: string | null;

  created_at?: string;
  updated_at?: string;
};

export type PaymentDetailResponse =
  PaymentResponse & {
    customer_name?: string | null;
    customer_code?: string | null;

    invoice_number?: string | null;

    transactions?: PaymentTransactionResponse[];
  };

export type PaymentTransactionResponse = {
  id?: number;
  payment_id?: number;
  transaction_type?: string;
  amount?: string;
  notes?: string | null;
  created_at?: string;
};

export type PaymentListResponse = {
  items: PaymentResponse[];
  total: number;
  page?: number;
  page_size?: number;
  pages?: number;
};

export type PaymentListParams = {
  page?: number;
  pageSize?: number;

  customerId?: number;
  invoiceId?: number;

  paymentMethod?: string;
  status?: string;

  search?: string;

  dateFrom?: string;
  dateTo?: string;
};

export type PaymentReceiveRequest = {
  invoice_id: number;
  amount: string;
  payment_method: PaymentMethod;

  reference_number?: string | null;
  notes?: string | null;
};

export type PaymentReverseRequest = {
  reason: string;
  notes?: string | null;
};
