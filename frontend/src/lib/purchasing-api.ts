import {
  api,
} from "@/lib/api";

import type {
  GoodsReceipt,
  GoodsReceiptCreatePayload,
  GoodsReceiptListResponse,
  PurchaseOrder,
  PurchaseOrderCreatePayload,
  PurchaseOrderListResponse,
  SupplierInvoice,
  SupplierInvoiceCreatePayload,
  SupplierInvoiceListResponse,
  SupplierPayment,
  SupplierPaymentCreatePayload,
  SupplierPaymentListResponse,
} from "@/types/purchasing";


export async function listPurchaseOrders(
  params: {
    page?: number;
    pageSize?: number;
    search?: string;
    status?: string;
    supplierId?: number;
    warehouseId?: number;
  } = {},
): Promise<PurchaseOrderListResponse> {
  const response =
    await api.get<PurchaseOrderListResponse>(
      "/purchase-orders",
      {
        params: {
          page:
            params.page ?? 1,

          page_size:
            params.pageSize ?? 50,

          search:
            params.search || undefined,

          order_status:
            params.status || undefined,

          supplier_id:
            params.supplierId,

          warehouse_id:
            params.warehouseId,
        },
      },
    );

  return response.data;
}


export async function getPurchaseOrder(
  purchaseOrderId: number,
): Promise<PurchaseOrder> {
  const response =
    await api.get<PurchaseOrder>(
      `/purchase-orders/${purchaseOrderId}`,
    );

  return response.data;
}


export async function createPurchaseOrder(
  payload: PurchaseOrderCreatePayload,
): Promise<PurchaseOrder> {
  const response =
    await api.post<PurchaseOrder>(
      "/purchase-orders",
      payload,
    );

  return response.data;
}


export async function approvePurchaseOrder(
  purchaseOrderId: number,
): Promise<PurchaseOrder> {
  const response =
    await api.post<PurchaseOrder>(
      `/purchase-orders/${purchaseOrderId}/approve`,
    );

  return response.data;
}


export async function receivePurchaseOrder(
  purchaseOrderId: number,
  payload: GoodsReceiptCreatePayload,
): Promise<GoodsReceipt> {
  const response =
    await api.post<GoodsReceipt>(
      `/purchase-orders/${purchaseOrderId}/receive`,
      payload,
    );

  return response.data;
}


export async function listGoodsReceipts(
  params: {
    page?: number;
    pageSize?: number;
    purchaseOrderId?: number;
    supplierId?: number;
  } = {},
): Promise<GoodsReceiptListResponse> {
  const response =
    await api.get<GoodsReceiptListResponse>(
      "/purchase-orders/goods-receipts",
      {
        params: {
          page:
            params.page ?? 1,

          page_size:
            params.pageSize ?? 100,

          purchase_order_id:
            params.purchaseOrderId,

          supplier_id:
            params.supplierId,
        },
      },
    );

  return response.data;
}


export async function createSupplierInvoice(
  payload: SupplierInvoiceCreatePayload,
): Promise<SupplierInvoice> {
  const response =
    await api.post<SupplierInvoice>(
      "/purchase-orders/supplier-invoices",
      payload,
    );

  return response.data;
}


export async function listSupplierInvoices(
  params: {
    page?: number;
    pageSize?: number;
    supplierId?: number;
    status?: string;
  } = {},
): Promise<SupplierInvoiceListResponse> {
  const response =
    await api.get<SupplierInvoiceListResponse>(
      "/purchase-orders/supplier-invoices",
      {
        params: {
          page:
            params.page ?? 1,

          page_size:
            params.pageSize ?? 100,

          supplier_id:
            params.supplierId,

          status:
            params.status || undefined,
        },
      },
    );

  return response.data;
}


export async function createSupplierPayment(
  payload: SupplierPaymentCreatePayload,
): Promise<SupplierPayment> {
  const response =
    await api.post<SupplierPayment>(
      "/purchase-orders/supplier-payments",
      payload,
    );

  return response.data;
}


export async function listSupplierPayments(
  params: {
    page?: number;
    pageSize?: number;
    supplierId?: number;
  } = {},
): Promise<SupplierPaymentListResponse> {
  const response =
    await api.get<SupplierPaymentListResponse>(
      "/purchase-orders/supplier-payments",
      {
        params: {
          page:
            params.page ?? 1,

          page_size:
            params.pageSize ?? 100,

          supplier_id:
            params.supplierId,
        },
      },
    );

  return response.data;
}
