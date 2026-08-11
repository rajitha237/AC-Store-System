export type CustomerType =
  | "cash"
  | "credit";

export type CustomerStatus =
  | "active"
  | "inactive";

export type CreditStatus =
  | "restricted"
  | "allowed";


export type Customer = {
  id: number;
  company_id: number;
  customer_number: string;

  customer_type: CustomerType;
  status: CustomerStatus;

  full_name: string;
  business_name: string | null;

  nic_number: string | null;
  registration_number: string | null;

  primary_phone: string;
  secondary_phone: string | null;
  sms_phone: string;

  email: string | null;

  address_line_1: string | null;
  address_line_2: string | null;
  city: string | null;
  district: string | null;
  province: string | null;
  postal_code: string | null;

  credit_status: CreditStatus;
  credit_limit: string | number;
  current_balance: string | number;

  sms_allowed: boolean;
  notes: string | null;

  created_by_id: number;
  updated_by_id: number | null;

  created_at: string;
  updated_at: string;
};


export type CustomerListResponse = {
  items: Customer[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};


export type CustomerCreatePayload = {
  customer_type: CustomerType;
  full_name: string;

  business_name?: string | null;
  nic_number?: string | null;
  registration_number?: string | null;

  primary_phone: string;
  secondary_phone?: string | null;
  sms_phone?: string | null;

  email?: string | null;

  address_line_1?: string | null;
  address_line_2?: string | null;
  city?: string | null;
  district?: string | null;
  province?: string | null;
  postal_code?: string | null;

  credit_status: CreditStatus;
  credit_limit: string;

  sms_allowed: boolean;

  notes?: string | null;
};


export type CustomerUpdatePayload = {
  full_name?: string | null;

  business_name?: string | null;

  customer_type?: CustomerType;
  status?: CustomerStatus;

  nic_number?: string | null;
  registration_number?: string | null;

  primary_phone?: string | null;
  secondary_phone?: string | null;
  sms_phone?: string | null;

  email?: string | null;

  address_line_1?: string | null;
  address_line_2?: string | null;
  city?: string | null;
  district?: string | null;
  province?: string | null;
  postal_code?: string | null;

  credit_status?: CreditStatus;
  credit_limit?: string | null;

  sms_allowed?: boolean;

  notes?: string | null;
};
