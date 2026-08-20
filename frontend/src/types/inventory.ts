export type Warehouse = {
  id: number;
  branch_id: number;

  code: string;
  name: string;

  warehouse_type: string;

  is_active: boolean;

  created_at: string;
};


export type StockBalance = {
  id: number;

  warehouse_id: number;
  warehouse_code: string;
  warehouse_name: string;

  product_id: number;
  product_code: string;
  product_name: string;

  track_serial_numbers: boolean;

  quantity_on_hand: string;
  quantity_reserved: string;
  quantity_available: string;

  average_cost: string;

  reorder_level: string;

  is_low_stock: boolean;
};


export type StockMovementType =
  | "opening_balance"
  | "purchase_receipt"
  | "sale_issue"
  | "sale_return"
  | "sale_return_reversal"
  | "replacement_issue"
  | "supplier_return"
  | "service_usage"
  | "adjustment_increase"
  | "adjustment_decrease"
  | "transfer_in"
  | "transfer_out"
  | "write_off";


export type StockMovement = {
  id: number;

  company_id: number;
  branch_id: number;

  warehouse_id: number;
  product_id: number;

  serial_number_id: number | null;

  movement_type: string;

  quantity: string;
  unit_cost: string;

  reference_type: string | null;
  reference_id: string | null;

  movement_date: string;

  notes: string | null;

  created_by_id: number;

  created_at: string;
};


export type StockMovementListResponse = {
  items?: StockMovement[];
  movements?: StockMovement[];

  total?: number;

  page?: number;
  page_size?: number;
  total_pages?: number;
};


export type NormalizedMovementList = {
  items: StockMovement[];

  total: number;

  page: number;
  page_size: number;
  total_pages: number;
};


export type SerialNumberStatus =
  | "available"
  | "reserved"
  | "sold"
  | "service"
  | "faulty"
  | "returned"
  | "supplier_claim"
  | string;


export type SerialNumberDetail = {
  id: number;

  company_id?: number;
  branch_id?: number;

  product_id: number;

  warehouse_id: number | null;

  serial_number: string;

  status: SerialNumberStatus;

  unit_cost?: string | number;

  current_customer_id?: number | null;

  warranty_start_date?: string | null;
  warranty_end_date?: string | null;

  reference_type?: string | null;
  reference_id?: string | null;

  notes?: string | null;

  created_at?: string;
  updated_at?: string;
};



// INVENTORY PHASE 3 - RECEIVE STOCK TYPES

export type NonSerializedReceivePayload = {
  product_id: number;
  warehouse_id: number;
  supplier_id?: number | null;

  quantity: string;
  unit_cost: string;

  reference_type: string;
  reference_id?: string | null;

  notes?: string | null;
};


export type SerializedReceiveItem = {
  serial_number: string;
};


export type SerializedReceivePayload = {
  product_id: number;
  warehouse_id: number;
  supplier_id?: number | null;

  unit_cost: string;

  reference_type: string;
  reference_id?: string | null;

  notes?: string | null;

  serials: SerializedReceiveItem[];
};


export type StockReceiveResponse = {
  product_id?: number;
  warehouse_id?: number;

  quantity_received:
    | string
    | number;

  quantity_on_hand:
    | string
    | number;

  average_cost:
    | string
    | number;

  movement?: StockMovement;

  serials?:
    SerialNumberDetail[];
};


export type StockAdjustmentDirection =
  | "increase"
  | "decrease";


export type StockAdjustmentPayload = {
  product_id: number;

  warehouse_id: number;

  direction:
    StockAdjustmentDirection;

  quantity: string;

  unit_cost?:
    string | null;

  reference_id?:
    string | null;

  reason: string;

  notes?:
    string | null;
};


export type StockAdjustmentResult = {
  message: string;

  product_id: number;
  warehouse_id: number;

  direction:
    StockAdjustmentDirection;

  quantity_adjusted:
    string | number;

  quantity_on_hand:
    string | number;

  quantity_reserved:
    string | number;

  quantity_available:
    string | number;

  average_cost:
    string | number;
};


export type NonSerializedTransferPayload = {
  product_id: number;

  source_warehouse_id: number;

  destination_warehouse_id: number;

  quantity: string;

  reference_id?:
    string | null;

  reason: string;

  notes?:
    string | null;
};


export type NonSerializedTransferResult = {
  message: string;

  product_id: number;

  source_warehouse_id: number;

  destination_warehouse_id: number;

  quantity_transferred:
    string | number;

  source_quantity_on_hand:
    string | number;

  source_quantity_reserved:
    string | number;

  source_quantity_available:
    string | number;

  destination_quantity_on_hand:
    string | number;

  destination_quantity_reserved:
    string | number;

  destination_quantity_available:
    string | number;

  destination_average_cost:
    string | number;
};


export type SerializedTransferPayload = {
  product_id: number;

  source_warehouse_id: number;

  destination_warehouse_id: number;

  serial_number_ids:
    number[];

  reference_id?:
    string | null;

  reason: string;

  notes?:
    string | null;
};


export type SerializedTransferResult = {
  message: string;

  product_id: number;

  source_warehouse_id: number;

  destination_warehouse_id: number;

  quantity_transferred:
    string | number;

  source_quantity_on_hand:
    string | number;

  destination_quantity_on_hand:
    string | number;

  serials:
    SerialNumberDetail[];
};
