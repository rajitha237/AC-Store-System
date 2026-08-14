"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { useRouter } from "next/navigation";

import {
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  CircleDollarSign,
  Download,
  FileText,
  LoaderCircle,
  Printer,
  RefreshCw,
  Search,
  WalletCards,
  X,
} from "lucide-react";

import { AppShell } from "@/components/app-shell";

import {
  getCurrentUser,
} from "@/lib/auth-api";

import {
  clearAuthSession,
  getAccessToken,
  getStoredUser,
  setStoredUser,
} from "@/lib/auth";

import type {
  UserResponse,
} from "@/types/auth";

import {
  getInstallmentPlan,
  getInstallmentPlans,
  receiveInstallmentPayment,
} from "@/lib/installment-api";

import {
  downloadPaymentReceipt,
} from "@/lib/payments-api";

import type {
  InstallmentPaymentMethod,
  InstallmentPaymentResponse,
  InstallmentPlan,
} from "@/types/installment";

import styles from "./installments.module.css";

// PHASE7C9D_INSTALLMENTS_MANAGEMENT_UI
// PHASE7C9E_V2_APPSHELL_INTEGRATION
// PHASE7_INSTALLMENT_PAYMENT_UI

function money(
  value: number | string | null | undefined,
): string {
  const numeric = Number(value ?? 0);

  return `LKR ${(
    Number.isFinite(numeric)
      ? numeric
      : 0
  ).toLocaleString("en-LK", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function prettyStatus(
  value: string | null | undefined,
): string {
  if (!value) {
    return "Unknown";
  }

  return value
    .replaceAll("_", " ")
    .replace(
      /\b\w/g,
      (letter) => letter.toUpperCase(),
    );
}

function shortDate(
  value: string | null | undefined,
): string {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(
    "en-GB",
    {
      year: "numeric",
      month: "short",
      day: "2-digit",
    },
  ).format(date);
}

export default function InstallmentsPage() {
  const router = useRouter();

  const [
    user,
    setUser,
  ] = useState<UserResponse | null>(
    null,
  );

  const [
    authLoading,
    setAuthLoading,
  ] = useState(true);

  const [plans, setPlans] =
    useState<InstallmentPlan[]>([]);

  const [selected, setSelected] =
    useState<InstallmentPlan | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [detailLoading, setDetailLoading] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const [search, setSearch] =
    useState("");

  const [statusFilter, setStatusFilter] =
    useState("all");

  const [paymentOpen, setPaymentOpen] =
    useState(false);

  const [paymentAmount, setPaymentAmount] =
    useState("");

  const [
    paymentMethod,
    setPaymentMethod,
  ] = useState<InstallmentPaymentMethod>(
    "cash",
  );

  const [
    paymentReference,
    setPaymentReference,
  ] = useState("");

  const [paymentNotes, setPaymentNotes] =
    useState("");

  const [
    paymentSubmitting,
    setPaymentSubmitting,
  ] = useState(false);

  const [
    paymentError,
    setPaymentError,
  ] = useState<string | null>(null);

  const [
    paymentResult,
    setPaymentResult,
  ] = useState<InstallmentPaymentResponse | null>(
    null,
  );

  const [
    receiptLoading,
    setReceiptLoading,
  ] = useState(false);

  const refreshPlans = useCallback(
    async () => {
      setLoading(true);
      setError(null);

      try {
        const response =
          await getInstallmentPlans({
            page: 1,
            page_size: 100,
          });

        setPlans(
          Array.isArray(response.items)
            ? response.items
            : [],
        );
      } catch (requestError) {
        console.error(
          "Installment refresh failed",
          requestError,
        );

        setError(
          "Installment agreements could not be loaded.",
        );
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    async function loadAuthenticatedUser() {
      const token = getAccessToken();

      if (!token) {
        router.replace("/login");
        setAuthLoading(false);
        return;
      }

      const cached = getStoredUser();

      if (cached) {
        setUser(cached);
      }

      try {
        const current =
          await getCurrentUser();

        setStoredUser(current);
        setUser(current);
      } catch (requestError) {
        console.error(
          "Installments authentication failed",
          requestError,
        );

        clearAuthSession();
        router.replace("/login");
      } finally {
        setAuthLoading(false);
      }
    }

    void loadAuthenticatedUser();
  }, [router]);

  useEffect(() => {
    let active = true;

    getInstallmentPlans({
      page: 1,
      page_size: 100,
    })
      .then((response) => {
        if (!active) {
          return;
        }

        setPlans(
          Array.isArray(response.items)
            ? response.items
            : [],
        );

        setError(null);
      })
      .catch((requestError: unknown) => {
        if (!active) {
          return;
        }

        console.error(
          "Initial installment load failed",
          requestError,
        );

        setError(
          "Installment agreements could not be loaded.",
        );
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const filteredPlans = useMemo(() => {
    const needle =
      search.trim().toLowerCase();

    return plans.filter((plan) => {
      const statusMatches =
        statusFilter === "all"
        || plan.status === statusFilter;

      if (!statusMatches) {
        return false;
      }

      if (!needle) {
        return true;
      }

      return [
        plan.agreement_number,
        plan.invoice_number,
        plan.customer_name,
        String(plan.customer_id),
      ].some((value) =>
        String(value ?? "")
          .toLowerCase()
          .includes(needle),
      );
    });
  }, [plans, search, statusFilter]);

  const metrics = useMemo(() => {
    return plans.reduce(
      (result, plan) => {
        result.financed += Number(
          plan.financed_amount ?? 0,
        );

        result.outstanding += Number(
          plan.outstanding_amount ?? 0,
        );

        if (plan.status === "active") {
          result.active += 1;
        }

        if (
          Number(
            plan.overdue_installment_count
            ?? 0,
          ) > 0
        ) {
          result.overdue += 1;
        }

        return result;
      },
      {
        financed: 0,
        outstanding: 0,
        active: 0,
        overdue: 0,
      },
    );
  }, [plans]);

  async function openPlan(
    plan: InstallmentPlan,
  ) {
    setSelected(plan);
    setDetailLoading(true);
    setError(null);

    try {
      const detail =
        await getInstallmentPlan(plan.id);

      setSelected(detail);
    } catch (requestError) {
      console.error(
        "Installment detail load failed",
        requestError,
      );

      setError(
        "Agreement details could not be loaded.",
      );
    } finally {
      setDetailLoading(false);
    }
  }

  function openPaymentForm() {
    if (!selected) {
      return;
    }

    const outstanding =
      Number(selected.outstanding_amount ?? 0);

    setPaymentAmount(
      outstanding > 0
        ? outstanding.toFixed(2)
        : "",
    );

    setPaymentMethod("cash");
    setPaymentReference("");
    setPaymentNotes("");
    setPaymentError(null);
    setPaymentResult(null);
    setPaymentOpen(true);
  }

  function closePaymentForm() {
    if (paymentSubmitting) {
      return;
    }

    setPaymentOpen(false);
    setPaymentError(null);
  }

  async function submitInstallmentPayment(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (!selected || paymentSubmitting) {
      return;
    }

    const amount = Number(paymentAmount);
    const outstanding =
      Number(selected.outstanding_amount ?? 0);

    if (
      !Number.isFinite(amount)
      || amount <= 0
    ) {
      setPaymentError(
        "Enter a valid payment amount greater than zero.",
      );
      return;
    }

    if (
      Number.isFinite(outstanding)
      && amount > outstanding
    ) {
      setPaymentError(
        "Payment amount cannot exceed the outstanding balance.",
      );
      return;
    }

    setPaymentSubmitting(true);
    setPaymentError(null);

    try {
      const result =
        await receiveInstallmentPayment(
          selected.id,
          {
            amount,
            payment_method: paymentMethod,
            reference_number:
              paymentReference.trim() || null,
            notes:
              paymentNotes.trim() || null,
          },
        );

      setPaymentResult(result);

      const detail =
        await getInstallmentPlan(selected.id);

      setSelected(detail);

      const list =
        await getInstallmentPlans({
          page: 1,
          page_size: 100,
        });

      setPlans(
        Array.isArray(list.items)
          ? list.items
          : [],
      );
    } catch (requestError) {
      console.error(
        "Installment payment failed",
        requestError,
      );

      setPaymentError(
        requestError instanceof Error
          ? requestError.message
          : "Installment payment could not be recorded.",
      );
    } finally {
      setPaymentSubmitting(false);
    }
  }

  async function downloadReceipt() {
    if (!paymentResult || receiptLoading) {
      return;
    }

    setReceiptLoading(true);
    setPaymentError(null);

    try {
      await downloadPaymentReceipt(
        paymentResult.payment_id,
        paymentResult.receipt_number,
      );
    } catch (requestError) {
      console.error(
        "Receipt download failed",
        requestError,
      );

      setPaymentError(
        "Payment was recorded, but the receipt PDF could not be downloaded.",
      );
    } finally {
      setReceiptLoading(false);
    }
  }

  if (authLoading) {
    return (
      <main className="page-center">
        <LoaderCircle
          className={styles.spin}
          size={28}
        />
      </main>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <AppShell user={user}>
      <main className={styles.page}>
      <section className={styles.hero}>
        <div>
          <span className={styles.eyebrow}>
            FINANCE OPERATIONS
          </span>

          <h1>Installments</h1>

          <p>
            Monitor customer installment
            agreements, balances, upcoming
            dues and payment schedules.
          </p>
        </div>

        <button
          type="button"
          className={styles.refreshButton}
          disabled={loading}
          onClick={() => {
            void refreshPlans();
          }}
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </section>

      {error ? (
        <div
          className={styles.error}
          role="status"
        >
          {error}
        </div>
      ) : null}

      <section className={styles.metrics}>
        <article className={styles.metricCard}>
          <span className={styles.metricIcon}>
            <WalletCards size={20} />
          </span>
          <div>
            <small>Total financed</small>
            <strong>
              {money(metrics.financed)}
            </strong>
          </div>
        </article>

        <article className={styles.metricCard}>
          <span className={styles.metricIcon}>
            <CircleDollarSign size={20} />
          </span>
          <div>
            <small>Outstanding</small>
            <strong>
              {money(metrics.outstanding)}
            </strong>
          </div>
        </article>

        <article className={styles.metricCard}>
          <span className={styles.metricIcon}>
            <FileText size={20} />
          </span>
          <div>
            <small>Active plans</small>
            <strong>{metrics.active}</strong>
          </div>
        </article>

        <article className={styles.metricCard}>
          <span className={styles.metricIcon}>
            <CalendarDays size={20} />
          </span>
          <div>
            <small>Overdue plans</small>
            <strong>{metrics.overdue}</strong>
          </div>
        </article>
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <div>
            <span className={styles.eyebrow}>
              AGREEMENTS
            </span>
            <h2>Installment plans</h2>
          </div>

          <span className={styles.count}>
            {filteredPlans.length} records
          </span>
        </div>

        <div className={styles.filters}>
          <label className={styles.search}>
            <Search size={17} />
            <input
              value={search}
              placeholder={
                "Search agreement, customer or invoice"
              }
              onChange={(event) => {
                setSearch(event.target.value);
              }}
            />
          </label>

          <select
            className={styles.select}
            value={statusFilter}
            onChange={(event) => {
              setStatusFilter(
                event.target.value,
              );
            }}
          >
            <option value="all">
              All statuses
            </option>
            <option value="active">
              Active
            </option>
            <option value="completed">
              Completed
            </option>
            <option value="cancelled">
              Cancelled
            </option>
          </select>
        </div>

        {loading ? (
          <div className={styles.empty}>
            <LoaderCircle
              className={styles.spin}
              size={26}
            />
            Loading installment agreements...
          </div>
        ) : filteredPlans.length === 0 ? (
          <div className={styles.empty}>
            No installment agreements found.
          </div>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Agreement</th>
                  <th>Customer</th>
                  <th>Invoice</th>
                  <th>Financed</th>
                  <th>Paid</th>
                  <th>Outstanding</th>
                  <th>Next due</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>

              <tbody>
                {filteredPlans.map((plan) => (
                  <tr key={plan.id}>
                    <td>
                      <strong>
                        {plan.agreement_number}
                      </strong>
                    </td>

                    <td>
                      <strong>
                        {plan.customer_name}
                      </strong>
                      <small>
                        Customer #{plan.customer_id}
                      </small>
                    </td>

                    <td>
                      {plan.invoice_number}
                    </td>

                    <td>
                      {money(
                        plan.financed_amount,
                      )}
                    </td>

                    <td>
                      {money(plan.total_paid)}
                    </td>

                    <td>
                      <strong>
                        {money(
                          plan.outstanding_amount,
                        )}
                      </strong>
                    </td>

                    <td>
                      <span>
                        {shortDate(
                          plan.next_due_date,
                        )}
                      </span>

                      {plan.next_due_amount
                        !== null
                        && plan.next_due_amount
                        !== undefined ? (
                          <small>
                            {money(
                              plan.next_due_amount,
                            )}
                          </small>
                        ) : null}
                    </td>

                    <td>
                      <span
                        className={styles.status}
                        data-status={plan.status}
                      >
                        {prettyStatus(
                          plan.status,
                        )}
                      </span>
                    </td>

                    <td>
                      <button
                        type="button"
                        title="View agreement"
                        className={
                          styles.openButton
                        }
                        onClick={() => {
                          void openPlan(plan);
                        }}
                      >
                        <ChevronRight
                          size={18}
                        />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selected ? (
        <div className={styles.overlay}>
          <aside className={styles.drawer}>
            <header
              className={styles.drawerHeader}
            >
              <div>
                <span
                  className={styles.eyebrow}
                >
                  INSTALLMENT AGREEMENT
                </span>

                <h2>
                  {selected.agreement_number}
                </h2>

                <p>
                  {selected.customer_name}
                  {" · "}
                  {selected.invoice_number}
                </p>
              </div>

              <button
                type="button"
                title="Close"
                className={
                  styles.closeButton
                }
                onClick={() => {
                  setSelected(null);
                }}
              >
                <X size={19} />
              </button>
            </header>

            {detailLoading ? (
              <div className={styles.empty}>
                <LoaderCircle
                  className={styles.spin}
                  size={26}
                />
                Loading agreement...
              </div>
            ) : (
              <>
                <section
                  className={
                    styles.drawerMetrics
                  }
                >
                  <div>
                    <small>Financed</small>
                    <strong>
                      {money(
                        selected.financed_amount,
                      )}
                    </strong>
                  </div>

                  <div>
                    <small>Total paid</small>
                    <strong>
                      {money(
                        selected.total_paid,
                      )}
                    </strong>
                  </div>

                  <div>
                    <small>Outstanding</small>
                    <strong>
                      {money(
                        selected
                          .outstanding_amount,
                      )}
                    </strong>
                  </div>
                </section>

                <section
                  className={styles.details}
                >
                  <div>
                    <small>Status</small>
                    <strong>
                      {prettyStatus(
                        selected.status,
                      )}
                    </strong>
                  </div>

                  <div>
                    <small>Frequency</small>
                    <strong>
                      {prettyStatus(
                        selected.frequency,
                      )}
                    </strong>
                  </div>

                  <div>
                    <small>Installments</small>
                    <strong>
                      {
                        selected
                          .installment_count
                      }
                    </strong>
                  </div>

                  <div>
                    <small>First due</small>
                    <strong>
                      {shortDate(
                        selected
                          .first_due_date,
                      )}
                    </strong>
                  </div>

                  <div>
                    <small>
                      Scheduled amount
                    </small>
                    <strong>
                      {money(
                        selected
                          .scheduled_installment_amount,
                      )}
                    </strong>
                  </div>

                  <div>
                    <small>Next due</small>
                    <strong>
                      {shortDate(
                        selected.next_due_date,
                      )}
                    </strong>
                  </div>
                </section>

                <section
                  className={
                    styles.scheduleSection
                  }
                >
                  <div
                    className={
                      styles.scheduleHeader
                    }
                  >
                    <div>
                      <span
                        className={
                          styles.eyebrow
                        }
                      >
                        SCHEDULE
                      </span>
                      <h3>
                        Payment schedule
                      </h3>
                    </div>

                    <span
                      className={styles.count}
                    >
                      {
                        selected.schedules
                          ?.length ?? 0
                      }{" "}
                      installments
                    </span>
                  </div>

                  {!selected.schedules
                    ?.length ? (
                      <div
                        className={styles.empty}
                      >
                        No schedule rows available.
                      </div>
                    ) : (
                      <div
                        className={
                          styles.scheduleList
                        }
                      >
                        {selected.schedules.map(
                          (schedule, index) => {
                            const extended =
                              schedule as typeof schedule & {
                                amount_due?:
                                  number | string;
                                amount_paid?:
                                  number | string;
                              };

                            const amount =
                              schedule.amount
                              ?? extended.amount_due
                              ?? 0;

                            const paid =
                              schedule.paid_amount
                              ?? extended.amount_paid
                              ?? 0;

                            return (
                              <article
                                key={
                                  schedule.id
                                  ?? index
                                }
                                className={
                                  styles
                                    .scheduleRow
                                }
                              >
                                <span
                                  className={
                                    styles
                                      .scheduleNumber
                                  }
                                >
                                  #
                                  {
                                    schedule
                                      .installment_number
                                    ?? index + 1
                                  }
                                </span>

                                <div>
                                  <small>
                                    Due date
                                  </small>
                                  <strong>
                                    {shortDate(
                                      schedule
                                        .due_date,
                                    )}
                                  </strong>
                                </div>

                                <div>
                                  <small>
                                    Amount
                                  </small>
                                  <strong>
                                    {money(amount)}
                                  </strong>
                                </div>

                                <div>
                                  <small>
                                    Paid
                                  </small>
                                  <strong>
                                    {money(paid)}
                                  </strong>
                                </div>

                                <span
                                  className={
                                    styles.status
                                  }
                                  data-status={
                                    schedule.status
                                  }
                                >
                                  {prettyStatus(
                                    schedule.status,
                                  )}
                                </span>
                              </article>
                            );
                          },
                        )}
                      </div>
                    )}
                </section>

                <section
                  className={
                    styles.paymentSection
                  }
                >
                  <div
                    className={
                      styles.paymentSectionText
                    }
                  >
                    <span
                      className={styles.eyebrow}
                    >
                      PAYMENT
                    </span>

                    <h3>
                      Receive installment payment
                    </h3>

                    <p>
                      Record a customer payment
                      against this agreement.
                      Payments are automatically
                      allocated to the oldest
                      unpaid installment first.
                    </p>
                  </div>

                  {selected.status === "active"
                  && Number(
                    selected.outstanding_amount
                      ?? 0,
                  ) > 0 ? (
                    <button
                      type="button"
                      className={
                        styles.receivePaymentButton
                      }
                      onClick={openPaymentForm}
                    >
                      <CircleDollarSign
                        size={17}
                      />
                      Receive Payment
                    </button>
                  ) : (
                    <div
                      className={
                        styles.paymentComplete
                      }
                    >
                      <CheckCircle2 size={17} />
                      Agreement fully settled
                    </div>
                  )}
                </section>

                <div
                  className={
                    styles.readOnlyNotice
                  }
                >
                  Payment receiving is enabled.
                  Cancellation and reversal remain
                  protected until their dedicated
                  transaction workflow is enabled.
                </div>
              </>
            )}
            {paymentOpen ? (
              <div
                className={
                  styles.paymentModalBackdrop
                }
                onMouseDown={(event) => {
                  if (
                    event.target
                    === event.currentTarget
                  ) {
                    closePaymentForm();
                  }
                }}
              >
                <div
                  className={
                    styles.paymentModal
                  }
                  role="dialog"
                  aria-modal="true"
                  aria-label={
                    "Receive installment payment"
                  }
                >
                  <header
                    className={
                      styles.paymentModalHeader
                    }
                  >
                    <div>
                      <span
                        className={
                          styles.eyebrow
                        }
                      >
                        RECEIVE PAYMENT
                      </span>

                      <h3>
                        {
                          selected
                            .agreement_number
                        }
                      </h3>

                      <p>
                        {selected.customer_name}
                        {" · "}
                        Outstanding{" "}
                        {money(
                          selected
                            .outstanding_amount,
                        )}
                      </p>
                    </div>

                    <button
                      type="button"
                      className={
                        styles.closeButton
                      }
                      disabled={
                        paymentSubmitting
                      }
                      onClick={
                        closePaymentForm
                      }
                    >
                      <X size={18} />
                    </button>
                  </header>

                  {paymentResult ? (
                    <div
                      className={
                        styles.paymentSuccess
                      }
                    >
                      <span
                        className={
                          styles.successIcon
                        }
                      >
                        <CheckCircle2
                          size={30}
                        />
                      </span>

                      <h4>
                        Payment recorded
                      </h4>

                      <strong>
                        {
                          paymentResult
                            .receipt_number
                        }
                      </strong>

                      <div
                        className={
                          styles.successGrid
                        }
                      >
                        <div>
                          <small>
                            Amount
                          </small>
                          <b>
                            {money(
                              paymentResult
                                .amount,
                            )}
                          </b>
                        </div>

                        <div>
                          <small>
                            Remaining
                          </small>
                          <b>
                            {money(
                              paymentResult
                                .plan_outstanding_amount,
                            )}
                          </b>
                        </div>

                        <div>
                          <small>
                            Invoice balance
                          </small>
                          <b>
                            {money(
                              paymentResult
                                .invoice_balance_amount,
                            )}
                          </b>
                        </div>

                        <div>
                          <small>
                            Customer balance
                          </small>
                          <b>
                            {money(
                              paymentResult
                                .customer_balance,
                            )}
                          </b>
                        </div>
                      </div>

                      {paymentError ? (
                        <div
                          className={
                            styles.paymentError
                          }
                        >
                          {paymentError}
                        </div>
                      ) : null}

                      <div
                        className={
                          styles.paymentActions
                        }
                      >
                        <button
                          type="button"
                          className={
                            styles.receiptButton
                          }
                          disabled={
                            receiptLoading
                          }
                          onClick={() => {
                            void downloadReceipt();
                          }}
                        >
                          {receiptLoading ? (
                            <LoaderCircle
                              className={
                                styles.spin
                              }
                              size={17}
                            />
                          ) : (
                            <Download
                              size={17}
                            />
                          )}
                          Receipt PDF
                        </button>

                        <button
                          type="button"
                          className={
                            styles.printHintButton
                          }
                          onClick={() => {
                            void downloadReceipt();
                          }}
                          disabled={
                            receiptLoading
                          }
                        >
                          <Printer size={17} />
                          Print Receipt
                        </button>

                        <button
                          type="button"
                          className={
                            styles.doneButton
                          }
                          onClick={() => {
                            setPaymentOpen(false);
                            setPaymentResult(null);
                          }}
                        >
                          Done
                        </button>
                      </div>
                    </div>
                  ) : (
                    <form
                      className={
                        styles.paymentForm
                      }
                      onSubmit={
                        submitInstallmentPayment
                      }
                    >
                      <label>
                        <span>
                          Payment amount
                        </span>

                        <input
                          type="number"
                          min="0.01"
                          step="0.01"
                          max={String(
                            selected
                              .outstanding_amount,
                          )}
                          required
                          value={
                            paymentAmount
                          }
                          onChange={(event) =>
                            setPaymentAmount(
                              event.target.value,
                            )
                          }
                        />

                        <small>
                          Maximum{" "}
                          {money(
                            selected
                              .outstanding_amount,
                          )}
                        </small>
                      </label>

                      <label>
                        <span>
                          Payment method
                        </span>

                        <select
                          value={
                            paymentMethod
                          }
                          onChange={(event) =>
                            setPaymentMethod(
                              (
                                event.target.value
                              ) as InstallmentPaymentMethod,
                            )
                          }
                        >
                          <option value="cash">
                            Cash
                          </option>
                          <option value="card">
                            Card
                          </option>
                          <option
                            value="bank_transfer"
                          >
                            Bank transfer
                          </option>
                          <option value="cheque">
                            Cheque
                          </option>
                          <option value="other">
                            Other
                          </option>
                        </select>
                      </label>

                      <label>
                        <span>
                          Reference number
                        </span>

                        <input
                          type="text"
                          maxLength={150}
                          placeholder={
                            "Optional reference"
                          }
                          value={
                            paymentReference
                          }
                          onChange={(event) =>
                            setPaymentReference(
                              event.target.value,
                            )
                          }
                        />
                      </label>

                      <label>
                        <span>
                          Notes
                        </span>

                        <textarea
                          rows={3}
                          placeholder={
                            "Optional payment notes"
                          }
                          value={
                            paymentNotes
                          }
                          onChange={(event) =>
                            setPaymentNotes(
                              event.target.value,
                            )
                          }
                        />
                      </label>

                      {paymentError ? (
                        <div
                          className={
                            styles.paymentError
                          }
                        >
                          {paymentError}
                        </div>
                      ) : null}

                      <div
                        className={
                          styles.paymentActions
                        }
                      >
                        <button
                          type="button"
                          className={
                            styles.cancelButton
                          }
                          disabled={
                            paymentSubmitting
                          }
                          onClick={
                            closePaymentForm
                          }
                        >
                          Cancel
                        </button>

                        <button
                          type="submit"
                          className={
                            styles.confirmPaymentButton
                          }
                          disabled={
                            paymentSubmitting
                          }
                        >
                          {paymentSubmitting ? (
                            <LoaderCircle
                              className={
                                styles.spin
                              }
                              size={17}
                            />
                          ) : (
                            <CircleDollarSign
                              size={17}
                            />
                          )}

                          {paymentSubmitting
                            ? "Recording..."
                            : "Confirm Payment"}
                        </button>
                      </div>
                    </form>
                  )}
                </div>
              </div>
            ) : null}
          </aside>
        </div>
      ) : null}
    </main>
    </AppShell>
  );
}
