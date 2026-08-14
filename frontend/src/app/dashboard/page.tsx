"use client";

import {
  Boxes,
  CircleDollarSign,
  ClipboardCheck,
  CreditCard,
  PackageCheck,
  ShoppingCart,
  TrendingUp,
  Users,
  Wrench,
} from "lucide-react";

import {
  useEffect,
  useState,
} from "react";

import { useRouter } from "next/navigation";

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

import { api } from "@/lib/api";

import type {
  UserResponse,
} from "@/types/auth";

import type {
  SalesInvoiceListResponse,
  SalesInvoiceResponse,
} from "@/types/sales";

type DashboardSalesMetrics = {
  todaySales: number;
  outstanding: number;
  invoiceCount: number;
};

type DashboardOperationalMetrics = {
  products: number;
  openServices: number;
};

type DashboardActivity = {
  id: string;
  title: string;
  detail: string;
  timestamp: string;
  href: string;
};

type UnknownRecord =
  Record<string, unknown>;

const emptySalesMetrics: DashboardSalesMetrics = {
  todaySales: 0,
  outstanding: 0,
  invoiceCount: 0,
};

const emptyOperationalMetrics:
DashboardOperationalMetrics = {
  products: 0,
  openServices: 0,
};

function asRecord(
  value: unknown,
): UnknownRecord {
  if (
    value !== null
    && typeof value === "object"
    && !Array.isArray(value)
  ) {
    return value as UnknownRecord;
  }

  return {};
}

function asArray(
  value: unknown,
): unknown[] {
  if (Array.isArray(value)) {
    return value;
  }

  const record = asRecord(value);

  if (Array.isArray(record.items)) {
    return record.items;
  }

  return [];
}

function asString(
  value: unknown,
  fallback = "",
): string {
  return (
    typeof value === "string"
      ? value
      : fallback
  );
}

function asNumber(
  value: unknown,
): number {
  const parsed = Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : 0;
}

function parseMoney(
  value: string | number | null | undefined,
): number {
  const parsed =
    Number.parseFloat(String(value ?? 0));

  return Number.isFinite(parsed)
    ? parsed
    : 0;
}

function localDateKey(
  value: string,
): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const year = date.getFullYear();

  const month = String(
    date.getMonth() + 1,
  ).padStart(2, "0");

  const day = String(
    date.getDate(),
  ).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function todayLocalDateKey(): string {
  const now = new Date();

  const year = now.getFullYear();

  const month = String(
    now.getMonth() + 1,
  ).padStart(2, "0");

  const day = String(
    now.getDate(),
  ).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function formatLkr(
  value: number,
): string {
  return `LKR ${value.toLocaleString(
    "en-LK",
    {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    },
  )}`;
}

function formatActivityTime(
  value: string,
): string {
  if (!value) {
    return "";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toLocaleString(
    "en-LK",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  );
}

function activityTimestamp(
  record: UnknownRecord,
): string {
  const candidates = [
    record.updated_at,
    record.created_at,
    record.invoice_date,
    record.start_date,
    record.first_due_date,
  ];

  for (const value of candidates) {
    if (
      typeof value === "string"
      && value.trim()
    ) {
      return value;
    }
  }

  return "";
}

function buildCards(
  salesMetrics: DashboardSalesMetrics,
  operationalMetrics:
    DashboardOperationalMetrics,
  dashboardLoading: boolean,
) {
  const todaySalesValue =
    dashboardLoading
      ? "Loading..."
      : formatLkr(
          salesMetrics.todaySales,
        );

  const outstandingValue =
    dashboardLoading
      ? "Loading..."
      : formatLkr(
          salesMetrics.outstanding,
        );

  return [
    {
      label: "Today's Sales",
      value: todaySalesValue,
      note:
        dashboardLoading
          ? "Loading confirmed sales"
          : `${
              salesMetrics.invoiceCount
            } confirmed invoice${
              salesMetrics.invoiceCount === 1
                ? ""
                : "s"
            } today`,
      icon: ShoppingCart,
    },
    {
      label: "Outstanding",
      value: outstandingValue,
      note: "Confirmed invoice balances",
      icon: CircleDollarSign,
    },
    {
      label: "Products",
      value:
        dashboardLoading
          ? "Loading..."
          : operationalMetrics.products
              .toLocaleString("en-LK"),
      note: "Active inventory catalog",
      icon: Boxes,
    },
    {
      label: "Open Services",
      value:
        dashboardLoading
          ? "Loading..."
          : operationalMetrics.openServices
              .toLocaleString("en-LK"),
      note: "Active job cards",
      icon: Wrench,
    },
  ];
}

export default function DashboardPage() {
  const router = useRouter();

  const [
    user,
    setUser,
  ] = useState<UserResponse | null>(
    null,
  );

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    dashboardLoading,
    setDashboardLoading,
  ] = useState(true);

  const [
    salesMetrics,
    setSalesMetrics,
  ] = useState<DashboardSalesMetrics>(
    emptySalesMetrics,
  );

  const [
    operationalMetrics,
    setOperationalMetrics,
  ] = useState<DashboardOperationalMetrics>(
    emptyOperationalMetrics,
  );

  const [
    recentActivity,
    setRecentActivity,
  ] = useState<DashboardActivity[]>([]);

  const [
    dashboardError,
    setDashboardError,
  ] = useState<string | null>(
    null,
  );

  useEffect(() => {
    async function load() {
      const token =
        getAccessToken();

      if (!token) {
        router.replace("/login");
        return;
      }

      const cached =
        getStoredUser();

      if (cached) {
        setUser(cached);
      }

      try {
        const current =
          await getCurrentUser();

        setStoredUser(current);
        setUser(current);

        try {
          const invoices:
            SalesInvoiceResponse[] = [];

          let salesPage = 1;
          let salesTotalPages = 1;

          do {
            const response =
              await api.get<
                SalesInvoiceListResponse
              >(
                "/sales/invoices",
                {
                  params: {
                    page: salesPage,
                    page_size: 100,
                  },
                },
              );

            invoices.push(
              ...response.data.items,
            );

            salesTotalPages =
              Math.max(
                1,
                response.data.total_pages,
              );

            salesPage += 1;
          } while (
            salesPage <= salesTotalPages
          );

          const confirmed =
            invoices.filter(
              (invoice) =>
                invoice.invoice_status
                === "confirmed",
            );

          const today =
            todayLocalDateKey();

          const todayInvoices =
            confirmed.filter(
              (invoice) =>
                localDateKey(
                  invoice.invoice_date,
                ) === today,
            );

          const todaySales =
            todayInvoices.reduce(
              (sum, invoice) =>
                sum
                + parseMoney(
                    invoice.grand_total,
                  ),
              0,
            );

          const outstanding =
            confirmed.reduce(
              (sum, invoice) =>
                sum
                + parseMoney(
                    invoice.balance_amount,
                  ),
              0,
            );

          setSalesMetrics({
            todaySales,
            outstanding,
            invoiceCount:
              todayInvoices.length,
          });

          const [
            productsResponse,
            servicesResponse,
            installmentsResponse,
          ] = await Promise.all([
            api.get<unknown>(
              "/catalog/products",
              {
                params: {
                  page: 1,
                  page_size: 100,
                  is_active: true,
                },
              },
            ),

            api.get<unknown>(
              "/service/jobs",
              {
                params: {
                  page: 1,
                  page_size: 100,
                },
              },
            ),

            api.get<unknown>(
              "/installments",
              {
                params: {
                  page: 1,
                  page_size: 100,
                },
              },
            ),
          ]);

          const productBody =
            asRecord(
              productsResponse.data,
            );

          const products =
            asArray(
              productsResponse.data,
            );

          const productCount =
            typeof productBody.total
              === "number"
              ? productBody.total
              : products.length;

          const services =
            asArray(
              servicesResponse.data,
            );

          const openServices =
            services.filter(
              (raw) => {
                const item =
                  asRecord(raw);

                const status =
                  asString(
                    item.status,
                  ).toLowerCase();

                return (
                  status !== "delivered"
                  && status !== "cancelled"
                  && status !== "completed"
                  && status !== "closed"
                );
              },
            );

          setOperationalMetrics({
            products: productCount,
            openServices:
              openServices.length,
          });

          const activities:
            DashboardActivity[] = [];

          for (
            const invoice
            of invoices.slice(0, 10)
          ) {
            const invoiceRecord =
              invoice as unknown as UnknownRecord;

            activities.push({
              id:
                `sale-${invoice.id}`,
              title:
                `Sale ${
                  invoice.invoice_number
                  || `#${invoice.id}`
                }`,
              detail:
                `${
                  invoice.payment_status
                  || "payment"
                } · ${
                  formatLkr(
                    parseMoney(
                      invoice.grand_total,
                    ),
                  )
                }`,
              timestamp:
                activityTimestamp(
                  invoiceRecord,
                ),
              href: "/sales",
            });
          }

          for (
            const raw
            of services.slice(0, 10)
          ) {
            const item =
              asRecord(raw);

            const id =
              asNumber(item.id);

            if (id <= 0) {
              continue;
            }

            const jobNumber =
              asString(
                item.job_number,
                `Job #${id}`,
              );

            const status =
              asString(
                item.status,
                "service",
              );

            activities.push({
              id: `service-${id}`,
              title:
                `Service ${jobNumber}`,
              detail:
                `Status: ${status.replaceAll(
                  "_",
                  " ",
                )}`,
              timestamp:
                activityTimestamp(item),
              href: "/service-jobs",
            });
          }

          const installments =
            asArray(
              installmentsResponse.data,
            );

          for (
            const raw
            of installments.slice(0, 10)
          ) {
            const item =
              asRecord(raw);

            const id =
              asNumber(item.id);

            if (id <= 0) {
              continue;
            }

            const agreement =
              asString(
                item.agreement_number,
                `Plan #${id}`,
              );

            const status =
              asString(
                item.status,
                "installment",
              );

            activities.push({
              id:
                `installment-${id}`,
              title:
                `Installment ${agreement}`,
              detail:
                `Status: ${status.replaceAll(
                  "_",
                  " ",
                )}`,
              timestamp:
                activityTimestamp(item),
              href: "/installments",
            });
          }

          activities.sort(
            (a, b) => {
              const aTime =
                new Date(
                  a.timestamp,
                ).getTime();

              const bTime =
                new Date(
                  b.timestamp,
                ).getTime();

              const safeA =
                Number.isFinite(aTime)
                  ? aTime
                  : 0;

              const safeB =
                Number.isFinite(bTime)
                  ? bTime
                  : 0;

              return safeB - safeA;
            },
          );

          setRecentActivity(
            activities.slice(0, 7),
          );

          setDashboardError(null);
        } catch (error) {
          console.error(
            "Dashboard live data load failed",
            error,
          );

          setDashboardError(
            "Some live dashboard data could not be loaded.",
          );
        } finally {
          setDashboardLoading(false);
        }
      } catch {
        clearAuthSession();
        router.replace("/login");
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [router]);

  if (loading && !user) {
    return (
      <main className="page-center">
        <div className="loading-spinner" />
      </main>
    );
  }

  if (!user) {
    return null;
  }

  const cards =
    buildCards(
      salesMetrics,
      operationalMetrics,
      dashboardLoading,
    );

  const navigate =
    (href: string) => {
      router.push(href);
    };

  return (
    <AppShell user={user}>
      <section className="dashboard-heading">
        <div>
          <p className="eyebrow">
            OVERVIEW
          </p>

          <h1>
            Welcome back,{" "}
            {user.full_name.split(" ")[0]}
          </h1>

          <p>
            Here&apos;s a quick view of
            your store operations.
          </p>
        </div>

        <div className="dashboard-status">
          <span className="status-dot" />
          System operational
        </div>
      </section>

      {dashboardError ? (
        <div
          role="status"
          style={{
            marginBottom: "1rem",
            opacity: 0.8,
          }}
        >
          {dashboardError}
        </div>
      ) : null}

      <section className="metric-grid">
        {cards.map((card) => {
          const Icon = card.icon;

          return (
            <article
              key={card.label}
              className="metric-card"
            >
              <div className="metric-icon">
                <Icon size={22} />
              </div>

              <div className="metric-copy">
                <span>
                  {card.label}
                </span>

                <strong>
                  {card.value}
                </strong>

                <small>
                  {card.note}
                </small>
              </div>
            </article>
          );
        })}
      </section>

      <section className="dashboard-grid">
        <article className="dashboard-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">
                OPERATIONS
              </p>

              <h2>
                Quick actions
              </h2>
            </div>
          </div>

          <div className="quick-action-grid">
            <button
              type="button"
              onClick={() =>
                navigate("/quick-sale")
              }
            >
              <ShoppingCart size={20} />
              New sale
            </button>

            <button
              type="button"
              onClick={() =>
                navigate("/customers")
              }
            >
              <Users size={20} />
              Add customer
            </button>

            <button
              type="button"
              onClick={() =>
                navigate("/inventory")
              }
            >
              <PackageCheck size={20} />
              Receive stock
            </button>

            <button
              type="button"
              onClick={() =>
                navigate("/service-jobs")
              }
            >
              <ClipboardCheck size={20} />
              New service job
            </button>

            <button
              type="button"
              onClick={() =>
                navigate("/installments")
              }
            >
              <CreditCard size={20} />
              Installments
            </button>
          </div>
        </article>

        <article className="dashboard-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">
                ACTIVITY
              </p>

              <h2>
                Recent activity
              </h2>
            </div>
          </div>

          {dashboardLoading ? (
            <div className="empty-state">
              <TrendingUp size={28} />

              <strong>
                Loading activity...
              </strong>

              <p>
                Reading recent store
                operations.
              </p>
            </div>
          ) : recentActivity.length === 0 ? (
            <div className="empty-state">
              <TrendingUp size={28} />

              <strong>
                No recent activity
              </strong>

              <p>
                New sales, services and
                installments will appear here.
              </p>
            </div>
          ) : (
            <div
              style={{
                display: "grid",
                gap: "10px",
                marginTop: "18px",
              }}
            >
              {recentActivity.map(
                (activity) => (
                  <button
                    key={activity.id}
                    type="button"
                    onClick={() =>
                      navigate(
                        activity.href,
                      )
                    }
                    style={{
                      background:
                        "var(--surface-soft)",
                      border:
                        "1px solid var(--border)",
                      borderRadius: "11px",
                      cursor: "pointer",
                      padding: "12px 14px",
                      textAlign: "left",
                      width: "100%",
                    }}
                  >
                    <strong
                      style={{
                        display: "block",
                        fontSize: "11px",
                      }}
                    >
                      {activity.title}
                    </strong>

                    <span
                      style={{
                        color: "var(--muted)",
                        display: "block",
                        fontSize: "9px",
                        marginTop: "4px",
                      }}
                    >
                      {activity.detail}
                    </span>

                    {activity.timestamp ? (
                      <small
                        style={{
                          color: "#98a1af",
                          display: "block",
                          fontSize: "8px",
                          marginTop: "5px",
                        }}
                      >
                        {formatActivityTime(
                          activity.timestamp,
                        )}
                      </small>
                    ) : null}
                  </button>
                ),
              )}
            </div>
          )}
        </article>
      </section>
    </AppShell>
  );
}
