"use client";

import axios from "axios";

import {
  Building2,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  CircleOff,
  Eye,
  Loader2,
  Mail,
  MapPin,
  Pencil,
  Phone,
  Plus,
  RefreshCw,
  Search,
  UserRound,
  WalletCards,
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
  activateSupplier,
  createSupplier,
  deactivateSupplier,
  getSupplier,
  getSuppliers,
  listSupplierInvoices,
  updateSupplier,
} from "@/lib/supplier-api";

import type {
  UserResponse,
} from "@/types/auth";

import type {
  Supplier,
  SupplierCreatePayload,
  SupplierInvoice,
  SupplierUpdatePayload,
} from "@/types/supplier";

import styles from "./suppliers.module.css";


const PAGE_SIZE = 20;


type StatusFilter =
  | "all"
  | "active"
  | "inactive";


type SupplierFormState = {
  companyName:
    string;

  contactPerson:
    string;

  phone:
    string;

  secondaryPhone:
    string;

  email:
    string;

  registrationNumber:
    string;

  taxNumber:
    string;

  addressLine1:
    string;

  addressLine2:
    string;

  city:
    string;

  creditLimit:
    string;

  paymentTermsDays:
    string;

  notes:
    string;
};


const EMPTY_FORM:
SupplierFormState = {
  companyName:
    "",

  contactPerson:
    "",

  phone:
    "",

  secondaryPhone:
    "",

  email:
    "",

  registrationNumber:
    "",

  taxNumber:
    "",

  addressLine1:
    "",

  addressLine2:
    "",

  city:
    "",

  creditLimit:
    "0.00",

  paymentTermsDays:
    "0",

  notes:
    "",
};


function nullableText(
  value:
    string,
): string | null {
  const trimmed =
    value.trim();

  return (
    trimmed
      ? trimmed
      : null
  );
}


function money(
  value:
    string | number,
): string {
  const numeric =
    Number(value);

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
    Number.isFinite(
      numeric,
    )
      ? numeric
      : 0,
  );
}



function financeTotal(
  invoices: SupplierInvoice[],
  field:
    | "grand_total"
    | "paid_amount"
    | "balance_amount",
): number {
  return invoices.reduce(
    (total, invoice) =>
      total + Number(
        invoice[field] ?? 0,
      ),
    0,
  );
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
      + "for this supplier operation."
    );
  }

  return (
    "Unable to complete the "
    + "supplier operation."
  );
}


function supplierToForm(
  supplier:
    Supplier,
): SupplierFormState {
  return {
    companyName:
      supplier.company_name,

    contactPerson:
      supplier.contact_person
      ?? "",

    phone:
      supplier.phone
      ?? "",

    secondaryPhone:
      supplier.secondary_phone
      ?? "",

    email:
      supplier.email
      ?? "",

    registrationNumber:
      supplier.registration_number
      ?? "",

    taxNumber:
      supplier.tax_number
      ?? "",

    addressLine1:
      supplier.address_line_1
      ?? "",

    addressLine2:
      supplier.address_line_2
      ?? "",

    city:
      supplier.city
      ?? "",

    creditLimit:
      String(
        supplier.credit_limit
        ?? 0,
      ),

    paymentTermsDays:
      String(
        supplier.payment_terms_days
        ?? 0,
      ),

    notes:
      supplier.notes
      ?? "",
  };
}


function formPayload(
  form:
    SupplierFormState,
): SupplierCreatePayload {
  return {
    company_name:
      form.companyName
        .trim(),

    contact_person:
      nullableText(
        form.contactPerson,
      ),

    phone:
      nullableText(
        form.phone,
      ),

    secondary_phone:
      nullableText(
        form.secondaryPhone,
      ),

    email:
      nullableText(
        form.email,
      ),

    registration_number:
      nullableText(
        form.registrationNumber,
      ),

    tax_number:
      nullableText(
        form.taxNumber,
      ),

    address_line_1:
      nullableText(
        form.addressLine1,
      ),

    address_line_2:
      nullableText(
        form.addressLine2,
      ),

    city:
      nullableText(
        form.city,
      ),

    credit_limit:
      Number(
        form.creditLimit
        || 0,
      ),

    payment_terms_days:
      Number(
        form.paymentTermsDays
        || 0,
      ),

    notes:
      nullableText(
        form.notes,
      ),
  };
}


export default function SuppliersPage() {
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
    suppliers,
    setSuppliers,
  ] =
    useState<Supplier[]>(
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
    statusFilter,
    setStatusFilter,
  ] =
    useState<StatusFilter>(
      "all",
    );


  const [
    selected,
    setSelected,
  ] =
    useState<
      Supplier | null
    >(
      null,
    );

  const [
    detailLoading,
    setDetailLoading,
  ] =
    useState(false);


  const [
    supplierInvoices,
    setSupplierInvoices,
  ] = useState<SupplierInvoice[]>([]);

  const [
    financeLoading,
    setFinanceLoading,
  ] = useState(false);

  const [
    financeError,
    setFinanceError,
  ] = useState("");


  useEffect(() => {
    let cancelled = false;

    async function loadSupplierFinance() {
      if (!selected) {
        setSupplierInvoices([]);
        setFinanceError("");
        return;
      }

      setFinanceLoading(true);
      setFinanceError("");

      try {
        const response =
          await listSupplierInvoices({
            supplierId: selected.id,
            page: 1,
            pageSize: 100,
          });

        if (!cancelled) {
          setSupplierInvoices(
            response.items,
          );
        }
      } catch (error) {
        if (!cancelled) {
          setSupplierInvoices([]);
          setFinanceError(
            apiError(error),
          );
        }
      } finally {
        if (!cancelled) {
          setFinanceLoading(false);
        }
      }
    }

    void loadSupplierFinance();

    return () => {
      cancelled = true;
    };
  }, [selected]);


  const [
    modalOpen,
    setModalOpen,
  ] =
    useState(false);

  const [
    editing,
    setEditing,
  ] =
    useState<
      Supplier | null
    >(
      null,
    );

  const [
    form,
    setForm,
  ] =
    useState<SupplierFormState>(
      EMPTY_FORM,
    );

  const [
    saving,
    setSaving,
  ] =
    useState(false);

  const [
    formError,
    setFormError,
  ] =
    useState("");


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


  const loadSuppliers =
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
            await getSuppliers({
              page,

              pageSize:
                PAGE_SIZE,

              search:
                search
                || undefined,

              isActive:
                statusFilter
                === "all"
                  ? undefined
                  : statusFilter
                    === "active",
            });

          setSuppliers(
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

          setSuppliers(
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
          void loadSuppliers();
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
    loadSuppliers,
  ]);


  const summary =
    useMemo(
      () => ({
        active:
          suppliers.filter(
            (supplier) =>
              supplier.is_active,
          ).length,

        inactive:
          suppliers.filter(
            (supplier) =>
              !supplier.is_active,
          ).length,

        payable:
          suppliers.reduce(
            (
              running,
              supplier,
            ) =>
              running
              + Number(
                  supplier
                    .current_payable
                  || 0,
                ),
            0,
          ),
      }),
      [suppliers],
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
          100,
        ),
    );
  }


  async function openDetail(
    supplier:
      Supplier,
  ) {
    setSelected(
      supplier,
    );

    setDetailLoading(
      true,
    );

    setError("");

    try {
      const detail =
        await getSupplier(
          supplier.id,
        );

      setSelected(
        detail,
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


  function openCreate() {
    setEditing(
      null,
    );

    setForm({
      ...EMPTY_FORM,
    });

    setFormError(
      "",
    );

    setModalOpen(
      true,
    );
  }


  function openEdit(
    supplier:
      Supplier,
  ) {
    setEditing(
      supplier,
    );

    setForm(
      supplierToForm(
        supplier,
      ),
    );

    setFormError(
      "",
    );

    setModalOpen(
      true,
    );
  }


  function closeModal() {
    if (saving) {
      return;
    }

    setModalOpen(
      false,
    );

    setEditing(
      null,
    );

    setFormError(
      "",
    );
  }


  async function submitSupplier(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (
      form.companyName
        .trim()
        .length < 2
    ) {
      setFormError(
        "Company name is required.",
      );

      return;
    }

    const creditLimit =
      Number(
        form.creditLimit
        || 0,
      );

    if (
      !Number.isFinite(
        creditLimit,
      )
      || creditLimit < 0
    ) {
      setFormError(
        "Credit limit must be "
        + "zero or greater.",
      );

      return;
    }

    const terms =
      Number(
        form.paymentTermsDays
        || 0,
      );

    if (
      !Number.isInteger(
        terms,
      )
      || terms < 0
    ) {
      setFormError(
        "Payment terms must be "
        + "a whole number of days.",
      );

      return;
    }

    setSaving(
      true,
    );

    setFormError(
      "",
    );

    try {
      const payload =
        formPayload(
          form,
        );

      let result:
        Supplier;

      if (editing) {
        result =
          await updateSupplier(
            editing.id,
            payload as
              SupplierUpdatePayload,
          );
      } else {
        result =
          await createSupplier(
            payload,
          );
      }

      setSelected(
        result,
      );

      setModalOpen(
        false,
      );

      setEditing(
        null,
      );

      setForm({
        ...EMPTY_FORM,
      });

      await loadSuppliers(
        true,
      );
    } catch (
      requestError
    ) {
      setFormError(
        apiError(
          requestError,
        ),
      );
    } finally {
      setSaving(
        false,
      );
    }
  }


  async function changeActiveState(
    supplier:
      Supplier,
  ) {
    setError("");

    try {
      const result =
        supplier.is_active
          ? await deactivateSupplier(
              supplier.id,
            )
          : await activateSupplier(
              supplier.id,
            );

      if (
        selected?.id
        === supplier.id
      ) {
        setSelected(
          result,
        );
      }

      await loadSuppliers(
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
            PROCUREMENT
          </p>

          <h1>
            Suppliers
          </h1>

          <p>
            Manage supplier profiles,
            contact information,
            credit limits, payment terms
            and payable exposure.
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
              styles.secondaryButton
            }
            disabled={
              refreshing
            }
            onClick={() =>
              void loadSuppliers(
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

          <button
            type="button"
            className={
              styles.primaryButton
            }
            onClick={
              openCreate
            }
          >
            <Plus size={17} />

            New supplier
          </button>
        </div>
      </section>


      <section
        className={
          styles.summaryGrid
        }
      >
        <article>
          <Building2 size={20} />

          <div>
            <span>
              Total suppliers
            </span>

            <strong>
              {total}
            </strong>
          </div>
        </article>

        <article>
          <CheckCircle2
            size={20}
          />

          <div>
            <span>
              Active loaded
            </span>

            <strong>
              {summary.active}
            </strong>
          </div>
        </article>

        <article>
          <CircleOff size={20} />

          <div>
            <span>
              Inactive loaded
            </span>

            <strong>
              {summary.inactive}
            </strong>
          </div>
        </article>

        <article>
          <WalletCards
            size={20}
          />

          <div>
            <span>
              Payable loaded
            </span>

            <strong>
              {money(
                summary.payable,
              )}
            </strong>
          </div>
        </article>
      </section>


      <section
        className={
          styles.toolbar
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
              "Search supplier, code, contact, phone or email..."
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
                  .value as
                  StatusFilter,
              );
            }
          }
        >
          <option value="all">
            All suppliers
          </option>

          <option value="active">
            Active
          </option>

          <option value="inactive">
            Inactive
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
          styles.contentGrid
        }
      >
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
                size={23}
                className={
                  styles.spin
                }
              />

              Loading suppliers...
            </div>
          ) : suppliers.length
            === 0 ? (
            <div
              className={
                styles.emptyState
              }
            >
              <Building2
                size={30}
              />

              <strong>
                No suppliers found
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
                      Supplier
                    </th>

                    <th>
                      Contact
                    </th>

                    <th>
                      Credit limit
                    </th>

                    <th>
                      Current payable
                    </th>

                    <th>
                      Terms
                    </th>

                    <th>
                      Status
                    </th>

                    <th />
                  </tr>
                </thead>

                <tbody>
                  {suppliers.map(
                    (supplier) => (
                      <tr
                        key={
                          supplier.id
                        }
                      >
                        <td>
                          <strong>
                            {
                              supplier
                                .company_name
                            }
                          </strong>

                          <small>
                            {
                              supplier
                                .supplier_code
                            }
                          </small>
                        </td>

                        <td>
                          <strong>
                            {supplier
                              .contact_person
                              || "—"
                            }
                          </strong>

                          <small>
                            {supplier.phone
                              || supplier.email
                              || "No contact"
                            }
                          </small>
                        </td>

                        <td>
                          {money(
                            supplier
                              .credit_limit,
                          )}
                        </td>

                        <td>
                          <strong>
                            {money(
                              supplier
                                .current_payable,
                            )}
                          </strong>
                        </td>

                        <td>
                          {
                            supplier
                              .payment_terms_days
                          }
                          {" days"}
                        </td>

                        <td>
                          <span
                            className={
                              supplier.is_active
                                ? styles.activeBadge
                                : styles.inactiveBadge
                            }
                          >
                            {supplier.is_active
                              ? "Active"
                              : "Inactive"
                            }
                          </span>
                        </td>

                        <td>
                          <div
                            className={
                              styles.rowActions
                            }
                          >
                            <button
                              type="button"
                              className={
                                styles.iconButton
                              }
                              title={
                                "View supplier"
                              }
                              onClick={() =>
                                void openDetail(
                                  supplier,
                                )
                              }
                            >
                              <Eye
                                size={15}
                              />
                            </button>

                            <button
                              type="button"
                              className={
                                styles.iconButton
                              }
                              title={
                                "Edit supplier"
                              }
                              onClick={() =>
                                openEdit(
                                  supplier,
                                )
                              }
                            >
                              <Pencil
                                size={15}
                              />
                            </button>

                            <button
                              type="button"
                              className={
                                styles.stateButton
                              }
                              onClick={() =>
                                void changeActiveState(
                                  supplier,
                                )
                              }
                            >
                              {supplier.is_active
                                ? "Deactivate"
                                : "Activate"
                              }
                            </button>
                          </div>
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
              Page {page}
              {" of "}
              {Math.max(
                1,
                totalPages,
              )}
              {" • "}
              {total} suppliers
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
        </div>


        <aside
          className={
            styles.detailCard
          }
        >
          {!selected ? (
            <div
              className={
                styles.detailEmpty
              }
            >
              <Building2
                size={34}
              />

              <strong>
                Supplier details
              </strong>

              <span>
                Select a supplier to
                inspect the complete
                profile.
              </span>
            </div>
          ) : detailLoading ? (
            <div
              className={
                styles.detailEmpty
              }
            >
              <Loader2
                size={22}
                className={
                  styles.spin
                }
              />

              Loading supplier...
            </div>
          ) : (
            <>
              <header
                className={
                  styles.detailHeader
                }
              >
                <div>
                  <p className="eyebrow">
                    SUPPLIER PROFILE
                  </p>

                  <h2>
                    {
                      selected
                        .company_name
                    }
                  </h2>

                  <span>
                    {
                      selected
                        .supplier_code
                    }
                  </span>
                </div>

                <button
                  type="button"
                  className={
                    styles.iconButton
                  }
                  onClick={() =>
                    setSelected(
                      null,
                    )
                  }
                >
                  <X size={17} />
                </button>
              </header>


              <div
                className={
                  styles.detailBody
                }
              >
                <div
                  className={
                    styles.detailActions
                  }
                >
                  <span
                    className={
                      selected.is_active
                        ? styles.activeBadge
                        : styles.inactiveBadge
                    }
                  >
                    {selected.is_active
                      ? "Active supplier"
                      : "Inactive supplier"
                    }
                  </span>

                  <button
                    type="button"
                    className={
                      styles.secondaryButton
                    }
                    onClick={() =>
                      openEdit(
                        selected,
                      )
                    }
                  >
                    <Pencil
                      size={14}
                    />

                    Edit
                  </button>
                </div>


                <section
                  className={
                    styles.financeGrid
                  }
                >
                  <div>
                    <span>
                      Credit limit
                    </span>

                    <strong>
                      {money(
                        selected
                          .credit_limit,
                      )}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Current payable
                    </span>

                    <strong>
                      {money(
                        selected
                          .current_payable,
                      )}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Payment terms
                    </span>

                    <strong>
                      {
                        selected
                          .payment_terms_days
                      }
                      {" days"}
                    </strong>
                  </div>
                </section>


                <section
                  style={{
                    marginTop: "18px",
                  }}
                >
                  <p className="eyebrow">
                    SUPPLIER FINANCE
                  </p>

                  {financeLoading ? (
                    <div
                      className={
                        styles.detailEmpty
                      }
                    >
                      <Loader2
                        size={18}
                        className={
                          styles.spin
                        }
                      />
                      Loading finance...
                    </div>
                  ) : financeError ? (
                    <div
                      className={
                        styles.detailEmpty
                      }
                    >
                      <CircleAlert
                        size={18}
                      />
                      {financeError}
                    </div>
                  ) : (
                    <>
                      <section
                        className={
                          styles.financeGrid
                        }
                      >
                        <div>
                          <span>
                            Total purchased
                          </span>

                          <strong>
                            {money(
                              financeTotal(
                                supplierInvoices,
                                "grand_total",
                              ),
                            )}
                          </strong>
                        </div>

                        <div>
                          <span>
                            Total paid
                          </span>

                          <strong>
                            {money(
                              financeTotal(
                                supplierInvoices,
                                "paid_amount",
                              ),
                            )}
                          </strong>
                        </div>

                        <div>
                          <span>
                            Outstanding
                          </span>

                          <strong>
                            {money(
                              financeTotal(
                                supplierInvoices,
                                "balance_amount",
                              ),
                            )}
                          </strong>
                        </div>
                      </section>

                      {supplierInvoices.length === 0 ? (
                        <div
                          className={
                            styles.detailEmpty
                          }
                          style={{
                            marginTop: "12px",
                          }}
                        >
                          No supplier invoices yet.
                        </div>
                      ) : (
                        <div
                          style={{
                            marginTop: "14px",
                            display: "grid",
                            gap: "10px",
                          }}
                        >
                          {supplierInvoices.map(
                            (invoice) => (
                              <div
                                key={
                                  invoice.id
                                }
                                style={{
                                  border:
                                    "1px solid var(--border)",
                                  borderRadius:
                                    "12px",
                                  padding:
                                    "12px",
                                }}
                              >
                                <strong>
                                  {
                                    invoice
                                      .invoice_number
                                  }
                                </strong>

                                <div
                                  style={{
                                    marginTop:
                                      "8px",
                                    display:
                                      "grid",
                                    gap: "4px",
                                    fontSize:
                                      "13px",
                                  }}
                                >
                                  <span>
                                    PO:{" "}
                                    {
                                      invoice
                                        .purchase_order_number
                                      || "—"
                                    }
                                  </span>

                                  <span>
                                    GRN:{" "}
                                    {
                                      invoice
                                        .grn_number
                                      || "—"
                                    }
                                  </span>

                                  <span>
                                    Purchase:{" "}
                                    {money(
                                      invoice
                                        .grand_total,
                                    )}
                                  </span>

                                  <span>
                                    Paid:{" "}
                                    {money(
                                      invoice
                                        .paid_amount,
                                    )}
                                  </span>

                                  <span>
                                    Balance:{" "}
                                    {money(
                                      invoice
                                        .balance_amount,
                                    )}
                                  </span>

                                  <span>
                                    Aging:{" "}
                                    {
                                      invoice
                                        .aging_bucket
                                    }
                                  </span>
                                </div>
                              </div>
                            ),
                          )}
                        </div>
                      )}
                    </>
                  )}
                </section>


                <section
                  className={
                    styles.detailList
                  }
                >
                  <div>
                    <UserRound
                      size={16}
                    />

                    <span>
                      <small>
                        Contact person
                      </small>

                      <strong>
                        {selected
                          .contact_person
                          || "Not provided"
                        }
                      </strong>
                    </span>
                  </div>

                  <div>
                    <Phone size={16} />

                    <span>
                      <small>
                        Primary phone
                      </small>

                      <strong>
                        {selected.phone
                          || "Not provided"
                        }
                      </strong>
                    </span>
                  </div>

                  <div>
                    <Phone size={16} />

                    <span>
                      <small>
                        Secondary phone
                      </small>

                      <strong>
                        {selected
                          .secondary_phone
                          || "Not provided"
                        }
                      </strong>
                    </span>
                  </div>

                  <div>
                    <Mail size={16} />

                    <span>
                      <small>
                        Email
                      </small>

                      <strong>
                        {selected.email
                          || "Not provided"
                        }
                      </strong>
                    </span>
                  </div>

                  <div>
                    <MapPin size={16} />

                    <span>
                      <small>
                        Address
                      </small>

                      <strong>
                        {[
                          selected
                            .address_line_1,
                          selected
                            .address_line_2,
                          selected.city,
                        ]
                          .filter(
                            Boolean,
                          )
                          .join(", ")
                          || "Not provided"
                        }
                      </strong>
                    </span>
                  </div>
                </section>


                <section
                  className={
                    styles.identifierGrid
                  }
                >
                  <div>
                    <span>
                      Registration
                    </span>

                    <strong>
                      {selected
                        .registration_number
                        || "—"
                      }
                    </strong>
                  </div>

                  <div>
                    <span>
                      Tax number
                    </span>

                    <strong>
                      {selected.tax_number
                        || "—"
                      }
                    </strong>
                  </div>
                </section>


                {selected.notes && (
                  <section
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
                  </section>
                )}
              </div>
            </>
          )}
        </aside>
      </section>


      {modalOpen && (
        <div
          className={
            styles.backdrop
          }
        >
          <form
            className={
              styles.modal
            }
            onSubmit={
              submitSupplier
            }
          >
            <header
              className={
                styles.modalHeader
              }
            >
              <div>
                <p className="eyebrow">
                  {editing
                    ? "UPDATE SUPPLIER"
                    : "NEW SUPPLIER"
                  }
                </p>

                <h2>
                  {editing
                    ? editing.company_name
                    : "Create supplier"
                  }
                </h2>
              </div>

              <button
                type="button"
                className={
                  styles.iconButton
                }
                disabled={
                  saving
                }
                onClick={
                  closeModal
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
                  Company name *

                  <input
                    required
                    minLength={2}
                    value={
                      form.companyName
                    }
                    onChange={
                      (event) =>
                        setForm(
                          (current) => ({
                            ...current,

                            companyName:
                              event
                                .target
                                .value,
                          }),
                        )
                    }
                  />
                </label>


                <label>
                  Contact person

                  <input
                    value={
                      form.contactPerson
                    }
                    onChange={
                      (event) =>
                        setForm(
                          (current) => ({
                            ...current,

                            contactPerson:
                              event
                                .target
                                .value,
                          }),
                        )
                    }
                  />
                </label>


                <label>
                  Email

                  <input
                    type="email"
                    value={
                      form.email
                    }
                    onChange={
                      (event) =>
                        setForm(
                          (current) => ({
                            ...current,

                            email:
                              event
                                .target
                                .value,
                          }),
                        )
                    }
                  />
                </label>


                <label>
                  Primary phone

                  <input
                    value={
                      form.phone
                    }
                    onChange={
                      (event) =>
                        setForm(
                          (current) => ({
                            ...current,

                            phone:
                              event
                                .target
                                .value,
                          }),
                        )
                    }
                  />
                </label>


                <label>
                  Secondary phone

                  <input
                    value={
                      form.secondaryPhone
                    }
                    onChange={
                      (event) =>
                        setForm(
                          (current) => ({
                            ...current,

                            secondaryPhone:
                              event
                                .target
                                .value,
                          }),
                        )
                    }
                  />
                </label>


                <label>
                  Registration number

                  <input
                    value={
                      form.registrationNumber
                    }
                    onChange={
                      (event) =>
                        setForm(
                          (current) => ({
                            ...current,

                            registrationNumber:
                              event
                                .target
                                .value,
                          }),
                        )
                    }
                  />
                </label>


                <label>
                  Tax number

                  <input
                    value={
                      form.taxNumber
                    }
                    onChange={
                      (event) =>
                        setForm(
                          (current) => ({
                            ...current,

                            taxNumber:
                              event
                                .target
                                .value,
                          }),
                        )
                    }
                  />
                </label>


                <label
                  className={
                    styles.fullField
                  }
                >
                  Address line 1

                  <input
                    value={
                      form.addressLine1
                    }
                    onChange={
                      (event) =>
                        setForm(
                          (current) => ({
                            ...current,

                            addressLine1:
                              event
                                .target
                                .value,
                          }),
                        )
                    }
                  />
                </label>


                <label
                  className={
                    styles.fullField
                  }
                >
                  Address line 2

                  <input
                    value={
                      form.addressLine2
                    }
                    onChange={
                      (event) =>
                        setForm(
                          (current) => ({
                            ...current,

                            addressLine2:
                              event
                                .target
                                .value,
                          }),
                        )
                    }
                  />
                </label>


                <label>
                  City

                  <input
                    value={
                      form.city
                    }
                    onChange={
                      (event) =>
                        setForm(
                          (current) => ({
                            ...current,

                            city:
                              event
                                .target
                                .value,
                          }),
                        )
                    }
                  />
                </label>


                <label>
                  Credit limit

                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={
                      form.creditLimit
                    }
                    onChange={
                      (event) =>
                        setForm(
                          (current) => ({
                            ...current,

                            creditLimit:
                              event
                                .target
                                .value,
                          }),
                        )
                    }
                  />
                </label>


                <label>
                  Payment terms (days)

                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={
                      form
                        .paymentTermsDays
                    }
                    onChange={
                      (event) =>
                        setForm(
                          (current) => ({
                            ...current,

                            paymentTermsDays:
                              event
                                .target
                                .value,
                          }),
                        )
                    }
                  />
                </label>


                <label
                  className={
                    styles.fullField
                  }
                >
                  Notes

                  <textarea
                    rows={4}
                    value={
                      form.notes
                    }
                    onChange={
                      (event) =>
                        setForm(
                          (current) => ({
                            ...current,

                            notes:
                              event
                                .target
                                .value,
                          }),
                        )
                    }
                  />
                </label>
              </div>


              {formError && (
                <div
                  className={
                    styles.errorBanner
                  }
                >
                  <CircleAlert
                    size={17}
                  />

                  {formError}
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
                  saving
                }
                onClick={
                  closeModal
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
                  saving
                }
              >
                {saving ? (
                  <Loader2
                    size={16}
                    className={
                      styles.spin
                    }
                  />
                ) : editing ? (
                  <Pencil size={16} />
                ) : (
                  <Plus size={16} />
                )}

                {saving
                  ? "Saving..."
                  : editing
                    ? "Save changes"
                    : "Create supplier"
                }
              </button>
            </footer>
          </form>
        </div>
      )}
    </AppShell>
  );
}
