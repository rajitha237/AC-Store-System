export type ServiceJobStatus =
  | "received"
  | "inspection"
  | "waiting_approval"
  | "approved"
  | "repairing"
  | "testing"
  | "ready"
  | "delivered"
  | "cancelled";


export type ServiceJobPriority =
  | "low"
  | "normal"
  | "high"
  | "urgent";


export type ServiceType =
  | "repair"
  | "warranty"
  | "installation"
  | "maintenance"
  | "inspection"
  | "other";


export type ApprovalStatus =
  | "not_required"
  | "pending"
  | "approved"
  | "rejected";


export type ServiceJobCreate = {
  customer_id:
    number;

  branch_id?:
    number | null;

  product_id?:
    number | null;

  sold_serial_id?:
    number | null;

  serial_number?:
    string | null;

  secondary_serial_number?:
    string | null;

  brand_name?:
    string | null;

  model_number?:
    string | null;

  item_color?:
    string | null;

  service_type:
    ServiceType;

  priority:
    ServiceJobPriority;

  complaint:
    string;

  reported_issue?:
    string | null;

  accessories_received?:
    string | null;

  physical_condition?:
    string | null;

  special_notes?:
    string | null;

  technician_id?:
    number | null;

  receiving_officer_id?:
    number | null;

  is_warranty_job:
    boolean;

  related_invoice_id?:
    number | null;

  estimated_cost:
    string;

  expected_completion_date?:
    string | null;
};


export type ServiceJobUpdate = {
  technician_id?:
    number | null;

  technician_diagnosis?:
    string | null;

  work_performed?:
    string | null;

  testing_result?:
    string | null;

  reported_issue?:
    string | null;

  accessories_received?:
    string | null;

  physical_condition?:
    string | null;

  special_notes?:
    string | null;

  warranty_notes?:
    string | null;

  estimated_cost?:
    string | null;

  discount_amount?:
    string | null;

  expected_completion_date?:
    string | null;
  scheduled_visit_date?:
    string | null;

};


export type ServiceApprovalRequest = {
  approval_status:
    ApprovalStatus;

  remarks?:
    string | null;
};


export type ServiceStatusChangeRequest = {
  new_status:
    ServiceJobStatus;

  remarks?:
    string | null;
};


export type ServiceLabourCreate = {
  description:
    string;

  hours:
    string;

  amount:
    string;

  notes?:
    string | null;
};


export type ServicePartCreate = {
  product_id:
    number;

  warehouse_id:
    number;

  quantity:
    string;

  unit_price?:
    string | null;

  notes?:
    string | null;
};


export type ServiceJobStatusHistoryResponse = {
  id:
    number;

  job_card_id:
    number;

  old_status:
    string | null;

  new_status:
    string;

  remarks:
    string | null;

  changed_by_id:
    number;

  created_at:
    string;
};


export type ServiceLabourResponse = {
  id:
    number;

  job_card_id:
    number;

  description:
    string;

  hours:
    string;

  amount:
    string;

  notes:
    string | null;

  created_by_id:
    number;

  created_at:
    string;
};


export type ServicePartResponse = {
  id:
    number;

  job_card_id:
    number;

  product_id:
    number;

  warehouse_id:
    number;

  quantity:
    string;

  unit_cost:
    string;

  unit_price:
    string;

  line_total:
    string;

  stock_movement_id:
    number | null;

  notes:
    string | null;

  created_by_id:
    number;

  created_at:
    string;
};


export type ServiceJobDetailResponse = {
  scheduled_visit_date?:
    string | null;

  id:
    number;

  company_id:
    number;

  branch_id:
    number;

  job_number:
    string;

  customer_id:
    number;

  customer_name:
    string;

  customer_phone:
    string;

  product_id:
    number | null;

  product_name:
    string | null;

  product_code:
    string | null;

  sold_serial_id:
    number | null;

  serial_number:
    string | null;

  secondary_serial_number:
    string | null;

  brand_name:
    string | null;

  model_number:
    string | null;

  item_color:
    string | null;

  service_type:
    string;

  priority:
    string;

  status:
    string;

  approval_status:
    string;

  complaint:
    string;

  reported_issue:
    string | null;

  technician_diagnosis:
    string | null;

  work_performed:
    string | null;

  testing_result:
    string | null;

  accessories_received:
    string | null;

  physical_condition:
    string | null;

  special_notes:
    string | null;

  technician_id:
    number | null;

  technician_name:
    string | null;

  receiving_officer_id:
    number | null;

  receiving_officer_name:
    string | null;

  is_warranty_job:
    boolean;

  warranty_verified:
    boolean;

  warranty_notes:
    string | null;

  related_invoice_id:
    number | null;

  estimated_cost:
    string;

  labour_total:
    string;

  parts_total:
    string;

  discount_amount:
    string;

  final_amount:
    string;

  received_at:
    string;

  expected_completion_date:
    string | null;

  approval_at:
    string | null;

  completed_at:
    string | null;

  delivered_at:
    string | null;

  created_by_id:
    number;

  updated_by_id:
    number | null;

  created_at:
    string;

  updated_at:
    string;

  status_history:
    ServiceJobStatusHistoryResponse[];

  parts:
    ServicePartResponse[];

  labour_items:
    ServiceLabourResponse[];
};


export type ServiceJobListResponse = {
  items:
    ServiceJobDetailResponse[];

  total:
    number;

  page:
    number;

  page_size:
    number;

  total_pages:
    number;
};


export type ServiceJobListParams = {
  page?:
    number;

  pageSize?:
    number;

  search?:
    string;

  jobStatus?:
    ServiceJobStatus | "";

  serviceType?:
    ServiceType | "";

  priority?:
    ServiceJobPriority | "";

  technicianId?:
    number;

  customerId?:
    number;

  warrantyOnly?:
    boolean;
};

// ============================================================
// LEGACY SERVICE JOB HISTORY
// ============================================================

export type LegacyServiceJobLineResponse = {
  id: number;
  line_number: number;
  legacy_code: string | null;
  name: string | null;
  line_type: string;
  quantity: string;
  rate: string;
  discount: string;
  discount_value: string;
  line_total: string;
  unit: string | null;
  serial_no: string | null;
};

export type LegacyServiceJobListItemResponse = {
  id: number;
  legacy_job_id: number;
  invoice_code: string | null;

  job_date: string;
  job_time: string | null;

  reference_no: string | null;
  sale_type: string | null;

  legacy_customer_id: number | null;
  customer_name: string | null;
  customer_phone: string | null;
  customer_address: string | null;

  source_total: string;
  net_amount: string;
  pay_amount: string;
  rest_amount: string;

  cash_amount: string;
  credit_amount: string;
  cheque_amount: string;
  card_amount: string;
  bank_amount: string;

  is_cancelled: boolean;

  legacy_user_id: number | null;
  legacy_user_name: string | null;

  legacy_service_date: string | null;
  legacy_warranty_period: string | null;

  management_status: string;
  status_remarks: string | null;
  status_updated_at: string | null;
  status_updated_by_id: number | null;
};

export type LegacyAdditionalSaleItemResponse = {
  product_id: number | null;
  product_code: string | null;
  product_name: string | null;
  warehouse_id: number | null;
  warehouse_code: string | null;
  warehouse_name: string | null;
  quantity: string;
  unit_price: string;
  line_total: string;
};

export type LegacyAdditionalSaleResponse = {
  id: number;
  invoice_number: string;
  grand_total: string;
  paid_amount: string;
  balance_amount: string;
  payment_status: string;
  invoice_status: string;
  created_at: string;
  items: LegacyAdditionalSaleItemResponse[];
};


export type LegacyServiceJobDetailResponse =
  LegacyServiceJobListItemResponse & {
    bill_discount: string;
    bill_discount_value: string;

    gross_amount: string;
    profit: string;

    over_balance_amount: string;
    balance_amount: string;

    migration_notes: string | null;

    lines: LegacyServiceJobLineResponse[];
    additional_sales: LegacyAdditionalSaleResponse[];
  };

export type LegacyServiceJobHistoryListResponse = {
  items: LegacyServiceJobListItemResponse[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type LegacyServiceJobListParams = {
  page?: number;
  pageSize?: number;
  search?: string;
  cancelled?: boolean;
};



export type LegacyServiceJobStatusUpdateRequest = {
  status: string;
  remarks?: string | null;
};


export type LegacyServiceJobStatusUpdateResponse = {
  legacy_job_id: number;
  management_status: string;
  status_remarks: string | null;
  status_updated_at: string;
  status_updated_by_id: number | null;
};
