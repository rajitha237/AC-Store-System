"use client";

import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  ArrowDownLeft,
  ArrowUpRight,
  BookOpenText,
  RefreshCw,
  Scale,
  WalletCards,
} from "lucide-react";

import {
  AppShell,
} from "@/components/app-shell";

import {
  useRouter,
} from "next/navigation";

import {
  clearAuthSession,
  getAccessToken,
  getStoredUser,
} from "@/lib/auth";

import type {
  UserResponse,
} from "@/types/auth";

import {
  confirmManualCashBookCheque,
  createManualCashBookEntry,
  deleteManualCashBookEntry,
  getCashBook,
  reverseManualCashBookEntry,
  updateManualCashBookEntry,
  updateCustomerPayment,
  reverseCustomerPayment,
} from "@/lib/cash-book-api";

import type {
  CashBookListResponse,
  CashBookTransaction,
} from "@/types/cash-book";

import styles from "./page.module.css";


function money(
  value: string | number | null | undefined,
) {
  const amount =
    Number(value ?? 0);

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


function dateTime(
  value: string,
) {
  const parsed =
    new Date(value);

  if (
    Number.isNaN(
      parsed.getTime(),
    )
  ) {
    return value;
  }

  return new Intl.DateTimeFormat(
    "en-LK",
    {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    },
  ).format(parsed);
}


function paymentMethodLabel(
  value: string,
) {
  return value
    .replaceAll("_", " ")
    .replace(
      /\b\w/g,
      (character) =>
        character.toUpperCase(),
    );
}


function sourceLabel(
  transaction: CashBookTransaction,
) {
  switch (
    transaction.source_type
  ) {
    case "customer_payment":
      return "Customer payment";

    case "supplier_payment":
      return "Supplier payment";

    case "manual_cash_book":
      return "Manual entry";

    default:
      return transaction.source_type
        .replaceAll("_", " ")
        .replace(
          /\b\w/g,
          (character) =>
            character.toUpperCase(),
        );
  }
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

  return "Unable to load the cash book.";
}


export default function CashBookPage() {
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

  const [
    data,
    setData,
  ] =
    useState<CashBookListResponse | null>(
      null,
    );

  const [
    loading,
    setLoading,
  ] =
    useState(true);

  const [
    error,
    setError,
  ] =
    useState("");

  const [
    dateFrom,
    setDateFrom,
  ] =
    useState("");

  const [
    dateTo,
    setDateTo,
  ] =
    useState("");

  const [
    page,
    setPage,
  ] =
    useState(1);

  const [
    manualEntryOpen,
    setManualEntryOpen,
  ] = useState(false);

  const [
    manualEntryType,
    setManualEntryType,
  ] = useState<
    "cash_in" | "cash_out"
  >("cash_in");

  const [
    manualAmount,
    setManualAmount,
  ] = useState("");

  const [
    manualPaymentMethod,
    setManualPaymentMethod,
  ] = useState("cash");

  const [
    manualCategory,
    setManualCategory,
  ] = useState("");

  const [
    manualDescription,
    setManualDescription,
  ] = useState("");

  const [
    manualReference,
    setManualReference,
  ] = useState("");

  const [
    manualNotes,
    setManualNotes,
  ] = useState("");

  const [
    manualSaving,
    setManualSaving,
  ] = useState(false);

  const [
    manualEntryDate,
    setManualEntryDate,
  ] = useState("");

  const [
    manualChequeDate,
    setManualChequeDate,
  ] = useState("");

  const [
    manualEditTarget,
    setManualEditTarget,
  ] = useState<CashBookTransaction | null>(
    null,
  );

  const [
    lifecycleSavingId,
    setLifecycleSavingId,
  ] = useState<number | null>(null);

  const pageSize = 50;


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


  const [
    reverseTarget,
    setReverseTarget,
  ] = useState<CashBookTransaction | null>(
    null,
  );

  const [
    reverseReason,
    setReverseReason,
  ] = useState("");

  const [
    reverseNotes,
    setReverseNotes,
  ] = useState("");

  const [
    reverseSaving,
    setReverseSaving,
  ] = useState(false);


  function openReverseDialog(
    transaction: CashBookTransaction,
  ) {
    if (
      transaction.source_type
      !== "manual_cash_book"
    ) {
      return;
    }

    setReverseTarget(
      transaction,
    );

    setReverseReason("");
    setReverseNotes("");
    setError("");
  }


  function closeReverseDialog() {
    if (reverseSaving) {
      return;
    }

    setReverseTarget(
      null,
    );

    setReverseReason("");
    setReverseNotes("");
  }


  async function submitReverseEntry(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (
      reverseSaving
      || !reverseTarget
    ) {
      return;
    }

    if (
      reverseTarget.source_type
      !== "manual_cash_book"
    ) {
      setError(
        "Only manual cash book entries can be reversed here.",
      );

      return;
    }

    const reason =
      reverseReason.trim();

    if (!reason) {
      setError(
        "Enter a reversal reason.",
      );

      return;
    }

    if (reason.length > 255) {
      setError(
        "Reversal reason must be 255 characters or less.",
      );

      return;
    }

    setReverseSaving(
      true,
    );

    setError("");

    try {
      await reverseManualCashBookEntry(
        reverseTarget.source_id,
        {
          reason,
          notes:
            reverseNotes.trim()
            || null,
        },
      );

      setReverseTarget(
        null,
      );

      setReverseReason("");
      setReverseNotes("");

      setPage(1);

      await loadCashBook();
    } catch (
      requestError
    ) {
      setError(
        errorMessage(
          requestError,
        ),
      );
    } finally {
      setReverseSaving(
        false,
      );
    }
  }


  const loadCashBook =
    useCallback(
      async () => {
        setLoading(true);
        setError("");

        try {
          const response =
            await getCashBook({
              page,
              pageSize,
              dateFrom:
                dateFrom || undefined,
              dateTo:
                dateTo || undefined,
            });

          setData(response);
        } catch (
          requestError
        ) {
          setError(
            errorMessage(
              requestError,
            ),
          );
        } finally {
          setLoading(false);
        }
      },
      [
        page,
        dateFrom,
        dateTo,
      ],
    );


  useEffect(
    () => {
      if (
        authLoading
        || !user
      ) {
        return;
      }

      const timer =
        window.setTimeout(
          () => {
            void loadCashBook();
          },
          0,
        );

      return () => {
        window.clearTimeout(
          timer,
        );
      };
    },
    [
      authLoading,
      user,
      loadCashBook,
    ],
  );


  function openManualEntry(
    entryType: "cash_in" | "cash_out",
  ) {
    setManualEntryType(entryType);
    setManualAmount("");
    setManualPaymentMethod("cash");
    setManualCategory("");
    setManualDescription("");
    setManualReference("");
    setManualNotes("");

    const now = new Date();

    const localToday = [
      now.getFullYear(),
      String(
        now.getMonth() + 1,
      ).padStart(2, "0"),
      String(
        now.getDate(),
      ).padStart(2, "0"),
    ].join("-");

    setManualEntryDate(localToday);
    setManualChequeDate("");
    setManualEditTarget(null);
    setError("");
    setManualEntryOpen(true);
  }

  async function submitManualEntry(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (manualSaving) {
      return;
    }

    const amount = Number(manualAmount);

    if (
      !Number.isFinite(amount)
      || amount <= 0
    ) {
      setError(
        "Enter a valid amount greater than zero.",
      );
      return;
    }

    if (!manualEntryDate) {
      setError(
        "Select the transaction date.",
      );
      return;
    }

    const now = new Date();

    const localToday = [
      now.getFullYear(),
      String(
        now.getMonth() + 1,
      ).padStart(2, "0"),
      String(
        now.getDate(),
      ).padStart(2, "0"),
    ].join("-");

    if (manualEntryDate > localToday) {
      setError(
        "Transaction date cannot be in the future.",
      );
      return;
    }

    if (
      manualPaymentMethod === "cheque"
      && !manualChequeDate
    ) {
      setError(
        "Select the cheque date.",
      );
      return;
    }

    const category =
      manualCategory.trim();

    const description =
      manualDescription.trim();

    const reference =
      manualReference.trim();

    if (!category) {
      setError("Enter a category.");
      return;
    }

    if (category.length > 100) {
      setError(
        "Category must be 100 characters or less.",
      );
      return;
    }

    if (!description) {
      setError("Enter a description.");
      return;
    }

    if (description.length > 255) {
      setError(
        "Description must be 255 characters or less.",
      );
      return;
    }

    if (reference.length > 100) {
      setError(
        "Reference must be 100 characters or less.",
      );
      return;
    }

    const payload = {
      entry_type: manualEntryType,
      entry_date: manualEntryDate,
      amount: amount.toFixed(2),
      payment_method:
        manualPaymentMethod,
      category,
      description,
      reference_number:
        reference || null,
      cheque_date:
        manualPaymentMethod === "cheque"
          ? manualChequeDate
          : null,
      notes:
        manualNotes.trim() || null,
    };

    setManualSaving(true);
    setError("");

    try {
      if (
        manualEditTarget?.source_type
          === "customer_payment"
      ) {
        await updateCustomerPayment(
          manualEditTarget.source_id,
          {
            payment_date:
              manualEntryDate,
            amount:
              amount.toFixed(2),
            payment_method:
              manualPaymentMethod,
            reference_number:
              reference || null,
            cheque_date:
              manualPaymentMethod
                === "cheque"
                ? manualChequeDate
                : null,
            notes:
              manualNotes.trim()
                || null,
          },
        );
      } else if (manualEditTarget) {
        await updateManualCashBookEntry(
          manualEditTarget.source_id,
          payload,
        );
      } else {
        await createManualCashBookEntry(
          payload,
        );
      }

      setManualEntryOpen(false);
      setManualEditTarget(null);
      setPage(1);

      await loadCashBook();
    } catch (requestError) {
      setError(
        errorMessage(requestError),
      );
    } finally {
      setManualSaving(false);
    }
  }

  function openEditManualEntry(
    transaction: CashBookTransaction,
  ) {
    const isManual =
      transaction.source_type
        === "manual_cash_book";

    const isCustomerPayment =
      transaction.source_type
        === "customer_payment";

    if (
      (!isManual && !isCustomerPayment)
      || (
        isManual
        && !transaction.can_edit
      )
    ) {
      return;
    }

    setManualEditTarget(transaction);
    setManualEntryType(
      transaction.direction,
    );
    setManualEntryDate(
      transaction.transaction_date.slice(
        0,
        10,
      ),
    );
    setManualAmount(transaction.amount);
    setManualPaymentMethod(
      transaction.payment_method,
    );
    setManualCategory(
      transaction.category,
    );
    setManualDescription(
      transaction.description,
    );
    setManualReference(
      transaction.reference_number || "",
    );
    setManualChequeDate(
      transaction.cheque_date || "",
    );
    setManualNotes(
      transaction.notes || "",
    );

    setError("");
    setManualEntryOpen(true);
  }

  async function confirmIssuedCheque(
    transaction: CashBookTransaction,
  ) {
    if (
      !transaction.can_confirm_cheque
      || lifecycleSavingId !== null
    ) {
      return;
    }

    if (
      !window.confirm(
        "Has this issued cheque actually cleared? "
        + "Only confirm after the cheque was paid.",
      )
    ) {
      return;
    }

    setLifecycleSavingId(
      transaction.source_id,
    );
    setError("");

    try {
      await confirmManualCashBookCheque(
        transaction.source_id,
        {},
      );

      await loadCashBook();
    } catch (requestError) {
      setError(
        errorMessage(requestError),
      );
    } finally {
      setLifecycleSavingId(null);
    }
  }

  async function deleteSourcePayment(
    transaction: CashBookTransaction,
  ) {
    if (
      transaction.source_type
        !== "customer_payment"
      || lifecycleSavingId !== null
    ) {
      return;
    }

    if (
      !window.confirm(
        "Reverse this customer payment? "
        + "Invoice and customer balances "
        + "will be restored.",
      )
    ) {
      return;
    }

    setLifecycleSavingId(
      transaction.source_id,
    );
    setError("");

    try {
      await reverseCustomerPayment(
        transaction.source_id,
        "Reversed from Cash Book",
      );

      await loadCashBook();
    } catch (requestError) {
      setError(
        errorMessage(requestError),
      );
    } finally {
      setLifecycleSavingId(null);
    }
  }

  async function deleteManualEntry(
    transaction: CashBookTransaction,
  ) {
    if (
      transaction.source_type
        !== "manual_cash_book"
      || !transaction.can_delete
      || lifecycleSavingId !== null
    ) {
      return;
    }

    if (
      !window.confirm(
        "Delete this manual Cash Book entry? "
        + "Its audit history will be preserved.",
      )
    ) {
      return;
    }

    setLifecycleSavingId(
      transaction.source_id,
    );
    setError("");

    try {
      await deleteManualCashBookEntry(
        transaction.source_id,
      );

      await loadCashBook();
    } catch (requestError) {
      setError(
        errorMessage(requestError),
      );
    } finally {
      setLifecycleSavingId(null);
    }
  }

  if (
    authLoading
    || !user
  ) {
    return (
      <main
        className="page-center"
      >
        <div
          className="loading-spinner"
        />
      </main>
    );
  }


  const summary =
    data?.summary;

  const transactions =
    data?.items ?? [];


  return (
    <AppShell user={user}>
      <section
        className={
          styles.page
        }
      >
        <header
          className={
            styles.pageHeader
          }
        >
          <div>
            <p
              className={
                styles.eyebrow
              }
            >
              FINANCE
            </p>

            <h1>
              Cash Book
            </h1>

            <p
              className={
                styles.subtitle
              }
            >
              Review cash inflows,
              cash outflows, and the
              running cash balance.
            </p>
          </div>

          <button
            type="button"
            className={
              styles.refreshButton
            }
            onClick={
              () => {
                void loadCashBook();
              }
            }
            disabled={loading}
          >
            <RefreshCw
              size={17}
              aria-hidden="true"
            />

            {loading
              ? "Refreshing..."
              : "Refresh"
            }
          </button>
        </header>


        <section
          className={
            styles.filterCard
          }
          aria-label="Cash book filters"
        >
          <div
            className={
              styles.filterHeader
            }
          >
            <div>
              <strong>
          <div
            className={
              styles.manualActions
            }
          >
            <button
              type="button"
              className={
                styles.cashInButton
              }
              onClick={() =>
                openManualEntry(
                  "cash_in",
                )
              }
            >
              Add Money In
            </button>

            <button
              type="button"
              className={
                styles.cashOutButton
              }
              onClick={() =>
                openManualEntry(
                  "cash_out",
                )
              }
            >
              Add Money Out
            </button>
          </div>

                Date Filters
              </strong>

              <span>
                Filter transactions by
                transaction date.
              </span>
            </div>

            <button
              type="button"
              className={
                styles.clearFilterButton
              }
              onClick={() => {
                setDateFrom("");
                setDateTo("");
                setPage(1);
              }}
              disabled={
                !dateFrom
                && !dateTo
              }
            >
              Clear Dates
            </button>
          </div>

          <div
            className={
              styles.filterGrid
            }
          >
            <label
              className={
                styles.filterField
              }
            >
              <span>
                From Date
              </span>

              <input
                type="date"
                value={dateFrom}
                max={
                  dateTo || undefined
                }
                onChange={
                  (event) => {
                    setDateFrom(
                      event.target.value,
                    );
                    setPage(1);
                  }
                }
              />
            </label>

            <label
              className={
                styles.filterField
              }
            >
              <span>
                To Date
              </span>

              <input
                type="date"
                value={dateTo}
                min={
                  dateFrom || undefined
                }
                onChange={
                  (event) => {
                    setDateTo(
                      event.target.value,
                    );
                    setPage(1);
                  }
                }
              />
            </label>
          </div>
        </section>

        {error ? (
          <div
            className={
              styles.errorBox
            }
            role="alert"
          >
            <strong>
              Cash book could not
              be loaded.
            </strong>

            <span>
              {error}
            </span>
          </div>
        ) : null}


        <section
          className={
            styles.summaryGrid
          }
          aria-label="Cash book summary"
        >
          <article
            className={
              styles.summaryCard
            }
          >
            <div
              className={
                styles.summaryIcon
              }
            >
              <WalletCards
                size={20}
                aria-hidden="true"
              />
            </div>

            <div>
              <span>
                Opening Balance
              </span>

              <strong>
                {money(
                  summary
                    ?.opening_balance,
                )}
              </strong>
            </div>
          </article>


          <article
            className={
              styles.summaryCard
            }
          >
            <div
              className={
                styles.summaryIcon
              }
            >
              <ArrowDownLeft
                size={20}
                aria-hidden="true"
              />
            </div>

            <div>
              <span>
                Money In
              </span>

              <strong>
                {money(
                  summary?.cash_in,
                )}
              </strong>
            </div>
          </article>


          <article
            className={
              styles.summaryCard
            }
          >
            <div
              className={
                styles.summaryIcon
              }
            >
              <ArrowUpRight
                size={20}
                aria-hidden="true"
              />
            </div>

            <div>
              <span>
                Money Out
              </span>

              <strong>
                {money(
                  summary?.cash_out,
                )}
              </strong>
            </div>
          </article>


          <article
            className={
              styles.summaryCard
            }
          >
            <div
              className={
                styles.summaryIcon
              }
            >
              <Scale
                size={20}
                aria-hidden="true"
              />
            </div>

            <div>
              <span>
                Closing Balance
              </span>

              <strong>
                {money(
                  summary
                    ?.closing_balance,
                )}
              </strong>
            </div>
          </article>
        </section>


        <section
          className={
            styles.breakdownSection
          }
          aria-label="Payment method breakdown"
        >
          <div
            className={
              styles.breakdownHeader
            }
          >
            <div
              className={
                styles.cardTitle
              }
            >
              <WalletCards
                size={19}
                aria-hidden="true"
              />

              <h2>
                Payment Method Breakdown
              </h2>
            </div>

            <p>
              Money movement for the
              selected date range,
              separated by payment method.
            </p>
          </div>

          <div
            className={
              styles.methodGrid
            }
          >
            {[
              {
                label: "Cash",
                incoming:
                  summary
                    ?.cash_method_in,
                outgoing:
                  summary
                    ?.cash_method_out,
              },
              {
                label:
                  "Bank Transfer",
                incoming:
                  summary
                    ?.bank_transfer_in,
                outgoing:
                  summary
                    ?.bank_transfer_out,
              },
              {
                label: "Cheque",
                incoming:
                  summary?.cheque_in,
                outgoing:
                  summary?.cheque_out,
                pendingOutgoing:
                  summary
                    ?.cheque_pending_out,
              },
              {
                label: "Card",
                incoming:
                  summary?.card_in,
                outgoing:
                  summary?.card_out,
              },
            ].map((item) => {
              const incoming =
                Number(
                  item.incoming
                  ?? 0,
                );

              const outgoing =
                Number(
                  item.outgoing
                  ?? 0,
                );

              const pendingOutgoing =
                Number(
                  item.pendingOutgoing
                  ?? 0,
                );

              const issuedTotal =
                outgoing
                + pendingOutgoing;

              const net =
                incoming - outgoing;

              const isCheque =
                item.label === "Cheque";

              return (
                <article
                  key={
                    item.label
                  }
                  className={
                    styles.methodCard
                  }
                >
                  <div
                    className={
                      styles.methodCardHeader
                    }
                  >
                    <span>
                      {item.label}
                    </span>

                    <strong>
                      {money(net)}
                    </strong>
                  </div>

                  <div
                    className={
                      styles.methodMetrics
                    }
                  >
                    <div>
                      <span>
                        Money In
                      </span>

                      <strong>
                        {money(
                          incoming,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Money Out
                      </span>

                      <strong>
                        {money(
                          outgoing,
                        )}
                      </strong>
                    </div>
                  </div>

                  {isCheque ? (
                    <>
                      <div
                        className={
                          styles.methodMetrics
                        }
                      >
                        <div>
                          <span>
                            Issued Total
                          </span>

                          <strong>
                            {money(
                              issuedTotal,
                            )}
                          </strong>
                        </div>

                        <div>
                          <span>
                            Pending Out
                          </span>

                          <strong>
                            {money(
                              pendingOutgoing,
                            )}
                          </strong>
                        </div>
                      </div>

                      <div
                        className={
                          styles.methodNet
                        }
                      >
                        <span>
                          Effective Net
                        </span>

                        <strong>
                          {money(net)}
                        </strong>
                      </div>

                      <p
                        style={{
                          margin: 0,
                          fontSize: "0.78rem",
                          opacity: 0.72,
                          lineHeight: 1.45,
                        }}
                      >
                        Money Out above includes
                        cleared cheques only.
                        Pending cheques are shown
                        separately and do not
                        affect the balance.
                      </p>
                    </>
                  ) : (
                    <div
                      className={
                        styles.methodNet
                      }
                    >
                      <span>
                        Net movement
                      </span>

                      <strong>
                        {money(net)}
                      </strong>
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        </section>


        <section
          className={
            styles.transactionsCard
          }
        >
          <div
            className={
              styles.cardHeader
            }
          >
            <div>
              <div
                className={
                  styles.cardTitle
                }
              >
                <BookOpenText
                  size={19}
                  aria-hidden="true"
                />

                <h2>
                  Transactions
                </h2>
              </div>

              <p>
                Newest transactions
                appear first.
              </p>
            </div>

            <span
              className={
                styles.countBadge
              }
            >
              {data?.total ?? 0}
              {" "}
              transactions
            </span>
          </div>


          {loading && !data ? (
            <div
              className={
                styles.stateBox
              }
            >
              <div
                className="loading-spinner"
              />

              <p>
                Loading cash book...
              </p>
            </div>
          ) : null}


          {!loading
          && !error
          && transactions.length === 0 ? (
            <div
              className={
                styles.stateBox
              }
            >
              <BookOpenText
                size={30}
                aria-hidden="true"
              />

              <strong>
                No cash transactions
                found
              </strong>

              <p>
                Cash transactions
                will appear here when
                activity is recorded.
              </p>
            </div>
          ) : null}


          {transactions.length > 0 ? (
            <div
              className={
                styles.tableWrap
              }
            >
              <table
                className={
                  styles.table
                }
              >
                <thead>
                  <tr>
                    <th>
                      Date
                    </th>

                    <th>
                      Reference
                    </th>

                    <th>
                      Source
                    </th>

                    <th>
                      Description
                    </th>

                    <th>
                      Method
                    </th>

                    <th>
                      Direction
                    </th>

                    <th
                      className={
                        styles.numberCell
                      }
                    >
                      Amount
                    </th>

                    <th
                      className={
                        styles.numberCell
                      }
                    >
                      Balance
                    </th>

                    <th
                      className={
                        styles.actionCell
                      }
                    >
                      Action
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {transactions.map(
                    (
                      transaction,
                      index,
                    ) => (
                      <tr
                        key={
                          `${transaction.source_type}-${transaction.source_id}-${transaction.transaction_date}-${index}`
                        }
                      >
                        <td>
                          {dateTime(
                            transaction
                              .transaction_date,
                          )}
                        </td>

                        <td>
                          <strong>
                            {transaction
                              .source_reference
                              || "—"
                            }
                          </strong>
                        </td>

                        <td>
                          {sourceLabel(
                            transaction,
                          )}
                        </td>

                        <td>
                          <div
                            className={
                              styles.descriptionCell
                            }
                          >
                            <strong>
                              {transaction
                                .description
                              }
                            </strong>

                            <span>
                              {transaction
                                .category
                              }
                            </span>
                          </div>
                        </td>

                        <td>
                          {paymentMethodLabel(
                            transaction
                              .payment_method,
                          )}
                        </td>

                        <td>
                          <span
                            className={
                              transaction
                                .direction
                                === "cash_in"
                                ? styles.cashInBadge
                                : styles.cashOutBadge
                            }
                          >
                            {transaction
                              .direction
                              === "cash_in"
                              ? "Money In"
                              : "Money Out"
                            }
                          </span>
                        </td>

                        <td
                          className={
                            styles.numberCell
                          }
                        >
                          <strong>
                            {money(
                              transaction
                                .amount,
                            )}
                          </strong>
                        </td>

                        <td
                          className={
                            styles.numberCell
                          }
                        >
                          {transaction
                            .running_balance
                            === null
                            ? "—"
                            : money(
                                transaction
                                  .running_balance,
                              )
                          }
                        </td>

                        <td
                          className={
                            styles.actionCell
                          }
                        >
                          {transaction
                              .source_type
                              === "manual_cash_book"
                              ? (
                                <div
                                  className={
                                    styles.rowActions
                                  }
                                >
                                  {transaction
                                    .can_confirm_cheque
                                    ? (
                                      <button
                                        type="button"
                                        className={
                                          styles.confirmChequeButton
                                        }
                                        disabled={
                                          lifecycleSavingId
                                            === transaction.source_id
                                        }
                                        onClick={() =>
                                          void confirmIssuedCheque(
                                            transaction,
                                          )
                                        }
                                      >
                                        Confirm Paid
                                      </button>
                                    )
                                    : null}

                                </div>
                              )
                              : transaction.source_type
                                  === "customer_payment"
                                ? (
                                  <div
                                    className={
                                      styles.actionButtons
                                    }
                                  >

                                  </div>
                                )
                                : (
                                  <span
                                    className={
                                      styles.noAction
                                    }
                                    title="Manage this record from its original payment."
                                  >
                                    Source managed
                                  </span>
                                )}
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>

        <nav
          className={
            styles.pagination
          }
          aria-label="Cash book pagination"
        >
          <div
            className={
              styles.paginationInfo
            }
          >
            <strong>
              Page {data?.page ?? page}
              {" "}
              of
              {" "}
              {Math.max(
                data?.pages ?? 1,
                1,
              )}
            </strong>

            <span>
              {data?.total ?? 0}
              {" "}
              transactions ·
              {" "}
              {pageSize}
              {" "}
              per page
            </span>
          </div>

          <div
            className={
              styles.paginationActions
            }
          >
            <button
              type="button"
              onClick={() => {
                setPage(
                  (currentPage) =>
                    Math.max(
                      1,
                      currentPage - 1,
                    ),
                );
              }}
              disabled={
                loading
                || page <= 1
              }
            >
              Previous
            </button>

            <button
              type="button"
              onClick={() => {
                setPage(
                  (currentPage) =>
                    currentPage + 1,
                );
              }}
              disabled={
                loading
                || page >= Math.max(
                  data?.pages ?? 1,
                  1,
                )
              }
            >
              Next
            </button>
          </div>
        </nav>
      </section>
      {manualEntryOpen ? (
        <div
          className={
            styles.modalBackdrop
          }
          role="presentation"
          onMouseDown={(
            event
          ) => {
            if (
              event.target
              === event.currentTarget
              && !manualSaving
            ) {
              setManualEntryOpen(
                false,
              );
            }
          }}
        >
          <div
            className={
              styles.manualEntryDialog
            }
            role="dialog"
            aria-modal="true"
            aria-labelledby="manual-cash-entry-title"
          >
            <div
              className={
                styles.modalHeader
              }
            >
              <div>
                <p
                  className={
                    styles.modalEyebrow
                  }
                >
                  MANUAL ENTRY
                </p>

                <h2
                  id="manual-cash-entry-title"
                >
                  {manualEditTarget
                      ? "Edit Cash Book Entry"
                      : (
                        manualEntryType
                          === "cash_in"
                          ? "Add Money In"
                          : "Add Money Out"
                      )}
                </h2>
              </div>

              <button
                type="button"
                className={
                  styles.modalClose
                }
                disabled={
                  manualSaving
                }
                onClick={() =>
                  setManualEntryOpen(
                    false,
                  )
                }
                aria-label="Close manual cash entry"
              >
                ×
              </button>
            </div>

            <form
              className={
                styles.manualEntryForm
              }
              onSubmit={
                submitManualEntry
              }
            >
              <div
                className={
                  styles.entryTypeSwitch
                }
              >
                <button
                  type="button"
                  className={
                    manualEntryType
                      === "cash_in"
                      ? styles.entryTypeActive
                      : styles.entryTypeButton
                  }
                  disabled={
                    manualSaving
                    || manualEditTarget
                      ?.source_type
                      === "customer_payment"
                  }
                  onClick={() =>
                    setManualEntryType(
                      "cash_in",
                    )
                  }
                >
                  Money In
                </button>

                <button
                  type="button"
                  className={
                    manualEntryType
                      === "cash_out"
                      ? styles.entryTypeActive
                      : styles.entryTypeButton
                  }
                  disabled={
                    manualSaving
                    || manualEditTarget
                      ?.source_type
                      === "customer_payment"
                  }
                  onClick={() =>
                    setManualEntryType(
                      "cash_out",
                    )
                  }
                >
                  Money Out
                </button>
              </div>

              <div
                className={
                  styles.formGrid
                }
              >
                <label>
                    Transaction Date *

                    <input
                      required
                      type="date"
                      value={
                        manualEntryDate
                      }
                      disabled={
                        manualSaving
                      }
                      onChange={(
                        event
                      ) =>
                        setManualEntryDate(
                          event.target.value,
                        )
                      }
                    />
                  </label>

                  <label>
                  Amount *

                  <input
                    required
                    type="number"
                    min="0.01"
                    step="0.01"
                    inputMode="decimal"
                    value={
                      manualAmount
                    }
                    disabled={
                      manualSaving
                    }
                    onChange={(
                      event
                    ) =>
                      setManualAmount(
                        event.target
                          .value,
                      )
                    }
                    placeholder="0.00"
                  />
                </label>

                <label>
                    Payment Method *

                    <select
                      required
                      value={
                        manualPaymentMethod
                      }
                      disabled={
                        manualSaving
                      }
                      onChange={(
                        event
                      ) => {
                        const method =
                          event.target.value;

                        setManualPaymentMethod(
                          method,
                        );

                        if (
                          method !== "cheque"
                        ) {
                          setManualChequeDate("");
                        }
                      }}
                    >
                      <option value="cash">
                        Cash
                      </option>

                      <option value="card">
                        Card
                      </option>

                      <option value="bank_transfer">
                        Bank Transfer
                      </option>

                      <option value="cheque">
                        Cheque
                      </option>
                    </select>
                  </label>

                  {manualPaymentMethod
                    === "cheque" ? (
                    <label>
                      Cheque Date *

                      <input
                        required
                        type="date"
                        value={
                          manualChequeDate
                        }
                        disabled={
                          manualSaving
                        }
                        onChange={(
                          event
                        ) =>
                          setManualChequeDate(
                            event.target.value,
                          )
                        }
                      />
                    </label>
                  ) : null}

                <label>
                  Category *

                  <input
                    required
                    type="text"
                    maxLength={100}
                    value={
                      manualCategory
                    }
                    disabled={
                      manualSaving
                      || manualEditTarget
                        ?.source_type
                        === "customer_payment"
                    }
                    onChange={(
                      event
                    ) =>
                      setManualCategory(
                        event.target
                          .value,
                      )
                    }
                    placeholder="Example: Petty cash"
                  />
                </label>

                <label>
                  Reference Number

                  <input
                    type="text"
                    maxLength={100}
                    value={
                      manualReference
                    }
                    disabled={
                      manualSaving
                    }
                    onChange={(
                      event
                    ) =>
                      setManualReference(
                        event.target
                          .value,
                      )
                    }
                    placeholder="Optional reference"
                  />
                </label>

                <label
                  className={
                    styles.fullField
                  }
                >
                  Description *

                  <input
                    required
                    type="text"
                    maxLength={255}
                    value={
                      manualDescription
                    }
                    disabled={
                      manualSaving
                      || manualEditTarget
                        ?.source_type
                        === "customer_payment"
                    }
                    onChange={(
                      event
                    ) =>
                      setManualDescription(
                        event.target
                          .value,
                      )
                    }
                    placeholder="Describe this cash entry"
                  />
                </label>

                <label
                  className={
                    styles.fullField
                  }
                >
                  Notes

                  <textarea
                    rows={3}
                    value={
                      manualNotes
                    }
                    disabled={
                      manualSaving
                    }
                    onChange={(
                      event
                    ) =>
                      setManualNotes(
                        event.target
                          .value,
                      )
                    }
                    placeholder="Optional notes"
                  />
                </label>
              </div>

              <div
                className={
                  styles.modalFooter
                }
              >
                <button
                  type="button"
                  className={
                    styles.cancelButton
                  }
                  disabled={
                    manualSaving
                  }
                  onClick={() =>
                    setManualEntryOpen(
                      false,
                    )
                  }
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className={
                    styles.saveButton
                  }
                  disabled={
                    manualSaving
                  }
                >
                  {manualSaving
                      ? "Saving..."
                      : (
                        manualEditTarget
                          ? "Save Changes"
                          : (
                            manualEntryType
                              === "cash_in"
                              ? "Save Money In"
                              : "Save Money Out"
                          )
                      )}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {reverseTarget ? (
        <div
          className={
            styles.modalBackdrop
          }
          role="presentation"
          onMouseDown={(
            event
          ) => {
            if (
              event.target
              === event.currentTarget
              && !reverseSaving
            ) {
              closeReverseDialog();
            }
          }}
        >
          <div
            className={
              styles.reverseDialog
            }
            role="dialog"
            aria-modal="true"
            aria-labelledby="reverse-cash-entry-title"
          >
            <div
              className={
                styles.modalHeader
              }
            >
              <div>
                <p
                  className={
                    styles.modalEyebrow
                  }
                >
                  MANUAL ENTRY
                </p>

                <h2
                  id="reverse-cash-entry-title"
                >
                  Reverse Cash Entry
                </h2>
              </div>

              <button
                type="button"
                className={
                  styles.modalClose
                }
                disabled={
                  reverseSaving
                }
                onClick={
                  closeReverseDialog
                }
                aria-label="Close reverse cash entry"
              >
                ×
              </button>
            </div>

            <div
              className={
                styles.reverseSummary
              }
            >
              <div>
                <span>
                  Reference
                </span>

                <strong>
                  {reverseTarget
                    .source_reference
                    || "—"}
                </strong>
              </div>

              <div>
                <span>
                  Amount
                </span>

                <strong>
                  {money(
                    reverseTarget.amount,
                  )}
                </strong>
              </div>

              <div>
                <span>
                  Direction
                </span>

                <strong>
                  {reverseTarget.direction
                    === "cash_in"
                    ? "Money In"
                    : "Money Out"}
                </strong>
              </div>
            </div>

            <form
              className={
                styles.manualEntryForm
              }
              onSubmit={
                submitReverseEntry
              }
            >
              <div
                className={
                  styles.formGrid
                }
              >
                <label
                  className={
                    styles.fullField
                  }
                >
                  Reversal Reason *

                  <input
                    required
                    type="text"
                    maxLength={255}
                    value={
                      reverseReason
                    }
                    disabled={
                      reverseSaving
                    }
                    onChange={(
                      event
                    ) =>
                      setReverseReason(
                        event.target.value,
                      )
                    }
                    placeholder="Why is this entry being reversed?"
                  />
                </label>

                <label
                  className={
                    styles.fullField
                  }
                >
                  Notes

                  <textarea
                    rows={3}
                    value={
                      reverseNotes
                    }
                    disabled={
                      reverseSaving
                    }
                    onChange={(
                      event
                    ) =>
                      setReverseNotes(
                        event.target.value,
                      )
                    }
                    placeholder="Optional reversal notes"
                  />
                </label>
              </div>

              <div
                className={
                  styles.modalFooter
                }
              >
                <button
                  type="button"
                  className={
                    styles.cancelButton
                  }
                  disabled={
                    reverseSaving
                  }
                  onClick={
                    closeReverseDialog
                  }
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className={
                    styles.reverseConfirmButton
                  }
                  disabled={
                    reverseSaving
                  }
                >
                  {reverseSaving
                    ? "Reversing..."
                    : "Confirm Reverse"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

    </AppShell>
  );
}
