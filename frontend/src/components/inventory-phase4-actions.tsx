"use client";

import axios from "axios";

import {
  ArrowLeftRight,
  Check,
  ChevronRight,
  CircleAlert,
  Minus,
  PackageSearch,
  Plus,
  RefreshCw,
  SlidersHorizontal,
  Warehouse as WarehouseIcon,
  X,
} from "lucide-react";

import {
  FormEvent,
  useMemo,
  useState,
} from "react";

import {
  getProducts,
} from "@/lib/catalog-api";

import {
  adjustStock,
  getSerialNumbers,
  transferNonSerializedStock,
  transferSerializedStock,
} from "@/lib/inventory-api";

import type {
  Product,
} from "@/types/catalog";

import type {
  SerialNumberDetail,
  StockAdjustmentDirection,
  Warehouse,
} from "@/types/inventory";

import styles from "@/app/inventory/inventory.module.css";


type Props = {
  warehouses: Warehouse[];

  onChanged:
    () => Promise<void> | void;
};


type AdjustmentForm = {
  productId: string;
  warehouseId: string;

  direction:
    StockAdjustmentDirection;

  quantity: string;
  unitCost: string;

  referenceId: string;
  reason: string;
  notes: string;
};


type TransferForm = {
  productId: string;

  sourceWarehouseId: string;
  destinationWarehouseId: string;

  quantity: string;

  referenceId: string;
  reason: string;
  notes: string;
};


const emptyAdjustment:
  AdjustmentForm = {
    productId: "",
    warehouseId: "",

    direction: "increase",

    quantity: "1.000",
    unitCost: "",

    referenceId: "",
    reason: "",
    notes: "",
  };


const emptyTransfer:
  TransferForm = {
    productId: "",

    sourceWarehouseId: "",
    destinationWarehouseId: "",

    quantity: "1.000",

    referenceId: "",
    reason: "",
    notes: "",
  };


function optionalText(
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
      + "to adjust or transfer inventory."
    );
  }

  return (
    "Unable to complete "
    + "the inventory operation."
  );
}


function quantity(
  value:
    | string
    | number,
): string {
  const parsed =
    Number(value);

  if (
    !Number.isFinite(
      parsed,
    )
  ) {
    return "0";
  }

  return new Intl.NumberFormat(
    "en-LK",
    {
      maximumFractionDigits:
        3,
    },
  ).format(parsed);
}


export function InventoryPhase4Actions({
  warehouses,
  onChanged,
}: Props) {
  const [
    products,
    setProducts,
  ] =
    useState<Product[]>(
      [],
    );

  const [
    productsLoaded,
    setProductsLoaded,
  ] =
    useState(false);

  const [
    loadingProducts,
    setLoadingProducts,
  ] =
    useState(false);

  const [
    adjustOpen,
    setAdjustOpen,
  ] =
    useState(false);

  const [
    transferOpen,
    setTransferOpen,
  ] =
    useState(false);

  const [
    adjustment,
    setAdjustment,
  ] =
    useState<AdjustmentForm>({
      ...emptyAdjustment,
    });

  const [
    transfer,
    setTransfer,
  ] =
    useState<TransferForm>({
      ...emptyTransfer,
    });

  const [
    serials,
    setSerials,
  ] =
    useState<
      SerialNumberDetail[]
    >(
      [],
    );

  const [
    selectedSerialIds,
    setSelectedSerialIds,
  ] =
    useState<number[]>(
      [],
    );

  const [
    loadingSerials,
    setLoadingSerials,
  ] =
    useState(false);

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
    confirmingAdjustment,
    setConfirmingAdjustment,
  ] =
    useState(false);

  const [
    confirmingTransfer,
    setConfirmingTransfer,
  ] =
    useState(false);


  const activeWarehouses =
    useMemo(
      () =>
        warehouses.filter(
          (warehouse) =>
            warehouse.is_active,
        ),
      [warehouses],
    );


  const activeProducts =
    useMemo(
      () =>
        products.filter(
          (product) =>
            product.is_active,
        ),
      [products],
    );


  const standardProducts =
    useMemo(
      () =>
        activeProducts.filter(
          (product) =>
            !product
              .track_serial_numbers,
        ),
      [activeProducts],
    );


  const selectedTransferProduct =
    useMemo(
      () =>
        activeProducts.find(
          (product) =>
            String(
              product.id,
            )
            === transfer.productId,
        )
        ?? null,
      [
        activeProducts,
        transfer.productId,
      ],
    );


  const serializedTransfer =
    selectedTransferProduct
      ?.track_serial_numbers
    ?? false;


  async function ensureProducts() {
    if (
      productsLoaded
      || loadingProducts
    ) {
      return;
    }

    setLoadingProducts(
      true,
    );

    try {
      const response =
        await getProducts({
          page: 1,
          pageSize: 100,
        });

      setProducts(
        response.items,
      );

      setProductsLoaded(
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

      throw requestError;
    } finally {
      setLoadingProducts(
        false,
      );
    }
  }


  async function openAdjustment() {
    setError("");

    try {
      await ensureProducts();

      setAdjustment({
        ...emptyAdjustment,

        warehouseId:
          activeWarehouses[0]
            ? String(
                activeWarehouses[0].id,
              )
            : "",
      });

      setConfirmingAdjustment(
        false,
      );

      setAdjustOpen(
        true,
      );
    } catch {
      return;
    }
  }


  async function openTransfer() {
    setError("");

    try {
      await ensureProducts();

      setTransfer({
        ...emptyTransfer,

        sourceWarehouseId:
          activeWarehouses[0]
            ? String(
                activeWarehouses[0].id,
              )
            : "",

        destinationWarehouseId:
          activeWarehouses[1]
            ? String(
                activeWarehouses[1].id,
              )
            : "",
      });

      setSerials(
        [],
      );

      setSelectedSerialIds(
        [],
      );

      setConfirmingTransfer(
        false,
      );

      setTransferOpen(
        true,
      );
    } catch {
      return;
    }
  }


  function closeAdjustment() {
    if (saving) {
      return;
    }

    setAdjustOpen(
      false,
    );

    setConfirmingAdjustment(
      false,
    );

    setError(
      "",
    );
  }


  function closeTransfer() {
    if (saving) {
      return;
    }

    setTransferOpen(
      false,
    );

    setConfirmingTransfer(
      false,
    );

    setSerials(
      [],
    );

    setSelectedSerialIds(
      [],
    );

    setError(
      "",
    );
  }


  async function loadTransferSerials(
    productId: string,
    warehouseId: string,
    serialized: boolean,
  ) {
    setSerials(
      [],
    );

    setSelectedSerialIds(
      [],
    );

    if (
      !serialized
      || !productId
      || !warehouseId
    ) {
      return;
    }

    setLoadingSerials(
      true,
    );

    try {
      const response =
        await getSerialNumbers({
          productId:
            Number(
              productId,
            ),

          warehouseId:
            Number(
              warehouseId,
            ),

          serialStatus:
            "available",
        });

      setSerials(
        response.filter(
          (serial) =>
            serial.status
              === "available"
            && serial
              .current_customer_id
              == null,
        ),
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
      setLoadingSerials(
        false,
      );
    }
  }


  async function changeTransferProduct(
    productId: string,
  ) {
    const product =
      activeProducts.find(
        (item) =>
          String(
            item.id,
          )
          === productId,
      );

    const isSerialized =
      product
        ?.track_serial_numbers
      ?? false;

    setTransfer(
      (current) => ({
        ...current,
        productId,
      }),
    );

    setConfirmingTransfer(
      false,
    );

    setError(
      "",
    );

    await loadTransferSerials(
      productId,
      transfer.sourceWarehouseId,
      isSerialized,
    );
  }


  async function changeTransferSource(
    warehouseId: string,
  ) {
    setTransfer(
      (current) => {
        const destination =
          current
            .destinationWarehouseId
          === warehouseId
            ? ""
            : current
                .destinationWarehouseId;

        return {
          ...current,

          sourceWarehouseId:
            warehouseId,

          destinationWarehouseId:
            destination,
        };
      },
    );

    setConfirmingTransfer(
      false,
    );

    setError(
      "",
    );

    await loadTransferSerials(
      transfer.productId,
      warehouseId,
      serializedTransfer,
    );
  }


  function toggleSerial(
    serialId: number,
  ) {
    setSelectedSerialIds(
      (current) =>
        current.includes(
          serialId,
        )
          ? current.filter(
              (value) =>
                value
                !== serialId,
            )
          : [
              ...current,
              serialId,
            ],
    );

    setConfirmingTransfer(
      false,
    );
  }


  function selectAllSerials() {
    if (
      selectedSerialIds.length
      === serials.length
    ) {
      setSelectedSerialIds(
        [],
      );
    } else {
      setSelectedSerialIds(
        serials.map(
          (serial) =>
            serial.id,
        ),
      );
    }

    setConfirmingTransfer(
      false,
    );
  }


  function validateAdjustment():
    string | null {
    if (
      !adjustment.productId
    ) {
      return (
        "Select a standard "
        + "stock product."
      );
    }

    if (
      !adjustment.warehouseId
    ) {
      return (
        "Select a warehouse."
      );
    }

    const amount =
      Number(
        adjustment.quantity,
      );

    if (
      !Number.isFinite(
        amount,
      )
      || amount <= 0
    ) {
      return (
        "Quantity must be "
        + "greater than zero."
      );
    }

    if (
      adjustment.direction
      === "increase"
      && adjustment.unitCost
    ) {
      const cost =
        Number(
          adjustment.unitCost,
        );

      if (
        !Number.isFinite(
          cost,
        )
        || cost < 0
      ) {
        return (
          "Unit cost cannot "
          + "be negative."
        );
      }
    }

    if (
      adjustment.reason
        .trim()
        .length < 3
    ) {
      return (
        "Enter a clear adjustment "
        + "reason."
      );
    }

    return null;
  }


  function requestAdjustmentConfirmation(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const validation =
      validateAdjustment();

    if (validation) {
      setError(
        validation,
      );

      return;
    }

    setError(
      "",
    );

    setConfirmingAdjustment(
      true,
    );
  }


  async function executeAdjustment() {
    const validation =
      validateAdjustment();

    if (validation) {
      setError(
        validation,
      );

      setConfirmingAdjustment(
        false,
      );

      return;
    }

    setSaving(
      true,
    );

    setError(
      "",
    );

    try {
      await adjustStock({
        product_id:
          Number(
            adjustment.productId,
          ),

        warehouse_id:
          Number(
            adjustment.warehouseId,
          ),

        direction:
          adjustment.direction,

        quantity:
          adjustment.quantity,

        unit_cost:
          adjustment.direction
            === "increase"
            && adjustment.unitCost
              ? adjustment.unitCost
              : null,

        reference_id:
          optionalText(
            adjustment.referenceId,
          ),

        reason:
          adjustment.reason.trim(),

        notes:
          optionalText(
            adjustment.notes,
          ),
      });

      await onChanged();

      closeAdjustment();
    } catch (
      requestError
    ) {
      setError(
        apiError(
          requestError,
        ),
      );

      setConfirmingAdjustment(
        false,
      );
    } finally {
      setSaving(
        false,
      );
    }
  }


  function validateTransfer():
    string | null {
    if (
      !transfer.productId
    ) {
      return (
        "Select a product."
      );
    }

    if (
      !transfer
        .sourceWarehouseId
      || !transfer
        .destinationWarehouseId
    ) {
      return (
        "Select both source and "
        + "destination warehouses."
      );
    }

    if (
      transfer
        .sourceWarehouseId
      === transfer
        .destinationWarehouseId
    ) {
      return (
        "Source and destination "
        + "warehouses must be different."
      );
    }

    if (
      transfer.reason
        .trim()
        .length < 3
    ) {
      return (
        "Enter a clear transfer "
        + "reason."
      );
    }

    if (serializedTransfer) {
      if (
        selectedSerialIds
          .length === 0
      ) {
        return (
          "Select at least one "
          + "serial number."
        );
      }
    } else {
      const amount =
        Number(
          transfer.quantity,
        );

      if (
        !Number.isFinite(
          amount,
        )
        || amount <= 0
      ) {
        return (
          "Transfer quantity must "
          + "be greater than zero."
        );
      }
    }

    return null;
  }


  function requestTransferConfirmation(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const validation =
      validateTransfer();

    if (validation) {
      setError(
        validation,
      );

      return;
    }

    setError(
      "",
    );

    setConfirmingTransfer(
      true,
    );
  }


  async function executeTransfer() {
    const validation =
      validateTransfer();

    if (validation) {
      setError(
        validation,
      );

      setConfirmingTransfer(
        false,
      );

      return;
    }

    setSaving(
      true,
    );

    setError(
      "",
    );

    try {
      if (serializedTransfer) {
        await transferSerializedStock({
          product_id:
            Number(
              transfer.productId,
            ),

          source_warehouse_id:
            Number(
              transfer
                .sourceWarehouseId,
            ),

          destination_warehouse_id:
            Number(
              transfer
                .destinationWarehouseId,
            ),

          serial_number_ids:
            selectedSerialIds,

          reference_id:
            optionalText(
              transfer.referenceId,
            ),

          reason:
            transfer.reason.trim(),

          notes:
            optionalText(
              transfer.notes,
            ),
        });
      } else {
        await transferNonSerializedStock({
          product_id:
            Number(
              transfer.productId,
            ),

          source_warehouse_id:
            Number(
              transfer
                .sourceWarehouseId,
            ),

          destination_warehouse_id:
            Number(
              transfer
                .destinationWarehouseId,
            ),

          quantity:
            transfer.quantity,

          reference_id:
            optionalText(
              transfer.referenceId,
            ),

          reason:
            transfer.reason.trim(),

          notes:
            optionalText(
              transfer.notes,
            ),
        });
      }

      await onChanged();

      closeTransfer();
    } catch (
      requestError
    ) {
      setError(
        apiError(
          requestError,
        ),
      );

      setConfirmingTransfer(
        false,
      );
    } finally {
      setSaving(
        false,
      );
    }
  }


  const adjustmentProduct =
    standardProducts.find(
      (product) =>
        String(
          product.id,
        )
        === adjustment.productId,
    );


  const sourceWarehouse =
    activeWarehouses.find(
      (warehouse) =>
        String(
          warehouse.id,
        )
        === transfer
          .sourceWarehouseId,
    );


  const destinationWarehouse =
    activeWarehouses.find(
      (warehouse) =>
        String(
          warehouse.id,
        )
        === transfer
          .destinationWarehouseId,
    );


  return (
    <>
      <button
        type="button"
        className={
          styles.phase4AdjustButton
        }
        disabled={
          loadingProducts
        }
        onClick={() =>
          void openAdjustment()
        }
      >
        <SlidersHorizontal
          size={16}
        />

        Adjust stock
      </button>


      <button
        type="button"
        className={
          styles.phase4TransferButton
        }
        disabled={
          loadingProducts
        }
        onClick={() =>
          void openTransfer()
        }
      >
        <ArrowLeftRight
          size={16}
        />

        Transfer stock
      </button>


      {adjustOpen && (
        <div
          className={
            styles.phase4Backdrop
          }
        >
          <section
            className={
              styles.phase4Modal
            }
            role="dialog"
            aria-modal="true"
            aria-labelledby={
              "adjust-stock-title"
            }
          >
            <header
              className={
                styles.phase4Header
              }
            >
              <div>
                <p className="eyebrow">
                  INVENTORY CONTROL
                </p>

                <h2
                  id="adjust-stock-title"
                >
                  Adjust stock
                </h2>

                <p>
                  Correct a physical
                  stock-count difference.
                </p>
              </div>

              <button
                type="button"
                className={
                  styles
                    .phase4IconButton
                }
                disabled={
                  saving
                }
                onClick={
                  closeAdjustment
                }
              >
                <X size={18} />
              </button>
            </header>


            <form
              onSubmit={
                requestAdjustmentConfirmation
              }
            >
              <div
                className={
                  styles.phase4Body
                }
              >
                <section
                  className={
                    styles.phase4Section
                  }
                >
                  <h3>
                    Stock item
                  </h3>

                  <div
                    className={
                      styles.phase4Grid
                    }
                  >
                    <label
                      className={
                        styles
                          .phase4FullField
                      }
                    >
                      Standard product *

                      <select
                        required
                        value={
                          adjustment
                            .productId
                        }
                        disabled={
                          saving
                        }
                        onChange={
                          (event) => {
                            const productId =
                              event
                                .target
                                .value;

                            const product =
                              standardProducts
                                .find(
                                  (item) =>
                                    String(
                                      item.id,
                                    )
                                    === productId,
                                );

                            setAdjustment({
                              ...adjustment,

                              productId,

                              unitCost:
                                product
                                  ? String(
                                      product
                                        .purchase_cost
                                      ?? "",
                                    )
                                  : "",
                            });

                            setConfirmingAdjustment(
                              false,
                            );
                          }
                        }
                      >
                        <option value="">
                          Select product
                        </option>

                        {standardProducts.map(
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
                            </option>
                          ),
                        )}
                      </select>
                    </label>


                    <label>
                      Warehouse *

                      <select
                        required
                        value={
                          adjustment
                            .warehouseId
                        }
                        disabled={
                          saving
                        }
                        onChange={
                          (event) => {
                            setAdjustment({
                              ...adjustment,

                              warehouseId:
                                event
                                  .target
                                  .value,
                            });

                            setConfirmingAdjustment(
                              false,
                            );
                          }
                        }
                      >
                        <option value="">
                          Select warehouse
                        </option>

                        {activeWarehouses.map(
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
                      Direction *

                      <select
                        value={
                          adjustment
                            .direction
                        }
                        disabled={
                          saving
                        }
                        onChange={
                          (event) => {
                            setAdjustment({
                              ...adjustment,

                              direction:
                                event
                                  .target
                                  .value
                                === "decrease"
                                  ? "decrease"
                                  : "increase",
                            });

                            setConfirmingAdjustment(
                              false,
                            );
                          }
                        }
                      >
                        <option
                          value="increase"
                        >
                          Increase
                        </option>

                        <option
                          value="decrease"
                        >
                          Decrease
                        </option>
                      </select>
                    </label>


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
                          adjustment
                            .quantity
                        }
                        onChange={
                          (event) => {
                            setAdjustment({
                              ...adjustment,

                              quantity:
                                event
                                  .target
                                  .value,
                            });

                            setConfirmingAdjustment(
                              false,
                            );
                          }
                        }
                      />
                    </label>


                    <label>
                      Unit cost
                      {
                        adjustment
                          .direction
                        === "increase"
                          ? " (optional)"
                          : ""
                      }

                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        disabled={
                          saving
                          || adjustment
                            .direction
                            === "decrease"
                        }
                        value={
                          adjustment
                            .unitCost
                        }
                        onChange={
                          (event) => {
                            setAdjustment({
                              ...adjustment,

                              unitCost:
                                event
                                  .target
                                  .value,
                            });

                            setConfirmingAdjustment(
                              false,
                            );
                          }
                        }
                      />
                    </label>
                  </div>


                  {adjustmentProduct && (
                    <div
                      className={
                        styles
                          .phase4InfoBanner
                      }
                    >
                      <PackageSearch
                        size={17}
                      />

                      <div>
                        <strong>
                          {
                            adjustmentProduct
                              .name
                          }
                        </strong>

                        <span>
                          Standard quantity-tracked
                          inventory
                        </span>
                      </div>
                    </div>
                  )}
                </section>


                <section
                  className={
                    styles.phase4Section
                  }
                >
                  <h3>
                    Adjustment reason
                  </h3>

                  <div
                    className={
                      styles.phase4Grid
                    }
                  >
                    <label
                      className={
                        styles
                          .phase4FullField
                      }
                    >
                      Reason *

                      <input
                        type="text"
                        minLength={3}
                        maxLength={250}
                        required
                        disabled={
                          saving
                        }
                        placeholder={
                          "Physical count surplus, damaged quantity correction..."
                        }
                        value={
                          adjustment.reason
                        }
                        onChange={
                          (event) => {
                            setAdjustment({
                              ...adjustment,

                              reason:
                                event
                                  .target
                                  .value,
                            });

                            setConfirmingAdjustment(
                              false,
                            );
                          }
                        }
                      />
                    </label>


                    <label>
                      Reference ID

                      <input
                        type="text"
                        maxLength={100}
                        disabled={
                          saving
                        }
                        placeholder={
                          "ADJ-2026-001"
                        }
                        value={
                          adjustment
                            .referenceId
                        }
                        onChange={
                          (event) =>
                            setAdjustment({
                              ...adjustment,

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
                        styles
                          .phase4FullField
                      }
                    >
                      Notes

                      <textarea
                        rows={3}
                        maxLength={1000}
                        disabled={
                          saving
                        }
                        value={
                          adjustment.notes
                        }
                        onChange={
                          (event) =>
                            setAdjustment({
                              ...adjustment,

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
                      styles.phase4Error
                    }
                  >
                    <CircleAlert
                      size={17}
                    />

                    {error}
                  </div>
                )}


                {confirmingAdjustment && (
                  <div
                    className={
                      styles
                        .phase4Confirmation
                    }
                  >
                    <div
                      className={
                        styles
                          .phase4ConfirmationIcon
                      }
                    >
                      {adjustment
                        .direction
                        === "increase"
                        ? (
                          <Plus
                            size={18}
                          />
                        )
                        : (
                          <Minus
                            size={18}
                          />
                        )
                      }
                    </div>

                    <div>
                      <strong>
                        Confirm stock
                        {" "}
                        {
                          adjustment
                            .direction
                        }
                      </strong>

                      <span>
                        {quantity(
                          adjustment
                            .quantity,
                        )}
                        {" units • "}
                        {
                          adjustmentProduct
                            ?.name
                          ?? "Selected product"
                        }
                      </span>
                    </div>
                  </div>
                )}
              </div>


              <footer
                className={
                  styles.phase4Footer
                }
              >
                <button
                  type="button"
                  className={
                    styles
                      .phase4SecondaryButton
                  }
                  disabled={
                    saving
                  }
                  onClick={
                    closeAdjustment
                  }
                >
                  Cancel
                </button>

                {confirmingAdjustment ? (
                  <button
                    type="button"
                    className={
                      styles
                        .phase4DangerButton
                    }
                    disabled={
                      saving
                    }
                    onClick={() =>
                      void executeAdjustment()
                    }
                  >
                    {saving
                      ? (
                        "Applying..."
                      )
                      : (
                        <>
                          <Check
                            size={16}
                          />

                          Confirm adjustment
                        </>
                      )
                    }
                  </button>
                ) : (
                  <button
                    type="submit"
                    className={
                      styles
                        .phase4PrimaryButton
                    }
                    disabled={
                      saving
                    }
                  >
                    Review adjustment

                    <ChevronRight
                      size={16}
                    />
                  </button>
                )}
              </footer>
            </form>
          </section>
        </div>
      )}


      {transferOpen && (
        <div
          className={
            styles.phase4Backdrop
          }
        >
          <section
            className={
              styles.phase4ModalLarge
            }
            role="dialog"
            aria-modal="true"
            aria-labelledby={
              "transfer-stock-title"
            }
          >
            <header
              className={
                styles.phase4Header
              }
            >
              <div>
                <p className="eyebrow">
                  WAREHOUSE CONTROL
                </p>

                <h2
                  id="transfer-stock-title"
                >
                  Transfer stock
                </h2>

                <p>
                  Move standard or
                  serialized inventory
                  between warehouses.
                </p>
              </div>

              <button
                type="button"
                className={
                  styles
                    .phase4IconButton
                }
                disabled={
                  saving
                }
                onClick={
                  closeTransfer
                }
              >
                <X size={18} />
              </button>
            </header>


            <form
              onSubmit={
                requestTransferConfirmation
              }
            >
              <div
                className={
                  styles.phase4Body
                }
              >
                <section
                  className={
                    styles.phase4Section
                  }
                >
                  <h3>
                    Transfer route
                  </h3>

                  <div
                    className={
                      styles.phase4Grid
                    }
                  >
                    <label
                      className={
                        styles
                          .phase4FullField
                      }
                    >
                      Product *

                      <select
                        required
                        disabled={
                          saving
                        }
                        value={
                          transfer
                            .productId
                        }
                        onChange={
                          (event) =>
                            void changeTransferProduct(
                              event
                                .target
                                .value,
                            )
                        }
                      >
                        <option value="">
                          Select product
                        </option>

                        {activeProducts.map(
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
                      Source warehouse *

                      <select
                        required
                        disabled={
                          saving
                        }
                        value={
                          transfer
                            .sourceWarehouseId
                        }
                        onChange={
                          (event) =>
                            void changeTransferSource(
                              event
                                .target
                                .value,
                            )
                        }
                      >
                        <option value="">
                          Select source
                        </option>

                        {activeWarehouses.map(
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
                      Destination warehouse *

                      <select
                        required
                        disabled={
                          saving
                        }
                        value={
                          transfer
                            .destinationWarehouseId
                        }
                        onChange={
                          (event) => {
                            setTransfer({
                              ...transfer,

                              destinationWarehouseId:
                                event
                                  .target
                                  .value,
                            });

                            setConfirmingTransfer(
                              false,
                            );
                          }
                        }
                      >
                        <option value="">
                          Select destination
                        </option>

                        {activeWarehouses
                          .filter(
                            (warehouse) =>
                              String(
                                warehouse.id,
                              )
                              !== transfer
                                .sourceWarehouseId,
                          )
                          .map(
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
                  </div>


                  {selectedTransferProduct && (
                    <div
                      className={
                        styles
                          .phase4TransferRoute
                      }
                    >
                      <div>
                        <WarehouseIcon
                          size={17}
                        />

                        <span>
                          {
                            sourceWarehouse
                              ?.code
                            ?? "SOURCE"
                          }
                        </span>
                      </div>

                      <ArrowLeftRight
                        size={18}
                      />

                      <div>
                        <WarehouseIcon
                          size={17}
                        />

                        <span>
                          {
                            destinationWarehouse
                              ?.code
                            ?? "DESTINATION"
                          }
                        </span>
                      </div>

                      <strong>
                        {serializedTransfer
                          ? "Serialized"
                          : "Standard"
                        }
                      </strong>
                    </div>
                  )}
                </section>


                {!serializedTransfer && (
                  <section
                    className={
                      styles.phase4Section
                    }
                  >
                    <h3>
                      Standard quantity
                    </h3>

                    <div
                      className={
                        styles.phase4Grid
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
                            transfer.quantity
                          }
                          onChange={
                            (event) => {
                              setTransfer({
                                ...transfer,

                                quantity:
                                  event
                                    .target
                                    .value,
                              });

                              setConfirmingTransfer(
                                false,
                              );
                            }
                          }
                        />
                      </label>
                    </div>
                  </section>
                )}


                {serializedTransfer && (
                  <section
                    className={
                      styles.phase4Section
                    }
                  >
                    <div
                      className={
                        styles
                          .phase4SerialHeader
                      }
                    >
                      <div>
                        <h3>
                          Available serial numbers
                        </h3>

                        <p>
                          Select the physical
                          units to transfer.
                        </p>
                      </div>

                      <span>
                        {
                          selectedSerialIds
                            .length
                        }
                        {" selected"}
                      </span>
                    </div>


                    {loadingSerials ? (
                      <div
                        className={
                          styles
                            .phase4SerialState
                        }
                      >
                        <RefreshCw
                          size={18}
                          className={
                            styles.spin
                          }
                        />

                        Loading serials...
                      </div>
                    ) : serials.length
                      === 0 ? (
                      <div
                        className={
                          styles
                            .phase4SerialState
                        }
                      >
                        <PackageSearch
                          size={22}
                        />

                        No available serials
                        in this source warehouse.
                      </div>
                    ) : (
                      <>
                        <button
                          type="button"
                          className={
                            styles
                              .phase4SelectAllButton
                          }
                          onClick={
                            selectAllSerials
                          }
                        >
                          <Check
                            size={14}
                          />

                          {selectedSerialIds
                            .length
                            === serials.length
                            ? "Clear selection"
                            : "Select all"
                          }
                        </button>

                        <div
                          className={
                            styles
                              .phase4SerialList
                          }
                        >
                          {serials.map(
                            (serial) => {
                              const checked =
                                selectedSerialIds
                                  .includes(
                                    serial.id,
                                  );

                              return (
                                <button
                                  key={
                                    serial.id
                                  }
                                  type="button"
                                  className={
                                    checked
                                      ? styles
                                          .phase4SerialSelected
                                      : styles
                                          .phase4SerialItem
                                  }
                                  onClick={() =>
                                    toggleSerial(
                                      serial.id,
                                    )
                                  }
                                >
                                  <span
                                    className={
                                      styles
                                        .phase4CheckBox
                                    }
                                  >
                                    {checked && (
                                      <Check
                                        size={13}
                                      />
                                    )}
                                  </span>

                                  <div>
                                    <strong>
                                      {
                                        serial
                                          .serial_number
                                      }
                                    </strong>

                                    <span>
                                      {
                                        serial.status
                                      }
                                    </span>
                                  </div>
                                </button>
                              );
                            },
                          )}
                        </div>
                      </>
                    )}
                  </section>
                )}


                <section
                  className={
                    styles.phase4Section
                  }
                >
                  <h3>
                    Transfer reason
                  </h3>

                  <div
                    className={
                      styles.phase4Grid
                    }
                  >
                    <label
                      className={
                        styles
                          .phase4FullField
                      }
                    >
                      Reason *

                      <input
                        type="text"
                        minLength={3}
                        maxLength={250}
                        required
                        disabled={
                          saving
                        }
                        placeholder={
                          "Branch replenishment, service stock relocation..."
                        }
                        value={
                          transfer.reason
                        }
                        onChange={
                          (event) => {
                            setTransfer({
                              ...transfer,

                              reason:
                                event
                                  .target
                                  .value,
                            });

                            setConfirmingTransfer(
                              false,
                            );
                          }
                        }
                      />
                    </label>


                    <label>
                      Reference ID

                      <input
                        type="text"
                        maxLength={100}
                        disabled={
                          saving
                        }
                        placeholder={
                          "TRF-2026-001"
                        }
                        value={
                          transfer
                            .referenceId
                        }
                        onChange={
                          (event) =>
                            setTransfer({
                              ...transfer,

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
                        styles
                          .phase4FullField
                      }
                    >
                      Notes

                      <textarea
                        rows={3}
                        maxLength={1000}
                        disabled={
                          saving
                        }
                        value={
                          transfer.notes
                        }
                        onChange={
                          (event) =>
                            setTransfer({
                              ...transfer,

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
                      styles.phase4Error
                    }
                  >
                    <CircleAlert
                      size={17}
                    />

                    {error}
                  </div>
                )}


                {confirmingTransfer && (
                  <div
                    className={
                      styles
                        .phase4Confirmation
                    }
                  >
                    <div
                      className={
                        styles
                          .phase4ConfirmationIcon
                      }
                    >
                      <ArrowLeftRight
                        size={18}
                      />
                    </div>

                    <div>
                      <strong>
                        Confirm warehouse
                        transfer
                      </strong>

                      <span>
                        {serializedTransfer
                          ? (
                            selectedSerialIds
                              .length
                            + " serialized units"
                          )
                          : (
                            quantity(
                              transfer.quantity,
                            )
                            + " standard units"
                          )
                        }
                        {" • "}
                        {
                          sourceWarehouse
                            ?.code
                          ?? "Source"
                        }
                        {" → "}
                        {
                          destinationWarehouse
                            ?.code
                          ?? "Destination"
                        }
                      </span>
                    </div>
                  </div>
                )}
              </div>


              <footer
                className={
                  styles.phase4Footer
                }
              >
                <button
                  type="button"
                  className={
                    styles
                      .phase4SecondaryButton
                  }
                  disabled={
                    saving
                  }
                  onClick={
                    closeTransfer
                  }
                >
                  Cancel
                </button>

                {confirmingTransfer ? (
                  <button
                    type="button"
                    className={
                      styles
                        .phase4PrimaryButton
                    }
                    disabled={
                      saving
                    }
                    onClick={() =>
                      void executeTransfer()
                    }
                  >
                    {saving
                      ? (
                        "Transferring..."
                      )
                      : (
                        <>
                          <Check
                            size={16}
                          />

                          Confirm transfer
                        </>
                      )
                    }
                  </button>
                ) : (
                  <button
                    type="submit"
                    className={
                      styles
                        .phase4PrimaryButton
                    }
                    disabled={
                      saving
                    }
                  >
                    Review transfer

                    <ChevronRight
                      size={16}
                    />
                  </button>
                )}
              </footer>
            </form>
          </section>
        </div>
      )}
    </>
  );
}
