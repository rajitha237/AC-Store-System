"use client";

import {
  Boxes,
  ChevronRight,
  ClipboardList,
  CreditCard,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  PackageSearch,
  ReceiptText,
  RotateCcw,
  Settings,
  ShieldCheck,
  UserRound,
  Users,
  Wrench,
  X,
  Truck,
  Building2,
  ShoppingCart,
} from "lucide-react";

import Link from "next/link";
import {
  usePathname,
  useRouter,
} from "next/navigation";

import {
  ReactNode,
  useEffect,
  useState,
} from "react";

import {
  clearAuthSession,
} from "@/lib/auth";

import {
  AUTH_UNAUTHORIZED_EVENT,
} from "@/lib/api";

import type {
  UserResponse,
} from "@/types/auth";


type AppShellProps = {
  user: UserResponse;
  children: ReactNode;
};


const navigation = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
    available: true,
  },
  {
    label: "Customers",
    href: "/customers",
    icon: Users,
    available: true,
  },
  {
    label: "Products",
    href: "/catalog",
    icon: PackageSearch,
    available: true,
  },
  {
    label: "Suppliers",
    href: "/suppliers",
    icon: Truck,
    available: true,
  },
  {
    label: "Purchases",
    href: "/purchases",
    icon: ClipboardList,
    available: true,
  },
  {
    label: "Inventory",
    href: "/inventory",
    icon: Boxes,
    available: true,
  },
  {
    label: "Sales",
    href: "/sales",
    icon: ReceiptText,
    available: true,
  },

  {
    label: "Quick Sale",
    href: "/quick-sale",
    icon: ShoppingCart,
    available: true,
  },
  {
    label: "Payments",
    href: "/payments",
    icon: CreditCard,
    available: true,
  },
{
    label: "Installments",
    href: "/installments",
    icon: CreditCard,
    available: true,

    // PHASE7C9D_INSTALLMENTS_NAV
  },
  {
    label: "Returns",
    href: "/returns",
    icon: RotateCcw,
    available: true,
  },
  {
    label: "Credit Notes",
    href: "/credit-notes",
    icon: FileText,
    available: true,
  },
  {
    label: "Service Jobs",
    href: "/service-jobs",
    icon: Wrench,
    available: true,
  },
  {
    label: "Audit Logs",
    href: "/audit-logs",
    icon: ClipboardList,
    available: true,
  },
  {
    label: "Access Control",
    href: "/access-control",
    icon: ShieldCheck,
    available: true,
  },
  {
    label: "Company Settings",
    href: "/company",
    icon: Building2,
    available: true,
  },
  {
    label: "Documents",
    href: "/documents",
    icon: FileText,
    available: true,
  },
];


export function AppShell({
  user,
  children,
}: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();

  const [
    mobileOpen,
    setMobileOpen,
  ] = useState(false);

  useEffect(() => {
    function handleUnauthorized() {
      clearAuthSession();
      router.replace("/login");
    }

    window.addEventListener(
      AUTH_UNAUTHORIZED_EVENT,
      handleUnauthorized,
    );

    return () => {
      window.removeEventListener(
        AUTH_UNAUTHORIZED_EVENT,
        handleUnauthorized,
      );
    };
  }, [router]);

  function logout() {
    clearAuthSession();
    setMobileOpen(false);
    router.replace("/login");
  }

  return (
    <div className="app-shell">
      <aside
        className={
          mobileOpen
            ? "sidebar sidebar-open"
            : "sidebar"
        }
      >
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <div className="logo-mark">
              <img
                src="/bandara-cool-world-logo.png"
                alt="Bandara Cool World logo"
                className="brand-logo-image"
              />
            </div>

            <div>
              <strong>
                BANDARA COOL WORLD
              </strong>

              <span>
                Management System
              </span>
            </div>
          </div>

          <button
            className="mobile-close"
            onClick={() =>
              setMobileOpen(false)
            }
            aria-label="Close menu"
          >
            <X size={21} />
          </button>
        </div>

        <nav className="sidebar-nav">
          <p className="nav-section-title">
            WORKSPACE
          </p>

          {navigation.map((item) => {
            const Icon = item.icon;

            const active =
              item.available
              && pathname === item.href;

            if (!item.available) {
              return (
                <button
                  key={item.label}
                  type="button"
                  className="nav-item"
                  title="Coming next"
                >
                  <Icon size={19} />

                  <span>
                    {item.label}
                  </span>
                </button>
              );
            }

            return (
              <Link
                key={item.label}
                href={item.href}
                onClick={() =>
                  setMobileOpen(false)
                }
                className={
                  active
                    ? "nav-item nav-item-active"
                    : "nav-item"
                }
              >
                <Icon size={19} />

                <span>
                  {item.label}
                </span>

                {active && (
                  <ChevronRight
                    size={16}
                    className="nav-chevron"
                  />
                )}
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="secure-indicator">
            <ShieldCheck size={17} />
            Secure session
          </div>

          <button
            type="button"
            className="logout-button"
            onClick={logout}
          >
            <LogOut size={18} />
            Sign out
          </button>
        </div>
      </aside>

      {mobileOpen && (
        <button
          type="button"
          className="sidebar-overlay"
          aria-label="Close navigation"
          onClick={() =>
            setMobileOpen(false)
          }
        />
      )}

      <div className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="menu-button"
              onClick={() =>
                setMobileOpen(true)
              }
              aria-label="Open menu"
            >
              <Menu size={21} />
            </button>

            <div>
              <p>
                BANDARA COOL WORLD
              </p>

              <span>
                Internal operations
              </span>
            </div>
          </div>

          <div className="topbar-actions">
            <button
              type="button"
              className="topbar-icon-button"
              aria-label="Settings"
            >
              <Settings size={19} />
            </button>

            <div className="user-chip">
              <div className="user-avatar">
                <UserRound size={18} />
              </div>

              <div>
                <strong>
                  {user.full_name}
                </strong>

                <span>
                  {user.role.replaceAll(
                    "_",
                    " ",
                  )}
                </span>
              </div>
            </div>
          </div>
        </header>

        <main className="content-area">
          {children}
        </main>
      </div>
    </div>
  );
}
