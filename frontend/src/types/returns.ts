export type ReturnType =
  | "sales_return"
  | string;

export type ReturnStatus =
  | "requested"
  | "inspected"
  | "approved"
  | "rejected"
  | "completed"
  | "cancelled"
  | string;

export type ReturnResolution =
  | "pending"
  | "refund"
  | "replacement"
  | "rejected"
  | string;

export type ReturnItemCondition =
  | "good"
  | "opened"
  | "damaged"
  | "faulty"
  | string;


export type SalesReturnItemCreate = {
  invoice_item_id: number;
  quantity: string;

  condition:
    ReturnItemCondition;

  reason?: string | null;

  destination_warehouse_id?:
    number | null;
};


export type SalesReturnCreate = {
  invoice_id: number;

  return_type:
    ReturnType;

  reason: string;

  items:
    SalesReturnItemCreate[];
};


export type ReturnInspectionRequest = {
  inspection_notes: string;
};


export type ReturnApprovalRequest = {
  approved: boolean;

  resolution:
    ReturnResolution;

  approval_notes?:
    string | null;

  refund_amount:
    string;
};


export type ReturnStatusChangeRequest = {
  new_status:
    ReturnStatus;

  remarks?:
    string | null;
};


export type ReplacementItemRequest = {
  return_item_id: number;

  replacement_product_id:
    number;

  replacement_serial_number_id?:
    number | null;

  warehouse_id:
    number;

  notes?:
    string | null;
};


export type SalesReturnStatusHistoryResponse = {
  id: number;
  return_id: number;

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


export type SalesReturnItemResponse = {
  id: number;

  return_id: number;

  invoice_item_id: number;

  product_id:
    number | null;

  serial_number_id:
    number | null;

  quantity:
    string;

  unit_price:
    string;

  line_total:
    string;

  condition:
    string;

  reason:
    string | null;

  destination_warehouse_id:
    number | null;

  stock_movement_id:
    number | null;

  replacement_product_id:
    number | null;

  replacement_serial_number_id:
    number | null;

  replacement_stock_movement_id:
    number | null;

  notes:
    string | null;

  created_at:
    string;
};


export type SalesReturnResponse = {
  id: number;

  company_id: number;
  branch_id: number;

  return_number:
    string;

  invoice_id:
    number;

  customer_id:
    number;

  return_type:
    string;

  status:
    string;

  resolution:
    string;

  reason:
    string;

  inspection_notes:
    string | null;

  approval_notes:
    string | null;

  subtotal:
    string;

  refund_amount:
    string;

  approved_by_id:
    number | null;

  approved_at:
    string | null;

  completed_at:
    string | null;

  created_by_id:
    number;

  updated_by_id:
    number | null;

  created_at:
    string;

  updated_at:
    string;
};


export type SalesReturnDetailResponse =
  SalesReturnResponse & {
    invoice_number:
      string;

    customer_name:
      string;

    customer_phone:
      string;

    items:
      SalesReturnItemResponse[];

    status_history:
      SalesReturnStatusHistoryResponse[];
  };


export type SalesReturnListResponse = {
  items:
    SalesReturnDetailResponse[];

  total:
    number;

  page:
    number;

  page_size:
    number;

  total_pages:
    number;
};


export type SalesReturnListParams = {
  page?: number;

  pageSize?: number;

  search?: string;

  returnStatus?: string;

  returnType?: string;

  resolution?: string;
};


export type ReturnDraftItem = {
  invoiceItemId:
    number;

  selected:
    boolean;

  quantity:
    string;

  condition:
    ReturnItemCondition;

  reason:
    string;

  destinationWarehouseId:
    string;
};
