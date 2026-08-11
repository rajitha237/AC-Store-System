"use client";

import axios from "axios";

import {
  BadgeDollarSign,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Eye,
  FileText,
  Loader2,
  Plus,
  RefreshCw,
  RotateCcw,
  Search,
  Send,
  Undo2,
  X,
} from "lucide-react";

import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

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
  approveCreditNote,
  createCreditNote,
  createRefund,
  getCreditNote,
  getCreditNotes,
  postCreditNote,
  postRefund,
  reverseCreditNote,
  reverseRefund,
} from "@/lib/credit-notes-api";

import type {
  UserResponse,
} from "@/types/auth";

import type {
  CreditNoteDetailResponse,
  CreditNoteListResult,
  CustomerRefundResponse,
  RefundMethod,
} from "@/types/credit-notes";

import styles from "./credit-notes.module.css";


const PAGE_SIZE = 20;


const emptyList:
CreditNoteListResult = {
  items: [],
  total: 0,
  page: 1,
  page_size: PAGE_SIZE,
  total_pages: 0,
};


function numberValue(
  value:
    | string
    | number
    | null
    | undefined,
): number {
  const parsed =
    Number(value);

  return (
    Number.isFinite(parsed)
      ? parsed
      : 0
  );
}


function money(
  value:
    | string
    | number
    | null
    | undefined,
): string {
  return new Intl.NumberFormat(
    "en-LK",
    {
      style:
        "currency",

      currency:
        "LKR",

      minimumFractionDigits:
        2,
    },
  ).format(
    numberValue(value),
  );
}


function dateTime(
  value:
    string | null,
): string {
  if (!value) {
    return "—";
  }

  const date =
    new Date(value);

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return value;
  }

  return new Intl.DateTimeFormat(
    "en-LK",
    {
      dateStyle:
        "medium",

      timeStyle:
        "short",
    },
  ).format(date);
}


function readable(
  value:
    string | null | undefined,
): string {
  if (!value) {
    return "—";
  }

  return value
    .split("_")
    .map(
      (part) =>
        part.charAt(0)
          .toUpperCase()
        + part.slice(1),
    )
    .join(" ");
}


function optionalText(
  value: string,
): string | null {
  const cleaned =
    value.trim();

  return (
    cleaned.length > 0
      ? cleaned
      : null
  );
}


function apiError(
  error: unknown,
): string {
  if (
    !axios.isAxiosError(
      error,
    )
  ) {
    return (
      "Something went wrong. "
      + "Please try again."
    );
  }

  const detail =
    error.response
      ?.data?.detail;

  if (
    typeof detail
    === "string"
  ) {
    return detail;
  }

  if (
    Array.isArray(detail)
    && detail.length > 0
    && typeof detail[0]?.msg
      === "string"
  ) {
    return detail[0].msg.replace(
      /^Value error, /,
      "",
    );
  }

  if (
    error.response?.status
    === 403
  ) {
    return (
      "You do not have permission "
      + "for this financial action."
    );
  }

  return (
    "Unable to complete "
    + "this credit note operation."
  );
}


export default function CreditNotesPage() {
  const router =
    useRouter();

  const [
    user,
    setUser,
  ] =
    useState<
      UserResponse | null
    >(
      null,
    );

  const [
    authLoading,
    setAuthLoading,
  ] =
    useState(true);


  const [
    list,
    setList,
  ] =
    useState<
      CreditNoteListResult
    >(
      emptyList,
    );

  const [
    loading,
    setLoading,
  ] =
    useState(true);

  const [
    refreshing,
    setRefreshing,
  ] =
    useState(false);

  const [
    error,
    setError,
  ] =
    useState("");


  const [
    page,
    setPage,
  ] =
    useState(1);

  const [
    searchInput,
    setSearchInput,
  ] =
    useState("");

  const [
    search,
    setSearch,
  ] =
    useState("");

  const [
    statusFilter,
    setStatusFilter,
  ] =
    useState("");


  const [
    selected,
    setSelected,
  ] =
    useState<
      CreditNoteDetailResponse
      | null
    >(
      null,
    );

  const [
    detailOpen,
    setDetailOpen,
  ] =
    useState(false);

  const [
    detailLoading,
    setDetailLoading,
  ] =
    useState(false);


  const [
    createOpen,
    setCreateOpen,
  ] =
    useState(false);

  const [
    createReturnId,
    setCreateReturnId,
  ] =
    useState("");

  const [
    createNotes,
    setCreateNotes,
  ] =
    useState("");


  const [
    actionMode,
    setActionMode,
  ] =
    useState<
      | "approve"
      | "reverse-credit"
      | "refund"
      | "reverse-refund"
      | null
    >(
      null,
    );

  const [
    actionLoading,
    setActionLoading,
  ] =
    useState(false);

  const [
    approvalNotes,
    setApprovalNotes,
  ] =
    useState("");

  const [
    reversalReason,
    setReversalReason,
  ] =
    useState("");


  const [
    refundAmount,
    setRefundAmount,
  ] =
    useState("");

  const [
    refundMethod,
    setRefundMethod,
  ] =
    useState<
      RefundMethod
    >(
      "cash",
    );

  const [
    refundReference,
    setRefundReference,
  ] =
    useState("");

  const [
    refundNotes,
    setRefundNotes,
  ] =
    useState("");


  const [
    selectedRefund,
    setSelectedRefund,
  ] =
    useState<
      CustomerRefundResponse
      | null
    >(
      null,
    );


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


  const loadCreditNotes =
    useCallback(
      async (
        refresh = false,
      ) => {
        if (refresh) {
          setRefreshing(
            true,
          );
        } else {
          setLoading(
            true,
          );
        }

        setError("");

        try {
          const result =
            await getCreditNotes({
              page,

              pageSize:
                PAGE_SIZE,

              search:
                search
                || undefined,

              status:
                statusFilter
                || undefined,
            });

          setList(
            result,
          );
        } catch (
          requestError
        ) {
          setError(
            apiError(
              requestError,
            ),
          );
        } finally {
          setLoading(
            false,
          );

          setRefreshing(
            false,
          );
        }
      },
      [
        page,
        search,
        statusFilter,
      ],
    );


  useEffect(() => {
    if (authLoading) {
      return;
    }

    const timer =
      window.setTimeout(
        () => {
          void loadCreditNotes();
        },
        0,
      );

    return () => {
      window.clearTimeout(
        timer,
      );
    };
  }, [
    authLoading,
    loadCreditNotes,
  ]);


  const summary =
    useMemo(
      () => {
        const draft =
          list.items.filter(
            (item) =>
              item.status
              === "draft",
          ).length;

        const posted =
          list.items.filter(
            (item) =>
              item.status
              === "posted",
          ).length;

        const value =
          list.items.reduce(
            (
              total,
              item,
            ) =>
              total
              + numberValue(
                  item.amount,
                ),
            0,
          );

        return {
          draft,
          posted,
          value,
        };
      },
      [list.items],
    );


  async function refreshSelected(
    id: number,
  ) {
    const detail =
      await getCreditNote(
        id,
      );

    setSelected(
      detail,
    );

    return detail;
  }


  async function openDetail(
    id: number,
  ) {
    setDetailOpen(
      true,
    );

    setDetailLoading(
      true,
    );

    setSelected(
      null,
    );

    setError("");

    try {
      await refreshSelected(
        id,
      );
    } catch (
      requestError
    ) {
      setError(
        apiError(
          requestError,
        ),
      );
    } finally {
      setDetailLoading(
        false,
      );
    }
  }


  function submitSearch(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setPage(
      1,
    );

    setSearch(
      searchInput
        .trim()
        .slice(
          0,
          150,
        ),
    );
  }


  async function submitCreate(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const returnId =
      Number(
        createReturnId,
      );

    if (
      !Number.isInteger(
        returnId,
      )
      || returnId <= 0
    ) {
      setError(
        "Enter a valid Return ID.",
      );

      return;
    }

    setActionLoading(
      true,
    );

    setError("");

    try {
      const created =
        await createCreditNote({
          return_id:
            returnId,

          notes:
            optionalText(
              createNotes,
            ),
        });

      setCreateOpen(
        false,
      );

      setCreateReturnId(
        "",
      );

      setCreateNotes(
        "",
      );

      setSelected(
        created,
      );

      setDetailOpen(
        true,
      );

      await loadCreditNotes(
        true,
      );
    } catch (
      requestError
    ) {
      setError(
        apiError(
          requestError,
        ),
      );
    } finally {
      setActionLoading(
        false,
      );
    }
  }


  async function submitApproval() {
    if (!selected) {
      return;
    }

    setActionLoading(
      true,
    );

    setError("");

    try {
      const result =
        await approveCreditNote(
          selected.id,
          {
            notes:
              optionalText(
                approvalNotes,
              ),
          },
        );

      setSelected(
        result,
      );

      setApprovalNotes(
        "",
      );

      setActionMode(
        null,
      );

      await loadCreditNotes(
        true,
      );
    } catch (
      requestError
    ) {
      setError(
        apiError(
          requestError,
        ),
      );
    } finally {
      setActionLoading(
        false,
      );
    }
  }


  async function submitPostCredit() {
    if (!selected) {
      return;
    }

    setActionLoading(
      true,
    );

    setError("");

    try {
      const result =
        await postCreditNote(
          selected.id,
        );

      setSelected(
        result,
      );

      await loadCreditNotes(
        true,
      );
    } catch (
      requestError
    ) {
      setError(
        apiError(
          requestError,
        ),
      );
    } finally {
      setActionLoading(
        false,
      );
    }
  }


  async function submitCreditReversal() {
    if (!selected) {
      return;
    }

    if (
      reversalReason
        .trim()
        .length < 3
    ) {
      setError(
        "Enter a reversal reason.",
      );

      return;
    }

    setActionLoading(
      true,
    );

    setError("");

    try {
      const result =
        await reverseCreditNote(
          selected.id,
          {
            reason:
              reversalReason.trim(),
          },
        );

      setSelected(
        result,
      );

      setReversalReason(
        "",
      );

      setActionMode(
        null,
      );

      await loadCreditNotes(
        true,
      );
    } catch (
      requestError
    ) {
      setError(
        apiError(
          requestError,
        ),
      );
    } finally {
      setActionLoading(
        false,
      );
    }
  }


  function openRefundCreate() {
    if (!selected) {
      return;
    }

    setRefundAmount(
      selected
        .refundable_overpayment,
    );

    setRefundMethod(
      "cash",
    );

    setRefundReference(
      "",
    );

    setRefundNotes(
      "",
    );

    setActionMode(
      "refund",
    );
  }


  async function submitRefund() {
    if (!selected) {
      return;
    }

    const amount =
      numberValue(
        refundAmount,
      );

    if (amount <= 0) {
      setError(
        "Refund amount must be "
        + "greater than zero.",
      );

      return;
    }

    const available =
      numberValue(
        selected
          .refundable_overpayment,
      );

    if (
      available > 0
      && amount > available
    ) {
      setError(
        "Refund amount cannot exceed "
        + "the refundable overpayment.",
      );

      return;
    }

    setActionLoading(
      true,
    );

    setError("");

    try {
      await createRefund({
        credit_note_id:
          selected.id,

        amount:
          amount.toFixed(2),

        refund_method:
          refundMethod,

        reference_number:
          optionalText(
            refundReference,
          ),

        notes:
          optionalText(
            refundNotes,
          ),
      });

      setActionMode(
        null,
      );

      await refreshSelected(
        selected.id,
      );

      await loadCreditNotes(
        true,
      );
    } catch (
      requestError
    ) {
      setError(
        apiError(
          requestError,
        ),
      );
    } finally {
      setActionLoading(
        false,
      );
    }
  }


  async function submitPostRefund(
    refund:
      CustomerRefundResponse,
  ) {
    if (!selected) {
      return;
    }

    setActionLoading(
      true,
    );

    setError("");

    try {
      await postRefund(
        refund.id,
      );

      await refreshSelected(
        selected.id,
      );

      await loadCreditNotes(
        true,
      );
    } catch (
      requestError
    ) {
      setError(
        apiError(
          requestError,
        ),
      );
    } finally {
      setActionLoading(
        false,
      );
    }
  }


  function openRefundReversal(
    refund:
      CustomerRefundResponse,
  ) {
    setSelectedRefund(
      refund,
    );

    setReversalReason(
      "",
    );

    setActionMode(
      "reverse-refund",
    );
  }


  async function submitRefundReversal() {
    if (
      !selected
      || !selectedRefund
    ) {
      return;
    }

    if (
      reversalReason
        .trim()
        .length < 3
    ) {
      setError(
        "Enter a refund "
        + "reversal reason.",
      );

      return;
    }

    setActionLoading(
      true,
    );

    setError("");

    try {
      await reverseRefund(
        selectedRefund.id,
        {
          reason:
            reversalReason.trim(),
        },
      );

      setActionMode(
        null,
      );

      setSelectedRefund(
        null,
      );

      setReversalReason(
        "",
      );

      await refreshSelected(
        selected.id,
      );

      await loadCreditNotes(
        true,
      );
    } catch (
      requestError
    ) {
      setError(
        apiError(
          requestError,
        ),
      );
    } finally {
      setActionLoading(
        false,
      );
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


  return (
    <AppShell user={user}>
      <section
        className={
          styles.pageHeader
        }
      >
        <div>
          <p className="eyebrow">
            SALES
          </p>

          <h1>
            Credit Notes
          </h1>

          <p>
            Create return-linked
            credit notes, approve and
            post financial credits,
            issue customer refunds,
            and manage reversals.
          </p>
        </div>

        <div
          className={
            styles.headerActions
          }
        >
          <button
            type="button"
            className={
              styles.primaryButton
            }
            onClick={() => {
              setError("");
              setCreateOpen(
                true,
              );
            }}
          >
            <Plus size={17} />

            New credit note
          </button>

          <button
            type="button"
            className={
              styles.secondaryButton
            }
            disabled={
              refreshing
            }
            onClick={() =>
              void loadCreditNotes(
                true,
              )
            }
          >
            <RefreshCw
              size={16}
              className={
                refreshing
                  ? styles.spin
                  : undefined
              }
            />

            Refresh
          </button>
        </div>
      </section>


      <section
        className={
          styles.summaryGrid
        }
      >
        <article>
          <FileText size={20} />

          <div>
            <span>
              Credit notes
            </span>

            <strong>
              {list.total}
            </strong>
          </div>
        </article>

        <article>
          <CircleAlert size={20} />

          <div>
            <span>
              Draft
            </span>

            <strong>
              {summary.draft}
            </strong>
          </div>
        </article>

        <article>
          <Check size={20} />

          <div>
            <span>
              Posted
            </span>

            <strong>
              {summary.posted}
            </strong>
          </div>
        </article>

        <article>
          <BadgeDollarSign
            size={20}
          />

          <div>
            <span>
              Loaded value
            </span>

            <strong>
              {money(
                summary.value,
              )}
            </strong>
          </div>
        </article>
      </section>


      <section
        className={
          styles.filters
        }
      >
        <form
          className={
            styles.searchForm
          }
          onSubmit={
            submitSearch
          }
        >
          <Search size={16} />

          <input
            value={
              searchInput
            }
            placeholder={
              "Credit note, return, invoice or customer..."
            }
            onChange={
              (event) =>
                setSearchInput(
                  event
                    .target
                    .value,
                )
            }
          />

          <button type="submit">
            Search
          </button>
        </form>

        <select
          value={
            statusFilter
          }
          onChange={
            (event) => {
              setPage(1);

              setStatusFilter(
                event
                  .target
                  .value,
              );
            }
          }
        >
          <option value="">
            All statuses
          </option>

          <option value="draft">
            Draft
          </option>

          <option value="approved">
            Approved
          </option>

          <option value="posted">
            Posted
          </option>

          <option value="reversed">
            Reversed
          </option>
        </select>
      </section>


      {error && (
        <div
          className={
            styles.errorBanner
          }
        >
          <CircleAlert
            size={17}
          />

          {error}
        </div>
      )}


      <section
        className={
          styles.tableCard
        }
      >
        {loading ? (
          <div
            className={
              styles.emptyState
            }
          >
            <Loader2
              size={22}
              className={
                styles.spin
              }
            />

            Loading credit notes...
          </div>
        ) : list.items.length
          === 0 ? (
          <div
            className={
              styles.emptyState
            }
          >
            <FileText size={29} />

            <strong>
              No credit notes found
            </strong>
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
                  <th>
                    Credit note
                  </th>

                  <th>
                    Return
                  </th>

                  <th>
                    Invoice
                  </th>

                  <th>
                    Customer
                  </th>

                  <th>
                    Amount
                  </th>

                  <th>
                    Status
                  </th>

                  <th>
                    Refundable
                  </th>

                  <th />
                </tr>
              </thead>

              <tbody>
                {list.items.map(
                  (item) => (
                    <tr
                      key={
                        item.id
                      }
                    >
                      <td>
                        <strong>
                          {
                            item
                              .credit_note_number
                          }
                        </strong>
                      </td>

                      <td>
                        {
                          item
                            .return_number
                        }
                      </td>

                      <td>
                        {
                          item
                            .invoice_number
                        }
                      </td>

                      <td>
                        {
                          item
                            .customer_name
                        }
                      </td>

                      <td>
                        {money(
                          item.amount,
                        )}
                      </td>

                      <td>
                        <span
                          className={
                            styles.badge
                          }
                        >
                          {readable(
                            item.status,
                          )}
                        </span>
                      </td>

                      <td>
                        <strong>
                          {money(
                            item
                              .refundable_overpayment,
                          )}
                        </strong>
                      </td>

                      <td>
                        <button
                          type="button"
                          className={
                            styles.iconButton
                          }
                          onClick={() =>
                            void openDetail(
                              item.id,
                            )
                          }
                        >
                          <Eye size={16} />
                        </button>
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        )}

        <footer
          className={
            styles.pagination
          }
        >
          <button
            type="button"
            disabled={
              page <= 1
            }
            onClick={() =>
              setPage(
                (current) =>
                  Math.max(
                    1,
                    current - 1,
                  ),
              )
            }
          >
            <ChevronLeft
              size={15}
            />

            Previous
          </button>

          <span>
            Page {list.page}
            {" of "}
            {Math.max(
              1,
              list.total_pages,
            )}
          </span>

          <button
            type="button"
            disabled={
              page
              >= list.total_pages
              || list.total_pages
                === 0
            }
            onClick={() =>
              setPage(
                (current) =>
                  current + 1,
              )
            }
          >
            Next

            <ChevronRight
              size={15}
            />
          </button>
        </footer>
      </section>


      {createOpen && (
        <div
          className={
            styles.backdrop
          }
        >
          <form
            className={
              styles.actionModal
            }
            onSubmit={
              submitCreate
            }
          >
            <header
              className={
                styles.modalHeader
              }
            >
              <div>
                <p className="eyebrow">
                  NEW CREDIT NOTE
                </p>

                <h2>
                  Create from return
                </h2>
              </div>

              <button
                type="button"
                className={
                  styles.iconButton
                }
                onClick={() =>
                  setCreateOpen(
                    false,
                  )
                }
              >
                <X size={18} />
              </button>
            </header>

            <div
              className={
                styles.modalBody
              }
            >
              <label>
                Return ID *

                <input
                  type="number"
                  min="1"
                  required
                  value={
                    createReturnId
                  }
                  onChange={
                    (event) =>
                      setCreateReturnId(
                        event
                          .target
                          .value,
                      )
                  }
                />
              </label>

              <label>
                Notes

                <textarea
                  rows={5}
                  maxLength={5000}
                  value={
                    createNotes
                  }
                  onChange={
                    (event) =>
                      setCreateNotes(
                        event
                          .target
                          .value,
                      )
                  }
                />
              </label>

              {error && (
                <div
                  className={
                    styles.errorBanner
                  }
                >
                  <CircleAlert
                    size={17}
                  />

                  {error}
                </div>
              )}
            </div>

            <footer
              className={
                styles.modalFooter
              }
            >
              <button
                type="button"
                className={
                  styles.secondaryButton
                }
                onClick={() =>
                  setCreateOpen(
                    false,
                  )
                }
              >
                Cancel
              </button>

              <button
                type="submit"
                className={
                  styles.primaryButton
                }
                disabled={
                  actionLoading
                }
              >
                {actionLoading
                  ? "Creating..."
                  : "Create credit note"
                }
              </button>
            </footer>
          </form>
        </div>
      )}


      {detailOpen && (
        <div
          className={
            styles.backdrop
          }
        >
          <aside
            className={
              styles.detailDrawer
            }
          >
            <header
              className={
                styles.modalHeader
              }
            >
              <div>
                <p className="eyebrow">
                  CREDIT NOTE
                </p>

                <h2>
                  {selected
                    ?.credit_note_number
                    ?? "Credit note"
                  }
                </h2>
              </div>

              <button
                type="button"
                className={
                  styles.iconButton
                }
                onClick={() => {
                  setDetailOpen(
                    false,
                  );

                  setSelected(
                    null,
                  );
                }}
              >
                <X size={18} />
              </button>
            </header>

            {detailLoading ? (
              <div
                className={
                  styles.emptyState
                }
              >
                <Loader2
                  size={22}
                  className={
                    styles.spin
                  }
                />

                Loading details...
              </div>
            ) : selected && (
              <>
                <div
                  className={
                    styles.detailBody
                  }
                >
                  <section
                    className={
                      styles.heroGrid
                    }
                  >
                    <div>
                      <span>
                        Customer
                      </span>

                      <strong>
                        {
                          selected
                            .customer_name
                        }
                      </strong>

                      <small>
                        {
                          selected
                            .customer_phone
                        }
                      </small>
                    </div>

                    <div>
                      <span>
                        Return
                      </span>

                      <strong>
                        {
                          selected
                            .return_number
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        Invoice
                      </span>

                      <strong>
                        {
                          selected
                            .invoice_number
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        Credit amount
                      </span>

                      <strong>
                        {money(
                          selected.amount,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Status
                      </span>

                      <strong>
                        {readable(
                          selected.status,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Refundable
                      </span>

                      <strong>
                        {money(
                          selected
                            .refundable_overpayment,
                        )}
                      </strong>
                    </div>
                  </section>


                  <section
                    className={
                      styles.financeGrid
                    }
                  >
                    <div>
                      <span>
                        Invoice total
                      </span>

                      <strong>
                        {money(
                          selected
                            .invoice_grand_total,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Invoice paid
                      </span>

                      <strong>
                        {money(
                          selected
                            .invoice_paid_amount,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Invoice balance
                      </span>

                      <strong>
                        {money(
                          selected
                            .invoice_balance_amount,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Active refunds
                      </span>

                      <strong>
                        {money(
                          selected
                            .active_refund_total,
                        )}
                      </strong>
                    </div>
                  </section>


                  <section
                    className={
                      styles.detailSection
                    }
                  >
                    <h3>
                      Reason
                    </h3>

                    <p>
                      {selected.reason}
                    </p>

                    {selected.notes && (
                      <p>
                        <strong>
                          Notes:
                        </strong>
                        {" "}
                        {selected.notes}
                      </p>
                    )}
                  </section>


                  <section
                    className={
                      styles.detailSection
                    }
                  >
                    <div
                      className={
                        styles.sectionHeader
                      }
                    >
                      <h3>
                        Customer refunds
                      </h3>

                      {selected.status
                        === "posted"
                        && numberValue(
                          selected
                            .refundable_overpayment,
                        ) > 0 && (
                        <button
                          type="button"
                          className={
                            styles.smallButton
                          }
                          onClick={
                            openRefundCreate
                          }
                        >
                          <Plus
                            size={14}
                          />

                          New refund
                        </button>
                      )}
                    </div>

                    {selected.refunds.length
                      === 0 ? (
                      <p
                        className={
                          styles.muted
                        }
                      >
                        No refunds created.
                      </p>
                    ) : (
                      <div
                        className={
                          styles.refundList
                        }
                      >
                        {selected.refunds.map(
                          (refund) => (
                            <article
                              key={
                                refund.id
                              }
                              className={
                                styles.refundCard
                              }
                            >
                              <div>
                                <span>
                                  {
                                    refund
                                      .refund_number
                                  }
                                </span>

                                <strong>
                                  {money(
                                    refund.amount,
                                  )}
                                </strong>

                                <small>
                                  {readable(
                                    refund
                                      .refund_method,
                                  )}
                                  {" • "}
                                  {readable(
                                    refund.status,
                                  )}
                                </small>
                              </div>

                              <div
                                className={
                                  styles.refundActions
                                }
                              >
                                {refund.status
                                  === "pending"
                                  && !refund
                                    .is_reversed && (
                                  <button
                                    type="button"
                                    disabled={
                                      actionLoading
                                    }
                                    onClick={() =>
                                      void submitPostRefund(
                                        refund,
                                      )
                                    }
                                  >
                                    <Send
                                      size={14}
                                    />

                                    Post
                                  </button>
                                )}

                                {refund.status
                                  === "posted"
                                  && !refund
                                    .is_reversed && (
                                  <button
                                    type="button"
                                    className={
                                      styles.dangerSmall
                                    }
                                    onClick={() =>
                                      openRefundReversal(
                                        refund,
                                      )
                                    }
                                  >
                                    <Undo2
                                      size={14}
                                    />

                                    Reverse
                                  </button>
                                )}
                              </div>
                            </article>
                          ),
                        )}
                      </div>
                    )}
                  </section>


                  {(selected
                    .approved_at
                    || selected
                      .posted_at
                    || selected
                      .reversed_at) && (
                    <section
                      className={
                        styles
                          .detailSection
                      }
                    >
                      <h3>
                        Financial history
                      </h3>

                      <div
                        className={
                          styles.history
                        }
                      >
                        {selected
                          .approved_at && (
                          <div>
                            <span>
                              Approved
                            </span>

                            <strong>
                              {dateTime(
                                selected
                                  .approved_at,
                              )}
                            </strong>
                          </div>
                        )}

                        {selected
                          .posted_at && (
                          <div>
                            <span>
                              Posted
                            </span>

                            <strong>
                              {dateTime(
                                selected
                                  .posted_at,
                              )}
                            </strong>
                          </div>
                        )}

                        {selected
                          .reversed_at && (
                          <div>
                            <span>
                              Reversed
                            </span>

                            <strong>
                              {dateTime(
                                selected
                                  .reversed_at,
                              )}
                            </strong>

                            <small>
                              {
                                selected
                                  .reversal_reason
                              }
                            </small>
                          </div>
                        )}
                      </div>
                    </section>
                  )}


                  {error && (
                    <div
                      className={
                        styles.errorBanner
                      }
                    >
                      <CircleAlert
                        size={17}
                      />

                      {error}
                    </div>
                  )}
                </div>


                <footer
                  className={
                    styles.actionBar
                  }
                >
                  {selected.status
                    === "draft" && (
                    <button
                      type="button"
                      onClick={() => {
                        setApprovalNotes(
                          "",
                        );

                        setActionMode(
                          "approve",
                        );
                      }}
                    >
                      <Check
                        size={15}
                      />

                      Approve
                    </button>
                  )}

                  {selected.status
                    === "approved" && (
                    <button
                      type="button"
                      className={
                        styles.primaryButton
                      }
                      disabled={
                        actionLoading
                      }
                      onClick={() =>
                        void submitPostCredit()
                      }
                    >
                      <Send
                        size={15}
                      />

                      {actionLoading
                        ? "Posting..."
                        : "Post credit note"
                      }
                    </button>
                  )}

                  {selected.status
                    === "posted"
                    && !selected
                      .is_reversed && (
                    <button
                      type="button"
                      className={
                        styles.dangerButton
                      }
                      onClick={() => {
                        setReversalReason(
                          "",
                        );

                        setActionMode(
                          "reverse-credit",
                        );
                      }}
                    >
                      <RotateCcw
                        size={15}
                      />

                      Reverse credit note
                    </button>
                  )}
                </footer>
              </>
            )}
          </aside>
        </div>
      )}


      {actionMode && selected && (
        <div
          className={
            styles.actionBackdrop
          }
        >
          <section
            className={
              styles.actionModal
            }
          >
            <header
              className={
                styles.modalHeader
              }
            >
              <div>
                <p className="eyebrow">
                  FINANCIAL ACTION
                </p>

                <h2>
                  {actionMode
                    === "approve"
                    ? "Approve credit note"
                    : actionMode
                        === "refund"
                      ? "Create customer refund"
                      : actionMode
                          === "reverse-refund"
                        ? "Reverse refund"
                        : "Reverse credit note"
                  }
                </h2>
              </div>

              <button
                type="button"
                className={
                  styles.iconButton
                }
                onClick={() => {
                  setActionMode(
                    null,
                  );

                  setSelectedRefund(
                    null,
                  );
                }}
              >
                <X size={18} />
              </button>
            </header>


            <div
              className={
                styles.modalBody
              }
            >
              {actionMode
                === "approve" && (
                <label>
                  Approval notes

                  <textarea
                    rows={5}
                    maxLength={5000}
                    value={
                      approvalNotes
                    }
                    onChange={
                      (event) =>
                        setApprovalNotes(
                          event
                            .target
                            .value,
                        )
                    }
                  />
                </label>
              )}


              {actionMode
                === "refund" && (
                <>
                  <div
                    className={
                      styles.infoBox
                    }
                  >
                    Available refundable
                    overpayment:
                    {" "}
                    <strong>
                      {money(
                        selected
                          .refundable_overpayment,
                      )}
                    </strong>
                  </div>

                  <label>
                    Refund amount *

                    <input
                      type="number"
                      min="0.01"
                      step="0.01"
                      value={
                        refundAmount
                      }
                      onChange={
                        (event) =>
                          setRefundAmount(
                            event
                              .target
                              .value,
                          )
                      }
                    />
                  </label>

                  <label>
                    Refund method

                    <select
                      value={
                        refundMethod
                      }
                      onChange={
                        (event) =>
                          setRefundMethod(
                            event
                              .target
                              .value,
                          )
                      }
                    >
                      <option
                        value="cash"
                      >
                        Cash
                      </option>

                      <option
                        value="card"
                      >
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

                      <option
                        value="cheque"
                      >
                        Cheque
                      </option>
                    </select>
                  </label>

                  <label>
                    Reference number

                    <input
                      maxLength={150}
                      value={
                        refundReference
                      }
                      onChange={
                        (event) =>
                          setRefundReference(
                            event
                              .target
                              .value,
                          )
                      }
                    />
                  </label>

                  <label>
                    Notes

                    <textarea
                      rows={4}
                      maxLength={5000}
                      value={
                        refundNotes
                      }
                      onChange={
                        (event) =>
                          setRefundNotes(
                            event
                              .target
                              .value,
                          )
                      }
                    />
                  </label>
                </>
              )}


              {(actionMode
                === "reverse-credit"
                || actionMode
                  === "reverse-refund") && (
                <>
                  {actionMode
                    === "reverse-refund"
                    && selectedRefund && (
                    <div
                      className={
                        styles.infoBox
                      }
                    >
                      Refund:
                      {" "}
                      <strong>
                        {
                          selectedRefund
                            .refund_number
                        }
                      </strong>
                      {" — "}
                      {money(
                        selectedRefund
                          .amount,
                      )}
                    </div>
                  )}

                  <label>
                    Reversal reason *

                    <textarea
                      rows={5}
                      value={
                        reversalReason
                      }
                      onChange={
                        (event) =>
                          setReversalReason(
                            event
                              .target
                              .value,
                          )
                      }
                    />
                  </label>
                </>
              )}


              {error && (
                <div
                  className={
                    styles.errorBanner
                  }
                >
                  <CircleAlert
                    size={17}
                  />

                  {error}
                </div>
              )}
            </div>


            <footer
              className={
                styles.modalFooter
              }
            >
              <button
                type="button"
                className={
                  styles.secondaryButton
                }
                disabled={
                  actionLoading
                }
                onClick={() => {
                  setActionMode(
                    null,
                  );

                  setSelectedRefund(
                    null,
                  );
                }}
              >
                Cancel
              </button>

              {actionMode
                === "approve" && (
                <button
                  type="button"
                  className={
                    styles.primaryButton
                  }
                  disabled={
                    actionLoading
                  }
                  onClick={() =>
                    void submitApproval()
                  }
                >
                  {actionLoading
                    ? "Approving..."
                    : "Approve credit note"
                  }
                </button>
              )}

              {actionMode
                === "refund" && (
                <button
                  type="button"
                  className={
                    styles.primaryButton
                  }
                  disabled={
                    actionLoading
                  }
                  onClick={() =>
                    void submitRefund()
                  }
                >
                  {actionLoading
                    ? "Creating..."
                    : "Create refund"
                  }
                </button>
              )}

              {actionMode
                === "reverse-credit" && (
                <button
                  type="button"
                  className={
                    styles.dangerButton
                  }
                  disabled={
                    actionLoading
                  }
                  onClick={() =>
                    void submitCreditReversal()
                  }
                >
                  Reverse credit note
                </button>
              )}

              {actionMode
                === "reverse-refund" && (
                <button
                  type="button"
                  className={
                    styles.dangerButton
                  }
                  disabled={
                    actionLoading
                  }
                  onClick={() =>
                    void submitRefundReversal()
                  }
                >
                  Reverse refund
                </button>
              )}
            </footer>
          </section>
        </div>
      )}
    </AppShell>
  );
}
