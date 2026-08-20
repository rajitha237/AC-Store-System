export type Supplier = {
  id: number;

  company_id: number;

  supplier_code: string;

  company_name: string;

  contact_person:
    string | null;

  phone:
    string | null;

  secondary_phone:
    string | null;

  email:
    string | null;

  registration_number:
    string | null;

  tax_number:
    string | null;

  address_line_1:
    string | null;

  address_line_2:
    string | null;

  city:
    string | null;

  credit_limit:
    string | number;

  current_payable:
    string | number;

  payment_terms_days:
    number;

  notes:
    string | null;

  is_active:
    boolean;

  created_by_id:
    number;

  updated_by_id:
    number | null;

  created_at:
    string;

  updated_at:
    string;
};


export type SupplierListResponse = {
  items:
    Supplier[];

  total:
    number;

  page:
    number;

  page_size:
    number;

  total_pages:
    number;
};


export type SupplierListParams = {
  page?:
    number;

  pageSize?:
    number;

  search?:
    string;

  isActive?:
    boolean;
};


export type SupplierCreatePayload = {
  company_name:
    string;

  contact_person?:
    string | null;

  phone?:
    string | null;

  secondary_phone?:
    string | null;

  email?:
    string | null;

  registration_number?:
    string | null;

  tax_number?:
    string | null;

  address_line_1?:
    string | null;

  address_line_2?:
    string | null;

  city?:
    string | null;

  credit_limit?:
    number;

  payment_terms_days?:
    number;

  notes?:
    string | null;
};


export type SupplierUpdatePayload = {
  company_name?:
    string;

  contact_person?:
    string | null;

  phone?:
    string | null;

  secondary_phone?:
    string | null;

  email?:
    string | null;

  registration_number?:
    string | null;

  tax_number?:
    string | null;

  address_line_1?:
    string | null;

  address_line_2?:
    string | null;

  city?:
    string | null;

  credit_limit?:
    number;

  payment_terms_days?:
    number;

  notes?:
    string | null;

  is_active?:
    boolean;
};

export type SupplierInvoice = {
  id: number;
  invoice_number: string;

  supplier_id: number;
  supplier_name: string;

  purchase_order_id: number | null;
  purchase_order_number: string | null;

  goods_receipt_id: number | null;
  grn_number: string | null;

  supplier_invoice_number: string;

  invoice_date: string;
  due_date: string | null;

  subtotal: number | string;
  discount_amount: number | string;
  tax_amount: number | string;
  grand_total: number | string;

  paid_amount: number | string;
  balance_amount: number | string;

  is_overdue: boolean;
  days_overdue: number;
  aging_bucket: string;

  status: string;

  notes: string | null;

  is_reversed: boolean;

  created_at: string;
};

export type SupplierInvoiceListResponse = {
  items: SupplierInvoice[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type SupplierInvoiceListParams = {
  page?: number;
  pageSize?: number;
  supplierId?: number;
  status?: string;
};
