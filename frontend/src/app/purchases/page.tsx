"use client";

import axios from "axios";

import {
  CheckCircle2,
  CircleAlert,
  CreditCard,
  FileText,
  Loader2,
  PackageCheck,
  Plus,
  RefreshCw,
  Search,
  ShoppingCart,
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
  getProducts,
} from "@/lib/catalog-api";

import {
  getWarehouses,
} from "@/lib/inventory-api";

import {
  approvePurchaseOrder,
  createPurchaseOrder,
  createSupplierInvoice,
  createSupplierPayment,
  getPurchaseOrder,
  listGoodsReceipts,
  listPurchaseOrders,
  listSupplierInvoices,
  receivePurchaseOrder,
} from "@/lib/purchasing-api";

import {
  getSuppliers,
} from "@/lib/supplier-api";

import {
  clearAuthSession,
  getAccessToken,
  getStoredUser,
} from "@/lib/auth";

import type {
  UserResponse,
} from "@/types/auth";

import type {
  Product,
} from "@/types/catalog";

import type {
  Warehouse,
} from "@/types/inventory";

import type {
  GoodsReceipt,
  PurchaseOrder,
  PurchaseOrderItemInput,
  SupplierInvoice,
} from "@/types/purchasing";

import type {
  Supplier,
} from "@/types/supplier";


type LineForm = {
  productId: string;
  quantity: string;
  unitCost: string;
  discount: string;
  tax: string;
};


const EMPTY_LINE: LineForm = {
  productId: "",
  quantity: "1.000",
  unitCost: "0.00",
  discount: "0.00",
  tax: "0.00",
};


function money(
  value:
    | string
    | number
    | null
    | undefined,
) {
  const amount =
    Number(value ?? 0);

  return new Intl.NumberFormat(
    "en-LK",
    {
      style: "currency",
      currency: "LKR",
      minimumFractionDigits: 2,
    },
  ).format(
    Number.isFinite(amount)
      ? amount
      : 0,
  );
}


function apiError(
  error: unknown,
) {
  if (!axios.isAxiosError(error)) {
    return "Something went wrong.";
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
    && typeof detail[0]?.msg
      === "string"
  ) {
    return detail[0].msg;
  }

  return (
    error.message
    || "Request failed."
  );
}


const pageStyle = {
  padding: "24px",
  display: "grid",
  gap: "20px",
} as const;


const cardStyle = {
  background: "white",
  border:
    "1px solid #e5e7eb",
  borderRadius: "16px",
  padding: "18px",
  boxShadow:
    "0 4px 18px rgba(15,23,42,.04)",
} as const;


const gridStyle = {
  display: "grid",
  gridTemplateColumns:
    "repeat(auto-fit,minmax(190px,1fr))",
  gap: "12px",
} as const;


const inputStyle = {
  width: "100%",
  border:
    "1px solid #d1d5db",
  borderRadius: "10px",
  padding: "10px 12px",
  background: "white",
} as const;


const buttonStyle = {
  border: 0,
  borderRadius: "10px",
  padding: "10px 14px",
  cursor: "pointer",
  fontWeight: 700,
} as const;


export default function PurchasesPage() {
  const router =
    useRouter();

  const [
    user,
  ] =
    useState<UserResponse | null>(
      () =>
        getStoredUser(),
    );

  const [
    suppliers,
    setSuppliers,
  ] =
    useState<Supplier[]>([]);

  const [
    warehouses,
    setWarehouses,
  ] =
    useState<Warehouse[]>([]);

  const [
    products,
    setProducts,
  ] =
    useState<Product[]>([]);

  const [
    orders,
    setOrders,
  ] =
    useState<PurchaseOrder[]>([]);

  const [
    selected,
    setSelected,
  ] =
    useState<PurchaseOrder | null>(
      null,
    );

  const [
    receipts,
    setReceipts,
  ] =
    useState<GoodsReceipt[]>([]);

  const [
    invoices,
    setInvoices,
  ] =
    useState<SupplierInvoice[]>([]);

  const [
    loading,
    setLoading,
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
    success,
    setSuccess,
  ] =
    useState("");

  const [
    search,
    setSearch,
  ] =
    useState("");

  const [
    supplierId,
    setSupplierId,
  ] =
    useState("");

  const [
    warehouseId,
    setWarehouseId,
  ] =
    useState("");

  const [
    expectedDate,
    setExpectedDate,
  ] =
    useState("");

  const [
    poNotes,
    setPoNotes,
  ] =
    useState("");

  const [
    lines,
    setLines,
  ] =
    useState<LineForm[]>([
      {
        ...EMPTY_LINE,
      },
    ]);

  const [
    deliveryNote,
    setDeliveryNote,
  ] =
    useState("");

  const [
    receiveNotes,
    setReceiveNotes,
  ] =
    useState("");

  const [
    invoiceReference,
    setInvoiceReference,
  ] =
    useState("");

  const [
    invoiceDueDate,
    setInvoiceDueDate,
  ] =
    useState("");

  const [
    invoiceDiscount,
    setInvoiceDiscount,
  ] =
    useState("0.00");

  const [
    invoiceTax,
    setInvoiceTax,
  ] =
    useState("0.00");

  const [
    paymentAmount,
    setPaymentAmount,
  ] =
    useState("");

  const [
    paymentMethod,
    setPaymentMethod,
  ] =
    useState("cash");

  const [
    paymentReference,
    setPaymentReference,
  ] =
    useState("");

  const [
    paymentInvoiceId,
    setPaymentInvoiceId,
  ] =
    useState("");


  useEffect(() => {
    const token =
      getAccessToken();

    if (
      !token
      || !user
    ) {
      clearAuthSession();

      router.replace(
        "/login",
      );
    }
  }, [
    router,
    user,
  ]);


  const loadBaseData =
    useCallback(
      async () => {
        if (!user) {
          return;
        }

        setLoading(true);
        setError("");

        try {
          const [
            supplierResponse,
            warehouseResponse,
            productResponse,
            orderResponse,
          ] =
            await Promise.all([
              getSuppliers({
                page: 1,
                pageSize: 100,
                isActive: true,
              }),

              getWarehouses(
                true,
              ),

              getProducts({
                page: 1,
                pageSize: 100,
              }),

              listPurchaseOrders({
                page: 1,
                pageSize: 100,
              }),
            ]);

          setSuppliers(
            supplierResponse.items,
          );

          setWarehouses(
            warehouseResponse,
          );

          setProducts(
            productResponse
              .items
              .filter(
                (product) =>
                  product.is_active,
              ),
          );

          setOrders(
            orderResponse.items,
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
          setLoading(false);
        }
      },
      [user],
    );


  useEffect(() => {
    const timer =
      window.setTimeout(
        () => {
          void loadBaseData();
        },
        0,
      );

    return () => {
      window.clearTimeout(
        timer,
      );
    };
  }, [loadBaseData]);


  const refreshSelected =
    useCallback(
      async (
        purchaseOrderId:
          number,
      ) => {
        const detail =
          await getPurchaseOrder(
            purchaseOrderId,
          );

        setSelected(detail);

        const [
          grnResponse,
          invoiceResponse,
        ] =
          await Promise.all([
            listGoodsReceipts({
              purchaseOrderId,
              pageSize: 100,
            }),

            listSupplierInvoices({
              supplierId:
                detail.supplier_id,
              pageSize: 100,
            }),
          ]);

        setReceipts(
          grnResponse.items,
        );

        setInvoices(
          invoiceResponse
            .items
            .filter(
              (invoice) =>
                invoice
                  .purchase_order_id
                === purchaseOrderId,
            ),
        );
      },
      [],
    );


  const selectOrder =
    async (
      purchaseOrderId:
        number,
    ) => {
      setLoading(true);
      setError("");

      try {
        await refreshSelected(
          purchaseOrderId,
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
        setLoading(false);
      }
    };


  const createPo =
    async (
      event:
        FormEvent,
    ) => {
      event.preventDefault();

      if (
        !supplierId
        || !warehouseId
      ) {
        setError(
          "Supplier and warehouse are required.",
        );
        return;
      }

      const validLines =
        lines.filter(
          (line) =>
            line.productId
            && Number(
              line.quantity,
            ) > 0,
        );

      if (
        validLines.length
        === 0
      ) {
        setError(
          "Add at least one product.",
        );
        return;
      }

      setSaving(true);
      setError("");
      setSuccess("");

      try {
        const items:
          PurchaseOrderItemInput[] =
          validLines.map(
            (line) => ({
              product_id:
                Number(
                  line.productId,
                ),

              quantity:
                line.quantity,

              unit_cost:
                line.unitCost,

              discount_amount:
                line.discount,

              tax_amount:
                line.tax,
            }),
          );

        const created =
          await createPurchaseOrder(
            {
              supplier_id:
                Number(
                  supplierId,
                ),

              warehouse_id:
                Number(
                  warehouseId,
                ),

              expected_date:
                expectedDate
                  || null,

              notes:
                poNotes.trim()
                  || null,

              items,
            },
          );

        setSuccess(
          `${created.purchase_order_number} created.`,
        );

        setSupplierId("");
        setWarehouseId("");
        setExpectedDate("");
        setPoNotes("");
        setLines([
          {
            ...EMPTY_LINE,
          },
        ]);

        await loadBaseData();
        await refreshSelected(
          created.id,
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
        setSaving(false);
      }
    };


  const approvePo =
    async () => {
      if (!selected) {
        return;
      }

      setSaving(true);
      setError("");
      setSuccess("");

      try {
        const result =
          await approvePurchaseOrder(
            selected.id,
          );

        setSuccess(
          `${result.purchase_order_number} approved.`,
        );

        await loadBaseData();
        await refreshSelected(
          selected.id,
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
        setSaving(false);
      }
    };


  const receivePo =
    async () => {
      if (
        !selected
        || !selected.items
      ) {
        return;
      }

      const receiveItems =
        selected.items
          .map((item) => {
            const ordered =
              Number(
                item.quantity_ordered
                ?? item.quantity
                ?? 0,
              );

            const received =
              Number(
                item.quantity_received
                ?? 0,
              );

            const remaining =
              ordered
              - received;

            return {
              purchase_order_item_id:
                item.id,

              quantity:
                String(
                  Math.max(
                    remaining,
                    0,
                  ),
                ),
            };
          })
          .filter(
            (item) =>
              Number(
                item.quantity,
              ) > 0,
          );

      if (
        receiveItems.length
        === 0
      ) {
        setError(
          "There is no remaining quantity to receive.",
        );
        return;
      }

      setSaving(true);
      setError("");
      setSuccess("");

      try {
        const receipt =
          await receivePurchaseOrder(
            selected.id,
            {
              delivery_note_number:
                deliveryNote.trim()
                  || null,

              notes:
                receiveNotes.trim()
                  || null,

              items:
                receiveItems,
            },
          );

        setSuccess(
          `${receipt.grn_number} created and stock received.`,
        );

        setDeliveryNote("");
        setReceiveNotes("");

        await loadBaseData();
        await refreshSelected(
          selected.id,
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
        setSaving(false);
      }
    };


  const createInvoice =
    async () => {
      if (!selected) {
        return;
      }

      const latestReceipt =
        receipts[0];

      if (
        !latestReceipt
      ) {
        setError(
          "Receive the purchase order before creating the supplier invoice.",
        );
        return;
      }

      if (
        !invoiceReference
          .trim()
      ) {
        setError(
          "Supplier invoice number is required.",
        );
        return;
      }

      setSaving(true);
      setError("");
      setSuccess("");

      try {
        const subtotal =
          Number(
            selected.grand_total
            ?? 0,
          );

        const created =
          await createSupplierInvoice(
            {
              supplier_id:
                selected.supplier_id,

              purchase_order_id:
                selected.id,

              goods_receipt_id:
                latestReceipt.id,

              supplier_invoice_number:
                invoiceReference
                  .trim(),

              due_date:
                invoiceDueDate
                  || null,

              subtotal:
                subtotal
                  .toFixed(2),

              discount_amount:
                invoiceDiscount
                || "0.00",

              tax_amount:
                invoiceTax
                || "0.00",

              notes:
                `Created from ${selected.purchase_order_number}`,
            },
          );

        setSuccess(
          `${created.invoice_number} created.`,
        );

        setInvoiceReference("");
        setInvoiceDueDate("");
        setInvoiceDiscount(
          "0.00",
        );
        setInvoiceTax(
          "0.00",
        );

        await refreshSelected(
          selected.id,
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
        setSaving(false);
      }
    };


  const createPayment =
    async () => {
      if (!selected) {
        return;
      }

      const invoice =
        invoices.find(
          (item) =>
            String(item.id)
            === paymentInvoiceId,
        );

      if (!invoice) {
        setError(
          "Select a supplier invoice.",
        );
        return;
      }

      if (
        Number(
          paymentAmount,
        ) <= 0
      ) {
        setError(
          "Enter a valid payment amount.",
        );
        return;
      }

      setSaving(true);
      setError("");
      setSuccess("");

      try {
        await createSupplierPayment(
          {
            supplier_id:
              selected.supplier_id,

            supplier_invoice_id:
              invoice.id,

            amount:
              paymentAmount,

            payment_method:
              paymentMethod,

            reference_number:
              paymentReference
                .trim()
                || null,

            notes:
              `Payment for ${invoice.invoice_number}`,
          },
        );

        setSuccess(
          "Supplier payment recorded.",
        );

        setPaymentAmount("");
        setPaymentReference("");
        setPaymentInvoiceId("");

        await refreshSelected(
          selected.id,
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
        setSaving(false);
      }
    };


  const filteredOrders =
    useMemo(
      () => {
        const query =
          search
            .trim()
            .toLowerCase();

        if (!query) {
          return orders;
        }

        return orders.filter(
          (order) =>
            order
              .purchase_order_number
              .toLowerCase()
              .includes(query)
            || (
              order.supplier_name
              ?? ""
            )
              .toLowerCase()
              .includes(query),
        );
      },
      [
        orders,
        search,
      ],
    );


  if (!user) {
    return (
      <div
        style={{
          padding: 40,
        }}
      >
        Loading...
      </div>
    );
  }


  return (
    <AppShell user={user}>
      <main style={pageStyle}>
        <header
          style={{
            display: "flex",
            justifyContent:
              "space-between",
            gap: "16px",
            alignItems:
              "center",
            flexWrap: "wrap",
          }}
        >
          <div>
            <p
              style={{
                margin: 0,
                fontSize: 12,
                fontWeight: 800,
                letterSpacing:
                  "0.12em",
              }}
            >
              PURCHASING
            </p>

            <h1
              style={{
                margin:
                  "4px 0 0",
              }}
            >
              Purchases
            </h1>

            <p
              style={{
                margin:
                  "6px 0 0",
                color:
                  "#64748b",
              }}
            >
              Purchase order → GRN →
              supplier invoice →
              payment.
            </p>
          </div>

          <button
            type="button"
            style={{
              ...buttonStyle,
              background:
                "#eef2ff",
            }}
            onClick={() =>
              void loadBaseData()
            }
          >
            <RefreshCw
              size={15}
            />{" "}
            Refresh
          </button>
        </header>


        {error ? (
          <div
            style={{
              ...cardStyle,
              borderColor:
                "#fecaca",
              background:
                "#fff7f7",
              color:
                "#991b1b",
            }}
          >
            <CircleAlert
              size={17}
            />{" "}
            {error}
          </div>
        ) : null}


        {success ? (
          <div
            style={{
              ...cardStyle,
              borderColor:
                "#bbf7d0",
              background:
                "#f0fdf4",
              color:
                "#166534",
            }}
          >
            <CheckCircle2
              size={17}
            />{" "}
            {success}
          </div>
        ) : null}


        <section style={cardStyle}>
          <h2>
            <Plus size={18} />{" "}
            New Purchase Order
          </h2>

          <form
            onSubmit={
              createPo
            }
          >
            <div style={gridStyle}>
              <label>
                Supplier *
                <select
                  required
                  style={inputStyle}
                  value={
                    supplierId
                  }
                  onChange={
                    (event) =>
                      setSupplierId(
                        event
                          .target
                          .value,
                      )
                  }
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


              <label>
                Warehouse *
                <select
                  required
                  style={inputStyle}
                  value={
                    warehouseId
                  }
                  onChange={
                    (event) =>
                      setWarehouseId(
                        event
                          .target
                          .value,
                      )
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
                Expected date
                <input
                  type="date"
                  style={inputStyle}
                  value={
                    expectedDate
                  }
                  onChange={
                    (event) =>
                      setExpectedDate(
                        event
                          .target
                          .value,
                      )
                  }
                />
              </label>
            </div>


            <div
              style={{
                marginTop: 18,
                display: "grid",
                gap: 12,
              }}
            >
              {lines.map(
                (
                  line,
                  index,
                ) => (
                  <div
                    key={index}
                    style={{
                      ...gridStyle,
                      padding: 12,
                      border:
                        "1px solid #e5e7eb",
                      borderRadius:
                        "12px",
                    }}
                  >
                    <label>
                      Product *
                      <select
                        required
                        style={
                          inputStyle
                        }
                        value={
                          line
                            .productId
                        }
                        onChange={
                          (event) => {
                            const value =
                              event
                                .target
                                .value;

                            const product =
                              products
                                .find(
                                  (item) =>
                                    String(
                                      item.id,
                                    )
                                    === value,
                                );

                            setLines(
                              (
                                current,
                              ) =>
                                current
                                  .map(
                                    (
                                      item,
                                      lineIndex,
                                    ) =>
                                      lineIndex
                                      === index
                                        ? {
                                            ...item,
                                            productId:
                                              value,
                                            unitCost:
                                              String(
                                                product
                                                  ?.purchase_cost
                                                ?? "0.00",
                                              ),
                                          }
                                        : item,
                                  ),
                            );
                          }
                        }
                      >
                        <option value="">
                          Select product
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
                            </option>
                          ),
                        )}
                      </select>
                    </label>


                    <label>
                      Quantity
                      <input
                        required
                        type="number"
                        min="0.001"
                        step="0.001"
                        style={
                          inputStyle
                        }
                        value={
                          line.quantity
                        }
                        onChange={
                          (event) =>
                            setLines(
                              (
                                current,
                              ) =>
                                current
                                  .map(
                                    (
                                      item,
                                      lineIndex,
                                    ) =>
                                      lineIndex
                                      === index
                                        ? {
                                            ...item,
                                            quantity:
                                              event
                                                .target
                                                .value,
                                          }
                                        : item,
                                  ),
                            )
                        }
                      />
                    </label>


                    <label>
                      Unit cost
                      <input
                        required
                        type="number"
                        min="0"
                        step="0.01"
                        style={
                          inputStyle
                        }
                        value={
                          line.unitCost
                        }
                        onChange={
                          (event) =>
                            setLines(
                              (
                                current,
                              ) =>
                                current
                                  .map(
                                    (
                                      item,
                                      lineIndex,
                                    ) =>
                                      lineIndex
                                      === index
                                        ? {
                                            ...item,
                                            unitCost:
                                              event
                                                .target
                                                .value,
                                          }
                                        : item,
                                  ),
                            )
                        }
                      />
                    </label>
                  </div>
                ),
              )}
            </div>


            <div
              style={{
                marginTop: 12,
              }}
            >
              <button
                type="button"
                style={{
                  ...buttonStyle,
                  background:
                    "#f1f5f9",
                }}
                onClick={() =>
                  setLines(
                    (current) => [
                      ...current,
                      {
                        ...EMPTY_LINE,
                      },
                    ],
                  )
                }
              >
                + Add product
              </button>
            </div>


            <label
              style={{
                display: "block",
                marginTop: 14,
              }}
            >
              Notes
              <textarea
                style={{
                  ...inputStyle,
                  minHeight: 70,
                }}
                value={
                  poNotes
                }
                onChange={
                  (event) =>
                    setPoNotes(
                      event
                        .target
                        .value,
                    )
                }
              />
            </label>


            <button
              type="submit"
              disabled={saving}
              style={{
                ...buttonStyle,
                marginTop: 14,
                background:
                  "#0f172a",
                color: "white",
              }}
            >
              <ShoppingCart
                size={16}
              />{" "}
              Create purchase order
            </button>
          </form>
        </section>


        <section style={cardStyle}>
          <div
            style={{
              display: "flex",
              justifyContent:
                "space-between",
              gap: 12,
              flexWrap:
                "wrap",
            }}
          >
            <h2>
              Purchase Orders
            </h2>

            <div
              style={{
                position:
                  "relative",
              }}
            >
              <Search
                size={16}
                style={{
                  position:
                    "absolute",
                  left: 10,
                  top: 12,
                }}
              />

              <input
                placeholder="Search PO..."
                style={{
                  ...inputStyle,
                  paddingLeft:
                    34,
                }}
                value={search}
                onChange={
                  (event) =>
                    setSearch(
                      event
                        .target
                        .value,
                    )
                }
              />
            </div>
          </div>


          {loading ? (
            <p>
              <Loader2
                size={16}
              />{" "}
              Loading...
            </p>
          ) : (
            <div
              style={{
                display: "grid",
                gap: 10,
              }}
            >
              {filteredOrders
                .map(
                  (order) => (
                    <button
                      key={
                        order.id
                      }
                      type="button"
                      onClick={() =>
                        void selectOrder(
                          order.id,
                        )
                      }
                      style={{
                        textAlign:
                          "left",
                        padding:
                          "12px",
                        border:
                          selected?.id
                          === order.id
                            ? "2px solid #0f172a"
                            : "1px solid #e5e7eb",
                        borderRadius:
                          "12px",
                        background:
                          "white",
                        cursor:
                          "pointer",
                      }}
                    >
                      <strong>
                        {
                          order
                            .purchase_order_number
                        }
                      </strong>

                      <div
                        style={{
                          marginTop:
                            5,
                          color:
                            "#64748b",
                        }}
                      >
                        {
                          order
                            .supplier_name
                          || `Supplier #${order.supplier_id}`
                        }
                        {" · "}
                        {
                          order.status
                        }
                        {" · "}
                        {money(
                          order
                            .grand_total,
                        )}
                      </div>
                    </button>
                  ),
                )}
            </div>
          )}
        </section>


        {selected ? (
          <section style={cardStyle}>
            <h2>
              {
                selected
                  .purchase_order_number
              }
            </h2>

            <div style={gridStyle}>
              <div>
                <small>
                  Supplier
                </small>
                <div>
                  {
                    selected
                      .supplier_name
                    || selected
                      .supplier_id
                  }
                </div>
              </div>

              <div>
                <small>
                  Status
                </small>
                <div>
                  {
                    selected.status
                  }
                </div>
              </div>

              <div>
                <small>
                  Total
                </small>
                <div>
                  {money(
                    selected
                      .grand_total,
                  )}
                </div>
              </div>
            </div>


            {selected.status
              === "draft" ? (
              <button
                type="button"
                disabled={saving}
                style={{
                  ...buttonStyle,
                  marginTop: 16,
                  background:
                    "#dcfce7",
                }}
                onClick={() =>
                  void approvePo()
                }
              >
                <CheckCircle2
                  size={16}
                />{" "}
                Approve PO
              </button>
            ) : null}


            {(
              selected.status
              === "approved"
              || selected.status
              === "partially_received"
            ) ? (
              <div
                style={{
                  marginTop: 22,
                  paddingTop: 18,
                  borderTop:
                    "1px solid #e5e7eb",
                }}
              >
                <h3>
                  <PackageCheck
                    size={17}
                  />{" "}
                  Receive / GRN
                </h3>

                <div style={gridStyle}>
                  <label>
                    Delivery note
                    <input
                      style={
                        inputStyle
                      }
                      value={
                        deliveryNote
                      }
                      onChange={
                        (event) =>
                          setDeliveryNote(
                            event
                              .target
                              .value,
                          )
                      }
                    />
                  </label>

                  <label>
                    Notes
                    <input
                      style={
                        inputStyle
                      }
                      value={
                        receiveNotes
                      }
                      onChange={
                        (event) =>
                          setReceiveNotes(
                            event
                              .target
                              .value,
                          )
                      }
                    />
                  </label>
                </div>

                <button
                  type="button"
                  disabled={saving}
                  style={{
                    ...buttonStyle,
                    marginTop: 12,
                    background:
                      "#dbeafe",
                  }}
                  onClick={() =>
                    void receivePo()
                  }
                >
                  Receive remaining stock
                </button>
              </div>
            ) : null}


            {receipts.length
              > 0 ? (
              <div
                style={{
                  marginTop: 22,
                  paddingTop: 18,
                  borderTop:
                    "1px solid #e5e7eb",
                }}
              >
                <h3>
                  <FileText
                    size={17}
                  />{" "}
                  Supplier Invoice
                </h3>

                <div style={gridStyle}>
                  <label>
                    Supplier invoice no. *
                    <input
                      style={
                        inputStyle
                      }
                      value={
                        invoiceReference
                      }
                      onChange={
                        (event) =>
                          setInvoiceReference(
                            event
                              .target
                              .value,
                          )
                      }
                    />
                  </label>

                  <label>
                    Due date
                    <input
                      type="date"
                      style={
                        inputStyle
                      }
                      value={
                        invoiceDueDate
                      }
                      onChange={
                        (event) =>
                          setInvoiceDueDate(
                            event
                              .target
                              .value,
                          )
                      }
                    />
                  </label>
                </div>

                <button
                  type="button"
                  disabled={saving}
                  style={{
                    ...buttonStyle,
                    marginTop: 12,
                    background:
                      "#fef3c7",
                  }}
                  onClick={() =>
                    void createInvoice()
                  }
                >
                  Create supplier invoice
                </button>
              </div>
            ) : null}


            {invoices.length
              > 0 ? (
              <div
                style={{
                  marginTop: 22,
                  paddingTop: 18,
                  borderTop:
                    "1px solid #e5e7eb",
                }}
              >
                <h3>
                  <CreditCard
                    size={17}
                  />{" "}
                  Supplier Payment
                </h3>

                <div style={gridStyle}>
                  <label>
                    Invoice *
                    <select
                      style={
                        inputStyle
                      }
                      value={
                        paymentInvoiceId
                      }
                      onChange={
                        (event) => {
                          const value =
                            event
                              .target
                              .value;

                          setPaymentInvoiceId(
                            value,
                          );

                          const invoice =
                            invoices
                              .find(
                                (item) =>
                                  String(
                                    item.id,
                                  )
                                  === value,
                              );

                          if (invoice) {
                            setPaymentAmount(
                              String(
                                invoice
                                  .balance_amount,
                              ),
                            );
                          }
                        }
                      }
                    >
                      <option value="">
                        Select invoice
                      </option>

                      {invoices.map(
                        (invoice) => (
                          <option
                            key={
                              invoice.id
                            }
                            value={
                              invoice.id
                            }
                          >
                            {
                              invoice
                                .invoice_number
                            }
                            {" — Balance "}
                            {money(
                              invoice
                                .balance_amount,
                            )}
                          </option>
                        ),
                      )}
                    </select>
                  </label>

                  <label>
                    Amount *
                    <input
                      type="number"
                      min="0.01"
                      step="0.01"
                      style={
                        inputStyle
                      }
                      value={
                        paymentAmount
                      }
                      onChange={
                        (event) =>
                          setPaymentAmount(
                            event
                              .target
                              .value,
                          )
                      }
                    />
                  </label>

                  <label>
                    Method
                    <select
                      style={
                        inputStyle
                      }
                      value={
                        paymentMethod
                      }
                      onChange={
                        (event) =>
                          setPaymentMethod(
                            event
                              .target
                              .value,
                          )
                      }
                    >
                      <option value="cash">
                        Cash
                      </option>
                      <option value="bank_transfer">
                        Bank transfer
                      </option>
                      <option value="cheque">
                        Cheque
                      </option>
                    </select>
                  </label>

                  <label>
                    Reference
                    <input
                      style={
                        inputStyle
                      }
                      value={
                        paymentReference
                      }
                      onChange={
                        (event) =>
                          setPaymentReference(
                            event
                              .target
                              .value,
                          )
                      }
                    />
                  </label>
                </div>

                <button
                  type="button"
                  disabled={saving}
                  style={{
                    ...buttonStyle,
                    marginTop: 12,
                    background:
                      "#dcfce7",
                  }}
                  onClick={() =>
                    void createPayment()
                  }
                >
                  Record payment
                </button>


                <div
                  style={{
                    marginTop: 16,
                    display: "grid",
                    gap: 8,
                  }}
                >
                  {invoices.map(
                    (invoice) => (
                      <div
                        key={
                          invoice.id
                        }
                        style={{
                          padding:
                            "10px",
                          border:
                            "1px solid #e5e7eb",
                          borderRadius:
                            "10px",
                        }}
                      >
                        <strong>
                          {
                            invoice
                              .invoice_number
                          }
                        </strong>
                        {" · "}
                        Paid{" "}
                        {money(
                          invoice
                            .paid_amount,
                        )}
                        {" · "}
                        Balance{" "}
                        {money(
                          invoice
                            .balance_amount,
                        )}
                      </div>
                    ),
                  )}
                </div>
              </div>
            ) : null}
          </section>
        ) : null}
      </main>
    </AppShell>
  );
}
