"use client";

import {
  useCallback,
  useMemo,
  useState,
  useSyncExternalStore,
} from "react";

import {
  ArrowDownToLine,
  Banknote,
  BarChart3,
  FileSpreadsheet,
  FileText,
  Landmark,
  RefreshCw,
  Scale,
  TrendingUp,
  WalletCards,
} from "lucide-react";

import {
  useRouter,
} from "next/navigation";

import {
  AppShell,
} from "@/components/app-shell";

import {
  clearAuthSession,
  getAccessToken,
  getStoredUser,
} from "@/lib/auth";

import {
  downloadFinancialExcel,
  downloadFinancialPdf,
  getFinancialSummary,
} from "@/lib/reports-api";

import type {
  FinancialReportsSummary,
} from "@/types/reports";

import type {
  UserResponse,
} from "@/types/auth";

import styles from "./page.module.css";


function localIsoDate(
  value: Date,
) {
  const year =
    value.getFullYear();

  const month =
    String(
      value.getMonth() + 1,
    ).padStart(
      2,
      "0",
    );

  const day =
    String(
      value.getDate(),
    ).padStart(
      2,
      "0",
    );

  return `${year}-${month}-${day}`;
}


function monthStart() {
  const today =
    new Date();

  return localIsoDate(
    new Date(
      today.getFullYear(),
      today.getMonth(),
      1,
    ),
  );
}


function todayDate() {
  return localIsoDate(
    new Date(),
  );
}


function money(
  value:
    | string
    | number
    | null
    | undefined,
) {
  const amount =
    Number(
      value ?? 0,
    );

  return new Intl.NumberFormat(
    "en-LK",
    {
      style: "currency",
      currency: "LKR",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    },
  ).format(
    Number.isFinite(amount)
      ? amount
      : 0,
  );
}


function errorMessage(
  error: unknown,
) {
  if (
    typeof error === "object"
    && error !== null
    && "response" in error
  ) {
    const response =
      (
        error as {
          response?: {
            data?: {
              detail?: unknown;
            };
          };
        }
      ).response;

    const detail =
      response?.data?.detail;

    if (
      typeof detail === "string"
      && detail.trim()
    ) {
      return detail;
    }
  }

  if (
    error instanceof Error
    && error.message
  ) {
    return error.message;
  }

  return (
    "Unable to load the "
    + "financial report."
  );
}


type SummaryCardProps = {
  label: string;
  value: string;
  hint: string;
  tone?:
    | "default"
    | "positive"
    | "warning";
  icon:
    React.ComponentType<{
      size?: number;
    }>;
};


function SummaryCard({
  label,
  value,
  hint,
  tone = "default",
  icon: Icon,
}: SummaryCardProps) {
  return (
    <article
      className={
        `${styles.summaryCard} `
        + `${
          tone === "positive"
            ? styles.positiveCard
            : tone === "warning"
              ? styles.warningCard
              : ""
        }`
      }
    >
      <div
        className={
          styles.cardIcon
        }
      >
        <Icon size={20} />
      </div>

      <div>
        <span
          className={
            styles.cardLabel
          }
        >
          {label}
        </span>

        <strong
          className={
            styles.cardValue
          }
        >
          {value}
        </strong>

        <p
          className={
            styles.cardHint
          }
        >
          {hint}
        </p>
      </div>
    </article>
  );
}


function ReportRow({
  label,
  value,
  strong = false,
  total = false,
}: {
  label: string;
  value: string;
  strong?: boolean;
  total?: boolean;
}) {
  return (
    <div
      className={
        `${styles.reportRow} `
        + `${
          strong
            ? styles.strongRow
            : ""
        } `
        + `${
          total
            ? styles.totalRow
            : ""
        }`
      }
    >
      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>
    </div>
  );
}


type AuthSnapshot = {
  token: string | null;
  user: UserResponse | null;
};


function readAuthSnapshot():
  AuthSnapshot {
  if (
    typeof window
      === "undefined"
  ) {
    return {
      token: null,
      user: null,
    };
  }

  return {
    token:
      getAccessToken(),
    user:
      getStoredUser(),
  };
}


function subscribeHydration() {
  return () => undefined;
}


function getHydratedSnapshot() {
  return true;
}


function getServerHydratedSnapshot() {
  return false;
}


export default function ReportsPage() {
  const router =
    useRouter();

  const hydrated =
    useSyncExternalStore(
      subscribeHydration,
      getHydratedSnapshot,
      getServerHydratedSnapshot,
    );

  const authSnapshot =
    hydrated
      ? readAuthSnapshot()
      : null;

  const [
    report,
    setReport,
  ] =
    useState<
      FinancialReportsSummary
      | null
    >(null);

  const [
    dateFrom,
    setDateFrom,
  ] =
    useState(
      monthStart(),
    );

  const [
    dateTo,
    setDateTo,
  ] =
    useState(
      todayDate(),
    );

  const [
    loading,
    setLoading,
  ] =
    useState(false);

  const [
    downloading,
    setDownloading,
  ] =
    useState<
      "pdf"
      | "xlsx"
      | null
    >(null);

  const [
    error,
    setError,
  ] =
    useState("");


  const validPeriod =
    useMemo(
      () =>
        Boolean(
          dateFrom
          && dateTo
          && dateFrom
            <= dateTo,
        ),
      [
        dateFrom,
        dateTo,
      ],
    );


  const loadReport =
    useCallback(
      async () => {
        if (
          !validPeriod
        ) {
          setError(
            "From date cannot "
            + "be after To date.",
          );

          return;
        }

        setLoading(
          true,
        );

        setError("");

        try {
          const data =
            await getFinancialSummary(
              {
                dateFrom,
                dateTo,
              },
            );

          setReport(
            data,
          );
        } catch (
          caught
        ) {
          setError(
            errorMessage(
              caught,
            ),
          );
        } finally {
          setLoading(
            false,
          );
        }
      },
      [
        dateFrom,
        dateTo,
        validPeriod,
      ],
    );


  async function handleDownload(
    type: "pdf" | "xlsx",
  ) {
    if (
      !validPeriod
    ) {
      setError(
        "Select a valid "
        + "date range first.",
      );

      return;
    }

    setDownloading(
      type,
    );

    setError("");

    try {
      if (
        type === "pdf"
      ) {
        await downloadFinancialPdf(
          {
            dateFrom,
            dateTo,
          },
        );
      } else {
        await downloadFinancialExcel(
          {
            dateFrom,
            dateTo,
          },
        );
      }
    } catch (
      caught
    ) {
      setError(
        errorMessage(
          caught,
        ),
      );
    } finally {
      setDownloading(
        null,
      );
    }
  }


  const user =
    authSnapshot?.user
      ?? null;

  const token =
    authSnapshot?.token
      ?? null;


  if (
    !token
    || !user
  ) {
    clearAuthSession();

    if (
      typeof window
        !== "undefined"
    ) {
      queueMicrotask(
        () => {
          router.replace(
            "/login",
          );
        },
      );
    }

    return (
      <main
        className={
          styles.authLoading
        }
      >
        Redirecting…
      </main>
    );
  }


  const pnl =
    report?.profit_and_loss;

  const cash =
    report?.cash_flow;

  const purchasing =
    report?.purchasing;

  const outstanding =
    report?.receivables;


  return (
    <AppShell user={user}>
      <main
        className={
          styles.page
        }
      >
        <section
          className={
            styles.hero
          }
        >
          <div>
            <div
              className={
                styles.eyebrow
              }
            >
              Accounts
            </div>

            <h1>
              Financial Reports
            </h1>

            <p>
              Review revenue,
              profit, cash flow,
              purchases and
              outstanding balances
              for any selected period.
            </p>
          </div>

          <div
            className={
              styles.heroIcon
            }
          >
            <BarChart3
              size={28}
            />
          </div>
        </section>

        <section
          className={
            styles.controls
          }
        >
          <div
            className={
              styles.dateField
            }
          >
            <label
              htmlFor="report-from"
            >
              From Date
            </label>

            <input
              id="report-from"
              type="date"
              value={dateFrom}
              onChange={
                (event) =>
                  setDateFrom(
                    event.target
                      .value,
                  )
              }
            />
          </div>

          <div
            className={
              styles.dateField
            }
          >
            <label
              htmlFor="report-to"
            >
              To Date
            </label>

            <input
              id="report-to"
              type="date"
              value={dateTo}
              onChange={
                (event) =>
                  setDateTo(
                    event.target
                      .value,
                  )
              }
            />
          </div>

          <button
            type="button"
            className={
              styles.refreshButton
            }
            onClick={
              () =>
                void loadReport()
            }
            disabled={
              loading
              || !validPeriod
            }
          >
            <RefreshCw
              size={17}
              className={
                loading
                  ? styles.spin
                  : ""
              }
            />

            {loading
              ? "Loading"
              : "Load Report"}
          </button>

          <div
            className={
              styles.downloadGroup
            }
          >
            <button
              type="button"
              className={
                styles.pdfButton
              }
              disabled={
                downloading
                  !== null
                || !report
              }
              onClick={
                () =>
                  void handleDownload(
                    "pdf",
                  )
              }
            >
              <FileText
                size={17}
              />

              {downloading
                === "pdf"
                ? "Preparing…"
                : "Download PDF"}
            </button>

            <button
              type="button"
              className={
                styles.csvButton
              }
              disabled={
                downloading
                  !== null
                || !report
              }
              onClick={
                () =>
                  void handleDownload(
                    "xlsx",
                  )
              }
            >
              <FileSpreadsheet
                size={17}
              />

              {downloading
                === "xlsx"
                ? "Preparing…"
                : "Download Excel"}
            </button>
          </div>
        </section>

        {error ? (
          <div
            className={
              styles.errorBox
            }
          >
            {error}
          </div>
        ) : null}

        {loading
          && !report ? (
            <section
              className={
                styles.loadingPanel
              }
            >
              <RefreshCw
                size={22}
                className={
                  styles.spin
                }
              />

              Loading financial
              report…
            </section>
          ) : null}

        {!report
          && !loading ? (
            <section
              className={
                styles.loadingPanel
              }
            >
              Select a date range
              and click Load Report.
            </section>
          ) : null}

        {report ? (
          <>
            <section
              className={
                styles.periodBar
              }
            >
              <div>
                <span>
                  Report Period
                </span>

                <strong>
                  {
                    report.period
                      .date_from
                  }
                  {" — "}
                  {
                    report.period
                      .date_to
                  }
                </strong>
              </div>

              <div
                className={
                  styles.periodStatus
                }
              >
                <ArrowDownToLine
                  size={16}
                />
                Ready to export
              </div>
            </section>

            <section
              className={
                styles.summaryGrid
              }
            >
              <SummaryCard
                label="Net Revenue"
                value={
                  money(
                    pnl?.net_revenue,
                  )
                }
                hint={
                  "Confirmed sales "
                  + "after credits"
                }
                icon={
                  TrendingUp
                }
              />

              <SummaryCard
                label="Gross Profit"
                value={
                  money(
                    pnl?.gross_profit,
                  )
                }
                hint={
                  "Revenue less "
                  + "recorded COGS"
                }
                tone="positive"
                icon={
                  Scale
                }
              />

              <SummaryCard
                label="Net Profit"
                value={
                  money(
                    pnl?.net_profit,
                  )
                }
                hint={
                  "After recorded "
                  + "operating expenses"
                }
                tone="positive"
                icon={
                  Banknote
                }
              />

              <SummaryCard
                label="Net Cash Flow"
                value={
                  money(
                    cash?.net_cash_flow,
                  )
                }
                hint={
                  "Cash in less "
                  + "cash out"
                }
                icon={
                  WalletCards
                }
              />

              <SummaryCard
                label="Receivables"
                value={
                  money(
                    outstanding
                      ?.customer_receivables,
                  )
                }
                hint={
                  "Current customer "
                  + "outstanding"
                }
                tone="warning"
                icon={
                  Landmark
                }
              />

              <SummaryCard
                label="Payables"
                value={
                  money(
                    outstanding
                      ?.supplier_payables,
                  )
                }
                hint={
                  "Current supplier "
                  + "outstanding"
                }
                tone="warning"
                icon={
                  Landmark
                }
              />
            </section>

            <section
              className={
                styles.reportGrid
              }
            >
              <article
                className={
                  styles.panel
                }
              >
                <div
                  className={
                    styles.panelHeader
                  }
                >
                  <div>
                    <span>
                      Profitability
                    </span>

                    <h2>
                      Profit & Loss
                    </h2>
                  </div>

                  <TrendingUp
                    size={21}
                  />
                </div>

                <div
                  className={
                    styles.rows
                  }
                >
                  <ReportRow
                    label="Gross sales"
                    value={
                      money(
                        pnl?.gross_sales,
                      )
                    }
                  />

                  <ReportRow
                    label={
                      "Sales credits "
                      + "/ reductions"
                    }
                    value={
                      money(
                        pnl?.sales_credits,
                      )
                    }
                  />

                  <ReportRow
                    label="Net revenue"
                    value={
                      money(
                        pnl?.net_revenue,
                      )
                    }
                    strong
                  />

                  <ReportRow
                    label={
                      "Cost of "
                      + "goods sold"
                    }
                    value={
                      money(
                        pnl
                          ?.cost_of_goods_sold,
                      )
                    }
                  />

                  <ReportRow
                    label="Gross profit"
                    value={
                      money(
                        pnl?.gross_profit,
                      )
                    }
                    strong
                  />

                  <ReportRow
                    label={
                      "Recorded "
                      + "operating expenses"
                    }
                    value={
                      money(
                        pnl
                          ?.operating_expenses,
                      )
                    }
                  />

                  <ReportRow
                    label="Net profit"
                    value={
                      money(
                        pnl?.net_profit,
                      )
                    }
                    strong
                    total
                  />
                </div>
              </article>

              <article
                className={
                  styles.panel
                }
              >
                <div
                  className={
                    styles.panelHeader
                  }
                >
                  <div>
                    <span>
                      Liquidity
                    </span>

                    <h2>
                      Cash Flow
                    </h2>
                  </div>

                  <WalletCards
                    size={21}
                  />
                </div>

                <div
                  className={
                    styles.rows
                  }
                >
                  <ReportRow
                    label={
                      "Customer "
                      + "collections"
                    }
                    value={
                      money(
                        cash
                          ?.customer_collections,
                      )
                    }
                  />

                  <ReportRow
                    label={
                      "Manual cash in"
                    }
                    value={
                      money(
                        cash
                          ?.manual_cash_in,
                      )
                    }
                  />

                  <ReportRow
                    label={
                      "Total cash in"
                    }
                    value={
                      money(
                        cash
                          ?.total_cash_in,
                      )
                    }
                    strong
                  />

                  <ReportRow
                    label={
                      "Supplier payments"
                    }
                    value={
                      money(
                        cash
                          ?.supplier_payments,
                      )
                    }
                  />

                  <ReportRow
                    label={
                      "Manual cash out"
                    }
                    value={
                      money(
                        cash
                          ?.manual_cash_out,
                      )
                    }
                  />

                  <ReportRow
                    label={
                      "Total cash out"
                    }
                    value={
                      money(
                        cash
                          ?.total_cash_out,
                      )
                    }
                    strong
                  />

                  <ReportRow
                    label={
                      "Net cash flow"
                    }
                    value={
                      money(
                        cash
                          ?.net_cash_flow,
                      )
                    }
                    strong
                    total
                  />
                </div>
              </article>

              <article
                className={
                  styles.panel
                }
              >
                <div
                  className={
                    styles.panelHeader
                  }
                >
                  <div>
                    <span>
                      Procurement
                    </span>

                    <h2>
                      Purchasing
                    </h2>
                  </div>

                  <FileSpreadsheet
                    size={21}
                  />
                </div>

                <div
                  className={
                    styles.rows
                  }
                >
                  <ReportRow
                    label={
                      "Supplier invoices"
                    }
                    value={
                      money(
                        purchasing
                          ?.supplier_invoices,
                      )
                    }
                  />

                  <ReportRow
                    label={
                      "Supplier payments"
                    }
                    value={
                      money(
                        purchasing
                          ?.supplier_payments,
                      )
                    }
                  />
                </div>
              </article>

              <article
                className={
                  styles.panel
                }
              >
                <div
                  className={
                    styles.panelHeader
                  }
                >
                  <div>
                    <span>
                      Outstanding
                    </span>

                    <h2>
                      Balances
                    </h2>
                  </div>

                  <Landmark
                    size={21}
                  />
                </div>

                <div
                  className={
                    styles.rows
                  }
                >
                  <ReportRow
                    label={
                      "Customer "
                      + "receivables"
                    }
                    value={
                      money(
                        outstanding
                          ?.customer_receivables,
                      )
                    }
                    strong
                  />

                  <ReportRow
                    label={
                      "Supplier payables"
                    }
                    value={
                      money(
                        outstanding
                          ?.supplier_payables,
                      )
                    }
                    strong
                  />
                </div>
              </article>
            </section>

            <section
              className={
                styles.accountingNote
              }
            >
              <strong>
                Accounting note
              </strong>

              <p>
                Profit is calculated
                separately from cash
                collections. Customer
                collections may include
                payments for invoices
                or installments from
                earlier periods.
                Operating expenses show
                only expenses currently
                recorded in the Cash
                Book.
              </p>
            </section>
          </>
        ) : null}
      </main>
    </AppShell>
  );
}
