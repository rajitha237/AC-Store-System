"use client";

import axios from "axios";

import {
  Building2,
  CircleAlert,
  CreditCard,
  Edit3,
  Mail,
  MapPin,
  Phone,
  Power,
  PowerOff,
  Save,
  ShieldCheck,
  UserRound,
  X,
} from "lucide-react";

import {
  FormEvent,
  useEffect,
  useState,
} from "react";

import {
  deactivateCustomer,
  getCustomer,
  reactivateCustomer,
  updateCustomer,
} from "@/lib/customer-api";

import type {
  Customer,
  CustomerUpdatePayload,
} from "@/types/customer";

import styles from "@/app/customers/customers.module.css";


type Props = {
  customerId: number;
  onClose: () => void;
  onChanged: () => Promise<void> | void;
};


type EditForm = {
  full_name: string;
  business_name: string;
  customer_type: "cash" | "credit";

  nic_number: string;
  registration_number: string;

  primary_phone: string;
  secondary_phone: string;
  sms_phone: string;

  email: string;

  address_line_1: string;
  address_line_2: string;
  city: string;
  district: string;
  province: string;
  postal_code: string;

  credit_status:
    | "restricted"
    | "allowed";

  credit_limit: string;

  sms_allowed: boolean;

  notes: string;
};


function emptyForm(): EditForm {
  return {
    full_name: "",
    business_name: "",
    customer_type: "cash",

    nic_number: "",
    registration_number: "",

    primary_phone: "",
    secondary_phone: "",
    sms_phone: "",

    email: "",

    address_line_1: "",
    address_line_2: "",
    city: "",
    district: "",
    province: "",
    postal_code: "",

    credit_status: "restricted",
    credit_limit: "0.00",

    sms_allowed: true,

    notes: "",
  };
}


function customerToForm(
  customer: Customer,
): EditForm {
  return {
    full_name:
      customer.full_name,

    business_name:
      customer.business_name ?? "",

    customer_type:
      customer.customer_type,

    nic_number:
      customer.nic_number ?? "",

    registration_number:
      customer.registration_number ?? "",

    primary_phone:
      customer.primary_phone,

    secondary_phone:
      customer.secondary_phone ?? "",

    sms_phone:
      customer.sms_phone ?? "",

    email:
      customer.email ?? "",

    address_line_1:
      customer.address_line_1 ?? "",

    address_line_2:
      customer.address_line_2 ?? "",

    city:
      customer.city ?? "",

    district:
      customer.district ?? "",

    province:
      customer.province ?? "",

    postal_code:
      customer.postal_code ?? "",

    credit_status:
      customer.credit_status,

    credit_limit:
      String(
        customer.credit_limit ?? "0.00",
      ),

    sms_allowed:
      customer.sms_allowed,

    notes:
      customer.notes ?? "",
  };
}


function optional(
  value: string,
): string | null {
  const normalized =
    value.trim();

  return normalized || null;
}


function currency(
  value: string | number,
): string {
  const number =
    Number(value ?? 0);

  if (!Number.isFinite(number)) {
    return "LKR 0.00";
  }

  return new Intl.NumberFormat(
    "en-LK",
    {
      style: "currency",
      currency: "LKR",
      minimumFractionDigits: 2,
    },
  ).format(number);
}


function dateTime(
  value: string,
): string {
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
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(date);
}


function apiError(
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

  if (
    typeof detail === "string"
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
    error.response?.status === 403
  ) {
    return (
      "You do not have permission "
      + "to update this customer."
    );
  }

  if (
    error.response?.status === 404
  ) {
    return (
      "Customer record was not found."
    );
  }

  return (
    "Unable to complete the request."
  );
}


export function CustomerDetailsModal({
  customerId,
  onClose,
  onChanged,
}: Props) {
  const [
    customer,
    setCustomer,
  ] =
    useState<Customer | null>(
      null,
    );

  const [
    form,
    setForm,
  ] =
    useState<EditForm>(
      emptyForm,
    );

  const [
    loading,
    setLoading,
  ] =
    useState(true);

  const [
    editing,
    setEditing,
  ] =
    useState(false);

  const [
    saving,
    setSaving,
  ] =
    useState(false);

  const [
    changingStatus,
    setChangingStatus,
  ] =
    useState(false);

  const [
    error,
    setError,
  ] =
    useState("");


  useEffect(() => {
    let cancelled = false;

    const timer =
      window.setTimeout(
        () => {
          async function load() {
            setLoading(true);
            setError("");

            try {
              const response =
                await getCustomer(
                  customerId,
                );

              if (cancelled) {
                return;
              }

              setCustomer(
                response,
              );

              setForm(
                customerToForm(
                  response,
                ),
              );
            } catch (requestError) {
              if (!cancelled) {
                setError(
                  apiError(
                    requestError,
                  ),
                );
              }
            } finally {
              if (!cancelled) {
                setLoading(false);
              }
            }
          }

          void load();
        },
        0,
      );

    return () => {
      cancelled = true;

      window.clearTimeout(
        timer,
      );
    };
  }, [customerId]);


  function startEdit() {
    if (!customer) {
      return;
    }

    setForm(
      customerToForm(
        customer,
      ),
    );

    setError("");
    setEditing(true);
  }


  function cancelEdit() {
    if (saving) {
      return;
    }

    if (customer) {
      setForm(
        customerToForm(
          customer,
        ),
      );
    }

    setError("");
    setEditing(false);
  }


  async function submitEdit(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (
      form.full_name
        .trim()
        .length < 2
    ) {
      setError(
        "Full name is required.",
      );

      return;
    }

    if (
      !form.primary_phone.trim()
    ) {
      setError(
        "Primary phone is required.",
      );

      return;
    }

    setSaving(true);
    setError("");

    const payload:
      CustomerUpdatePayload = {
        full_name:
          form.full_name.trim(),

        business_name:
          optional(
            form.business_name,
          ),

        customer_type:
          form.customer_type,

        nic_number:
          optional(
            form.nic_number,
          ),

        registration_number:
          optional(
            form.registration_number,
          ),

        primary_phone:
          form.primary_phone.trim(),

        secondary_phone:
          optional(
            form.secondary_phone,
          ),

        sms_phone:
          optional(
            form.sms_phone,
          ),

        email:
          optional(
            form.email,
          ),

        address_line_1:
          optional(
            form.address_line_1,
          ),

        address_line_2:
          optional(
            form.address_line_2,
          ),

        city:
          optional(
            form.city,
          ),

        district:
          optional(
            form.district,
          ),

        province:
          optional(
            form.province,
          ),

        postal_code:
          optional(
            form.postal_code,
          ),

        credit_status:
          form.credit_status,

        credit_limit:
          form.credit_limit
          || "0.00",

        sms_allowed:
          form.sms_allowed,

        notes:
          optional(
            form.notes,
          ),
      };

    try {
      const updated =
        await updateCustomer(
          customerId,
          payload,
        );

      setCustomer(
        updated,
      );

      setForm(
        customerToForm(
          updated,
        ),
      );

      setEditing(false);

      await onChanged();
    } catch (requestError) {
      setError(
        apiError(
          requestError,
        ),
      );
    } finally {
      setSaving(false);
    }
  }


  async function changeStatus() {
    if (!customer) {
      return;
    }

    const activating =
      customer.status
      === "inactive";

    const confirmed =
      window.confirm(
        activating
          ? (
            "Reactivate this customer?"
          )
          : (
            "Deactivate this customer? "
            + "The record will remain "
            + "available for history."
          ),
      );

    if (!confirmed) {
      return;
    }

    setChangingStatus(true);
    setError("");

    try {
      const updated =
        activating
          ? await reactivateCustomer(
              customer.id,
            )
          : await deactivateCustomer(
              customer.id,
            );

      setCustomer(
        updated,
      );

      setForm(
        customerToForm(
          updated,
        ),
      );

      setEditing(false);

      await onChanged();
    } catch (requestError) {
      setError(
        apiError(
          requestError,
        ),
      );
    } finally {
      setChangingStatus(false);
    }
  }


  const busy =
    loading
    || saving
    || changingStatus;


  return (
    <div
      className={
        styles.detailBackdrop
      }
      role="presentation"
    >
      <section
        className={
          styles.detailDrawer
        }
        role="dialog"
        aria-modal="true"
        aria-labelledby={
          "customer-details-title"
        }
      >
        <header
          className={
            styles.detailHeader
          }
        >
          <div>
            <p className="eyebrow">
              CUSTOMER PROFILE
            </p>

            <h2
              id="customer-details-title"
            >
              {customer
                ? customer.full_name
                : "Customer details"
              }
            </h2>

            {customer && (
              <span
                className={
                  styles.customerNumber
                }
              >
                {customer.customer_number}
              </span>
            )}
          </div>

          <button
            type="button"
            className={
              styles.closeButton
            }
            onClick={
              onClose
            }
            disabled={
              saving
              || changingStatus
            }
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </header>


        {loading ? (
          <div
            className={
              styles.detailLoading
            }
          >
            <div
              className="loading-spinner"
            />

            Loading customer...
          </div>
        ) : !customer ? (
          <div
            className={
              styles.detailLoading
            }
          >
            <CircleAlert
              size={28}
            />

            {error
              || "Customer could not be loaded."
            }
          </div>
        ) : (
          <>
            <div
              className={
                styles.profileSummary
              }
            >
              <div
                className={
                  styles.profileAvatar
                }
              >
                <UserRound
                  size={26}
                />
              </div>

              <div
                className={
                  styles.profileIdentity
                }
              >
                <strong>
                  {customer.full_name}
                </strong>

                <span>
                  {customer.business_name
                    || "Individual customer"
                  }
                </span>
              </div>

              <span
                className={
                  customer.status
                  === "active"
                    ? styles.activeBadge
                    : styles.inactiveBadge
                }
              >
                {customer.status}
              </span>
            </div>


            <div
              className={
                styles.creditSummaryGrid
              }
            >
              <article>
                <span>
                  Current balance
                </span>

                <strong>
                  {currency(
                    customer.current_balance,
                  )}
                </strong>
              </article>

              <article>
                <span>
                  Credit limit
                </span>

                <strong>
                  {currency(
                    customer.credit_limit,
                  )}
                </strong>
              </article>

              <article>
                <span>
                  Credit status
                </span>

                <strong
                  className={
                    styles.capitalize
                  }
                >
                  {customer.credit_status}
                </strong>
              </article>
            </div>


            {error && (
              <div
                className={
                  styles.detailError
                }
              >
                <CircleAlert
                  size={17}
                />

                {error}
              </div>
            )}


            {editing ? (
              <form
                className={
                  styles.editCustomerForm
                }
                onSubmit={
                  submitEdit
                }
              >
                <section
                  className={
                    styles.detailSection
                  }
                >
                  <h3>
                    Basic information
                  </h3>

                  <div
                    className={
                      styles.detailFormGrid
                    }
                  >
                    <label
                      className={
                        styles.detailFullField
                      }
                    >
                      Full name *

                      <input
                        type="text"
                        minLength={2}
                        maxLength={180}
                        required
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
                      NIC

                      <input
                        type="text"
                        maxLength={20}
                        value={
                          form.nic_number
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
                </section>


                <section
                  className={
                    styles.detailSection
                  }
                >
                  <h3>
                    Contact
                  </h3>

                  <div
                    className={
                      styles.detailFormGrid
                    }
                  >
                    <label>
                      Primary phone *

                      <input
                        type="tel"
                        maxLength={20}
                        required
                        value={
                          form.primary_phone
                        }
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
                </section>


                <section
                  className={
                    styles.detailSection
                  }
                >
                  <h3>
                    Address
                  </h3>

                  <div
                    className={
                      styles.detailFormGrid
                    }
                  >
                    <label
                      className={
                        styles.detailFullField
                      }
                    >
                      Address line 1

                      <input
                        type="text"
                        maxLength={255}
                        value={
                          form.address_line_1
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
                        styles.detailFullField
                      }
                    >
                      Address line 2

                      <input
                        type="text"
                        maxLength={255}
                        value={
                          form.address_line_2
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
                </section>


                <section
                  className={
                    styles.detailSection
                  }
                >
                  <h3>
                    Credit settings
                  </h3>

                  <div
                    className={
                      styles.detailFormGrid
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
                        styles.detailCheckbox
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

                      Allow SMS
                    </label>

                    <label
                      className={
                        styles.detailFullField
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
                            setForm({
                              ...form,
                              notes:
                                event.target.value,
                            })
                        }
                      />
                    </label>
                  </div>
                </section>


                <div
                  className={
                    styles.detailActionBar
                  }
                >
                  <button
                    type="button"
                    className={
                      styles.secondaryAction
                    }
                    onClick={
                      cancelEdit
                    }
                    disabled={
                      saving
                    }
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    className={
                      styles.primaryAction
                    }
                    disabled={
                      saving
                    }
                  >
                    <Save size={17} />

                    {saving
                      ? "Saving..."
                      : "Save changes"
                    }
                  </button>
                </div>
              </form>
            ) : (
              <>
                <section
                  className={
                    styles.detailSection
                  }
                >
                  <h3>
                    Contact information
                  </h3>

                  <div
                    className={
                      styles.infoGrid
                    }
                  >
                    <div>
                      <Phone size={16} />

                      <span>
                        Primary phone
                      </span>

                      <strong>
                        {customer.primary_phone}
                      </strong>
                    </div>

                    <div>
                      <Phone size={16} />

                      <span>
                        Secondary phone
                      </span>

                      <strong>
                        {customer.secondary_phone
                          || "—"
                        }
                      </strong>
                    </div>

                    <div>
                      <Mail size={16} />

                      <span>
                        Email
                      </span>

                      <strong>
                        {customer.email
                          || "—"
                        }
                      </strong>
                    </div>

                    <div>
                      <ShieldCheck
                        size={16}
                      />

                      <span>
                        SMS phone
                      </span>

                      <strong>
                        {customer.sms_phone
                          || "—"
                        }
                      </strong>
                    </div>
                  </div>
                </section>


                <section
                  className={
                    styles.detailSection
                  }
                >
                  <h3>
                    Identity & business
                  </h3>

                  <div
                    className={
                      styles.infoGrid
                    }
                  >
                    <div>
                      <UserRound size={16} />

                      <span>
                        NIC number
                      </span>

                      <strong>
                        {customer.nic_number
                          || "—"
                        }
                      </strong>
                    </div>

                    <div>
                      <Building2 size={16} />

                      <span>
                        Business
                      </span>

                      <strong>
                        {customer.business_name
                          || "—"
                        }
                      </strong>
                    </div>

                    <div>
                      <Building2 size={16} />

                      <span>
                        Registration
                      </span>

                      <strong>
                        {customer.registration_number
                          || "—"
                        }
                      </strong>
                    </div>

                    <div>
                      <CreditCard size={16} />

                      <span>
                        Customer type
                      </span>

                      <strong
                        className={
                          styles.capitalize
                        }
                      >
                        {customer.customer_type}
                      </strong>
                    </div>
                  </div>
                </section>


                <section
                  className={
                    styles.detailSection
                  }
                >
                  <h3>
                    Address
                  </h3>

                  <div
                    className={
                      styles.addressCard
                    }
                  >
                    <MapPin size={17} />

                    <div>
                      <strong>
                        {[
                          customer.address_line_1,
                          customer.address_line_2,
                        ]
                          .filter(Boolean)
                          .join(", ")
                          || "No address recorded"
                        }
                      </strong>

                      <span>
                        {[
                          customer.city,
                          customer.district,
                          customer.province,
                          customer.postal_code,
                        ]
                          .filter(Boolean)
                          .join(" • ")
                          || "—"
                        }
                      </span>
                    </div>
                  </div>
                </section>


                <section
                  className={
                    styles.detailSection
                  }
                >
                  <h3>
                    Record information
                  </h3>

                  <div
                    className={
                      styles.recordGrid
                    }
                  >
                    <div>
                      <span>
                        SMS allowed
                      </span>

                      <strong>
                        {customer.sms_allowed
                          ? "Yes"
                          : "No"
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        Created
                      </span>

                      <strong>
                        {dateTime(
                          customer.created_at,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Last updated
                      </span>

                      <strong>
                        {dateTime(
                          customer.updated_at,
                        )}
                      </strong>
                    </div>
                  </div>

                  {customer.notes && (
                    <div
                      className={
                        styles.notesCard
                      }
                    >
                      <span>
                        Notes
                      </span>

                      <p>
                        {customer.notes}
                      </p>
                    </div>
                  )}
                </section>


                <div
                  className={
                    styles.detailActionBar
                  }
                >
                  <button
                    type="button"
                    className={
                      customer.status
                      === "active"
                        ? styles.dangerAction
                        : styles.activateAction
                    }
                    disabled={
                      busy
                    }
                    onClick={
                      changeStatus
                    }
                  >
                    {customer.status
                    === "active"
                      ? (
                        <>
                          <PowerOff
                            size={17}
                          />
                          Deactivate
                        </>
                      )
                      : (
                        <>
                          <Power
                            size={17}
                          />
                          Reactivate
                        </>
                      )
                    }
                  </button>

                  <button
                    type="button"
                    className={
                      styles.primaryAction
                    }
                    onClick={
                      startEdit
                    }
                    disabled={
                      busy
                    }
                  >
                    <Edit3 size={17} />
                    Edit customer
                  </button>
                </div>
              </>
            )}
          </>
        )}
      </section>
    </div>
  );
}
