"use client";

import {
  Boxes,
  CircleDollarSign,
  ClipboardCheck,
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

import type {
  UserResponse,
} from "@/types/auth";

const cards = [
  {
    label: "Today's Sales",
    value: "LKR 0.00",
    note: "Ready for live data",
    icon: ShoppingCart,
  },
  {
    label: "Outstanding",
    value: "LKR 0.00",
    note: "Customer balances",
    icon: CircleDollarSign,
  },
  {
    label: "Products",
    value: "—",
    note: "Inventory catalog",
    icon: Boxes,
  },
  {
    label: "Open Services",
    value: "—",
    note: "Active job cards",
    icon: Wrench,
  },
];

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
            <button>
              <ShoppingCart size={20} />
              New sale
            </button>

            <button>
              <Users size={20} />
              Add customer
            </button>

            <button>
              <PackageCheck size={20} />
              Receive stock
            </button>

            <button>
              <ClipboardCheck size={20} />
              New service job
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

          <div className="empty-state">
            <TrendingUp size={28} />

            <strong>
              Ready for live data
            </strong>

            <p>
              Recent sales, payments,
              inventory and service
              activity will appear here.
            </p>
          </div>
        </article>
      </section>
    </AppShell>
  );
}
