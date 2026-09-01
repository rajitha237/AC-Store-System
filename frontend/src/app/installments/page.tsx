"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { FormEvent } from "react";

import { useRouter } from "next/navigation";

import {
  ArchiveRestore,
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
  createLegacyInstallmentPlan,
  getInstallmentPlan,
  getInstallmentPlans,
  receiveInstallmentPayment,
} from "@/lib/installment-api";
import { getCustomers } from "@/lib/customer-api";

import {
  downloadPaymentReceipt,
} from "@/lib/payments-api";

import type {
  InstallmentPaymentMethod,
  InstallmentPaymentResponse,
  InstallmentPlan,
} from "@/types/installment";
import type { Customer } from "@/types/customer";

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

  const [legacyOpen, setLegacyOpen] =
    useState(false);
  const [legacyCustomerQuery, setLegacyCustomerQuery] =
    useState("");
  const [legacyCustomers, setLegacyCustomers] =
    useState<Customer[]>([]);
  const [legacyCustomerLoading, setLegacyCustomerLoading] =
    useState(false);
  const [legacySelectedCustomer, setLegacySelectedCustomer] =
    useState<Customer | null>(null);
  const [legacyPrincipal, setLegacyPrincipal] =
    useState("");
  const [legacyFirstDueDate, setLegacyFirstDueDate] =
    useState("");
  const [legacyNotes, setLegacyNotes] =
    useState("");
  const [legacySubmitting, setLegacySubmitting] =
    useState(false);
  const [legacyError, setLegacyError] =
    useState<string | null>(null);
  const [legacyCreated, setLegacyCreated] =
    useState<InstallmentPlan | null>(null);

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

  function openLegacyForm() {
    setLegacyOpen(true);
    setLegacyCustomerQuery("");
    setLegacyCustomers([]);
    setLegacySelectedCustomer(null);
    setLegacyPrincipal("");
    setLegacyFirstDueDate("");
    setLegacyNotes("");
    setLegacyError(null);
    setLegacyCreated(null);
  }

  function closeLegacyForm() {
    if (legacySubmitting) {
      return;
    }

    setLegacyOpen(false);
    setLegacyError(null);
    setLegacyCreated(null);
  }

  async function searchLegacyCustomers() {
    const query =
      legacyCustomerQuery.trim();

    if (query.length < 2) {
      setLegacyError(
        "Enter at least 2 characters to search customers.",
      );
      return;
    }

    setLegacyCustomerLoading(true);
    setLegacyError(null);

    try {
      const result = await getCustomers({
        page: 1,
        pageSize: 12,
        search: query,
        customerStatus: "active",
      });

      setLegacyCustomers(
        result.items,
      );

      if (result.items.length === 0) {
        setLegacyError(
          "No active customers matched this search.",
        );
      }
    } catch (error) {
      setLegacyError(
        error instanceof Error
          ? error.message
          : "Unable to search customers.",
      );
    } finally {
      setLegacyCustomerLoading(false);
    }
  }

  function addMonthsToDate(
    isoDate: string,
    months: number,
  ): string {
    const parts = isoDate
      .split("-")
      .map(Number);

    if (
      parts.length !== 3
      || parts.some(
        (part) => !Number.isFinite(part),
      )
    ) {
      return isoDate;
    }

    const [year, month, day] = parts;

    const target = new Date(
      year,
      month - 1 + months,
      1,
    );

    const lastDay = new Date(
      target.getFullYear(),
      target.getMonth() + 1,
      0,
    ).getDate();

    target.setDate(
      Math.min(day, lastDay),
    );

    const y = target.getFullYear();
    const m = String(
      target.getMonth() + 1,
    ).padStart(2, "0");
    const d = String(
      target.getDate(),
    ).padStart(2, "0");

    return `${y}-${m}-${d}`;
  }

  function legacySchedulePreview() {
    const principal =
      Number(legacyPrincipal);

    if (
      !Number.isFinite(principal)
      || principal <= 0
      || !legacyFirstDueDate
    ) {
      return [];
    }

    const base =
      Math.round(
        (principal / 6) * 100,
      ) / 100;

    let allocated = 0;

    return Array.from(
      { length: 6 },
      (_, index) => {
        const amount =
          index === 5
            ? Math.round(
                (
                  principal
                  - allocated
                ) * 100,
              ) / 100
            : base;

        allocated =
          Math.round(
            (
              allocated
              + amount
            ) * 100,
          ) / 100;

        return {
          number: index + 1,
          dueDate: addMonthsToDate(
            legacyFirstDueDate,
            index,
          ),
          amount,
        };
      },
    );
  }

  const legacyExistingBalance =
    legacySelectedCustomer
      ? Number(
          legacySelectedCustomer
            .current_balance
          ?? 0,
        )
      : 0;

  const legacyUsesExistingBalance =
    Number.isFinite(
      legacyExistingBalance,
    )
    && legacyExistingBalance > 0;

  const legacyBalanceMode =
    legacyUsesExistingBalance
      ? "use_existing_balance"
      : "register_new_debt";

  async function submitLegacyPlan(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (!legacySelectedCustomer) {
      setLegacyError(
        "Select the customer first.",
      );
      return;
    }

    const principal =
      Number(legacyPrincipal);

    if (
      !Number.isFinite(principal)
      || principal <= 0
    ) {
      setLegacyError(
        "Enter a valid old outstanding balance.",
      );
      return;
    }

    if (!legacyFirstDueDate) {
      setLegacyError(
        "Select the first due date.",
      );
      return;
    }

    if (
      legacyUsesExistingBalance
      && Math.abs(
        principal
        - legacyExistingBalance
      ) > 0.001
    ) {
      setLegacyError(
        "Old outstanding balance must "
        + "match the customer's existing "
        + "system balance.",
      );
      return;
    }

    setLegacySubmitting(true);
    setLegacyError(null);

    try {
      const created =
        await createLegacyInstallmentPlan({
          customer_id:
            legacySelectedCustomer.id,
          principal_amount:
            principal,
          first_due_date:
            legacyFirstDueDate,
          balance_mode:
            legacyBalanceMode,
          notes:
            legacyNotes.trim()
              || null,
        });

      setLegacyCreated(created);

      await refreshPlans();
    } catch (error) {
      setLegacyError(
        error instanceof Error
          ? error.message
          : "Unable to create legacy installment plan.",
      );
    } finally {
      setLegacySubmitting(false);
    }
  }

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
              className={
                styles.legacyCreateButton
              }
              onClick={openLegacyForm}
            >
              <ArchiveRestore size={17} />
              Add Legacy Debtor
            </button>

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

      {legacyOpen ? (
        <div
          className={
            styles.legacyModalBackdrop
          }
          onMouseDown={(event) => {
            if (
              event.target
              === event.currentTarget
            ) {
              closeLegacyForm();
            }
          }}
        >
          <div
            className={
              styles.legacyModal
            }
            role="dialog"
            aria-modal="true"
            aria-label={
              "Add legacy debtor"
            }
          >
            <header
              className={
                styles.legacyModalHeader
              }
            >
              <div>
                <span
                  className={
                    styles.eyebrow
                  }
                >
                  LEGACY DEBT ENTRY
                </span>

                <h3>
                  Add Legacy Debtor
                </h3>

                <p>
                  Convert an old customer
                  balance into a controlled
                  six-month installment plan.
                </p>
              </div>

              <button
                type="button"
                className={
                  styles.closeButton
                }
                disabled={
                  legacySubmitting
                }
                onClick={
                  closeLegacyForm
                }
              >
                <X size={18} />
              </button>
            </header>

            {legacyCreated ? (
              <div
                className={
                  styles.legacySuccess
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
                  Legacy plan created
                </h4>

                <strong>
                  {
                    legacyCreated
                      .agreement_number
                  }
                </strong>

                <p>
                  {
                    legacyCreated
                      .customer_name
                  }
                  {" · "}
                  {money(
                    legacyCreated
                      .financed_amount,
                  )}
                </p>

                <div
                  className={
                    styles.legacySuccessGrid
                  }
                >
                  <div>
                    <small>
                      Installments
                    </small>
                    <b>6 monthly</b>
                  </div>

                  <div>
                    <small>
                      Interest
                    </small>
                    <b>0%</b>
                  </div>

                  <div>
                    <small>
                      First due
                    </small>
                    <b>
                      {
                        legacyCreated
                          .first_due_date
                      }
                    </b>
                  </div>

                  <div>
                    <small>
                      Outstanding
                    </small>
                    <b>
                      {money(
                        legacyCreated
                          .outstanding_amount,
                      )}
                    </b>
                  </div>
                </div>

                <button
                  type="button"
                  className={
                    styles.legacyDoneButton
                  }
                  onClick={() => {
                    setLegacyOpen(false);
                    setLegacyCreated(null);
                  }}
                >
                  Done
                </button>
              </div>
            ) : (
              <form
                className={
                  styles.legacyForm
                }
                onSubmit={
                  submitLegacyPlan
                }
              >
                <section
                  className={
                    styles.legacySection
                  }
                >
                  <div
                    className={
                      styles.legacySectionTitle
                    }
                  >
                    <Search size={17} />

                    <div>
                      <strong>
                        Customer
                      </strong>
                      <small>
                        Search by name,
                        phone, NIC or
                        customer number.
                      </small>
                    </div>
                  </div>

                  <div
                    className={
                      styles.legacySearchRow
                    }
                  >
                    <input
                      type="search"
                      placeholder={
                        "Search existing customer..."
                      }
                      value={
                        legacyCustomerQuery
                      }
                      onChange={(event) =>
                        setLegacyCustomerQuery(
                          event.target.value,
                        )
                      }
                      onKeyDown={(event) => {
                        if (
                          event.key
                          === "Enter"
                        ) {
                          event.preventDefault();
                          void searchLegacyCustomers();
                        }
                      }}
                    />

                    <button
                      type="button"
                      disabled={
                        legacyCustomerLoading
                      }
                      onClick={() => {
                        void searchLegacyCustomers();
                      }}
                    >
                      {legacyCustomerLoading ? (
                        <LoaderCircle
                          className={
                            styles.spin
                          }
                          size={16}
                        />
                      ) : (
                        <Search
                          size={16}
                        />
                      )}
                      Search
                    </button>
                  </div>

                  {legacyCustomers.length
                  > 0 ? (
                    <div
                      className={
                        styles.legacyCustomerResults
                      }
                    >
                      {legacyCustomers.map(
                        (customer) => {
                          const selectedCustomer =
                            legacySelectedCustomer
                              ?.id
                            === customer.id;

                          return (
                            <button
                              key={
                                customer.id
                              }
                              type="button"
                              className={
                                selectedCustomer
                                  ? styles
                                      .legacyCustomerSelected
                                  : styles
                                      .legacyCustomerOption
                              }
                              onClick={() => {
                                setLegacySelectedCustomer(
                                  customer,
                                );

                                const existingBalance =
                                  Number(
                                    customer
                                      .current_balance
                                    ?? 0,
                                  );

                                if (
                                  Number.isFinite(
                                    existingBalance,
                                  )
                                  && existingBalance > 0
                                ) {
                                  setLegacyPrincipal(
                                    existingBalance
                                      .toFixed(2),
                                  );
                                } else {
                                  setLegacyPrincipal(
                                    "",
                                  );
                                }

                                setLegacyError(
                                  null,
                                );
                              }}
                            >
                              <span>
                                <strong>
                                  {
                                    customer
                                      .full_name
                                  }
                                </strong>

                                <small>
                                  {
                                    customer
                                      .customer_number
                                  }
                                  {" · "}
                                  {
                                    customer
                                      .primary_phone
                                  }
                                </small>
                              </span>

                              <b>
                                Balance{" "}
                                {money(
                                  customer
                                    .current_balance,
                                )}
                              </b>
                            </button>
                          );
                        },
                      )}
                    </div>
                  ) : null}

                  {legacySelectedCustomer ? (
                    <div
                      className={
                        styles.legacySelectedCard
                      }
                    >
                      <div>
                        <small>
                          SELECTED CUSTOMER
                        </small>
                        <strong>
                          {
                            legacySelectedCustomer
                              .full_name
                          }
                        </strong>
                        <span>
                          {
                            legacySelectedCustomer
                              .customer_number
                          }
                          {" · "}
                          {
                            legacySelectedCustomer
                              .primary_phone
                          }
                        </span>
                      </div>

                      <b>
                        {money(
                          legacySelectedCustomer
                            .current_balance,
                        )}
                      </b>
                    </div>
                  ) : null}

                  {legacySelectedCustomer
                    && Number(
                      legacySelectedCustomer
                        .current_balance,
                    ) > 0 ? (
                    <div
                      className={
                        styles.legacyBalanceWarning
                      }
                    >
                      <strong>
                        Existing customer
                        balance detected
                      </strong>

                      <span>
                        This customer already
                        has{" "}
                        {money(
                          legacySelectedCustomer
                            .current_balance,
                        )}
                        {" "}
                        in the system. This
                        amount will be converted
                        into the six-installment
                        legacy plan without
                        adding the debt to the
                        customer balance again.
                      </span>
                    </div>
                  ) : null}
                </section>

                <section
                  className={
                    styles.legacySection
                  }
                >
                  <div
                    className={
                      styles.legacySectionTitle
                    }
                  >
                    <CalendarDays
                      size={17}
                    />

                    <div>
                      <strong>
                        Plan details
                      </strong>
                      <small>
                        Fixed at 6 monthly
                        installments with
                        0% interest.
                      </small>
                    </div>
                  </div>

                  <div
                    className={
                      styles.legacyFieldGrid
                    }
                  >
                    <label>
                      <span>
                        Old outstanding
                        balance
                      </span>

                      <input
                        type="number"
                        min="0.01"
                        step="0.01"
                        required
                        placeholder="0.00"
                        value={
                          legacyPrincipal
                        }
                        onChange={(event) =>
                          setLegacyPrincipal(
                            event.target
                              .value,
                          )
                        }
                        readOnly={
                          legacyUsesExistingBalance
                        }
                      />
                    </label>

                    <label>
                      <span>
                        First due date
                      </span>

                      <input
                        type="date"
                        required
                        value={
                          legacyFirstDueDate
                        }
                        onChange={(event) =>
                          setLegacyFirstDueDate(
                            event.target
                              .value,
                          )
                        }
                      />
                    </label>
                  </div>

                  <div
                    className={
                      styles.legacyFixedRules
                    }
                  >
                    <div>
                      <small>
                        INSTALLMENTS
                      </small>
                      <strong>6</strong>
                    </div>

                    <div>
                      <small>
                        FREQUENCY
                      </small>
                      <strong>
                        Monthly
                      </strong>
                    </div>

                    <div>
                      <small>
                        INTEREST
                      </small>
                      <strong>0%</strong>
                    </div>
                  </div>

                  <label
                    className={
                      styles.legacyNotes
                    }
                  >
                    <span>
                      Notes
                    </span>

                    <textarea
                      rows={3}
                      maxLength={1000}
                      placeholder={
                        "Optional note about this old debt"
                      }
                      value={
                        legacyNotes
                      }
                      onChange={(event) =>
                        setLegacyNotes(
                          event.target.value,
                        )
                      }
                    />
                  </label>
                </section>

                {legacySchedulePreview()
                  .length > 0 ? (
                  <section
                    className={
                      styles.legacyPreview
                    }
                  >
                    <div
                      className={
                        styles.legacyPreviewHeader
                      }
                    >
                      <div>
                        <strong>
                          6-month preview
                        </strong>
                        <small>
                          Final installment
                          automatically absorbs
                          rounding.
                        </small>
                      </div>

                      <b>
                        {money(
                          Number(
                            legacyPrincipal,
                          ),
                        )}
                      </b>
                    </div>

                    <div
                      className={
                        styles.legacyPreviewRows
                      }
                    >
                      {legacySchedulePreview().map(
                        (item) => (
                          <div
                            key={
                              item.number
                            }
                          >
                            <span>
                              <b>
                                {
                                  item.number
                                }
                              </b>
                              <small>
                                {
                                  item.dueDate
                                }
                              </small>
                            </span>

                            <strong>
                              {money(
                                item.amount,
                              )}
                            </strong>
                          </div>
                        ),
                      )}
                    </div>
                  </section>
                ) : null}

                {legacyError ? (
                  <div
                    className={
                      styles.paymentError
                    }
                  >
                    {legacyError}
                  </div>
                ) : null}

                <div
                  className={
                    styles.legacyActions
                  }
                >
                  <button
                    type="button"
                    className={
                      styles.cancelButton
                    }
                    disabled={
                      legacySubmitting
                    }
                    onClick={
                      closeLegacyForm
                    }
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    className={
                      styles.legacySubmitButton
                    }
                    disabled={
                      legacySubmitting
                      || !legacySelectedCustomer
                      || !legacyPrincipal
                      || !legacyFirstDueDate
                    }
                  >
                    {legacySubmitting ? (
                      <LoaderCircle
                        className={
                          styles.spin
                        }
                        size={17}
                      />
                    ) : (
                      <ArchiveRestore
                        size={17}
                      />
                    )}

                    {legacySubmitting
                      ? "Creating..."
                      : "Create 6 Installments"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      ) : null}
    </main>
    </AppShell>
  );
}
