"use client";

import axios from "axios";

import {
  Barcode,
  Boxes,
  CircleAlert,
  PackagePlus,
  Plus,
  Trash2,
  X,
} from "lucide-react";

import {
  FormEvent,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getProducts,
} from "@/lib/catalog-api";

import {
  receiveNonSerializedStock,
  receiveSerializedStock,
} from "@/lib/inventory-api";

import type {
  Product,
} from "@/types/catalog";

import type {
  Warehouse,
} from "@/types/inventory";

import styles from "@/app/inventory/inventory.module.css";


type Props = {
  warehouses: Warehouse[];

  onClose: () => void;

  onReceived:
    () => Promise<void> | void;
};


type FormState = {
  productId: string;
  warehouseId: string;

  quantity: string;
  unitCost: string;

  referenceType: string;
  referenceId: string;

  notes: string;
};


const emptyForm: FormState = {
  productId: "",
  warehouseId: "",

  quantity: "1.000",
  unitCost: "0.00",

  referenceType:
    "opening_balance",

  referenceId: "",

  notes: "",
};


function optional(
  value: string,
): string | null {
  const clean =
    value.trim();

  return clean || null;
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
      + "to receive inventory."
    );
  }

  if (
    error.response?.status
    === 409
  ) {
    return (
      "This stock receipt conflicts "
      + "with existing inventory data. "
      + "Check serial numbers or "
      + "reference information."
    );
  }

  return (
    "Unable to receive stock."
  );
}


function uniqueSerials(
  raw: string,
): {
  serials: string[];
  duplicates: string[];
} {
  const lines =
    raw
      .split(/\r?\n|,/)
      .map(
        (item) =>
          item.trim(),
      )
      .filter(Boolean);

  const seen =
    new Set<string>();

  const serials:
    string[] = [];

  const duplicateSet =
    new Set<string>();

  for (
    const serial of lines
  ) {
    const normalized =
      serial.toUpperCase();

    if (
      seen.has(
        normalized,
      )
    ) {
      duplicateSet.add(
        serial,
      );

      continue;
    }

    seen.add(
      normalized,
    );

    serials.push(
      serial,
    );
  }

  return {
    serials,

    duplicates:
      Array.from(
        duplicateSet,
      ),
  };
}


export function ReceiveStockModal({
  warehouses,
  onClose,
  onReceived,
}: Props) {
  const [
    products,
    setProducts,
  ] =
    useState<Product[]>(
      [],
    );

  const [
    loadingProducts,
    setLoadingProducts,
  ] =
    useState(true);

  const [
    saving,
    setSaving,
  ] =
    useState(false);

  const [
    error,
    setError,
  ] =
    useState("");

  const [
    form,
    setForm,
  ] =
    useState<FormState>({
      ...emptyForm,

      warehouseId:
        warehouses[0]
          ? String(
              warehouses[0].id,
            )
          : "",
    });

  const [
    serialInput,
    setSerialInput,
  ] =
    useState("");


  useEffect(() => {
    let cancelled =
      false;

    const timer =
      window.setTimeout(
        () => {
          async function load() {
            setLoadingProducts(
              true,
            );

            setError("");

            try {
              const response =
                await getProducts({
                  page: 1,
                  pageSize: 100,
                });

              if (cancelled) {
                return;
              }

              const active =
                response.items.filter(
                  (product) =>
                    product.is_active,
                );

              setProducts(
                active,
              );

              if (
                active.length > 0
              ) {
                setForm(
                  (current) => ({
                    ...current,

                    productId:
                      current.productId
                      || String(
                          active[0].id,
                        ),

                    unitCost:
                      current.unitCost
                      !== "0.00"
                        ? current.unitCost
                        : String(
                            active[0]
                              .purchase_cost
                            ?? "0.00",
                          ),
                  }),
                );
              }
            } catch (
              requestError
            ) {
              if (!cancelled) {
                setError(
                  apiError(
                    requestError,
                  ),
                );
              }
            } finally {
              if (!cancelled) {
                setLoadingProducts(
                  false,
                );
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
  }, []);


  const selectedProduct =
    useMemo(
      () =>
        products.find(
          (product) =>
            String(
              product.id,
            )
            === form.productId,
        )
        ?? null,
      [
        products,
        form.productId,
      ],
    );


  const serialized =
    selectedProduct
      ?.track_serial_numbers
    ?? false;


  const parsedSerials =
    useMemo(
      () =>
        uniqueSerials(
          serialInput,
        ),
      [serialInput],
    );


  function selectProduct(
    productId: string,
  ) {
    const product =
      products.find(
        (item) =>
          String(
            item.id,
          )
          === productId,
      );

    setForm(
      (current) => ({
        ...current,

        productId,

        unitCost:
          product
            ? String(
                product.purchase_cost
                ?? "0.00",
              )
            : current.unitCost,
      }),
    );

    setSerialInput(
      "",
    );

    setError(
      "",
    );
  }


  function addSerialRow() {
    setSerialInput(
      (current) => {
        if (
          current.length === 0
        ) {
          return "";
        }

        return current.endsWith(
          "\n",
        )
          ? current
          : current + "\n";
      },
    );
  }


  function clearSerials() {
    setSerialInput(
      "",
    );
  }


  async function submit(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setError(
      "",
    );

    const productId =
      Number(
        form.productId,
      );

    const warehouseId =
      Number(
        form.warehouseId,
      );

    const unitCost =
      Number(
        form.unitCost,
      );


    if (
      !Number.isInteger(
        productId,
      )
      || productId < 1
    ) {
      setError(
        "Please select a product.",
      );

      return;
    }


    if (
      !Number.isInteger(
        warehouseId,
      )
      || warehouseId < 1
    ) {
      setError(
        "Please select a warehouse.",
      );

      return;
    }


    if (
      !Number.isFinite(
        unitCost,
      )
      || unitCost < 0
    ) {
      setError(
        "Unit cost must be zero "
        + "or greater.",
      );

      return;
    }


    if (
      serialized
    ) {
      if (
        parsedSerials
          .duplicates.length > 0
      ) {
        setError(
          "Duplicate serial numbers "
          + "entered: "
          + parsedSerials
              .duplicates
              .join(", "),
        );

        return;
      }

      if (
        parsedSerials
          .serials.length === 0
      ) {
        setError(
          "Enter at least one "
          + "serial number.",
        );

        return;
      }
    } else {
      const amount =
        Number(
          form.quantity,
        );

      if (
        !Number.isFinite(
          amount,
        )
        || amount <= 0
      ) {
        setError(
          "Quantity must be "
          + "greater than zero.",
        );

        return;
      }
    }


    setSaving(
      true,
    );

    try {
      if (
        serialized
      ) {
        await receiveSerializedStock({
          product_id:
            productId,

          warehouse_id:
            warehouseId,

          unit_cost:
            form.unitCost,

          reference_type:
            form.referenceType
              .trim(),

          reference_id:
            optional(
              form.referenceId,
            ),

          notes:
            optional(
              form.notes,
            ),

          serials:
            parsedSerials
              .serials
              .map(
                (
                  serialNumber,
                ) => ({
                  serial_number:
                    serialNumber,
                }),
              ),
        });
      } else {
        await receiveNonSerializedStock({
          product_id:
            productId,

          warehouse_id:
            warehouseId,

          quantity:
            form.quantity,

          unit_cost:
            form.unitCost,

          reference_type:
            form.referenceType
              .trim(),

          reference_id:
            optional(
              form.referenceId,
            ),

          notes:
            optional(
              form.notes,
            ),
        });
      }

      await onReceived();

      onClose();
    } catch (
      requestError
    ) {
      setError(
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


  return (
    <div
      className={
        styles.receiveBackdrop
      }
    >
      <section
        className={
          styles.receiveModal
        }
        role="dialog"
        aria-modal="true"
        aria-labelledby={
          "receive-stock-title"
        }
      >
        <header
          className={
            styles.receiveHeader
          }
        >
          <div>
            <p className="eyebrow">
              INVENTORY RECEIPT
            </p>

            <h2
              id="receive-stock-title"
            >
              Receive stock
            </h2>

            <p>
              Receive standard or
              serialized inventory into
              a warehouse.
            </p>
          </div>

          <button
            type="button"
            className={
              styles.detailIconButton
            }
            disabled={
              saving
            }
            onClick={
              onClose
            }
            aria-label="Close"
          >
            <X size={19} />
          </button>
        </header>


        <form
          className={
            styles.receiveForm
          }
          onSubmit={
            submit
          }
        >
          <section
            className={
              styles.receiveSection
            }
          >
            <div
              className={
                styles.receiveSectionTitle
              }
            >
              <div>
                <h3>
                  Stock destination
                </h3>

                <p>
                  Select the product and
                  destination warehouse.
                </p>
              </div>
            </div>


            <div
              className={
                styles.receiveGrid
              }
            >
              <label
                className={
                  styles.receiveFullField
                }
              >
                Product *

                <select
                  required
                  disabled={
                    loadingProducts
                    || saving
                  }
                  value={
                    form.productId
                  }
                  onChange={
                    (event) =>
                      selectProduct(
                        event
                          .target
                          .value,
                      )
                  }
                >
                  <option value="">
                    {loadingProducts
                      ? "Loading products..."
                      : "Select product"
                    }
                  </option>

                  {products.map(
                    (product) => (
                      <option
                        key={
                          product.id
                        }
                        value={
                          product.id
                        }
                      >
                        {
                          product
                            .product_code
                        }
                        {" — "}
                        {
                          product.name
                        }
                        {" — "}
                        {product
                          .track_serial_numbers
                          ? "Serialized"
                          : "Standard"
                        }
                      </option>
                    ),
                  )}
                </select>
              </label>


              <label>
                Warehouse *

                <select
                  required
                  disabled={
                    saving
                  }
                  value={
                    form.warehouseId
                  }
                  onChange={
                    (event) =>
                      setForm({
                        ...form,

                        warehouseId:
                          event
                            .target
                            .value,
                      })
                  }
                >
                  <option value="">
                    Select warehouse
                  </option>

                  {warehouses.map(
                    (warehouse) => (
                      <option
                        key={
                          warehouse.id
                        }
                        value={
                          warehouse.id
                        }
                      >
                        {
                          warehouse.code
                        }
                        {" — "}
                        {
                          warehouse.name
                        }
                      </option>
                    ),
                  )}
                </select>
              </label>


              <label>
                Unit cost *

                <input
                  type="number"
                  min="0"
                  step="0.01"
                  required
                  disabled={
                    saving
                  }
                  value={
                    form.unitCost
                  }
                  onChange={
                    (event) =>
                      setForm({
                        ...form,

                        unitCost:
                          event
                            .target
                            .value,
                      })
                  }
                />
              </label>
            </div>


            {selectedProduct && (
              <div
                className={
                  serialized
                    ? styles
                        .serializedModeCard
                    : styles
                        .standardModeCard
                }
              >
                <div
                  className={
                    styles.receiveModeIcon
                  }
                >
                  {serialized
                    ? (
                      <Barcode
                        size={19}
                      />
                    )
                    : (
                      <Boxes
                        size={19}
                      />
                    )
                  }
                </div>

                <div>
                  <strong>
                    {serialized
                      ? (
                        "Serialized stock"
                      )
                      : (
                        "Standard stock"
                      )
                    }
                  </strong>

                  <span>
                    {serialized
                      ? (
                        "Every physical unit "
                        + "must have a unique "
                        + "serial number."
                      )
                      : (
                        "Stock is managed "
                        + "by quantity."
                      )
                    }
                  </span>
                </div>
              </div>
            )}
          </section>


          {!serialized && (
            <section
              className={
                styles.receiveSection
              }
            >
              <div
                className={
                  styles.receiveSectionTitle
                }
              >
                <div>
                  <h3>
                    Standard stock
                  </h3>

                  <p>
                    Enter the quantity
                    being received.
                  </p>
                </div>
              </div>

              <div
                className={
                  styles.receiveGrid
                }
              >
                <label>
                  Quantity *

                  <input
                    type="number"
                    min="0.001"
                    step="0.001"
                    required
                    disabled={
                      saving
                    }
                    value={
                      form.quantity
                    }
                    onChange={
                      (event) =>
                        setForm({
                          ...form,

                          quantity:
                            event
                              .target
                              .value,
                        })
                    }
                  />
                </label>

                <div
                  className={
                    styles.receiveInfoCard
                  }
                >
                  <Boxes
                    size={18}
                  />

                  <div>
                    <span>
                      Receipt quantity
                    </span>

                    <strong>
                      {
                        form.quantity
                        || "0"
                      }
                    </strong>
                  </div>
                </div>
              </div>
            </section>
          )}


          {serialized && (
            <section
              className={
                styles.receiveSection
              }
            >
              <div
                className={
                  styles.receiveSectionTitle
                }
              >
                <div>
                  <h3>
                    Serial numbers
                  </h3>

                  <p>
                    Enter one serial per
                    line. Comma-separated
                    values are also accepted.
                  </p>
                </div>

                <span
                  className={
                    styles.receiveCountBadge
                  }
                >
                  {
                    parsedSerials
                      .serials.length
                  }
                  {" "}
                  units
                </span>
              </div>


              <textarea
                className={
                  styles.serialEntry
                }
                rows={8}
                disabled={
                  saving
                }
                value={
                  serialInput
                }
                placeholder={
                  "SN-000001\n"
                  + "SN-000002\n"
                  + "SN-000003"
                }
                onChange={
                  (event) =>
                    setSerialInput(
                      event
                        .target
                        .value,
                    )
                }
              />


              <div
                className={
                  styles.serialEntryActions
                }
              >
                <button
                  type="button"
                  disabled={
                    saving
                  }
                  onClick={
                    addSerialRow
                  }
                >
                  <Plus
                    size={15}
                  />

                  New line
                </button>

                <button
                  type="button"
                  disabled={
                    saving
                    || serialInput
                      .length === 0
                  }
                  onClick={
                    clearSerials
                  }
                >
                  <Trash2
                    size={15}
                  />

                  Clear serials
                </button>
              </div>


              {parsedSerials
                .duplicates.length
                > 0 && (
                <div
                  className={
                    styles.receiveWarning
                  }
                >
                  <CircleAlert
                    size={16}
                  />

                  Duplicate entries:
                  {" "}
                  {
                    parsedSerials
                      .duplicates
                      .join(", ")
                  }
                </div>
              )}
            </section>
          )}


          <section
            className={
              styles.receiveSection
            }
          >
            <div
              className={
                styles.receiveSectionTitle
              }
            >
              <div>
                <h3>
                  Receipt reference
                </h3>

                <p>
                  Record where this stock
                  receipt came from.
                </p>
              </div>
            </div>


            <div
              className={
                styles.receiveGrid
              }
            >
              <label>
                Reference type *

                <select
                  required
                  disabled={
                    saving
                  }
                  value={
                    form.referenceType
                  }
                  onChange={
                    (event) =>
                      setForm({
                        ...form,

                        referenceType:
                          event
                            .target
                            .value,
                      })
                  }
                >
                  <option
                    value={
                      "opening_balance"
                    }
                  >
                    Opening balance
                  </option>

                  <option
                    value={
                      "purchase"
                    }
                  >
                    Purchase receipt
                  </option>

                  <option
                    value={
                      "manual_receipt"
                    }
                  >
                    Manual receipt
                  </option>
                </select>
              </label>


              <label>
                Reference ID

                <input
                  type="text"
                  maxLength={100}
                  disabled={
                    saving
                  }
                  value={
                    form.referenceId
                  }
                  placeholder={
                    "PO-000123 / OPEN-001"
                  }
                  onChange={
                    (event) =>
                      setForm({
                        ...form,

                        referenceId:
                          event
                            .target
                            .value,
                      })
                  }
                />
              </label>


              <label
                className={
                  styles.receiveFullField
                }
              >
                Notes

                <textarea
                  rows={3}
                  disabled={
                    saving
                  }
                  value={
                    form.notes
                  }
                  placeholder={
                    "Optional receipt notes"
                  }
                  onChange={
                    (event) =>
                      setForm({
                        ...form,

                        notes:
                          event
                            .target
                            .value,
                      })
                  }
                />
              </label>
            </div>
          </section>


          {error && (
            <div
              className={
                styles.receiveError
              }
            >
              <CircleAlert
                size={17}
              />

              {error}
            </div>
          )}


          <footer
            className={
              styles.receiveFooter
            }
          >
            <div
              className={
                styles.receiveFooterHint
              }
            >
              {serialized
                ? (
                  <>
                    <Barcode
                      size={15}
                    />

                    {
                      parsedSerials
                        .serials.length
                    }
                    {" "}
                    serialized units
                  </>
                )
                : (
                  <>
                    <Boxes
                      size={15}
                    />

                    {
                      form.quantity
                      || "0"
                    }
                    {" "}
                    standard units
                  </>
                )
              }
            </div>

            <div
              className={
                styles.receiveFooterButtons
              }
            >
              <button
                type="button"
                className={
                  styles.receiveCancelButton
                }
                disabled={
                  saving
                }
                onClick={
                  onClose
                }
              >
                Cancel
              </button>

              <button
                type="submit"
                className={
                  styles.receiveSubmitButton
                }
                disabled={
                  saving
                  || loadingProducts
                  || !selectedProduct
                }
              >
                {saving
                  ? (
                    "Receiving..."
                  )
                  : (
                    <>
                      <PackagePlus
                        size={17}
                      />

                      Receive stock
                    </>
                  )
                }
              </button>
            </div>
          </footer>
        </form>
      </section>
    </div>
  );
}
