import { getAccessToken } from "@/lib/auth";

import type {
  QuickSaleConfirmResponse,
  QuickSaleCustomer,
  QuickSaleCustomerCreate,
  QuickSaleDraftInvoice,
  QuickSaleProduct,
  QuickSaleSerial,
} from "@/types/quick-sale";

function apiBase(): string {
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://127.0.0.1:8000/api/v1"
  ).replace(/\/$/, "");
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);

  if (!headers.has("Content-Type")) {
    headers.set(
      "Content-Type",
      "application/json",
    );
  }

  const accessToken = getAccessToken();

  if (accessToken) {
    headers.set(
      "Authorization",
      `Bearer ${accessToken}`,
    );
  }

  const response = await fetch(
    `${apiBase()}${path}`,
    {
      ...init,
      headers,
      cache: "no-store",
    },
  );

  if (!response.ok) {
    let message =
      `Request failed (${response.status})`;

    try {
      const body = await response.json();

      if (
        body &&
        typeof body.detail === "string"
      ) {
        message = body.detail;
      } else if (
        body &&
        Array.isArray(body.detail)
      ) {
        message = body.detail
          .map(
            (
              item: {
                msg?: string;
              },
            ) => item.msg ?? "Validation error",
          )
          .join(", ");
      }
    } catch {
      // Keep fallback.
    }

    throw new Error(message);
  }

  return (await response.json()) as T;
}

function unwrapItems<T>(
  value: unknown,
): T[] {
  if (Array.isArray(value)) {
    return value as T[];
  }

  if (
    value &&
    typeof value === "object"
  ) {
    const record =
      value as Record<string, unknown>;

    for (const key of [
      "items",
      "results",
      "data",
      "customers",
      "products",
      "serials",
    ]) {
      if (Array.isArray(record[key])) {
        return record[key] as T[];
      }
    }
  }

  return [];
}

export async function searchCustomers(
  search: string,
): Promise<QuickSaleCustomer[]> {
  const query =
    new URLSearchParams();

  if (search.trim()) {
    query.set(
      "search",
      search.trim(),
    );
  }

  query.set("page", "1");
  query.set("page_size", "20");

  const value = await request<unknown>(
    `/customers?${query.toString()}`,
  );

  return unwrapItems<QuickSaleCustomer>(
    value,
  );
}

export async function createCustomer(
  payload: QuickSaleCustomerCreate,
): Promise<QuickSaleCustomer> {
  return request<QuickSaleCustomer>(
    "/customers",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function searchProducts(
  search: string,
): Promise<QuickSaleProduct[]> {
  const query =
    new URLSearchParams();

  if (search.trim()) {
    query.set(
      "search",
      search.trim(),
    );
  }

  query.set("page", "1");
  query.set("page_size", "30");

  const candidates = [
    `/catalog/products?${query.toString()}`,
    `/inventory/products?${query.toString()}`,
    `/products?${query.toString()}`,
  ];

  let lastError:
    | Error
    | null = null;

  for (const path of candidates) {
    try {
      const value =
        await request<unknown>(path);

      return unwrapItems<QuickSaleProduct>(
        value,
      );
    } catch (error) {
      lastError =
        error instanceof Error
          ? error
          : new Error(
              "Product search failed",
            );
    }
  }

  throw (
    lastError ??
    new Error(
      "Product search endpoint unavailable",
    )
  );
}

export async function getQuickSaleAverageCost(
  productId: number,
  warehouseId: number,
): Promise<number | null> {
  const query = new URLSearchParams();

  query.set("product_id", String(productId));
  query.set("warehouse_id", String(warehouseId));

  const value = await request<unknown>(
    `/inventory/balances?${query.toString()}`,
  );

  const balances = unwrapItems<
    {
      product_id?: number;
      warehouse_id?: number;
      average_cost?: number | string;
    }
  >(value);

  const balance = balances.find(
    (item) =>
      Number(item.product_id) === productId &&
      Number(item.warehouse_id) === warehouseId,
  );

  if (!balance) {
    return null;
  }

  const averageCost = Number(balance.average_cost);

  return Number.isFinite(averageCost)
    ? averageCost
    : null;
}


export async function getAvailableSerials(
  productId: number,
): Promise<QuickSaleSerial[]> {
  const candidates = [
    // AC_PHASE7C4B_SERIAL_ENDPOINT_CONTRACT_REPAIR
    `/inventory/serial-numbers?product_id=${productId}&serial_status=available`,
    `/catalog/products/${productId}/serials`,
    `/inventory/products/${productId}/serials`,
  ];

  for (const path of candidates) {
    try {
      const value =
        await request<unknown>(path);

      return unwrapItems<QuickSaleSerial>(
        value,
      );
    } catch {
      // Try next known read-only endpoint.
    }
  }

  return [];
}

// AC_QUICK_SALE_WAREHOUSE_CONTRACT_REPAIR_V3
export async function createDraftInvoice(
  payload: {
    branch_id: number;
    customer_id: number;
    invoice_discount_amount: number;
    tax_amount: number;
    notes?: string | null;
    trade_ins?: Array<{
      brand?: string | null;
      model?: string | null;
      serial_number?: string | null;
      condition?: string | null;
      description?: string | null;
      allowance_amount: number;
    }>;
    items: Array<{
      product_id: number;
      quantity: number;
      unit_price: number;
      discount_amount: number;
      warehouse_id: number;
      serial_number_id?: number | null;
    }>;
  },
): Promise<QuickSaleDraftInvoice> {
  return request<QuickSaleDraftInvoice>(
    "/sales/invoices",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export type QuickSalePaymentInput = {
  amount: number;
  payment_method: string;
  reference_number?: string | null;
  notes?: string | null;
};


export async function confirmInvoice(
  invoiceId: number,
  initialPayment:
    | QuickSalePaymentInput
    | null = null,
  initialPayments:
    QuickSalePaymentInput[] = [],
): Promise<QuickSaleConfirmResponse> {
  return request<QuickSaleConfirmResponse>(
    `/sales/invoices/${invoiceId}/confirm`,
    {
      method: "POST",
      body: JSON.stringify({
        initial_payment:
          initialPayment,
        initial_payments:
          initialPayments,
      }),
    },
  );
}


export async function receiveQuickSaleSplitPayments(
  invoiceId: number,
  payments: QuickSalePaymentInput[],
): Promise<{
  payments: Array<{
    id: number;
    receipt_number: string;
    amount: string;
    payment_method: string;
    reference_number?: string | null;
  }>;
  invoice: QuickSaleConfirmResponse;
}> {
  return request(
    `/sales/invoices/${invoiceId}/split-payments`,
    {
      method: "POST",
      body: JSON.stringify({
        payments,
      }),
    },
  );
}

async function downloadPdf(
  path: string,
  fallbackName: string,
): Promise<void> {
  const headers =
    new Headers();

  const accessToken = getAccessToken();

  if (accessToken) {
    headers.set(
      "Authorization",
      `Bearer ${accessToken}`,
    );
  }

  const response = await fetch(
    `${apiBase()}${path}`,
    {
      headers,
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      `PDF download failed (${response.status})`,
    );
  }

  const blob = await response.blob();

  const url =
    URL.createObjectURL(blob);

  const anchor =
    document.createElement("a");

  anchor.href = url;
  anchor.download = fallbackName;

  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  URL.revokeObjectURL(url);
}

export async function downloadInvoicePdf(
  invoiceId: number,
  invoiceNumber?: string,
): Promise<void> {
  await downloadPdf(
    `/documents/sales-invoices/${invoiceId}/pdf`,
    `${invoiceNumber ?? `invoice-${invoiceId}`}.pdf`,
  );
}

export async function downloadReceiptPdf(
  paymentId: number,
  receiptNumber?: string,
): Promise<void> {
  await downloadPdf(
    `/documents/payment-receipts/${paymentId}/pdf`,
    `${receiptNumber ?? `receipt-${paymentId}`}.pdf`,
  );
}
