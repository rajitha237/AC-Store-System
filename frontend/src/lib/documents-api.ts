import {
  api,
} from "@/lib/api";

import type {
  DownloadedDocument,
} from "@/types/documents";


function filenameFromDisposition(
  disposition:
    string | undefined,

  fallback:
    string,
): string {
  if (!disposition) {
    return fallback;
  }

  const utf8Match =
    disposition.match(
      /filename\*=UTF-8''([^;]+)/i,
    );

  if (
    utf8Match
    && utf8Match[1]
  ) {
    try {
      return decodeURIComponent(
        utf8Match[1]
          .replace(
            /^["']|["']$/g,
            "",
          ),
      );
    } catch {
      return utf8Match[1];
    }
  }

  const normalMatch =
    disposition.match(
      /filename="?([^";]+)"?/i,
    );

  if (
    normalMatch
    && normalMatch[1]
  ) {
    return normalMatch[1];
  }

  return fallback;
}


async function downloadPdf(
  url:
    string,

  fallbackFilename:
    string,
): Promise<
  DownloadedDocument
> {
  const response =
    await api.get<Blob>(
      url,
      {
        responseType:
          "blob",
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

  const blob =
    response.data
      instanceof Blob
      ? response.data
      : new Blob(
          [response.data],
          {
            type:
              contentType,
          },
        );

  const rawDisposition =
    response.headers[
      "content-disposition"
    ];

  const disposition =
    typeof rawDisposition
      === "string"
      ? rawDisposition
      : undefined;

  return {
    blob,

    filename:
      filenameFromDisposition(
        disposition,
        fallbackFilename,
      ),
  };
}


export async function
downloadSalesInvoicePdf(
  invoiceId:
    number,
): Promise<
  DownloadedDocument
> {
  return downloadPdf(
    (
      "/documents/"
      + "sales-invoices/"
      + `${invoiceId}/pdf`
    ),
    `sales-invoice-${invoiceId}.pdf`,
  );
}


export async function
downloadServiceJobCardPdf(
  jobId:
    number,
): Promise<
  DownloadedDocument
> {
  return downloadPdf(
    (
      "/documents/"
      + "service-jobs/"
      + `${jobId}/pdf`
    ),
    `job-card-${jobId}.pdf`,
  );
}


export async function
downloadPaymentReceiptPdf(
  paymentId:
    number,
): Promise<
  DownloadedDocument
> {
  return downloadPdf(
    (
      "/documents/"
      + "payment-receipts/"
      + `${paymentId}/pdf`
    ),
    `payment-receipt-${paymentId}.pdf`,
  );
}


export function
saveDownloadedDocument(
  document:
    DownloadedDocument,
): void {
  const url =
    URL.createObjectURL(
      document.blob,
    );

  const anchor =
    window.document
      .createElement(
        "a",
      );

  anchor.href =
    url;

  anchor.download =
    document.filename;

  anchor.style.display =
    "none";

  window.document.body
    .appendChild(
      anchor,
    );

  anchor.click();

  anchor.remove();

  window.setTimeout(
    () => {
      URL.revokeObjectURL(
        url,
      );
    },
    1000,
  );
}
