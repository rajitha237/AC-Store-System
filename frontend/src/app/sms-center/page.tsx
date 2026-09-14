"use client";

import axios from "axios";

import {
  AlertCircle,
  Ban,
  CalendarDays,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Eye,
  Loader2,
  MessageSquareText,
  RefreshCw,
  Search,
  Send,
  UserRound,
  X,
} from "lucide-react";

import {
  FormEvent,
  useCallback,
  useEffect,
  useState,
  useSyncExternalStore,
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
  getSmsNotifications,
} from "@/lib/sms-center-api";

import type {
  UserResponse,
} from "@/types/auth";

import type {
  SmsNotification,
  SmsNotificationListResponse,
} from "@/types/sms-center";

import styles from "./page.module.css";


const PAGE_SIZE = 20;


function readable(
  value:
    string
    | null
    | undefined,
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


function dateTime(
  value:
    string
    | null
    | undefined,
): string {
  if (!value) {
    return "—";
  }

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
      dateStyle:
        "medium",

      timeStyle:
        "short",
    },
  ).format(parsed);
}


function toStartIso(
  value:
    string,
): string | undefined {
  if (!value) {
    return undefined;
  }

  const parsed =
    new Date(
      `${value}T00:00:00`,
    );

  if (
    Number.isNaN(
      parsed.getTime(),
    )
  ) {
    return undefined;
  }

  return parsed.toISOString();
}


function toEndIso(
  value:
    string,
): string | undefined {
  if (!value) {
    return undefined;
  }

  const parsed =
    new Date(
      `${value}T23:59:59.999`,
    );

  if (
    Number.isNaN(
      parsed.getTime(),
    )
  ) {
    return undefined;
  }

  return parsed.toISOString();
}


function errorMessage(
  error:
    unknown,
): string {
  if (
    axios.isAxiosError(
      error,
    )
  ) {
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
      error.response
        ?.status
      === 403
    ) {
      return (
        "Your account does not "
        + "have permission to "
        + "view the SMS Center."
      );
    }
  }

  return (
    "Unable to load SMS history. "
    + "Please try again."
  );
}


function statusClass(
  status:
    string,
): string {
  switch (
    status.toLowerCase()
  ) {
    case "sent":
      return styles.statusSent;

    case "failed":
      return styles.statusFailed;

    case "pending":
      return styles.statusPending;

    case "processing":
      return styles.statusProcessing;

    case "cancelled":
      return styles.statusCancelled;

    default:
      return styles.statusDefault;
  }
}


function eventLabel(
  value:
    string,
): string {
  const labels:
    Record<string, string> = {
      customer_service_received:
        "Job Received",

      customer_service_ready:
        "Job Ready",

      installment_due_reminder:
        "Installment Reminder",

      owner_job_visit_reminder:
        "Owner Job Reminder",

      owner_daily_cash_summary:
        "Daily Cash Summary",
    };

  return (
    labels[value]
    ?? readable(value)
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


export default function SmsCenterPage() {
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

  const user =
    authSnapshot?.user
      ?? null;

  const token =
    authSnapshot?.token
      ?? null;

  const [
    data,
    setData,
  ] = useState<
    SmsNotificationListResponse
    | null
  >(null);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState<
    string | null
  >(null);

  const [
    page,
    setPage,
  ] = useState(1);

  const [
    searchInput,
    setSearchInput,
  ] = useState("");

  const [
    search,
    setSearch,
  ] = useState("");

  const [
    statusFilter,
    setStatusFilter,
  ] = useState("");

  const [
    recipientFilter,
    setRecipientFilter,
  ] = useState("");

  const [
    eventFilter,
    setEventFilter,
  ] = useState("");

  const [
    dateFrom,
    setDateFrom,
  ] = useState("");

  const [
    dateTo,
    setDateTo,
  ] = useState("");

  const [
    selected,
    setSelected,
  ] = useState<
    SmsNotification | null
  >(null);


  const loadData =
    useCallback(
      async () => {
        if (!token) {
          return;
        }

        setLoading(true);
        setError(null);

        try {
          const result =
            await getSmsNotifications(
              {
                page,
                pageSize:
                  PAGE_SIZE,

                search,

                status:
                  statusFilter,

                recipientType:
                  recipientFilter,

                eventType:
                  eventFilter,

                dateFrom:
                  toStartIso(
                    dateFrom,
                  ),

                dateTo:
                  toEndIso(
                    dateTo,
                  ),
              },
            );

          setData(
            result,
          );
        } catch (loadError) {
          setError(
            errorMessage(
              loadError,
            ),
          );
        } finally {
          setLoading(false);
        }
      },
      [
        token,
        page,
        search,
        statusFilter,
        recipientFilter,
        eventFilter,
        dateFrom,
        dateTo,
      ],
    );


  useEffect(() => {
    if (
      !hydrated
      || (
        token
        && user
      )
    ) {
      return;
    }

    clearAuthSession();

    router.replace(
      "/login",
    );
  }, [
    hydrated,
    token,
    user,
    router,
  ]);


  useEffect(() => {
    if (!token) {
      return;
    }

    queueMicrotask(
      () => {
        void loadData();
      },
    );
  }, [
    token,
    loadData,
  ]);


  function submitSearch(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setPage(1);

    setSearch(
      searchInput.trim(),
    );
  }


  function resetFilters() {
    setSearchInput("");
    setSearch("");

    setStatusFilter("");
    setRecipientFilter("");
    setEventFilter("");

    setDateFrom("");
    setDateTo("");

    setPage(1);
  }


  if (
    !hydrated
    || !token
    || !user
  ) {
    return (
      <div
        className={
          styles.fullLoader
        }
      >
        <Loader2
          size={24}
          className={
            styles.spin
          }
        />

        <span>
          {
            hydrated
              ? "Redirecting…"
              : "Loading SMS Center…"
          }
        </span>
      </div>
    );
  }


  const summary =
    data?.summary;

  return (
    <AppShell user={user}>
      <section>
        <div
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
              Communications
            </p>

            <h1>
              SMS Center
            </h1>

            <p>
              Review SMS delivery
              history, recipients,
              messages, job references,
              status and send times.
            </p>
          </div>

          <button
            type="button"
            className={
              styles.primaryButton
            }
            onClick={() =>
              void loadData()
            }
            disabled={loading}
          >
            <RefreshCw
              size={15}
              className={
                loading
                  ? styles.spin
                  : undefined
              }
            />

            Refresh
          </button>
        </div>

        <div
          className={
            styles.summaryGrid
          }
        >
          <article>
            <MessageSquareText
              size={21}
            />

            <div>
              <span>
                Total SMS
              </span>

              <strong>
                {
                  summary
                    ?.total
                  ?? 0
                }
              </strong>
            </div>
          </article>

          <article>
            <CheckCircle2
              size={21}
            />

            <div>
              <span>
                Sent
              </span>

              <strong>
                {
                  summary
                    ?.sent
                  ?? 0
                }
              </strong>
            </div>
          </article>

          <article>
            <Clock3
              size={21}
            />

            <div>
              <span>
                Pending
              </span>

              <strong>
                {
                  summary
                    ?.pending
                  ?? 0
                }
              </strong>
            </div>
          </article>

          <article>
            <AlertCircle
              size={21}
            />

            <div>
              <span>
                Failed
              </span>

              <strong>
                {
                  summary
                    ?.failed
                  ?? 0
                }
              </strong>
            </div>
          </article>

          <article>
            <Send
              size={21}
            />

            <div>
              <span>
                Sent Today
              </span>

              <strong>
                {
                  summary
                    ?.today_sent
                  ?? 0
                }
              </strong>
            </div>
          </article>

          <article>
            <Ban
              size={21}
            />

            <div>
              <span>
                Cancelled
              </span>

              <strong>
                {
                  summary
                    ?.cancelled
                  ?? 0
                }
              </strong>
            </div>
          </article>
        </div>

        <div
          className={
            styles.filterCard
          }
        >
          <form
            onSubmit={
              submitSearch
            }
          >
            <div
              className={
                styles.searchRow
              }
            >
              <div
                className={
                  styles.searchBox
                }
              >
                <Search
                  size={16}
                />

                <input
                  value={
                    searchInput
                  }
                  onChange={(
                    event,
                  ) =>
                    setSearchInput(
                      event
                        .target
                        .value,
                    )
                  }
                  placeholder={
                    "Search customer, "
                    + "phone, job or message"
                  }
                />
              </div>

              <button
                type="submit"
                className={
                  styles.primaryButton
                }
              >
                Search
              </button>

              <button
                type="button"
                className={
                  styles.secondaryButton
                }
                onClick={
                  resetFilters
                }
              >
                Clear
              </button>
            </div>

            <div
              className={
                styles.filterGrid
              }
            >
              <label>
                Status

                <select
                  value={
                    statusFilter
                  }
                  onChange={(
                    event,
                  ) => {
                    setPage(1);

                    setStatusFilter(
                      event
                        .target
                        .value,
                    );
                  }}
                >
                  <option value="">
                    All statuses
                  </option>

                  <option value="sent">
                    Sent
                  </option>

                  <option value="pending">
                    Pending
                  </option>

                  <option value="processing">
                    Processing
                  </option>

                  <option value="failed">
                    Failed
                  </option>

                  <option value="cancelled">
                    Cancelled
                  </option>
                </select>
              </label>

              <label>
                Recipient

                <select
                  value={
                    recipientFilter
                  }
                  onChange={(
                    event,
                  ) => {
                    setPage(1);

                    setRecipientFilter(
                      event
                        .target
                        .value,
                    );
                  }}
                >
                  <option value="">
                    All recipients
                  </option>

                  <option value="customer">
                    Customer
                  </option>

                  <option value="owner">
                    Owner
                  </option>
                </select>
              </label>

              <label>
                Event

                <select
                  value={
                    eventFilter
                  }
                  onChange={(
                    event,
                  ) => {
                    setPage(1);

                    setEventFilter(
                      event
                        .target
                        .value,
                    );
                  }}
                >
                  <option value="">
                    All events
                  </option>

                  <option
                    value={
                      "customer_service_received"
                    }
                  >
                    Job Received
                  </option>

                  <option
                    value={
                      "customer_service_ready"
                    }
                  >
                    Job Ready
                  </option>

                  <option
                    value={
                      "installment_due_reminder"
                    }
                  >
                    Installment Reminder
                  </option>

                  <option
                    value={
                      "owner_job_visit_reminder"
                    }
                  >
                    Owner Job Reminder
                  </option>

                  <option
                    value={
                      "owner_daily_cash_summary"
                    }
                  >
                    Daily Cash Summary
                  </option>
                </select>
              </label>

              <label>
                From Date

                <input
                  type="date"
                  value={
                    dateFrom
                  }
                  onChange={(
                    event,
                  ) => {
                    setPage(1);

                    setDateFrom(
                      event
                        .target
                        .value,
                    );
                  }}
                />
              </label>

              <label>
                To Date

                <input
                  type="date"
                  value={
                    dateTo
                  }
                  onChange={(
                    event,
                  ) => {
                    setPage(1);

                    setDateTo(
                      event
                        .target
                        .value,
                    );
                  }}
                />
              </label>
            </div>
          </form>
        </div>

        {error && (
          <div
            className={
              styles.errorBanner
            }
          >
            <AlertCircle
              size={16}
            />

            {error}
          </div>
        )}

        <div
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
                size={24}
                className={
                  styles.spin
                }
              />

              <strong>
                Loading SMS history…
              </strong>
            </div>
          ) : (
            <>
              <div
                className={
                  styles.tableWrap
                }
              >
                <table>
                  <thead>
                    <tr>
                      <th>
                        Sent / Created
                      </th>

                      <th>
                        Recipient
                      </th>

                      <th>
                        Type
                      </th>

                      <th>
                        Reference
                      </th>

                      <th>
                        Message
                      </th>

                      <th>
                        Status
                      </th>

                      <th>
                        Attempts
                      </th>

                      <th>
                        Details
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {data?.items.map(
                      (item) => (
                        <tr
                          key={
                            item.id
                          }
                        >
                          <td>
                            <strong>
                              {
                                dateTime(
                                  item.sent_at,
                                )
                              }
                            </strong>

                            <small>
                              Created{" "}
                              {
                                dateTime(
                                  item.created_at,
                                )
                              }
                            </small>
                          </td>

                          <td>
                            <strong>
                              {
                                item
                                  .recipient_name
                                ?? readable(
                                  item
                                    .recipient_type,
                                )
                              }
                            </strong>

                            <small>
                              {
                                item
                                  .recipient_phone
                              }
                            </small>
                          </td>

                          <td>
                            <span
                              className={
                                styles.eventBadge
                              }
                            >
                              {
                                eventLabel(
                                  item
                                    .event_type,
                                )
                              }
                            </span>
                          </td>

                          <td>
                            <strong>
                              {
                                item
                                  .job_number
                                ?? "—"
                              }
                            </strong>

                            <small>
                              {
                                item
                                  .customer_number
                                ?? ""
                              }
                            </small>
                          </td>

                          <td
                            className={
                              styles.messageCell
                            }
                          >
                            {
                              item.message
                            }
                          </td>

                          <td>
                            <span
                              className={
                                `${styles.statusBadge} ${
                                  statusClass(
                                    item.status,
                                  )
                                }`
                              }
                            >
                              {
                                readable(
                                  item.status,
                                )
                              }
                            </span>
                          </td>

                          <td>
                            {
                              item
                                .attempt_count
                            }
                          </td>

                          <td>
                            <button
                              type="button"
                              className={
                                styles.iconButton
                              }
                              onClick={() =>
                                setSelected(
                                  item,
                                )
                              }
                              title={
                                "View SMS details"
                              }
                            >
                              <Eye
                                size={15}
                              />
                            </button>
                          </td>
                        </tr>
                      ),
                    )}
                  </tbody>
                </table>
              </div>

              {!data?.items.length && (
                <div
                  className={
                    styles.emptyState
                  }
                >
                  <MessageSquareText
                    size={28}
                  />

                  <strong>
                    No SMS records found
                  </strong>

                  <span>
                    Try changing the
                    filters or date range.
                  </span>
                </div>
              )}

              <div
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
                    size={14}
                  />

                  Previous
                </button>

                <span>
                  Page{" "}
                  {data?.page ?? page}
                  {" of "}
                  {
                    Math.max(
                      data
                        ?.total_pages
                      ?? 0,
                      1,
                    )
                  }
                  {" · "}
                  {data?.total ?? 0}
                  {" records"}
                </span>

                <button
                  type="button"
                  disabled={
                    !data
                    || page
                      >= data
                        .total_pages
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
                    size={14}
                  />
                </button>
              </div>
            </>
          )}
        </div>

        {selected && (
          <div
            className={
              styles.backdrop
            }
            role="presentation"
            onMouseDown={() =>
              setSelected(null)
            }
          >
            <aside
              className={
                styles.detailDrawer
              }
              onMouseDown={(
                event,
              ) =>
                event.stopPropagation()
              }
            >
              <header
                className={
                  styles.drawerHeader
                }
              >
                <div>
                  <p
                    className={
                      styles.eyebrow
                    }
                  >
                    SMS Record
                  </p>

                  <h2>
                    SMS #
                    {selected.id}
                  </h2>
                </div>

                <button
                  type="button"
                  className={
                    styles.iconButton
                  }
                  onClick={() =>
                    setSelected(null)
                  }
                  aria-label={
                    "Close details"
                  }
                >
                  <X
                    size={17}
                  />
                </button>
              </header>

              <div
                className={
                  styles.drawerBody
                }
              >
                <div
                  className={
                    styles.detailGrid
                  }
                >
                  <div>
                    <UserRound
                      size={17}
                    />

                    <span>
                      Recipient
                    </span>

                    <strong>
                      {
                        selected
                          .recipient_name
                        ?? readable(
                          selected
                            .recipient_type,
                        )
                      }
                    </strong>

                    <small>
                      {
                        selected
                          .recipient_phone
                      }
                    </small>
                  </div>

                  <div>
                    <CheckCircle2
                      size={17}
                    />

                    <span>
                      Status
                    </span>

                    <strong>
                      {
                        readable(
                          selected
                            .status,
                        )
                      }
                    </strong>

                    <small>
                      {
                        selected
                          .attempt_count
                      }
                      {" attempt(s)"}
                    </small>
                  </div>

                  <div>
                    <CalendarDays
                      size={17}
                    />

                    <span>
                      Sent At
                    </span>

                    <strong>
                      {
                        dateTime(
                          selected
                            .sent_at,
                        )
                      }
                    </strong>

                    <small>
                      Created{" "}
                      {
                        dateTime(
                          selected
                            .created_at,
                        )
                      }
                    </small>
                  </div>
                </div>

                <section
                  className={
                    styles.detailSection
                  }
                >
                  <h3>
                    Message
                  </h3>

                  <div
                    className={
                      styles.messageBox
                    }
                  >
                    {
                      selected
                        .message
                    }
                  </div>
                </section>

                <section
                  className={
                    styles.detailSection
                  }
                >
                  <h3>
                    Reference Details
                  </h3>

                  <dl
                    className={
                      styles.definitionGrid
                    }
                  >
                    <div>
                      <dt>
                        Event Type
                      </dt>

                      <dd>
                        {
                          eventLabel(
                            selected
                              .event_type,
                          )
                        }
                      </dd>
                    </div>

                    <div>
                      <dt>
                        Job Number
                      </dt>

                      <dd>
                        {
                          selected
                            .job_number
                          ?? "—"
                        }
                      </dd>
                    </div>

                    <div>
                      <dt>
                        Customer Number
                      </dt>

                      <dd>
                        {
                          selected
                            .customer_number
                          ?? "—"
                        }
                      </dd>
                    </div>

                    <div>
                      <dt>
                        Provider ID
                      </dt>

                      <dd>
                        {
                          selected
                            .provider_message_id
                          ?? "—"
                        }
                      </dd>
                    </div>

                    <div>
                      <dt>
                        Scheduled For
                      </dt>

                      <dd>
                        {
                          dateTime(
                            selected
                              .scheduled_for,
                          )
                        }
                      </dd>
                    </div>

                    <div>
                      <dt>
                        Last Error
                      </dt>

                      <dd>
                        {
                          selected
                            .last_error
                          ?? "—"
                        }
                      </dd>
                    </div>
                  </dl>
                </section>
              </div>
            </aside>
          </div>
        )}
      </section>
    </AppShell>
  );
}
