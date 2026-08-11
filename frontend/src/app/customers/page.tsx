"use client";

import axios from "axios";

import {
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Filter,
  Mail,
  MapPin,
  Phone,
  Plus,
  Search,
  UserRound,
  Users,
  X,
} from "lucide-react";

import {
  FormEvent,
  useCallback,
  useEffect,
  useState,
} from "react";

import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import {
  CustomerDetailsModal,
} from "@/components/customer-details-modal";

import {
  createCustomer,
  getCustomers,
} from "@/lib/customer-api";

import {
  clearAuthSession,
  getAccessToken,
  getStoredUser,
} from "@/lib/auth";

import type {
  Customer,
  CustomerCreatePayload,
  CustomerListResponse,
} from "@/types/customer";

import type {
  UserResponse,
} from "@/types/auth";

import styles from "./customers.module.css";


const PAGE_SIZE = 10;


const initialCustomerForm:
  CustomerCreatePayload = {
    customer_type:
      "cash",

    full_name:
      "",

    business_name:
      "",

    nic_number:
      "",

    registration_number:
      "",

    primary_phone:
      "",

    secondary_phone:
      "",

    sms_phone:
      "",

    email:
      "",

    address_line_1:
      "",

    address_line_2:
      "",

    city:
      "",

    district:
      "",

    province:
      "",

    postal_code:
      "",

    credit_status:
      "restricted",

    credit_limit:
      "0.00",

    sms_allowed:
      true,

    notes:
      "",
  };


function cleanOptional(
  value: string | null | undefined,
): string | null {
  if (!value) {
    return null;
  }

  const normalized =
    value.trim();

  return normalized || null;
}


function formatCurrency(
  value: string | number,
): string {
  const amount =
    Number(value ?? 0);

  if (Number.isNaN(amount)) {
    return "LKR 0.00";
  }

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
  ).format(amount);
}


function extractApiError(
  error: unknown,
): string {
  if (!axios.isAxiosError(error)) {
    return (
      "Something went wrong. "
      + "Please try again."
    );
  }

  const detail =
    error.response?.data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const first =
      detail[0];

    if (
      first
      && typeof first.msg === "string"
    ) {
      return first.msg.replace(
        /^Value error, /,
        "",
      );
    }
  }

  if (
    error.response?.status === 403
  ) {
    return (
      "You do not have permission "
      + "to perform this action."
    );
  }

  return (
    "Unable to complete the request."
  );
}


export default function CustomersPage() {
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
    loadingAuth,
    setLoadingAuth,
  ] =
    useState(true);

  const [
    data,
    setData,
  ] =
    useState<CustomerListResponse>({
      items:
        [],

      total:
        0,

      page:
        1,

      page_size:
        PAGE_SIZE,

      total_pages:
        0,
    });

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
    customerType,
    setCustomerType,
  ] =
    useState("");

  const [
    customerStatus,
    setCustomerStatus,
  ] =
    useState("");

  const [
    createOpen,
    setCreateOpen,
  ] =
    useState(false);

  const [
    form,
    setForm,
  ] =
    useState<CustomerCreatePayload>(
      initialCustomerForm,
    );

  const [
    formError,
    setFormError,
  ] =
    useState("");

  const [
    saving,
    setSaving,
  ] =
    useState(false);

  const [
    selectedCustomerId,
    setSelectedCustomerId,
  ] =
    useState<number | null>(
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

          setLoadingAuth(
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


  const loadCustomers =
    useCallback(
      async () => {
        setLoading(
          true,
        );

        setError(
          "",
        );

        try {
          const response =
            await getCustomers({
              page,
              pageSize:
                PAGE_SIZE,

              search,

              customerType,

              customerStatus,
            });

          setData(
            response,
          );
        } catch (requestError) {
          setError(
            extractApiError(
              requestError,
            ),
          );
        } finally {
          setLoading(
            false,
          );
        }
      },
      [
        page,
        search,
        customerType,
        customerStatus,
      ],
    );


  useEffect(() => {
    if (loadingAuth) {
      return;
    }

    const timer =
      window.setTimeout(
        () => {
          void loadCustomers();
        },
        0,
      );

    return () => {
      window.clearTimeout(
        timer,
      );
    };
  }, [
    loadingAuth,
    loadCustomers,
  ]);


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
        .slice(0, 100),
    );
  }


  function resetFilters() {
    setSearchInput(
      "",
    );

    setSearch(
      "",
    );

    setCustomerType(
      "",
    );

    setCustomerStatus(
      "",
    );

    setPage(
      1,
    );
  }


  function openCreate() {
    setForm(
      initialCustomerForm,
    );

    setFormError(
      "",
    );

    setCreateOpen(
      true,
    );
  }


  function closeCreate() {
    if (saving) {
      return;
    }

    setCreateOpen(
      false,
    );

    setFormError(
      "",
    );
  }


  async function submitCustomer(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setFormError(
      "",
    );

    if (
      form.full_name.trim().length < 2
    ) {
      setFormError(
        "Full name is required.",
      );

      return;
    }

    if (
      !form.primary_phone.trim()
    ) {
      setFormError(
        "Primary phone number is required.",
      );

      return;
    }

    setSaving(
      true,
    );

    try {
      await createCustomer({
        ...form,

        full_name:
          form.full_name.trim(),

        primary_phone:
          form.primary_phone.trim(),

        business_name:
          cleanOptional(
            form.business_name,
          ),

        nic_number:
          cleanOptional(
            form.nic_number,
          ),

        registration_number:
          cleanOptional(
            form.registration_number,
          ),

        secondary_phone:
          cleanOptional(
            form.secondary_phone,
          ),

        sms_phone:
          cleanOptional(
            form.sms_phone,
          ),

        email:
          cleanOptional(
            form.email,
          ),

        address_line_1:
          cleanOptional(
            form.address_line_1,
          ),

        address_line_2:
          cleanOptional(
            form.address_line_2,
          ),

        city:
          cleanOptional(
            form.city,
          ),

        district:
          cleanOptional(
            form.district,
          ),

        province:
          cleanOptional(
            form.province,
          ),

        postal_code:
          cleanOptional(
            form.postal_code,
          ),

        notes:
          cleanOptional(
            form.notes,
          ),

        credit_limit:
          form.credit_limit || "0.00",
      });

      setCreateOpen(
        false,
      );

      setPage(
        1,
      );

      await loadCustomers();
    } catch (requestError) {
      setFormError(
        extractApiError(
          requestError,
        ),
      );
    } finally {
      setSaving(
        false,
      );
    }
  }


  if (
    loadingAuth
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
      <section
        className={
          styles.pageHeader
        }
      >
        <div>
          <p className="eyebrow">
            CRM
          </p>

          <h1>
            Customers
          </h1>

          <p>
            Manage customer profiles,
            contact details and credit
            settings.
          </p>
        </div>

        <button
          type="button"
          className={
            styles.addButton
          }
          onClick={
            openCreate
          }
        >
          <Plus
            size={18}
          />

          Add customer
        </button>
      </section>


      <section
        className={
          styles.summaryGrid
        }
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
            <Users size={21} />
          </div>

          <div>
            <span>
              Total customers
            </span>

            <strong>
              {data.total}
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
            <Filter size={21} />
          </div>

          <div>
            <span>
              Showing
            </span>

            <strong>
              {data.items.length}
            </strong>
          </div>
        </article>
      </section>


      <section
        className={
          styles.panel
        }
      >
        <div
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
            <div
              className={
                styles.searchBox
              }
            >
              <Search
                size={18}
              />

              <input
                type="search"
                value={
                  searchInput
                }
                maxLength={100}
                placeholder={
                  "Search by name, "
                  + "phone or customer number"
                }
                onChange={
                  (event) =>
                    setSearchInput(
                      event.target.value,
                    )
                }
              />
            </div>

            <button
              type="submit"
              className={
                styles.searchButton
              }
            >
              Search
            </button>
          </form>


          <div
            className={
              styles.filters
            }
          >
            <select
              value={
                customerType
              }
              onChange={
                (event) => {
                  setPage(
                    1,
                  );

                  setCustomerType(
                    event.target.value,
                  );
                }
              }
            >
              <option value="">
                All types
              </option>

              <option value="cash">
                Cash
              </option>

              <option value="credit">
                Credit
              </option>
            </select>

            <select
              value={
                customerStatus
              }
              onChange={
                (event) => {
                  setPage(
                    1,
                  );

                  setCustomerStatus(
                    event.target.value,
                  );
                }
              }
            >
              <option value="">
                All statuses
              </option>

              <option value="active">
                Active
              </option>

              <option value="inactive">
                Inactive
              </option>
            </select>

            <button
              type="button"
              className={
                styles.clearButton
              }
              onClick={
                resetFilters
              }
            >
              Clear
            </button>
          </div>
        </div>


        {error && (
          <div
            className={
              styles.errorBanner
            }
          >
            <CircleAlert
              size={18}
            />

            {error}
          </div>
        )}


        <div
          className={
            styles.tableWrapper
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
                  Customer
                </th>

                <th>
                  Contact
                </th>

                <th>
                  Location
                </th>

                <th>
                  Type
                </th>

                <th>
                  Balance
                </th>

                <th>
                  Status
                </th>
              </tr>
            </thead>

            <tbody>
              {loading ? (
                <tr>
                  <td
                    colSpan={6}
                  >
                    <div
                      className={
                        styles.tableState
                      }
                    >
                      <div className="loading-spinner" />

                      <span>
                        Loading customers...
                      </span>
                    </div>
                  </td>
                </tr>
              ) : data.items.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                  >
                    <div
                      className={
                        styles.emptyState
                      }
                    >
                      <Users size={30} />

                      <strong>
                        No customers found
                      </strong>

                      <p>
                        Try changing the
                        search or filters,
                        or add your first
                        customer.
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                data.items.map(
                  (
                    customer:
                      Customer,
                  ) => (
                    <tr
                      key={
                        customer.id
                      }
                      className={
                        styles.clickableRow
                      }
                      onClick={() =>
                        setSelectedCustomerId(
                          customer.id,
                        )
                      }
                    >
                      <td>
                        <div
                          className={
                            styles.customerCell
                          }
                        >
                          <div
                            className={
                              styles.avatar
                            }
                          >
                            <UserRound
                              size={18}
                            />
                          </div>

                          <div>
                            <strong
                              className={
                                styles.customerNameLink
                              }
                            >
                              {
                                customer.full_name
                              }
                            </strong>

                            <span>
                              {
                                customer.customer_number
                              }
                            </span>

                            {customer.business_name && (
                              <small>
                                {
                                  customer.business_name
                                }
                              </small>
                            )}
                          </div>
                        </div>
                      </td>

                      <td>
                        <div
                          className={
                            styles.contactCell
                          }
                        >
                          <span>
                            <Phone
                              size={14}
                            />

                            {
                              customer.primary_phone
                            }
                          </span>

                          {customer.email && (
                            <span>
                              <Mail
                                size={14}
                              />

                              {
                                customer.email
                              }
                            </span>
                          )}
                        </div>
                      </td>

                      <td>
                        <div
                          className={
                            styles.locationCell
                          }
                        >
                          <MapPin
                            size={14}
                          />

                          <span>
                            {
                              customer.city
                              || customer.district
                              || "—"
                            }
                          </span>
                        </div>
                      </td>

                      <td>
                        <span
                          className={
                            styles.typeBadge
                          }
                        >
                          {
                            customer.customer_type
                          }
                        </span>
                      </td>

                      <td>
                        <strong
                          className={
                            styles.balance
                          }
                        >
                          {
                            formatCurrency(
                              customer.current_balance,
                            )
                          }
                        </strong>
                      </td>

                      <td>
                        <span
                          className={
                            customer.status
                            === "active"
                              ? styles.activeBadge
                              : styles.inactiveBadge
                          }
                        >
                          {
                            customer.status
                          }
                        </span>
                      </td>
                    </tr>
                  ),
                )
              )}
            </tbody>
          </table>
        </div>


        <div
          className={
            styles.pagination
          }
        >
          <span>
            Page{" "}
            {data.page} of{" "}
            {
              Math.max(
                data.total_pages,
                1,
              )
            }
          </span>

          <div>
            <button
              type="button"
              disabled={
                page <= 1
                || loading
              }
              onClick={
                () =>
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
                size={17}
              />

              Previous
            </button>

            <button
              type="button"
              disabled={
                page
                >= data.total_pages
                || data.total_pages === 0
                || loading
              }
              onClick={
                () =>
                  setPage(
                    (current) =>
                      current + 1,
                  )
              }
            >
              Next

              <ChevronRight
                size={17}
              />
            </button>
          </div>
        </div>
      </section>


      {selectedCustomerId !== null && (
        <CustomerDetailsModal
          customerId={
            selectedCustomerId
          }
          onClose={() =>
            setSelectedCustomerId(
              null,
            )
          }
          onChanged={
            loadCustomers
          }
        />
      )}

      {createOpen && (
        <div
          className={
            styles.modalBackdrop
          }
          role="presentation"
        >
          <div
            className={
              styles.modal
            }
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-customer-title"
          >
            <div
              className={
                styles.modalHeader
              }
            >
              <div>
                <p className="eyebrow">
                  NEW CUSTOMER
                </p>

                <h2
                  id="create-customer-title"
                >
                  Add customer
                </h2>

                <p>
                  Create a customer
                  profile for sales,
                  service and credit
                  operations.
                </p>
              </div>

              <button
                type="button"
                className={
                  styles.closeButton
                }
                onClick={
                  closeCreate
                }
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </div>


            <form
              className={
                styles.customerForm
              }
              onSubmit={
                submitCustomer
              }
            >
              <div
                className={
                  styles.formSection
                }
              >
                <h3>
                  Basic information
                </h3>

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
                    Full name *

                    <input
                      type="text"
                      required
                      minLength={2}
                      maxLength={180}
                      value={
                        form.full_name
                      }
                      onChange={
                        (event) =>
                          setForm({
                            ...form,
                            full_name:
                              event.target.value,
                          })
                      }
                    />
                  </label>

                  <label>
                    Customer type

                    <select
                      value={
                        form.customer_type
                      }
                      onChange={
                        (event) =>
                          setForm({
                            ...form,
                            customer_type:
                              event.target.value
                              === "credit"
                                ? "credit"
                                : "cash",
                          })
                      }
                    >
                      <option value="cash">
                        Cash
                      </option>

                      <option value="credit">
                        Credit
                      </option>
                    </select>
                  </label>

                  <label>
                    Business name

                    <input
                      type="text"
                      maxLength={200}
                      value={
                        form.business_name
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setForm({
                            ...form,
                            business_name:
                              event.target.value,
                          })
                      }
                    />
                  </label>

                  <label>
                    NIC number

                    <input
                      type="text"
                      maxLength={20}
                      value={
                        form.nic_number
                        ?? ""
                      }
                      placeholder={
                        "991234567V "
                        + "or 200012345678"
                      }
                      onChange={
                        (event) =>
                          setForm({
                            ...form,
                            nic_number:
                              event.target.value,
                          })
                      }
                    />
                  </label>

                  <label>
                    Registration number

                    <input
                      type="text"
                      maxLength={100}
                      value={
                        form.registration_number
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setForm({
                            ...form,
                            registration_number:
                              event.target.value,
                          })
                      }
                    />
                  </label>
                </div>
              </div>


              <div
                className={
                  styles.formSection
                }
              >
                <h3>
                  Contact details
                </h3>

                <div
                  className={
                    styles.formGrid
                  }
                >
                  <label>
                    Primary phone *

                    <input
                      type="tel"
                      required
                      maxLength={20}
                      value={
                        form.primary_phone
                      }
                      placeholder="0771234567"
                      onChange={
                        (event) =>
                          setForm({
                            ...form,
                            primary_phone:
                              event.target.value,
                          })
                      }
                    />
                  </label>

                  <label>
                    Secondary phone

                    <input
                      type="tel"
                      maxLength={20}
                      value={
                        form.secondary_phone
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setForm({
                            ...form,
                            secondary_phone:
                              event.target.value,
                          })
                      }
                    />
                  </label>

                  <label>
                    SMS phone

                    <input
                      type="tel"
                      maxLength={20}
                      value={
                        form.sms_phone
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setForm({
                            ...form,
                            sms_phone:
                              event.target.value,
                          })
                      }
                    />
                  </label>

                  <label>
                    Email

                    <input
                      type="email"
                      maxLength={255}
                      value={
                        form.email
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setForm({
                            ...form,
                            email:
                              event.target.value,
                          })
                      }
                    />
                  </label>
                </div>
              </div>


              <div
                className={
                  styles.formSection
                }
              >
                <h3>
                  Address
                </h3>

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
                    Address line 1

                    <input
                      type="text"
                      maxLength={255}
                      value={
                        form.address_line_1
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setForm({
                            ...form,
                            address_line_1:
                              event.target.value,
                          })
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
                      type="text"
                      maxLength={255}
                      value={
                        form.address_line_2
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setForm({
                            ...form,
                            address_line_2:
                              event.target.value,
                          })
                      }
                    />
                  </label>

                  <label>
                    City

                    <input
                      type="text"
                      maxLength={100}
                      value={
                        form.city
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setForm({
                            ...form,
                            city:
                              event.target.value,
                          })
                      }
                    />
                  </label>

                  <label>
                    District

                    <input
                      type="text"
                      maxLength={100}
                      value={
                        form.district
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setForm({
                            ...form,
                            district:
                              event.target.value,
                          })
                      }
                    />
                  </label>

                  <label>
                    Province

                    <input
                      type="text"
                      maxLength={100}
                      value={
                        form.province
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setForm({
                            ...form,
                            province:
                              event.target.value,
                          })
                      }
                    />
                  </label>

                  <label>
                    Postal code

                    <input
                      type="text"
                      maxLength={20}
                      value={
                        form.postal_code
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setForm({
                            ...form,
                            postal_code:
                              event.target.value,
                          })
                      }
                    />
                  </label>
                </div>
              </div>


              <div
                className={
                  styles.formSection
                }
              >
                <h3>
                  Credit settings
                </h3>

                <div
                  className={
                    styles.formGrid
                  }
                >
                  <label>
                    Credit status

                    <select
                      value={
                        form.credit_status
                      }
                      onChange={
                        (event) =>
                          setForm({
                            ...form,
                            credit_status:
                              event.target.value
                              === "allowed"
                                ? "allowed"
                                : "restricted",
                          })
                      }
                    >
                      <option
                        value="restricted"
                      >
                        Restricted
                      </option>

                      <option
                        value="allowed"
                      >
                        Allowed
                      </option>
                    </select>
                  </label>

                  <label>
                    Credit limit

                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={
                        form.credit_limit
                      }
                      onChange={
                        (event) =>
                          setForm({
                            ...form,
                            credit_limit:
                              event.target.value,
                          })
                      }
                    />
                  </label>

                  <label
                    className={
                      styles.checkboxField
                    }
                  >
                    <input
                      type="checkbox"
                      checked={
                        form.sms_allowed
                      }
                      onChange={
                        (event) =>
                          setForm({
                            ...form,
                            sms_allowed:
                              event.target.checked,
                          })
                      }
                    />

                    Allow SMS notifications
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
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setForm({
                            ...form,
                            notes:
                              event.target.value,
                          })
                      }
                    />
                  </label>
                </div>
              </div>


              {formError && (
                <div
                  className={
                    styles.formError
                  }
                >
                  <CircleAlert
                    size={18}
                  />

                  {formError}
                </div>
              )}


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
                    saving
                  }
                  onClick={
                    closeCreate
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
                    saving
                  }
                >
                  {saving
                    ? "Saving..."
                    : "Create customer"
                  }
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppShell>
  );
}
