import { api } from "@/lib/api";

import type {
  PaymentDetailResponse,
  PaymentListParams,
  PaymentListResponse,
  PaymentReceiveRequest,
  PaymentResponse,
  PaymentReverseRequest,
} from "@/types/payments";

function compactParams(
  params: Record<
    string,
    string | number | undefined
  >,
) {
  return Object.fromEntries(
    Object.entries(params).filter(
      ([, value]) =>
        value !== undefined
        && value !== "",
    ),
  );
}

export async function getPayments(
  params: PaymentListParams = {},
): Promise<PaymentListResponse> {
  const response = await api.get(
    "/payments",
    {
      params: compactParams({
        page: params.page,
        page_size: params.pageSize,
        customer_id: params.customerId,
        invoice_id: params.invoiceId,
        payment_method:
          params.paymentMethod,
        status: params.status,
        search: params.search,
        date_from: params.dateFrom,
        date_to: params.dateTo,
      }),
    },
  );

  return response.data;
}

export async function getPayment(
  paymentId: number,
): Promise<PaymentDetailResponse> {
  const response = await api.get(
    `/payments/${paymentId}`,
  );

  return response.data;
}

export async function receivePayment(
  payload: PaymentReceiveRequest,
): Promise<PaymentDetailResponse> {
  const response = await api.post(
    "/payments",
    payload,
  );

  return response.data;
}

export async function reversePayment(
  paymentId: number,
  payload: PaymentReverseRequest,
): Promise<PaymentDetailResponse> {
  const response = await api.post(
    `/payments/${paymentId}/reverse`,
    payload,
  );

  return response.data;
}

async function downloadPdf(
  path: string,
  fallbackName: string,
) {
  const response = await api.get(
    path,
    {
      responseType: "blob",
    },
  );

  const rawContentType =
    response.headers[
      "content-type"
    ];

  const contentType =
    typeof rawContentType
      === "string"
      ? rawContentType
      : "application/pdf";

  const blob = new Blob(
    [response.data],
    {
      type:
        contentType,
    },
  );

  const contentDisposition =
    response.headers[
      "content-disposition"
    ] as string | undefined;

  let filename = fallbackName;

  if (contentDisposition) {
    const match =
      contentDisposition.match(
        /filename="?([^"]+)"?/i,
      );

    if (match?.[1]) {
      filename = match[1];
    }
  }

  const url =
    window.URL.createObjectURL(blob);

  const anchor =
    document.createElement("a");

  anchor.href = url;
  anchor.download = filename;

  document.body.appendChild(anchor);

  anchor.click();
  anchor.remove();

  window.URL.revokeObjectURL(url);
}

export async function downloadPaymentReceipt(
  paymentId: number,
  receiptNumber?: string,
) {
  await downloadPdf(
    `/documents/payment-receipts/${paymentId}/pdf`,
    `${
      receiptNumber || `payment-${paymentId}`
    }.pdf`,
  );
}

export async function downloadSalesInvoice(
  invoiceId: number,
  invoiceNumber?: string,
) {
  await downloadPdf(
    `/documents/sales-invoices/${invoiceId}/pdf`,
    `${
      invoiceNumber || `invoice-${invoiceId}`
    }.pdf`,
  );
}

export type {
  PaymentResponse,
};
