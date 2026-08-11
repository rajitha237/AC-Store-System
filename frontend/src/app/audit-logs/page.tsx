"use client";

import axios from "axios";

import {
  Activity,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  ClipboardList,
  Clock3,
  Eye,
  FileJson2,
  FilterX,
  History,
  Loader2,
  Network,
  RefreshCw,
  Search,
  ShieldCheck,
  UserRound,
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
  getAuditLogs,
} from "@/lib/audit-logs-api";

import type {
  UserResponse,
} from "@/types/auth";

import type {
  AuditLogResponse,
} from "@/types/audit-logs";

import styles from "./audit-logs.module.css";


const PAGE_SIZE = 20;


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


function dateTime(
  value:
    string | null | undefined,
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
        "medium",
    },
  ).format(parsed);
}


function shortDateTime(
  value:
    string,
): string {
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
      month:
        "short",

      day:
        "2-digit",

      hour:
        "2-digit",

      minute:
        "2-digit",
    },
  ).format(parsed);
}


function optionalPositiveId(
  value:
    string,
): number | undefined {
  if (!value.trim()) {
    return undefined;
  }

  const parsed =
    Number(value);

  if (
    !Number.isInteger(parsed)
    || parsed <= 0
  ) {
    return undefined;
  }

  return parsed;
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


function apiError(
  error:
    unknown,
): string {
  if (
    !axios.isAxiosError(
      error,
    )
  ) {
    return (
      "Something went wrong while "
      + "loading the audit trail."
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
    error.response?.status
    === 403
  ) {
    return (
      "Your account does not have "
      + "permission to view audit logs."
    );
  }

  return (
    "Unable to load audit logs. "
    + "Please try again."
  );
}


function normalizeAuditData(
  value:
    unknown,
): unknown {
  if (
    typeof value
    !== "string"
  ) {
    return value;
  }

  const trimmed =
    value.trim();

  if (!trimmed) {
    return null;
  }

  try {
    return JSON.parse(
      trimmed,
    ) as unknown;
  } catch {
    return value;
  }
}


function formattedJson(
  value:
    unknown,
): string {
  const normalized =
    normalizeAuditData(
      value,
    );

  if (
    normalized === null
    || normalized === undefined
  ) {
    return "No data";
  }

  if (
    typeof normalized
    === "string"
  ) {
    return normalized;
  }

  try {
    return JSON.stringify(
      normalized,
      null,
      2,
    );
  } catch {
    return String(
      normalized,
    );
  }
}


function objectKeys(
  value:
    unknown,
): string[] {
  const normalized =
    normalizeAuditData(
      value,
    );

  if (
    normalized === null
    || typeof normalized
      !== "object"
    || Array.isArray(
      normalized,
    )
  ) {
    return [];
  }

  return Object.keys(
    normalized,
  );
}


function changedFieldCount(
  before:
    unknown,

  after:
    unknown,
): number {
  const beforeData =
    normalizeAuditData(
      before,
    );

  const afterData =
    normalizeAuditData(
      after,
    );

  if (
    beforeData === null
    || afterData === null
    || typeof beforeData
      !== "object"
    || typeof afterData
      !== "object"
    || Array.isArray(
      beforeData,
    )
    || Array.isArray(
      afterData,
    )
  ) {
    return 0;
  }

  const beforeRecord =
    beforeData as
      Record<
        string,
        unknown
      >;

  const afterRecord =
    afterData as
      Record<
        string,
        unknown
      >;

  const keys =
    new Set([
      ...Object.keys(
        beforeRecord,
      ),

      ...Object.keys(
        afterRecord,
      ),
    ]);

  let changed =
    0;

  for (
    const key
    of keys
  ) {
    if (
      JSON.stringify(
        beforeRecord[key],
      )
      !==
      JSON.stringify(
        afterRecord[key],
      )
    ) {
      changed += 1;
    }
  }

  return changed;
}


export default function AuditLogsPage() {
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
    logs,
    setLogs,
  ] =
    useState<
      AuditLogResponse[]
    >(
      [],
    );

  const [
    total,
    setTotal,
  ] =
    useState(0);

  const [
    totalPages,
    setTotalPages,
  ] =
    useState(0);

  const [
    page,
    setPage,
  ] =
    useState(1);

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
    moduleFilter,
    setModuleFilter,
  ] =
    useState("");

  const [
    actionFilter,
    setActionFilter,
  ] =
    useState("");

  const [
    entityTypeFilter,
    setEntityTypeFilter,
  ] =
    useState("");

  const [
    entityIdInput,
    setEntityIdInput,
  ] =
    useState("");

  const [
    userIdInput,
    setUserIdInput,
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
    selected,
    setSelected,
  ] =
    useState<
      AuditLogResponse
      | null
    >(
      null,
    );

  const [
    detailOpen,
    setDetailOpen,
  ] =
    useState(false);


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


  const loadAuditLogs =
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
            await getAuditLogs({
              page,

              pageSize:
                PAGE_SIZE,

              search:
                search
                || undefined,

              module:
                moduleFilter
                  .trim()
                || undefined,

              action:
                actionFilter
                  .trim()
                || undefined,

              entityType:
                entityTypeFilter
                  .trim()
                || undefined,

              entityId:
                optionalPositiveId(
                  entityIdInput,
                ),

              userId:
                optionalPositiveId(
                  userIdInput,
                ),

              dateFrom:
                toStartIso(
                  dateFrom,
                ),

              dateTo:
                toEndIso(
                  dateTo,
                ),
            });

          setLogs(
            result.items,
          );

          setTotal(
            result.total,
          );

          setTotalPages(
            result.total_pages,
          );
        } catch (
          requestError
        ) {
          setError(
            apiError(
              requestError,
            ),
          );

          setLogs(
            [],
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
        moduleFilter,
        actionFilter,
        entityTypeFilter,
        entityIdInput,
        userIdInput,
        dateFrom,
        dateTo,
      ],
    );


  useEffect(() => {
    if (authLoading) {
      return;
    }

    const timer =
      window.setTimeout(
        () => {
          void loadAuditLogs();
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
    loadAuditLogs,
  ]);


  const summary =
    useMemo(
      () => {
        const modules =
          new Set(
            logs.map(
              (log) =>
                log.module,
            ),
          );

        const users =
          new Set(
            logs
              .map(
                (log) =>
                  log.user_id,
              )
              .filter(
                (
                  value,
                ): value is number =>
                  value !== null,
              ),
          );

        const changes =
          logs.filter(
            (log) =>
              log.before_data
                !== null
              && log.before_data
                !== undefined
              && log.after_data
                !== null
              && log.after_data
                !== undefined,
          ).length;

        return {
          modules:
            modules.size,

          users:
            users.size,

          changes,
        };
      },
      [logs],
    );


  const moduleSuggestions =
    useMemo(
      () =>
        Array.from(
          new Set(
            logs.map(
              (log) =>
                log.module,
            ),
          ),
        ).sort(),
      [logs],
    );


  const actionSuggestions =
    useMemo(
      () =>
        Array.from(
          new Set(
            logs.map(
              (log) =>
                log.action,
            ),
          ),
        ).sort(),
      [logs],
    );


  const entitySuggestions =
    useMemo(
      () =>
        Array.from(
          new Set(
            logs.map(
              (log) =>
                log.entity_type,
            ),
          ),
        ).sort(),
      [logs],
    );


  function submitSearch(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setPage(1);

    setSearch(
      searchInput
        .trim()
        .slice(
          0,
          150,
        ),
    );
  }


  function clearFilters() {
    setSearchInput(
      "",
    );

    setSearch(
      "",
    );

    setModuleFilter(
      "",
    );

    setActionFilter(
      "",
    );

    setEntityTypeFilter(
      "",
    );

    setEntityIdInput(
      "",
    );

    setUserIdInput(
      "",
    );

    setDateFrom(
      "",
    );

    setDateTo(
      "",
    );

    setPage(1);
  }


  function openDetail(
    log:
      AuditLogResponse,
  ) {
    setSelected(
      log,
    );

    setDetailOpen(
      true,
    );
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
            SECURITY & CONTROL
          </p>

          <h1>
            Audit Logs
          </h1>

          <p>
            Review system activity,
            user actions, financial and
            inventory changes, entity
            history and before/after
            snapshots.
          </p>
        </div>

        <button
          type="button"
          className={
            styles.secondaryButton
          }
          disabled={
            refreshing
          }
          onClick={() =>
            void loadAuditLogs(
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
      </section>


      <section
        className={
          styles.summaryGrid
        }
      >
        <article>
          <History size={20} />

          <div>
            <span>
              Total records
            </span>

            <strong>
              {total}
            </strong>
          </div>
        </article>

        <article>
          <ClipboardList
            size={20}
          />

          <div>
            <span>
              Modules loaded
            </span>

            <strong>
              {summary.modules}
            </strong>
          </div>
        </article>

        <article>
          <UserRound size={20} />

          <div>
            <span>
              Users loaded
            </span>

            <strong>
              {summary.users}
            </strong>
          </div>
        </article>

        <article>
          <Activity size={20} />

          <div>
            <span>
              Snapshot changes
            </span>

            <strong>
              {summary.changes}
            </strong>
          </div>
        </article>
      </section>


      <section
        className={
          styles.filterCard
        }
      >
        <form
          className={
            styles.searchRow
          }
          onSubmit={
            submitSearch
          }
        >
          <div
            className={
              styles.searchBox
            }
          >
            <Search size={16} />

            <input
              value={
                searchInput
              }
              maxLength={150}
              placeholder={
                "Search descriptions, references, users or actions..."
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
              clearFilters
            }
          >
            <FilterX size={15} />

            Clear
          </button>
        </form>


        <div
          className={
            styles.filterGrid
          }
        >
          <label>
            Module

            <input
              list="audit-module-options"
              value={
                moduleFilter
              }
              maxLength={100}
              placeholder="inventory"
              onChange={
                (event) => {
                  setPage(1);

                  setModuleFilter(
                    event
                      .target
                      .value,
                  );
                }
              }
            />

            <datalist
              id="audit-module-options"
            >
              {moduleSuggestions.map(
                (value) => (
                  <option
                    key={value}
                    value={value}
                  />
                ),
              )}
            </datalist>
          </label>


          <label>
            Action

            <input
              list="audit-action-options"
              value={
                actionFilter
              }
              maxLength={100}
              placeholder="invoice_confirmed"
              onChange={
                (event) => {
                  setPage(1);

                  setActionFilter(
                    event
                      .target
                      .value,
                  );
                }
              }
            />

            <datalist
              id="audit-action-options"
            >
              {actionSuggestions.map(
                (value) => (
                  <option
                    key={value}
                    value={value}
                  />
                ),
              )}
            </datalist>
          </label>


          <label>
            Entity type

            <input
              list="audit-entity-options"
              value={
                entityTypeFilter
              }
              maxLength={100}
              placeholder="sales_invoice"
              onChange={
                (event) => {
                  setPage(1);

                  setEntityTypeFilter(
                    event
                      .target
                      .value,
                  );
                }
              }
            />

            <datalist
              id="audit-entity-options"
            >
              {entitySuggestions.map(
                (value) => (
                  <option
                    key={value}
                    value={value}
                  />
                ),
              )}
            </datalist>
          </label>


          <label>
            Entity ID

            <input
              type="number"
              min="1"
              value={
                entityIdInput
              }
              placeholder="Any"
              onChange={
                (event) => {
                  setPage(1);

                  setEntityIdInput(
                    event
                      .target
                      .value,
                  );
                }
              }
            />
          </label>


          <label>
            User ID

            <input
              type="number"
              min="1"
              value={
                userIdInput
              }
              placeholder="Any"
              onChange={
                (event) => {
                  setPage(1);

                  setUserIdInput(
                    event
                      .target
                      .value,
                  );
                }
              }
            />
          </label>


          <label>
            From date

            <input
              type="date"
              value={
                dateFrom
              }
              onChange={
                (event) => {
                  setPage(1);

                  setDateFrom(
                    event
                      .target
                      .value,
                  );
                }
              }
            />
          </label>


          <label>
            To date

            <input
              type="date"
              value={
                dateTo
              }
              onChange={
                (event) => {
                  setPage(1);

                  setDateTo(
                    event
                      .target
                      .value,
                  );
                }
              }
            />
          </label>
        </div>
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
              size={23}
              className={
                styles.spin
              }
            />

            Loading audit trail...
          </div>
        ) : logs.length === 0 ? (
          <div
            className={
              styles.emptyState
            }
          >
            <ShieldCheck
              size={30}
            />

            <strong>
              No audit records found
            </strong>

            <span>
              Try changing the filters
              or date range.
            </span>
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
                    Time
                  </th>

                  <th>
                    User
                  </th>

                  <th>
                    Module
                  </th>

                  <th>
                    Action
                  </th>

                  <th>
                    Entity
                  </th>

                  <th>
                    Description
                  </th>

                  <th>
                    Changes
                  </th>

                  <th />
                </tr>
              </thead>

              <tbody>
                {logs.map(
                  (log) => {
                    const changed =
                      changedFieldCount(
                        log.before_data,
                        log.after_data,
                      );

                    return (
                      <tr
                        key={log.id}
                      >
                        <td>
                          <strong>
                            {shortDateTime(
                              log.created_at,
                            )}
                          </strong>
                        </td>

                        <td>
                          <strong>
                            {log.user_full_name
                              || log.username
                              || (
                                log.user_id
                                  ? `User #${log.user_id}`
                                  : "System"
                              )
                            }
                          </strong>

                          {log.username
                            && log.user_full_name && (
                            <small>
                              @{log.username}
                            </small>
                          )}
                        </td>

                        <td>
                          <span
                            className={
                              styles.moduleBadge
                            }
                          >
                            {readable(
                              log.module,
                            )}
                          </span>
                        </td>

                        <td>
                          <strong>
                            {readable(
                              log.action,
                            )}
                          </strong>
                        </td>

                        <td>
                          <strong>
                            {readable(
                              log.entity_type,
                            )}
                          </strong>

                          <small>
                            {log.entity_reference
                              || (
                                log.entity_id
                                  ? `#${log.entity_id}`
                                  : "—"
                              )
                            }
                          </small>
                        </td>

                        <td
                          className={
                            styles.descriptionCell
                          }
                        >
                          {
                            log.description
                          }
                        </td>

                        <td>
                          {changed > 0 ? (
                            <span
                              className={
                                styles.changeBadge
                              }
                            >
                              {changed} changed
                            </span>
                          ) : (
                            <span
                              className={
                                styles.noChange
                              }
                            >
                              —
                            </span>
                          )}
                        </td>

                        <td>
                          <button
                            type="button"
                            className={
                              styles.iconButton
                            }
                            aria-label={
                              "View audit log"
                            }
                            onClick={() =>
                              openDetail(
                                log,
                              )
                            }
                          >
                            <Eye size={16} />
                          </button>
                        </td>
                      </tr>
                    );
                  },
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
            Page {page}
            {" of "}
            {Math.max(
              1,
              totalPages,
            )}
            {" • "}
            {total} records
          </span>

          <button
            type="button"
            disabled={
              page >= totalPages
              || totalPages === 0
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


      {detailOpen && selected && (
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
                styles.drawerHeader
              }
            >
              <div>
                <p className="eyebrow">
                  AUDIT RECORD
                </p>

                <h2>
                  #{selected.id}
                  {" · "}
                  {readable(
                    selected.action,
                  )}
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


            <div
              className={
                styles.drawerBody
              }
            >
              <section
                className={
                  styles.heroGrid
                }
              >
                <div>
                  <Clock3 size={15} />

                  <span>
                    Timestamp
                  </span>

                  <strong>
                    {dateTime(
                      selected.created_at,
                    )}
                  </strong>
                </div>

                <div>
                  <UserRound
                    size={15}
                  />

                  <span>
                    Actor
                  </span>

                  <strong>
                    {selected.user_full_name
                      || selected.username
                      || "System"
                    }
                  </strong>

                  <small>
                    {selected.user_id
                      ? `User #${selected.user_id}`
                      : "No user ID"
                    }
                  </small>
                </div>

                <div>
                  <Network size={15} />

                  <span>
                    IP address
                  </span>

                  <strong>
                    {selected.ip_address
                      || "Not recorded"
                    }
                  </strong>
                </div>
              </section>


              <section
                className={
                  styles.contextGrid
                }
              >
                <div>
                  <span>
                    Module
                  </span>

                  <strong>
                    {readable(
                      selected.module,
                    )}
                  </strong>
                </div>

                <div>
                  <span>
                    Action
                  </span>

                  <strong>
                    {readable(
                      selected.action,
                    )}
                  </strong>
                </div>

                <div>
                  <span>
                    Entity type
                  </span>

                  <strong>
                    {readable(
                      selected.entity_type,
                    )}
                  </strong>
                </div>

                <div>
                  <span>
                    Entity
                  </span>

                  <strong>
                    {selected.entity_reference
                      || (
                        selected.entity_id
                          ? `#${selected.entity_id}`
                          : "—"
                      )
                    }
                  </strong>
                </div>
              </section>


              <section
                className={
                  styles.detailSection
                }
              >
                <h3>
                  Description
                </h3>

                <p
                  className={
                    styles.description
                  }
                >
                  {
                    selected.description
                  }
                </p>
              </section>


              <section
                className={
                  styles.detailSection
                }
              >
                <div
                  className={
                    styles.sectionTitle
                  }
                >
                  <h3>
                    Before / After
                  </h3>

                  <span>
                    {changedFieldCount(
                      selected.before_data,
                      selected.after_data,
                    )}
                    {" changed fields"}
                  </span>
                </div>

                <div
                  className={
                    styles.snapshotGrid
                  }
                >
                  <article>
                    <header>
                      Before snapshot
                    </header>

                    <pre>
                      {formattedJson(
                        selected.before_data,
                      )}
                    </pre>
                  </article>

                  <article>
                    <header>
                      After snapshot
                    </header>

                    <pre>
                      {formattedJson(
                        selected.after_data,
                      )}
                    </pre>
                  </article>
                </div>
              </section>


              <section
                className={
                  styles.detailSection
                }
              >
                <div
                  className={
                    styles.sectionTitle
                  }
                >
                  <h3>
                    Metadata
                  </h3>

                  <span>
                    {objectKeys(
                      selected.metadata,
                    ).length}
                    {" fields"}
                  </span>
                </div>

                <div
                  className={
                    styles.metadataBox
                  }
                >
                  <FileJson2
                    size={17}
                  />

                  <pre>
                    {formattedJson(
                      selected.metadata,
                    )}
                  </pre>
                </div>
              </section>
            </div>
          </aside>
        </div>
      )}
    </AppShell>
  );
}
