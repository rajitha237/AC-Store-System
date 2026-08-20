export type PurchaseOrderStatus =
  | "draft"
  | "approved"
  | "partially_received"
  | "received"
  | "cancelled"
  | string;


export type PurchaseOrderItemInput = {
  product_id: number;
  quantity: string;
  unit_cost: string;
  discount_amount?: string;
  tax_amount?: string;
  notes?: string | null;
};


export type PurchaseOrderCreatePayload = {
  supplier_id: number;
  warehouse_id: number;
  order_date?: string;
  expected_date?: string | null;
  notes?: string | null;
  items: PurchaseOrderItemInput[];
};


export type PurchaseOrderItem = {
  id: number;
  product_id: number;

  product_code?: string;
  product_name?: string;

  track_serial_numbers?: boolean;

  quantity?: string | number;
  quantity_ordered?: string | number;
  quantity_received?: string | number;

  unit_cost: string | number;
  discount_amount?: string | number;
  tax_amount?: string | number;
  line_total?: string | number;

  notes?: string | null;
};


export type PurchaseOrder = {
  id: number;
  purchase_order_number: string;

  supplier_id: number;
  supplier_name?: string;

  warehouse_id: number;
  warehouse_name?: string;

  order_date: string;
  expected_date?: string | null;

  status: PurchaseOrderStatus;

  subtotal?: string | number;
  discount_amount?: string | number;
  tax_amount?: string | number;
  grand_total: string | number;

  notes?: string | null;

  created_at?: string;

  items?: PurchaseOrderItem[];
};


export type PurchaseOrderListResponse = {
  items: PurchaseOrder[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};


export type GoodsReceiptSerialInput = {
  serial_number: string;
  secondary_serial_number?: string | null;
};


export type GoodsReceiptItemInput = {
  purchase_order_item_id: number;
  quantity: string;
  serials?: GoodsReceiptSerialInput[];
};


export type GoodsReceiptCreatePayload = {
  delivery_note_number?: string | null;
  notes?: string | null;
  items: GoodsReceiptItemInput[];
};


export type GoodsReceipt = {
  id: number;
  grn_number: string;

  purchase_order_id: number;
  purchase_order_number?: string;

  supplier_id: number;
  supplier_name?: string;

  warehouse_id?: number;
  warehouse_name?: string;

  delivery_note_number?: string | null;

  received_at?: string;
  notes?: string | null;

  po_status?: string;

  items?: Array<{
    id?: number;
    purchase_order_item_id: number;
    product_id?: number;
    product_code?: string;
    product_name?: string;
    quantity_received: string | number;
    unit_cost?: string | number;
  }>;
};


export type GoodsReceiptListResponse = {
  items: GoodsReceipt[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
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

  subtotal: string | number;
  discount_amount: string | number;
  tax_amount: string | number;
  grand_total: string | number;

  paid_amount: string | number;
  balance_amount: string | number;

  is_overdue: boolean;
  days_overdue: number;
  aging_bucket: string;

  status: string;
  notes: string | null;
  is_reversed: boolean;
  created_at: string;
};


export type SupplierInvoiceCreatePayload = {
  supplier_id: number;
  purchase_order_id?: number | null;
  goods_receipt_id?: number | null;

  supplier_invoice_number: string;

  invoice_date?: string | null;
  due_date?: string | null;

  subtotal: string;
  discount_amount?: string;
  tax_amount?: string;

  notes?: string | null;
};


export type SupplierInvoiceListResponse = {
  items: SupplierInvoice[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};


export type SupplierPaymentCreatePayload = {
  supplier_id: number;
  supplier_invoice_id?: number | null;

  amount: string;
  payment_method: string;

  reference_number?: string | null;
  notes?: string | null;
};


export type SupplierPayment = {
  id: number;

  payment_number?: string;

  supplier_id: number;
  supplier_name?: string;

  supplier_invoice_id?: number | null;
  invoice_number?: string | null;

  amount: string | number;
  payment_method: string;

  reference_number?: string | null;
  notes?: string | null;

  is_reversed?: boolean;
  created_at?: string;
};


export type SupplierPaymentListResponse = {
  items: SupplierPayment[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};
