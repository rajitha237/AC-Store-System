"use client";

import Link from "next/link";
import {
  FormEvent,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getSerialNumbers,
  getStockBalances,
  getWarehouses,
  returnStockToSupplier,
} from "@/lib/inventory-api";

import {
  getSuppliers,
} from "@/lib/supplier-api";

import type {
  SerialNumberDetail,
  StockBalance,
  Warehouse,
} from "@/types/inventory";

import type {
  Supplier,
} from "@/types/supplier";


function getErrorMessage(
  error: unknown,
): string {
  if (
    typeof error === "object"
    && error !== null
    && "response" in error
  ) {
    const response = (
      error as {
        response?: {
          data?: {
            detail?: string;
          };
        };
      }
    ).response;

    if (
      typeof response?.data?.detail
      === "string"
    ) {
      return response.data.detail;
    }
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Supplier return failed.";
}


const cardStyle = {
  background: "#ffffff",
  border: "1px solid #e5e7eb",
  borderRadius: 18,
  boxShadow:
    "0 10px 30px rgba(15, 23, 42, 0.06)",
} as const;


const inputStyle = {
  width: "100%",
  minHeight: 46,
  border: "1px solid #cbd5e1",
  borderRadius: 10,
  padding: "10px 12px",
  background: "#ffffff",
  color: "#0f172a",
  fontSize: 14,
  outline: "none",
} as const;


const labelStyle = {
  display: "grid",
  gap: 7,
  color: "#334155",
  fontSize: 13,
  fontWeight: 700,
} as const;


export default function SupplierReturnPage() {
  const [
    suppliers,
    setSuppliers,
  ] = useState<Supplier[]>([]);

  const [
    warehouses,
    setWarehouses,
  ] = useState<Warehouse[]>([]);

  const [
    balances,
    setBalances,
  ] = useState<StockBalance[]>([]);

  const [
    serials,
    setSerials,
  ] = useState<SerialNumberDetail[]>([]);

  const [
    supplierId,
    setSupplierId,
  ] = useState("");

  const [
    warehouseId,
    setWarehouseId,
  ] = useState("");

  const [
    productId,
    setProductId,
  ] = useState("");

  const [
    quantity,
    setQuantity,
  ] = useState("1");

  const [
    serialNumberId,
    setSerialNumberId,
  ] = useState("");

  const [
    referenceId,
    setReferenceId,
  ] = useState("");

  const [
    notes,
    setNotes,
  ] = useState("");

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    submitting,
    setSubmitting,
  ] = useState(false);

  const [
    message,
    setMessage,
  ] = useState("");

  const [
    error,
    setError,
  ] = useState("");


  const selectedBalance =
    useMemo(
      () =>
        balances.find(
          (item) =>
            item.product_id
              === Number(productId)
            && item.warehouse_id
              === Number(warehouseId),
        ) ?? null,
      [
        balances,
        productId,
        warehouseId,
      ],
    );


  const productBalances =
    useMemo(
      () =>
        balances.filter(
          (item) =>
            Number(
              item.quantity_available,
            ) > 0,
        ),
      [balances],
    );


  useEffect(() => {
    let active = true;

    const load =
      async () => {
        try {
          const [
            supplierResponse,
            warehouseResponse,
            stockResponse,
          ] = await Promise.all([
            getSuppliers({
              page: 1,
              pageSize: 500,
              isActive: true,
            }),
            getWarehouses(true),
            getStockBalances(),
          ]);

          if (!active) {
            return;
          }

          setSuppliers(
            supplierResponse.items,
          );

          setWarehouses(
            warehouseResponse,
          );

          setBalances(
            stockResponse.filter(
              (item: StockBalance) =>
                Number(
                  item.quantity_available,
                ) > 0,
            ),
          );
        } catch (loadError) {
          if (active) {
            setError(
              getErrorMessage(
                loadError,
              ),
            );
          }
        } finally {
          if (active) {
            setLoading(false);
          }
        }
      };

    void load();

    return () => {
      active = false;
    };
  }, []);


  useEffect(() => {
    const loadSerials =
      async () => {
        setSerialNumberId("");
        setSerials([]);

        if (
          !productId
          || !warehouseId
        ) {
          return;
        }

        try {
          const result =
            await getSerialNumbers({
              productId:
                Number(productId),
              warehouseId:
                Number(warehouseId),
              serialStatus:
                "available",
            });

          setSerials(result);
        } catch {
          setSerials([]);
        }
      };

    void loadSerials();
  }, [
    productId,
    warehouseId,
  ]);


  const submit =
    async (
      event: FormEvent,
    ) => {
      event.preventDefault();

      setError("");
      setMessage("");

      if (
        !supplierId
        || !warehouseId
        || !productId
      ) {
        setError(
          "Select supplier, warehouse and product.",
        );
        return;
      }

      const parsedQuantity =
        Number(quantity);

      if (
        !Number.isFinite(
          parsedQuantity,
        )
        || parsedQuantity <= 0
      ) {
        setError(
          "Enter a valid return quantity.",
        );
        return;
      }

      if (
        selectedBalance
        && parsedQuantity
          > Number(
            selectedBalance
              .quantity_available,
          )
      ) {
        setError(
          "Return quantity exceeds available stock.",
        );
        return;
      }

      if (
        serials.length > 0
        && !serialNumberId
      ) {
        setError(
          "Select the serial number being returned.",
        );
        return;
      }

      setSubmitting(true);

      try {
        const result =
          await returnStockToSupplier({
            supplier_id:
              Number(supplierId),

            warehouse_id:
              Number(warehouseId),

            product_id:
              Number(productId),

            quantity:
              serialNumberId
                ? "1"
                : quantity,

            serial_number_id:
              serialNumberId
                ? Number(
                    serialNumberId,
                  )
                : null,

            reference_id:
              referenceId.trim()
                || null,

            notes:
              notes.trim()
                || null,
          });

        setMessage(
          `${result.message}. `
          + `Remaining stock: `
          + `${result.quantity_on_hand}`,
        );

        setQuantity("1");
        setSerialNumberId("");
        setReferenceId("");
        setNotes("");

        const stockResponse =
          await getStockBalances();

        setBalances(
          stockResponse.filter(
            (item) =>
              Number(
                item.quantity_available,
              ) > 0,
          ),
        );

        if (
          productId
          && warehouseId
        ) {
          const serialResponse =
            await getSerialNumbers({
              productId:
                Number(productId),
              warehouseId:
                Number(warehouseId),
              serialStatus:
                "available",
            });

          setSerials(
            serialResponse,
          );
        }
      } catch (submitError) {
        setError(
          getErrorMessage(
            submitError,
          ),
        );
      } finally {
        setSubmitting(false);
      }
    };


  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#f8fafc",
        padding: "28px",
      }}
    >
      <div
        style={{
          maxWidth: 1120,
          margin: "0 auto",
          display: "grid",
          gap: 20,
        }}
      >
        <header
          style={{
            display: "flex",
            justifyContent:
              "space-between",
            alignItems: "center",
            gap: 16,
            flexWrap: "wrap",
          }}
        >
          <div>
            <div
              style={{
                color: "#64748b",
                fontSize: 13,
                fontWeight: 700,
                marginBottom: 6,
              }}
            >
              PURCHASES / INVENTORY
            </div>

            <h1
              style={{
                margin: 0,
                color: "#0f172a",
                fontSize: 30,
              }}
            >
              Return to Supplier
            </h1>

            <p
              style={{
                color: "#64748b",
                margin:
                  "8px 0 0",
              }}
            >
              Return available stock
              to a supplier with a
              traceable inventory
              movement and audit record.
            </p>
          </div>

          <Link
            href="/purchases"
            style={{
              textDecoration: "none",
              border:
                "1px solid #cbd5e1",
              borderRadius: 10,
              padding: "10px 15px",
              color: "#334155",
              background: "#ffffff",
              fontWeight: 700,
            }}
          >
            ← Back to Purchases
          </Link>
        </header>

        <section
          style={{
            ...cardStyle,
            padding: 22,
          }}
        >
          <div
            style={{
              padding:
                "12px 14px",
              borderRadius: 12,
              background: "#fff7ed",
              border:
                "1px solid #fed7aa",
              color: "#9a3412",
              marginBottom: 20,
              fontSize: 13,
              lineHeight: 1.6,
            }}
          >
            <strong>
              Stock operation:
            </strong>{" "}
            this removes stock from the
            selected warehouse. Supplier
            payable / supplier invoice
            values are not automatically
            changed by this emergency
            return workflow.
          </div>

          {error ? (
            <div
              style={{
                background: "#fef2f2",
                border:
                  "1px solid #fecaca",
                color: "#b91c1c",
                borderRadius: 10,
                padding: 12,
                marginBottom: 16,
              }}
            >
              {error}
            </div>
          ) : null}

          {message ? (
            <div
              style={{
                background: "#f0fdf4",
                border:
                  "1px solid #bbf7d0",
                color: "#166534",
                borderRadius: 10,
                padding: 12,
                marginBottom: 16,
              }}
            >
              {message}
            </div>
          ) : null}

          {loading ? (
            <div
              style={{
                color: "#64748b",
                padding: "30px 0",
              }}
            >
              Loading supplier and
              stock information...
            </div>
          ) : (
            <form
              onSubmit={submit}
              style={{
                display: "grid",
                gap: 18,
              }}
            >
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns:
                    "repeat(auto-fit, minmax(240px, 1fr))",
                  gap: 16,
                }}
              >
                <label
                  style={labelStyle}
                >
                  Supplier *

                  <select
                    value={supplierId}
                    onChange={(event) =>
                      setSupplierId(
                        event.target
                          .value,
                      )
                    }
                    style={inputStyle}
                    required
                  >
                    <option value="">
                      Select supplier
                    </option>

                    {suppliers.map(
                      (supplier) => (
                        <option
                          key={
                            supplier.id
                          }
                          value={
                            supplier.id
                          }
                        >
                          {
                            supplier
                              .supplier_code
                          }
                          {" — "}
                          {
                            supplier
                              .company_name
                          }
                        </option>
                      ),
                    )}
                  </select>
                </label>

                <label
                  style={labelStyle}
                >
                  Warehouse *

                  <select
                    value={warehouseId}
                    onChange={(event) => {
                      setWarehouseId(
                        event.target
                          .value,
                      );
                      setProductId("");
                    }}
                    style={inputStyle}
                    required
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
                            warehouse.name
                          }
                        </option>
                      ),
                    )}
                  </select>
                </label>
              </div>

              <label
                style={labelStyle}
              >
                Product in Stock *

                <select
                  value={productId}
                  onChange={(event) => {
                    setProductId(
                      event.target.value,
                    );
                    setQuantity("1");
                  }}
                  style={inputStyle}
                  required
                  disabled={!warehouseId}
                >
                  <option value="">
                    {warehouseId
                      ? "Select product"
                      : "Select warehouse first"}
                  </option>

                  {productBalances
                    .filter(
                      (item) =>
                        item.warehouse_id
                        === Number(
                          warehouseId,
                        ),
                    )
                    .map((item) => (
                      <option
                        key={
                          `${item.warehouse_id}-${item.product_id}`
                        }
                        value={
                          item.product_id
                        }
                      >
                        Product #{item.product_id}
                        {" | Available: "}
                        {item.quantity_available}
                      </option>
                    ))}
                </select>
              </label>

              {selectedBalance ? (
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "repeat(auto-fit, minmax(160px, 1fr))",
                    gap: 12,
                  }}
                >
                  <div
                    style={{
                      background:
                        "#f8fafc",
                      border:
                        "1px solid #e2e8f0",
                      borderRadius: 12,
                      padding: 14,
                    }}
                  >
                    <div
                      style={{
                        color:
                          "#64748b",
                        fontSize: 12,
                      }}
                    >
                      Product
                    </div>

                    <strong>
                      Product #{selectedBalance.product_id}
                    </strong>
                  </div>

                  <div
                    style={{
                      background:
                        "#f8fafc",
                      border:
                        "1px solid #e2e8f0",
                      borderRadius: 12,
                      padding: 14,
                    }}
                  >
                    <div
                      style={{
                        color:
                          "#64748b",
                        fontSize: 12,
                      }}
                    >
                      On Hand
                    </div>

                    <strong>
                      {
                        selectedBalance
                          .quantity_on_hand
                      }
                    </strong>
                  </div>

                  <div
                    style={{
                      background:
                        "#f8fafc",
                      border:
                        "1px solid #e2e8f0",
                      borderRadius: 12,
                      padding: 14,
                    }}
                  >
                    <div
                      style={{
                        color:
                          "#64748b",
                        fontSize: 12,
                      }}
                    >
                      Available
                    </div>

                    <strong>
                      {
                        selectedBalance
                          .quantity_available
                      }
                    </strong>
                  </div>
                </div>
              ) : null}

              {serials.length > 0 ? (
                <label
                  style={labelStyle}
                >
                  Serial Number *

                  <select
                    value={
                      serialNumberId
                    }
                    onChange={(event) => {
                      setSerialNumberId(
                        event.target
                          .value,
                      );
                      setQuantity("1");
                    }}
                    style={inputStyle}
                    required
                  >
                    <option value="">
                      Select serial
                    </option>

                    {serials.map(
                      (serial) => (
                        <option
                          key={
                            serial.id
                          }
                          value={
                            serial.id
                          }
                        >
                          {
                            serial
                              .serial_number
                          }
                        </option>
                      ),
                    )}
                  </select>

                  <span
                    style={{
                      color: "#64748b",
                      fontSize: 12,
                      fontWeight: 500,
                    }}
                  >
                    Serialized returns
                    are always quantity 1.
                  </span>
                </label>
              ) : (
                <label
                  style={labelStyle}
                >
                  Return Quantity *

                  <input
                    type="number"
                    min="0.001"
                    step="0.001"
                    max={
                      selectedBalance
                        ?.quantity_available
                    }
                    value={quantity}
                    onChange={(event) =>
                      setQuantity(
                        event.target
                          .value,
                      )
                    }
                    style={inputStyle}
                    required
                  />
                </label>
              )}

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns:
                    "repeat(auto-fit, minmax(240px, 1fr))",
                  gap: 16,
                }}
              >
                <label
                  style={labelStyle}
                >
                  Reference

                  <input
                    value={referenceId}
                    onChange={(event) =>
                      setReferenceId(
                        event.target
                          .value,
                      )
                    }
                    placeholder="GRN / supplier reference"
                    maxLength={100}
                    style={inputStyle}
                  />
                </label>

                <label
                  style={labelStyle}
                >
                  Return Reason / Notes

                  <input
                    value={notes}
                    onChange={(event) =>
                      setNotes(
                        event.target
                          .value,
                      )
                    }
                    placeholder="Damaged, wrong item, supplier request..."
                    style={inputStyle}
                  />
                </label>
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent:
                    "flex-end",
                  gap: 12,
                  borderTop:
                    "1px solid #e2e8f0",
                  paddingTop: 18,
                }}
              >
                <Link
                  href="/purchases"
                  style={{
                    textDecoration:
                      "none",
                    border:
                      "1px solid #cbd5e1",
                    borderRadius: 10,
                    padding:
                      "11px 18px",
                    color: "#334155",
                    fontWeight: 700,
                  }}
                >
                  Cancel
                </Link>

                <button
                  type="submit"
                  disabled={
                    submitting
                    || !supplierId
                    || !warehouseId
                    || !productId
                  }
                  style={{
                    border: 0,
                    borderRadius: 10,
                    padding:
                      "11px 20px",
                    background:
                      submitting
                        ? "#94a3b8"
                        : "#0f172a",
                    color: "#ffffff",
                    fontWeight: 800,
                    cursor:
                      submitting
                        ? "wait"
                        : "pointer",
                  }}
                >
                  {submitting
                    ? "Returning..."
                    : "Confirm Supplier Return"}
                </button>
              </div>
            </form>
          )}
        </section>
      </div>
    </main>
  );
}
