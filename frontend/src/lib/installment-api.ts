import { getAccessToken } from "@/lib/auth";

import type {
  CustomerLedger,
  CustomerStatement,
  InstallmentPaymentCreate,
  InstallmentPaymentResponse,
  InstallmentPlan,
  InstallmentPlanCreate,
} from "@/types/installment";

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
      }
    } catch {
      // Keep fallback message.
    }

    throw new Error(message);
  }

  return (await response.json()) as T;
}

export async function createInstallmentPlan(
  payload: InstallmentPlanCreate,
): Promise<InstallmentPlan> {
  return request<InstallmentPlan>(
    "/installments",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function receiveInstallmentPayment(
  planId: number,
  payload: InstallmentPaymentCreate,
): Promise<InstallmentPaymentResponse> {
  return request<InstallmentPaymentResponse>(
    `/installments/${planId}/payments`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function getCustomerLedger(
  customerId: number,
): Promise<CustomerLedger> {
  return request<CustomerLedger>(
    `/installments/customers/${customerId}/ledger`,
  );
}

export async function getCustomerStatement(
  customerId: number,
): Promise<CustomerStatement> {
  return request<CustomerStatement>(
    `/installments/customers/${customerId}/statement`,
  );
}

// PHASE7C9D_INSTALLMENT_READ_API

export async function getInstallmentPlans(
  params: {
    page?: number;
    page_size?: number;
    status?: string;
    customer_id?: number;
    invoice_id?: number;
  } = {},
): Promise<
  import("@/types/installment").InstallmentPlanListResponse
> {
  const search = new URLSearchParams();

  if (params.page !== undefined) {
    search.set("page", String(params.page));
  }

  if (params.page_size !== undefined) {
    search.set(
      "page_size",
      String(params.page_size),
    );
  }

  if (params.status) {
    search.set("status", params.status);
  }

  if (params.customer_id !== undefined) {
    search.set(
      "customer_id",
      String(params.customer_id),
    );
  }

  if (params.invoice_id !== undefined) {
    search.set(
      "invoice_id",
      String(params.invoice_id),
    );
  }

  const query = search.toString();

  return request<
    import("@/types/installment").InstallmentPlanListResponse
  >(
    `/installments${query ? `?${query}` : ""}`,
  );
}

export async function getInstallmentPlan(
  planId: number,
): Promise<
  import("@/types/installment").InstallmentPlan
> {
  return request<
    import("@/types/installment").InstallmentPlan
  >(`/installments/${planId}`);
}
