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
