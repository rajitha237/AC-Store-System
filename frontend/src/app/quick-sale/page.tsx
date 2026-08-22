"use client";

// QUICK_SALE_EFFECT_LINT_REPAIR_V1

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  ArrowRight,
  Check,
  ChevronRight,
  CircleDollarSign,
  FileDown,
  Loader2,
  Minus,
  PackageSearch,
  Plus,
  ReceiptText,
  Search,
  ShoppingCart,
  UserPlus,
  Users,
  WalletCards,
  X,
} from "lucide-react";

import {
  createCustomer,
  createDraftInvoice,
  confirmInvoice,
  downloadInvoicePdf,
  downloadReceiptPdf,
  getAvailableSerials,
  getQuickSaleAverageCost,
  searchCustomers,
  searchProducts,
  type QuickSalePaymentInput,
} from "@/lib/quick-sale-api";

import {
  createInstallmentPlan,
  getCustomerLedger,
  getCustomerStatement,
} from "@/lib/installment-api";

import type {
  CustomerLedger,
  CustomerStatement,
  InstallmentPlan,
} from "@/types/installment";

import type {
  InstallmentPreview,
  QuickSaleCartItem,
  QuickSaleConfirmResponse,
  QuickSaleCustomer,
  QuickSaleDraftInvoice,
  QuickSaleFormState,
  QuickSaleProduct,
  QuickSaleSerial,
} from "@/types/quick-sale";

import styles from "./quick-sale.module.css";

type QuickSalePaymentRow = {
  id: number;
  paymentMethod:
    | "cash"
    | "card"
    | "bank_transfer"
    | "cheque"
    | "other";
  amount: string;
  referenceNumber: string;
};


function money(
  value:
    | number
    | string
    | null
    | undefined,
): string {
  const number =
    Number(value ?? 0);

  return new Intl.NumberFormat(
    "en-LK",
    {
      style: "currency",
      currency: "LKR",
      minimumFractionDigits: 2,
    },
  ).format(
    Number.isFinite(number)
      ? number
      : 0,
  );
}

function productName(
  product: QuickSaleProduct,
): string {
  return String(
    product.name ??
    product.product_name ??
    `Product #${product.id}`,
  );
}

function productSku(
  product: QuickSaleProduct,
): string {
  return String(
    product.sku ??
    product.product_code ??
    product.barcode ??
    `#${product.id}`,
  );
}

function productPrice(
  product: QuickSaleProduct,
): number {
  const value =
    product.selling_price ??
    product.sale_price ??
    product.retail_price ??
    product.unit_price ??
    0;

  const number = Number(value);

  return Number.isFinite(number)
    ? number
    : 0;
}

function customerName(
  customer: QuickSaleCustomer,
): string {
  return (
    customer.full_name ??
    customer.business_name ??
    `Customer #${customer.id}`
  );
}

function todayPlus(
  days: number,
): string {
  const date = new Date();

  date.setDate(
    date.getDate() + days,
  );

  return date
    .toISOString()
    .slice(0, 10);
}

function addPeriod(
  dateText: string,
  index: number,
  frequency:
    | "weekly"
    | "biweekly"
    | "monthly",
): string {
  const date =
    new Date(
      `${dateText}T12:00:00`,
    );

  if (frequency === "weekly") {
    date.setDate(
      date.getDate() +
      index * 7,
    );
  } else if (
    frequency === "biweekly"
  ) {
    date.setDate(
      date.getDate() +
      index * 14,
    );
  } else {
    date.setMonth(
      date.getMonth() +
      index,
    );
  }

  return date
    .toISOString()
    .slice(0, 10);
}

export default function QuickSalePage() {
  const [
    customerQuery,
    setCustomerQuery,
  ] = useState("");

  const [
    customers,
    setCustomers,
  ] = useState<
    QuickSaleCustomer[]
  >([]);

  const [
    selectedCustomer,
    setSelectedCustomer,
  ] = useState<
    QuickSaleCustomer | null
  >(null);

  const [
    customerLoading,
    setCustomerLoading,
  ] = useState(false);

  const [
    showCustomerForm,
    setShowCustomerForm,
  ] = useState(false);

  const [
    customerForm,
    setCustomerForm,
  ] = useState({
    fullName: "",
    phone: "",
    nic: "",
    address: "",
    city: "",
    smsAllowed: true,
  });

  const [
    productQuery,
    setProductQuery,
  ] = useState("");

  const [
    products,
    setProducts,
  ] = useState<
    QuickSaleProduct[]
  >([]);

  const [
    productLoading,
    setProductLoading,
  ] = useState(false);

  const [
    cart,
    setCart,
  ] = useState<
    QuickSaleCartItem[]
  >([]);

  const [
    serialPicker,
    setSerialPicker,
  ] = useState<{
    product: QuickSaleProduct;
    serials: QuickSaleSerial[];
  } | null>(null);

  const [
    serialLoading,
    setSerialLoading,
  ] = useState(false);

  const [
    form,
    setForm,
  ] = useState<QuickSaleFormState>({
    branchId: 1,
    paymentMode: "cash",
    paymentMethod: "cash",
    downPayment: "",
    interestRate: "",
    referenceNumber: "",
    notes: "",
    frequency: "monthly",
    installmentCount: 6,
    firstDueDate: todayPlus(30),
    graceDays: 3,
  });

  const [
    paymentRows,
    setPaymentRows,
  ] = useState<
    QuickSalePaymentRow[]
  >([
    {
      id: 1,
      paymentMethod: "cash",
      amount: "",
      referenceNumber: "",
    },
  ]);

  const [
    savedDraft,
    setSavedDraft,
  ] = useState<
    QuickSaleDraftInvoice | null
  >(null);


  const [
    tradeInEnabled,
    setTradeInEnabled,
  ] = useState(false);

  const [
    tradeIn,
    setTradeIn,
  ] = useState({
    brand: "",
    model: "",
    serialNumber: "",
    condition: "Used",
    description: "",
    allowance: "",
  });


  const [
    busy,
    setBusy,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  const [
    success,
    setSuccess,
  ] = useState("");

  const [
    completed,
    setCompleted,
  ] = useState<{
    invoice:
      QuickSaleDraftInvoice;
    confirmation:
      QuickSaleConfirmResponse;
    plan:
      InstallmentPlan | null;
  } | null>(null);

  const [
    ledger,
    setLedger,
  ] = useState<
    CustomerLedger | null
  >(null);

  const [
    statement,
    setStatement,
  ] = useState<
    CustomerStatement | null
  >(null);

  const subtotal =
    useMemo(
      () =>
        cart.reduce(
          (
            sum,
            item,
          ) =>
            sum +
            item.quantity *
              item.unitPrice,
          0,
        ),
      [cart],
    );

  const discountTotal =
    useMemo(
      () =>
        cart.reduce(
          (
            sum,
            item,
          ) =>
            sum +
            item.discountAmount,
          0,
        ),
      [cart],
    );

  const grandTotal =
    Math.max(
      0,
      subtotal -
        discountTotal,
    );

  const tradeInAllowance =
    tradeInEnabled
      ? Math.max(
          0,
          Number(
            tradeIn.allowance
            || 0,
          ) || 0,
        )
      : 0;

  const customerPayable =
    Math.max(
      0,
      grandTotal -
        tradeInAllowance,
    );


  const paidNow =
    paymentRows.reduce(
      (
        total,
        payment,
      ) => {
        const amount =
          Number(
            payment.amount || 0,
          );

        return (
          total
          + (
            Number.isFinite(amount)
              ? Math.max(
                  0,
                  amount,
                )
              : 0
          )
        );
      },
      0,
    );

  const downPayment =
    paidNow;

  const paymentRemaining =
    Math.max(
      0,
      customerPayable
      - paidNow,
    );

  const financedAmount =
    form.paymentMode ===
    "installment"
      ? Math.max(
          0,
          customerPayable -
            downPayment,
        )
      : 0;

  const interestRate =
    Math.max(
      0,
      Number(
        form.interestRate || 0,
      ) || 0,
    );

  const interestAmount =
    form.paymentMode ===
    "installment"
      ? Number(
          (
            financedAmount *
            interestRate /
            100
          ).toFixed(2),
        )
      : 0;

  const totalRepayable =
    form.paymentMode ===
    "installment"
      ? Number(
          (
            financedAmount +
            interestAmount
          ).toFixed(2),
        )
      : 0;

  const installmentPreview =
    useMemo<
      InstallmentPreview[]
    >(() => {
      if (
        form.paymentMode !==
          "installment" ||
        financedAmount <= 0 ||
        form.installmentCount <= 0
      ) {
        return [];
      }

      const count =
        form.installmentCount;

      const base =
        Math.floor(
          (totalRepayable /
            count) *
            100,
        ) / 100;

      let assigned = 0;

      return Array.from(
        {
          length: count,
        },
        (
          _,
          index,
        ) => {
          const amount =
            index === count - 1
              ? Number(
                  (
                    totalRepayable -
                    assigned
                  ).toFixed(2),
                )
              : base;

          assigned += amount;

          return {
            number: index + 1,
            dueDate: addPeriod(
              form.firstDueDate,
              index,
              form.frequency,
            ),
            amount,
          };
        },
      );
    }, [
      financedAmount,
      totalRepayable,
      form.firstDueDate,
      form.frequency,
      form.installmentCount,
      form.paymentMode,
    ]);

  useEffect(() => {
    if (
      customerQuery.trim()
        .length < 2
    ) {
      return;
    }

    const timeout =
      window.setTimeout(
        async () => {
          setCustomerLoading(true);

          try {
            const result =
              await searchCustomers(
                customerQuery,
              );

            setCustomers(
              result,
            );
          } catch (requestError) {
            setError(
              requestError
                instanceof Error
                ? requestError.message
                : "Customer search failed.",
            );
          } finally {
            setCustomerLoading(false);
          }
        },
        300,
      );

    return () =>
      window.clearTimeout(
        timeout,
      );
  }, [customerQuery]);

  useEffect(() => {
    if (
      productQuery.trim()
        .length < 2
    ) {
      return;
    }

    const timeout =
      window.setTimeout(
        async () => {
          setProductLoading(true);

          try {
            const result =
              await searchProducts(
                productQuery,
              );

            setProducts(result);
          } catch (requestError) {
            setError(
              requestError
                instanceof Error
                ? requestError.message
                : "Product search failed.",
            );
          } finally {
            setProductLoading(false);
          }
        },
        250,
      );

    return () =>
      window.clearTimeout(
        timeout,
      );
  }, [productQuery]);

  async function chooseProduct(
    product: QuickSaleProduct,
  ) {
    setError("");

    // AC_PHASE7C3_SERIALIZED_PRODUCT_DETECTION_REPAIR
    const serialized =
      Boolean(
        product.track_serial_numbers ??
        product.track_serial ??
        product.is_serialized ??
        product.requires_serial,
      );

    if (serialized) {
      setSerialLoading(true);

      try {
        const serials =
          await getAvailableSerials(
            product.id,
          );

        setSerialPicker({
          product,
          serials,
        });
      } catch (requestError) {
        setError(
          requestError
            instanceof Error
            ? requestError.message
            : "Could not load serial numbers.",
        );
      } finally {
        setSerialLoading(false);
      }

      return;
    }

    addCartItem(
      product,
      null,
    );
  }

  async function addCartItem(
    product: QuickSaleProduct,
    serial:
      | QuickSaleSerial
      | null,
  ) {
    // AC_QUICK_SALE_WAREHOUSE_CONTRACT_REPAIR_V3
    const warehouseId =
      serial?.warehouse_id;

    if (
      !Number.isInteger(warehouseId) ||
      warehouseId === undefined ||
      warehouseId <= 0
    ) {
      setError(
        serial
          ? "Selected serial does not have a valid warehouse. Sale was not submitted."
          : "A valid warehouse is required for this product before it can be added to Quick Sale.",
      );
      return;
    }

    const key =
      serial
        ? `${product.id}:${serial.id}`
        : `${product.id}:standard`;

    let averageCost: number | null = null;

    try {
      averageCost =
        await getQuickSaleAverageCost(
          product.id,
          warehouseId,
        );
    } catch {
      setError(
        "Unable to verify warehouse cost for this product. Sale confirmation is blocked for safety.",
      );
      return;
    }

    if (
      averageCost === null ||
      !Number.isFinite(averageCost)
    ) {
      setError(
        "Warehouse average cost is unavailable for this product. Sale confirmation is blocked for safety.",
      );
      return;
    }

    setCart(
      (
        current,
      ) => {
        const existing =
          current.find(
            (item) =>
              item.key === key,
          );

        if (
          existing &&
          !serial
        ) {
          return current.map(
            (item) =>
              item.key === key
                ? {
                    ...item,
                    quantity:
                      item.quantity +
                      1,
                  }
                : item,
          );
        }

        return [
          ...current,
          {
            key,
            productId:
              product.id,
              warehouseId,
            productName:
              productName(
                product,
              ),
            sku:
              productSku(
                product,
              ),
            quantity: 1,
            unitPrice:
              productPrice(
                product,
              ),
            discountAmount: 0,
            // AC_BELOW_COST_UI_PROTECTION
            averageCost,
            serialId:
              serial?.id ??
              null,
            serialNumber:
              serial?.serial_number ??
              null,
          },
        ];
      },
    );

    setProductQuery("");
    setProducts([]);
    setSerialPicker(null);
  }

  function changeQuantity(
    key: string,
    delta: number,
  ) {
    setCart(
      (
        current,
      ) =>
        current
          .map(
            (item) => {
              if (
                item.key !== key
              ) {
                return item;
              }

              if (
                item.serialId
              ) {
                return item;
              }

              return {
                ...item,
                quantity:
                  Math.max(
                    1,
                    item.quantity +
                      delta,
                  ),
              };
            },
          ),
    );
  }

  function changeSellingPrice(
    key: string,
    value: string,
  ) {
    const requestedPrice =
      Number(value);

    if (
      !Number.isFinite(requestedPrice) ||
      requestedPrice < 0
    ) {
      return;
    }

    setCart(
      (current) =>
        current.map(
          (item) => {
            if (item.key !== key) {
              return item;
            }

            const originalLineTotal =
              item.unitPrice *
              item.quantity;

            const requestedLineTotal =
              requestedPrice *
              item.quantity;

            const discountAmount =
              Math.max(
                0,
                Number(
                  (
                    originalLineTotal -
                    requestedLineTotal
                  ).toFixed(2),
                ),
              );

            return {
              ...item,
              discountAmount,
            };
          },
        ),
    );
  }

  function effectiveUnitPrice(
    item: QuickSaleCartItem,
  ): number {
    if (item.quantity <= 0) {
      return item.unitPrice;
    }

    return Number(
      (
        (
          item.unitPrice *
          item.quantity -
          item.discountAmount
        ) /
        item.quantity
      ).toFixed(2),
    );
  }

  function removeCartItem(
    key: string,
  ) {
    setCart(
      (
        current,
      ) =>
        current.filter(
          (item) =>
            item.key !== key,
        ),
    );
  }

  function addPaymentRow() {
    setPaymentRows(
      (current) => {
        const nextId =
          current.reduce(
            (
              highest,
              item,
            ) =>
              Math.max(
                highest,
                item.id,
              ),
            0,
          ) + 1;

        return [
          ...current,
          {
            id: nextId,
            paymentMethod: "cash",
            amount: "",
            referenceNumber: "",
          },
        ];
      },
    );
  }


  function removePaymentRow(
    id: number,
  ) {
    setPaymentRows(
      (current) => {
        if (
          current.length <= 1
        ) {
          return [
            {
              id: current[0]?.id ?? 1,
              paymentMethod: "cash",
              amount: "",
              referenceNumber: "",
            },
          ];
        }

        return current.filter(
          (item) =>
            item.id !== id,
        );
      },
    );
  }


  function updatePaymentRow(
    id: number,
    patch:
      Partial<
        QuickSalePaymentRow
      >,
  ) {
    setPaymentRows(
      (current) =>
        current.map(
          (item) =>
            item.id === id
              ? {
                  ...item,
                  ...patch,
                }
              : item,
        ),
    );
  }


  function fillPaymentBalance(
    id: number,
  ) {
    const otherPayments =
      paymentRows.reduce(
        (
          total,
          payment,
        ) => {
          if (
            payment.id === id
          ) {
            return total;
          }

          const amount =
            Number(
              payment.amount || 0,
            );

          return (
            total
            + (
              Number.isFinite(
                amount,
              )
                ? Math.max(
                    0,
                    amount,
                  )
                : 0
            )
          );
        },
        0,
      );

    updatePaymentRow(
      id,
      {
        amount:
          Math.max(
            0,
            customerPayable
            - otherPayments,
          ).toFixed(2),
      },
    );
  }


  function paymentInputs():
    QuickSalePaymentInput[] {
    return paymentRows
      .map(
        (payment) => ({
          amount:
            Math.max(
              0,
              Number(
                payment.amount
                || 0,
              ) || 0,
            ),
          payment_method:
            payment.paymentMethod,
          reference_number:
            payment.referenceNumber
              .trim()
              || null,
          notes:
            form.notes.trim()
            || null,
        }),
      )
      .filter(
        (payment) =>
          payment.amount > 0,
      );
  }


  async function registerCustomer() {
    if (
      !customerForm.fullName
        .trim() ||
      !customerForm.phone
        .trim()
    ) {
      setError(
        "Customer name and phone number are required.",
      );
      return;
    }

    const invalidWarehouseItem =
      cart.find(
        (item) =>
          !Number.isInteger(item.warehouseId) ||
          item.warehouseId <= 0,
      );

    if (invalidWarehouseItem) {
      setError(
        `A valid warehouse is required for ${invalidWarehouseItem.productName}. Sale was not submitted.`,
      );
      return;
    }

    setBusy(true);
    setError("");

    try {
      const customer =
        await createCustomer({
          full_name:
            customerForm.fullName.trim(),
          primary_phone:
            customerForm.phone.trim(),
          nic_number:
            customerForm.nic.trim() ||
            null,
          address_line_1:
            customerForm.address.trim() ||
            null,
          city:
            customerForm.city.trim() ||
            null,
          sms_allowed:
            customerForm.smsAllowed,
          sms_phone:
            customerForm.smsAllowed
              ? customerForm.phone.trim()
              : null,
        });

      setSelectedCustomer(
        customer,
      );

      setCustomerQuery("");
      setCustomers([]);
      setShowCustomerForm(false);

      setCustomerForm({
        fullName: "",
        phone: "",
        nic: "",
        address: "",
        city: "",
        smsAllowed: true,
      });

      setSuccess(
        "Customer registered and selected.",
      );
    } catch (requestError) {
      setError(
        requestError
          instanceof Error
          ? requestError.message
          : "Customer registration failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function completeSale(
    saveAsDraft = false,
  ) {
    setError("");
    setSuccess("");

    if (!selectedCustomer) {
      setError(
        "Select or register a customer first.",
      );
      return;
    }

    if (cart.length === 0) {
      setError(
        "Add at least one product.",
      );
      return;
    }

    const belowCostItems = cart.filter(
      (item) =>
        item.averageCost !== null &&
        effectiveUnitPrice(item) <
          item.averageCost,
    );

    if (belowCostItems.length > 0) {
      setError(
        "Sale cannot be confirmed because one or more products are priced below warehouse average cost.",
      );
      return;
    }

    if (
      tradeInEnabled
      && tradeInAllowance <= 0
    ) {
      setError(
        "Enter a valid trade-in allowance.",
      );
      return;
    }

    if (
      tradeInEnabled
      && tradeInAllowance >
        grandTotal
    ) {
      setError(
        "Trade-in allowance cannot exceed the sale total.",
      );
      return;
    }

    if (
      tradeInEnabled
      && !(
        tradeIn.brand.trim()
        || tradeIn.model.trim()
        || tradeIn.serialNumber.trim()
        || tradeIn.description.trim()
      )
    ) {
      setError(
        "Enter brand, model, serial number or a description for the trade-in unit.",
      );
      return;
    }


    if (
      !Number.isFinite(
        form.branchId,
      ) ||
      form.branchId <= 0
    ) {
      setError(
        "A valid branch ID is required.",
      );
      return;
    }

    if (
      form.paymentMode ===
        "installment" &&
      financedAmount <= 0
    ) {
      setError(
        "Installment sale must have an outstanding financed balance.",
      );
      return;
    }

    if (
      paidNow >
      customerPayable
    ) {
      setError(
        "Combined payments cannot exceed the customer payable balance.",
      );
      return;
    }

    if (
      !saveAsDraft
      && form.paymentMode ===
        "cash"
      && paidNow <= 0
    ) {
      setError(
        "Enter a payment amount or use Save as Draft to collect payment later.",
      );
      return;
    }

    if (
      form.paymentMode ===
        "installment" &&
      (
        !Number.isFinite(
          interestRate,
        ) ||
        interestRate < 0 ||
        interestRate > 100
      )
    ) {
      setError(
        "Interest rate must be between 0% and 100%.",
      );
      return;
    }

    setBusy(true);

    try {
      const invoice =
        savedDraft
        ?? await createDraftInvoice({
          branch_id:
            form.branchId,
          customer_id:
            selectedCustomer.id,
          invoice_discount_amount:
            0,
          tax_amount: 0,
          notes:
            form.notes.trim() ||
            null,
          trade_ins:
            tradeInEnabled
              ? [
                  {
                    brand:
                      tradeIn.brand.trim()
                      || null,
                    model:
                      tradeIn.model.trim()
                      || null,
                    serial_number:
                      tradeIn.serialNumber
                        .trim()
                      || null,
                    condition:
                      tradeIn.condition
                        .trim()
                      || null,
                    description:
                      tradeIn.description
                        .trim()
                      || null,
                    allowance_amount:
                      tradeInAllowance,
                  },
                ]
              : [],
          items:
            cart.map(
              (item) => ({
                product_id:
                  item.productId,
                  warehouse_id:
                    item.warehouseId,
                quantity:
                  item.quantity,
                unit_price:
                  item.unitPrice,
                discount_amount:
                  item.discountAmount,
                serial_number_id:
                  item.serialId ??
                  null,
              }),
            ),
        });

      if (saveAsDraft) {
        setSavedDraft(
          invoice,
        );

        setSuccess(
          `Draft ${invoice.invoice_number ?? `#${invoice.id}`} saved. Payment can be received later from Sales.`,
        );

        return;
      }

      const initialPayments =
        paymentInputs();

      const confirmation =
        await confirmInvoice(
          invoice.id,
          null,
          initialPayments,
        );

      setSavedDraft(
        null,
      );

      let plan:
        | InstallmentPlan
        | null = null;

      if (
        form.paymentMode ===
          "installment" &&
        financedAmount > 0
      ) {
        plan =
          await createInstallmentPlan({
            invoice_id:
              invoice.id,
            frequency:
              form.frequency,
            installment_count:
              form.installmentCount,
            first_due_date:
              form.firstDueDate,
            grace_days:
              form.graceDays,
            interest_rate:
              interestRate,
            notes:
              form.notes.trim() ||
              null,
          });
      }

      setCompleted({
        invoice,
        confirmation,
        plan,
      });

      setSuccess(
        plan
          ? `Sale completed. Installment agreement ${plan.agreement_number} created.`
          : "Sale completed successfully.",
      );

      try {
        const [
          ledgerResult,
          statementResult,
        ] =
          await Promise.all([
            getCustomerLedger(
              selectedCustomer.id,
            ),
            getCustomerStatement(
              selectedCustomer.id,
            ),
          ]);

        setLedger(
          ledgerResult,
        );

        setStatement(
          statementResult,
        );
      } catch {
        // Sale completion is not failed by
        // optional post-sale reporting reads.
      }
    } catch (requestError) {
      setError(
        requestError
          instanceof Error
          ? requestError.message
          : "Sale could not be completed.",
      );
    } finally {
      setBusy(false);
    }
  }

  function newSale() {
    setCart([]);
    setSelectedCustomer(
      null,
    );
    setCustomerQuery("");
    setProductQuery("");
    setProducts([]);
    setCustomers([]);
    setCompleted(null);
    setLedger(null);
    setStatement(null);
    setError("");
    setSuccess("");
    setSavedDraft(null);

    setPaymentRows([
      {
        id: 1,
        paymentMethod: "cash",
        amount: "",
        referenceNumber: "",
      },
    ]);

    setTradeInEnabled(false);

    setTradeIn({
      brand: "",
      model: "",
      serialNumber: "",
      condition: "Used",
      description: "",
      allowance: "",
    });

    setForm({
      branchId:
        form.branchId,
      paymentMode: "cash",
      paymentMethod: "cash",
      downPayment: "",
      interestRate: "",
      referenceNumber: "",
      notes: "",
      frequency: "monthly",
      installmentCount: 6,
      firstDueDate:
        todayPlus(30),
      graceDays: 3,
    });
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <div>
          <div className={styles.eyebrow}>
            Counter workspace
          </div>

          <h1>
            Quick Sale
          </h1>

          <p>
            Customer, products, payment,
            installment agreement and
            documents — one guided flow.
          </p>
        </div>

        <div className={styles.heroSteps}>
          <span>
            <Check size={15} />
            Customer
          </span>

          <ChevronRight size={16} />

          <span>
            <ShoppingCart size={15} />
            Cart
          </span>

          <ChevronRight size={16} />

          <span>
            <WalletCards size={15} />
            Payment
          </span>

          <ChevronRight size={16} />

          <span>
            <ReceiptText size={15} />
            Documents
          </span>
        </div>
      </section>

      {error ? (
        <div className={styles.error}>
          <X size={18} />
          <span>{error}</span>

          <button
            type="button"
            onClick={() =>
              setError("")
            }
          >
            <X size={16} />
          </button>
        </div>
      ) : null}

      {success ? (
        <div className={styles.success}>
          <Check size={18} />
          {success}
        </div>
      ) : null}

      <div className={styles.workspace}>
        <section className={styles.mainColumn}>
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <div>
                <span className={styles.step}>
                  01
                </span>

                <h2>
                  Customer
                </h2>
              </div>

              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() =>
                  setShowCustomerForm(
                    true,
                  )
                }
              >
                <UserPlus size={17} />
                New customer
              </button>
            </div>

            {selectedCustomer ? (
              <div className={styles.selectedCustomer}>
                <div className={styles.avatar}>
                  <Users size={22} />
                </div>

                <div className={styles.customerInfo}>
                  <strong>
                    {customerName(
                      selectedCustomer,
                    )}
                  </strong>

                  <span>
                    {selectedCustomer.customer_number ??
                      "Registered customer"}
                    {" · "}
                    {selectedCustomer.primary_phone ??
                      "No phone"}
                  </span>
                </div>

                <div className={styles.balanceBox}>
                  <small>
                    Current balance
                  </small>

                  <strong>
                    {money(
                      selectedCustomer.current_balance,
                    )}
                  </strong>
                </div>

                <button
                  type="button"
                  className={styles.iconButton}
                  onClick={() =>
                    setSelectedCustomer(
                      null,
                    )
                  }
                  aria-label="Change customer"
                >
                  <X size={18} />
                </button>
              </div>
            ) : (
              <>
                <div className={styles.searchBox}>
                  <Search size={19} />

                  <input
                    value={customerQuery}
                    onChange={(event) => {
                      const value =
                        event.target.value;

                      setCustomerQuery(
                        value,
                      );

                      if (
                        value.trim()
                          .length < 2
                      ) {
                        setCustomers([]);
                      }
                    }}
                    placeholder="Search by name, phone, NIC or customer number"
                    autoComplete="off"
                  />

                  {customerLoading ? (
                    <Loader2
                      size={18}
                      className={styles.spin}
                    />
                  ) : null}
                </div>

                {customers.length > 0 ? (
                  <div className={styles.searchResults}>
                    {customers.map(
                      (customer) => (
                        <button
                          type="button"
                          key={customer.id}
                          onClick={() => {
                            setSelectedCustomer(
                              customer,
                            );
                            setCustomerQuery(
                              "",
                            );
                            setCustomers(
                              [],
                            );
                          }}
                        >
                          <span>
                            <strong>
                              {customerName(
                                customer,
                              )}
                            </strong>

                            <small>
                              {customer.customer_number ??
                                ""}
                              {" "}
                              {customer.primary_phone ??
                                ""}
                            </small>
                          </span>

                          <span>
                            {money(
                              customer.current_balance,
                            )}
                            <ArrowRight
                              size={16}
                            />
                          </span>
                        </button>
                      ),
                    )}
                  </div>
                ) : null}
              </>
            )}
          </div>

          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <div>
                <span className={styles.step}>
                  02
                </span>

                <h2>
                  Products
                </h2>
              </div>

              <div className={styles.cartCount}>
                {cart.reduce(
                  (
                    sum,
                    item,
                  ) =>
                    sum +
                    item.quantity,
                  0,
                )}
                {" "}
                items
              </div>
            </div>

            <div className={styles.searchBox}>
              <PackageSearch size={19} />

              <input
                value={productQuery}
                onChange={(event) => {
                  const value =
                    event.target.value;

                  setProductQuery(
                    value,
                  );

                  if (
                    value.trim()
                      .length < 2
                  ) {
                    setProducts([]);
                  }
                }}
                placeholder="Scan barcode or search product / SKU"
                autoComplete="off"
              />

              {productLoading ||
              serialLoading ? (
                <Loader2
                  size={18}
                  className={styles.spin}
                />
              ) : null}
            </div>

            {products.length > 0 ? (
              <div className={styles.productResults}>
                {products.map(
                  (product) => (
                    <button
                      type="button"
                      key={product.id}
                      onClick={() =>
                        void chooseProduct(
                          product,
                        )
                      }
                    >
                      <span>
                        <strong>
                          {productName(
                            product,
                          )}
                        </strong>

                        <small>
                          {productSku(
                            product,
                          )}
                        </small>
                      </span>

                      <strong>
                        {money(
                          productPrice(
                            product,
                          ),
                        )}
                      </strong>
                    </button>
                  ),
                )}
              </div>
            ) : null}

            {cart.length === 0 ? (
              <div className={styles.emptyCart}>
                <ShoppingCart size={32} />
                <strong>
                  Cart is empty
                </strong>
                <span>
                  Search or scan a product
                  to begin the sale.
                </span>
              </div>
            ) : (
              <div className={styles.cartTable}>
                {cart.map(
                  (item) => (
                    <div
                      className={styles.cartRow}
                      key={item.key}
                    >
                      <div className={styles.cartProduct}>
                        <strong>
                          {item.productName}
                        </strong>

                        <small>
                          {item.sku}

                          {item.serialNumber
                            ? ` · S/N ${item.serialNumber}`
                            : ""}
                        </small>

                        {item.averageCost !== null &&
                        effectiveUnitPrice(item) <
                          item.averageCost ? (
                          <small
                            style={{
                              color: "#dc2626",
                              fontWeight: 700,
                            }}
                          >
                            Selling below cost · Cost{" "}
                            {money(item.averageCost)} ·
                            Loss{" "}
                            {money(
                              (
                                item.averageCost -
                                effectiveUnitPrice(
                                  item,
                                )
                              ) *
                                item.quantity,
                            )}
                          </small>
                        ) : null}
                      </div>

                      <div className={styles.qtyControl}>
                        <button
                          type="button"
                          disabled={
                            Boolean(
                              item.serialId,
                            )
                          }
                          onClick={() =>
                            changeQuantity(
                              item.key,
                              -1,
                            )
                          }
                        >
                          <Minus size={14} />
                        </button>

                        <span>
                          {item.quantity}
                        </span>

                        <button
                          type="button"
                          disabled={
                            Boolean(
                              item.serialId,
                            )
                          }
                          onClick={() =>
                            changeQuantity(
                              item.key,
                              1,
                            )
                          }
                        >
                          <Plus size={14} />
                        </button>
                      </div>

                      <div
                        className={
                          styles.salePriceControl
                        }
                      >
                        <small>
                          Selling price
                        </small>

                        <input
                          type="number"
                          min={0}
                          step="0.01"
                          value={
                            effectiveUnitPrice(
                              item,
                            )
                          }
                          onChange={(event) =>
                            changeSellingPrice(
                              item.key,
                              event.target.value,
                            )
                          }
                          aria-label={
                            `Selling price for ${item.productName}`
                          }
                        />

                        {item.discountAmount > 0 ? (
                          <span>
                            List{" "}
                            {money(
                              item.unitPrice,
                            )}
                            {" · "}
                            Discount{" "}
                            {money(
                              item.discountAmount,
                            )}
                          </span>
                        ) : (
                          <span>
                            List{" "}
                            {money(
                              item.unitPrice,
                            )}
                          </span>
                        )}
                      </div>

                      <div className={styles.linePrice}>
                        {money(
                          item.unitPrice *
                            item.quantity -
                            item.discountAmount,
                        )}
                      </div>

                      <button
                        type="button"
                        className={styles.removeButton}
                        onClick={() =>
                          removeCartItem(
                            item.key,
                          )
                        }
                        aria-label="Remove item"
                      >
                        <X size={17} />
                      </button>
                    </div>
                  ),
                )}
              </div>
            )}
          </div>

          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <div>
                <span className={styles.step}>
                  EXCHANGE
                </span>

                <h2>
                  Trade-in / Exchange
                </h2>

                <p className={styles.tradeInHint}>
                  Accept the customer&apos;s old A/C unit and apply its agreed value separately from normal discounts.
                </p>
              </div>

              <label className={styles.tradeInToggle}>
                <input
                  type="checkbox"
                  checked={tradeInEnabled}
                  onChange={(event) =>
                    setTradeInEnabled(
                      event.target.checked,
                    )
                  }
                />

                Use trade-in
              </label>
            </div>

            {tradeInEnabled && (
              <>
                <div className={styles.formGrid}>
                  <label>
                    <span>Brand</span>

                    <input
                      value={tradeIn.brand}
                      onChange={(event) =>
                        setTradeIn(
                          (current) => ({
                            ...current,
                            brand:
                              event.target.value,
                          }),
                        )
                      }
                      placeholder="e.g. Panasonic"
                    />
                  </label>

                  <label>
                    <span>Model</span>

                    <input
                      value={tradeIn.model}
                      onChange={(event) =>
                        setTradeIn(
                          (current) => ({
                            ...current,
                            model:
                              event.target.value,
                          }),
                        )
                      }
                      placeholder="Old unit model"
                    />
                  </label>

                  <label>
                    <span>Serial number</span>

                    <input
                      value={
                        tradeIn.serialNumber
                      }
                      onChange={(event) =>
                        setTradeIn(
                          (current) => ({
                            ...current,
                            serialNumber:
                              event.target.value,
                          }),
                        )
                      }
                      placeholder="Optional serial"
                    />
                  </label>

                  <label>
                    <span>Condition</span>

                    <select
                      value={
                        tradeIn.condition
                      }
                      onChange={(event) =>
                        setTradeIn(
                          (current) => ({
                            ...current,
                            condition:
                              event.target.value,
                          }),
                        )
                      }
                    >
                      <option value="Used">
                        Used
                      </option>
                      <option value="Working">
                        Working
                      </option>
                      <option value="Repair required">
                        Repair required
                      </option>
                      <option value="Scrap">
                        Scrap
                      </option>
                    </select>
                  </label>

                  <label>
                    <span>
                      Trade-in allowance
                    </span>

                    <input
                      type="number"
                      min={0}
                      step="0.01"
                      value={
                        tradeIn.allowance
                      }
                      onChange={(event) =>
                        setTradeIn(
                          (current) => ({
                            ...current,
                            allowance:
                              event.target.value,
                          }),
                        )
                      }
                      placeholder="0.00"
                    />
                  </label>

                  <label
                    className={
                      styles.fullField
                    }
                  >
                    <span>
                      Old unit details
                    </span>

                    <textarea
                      rows={2}
                      value={
                        tradeIn.description
                      }
                      onChange={(event) =>
                        setTradeIn(
                          (current) => ({
                            ...current,
                            description:
                              event.target.value,
                          }),
                        )
                      }
                      placeholder="Capacity, condition, accessories, defects or any other identifying information"
                    />
                  </label>
                </div>

                <div className={styles.tradeInSummary}>
                  <div>
                    <span>
                      Sale total
                    </span>

                    <strong>
                      {money(grandTotal)}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Trade-in allowance
                    </span>

                    <strong>
                      -{money(
                        tradeInAllowance,
                      )}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Customer payable
                    </span>

                    <strong>
                      {money(
                        customerPayable,
                      )}
                    </strong>
                  </div>
                </div>
              </>
            )}
          </div>


          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <div>
                <span className={styles.step}>
                  03
                </span>

                <h2>
                  Payment
                </h2>
              </div>
            </div>

            <div className={styles.modeTabs}>
              <button
                type="button"
                className={
                  form.paymentMode ===
                  "cash"
                    ? styles.modeActive
                    : ""
                }
                onClick={() =>
                  setForm(
                    (
                      current,
                    ) => ({
                      ...current,
                      paymentMode:
                        "cash",
                      downPayment:
                        "",
                      interestRate:
                        "",
                    }),
                  )
                }
              >
                <CircleDollarSign
                  size={20}
                />
                Pay now
                <small>
                  Full or split payment
                </small>
              </button>

              <button
                type="button"
                className={
                  form.paymentMode ===
                  "installment"
                    ? styles.modeActive
                    : ""
                }
                onClick={() =>
                  setForm(
                    (
                      current,
                    ) => ({
                      ...current,
                      paymentMode:
                        "installment",
                    }),
                  )
                }
              >
                <WalletCards
                  size={20}
                />
                Installment
                <small>
                  Split down payment + schedule
                </small>
              </button>
            </div>

            <div
              className={
                styles.splitPaymentSection
              }
            >
              <div
                className={
                  styles.splitPaymentHeader
                }
              >
                <div>
                  <strong>
                    Split payment
                  </strong>

                  <span>
                    Use one or more payment methods.
                  </span>
                </div>

                <button
                  type="button"
                  className={
                    styles.secondaryButton
                  }
                  onClick={
                    addPaymentRow
                  }
                  disabled={
                    paymentRows.length >= 10
                  }
                >
                  <Plus size={16} />
                  Add payment
                </button>
              </div>

              <div
                className={
                  styles.paymentRows
                }
              >
                {paymentRows.map(
                  (
                    payment,
                    index,
                  ) => (
                    <div
                      className={
                        styles.paymentRow
                      }
                      key={payment.id}
                    >
                      <div
                        className={
                          styles.paymentNumber
                        }
                      >
                        {index + 1}
                      </div>

                      <label>
                        <span>
                          Method
                        </span>

                        <select
                          value={
                            payment
                              .paymentMethod
                          }
                          onChange={
                            (event) =>
                              updatePaymentRow(
                                payment.id,
                                {
                                  paymentMethod:
                                    event.target
                                      .value as QuickSalePaymentRow["paymentMethod"],
                                },
                              )
                          }
                        >
                          <option value="cash">
                            Cash
                          </option>

                          <option value="card">
                            Card
                          </option>

                          <option value="bank_transfer">
                            Bank transfer
                          </option>

                          <option value="cheque">
                            Cheque
                          </option>

                          <option value="other">
                            Other
                          </option>
                        </select>
                      </label>

                      <label>
                        <span>
                          Amount
                        </span>

                        <div
                          className={
                            styles.paymentAmountControl
                          }
                        >
                          <input
                            type="number"
                            min={0}
                            step="0.01"
                            value={
                              payment.amount
                            }
                            onChange={
                              (event) =>
                                updatePaymentRow(
                                  payment.id,
                                  {
                                    amount:
                                      event.target
                                        .value,
                                  },
                                )
                            }
                            placeholder="0.00"
                          />

                          <button
                            type="button"
                            onClick={() =>
                              fillPaymentBalance(
                                payment.id,
                              )
                            }
                          >
                            Balance
                          </button>
                        </div>
                      </label>

                      <label>
                        <span>
                          {payment
                            .paymentMethod
                            === "cheque"
                            ? "Cheque / reference no."
                            : "Reference"
                          }
                        </span>

                        <input
                          value={
                            payment
                              .referenceNumber
                          }
                          onChange={
                            (event) =>
                              updatePaymentRow(
                                payment.id,
                                {
                                  referenceNumber:
                                    event.target
                                      .value,
                                },
                              )
                          }
                          placeholder={
                            payment
                              .paymentMethod
                              === "cash"
                              ? "Optional"
                              : "Recommended"
                          }
                        />
                      </label>

                      <button
                        type="button"
                        className={
                          styles.paymentRemoveButton
                        }
                        onClick={() =>
                          removePaymentRow(
                            payment.id,
                          )
                        }
                        aria-label={
                          `Remove payment ${index + 1}`
                        }
                      >
                        <X size={16} />
                      </button>
                    </div>
                  ),
                )}
              </div>

              <div
                className={
                  styles.paymentTotals
                }
              >
                <div>
                  <span>
                    Customer payable
                  </span>

                  <strong>
                    {money(
                      customerPayable,
                    )}
                  </strong>
                </div>

                <div>
                  <span>
                    Paid now
                  </span>

                  <strong>
                    {money(
                      paidNow,
                    )}
                  </strong>
                </div>

                <div>
                  <span>
                    Remaining
                  </span>

                  <strong>
                    {money(
                      paymentRemaining,
                    )}
                  </strong>
                </div>
              </div>

              {savedDraft ? (
                <div
                  className={
                    styles.draftNotice
                  }
                >
                  Draft{" "}
                  <strong>
                    {savedDraft
                      .invoice_number
                      ?? `#${savedDraft.id}`
                    }
                  </strong>{" "}
                  is saved. Confirming now will use this same draft invoice.
                </div>
              ) : null}
            </div>

            <div className={styles.formGrid}>
              <label>
                <span>
                  Branch ID
                </span>

                <input
                  type="number"
                  min={1}
                  value={
                    form.branchId
                  }
                  onChange={(event) =>
                    setForm(
                      (
                        current,
                      ) => ({
                        ...current,
                        branchId:
                          Number(
                            event.target
                              .value,
                          ) || 0,
                      }),
                    )
                  }
                />
              </label>

              {form.paymentMode ===
              "installment" ? (
                <>
                  <label>
                    <span>
                      Interest %
                    </span>

                    <input
                      type="number"
                      min={0}
                      max={100}
                      step="0.0001"
                      value={
                        form.interestRate
                      }
                      onChange={(event) =>
                        setForm(
                          (
                            current,
                          ) => ({
                            ...current,
                            interestRate:
                              event.target
                                .value,
                          }),
                        )
                      }
                      placeholder="0.00"
                    />
                  </label>

                  <label>
                    <span>
                      Frequency
                    </span>

                    <select
                      value={
                        form.frequency
                      }
                      onChange={(event) =>
                        setForm(
                          (
                            current,
                          ) => ({
                            ...current,
                            frequency:
                              event.target
                                .value as QuickSaleFormState["frequency"],
                          }),
                        )
                      }
                    >
                      <option value="weekly">
                        Weekly
                      </option>
                      <option value="biweekly">
                        Every 2 weeks
                      </option>
                      <option value="monthly">
                        Monthly
                      </option>
                    </select>
                  </label>

                  <label>
                    <span>
                      Installments
                    </span>

                    <input
                      type="number"
                      min={1}
                      max={60}
                      value={
                        form.installmentCount
                      }
                      onChange={(event) =>
                        setForm(
                          (
                            current,
                          ) => ({
                            ...current,
                            installmentCount:
                              Math.max(
                                1,
                                Number(
                                  event.target
                                    .value,
                                ) || 1,
                              ),
                          }),
                        )
                      }
                    />
                  </label>

                  <label>
                    <span>
                      First due date
                    </span>

                    <input
                      type="date"
                      value={
                        form.firstDueDate
                      }
                      onChange={(event) =>
                        setForm(
                          (
                            current,
                          ) => ({
                            ...current,
                            firstDueDate:
                              event.target
                                .value,
                          }),
                        )
                      }
                    />
                  </label>

                  <label>
                    <span>
                      Grace days
                    </span>

                    <input
                      type="number"
                      min={0}
                      max={30}
                      value={
                        form.graceDays
                      }
                      onChange={(event) =>
                        setForm(
                          (
                            current,
                          ) => ({
                            ...current,
                            graceDays:
                              Math.max(
                                0,
                                Number(
                                  event.target
                                    .value,
                                ) || 0,
                              ),
                          }),
                        )
                      }
                    />
                  </label>
                </>
              ) : null}

              <label className={styles.fullField}>
                <span>
                  Sale notes
                </span>

                <textarea
                  rows={3}
                  value={form.notes}
                  onChange={(event) =>
                    setForm(
                      (
                        current,
                      ) => ({
                        ...current,
                        notes:
                          event.target
                            .value,
                      }),
                    )
                  }
                  placeholder="Optional notes"
                />
              </label>
            </div>

            {form.paymentMode ===
              "installment" &&
            installmentPreview.length >
              0 ? (
              <div className={styles.schedule}>
                <div className={styles.scheduleHeader}>
                  <div>
                    <strong>
                      Schedule preview
                    </strong>

                    <span>
                      Final schedule is
                      confirmed by backend.
                    </span>
                  </div>

                  <strong>
                    {money(
                      totalRepayable,
                    )}
                  </strong>
                </div>

                <div className={styles.scheduleList}>
                  {installmentPreview.map(
                    (item) => (
                      <div
                        key={
                          item.number
                        }
                      >
                        <span>
                          #{item.number}
                        </span>

                        <span>
                          {item.dueDate}
                        </span>

                        <strong>
                          {money(
                            item.amount,
                          )}
                        </strong>
                      </div>
                    ),
                  )}
                </div>
              </div>
            ) : null}
          </div>
        </section>

        <aside className={styles.summaryColumn}>
          <div className={styles.summaryCard}>
            <div className={styles.summaryTitle}>
              <span>
                Sale summary
              </span>

              <ShoppingCart size={19} />
            </div>

            <div className={styles.summaryLines}>
              <div>
                <span>
                  Subtotal
                </span>
                <strong>
                  {money(subtotal)}
                </strong>
              </div>

              <div>
                <span>
                  Discounts
                </span>
                <strong>
                  -{money(
                    discountTotal,
                  )}
                </strong>
              </div>
            </div>

            <div className={styles.total}>
              <span>
                Total
              </span>

              <strong>
                {money(
                  grandTotal,
                )}
              </strong>
            </div>

            {tradeInAllowance > 0 ? (
              <div
                className={
                  styles.financeSummary
                }
              >
                <div>
                  <span>
                    Trade-in allowance
                  </span>

                  <strong>
                    -{money(
                      tradeInAllowance,
                    )}
                  </strong>
                </div>

                <div>
                  <span>
                    Customer payable
                  </span>

                  <strong>
                    {money(
                      customerPayable,
                    )}
                  </strong>
                </div>
              </div>
            ) : null}

            <div
              className={
                styles.paymentSummary
              }
            >
              <div>
                <span>
                  Paid now
                </span>

                <strong>
                  {money(
                    paidNow,
                  )}
                </strong>
              </div>

              <div>
                <span>
                  Remaining
                </span>

                <strong>
                  {money(
                    paymentRemaining,
                  )}
                </strong>
              </div>
            </div>

            {form.paymentMode ===
            "installment" ? (
              <div className={styles.financeSummary}>
                <div>
                  <span>
                    Down payment
                  </span>
                  <strong>
                    {money(
                      downPayment,
                    )}
                  </strong>
                </div>

                <div>
                  <span>
                    Principal
                  </span>
                  <strong>
                    {money(
                      financedAmount,
                    )}
                  </strong>
                </div>

                <div>
                  <span>
                    Interest ({interestRate}%)
                  </span>
                  <strong>
                    {money(
                      interestAmount,
                    )}
                  </strong>
                </div>

                <div>
                  <span>
                    Total repayable
                  </span>
                  <strong>
                    {money(
                      totalRepayable,
                    )}
                  </strong>
                </div>

                <div>
                  <span>
                    Approx. installment
                  </span>
                  <strong>
                    {money(
                      installmentPreview[0]
                        ?.amount ??
                        0,
                    )}
                  </strong>
                </div>
              </div>
            ) : null}

            <div
              className={
                styles.saleActions
              }
            >
              <button
                type="button"
                className={
                  styles.draftButton
                }
                disabled={
                  busy
                  || !selectedCustomer
                  || cart.length === 0
                  || Boolean(
                    savedDraft,
                  )
                }
                onClick={() =>
                  void completeSale(
                    true,
                  )
                }
              >
                {busy ? (
                  <Loader2
                    size={18}
                    className={
                      styles.spin
                    }
                  />
                ) : (
                  <ReceiptText
                    size={18}
                  />
                )}

                {savedDraft
                  ? "Draft saved"
                  : "Save as Draft"
                }
              </button>

              <button
                type="button"
                className={
                  styles.primaryButton
                }
                disabled={
                  busy ||
                  !selectedCustomer ||
                  cart.length === 0 ||
                  paidNow >
                    customerPayable ||
                  cart.some(
                    (item) =>
                      item.averageCost !== null &&
                      effectiveUnitPrice(
                        item,
                      ) <
                        item.averageCost,
                  )
                }
                onClick={() =>
                  void completeSale(
                    false,
                  )
                }
              >
                {busy ? (
                  <Loader2
                    size={19}
                    className={
                      styles.spin
                    }
                  />
                ) : (
                  <Check size={19} />
                )}

                {savedDraft
                  ? "Confirm saved draft"
                  : form.paymentMode ===
                    "installment"
                    ? "Confirm installment sale"
                    : "Confirm Sale"
                }
              </button>
            </div>

            <p className={styles.safeNote}>
              Save as Draft does not finalize stock or payment. Confirm Sale posts stock and all entered payments under backend business rules.
            </p>
          </div>

          {completed ? (
            <div className={styles.completedCard}>
              <div className={styles.completedIcon}>
                <Check size={25} />
              </div>

              <h3>
                Sale complete
              </h3>

              <p>
                {completed.invoice
                  .invoice_number ??
                  completed.confirmation
                    .invoice_number ??
                  `Invoice #${completed.invoice.id}`}
              </p>

              {completed.plan ? (
                <div className={styles.agreement}>
                  <span>
                    Installment agreement
                  </span>

                  <strong>
                    {
                      completed.plan
                        .agreement_number
                    }
                  </strong>

                  <small>
                    Outstanding{" "}
                    {money(
                      completed.plan
                        .outstanding_amount,
                    )}
                  </small>
                </div>
              ) : null}

              <button
                type="button"
                className={styles.documentButton}
                onClick={() =>
                  void downloadInvoicePdf(
                    completed.invoice.id,
                    completed.invoice
                      .invoice_number,
                  )
                }
              >
                <FileDown size={17} />
                Invoice PDF
              </button>

              {completed.confirmation
                .payment_id ? (
                <button
                  type="button"
                  className={styles.documentButton}
                  onClick={() =>
                    void downloadReceiptPdf(
                      Number(
                        completed
                          .confirmation
                          .payment_id,
                      ),
                      completed
                        .confirmation
                        .receipt_number ??
                        undefined,
                    )
                  }
                >
                  <ReceiptText
                    size={17}
                  />
                  Payment receipt
                </button>
              ) : null}

              {ledger ? (
                <div className={styles.postSaleInfo}>
                  <span>
                    Ledger balance
                  </span>

                  <strong>
                    {money(
                      ledger.closing_balance,
                    )}
                  </strong>
                </div>
              ) : null}

              {statement ? (
                <div className={styles.postSaleInfo}>
                  <span>
                    Statement entries
                  </span>

                  <strong>
                    {
                      statement.entries
                        .length
                    }
                  </strong>
                </div>
              ) : null}

              <button
                type="button"
                className={styles.newSaleButton}
                onClick={newSale}
              >
                <Plus size={17} />
                Start next sale
              </button>
            </div>
          ) : null}
        </aside>
      </div>

      {showCustomerForm ? (
        <div className={styles.modalBackdrop}>
          <div className={styles.modal}>
            <div className={styles.modalHeader}>
              <div>
                <span className={styles.eyebrow}>
                  Quick registration
                </span>

                <h2>
                  New customer
                </h2>
              </div>

              <button
                type="button"
                className={styles.iconButton}
                onClick={() =>
                  setShowCustomerForm(
                    false,
                  )
                }
              >
                <X size={19} />
              </button>
            </div>

            <div className={styles.modalGrid}>
              <label>
                <span>
                  Full name *
                </span>

                <input
                  autoFocus
                  value={
                    customerForm.fullName
                  }
                  onChange={(event) =>
                    setCustomerForm(
                      (
                        current,
                      ) => ({
                        ...current,
                        fullName:
                          event.target
                            .value,
                      }),
                    )
                  }
                />
              </label>

              <label>
                <span>
                  Phone *
                </span>

                <input
                  value={
                    customerForm.phone
                  }
                  onChange={(event) =>
                    setCustomerForm(
                      (
                        current,
                      ) => ({
                        ...current,
                        phone:
                          event.target
                            .value,
                      }),
                    )
                  }
                />
              </label>

              <label>
                <span>
                  NIC
                </span>

                <input
                  value={
                    customerForm.nic
                  }
                  onChange={(event) =>
                    setCustomerForm(
                      (
                        current,
                      ) => ({
                        ...current,
                        nic:
                          event.target
                            .value,
                      }),
                    )
                  }
                />
              </label>

              <label>
                <span>
                  City
                </span>

                <input
                  value={
                    customerForm.city
                  }
                  onChange={(event) =>
                    setCustomerForm(
                      (
                        current,
                      ) => ({
                        ...current,
                        city:
                          event.target
                            .value,
                      }),
                    )
                  }
                />
              </label>

              <label className={styles.fullField}>
                <span>
                  Address
                </span>

                <input
                  value={
                    customerForm.address
                  }
                  onChange={(event) =>
                    setCustomerForm(
                      (
                        current,
                      ) => ({
                        ...current,
                        address:
                          event.target
                            .value,
                      }),
                    )
                  }
                />
              </label>

              <label className={styles.checkbox}>
                <input
                  type="checkbox"
                  checked={
                    customerForm.smsAllowed
                  }
                  onChange={(event) =>
                    setCustomerForm(
                      (
                        current,
                      ) => ({
                        ...current,
                        smsAllowed:
                          event.target
                            .checked,
                      }),
                    )
                  }
                />

                <span>
                  Customer allows SMS
                  notifications
                </span>
              </label>
            </div>

            <div className={styles.modalActions}>
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() =>
                  setShowCustomerForm(
                    false,
                  )
                }
              >
                Cancel
              </button>

              <button
                type="button"
                className={styles.primaryButton}
                disabled={busy}
                onClick={() =>
                  void registerCustomer()
                }
              >
                {busy ? (
                  <Loader2
                    size={18}
                    className={styles.spin}
                  />
                ) : (
                  <UserPlus size={18} />
                )}

                Register & use customer
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {serialPicker ? (
        <div className={styles.modalBackdrop}>
          <div className={styles.modal}>
            <div className={styles.modalHeader}>
              <div>
                <span className={styles.eyebrow}>
                  Serialized product
                </span>

                <h2>
                  Select serial number
                </h2>

                <p>
                  {productName(
                    serialPicker.product,
                  )}
                </p>
              </div>

              <button
                type="button"
                className={styles.iconButton}
                onClick={() =>
                  setSerialPicker(
                    null,
                  )
                }
              >
                <X size={19} />
              </button>
            </div>

            <div className={styles.serialList}>
              {serialPicker.serials
                .length > 0 ? (
                serialPicker.serials.map(
                  (serial) => (
                    <button
                      type="button"
                      key={serial.id}
                      onClick={() =>
                        addCartItem(
                          serialPicker.product,
                          serial,
                        )
                      }
                    >
                      <span>
                        <strong>
                          {serial.serial_number ??
                            `Serial #${serial.id}`}
                        </strong>

                        <small>
                          {serial.secondary_serial_number ??
                            "Available"}
                        </small>
                      </span>

                      <ArrowRight
                        size={17}
                      />
                    </button>
                  ),
                )
              ) : (
                <div className={styles.emptyCart}>
                  <PackageSearch
                    size={30}
                  />
                  <strong>
                    No available serials
                  </strong>
                  <span>
                    Check inventory before
                    adding this product.
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
