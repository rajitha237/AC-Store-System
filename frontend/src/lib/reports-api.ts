import {
  api,
} from "@/lib/api";

import type {
  FinancialReportsSummary,
} from "@/types/reports";


export type FinancialReportFilters = {
  dateFrom: string;
  dateTo: string;
};


function params(
  filters: FinancialReportFilters,
) {
  return {
    date_from: filters.dateFrom,
    date_to: filters.dateTo,
  };
}


export async function getFinancialSummary(
  filters: FinancialReportFilters,
): Promise<FinancialReportsSummary> {
  const response =
    await api.get<FinancialReportsSummary>(
      "/reports/financial-summary",
      {
        params: params(filters),
      },
    );

  return response.data;
}


async function downloadReport(
  path: string,
  filters: FinancialReportFilters,
  fallbackFilename: string,
) {
  const response =
    await api.get<Blob>(
      path,
      {
        params: params(filters),
        responseType: "blob",
      },
    );

  const disposition =
    response.headers[
      "content-disposition"
    ];

  let filename = fallbackFilename;

  if (
    typeof disposition === "string"
  ) {
    const match =
      disposition.match(
        /filename="?([^"]+)"?/i,
      );

    if (match?.[1]) {
      filename = match[1];
    }
  }

  const url =
    window.URL.createObjectURL(
      response.data,
    );

  const anchor =
    document.createElement("a");

  anchor.href = url;
  anchor.download = filename;

  document.body.appendChild(
    anchor,
  );

  anchor.click();
  anchor.remove();

  window.URL.revokeObjectURL(
    url,
  );
}


export async function downloadFinancialPdf(
  filters: FinancialReportFilters,
) {
  return downloadReport(
    "/reports/financial-summary.pdf",
    filters,
    (
      `financial-report-`
      + `${filters.dateFrom}-`
      + `${filters.dateTo}.pdf`
    ),
  );
}


export async function downloadFinancialCsv(
  filters: FinancialReportFilters,
) {
  return downloadReport(
    "/reports/financial-summary.csv",
    filters,
    (
      `financial-report-`
      + `${filters.dateFrom}-`
      + `${filters.dateTo}.csv`
    ),
  );
}

export async function downloadFinancialExcel(
  filters: FinancialReportFilters,
) {
  return downloadReport(
    "/reports/financial-summary.xlsx",
    filters,
    (
      `financial-report-`
      + `${filters.dateFrom}-`
      + `${filters.dateTo}.xlsx`
    ),
  );
}
