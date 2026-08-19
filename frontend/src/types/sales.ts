export type InvoiceStatus =
  | "draft"
  | "confirmed"
  | "cancelled"
  | string;


export type PaymentStatus =
  | "unpaid"
  | "partial"
  | "paid"
  | string;


export type PaymentMethod =
  | "cash"
  | "card"
  | "bank_transfer"
  | "cheque"
  | "mobile_payment"
  | string;


export type SalesItemCreate = {
  product_id: number;
  warehouse_id: number;
  serial_number_id?: number | null;
  quantity: string;
  unit_price: string;
  discount_amount: string;
  description?: string | null;
};


export type SalesInvoiceCreate = {
  customer_id: number;
  branch_id?: number | null;
  invoice_discount_amount: string;
  tax_amount: string;
  notes?: string | null;
  source_type?: "legacy_service_job" | null;
  source_id?: number | null;
  items: SalesItemCreate[];
};


export type InitialPaymentCreate = {
  amount: string;
  payment_method: PaymentMethod;
  reference_number?: string | null;
  notes?: string | null;
};


export type SalesInvoiceConfirmRequest = {
  initial_payment?: InitialPaymentCreate | null;
};


export type SalesInvoiceItemResponse = {
  id: number;
  invoice_id?: number;
  product_id: number;
  warehouse_id: number;
  serial_number_id?: number | null;
  quantity: string;
  unit_price: string;
  discount_amount: string;
  line_total: string;
  description?: string | null;

  product_name?: string | null;
  product_code?: string | null;
  serial_number?: string | null;
  warehouse_name?: string | null;
};


export type CustomerPaymentResponse = {
  id: number;
  company_id: number;
  branch_id: number;
  receipt_number: string;
  customer_id: number;
  invoice_id: number | null;
  payment_date: string;
  amount: string;
  payment_method: string;
  reference_number: string | null;
  notes: string | null;
  is_reversed: boolean;
  reversed_at: string | null;
  reversal_reason: string | null;
  created_by_id: number;
  created_at: string;
};


export type SalesInvoiceResponse = {
  id: number;
  company_id: number;
  branch_id: number;
  invoice_number: string;
  customer_id: number;
  source_type: string;
  source_id: number | null;
  invoice_date: string;

  subtotal: string;
  discount_amount: string;
  tax_amount: string;
  grand_total: string;
  credited_amount: string;
  paid_amount: string;
  balance_amount: string;

  payment_status: string;
  invoice_status: string;

  notes: string | null;

  created_by_id: number;
  updated_by_id: number | null;

  created_at: string;
  updated_at: string;

  items: SalesInvoiceItemResponse[];
};


export type SalesInvoiceDetailResponse =
  SalesInvoiceResponse & {
    customer_name: string;
    customer_phone: string;
    payments: CustomerPaymentResponse[];
  };


export type SalesInvoiceListResponse = {
  items: SalesInvoiceResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};


export type SalesInvoiceListParams = {
  page?: number;
  pageSize?: number;
  search?: string;
  invoiceStatus?: string;
  paymentStatus?: string;
};


export type SalesCustomerOption = {
  id: number;
  customer_code?: string | null;
  full_name: string;
  phone?: string | null;
  mobile_number?: string | null;
  nic_number?: string | null;
  customer_type?: string;
  credit_status?: string;
  is_active: boolean;
};


export type SalesProductOption = {
  id: number;
  product_code: string;
  name: string;
  selling_price:
    | string
    | number;
  minimum_selling_price?:
    | string
    | number
    | null;
  track_serial_numbers: boolean;
  is_active: boolean;
};


export type SalesWarehouseOption = {
  id: number;
  branch_id: number;
  code: string;
  name: string;
  is_active: boolean;
};


export type SalesSerialOption = {
  id: number;
  serial_number: string;
  product_id: number;
  warehouse_id: number | null;
  status: string;
  current_customer_id?: number | null;
};


export type SalesDraftLine = {
  key: string;

  productId: string;
  warehouseId: string;
  serialNumberId: string;

  quantity: string;
  unitPrice: string;
  discountAmount: string;
  description: string;
};
