import type {
  InstallmentFrequency,
} from "@/types/installment";

export interface QuickSaleCustomer {
  id: number;
  customer_number?: string;
  full_name?: string;
  business_name?: string | null;
  nic_number?: string | null;
  primary_phone?: string | null;
  sms_phone?: string | null;
  sms_allowed?: boolean;
  current_balance?: number | string;
  credit_limit?: number | string;
  credit_status?: string;
  status?: string;
}

export interface QuickSaleProduct {
  id: number;
  sku?: string;
  product_code?: string;
  barcode?: string | null;
  name?: string;
  product_name?: string;
  selling_price?: number | string;
  sale_price?: number | string;
  retail_price?: number | string;
  unit_price?: number | string;
  // AC_PHASE7C3_SERIALIZED_PRODUCT_DETECTION_REPAIR
  track_serial_numbers?: boolean | number;
  track_serial?: boolean;
  is_serialized?: boolean;
  requires_serial?: boolean;
  status?: string;
  [key: string]: unknown;
}

export interface QuickSaleSerial {
  id: number;
  serial_number?: string;
  secondary_serial_number?: string | null;
  status?: string;
  product_id?: number;
  warehouse_id?: number;
  [key: string]: unknown;
}

export // AC_QUICK_SALE_WAREHOUSE_CONTRACT_REPAIR_V3
interface QuickSaleCartItem {
  key: string;
  productId: number;
  warehouseId: number;
  productName: string;
  sku: string;
  quantity: number;
  unitPrice: number;
  discountAmount: number;
  // AC_BELOW_COST_UI_PROTECTION
  averageCost: number | null;
  serialId?: number | null;
  serialNumber?: string | null;
}

export interface QuickSaleCustomerCreate {
  full_name: string;
  primary_phone: string;
  nic_number?: string | null;
  address_line_1?: string | null;
  city?: string | null;
  sms_allowed: boolean;
  sms_phone?: string | null;
}

export interface QuickSaleDraftInvoice {
  id: number;
  invoice_number?: string;
  total_amount?: number | string;
  grand_total?: number | string;
  net_total?: number | string;
  paid_amount?: number | string;
  balance_amount?: number | string;
  status?: string;
  [key: string]: unknown;
}

export interface QuickSaleConfirmResponse {
  id?: number;
  invoice_id?: number;
  invoice_number?: string;
  payment_id?: number | null;
  receipt_number?: string | null;
  paid_amount?: number | string;
  balance_amount?: number | string;
  status?: string;
  [key: string]: unknown;
}

export interface InstallmentPreview {
  number: number;
  dueDate: string;
  amount: number;
}

export interface QuickSaleFormState {
  branchId: number;
  paymentMode: "cash" | "installment";
  paymentMethod:
    | "cash"
    | "card"
    | "bank_transfer"
    | "cheque"
    | "other";
  downPayment: string;
  interestRate: string;
  referenceNumber: string;
  notes: string;
  frequency: InstallmentFrequency;
  installmentCount: number;
  firstDueDate: string;
  graceDays: number;
}
