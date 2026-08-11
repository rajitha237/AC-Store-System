"use client";

import {
  Banknote,
  Download,
  Eye,
  FileText,
  Loader2,
  RefreshCw,
  RotateCcw,
  Search,
  WalletCards,
  X,
} from "lucide-react";

import {
  FormEvent,
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

import { AppShell } from "@/components/app-shell";

import {
  clearAuthSession,
  getAccessToken,
  getStoredUser,
} from "@/lib/auth";

import type {
  UserResponse,
} from "@/types/auth";

import {
  downloadPaymentReceipt,
  downloadSalesInvoice,
  getPayment,
  getPayments,
  receivePayment,
  reversePayment,
} from "@/lib/payments-api";

import type {
  PaymentDetailResponse,
  PaymentMethod,
  PaymentResponse,
} from "@/types/payments";

import styles from "./payments.module.css";

function money(value: string | number) {
  const amount = Number(value || 0);

  return new Intl.NumberFormat(
    "en-LK",
    {
      style: "currency",
      currency: "LKR",
      minimumFractionDigits: 2,
    },
  ).format(amount);
}

function dateTime(value?: string | null) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(
    "en-LK",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(date);
}

function readable(value?: string | null) {
  if (!value) {
    return "—";
  }

  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) =>
      char.toUpperCase(),
    );
}

function errorText(error: unknown) {
  if (
    typeof error === "object"
    && error !== null
    && "response" in error
  ) {
    const response = (
      error as {
        response?: {
          data?: {
            detail?:
              | string
              | Array<{
                  msg?: string;
                }>;
          };
        };
      }
    ).response;

    const detail =
      response?.data?.detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (
      Array.isArray(detail)
      && detail[0]?.msg
    ) {
      return detail[0].msg;
    }
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Something went wrong.";
}

export default function PaymentsPage() {
  const router =
    useRouter();

  const [
    user,
    setUser,
  ] =
    useState<UserResponse | null>(
      null,
    );

  const [
    authLoading,
    setAuthLoading,
  ] =
    useState(true);

  const [items, setItems] =
    useState<PaymentResponse[]>([]);

  const [total, setTotal] =
    useState(0);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [search, setSearch] =
    useState("");

  const [method, setMethod] =
    useState("");

  const [status, setStatus] =
    useState("");

  const [page, setPage] =
    useState(1);

  const pageSize = 25;

  const [
    selected,
    setSelected,
  ] =
    useState<PaymentDetailResponse | null>(
      null,
    );

  const [
    detailLoading,
    setDetailLoading,
  ] = useState(false);

  const [
    receiveOpen,
    setReceiveOpen,
  ] = useState(false);

  const [
    reverseOpen,
    setReverseOpen,
  ] = useState(false);

  const [
    actionLoading,
    setActionLoading,
  ] = useState(false);

  const [
    invoiceId,
    setInvoiceId,
  ] = useState("");

  const [
    amount,
    setAmount,
  ] = useState("");

  const [
    paymentMethod,
    setPaymentMethod,
  ] =
    useState<PaymentMethod>("cash");

  const [
    reference,
    setReference,
  ] = useState("");

  const [
    notes,
    setNotes,
  ] = useState("");

  const [
    reversalReason,
    setReversalReason,
  ] = useState("");

  const [
    reversalNotes,
    setReversalNotes,
  ] = useState("");

  useEffect(() => {
    const timer =
      window.setTimeout(
        () => {
          const token =
            getAccessToken();

          const storedUser =
            getStoredUser();

          if (
            !token
            || !storedUser
          ) {
            clearAuthSession();

            router.replace(
              "/login",
            );

            return;
          }

          setUser(
            storedUser,
          );

          setAuthLoading(
            false,
          );
        },
        0,
      );

    return () => {
      window.clearTimeout(
        timer,
      );
    };
  }, [router]);


  const loadPayments =
    useCallback(async () => {
      setLoading(true);
      setError("");

      try {
        const result =
          await getPayments({
            page,
            pageSize,
            search:
              search.trim()
              || undefined,
            paymentMethod:
              method || undefined,
            status:
              status || undefined,
          });

        setItems(result.items || []);
        setTotal(result.total || 0);
      } catch (requestError) {
        setError(
          errorText(requestError),
        );
      } finally {
        setLoading(false);
      }
    }, [
      page,
      search,
      method,
      status,
    ]);

  useEffect(() => {
    if (authLoading) {
      return;
    }

    const timer =
      window.setTimeout(() => {
        void loadPayments();
      }, 250);

    return () => {
      window.clearTimeout(timer);
    };
  }, [
    authLoading,
    loadPayments,
  ]);

  async function openDetail(
    paymentId: number,
  ) {
    setDetailLoading(true);
    setError("");

    try {
      const detail =
        await getPayment(paymentId);

      setSelected(detail);
    } catch (requestError) {
      setError(
        errorText(requestError),
      );
    } finally {
      setDetailLoading(false);
    }
  }

  async function submitPayment(
    event: FormEvent,
  ) {
    event.preventDefault();

    const parsedInvoiceId =
      Number(invoiceId);

    const parsedAmount =
      Number(amount);

    if (
      !Number.isInteger(
        parsedInvoiceId,
      )
      || parsedInvoiceId <= 0
    ) {
      setError(
        "Enter a valid invoice ID.",
      );
      return;
    }

    if (
      !Number.isFinite(parsedAmount)
      || parsedAmount <= 0
    ) {
      setError(
        "Payment amount must be greater than zero.",
      );
      return;
    }

    setActionLoading(true);
    setError("");

    try {
      const result =
        await receivePayment({
          invoice_id:
            parsedInvoiceId,
          amount:
            parsedAmount.toFixed(2),
          payment_method:
            paymentMethod,
          reference_number:
            reference.trim()
            || null,
          notes:
            notes.trim()
            || null,
        });

      setReceiveOpen(false);

      setInvoiceId("");
      setAmount("");
      setReference("");
      setNotes("");

      setSelected(result);

      await loadPayments();
    } catch (requestError) {
      setError(
        errorText(requestError),
      );
    } finally {
      setActionLoading(false);
    }
  }

  async function submitReversal(
    event: FormEvent,
  ) {
    event.preventDefault();

    if (!selected) {
      return;
    }

    if (
      reversalReason.trim().length < 3
    ) {
      setError(
        "Enter a reversal reason.",
      );
      return;
    }

    setActionLoading(true);
    setError("");

    try {
      const result =
        await reversePayment(
          selected.id,
          {
            reason:
              reversalReason.trim(),
            notes:
              reversalNotes.trim()
              || null,
          },
        );

      setSelected(result);
      setReverseOpen(false);
      setReversalReason("");
      setReversalNotes("");

      await loadPayments();
    } catch (requestError) {
      setError(
        errorText(requestError),
      );
    } finally {
      setActionLoading(false);
    }
  }

  const pages = Math.max(
    1,
    Math.ceil(total / pageSize),
  );

  if (
    authLoading
    || !user
  ) {
    return (
      <main className="page-center">
        <div className="loading-spinner" />
      </main>
    );
  }

  return (
    <AppShell user={user}>
      <main className={styles.page}>
        <section
          className={styles.header}
        >
          <div>
            <div
              className={
                styles.eyebrow
              }
            >
              SALES
            </div>

            <h1>Payments</h1>

            <p>
              Receive invoice payments,
              review receipts, reverse
              incorrect transactions and
              print financial documents.
            </p>
          </div>

          <div
            className={
              styles.headerActions
            }
          >
            <button
              className={
                styles.secondaryButton
              }
              onClick={() =>
                void loadPayments()
              }
              type="button"
            >
              <RefreshCw size={17} />
              Refresh
            </button>

            <button
              className={
                styles.primaryButton
              }
              onClick={() => {
                setError("");
                setReceiveOpen(true);
              }}
              type="button"
            >
              <Banknote size={18} />
              Receive payment
            </button>
          </div>
        </section>

        {error && (
          <div
            className={
              styles.errorBanner
            }
          >
            {error}
          </div>
        )}

        <section
          className={styles.summary}
        >
          <div
            className={
              styles.summaryCard
            }
          >
            <WalletCards size={20} />

            <div>
              <span>
                Payment records
              </span>
              <strong>{total}</strong>
            </div>
          </div>

          <div
            className={
              styles.summaryCard
            }
          >
            <Banknote size={20} />

            <div>
              <span>
                Loaded amount
              </span>
              <strong>
                {money(
                  items.reduce(
                    (sum, item) =>
                      sum
                      + Number(
                        item.amount
                        || 0,
                      ),
                    0,
                  ),
                )}
              </strong>
            </div>
          </div>
        </section>

        <section
          className={styles.panel}
        >
          <div
            className={
              styles.filters
            }
          >
            <label
              className={
                styles.searchBox
              }
            >
              <Search size={17} />

              <input
                value={search}
                onChange={(event) => {
                  setPage(1);
                  setSearch(
                    event.target.value,
                  );
                }}
                placeholder="Search receipt or reference"
              />
            </label>

            <select
              value={method}
              onChange={(event) => {
                setPage(1);
                setMethod(
                  event.target.value,
                );
              }}
            >
              <option value="">
                All payment methods
              </option>
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
              <option
                value="mobile_payment"
              >
                Mobile payment
              </option>
              <option value="cheque">
                Cheque
              </option>
            </select>

            <select
              value={status}
              onChange={(event) => {
                setPage(1);
                setStatus(
                  event.target.value,
                );
              }}
            >
              <option value="">
                All statuses
              </option>
              <option value="active">
                Active
              </option>
              <option value="reversed">
                Reversed
              </option>
            </select>
          </div>

          {loading ? (
            <div
              className={
                styles.emptyState
              }
            >
              <Loader2
                className={
                  styles.spin
                }
                size={24}
              />
              Loading payments...
            </div>
          ) : items.length === 0 ? (
            <div
              className={
                styles.emptyState
              }
            >
              No payment records found.
            </div>
          ) : (
            <div
              className={
                styles.tableWrap
              }
            >
              <table>
                <thead>
                  <tr>
                    <th>Receipt</th>
                    <th>Date</th>
                    <th>Invoice</th>
                    <th>Method</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th />
                  </tr>
                </thead>

                <tbody>
                  {items.map(
                    (payment) => (
                      <tr
                        key={
                          payment.id
                        }
                      >
                        <td>
                          <strong>
                            {
                              payment
                                .receipt_number
                            }
                          </strong>
                        </td>

                        <td>
                          {dateTime(
                            payment
                              .payment_date,
                          )}
                        </td>

                        <td>
                          {payment.invoice_id
                            ? `#${payment.invoice_id}`
                            : "—"}
                        </td>

                        <td>
                          {readable(
                            payment
                              .payment_method,
                          )}
                        </td>

                        <td>
                          <strong>
                            {money(
                              payment.amount,
                            )}
                          </strong>
                        </td>

                        <td>
                          <span
                            className={
                              styles.statusBadge
                            }
                          >
                            {readable(
                              payment.status
                                || "active",
                            )}
                          </span>
                        </td>

                        <td>
                          <button
                            className={
                              styles.iconButton
                            }
                            onClick={() =>
                              void openDetail(
                                payment.id,
                              )
                            }
                            type="button"
                            title="View payment"
                          >
                            <Eye
                              size={17}
                            />
                          </button>
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          )}

          <div
            className={
              styles.pagination
            }
          >
            <span>
              Page {page} of {pages}
            </span>

            <div>
              <button
                type="button"
                disabled={page <= 1}
                onClick={() =>
                  setPage((value) =>
                    Math.max(
                      1,
                      value - 1,
                    ),
                  )
                }
              >
                Previous
              </button>

              <button
                type="button"
                disabled={page >= pages}
                onClick={() =>
                  setPage((value) =>
                    Math.min(
                      pages,
                      value + 1,
                    ),
                  )
                }
              >
                Next
              </button>
            </div>
          </div>
        </section>

        {(selected
          || detailLoading) && (
          <div
            className={
              styles.modalBackdrop
            }
          >
            <section
              className={
                styles.detailModal
              }
            >
              {detailLoading
                ? (
                  <div
                    className={
                      styles.emptyState
                    }
                  >
                    <Loader2
                      className={
                        styles.spin
                      }
                    />
                    Loading...
                  </div>
                )
                : selected && (
                  <>
                    <div
                      className={
                        styles.modalHeader
                      }
                    >
                      <div>
                        <span>
                          PAYMENT
                        </span>

                        <h2>
                          {
                            selected
                              .receipt_number
                          }
                        </h2>
                      </div>

                      <button
                        type="button"
                        onClick={() =>
                          setSelected(
                            null,
                          )
                        }
                      >
                        <X size={20} />
                      </button>
                    </div>

                    <div
                      className={
                        styles.detailGrid
                      }
                    >
                      <div>
                        <span>
                          Amount
                        </span>
                        <strong>
                          {money(
                            selected.amount,
                          )}
                        </strong>
                      </div>

                      <div>
                        <span>
                          Method
                        </span>
                        <strong>
                          {readable(
                            selected
                              .payment_method,
                          )}
                        </strong>
                      </div>

                      <div>
                        <span>
                          Invoice
                        </span>
                        <strong>
                          {selected.invoice_number
                            || (
                              selected.invoice_id
                                ? `#${selected.invoice_id}`
                                : "—"
                            )}
                        </strong>
                      </div>

                      <div>
                        <span>
                          Status
                        </span>
                        <strong>
                          {readable(
                            selected.status
                              || "active",
                          )}
                        </strong>
                      </div>

                      <div>
                        <span>
                          Date
                        </span>
                        <strong>
                          {dateTime(
                            selected
                              .payment_date,
                          )}
                        </strong>
                      </div>

                      <div>
                        <span>
                          Reference
                        </span>
                        <strong>
                          {selected.reference_number
                            || "—"}
                        </strong>
                      </div>
                    </div>

                    {selected.notes && (
                      <div
                        className={
                          styles.notesBox
                        }
                      >
                        <span>
                          Notes
                        </span>
                        <p>
                          {
                            selected.notes
                          }
                        </p>
                      </div>
                    )}

                    <div
                      className={
                        styles.documentActions
                      }
                    >
                      <button
                        type="button"
                        onClick={() =>
                          void downloadPaymentReceipt(
                            selected.id,
                            selected
                              .receipt_number,
                          )
                        }
                      >
                        <Download
                          size={17}
                        />
                        Receipt PDF
                      </button>

                      {selected.invoice_id && (
                        <button
                          type="button"
                          onClick={() =>
                            void downloadSalesInvoice(
                              selected.invoice_id!,
                              selected
                                .invoice_number
                                || undefined,
                            )
                          }
                        >
                          <FileText
                            size={17}
                          />
                          Invoice PDF
                        </button>
                      )}

                      {(
                        selected.status
                        || "active"
                      ) !== "reversed" && (
                        <button
                          className={
                            styles.dangerButton
                          }
                          type="button"
                          onClick={() => {
                            setError("");
                            setReverseOpen(
                              true,
                            );
                          }}
                        >
                          <RotateCcw
                            size={17}
                          />
                          Reverse payment
                        </button>
                      )}
                    </div>
                  </>
                )}
            </section>
          </div>
        )}

        {receiveOpen && (
          <div
            className={
              styles.modalBackdrop
            }
          >
            <form
              className={
                styles.formModal
              }
              onSubmit={
                submitPayment
              }
            >
              <div
                className={
                  styles.modalHeader
                }
              >
                <div>
                  <span>
                    SALES PAYMENT
                  </span>
                  <h2>
                    Receive payment
                  </h2>
                </div>

                <button
                  type="button"
                  onClick={() =>
                    setReceiveOpen(
                      false,
                    )
                  }
                >
                  <X size={20} />
                </button>
              </div>

              <label>
                Invoice ID
                <input
                  type="number"
                  min="1"
                  required
                  value={invoiceId}
                  onChange={(event) =>
                    setInvoiceId(
                      event.target
                        .value,
                    )
                  }
                />
              </label>

              <label>
                Amount
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  required
                  value={amount}
                  onChange={(event) =>
                    setAmount(
                      event.target
                        .value,
                    )
                  }
                />
              </label>

              <label>
                Payment method
                <select
                  value={
                    paymentMethod
                  }
                  onChange={(event) =>
                    setPaymentMethod(
                      event.target
                        .value,
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
                  <option
                    value="mobile_payment"
                  >
                    Mobile payment
                  </option>
                  <option value="cheque">
                    Cheque
                  </option>
                </select>
              </label>

              <label>
                Reference
                <input
                  value={reference}
                  onChange={(event) =>
                    setReference(
                      event.target
                        .value,
                    )
                  }
                />
              </label>

              <label>
                Notes
                <textarea
                  value={notes}
                  onChange={(event) =>
                    setNotes(
                      event.target
                        .value,
                    )
                  }
                />
              </label>

              <div
                className={
                  styles.modalFooter
                }
              >
                <button
                  type="button"
                  onClick={() =>
                    setReceiveOpen(
                      false,
                    )
                  }
                >
                  Cancel
                </button>

                <button
                  className={
                    styles.primaryButton
                  }
                  disabled={
                    actionLoading
                  }
                  type="submit"
                >
                  {actionLoading
                    ? "Saving..."
                    : "Receive payment"}
                </button>
              </div>
            </form>
          </div>
        )}

        {reverseOpen
          && selected && (
          <div
            className={
              styles.modalBackdrop
            }
          >
            <form
              className={
                styles.formModal
              }
              onSubmit={
                submitReversal
              }
            >
              <div
                className={
                  styles.modalHeader
                }
              >
                <div>
                  <span>
                    REVERSAL
                  </span>
                  <h2>
                    Reverse payment
                  </h2>
                </div>

                <button
                  type="button"
                  onClick={() =>
                    setReverseOpen(
                      false,
                    )
                  }
                >
                  <X size={20} />
                </button>
              </div>

              <div
                className={
                  styles.warningBox
                }
              >
                This reverses{" "}
                <strong>
                  {
                    selected
                      .receipt_number
                  }
                </strong>{" "}
                for{" "}
                <strong>
                  {money(
                    selected.amount,
                  )}
                </strong>
                .
              </div>

              <label>
                Reversal reason
                <input
                  required
                  minLength={3}
                  value={
                    reversalReason
                  }
                  onChange={(event) =>
                    setReversalReason(
                      event.target
                        .value,
                    )
                  }
                />
              </label>

              <label>
                Notes
                <textarea
                  value={
                    reversalNotes
                  }
                  onChange={(event) =>
                    setReversalNotes(
                      event.target
                        .value,
                    )
                  }
                />
              </label>

              <div
                className={
                  styles.modalFooter
                }
              >
                <button
                  type="button"
                  onClick={() =>
                    setReverseOpen(
                      false,
                    )
                  }
                >
                  Cancel
                </button>

                <button
                  className={
                    styles.dangerButton
                  }
                  disabled={
                    actionLoading
                  }
                  type="submit"
                >
                  {actionLoading
                    ? "Reversing..."
                    : "Reverse payment"}
                </button>
              </div>
            </form>
          </div>
        )}
      </main>
    </AppShell>
  );
}
