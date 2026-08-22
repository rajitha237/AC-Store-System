"use client";

import axios from "axios";

import {
  ArrowLeft,
  BadgeDollarSign,
  Banknote,
  Boxes,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Eye,
  FileText,
  PackagePlus,
  Plus,
  RefreshCw,
  Search,
  ShoppingCart,
  Trash2,
  UserRound,
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
  confirmSalesInvoice,
  createSalesInvoice,
  getAvailableSalesSerials,
  getSalesCustomers,
  getSalesInvoice,
  getSalesInvoices,
  getSalesProducts,
  getSalesWarehouses,
} from "@/lib/sales-api";

import type {
  UserResponse,
} from "@/types/auth";

import type {
  InitialPaymentCreate,
  PaymentMethod,
  SalesCustomerOption,
  SalesDraftLine,
  SalesInvoiceDetailResponse,
  SalesInvoiceListResponse,
  SalesInvoiceResponse,
  SalesProductOption,
  SalesSerialOption,
  SalesWarehouseOption,
} from "@/types/sales";

import styles from "./sales.module.css";


const PAGE_SIZE = 20;


const emptyInvoiceList:
  SalesInvoiceListResponse = {
    items: [],
    total: 0,
    page: 1,
    page_size: PAGE_SIZE,
    total_pages: 0,
  };


function makeLine():
SalesDraftLine {
  return {
    key:
      `${Date.now()}-${Math.random()}`,

    productId: "",
    warehouseId: "",
    serialNumberId: "",

    quantity:
      "1.000",

    unitPrice:
      "0.00",

    discountAmount:
      "0.00",

    description:
      "",
  };
}


function numeric(
  value:
    | string
    | number
    | null
    | undefined,
): number {
  const parsed =
    Number(value);

  return (
    Number.isFinite(parsed)
      ? parsed
      : 0
  );
}


function money(
  value:
    | string
    | number
    | null
    | undefined,
): string {
  return new Intl.NumberFormat(
    "en-LK",
    {
      style: "currency",
      currency: "LKR",
      minimumFractionDigits: 2,
    },
  ).format(
    numeric(value),
  );
}


function quantityLabel(
  value:
    | string
    | number,
): string {
  return new Intl.NumberFormat(
    "en-LK",
    {
      maximumFractionDigits: 3,
    },
  ).format(
    numeric(value),
  );
}


function formatDate(
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
      dateStyle:
        "medium",

      timeStyle:
        "short",
    },
  ).format(date);
}


function cleanText(
  value: string,
): string | null {
  const clean =
    value.trim();

  return (
    clean.length > 0
      ? clean
      : null
  );
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
      + "to manage sales."
    );
  }

  return (
    "Unable to complete "
    + "the sales operation."
  );
}


function statusText(
  value: string,
): string {
  return value
    .split("_")
    .map(
      (part) =>
        part.charAt(0)
          .toUpperCase()
        + part.slice(1),
    )
    .join(" ");
}


export default function SalesPage() {
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
    invoices,
    setInvoices,
  ] =
    useState<
      SalesInvoiceListResponse
    >(
      emptyInvoiceList,
    );

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
    invoiceStatus,
    setInvoiceStatus,
  ] =
    useState("");

  const [
    paymentStatus,
    setPaymentStatus,
  ] =
    useState("");


  const [
    newSaleOpen,
    setNewSaleOpen,
  ] =
    useState(false);

  const [
    customers,
    setCustomers,
  ] =
    useState<
      SalesCustomerOption[]
    >(
      [],
    );

  const [
    products,
    setProducts,
  ] =
    useState<
      SalesProductOption[]
    >(
      [],
    );

  const [
    warehouses,
    setWarehouses,
  ] =
    useState<
      SalesWarehouseOption[]
    >(
      [],
    );

  const [
    loadingReferenceData,
    setLoadingReferenceData,
  ] =
    useState(false);

  const [
    customerId,
    setCustomerId,
  ] =
    useState("");


  const [
    saleCustomerSearch,
    setSaleCustomerSearch,
  ] =
    useState("");

  const [
    saleCustomerSearchOpen,
    setSaleCustomerSearchOpen,
  ] =
    useState(false);

  const [
    saleProductSearch,
    setSaleProductSearch,
  ] =
    useState<
      Record<string, string>
    >({});

  const [
    saleProductSearchOpenKey,
    setSaleProductSearchOpenKey,
  ] =
    useState<string | null>(
      null,
    );

  const [
    lines,
    setLines,
  ] =
    useState<
      SalesDraftLine[]
    >([
      makeLine(),
    ]);

  const [
    invoiceDiscount,
    setInvoiceDiscount,
  ] =
    useState("0.00");

  const [
    taxAmount,
    setTaxAmount,
  ] =
    useState("0.00");

  const [
    notes,
    setNotes,
  ] =
    useState("");

  const [
    salesTradeInEnabled,
    setSalesTradeInEnabled,
  ] =
    useState(false);

  const [
    salesTradeIn,
    setSalesTradeIn,
  ] =
    useState({
      brand: "",
      model: "",
      serialNumber: "",
      condition: "Used",
      description: "",
      allowance: "",
    });


  const [
    saving,
    setSaving,
  ] =
    useState(false);

  const [
    confirming,
    setConfirming,
  ] =
    useState(false);

  const [
    createdDraft,
    setCreatedDraft,
  ] =
    useState<
      SalesInvoiceResponse | null
    >(
      null,
    );


  const [
    initialPaymentEnabled,
    setInitialPaymentEnabled,
  ] =
    useState(false);

  const [
    initialPaymentAmount,
    setInitialPaymentAmount,
  ] =
    useState("");

  const [
    initialPaymentMethod,
    setInitialPaymentMethod,
  ] =
    useState<PaymentMethod>(
      "cash",
    );

  const [
    paymentReference,
    setPaymentReference,
  ] =
    useState("");

  const [
    paymentNotes,
    setPaymentNotes,
  ] =
    useState("");


  const [
    serialOptions,
    setSerialOptions,
  ] =
    useState<
      Record<
        string,
        SalesSerialOption[]
      >
    >({});

  const [
    serialLoadingKey,
    setSerialLoadingKey,
  ] =
    useState<
      string | null
    >(
      null,
    );


  const [
    detailOpen,
    setDetailOpen,
  ] =
    useState(false);

  const [
    detailLoading,
    setDetailLoading,
  ] =
    useState(false);

  const [
    selectedInvoice,
    setSelectedInvoice,
  ] =
    useState<
      SalesInvoiceDetailResponse
      | null
    >(
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


  const loadInvoices =
    useCallback(
      async (
        showRefresh = false,
      ) => {
        if (showRefresh) {
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
          const response =
            await getSalesInvoices({
              page,
              pageSize:
                PAGE_SIZE,
              search,
              invoiceStatus,
              paymentStatus,
            });

          setInvoices(
            response,
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
        invoiceStatus,
        paymentStatus,
      ],
    );


  useEffect(() => {
    if (authLoading) {
      return;
    }

    const timer =
      window.setTimeout(
        () => {
          void loadInvoices();
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
    loadInvoices,
  ]);


  const summary =
    useMemo(
      () => {
        const totalValue =
          invoices.items.reduce(
            (
              total,
              invoice,
            ) =>
              total
              + numeric(
                  invoice.grand_total,
                ),
            0,
          );

        const balance =
          invoices.items.reduce(
            (
              total,
              invoice,
            ) =>
              total
              + numeric(
                  invoice.balance_amount,
                ),
            0,
          );

        const confirmed =
          invoices.items.filter(
            (invoice) =>
              invoice.invoice_status
              === "confirmed",
          ).length;

        return {
          totalValue,
          balance,
          confirmed,
        };
      },
      [invoices.items],
    );


  const calculatedSubtotal =
    useMemo(
      () =>
        lines.reduce(
          (
            total,
            line,
          ) => {
            const quantity =
              numeric(
                line.quantity,
              );

            const price =
              numeric(
                line.unitPrice,
              );

            const discount =
              numeric(
                line.discountAmount,
              );

            return (
              total
              + Math.max(
                  0,
                  quantity
                  * price
                  - discount,
                )
            );
          },
          0,
        ),
      [lines],
    );


  const calculatedGrandTotal =
    useMemo(
      () =>
        Math.max(
          0,
          calculatedSubtotal
          - numeric(
              invoiceDiscount,
            )
          + numeric(
              taxAmount,
            ),
        ),
      [
        calculatedSubtotal,
        invoiceDiscount,
        taxAmount,
      ],
    );


  const calculatedTradeInAmount =
    salesTradeInEnabled
      ? Math.max(
          0,
          numeric(
            salesTradeIn.allowance,
          ),
        )
      : 0;


  const calculatedCustomerPayable =
    Math.max(
      0,
      calculatedGrandTotal
      - calculatedTradeInAmount,
    );


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
        .slice(
          0,
          100,
        ),
    );
  }


  function clearFilters() {
    setSearchInput("");
    setSearch("");
    setInvoiceStatus("");
    setPaymentStatus("");
    setPage(1);
  }


  async function searchSaleCustomers(
    query: string,
  ) {
    try {
      const result =
        await getSalesCustomers(
          query,
        );

      setCustomers(
        result,
      );
    } catch (
      requestError
    ) {
      console.error(
        "Sales customer search failed",
        requestError,
      );
    }
  }


  async function searchSaleProducts(
    query: string,
  ) {
    try {
      const result =
        await getSalesProducts(
          query,
        );

      setProducts(
        result,
      );
    } catch (
      requestError
    ) {
      console.error(
        "Sales product search failed",
        requestError,
      );
    }
  }


  async function loadReferenceData() {
    setLoadingReferenceData(
      true,
    );

    setError("");

    try {
      const [
        customerData,
        productData,
        warehouseData,
      ] =
        await Promise.all([
          getSalesCustomers(),
          getSalesProducts(),
          getSalesWarehouses(),
        ]);

      setCustomers(
        customerData,
      );

      setProducts(
        productData,
      );

      setWarehouses(
        warehouseData,
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
      setLoadingReferenceData(
        false,
      );
    }
  }


  async function openNewSale() {
    setError("");

    try {
      await loadReferenceData();
    } catch {
      return;
    }

    setCustomerId("");

    setSaleCustomerSearch(
      "",
    );

    setSaleCustomerSearchOpen(
      false,
    );

    setSaleProductSearch(
      {},
    );

    setSaleProductSearchOpenKey(
      null,
    );

    setLines([
      makeLine(),
    ]);

    setInvoiceDiscount(
      "0.00",
    );

    setTaxAmount(
      "0.00",
    );

    setNotes("");

    setSalesTradeInEnabled(
      false,
    );

    setSalesTradeIn({
      brand: "",
      model: "",
      serialNumber: "",
      condition: "Used",
      description: "",
      allowance: "",
    });

    setCreatedDraft(
      null,
    );

    setConfirming(
      false,
    );

    setInitialPaymentEnabled(
      false,
    );

    setInitialPaymentAmount(
      "",
    );

    setInitialPaymentMethod(
      "cash",
    );

    setPaymentReference(
      "",
    );

    setPaymentNotes(
      "",
    );

    setSerialOptions(
      {},
    );

    setNewSaleOpen(
      true,
    );
  }


  function closeNewSale() {
    if (saving) {
      return;
    }

    setNewSaleOpen(
      false,
    );

    setCreatedDraft(
      null,
    );

    setConfirming(
      false,
    );

    setError(
      "",
    );
  }


  function addLine() {
    setLines(
      (current) => [
        ...current,
        makeLine(),
      ],
    );
  }


  function removeLine(
    key: string,
  ) {
    setLines(
      (current) => {
        if (
          current.length <= 1
        ) {
          return current;
        }

        return current.filter(
          (line) =>
            line.key !== key,
        );
      },
    );

    setSerialOptions(
      (current) => {
        const next = {
          ...current,
        };

        delete next[key];

        return next;
      },
    );
  }


  function updateLine(
    key: string,
    update:
      Partial<SalesDraftLine>,
  ) {
    setLines(
      (current) =>
        current.map(
          (line) =>
            line.key === key
              ? {
                  ...line,
                  ...update,
                }
              : line,
        ),
    );

    setCreatedDraft(
      null,
    );

    setConfirming(
      false,
    );
  }


  async function refreshSerials(
    line:
      SalesDraftLine,
    productId:
      string,
    warehouseId:
      string,
  ) {
    const product =
      products.find(
        (item) =>
          String(
            item.id,
          )
          === productId,
      );

    if (
      !product
      || !product
        .track_serial_numbers
      || !productId
      || !warehouseId
    ) {
      setSerialOptions(
        (current) => ({
          ...current,
          [line.key]: [],
        }),
      );

      return;
    }

    setSerialLoadingKey(
      line.key,
    );

    try {
      const serials =
        await getAvailableSalesSerials(
          Number(
            productId,
          ),
          Number(
            warehouseId,
          ),
        );

      setSerialOptions(
        (current) => ({
          ...current,
          [line.key]:
            serials,
        }),
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
      setSerialLoadingKey(
        null,
      );
    }
  }


  async function changeProduct(
    line:
      SalesDraftLine,
    productId:
      string,
  ) {
    const product =
      products.find(
        (item) =>
          String(
            item.id,
          )
          === productId,
      );

    updateLine(
      line.key,
      {
        productId,

        serialNumberId:
          "",

        quantity:
          product
            ?.track_serial_numbers
            ? "1.000"
            : line.quantity,

        unitPrice:
          product
            ? String(
                product.selling_price,
              )
            : "0.00",
      },
    );

    await refreshSerials(
      line,
      productId,
      line.warehouseId,
    );
  }


  async function changeWarehouse(
    line:
      SalesDraftLine,
    warehouseId:
      string,
  ) {
    updateLine(
      line.key,
      {
        warehouseId,

        serialNumberId:
          "",
      },
    );

    await refreshSerials(
      line,
      line.productId,
      warehouseId,
    );
  }


  function validateSale():
    string | null {
    if (!customerId) {
      return (
        "Select a customer."
      );
    }

    if (
      lines.length === 0
    ) {
      return (
        "Add at least one "
        + "sales item."
      );
    }

    for (
      let index = 0;
      index < lines.length;
      index += 1
    ) {
      const line =
        lines[index];

      const row =
        index + 1;

      if (
        !line.productId
      ) {
        return (
          `Select a product on row ${row}.`
        );
      }

      if (
        !line.warehouseId
      ) {
        return (
          `Select a warehouse on row ${row}.`
        );
      }

      const product =
        products.find(
          (item) =>
            String(
              item.id,
            )
            === line.productId,
        );

      if (
        product
        ?.track_serial_numbers
      ) {
        if (
          !line.serialNumberId
        ) {
          return (
            `Select a serial number on row ${row}.`
          );
        }
      } else {
        if (
          numeric(
            line.quantity,
          ) <= 0
        ) {
          return (
            `Quantity must be greater than zero on row ${row}.`
          );
        }
      }

      if (
        numeric(
          line.unitPrice,
        ) < 0
      ) {
        return (
          `Unit price cannot be negative on row ${row}.`
        );
      }

      const lineGross =
        numeric(
          line.quantity,
        )
        * numeric(
            line.unitPrice,
          );

      if (
        numeric(
          line.discountAmount,
        )
        > lineGross
      ) {
        return (
          `Discount is greater than line value on row ${row}.`
        );
      }
    }

    if (
      numeric(
        invoiceDiscount,
      )
      > calculatedSubtotal
    ) {
      return (
        "Invoice discount cannot "
        + "exceed the subtotal."
      );
    }

    if (
      salesTradeInEnabled
      && calculatedTradeInAmount <= 0
    ) {
      return (
        "Enter a valid trade-in allowance."
      );
    }

    if (
      salesTradeInEnabled
      && calculatedTradeInAmount
      > calculatedCustomerPayable
    ) {
      return (
        "Trade-in allowance cannot exceed the invoice total."
      );
    }

    if (
      salesTradeInEnabled
      && !(
        salesTradeIn.brand.trim()
        || salesTradeIn.model.trim()
        || salesTradeIn.serialNumber.trim()
        || salesTradeIn.description.trim()
      )
    ) {
      return (
        "Enter brand, model, serial number or description for the trade-in unit."
      );
    }


    if (
      initialPaymentEnabled
      && initialPaymentAmount
      && numeric(
        initialPaymentAmount,
      )
      > calculatedGrandTotal
    ) {
      return (
        "Initial payment cannot "
        + "exceed the customer payable balance."
      );
    }

    return null;
  }


  async function createDraft() {
    const validation =
      validateSale();

    if (validation) {
      setError(
        validation,
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
      const created =
        await createSalesInvoice({
          customer_id:
            Number(
              customerId,
            ),

          invoice_discount_amount:
            invoiceDiscount
            || "0.00",

          tax_amount:
            taxAmount
            || "0.00",

          notes:
            cleanText(
              notes,
            ),

          trade_ins:
            salesTradeInEnabled
              ? [
                  {
                    brand:
                      cleanText(
                        salesTradeIn.brand,
                      ),
                    model:
                      cleanText(
                        salesTradeIn.model,
                      ),
                    serial_number:
                      cleanText(
                        salesTradeIn.serialNumber,
                      ),
                    condition:
                      cleanText(
                        salesTradeIn.condition,
                      ),
                    description:
                      cleanText(
                        salesTradeIn.description,
                      ),
                    allowance_amount:
                      salesTradeIn.allowance
                      || "0.00",
                  },
                ]
              : [],

          items:
            lines.map(
              (line) => {
                const product =
                  products.find(
                    (item) =>
                      String(
                        item.id,
                      )
                      === line
                        .productId,
                  );

                return {
                  product_id:
                    Number(
                      line.productId,
                    ),

                  warehouse_id:
                    Number(
                      line.warehouseId,
                    ),

                  serial_number_id:
                    line.serialNumberId
                      ? Number(
                          line.serialNumberId,
                        )
                      : null,

                  quantity:
                    product
                      ?.track_serial_numbers
                      ? "1.000"
                      : line.quantity,

                  unit_price:
                    line.unitPrice,

                  discount_amount:
                    line.discountAmount
                    || "0.00",

                  description:
                    cleanText(
                      line.description,
                    ),
                };
              },
            ),
        });

      setCreatedDraft(
        created,
      );

      setConfirming(
        true,
      );

      if (
        initialPaymentEnabled
        && !initialPaymentAmount
      ) {
        setInitialPaymentAmount(
          created.balance_amount,
        );
      }
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


  async function confirmDraft() {
    if (
      !createdDraft
    ) {
      return;
    }

    let initialPayment:
      InitialPaymentCreate
      | null = null;

    if (
      initialPaymentEnabled
    ) {
      const amount =
        numeric(
          initialPaymentAmount,
        );

      if (amount <= 0) {
        setError(
          "Initial payment amount "
          + "must be greater than zero.",
        );

        return;
      }

      if (
        amount
        > numeric(
            createdDraft
              .balance_amount,
          )
      ) {
        setError(
          "Initial payment cannot "
          + "exceed the invoice total.",
        );

        return;
      }

      initialPayment = {
        amount:
          initialPaymentAmount,

        payment_method:
          initialPaymentMethod,

        reference_number:
          cleanText(
            paymentReference,
          ),

        notes:
          cleanText(
            paymentNotes,
          ),
      };
    }

    setSaving(
      true,
    );

    setError(
      "",
    );

    try {
      const confirmed =
        await confirmSalesInvoice(
          createdDraft.id,
          {
            initial_payment:
              initialPayment,
          },
        );

      setCreatedDraft(
        confirmed,
      );

      await loadInvoices(
        true,
      );

      setNewSaleOpen(
        false,
      );

      setConfirming(
        false,
      );

      setCreatedDraft(
        null,
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
      setSaving(
        false,
      );
    }
  }


  async function openDetail(
    invoiceId: number,
  ) {
    setDetailOpen(
      true,
    );

    setDetailLoading(
      true,
    );

    setSelectedInvoice(
      null,
    );

    setError(
      "",
    );

    try {
      const detail =
        await getSalesInvoice(
          invoiceId,
        );

      setSelectedInvoice(
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
            SALES
          </p>

          <h1>
            Sales & invoices
          </h1>

          <p>
            Create sales invoices,
            assign stock and serial
            numbers, confirm sales and
            monitor customer balances.
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
              styles.primaryButton
            }
            disabled={
              loadingReferenceData
            }
            onClick={() =>
              void openNewSale()
            }
          >
            <Plus size={17} />

            New sale
          </button>

          <button
            type="button"
            className={
              styles.secondaryButton
            }
            disabled={
              refreshing
            }
            onClick={() =>
              void loadInvoices(
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

            {refreshing
              ? "Refreshing..."
              : "Refresh"
            }
          </button>
        </div>
      </section>


      <section
        className={
          styles.summaryGrid
        }
      >
        <article>
          <div
            className={
              styles.summaryIcon
            }
          >
            <FileText
              size={19}
            />
          </div>

          <div>
            <span>
              Invoices
            </span>

            <strong>
              {invoices.total}
            </strong>
          </div>
        </article>

        <article>
          <div
            className={
              styles.summaryIcon
            }
          >
            <Check
              size={19}
            />
          </div>

          <div>
            <span>
              Confirmed
            </span>

            <strong>
              {summary.confirmed}
            </strong>
          </div>
        </article>

        <article>
          <div
            className={
              styles.summaryIcon
            }
          >
            <BadgeDollarSign
              size={19}
            />
          </div>

          <div>
            <span>
              Page sales
            </span>

            <strong>
              {money(
                summary.totalValue,
              )}
            </strong>
          </div>
        </article>

        <article>
          <div
            className={
              styles.summaryIcon
            }
          >
            <Banknote
              size={19}
            />
          </div>

          <div>
            <span>
              Outstanding
            </span>

            <strong>
              {money(
                summary.balance,
              )}
            </strong>
          </div>
        </article>
      </section>


      <section
        className={
          styles.filterCard
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
            type="search"
            value={
              searchInput
            }
            placeholder={
              "Invoice number or customer..."
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

          <button
            type="submit"
          >
            Search
          </button>
        </form>

        <select
          value={
            invoiceStatus
          }
          onChange={
            (event) => {
              setPage(1);

              setInvoiceStatus(
                event.target.value,
              );
            }
          }
        >
          <option value="">
            All invoice statuses
          </option>

          <option value="draft">
            Draft
          </option>

          <option value="confirmed">
            Confirmed
          </option>

          <option value="cancelled">
            Cancelled
          </option>
        </select>

        <select
          value={
            paymentStatus
          }
          onChange={
            (event) => {
              setPage(1);

              setPaymentStatus(
                event.target.value,
              );
            }
          }
        >
          <option value="">
            All payment statuses
          </option>

          <option value="unpaid">
            Unpaid
          </option>

          <option value="partial">
            Partial
          </option>

          <option value="paid">
            Paid
          </option>
        </select>

        <button
          type="button"
          className={
            styles.clearButton
          }
          onClick={
            clearFilters
          }
        >
          Clear
        </button>
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
          styles.tableCard
        }
      >
        <div
          className={
            styles.tableHeader
          }
        >
          <div>
            <h2>
              Sales invoices
            </h2>

            <p>
              {invoices.total}
              {" total invoices"}
            </p>
          </div>
        </div>

        {loading ? (
          <div
            className={
              styles.emptyState
            }
          >
            <div
              className="loading-spinner"
            />

            Loading sales...
          </div>
        ) : invoices.items.length
          === 0 ? (
          <div
            className={
              styles.emptyState
            }
          >
            <ShoppingCart
              size={28}
            />

            <strong>
              No sales invoices
            </strong>

            <span>
              Create the first sale
              or change the filters.
            </span>
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
                    Invoice
                  </th>

                  <th>
                    Date
                  </th>

                  <th>
                    Customer
                  </th>

                  <th>
                    Total
                  </th>

                  <th>
                    Paid
                  </th>

                  <th>
                    Balance
                  </th>

                  <th>
                    Invoice status
                  </th>

                  <th>
                    Payment
                  </th>

                  <th />
                </tr>
              </thead>

              <tbody>
                {invoices.items.map(
                  (invoice) => (
                    <tr
                      key={
                        invoice.id
                      }
                    >
                      <td>
                        <strong>
                          {
                            invoice
                              .invoice_number
                          }
                        </strong>
                      </td>

                      <td>
                        {formatDate(
                          invoice
                            .invoice_date,
                        )}
                      </td>

                      <td>
                        Customer #
                        {
                          invoice
                            .customer_id
                        }
                      </td>

                      <td>
                        {money(
                          invoice
                            .grand_total,
                        )}
                      </td>

                      <td>
                        {money(
                          invoice
                            .paid_amount,
                        )}
                      </td>

                      <td>
                        <strong>
                          {money(
                            invoice
                              .balance_amount,
                          )}
                        </strong>
                      </td>

                      <td>
                        <span
                          className={
                            styles.statusBadge
                          }
                        >
                          {statusText(
                            invoice
                              .invoice_status,
                          )}
                        </span>
                      </td>

                      <td>
                        <span
                          className={
                            invoice
                              .payment_status
                            === "paid"
                              ? styles
                                  .paidBadge
                              : styles
                                  .paymentBadge
                          }
                        >
                          {statusText(
                            invoice
                              .payment_status,
                          )}
                        </span>
                      </td>

                      <td>
                        <button
                          type="button"
                          className={
                            styles.iconButton
                          }
                          aria-label={
                            "View invoice"
                          }
                          onClick={() =>
                            void openDetail(
                              invoice.id,
                            )
                          }
                        >
                          <Eye
                            size={16}
                          />
                        </button>
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        )}

        <div
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
            Page {invoices.page}
            {" of "}
            {Math.max(
              1,
              invoices.total_pages,
            )}
          </span>

          <button
            type="button"
            disabled={
              page
              >= invoices.total_pages
              || invoices
                .total_pages === 0
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
        </div>
      </section>


      {newSaleOpen && (
        <div
          className={
            styles.modalBackdrop
          }
        >
          <section
            className={
              styles.saleModal
            }
            role="dialog"
            aria-modal="true"
            aria-labelledby={
              "new-sale-title"
            }
          >
            <header
              className={
                styles.modalHeader
              }
            >
              <div>
                <p className="eyebrow">
                  NEW SALE
                </p>

                <h2
                  id="new-sale-title"
                >
                  {confirming
                    ? "Review & confirm invoice"
                    : "Create sales invoice"
                  }
                </h2>

                <p>
                  {confirming
                    ? "The draft is created. Confirming the invoice posts the sale and stock transaction."
                    : "Select customer, warehouse stock and products for this invoice."
                  }
                </p>
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
                  closeNewSale
                }
              >
                <X size={18} />
              </button>
            </header>


            {!confirming ? (
              <>
                <div
                  className={
                    styles.modalBody
                  }
                >
                  <section
                    className={
                      styles.formSection
                    }
                  >
                    <h3>
                      Customer
                    </h3>

                    <label
                      className={
                        styles.fullField
                      }
                    >
                      Customer *

                      <div
                        className={
                          styles.searchableSelect
                        }
                      >
                        <input
                          required
                          type="text"
                          autoComplete="off"
                          placeholder="Search customer name, code, phone or NIC..."
                          value={
                            saleCustomerSearchOpen
                              ? saleCustomerSearch
                              : (
                                  customers.find(
                                    (customer) =>
                                      String(
                                        customer.id,
                                      )
                                      === customerId,
                                  )
                                    ? `${
                                        customers.find(
                                          (customer) =>
                                            String(
                                              customer.id,
                                            )
                                            === customerId,
                                        )?.customer_code
                                        ?? `#${customerId}`
                                      } — ${
                                        customers.find(
                                          (customer) =>
                                            String(
                                              customer.id,
                                            )
                                            === customerId,
                                        )?.full_name
                                        ?? ""
                                      }`
                                    : ""
                                )
                          }
                          onFocus={() => {
                            setSaleCustomerSearch(
                              "",
                            );

                            setSaleCustomerSearchOpen(
                              true,
                            );

                            void searchSaleCustomers(
                              "",
                            );
                          }}
                          onChange={(event) => {
                            const value =
                              event.target.value;

                            setSaleCustomerSearch(
                              value,
                            );

                            setSaleCustomerSearchOpen(
                              true,
                            );

                            void searchSaleCustomers(
                              value,
                            );

                            if (
                              customerId
                            ) {
                              setCustomerId(
                                "",
                              );
                            }
                          }}
                          onBlur={() => {
                            window.setTimeout(
                              () => {
                                setSaleCustomerSearchOpen(
                                  false,
                                );
                              },
                              150,
                            );
                          }}
                        />

                        {saleCustomerSearchOpen && (
                          <div
                            className={
                              styles.searchableMenu
                            }
                          >
                            {customers.length > 0 ? (
                              customers.map(
                                (customer) => (
                                  <button
                                    key={
                                      customer.id
                                    }
                                    type="button"
                                    className={
                                      styles.searchableOption
                                    }
                                    onMouseDown={(
                                      event,
                                    ) => {
                                      event.preventDefault();

                                      setCustomerId(
                                        String(
                                          customer.id,
                                        ),
                                      );

                                      setSaleCustomerSearch(
                                        `${
                                          customer.customer_code
                                          ?? `#${customer.id}`
                                        } — ${
                                          customer.full_name
                                        }`,
                                      );

                                      setSaleCustomerSearchOpen(
                                        false,
                                      );
                                    }}
                                  >
                                    <strong>
                                      {
                                        customer.customer_code
                                        ?? `#${customer.id}`
                                      }
                                      {" — "}
                                      {
                                        customer.full_name
                                      }
                                    </strong>

                                    <span>
                                      {customer.phone
                                        || customer.mobile_number
                                        || customer.nic_number
                                        || "No phone / NIC"
                                      }
                                    </span>
                                  </button>
                                ),
                              )
                            ) : (
                              <div
                                className={
                                  styles.searchableEmpty
                                }
                              >
                                No customers found.
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </label>
                  </section>


                  <section
                    className={
                      styles.formSection
                    }
                  >
                    <div
                      className={
                        styles.sectionHeader
                      }
                    >
                      <div>
                        <h3>
                          Sale items
                        </h3>

                        <p>
                          Serialized products
                          require an available
                          serial number.
                        </p>
                      </div>

                      <button
                        type="button"
                        className={
                          styles.addLineButton
                        }
                        onClick={
                          addLine
                        }
                      >
                        <PackagePlus
                          size={15}
                        />

                        Add item
                      </button>
                    </div>

                    <div
                      className={
                        styles.lineList
                      }
                    >
                      {lines.map(
                        (
                          line,
                          index,
                        ) => {
                          const product =
                            products.find(
                              (item) =>
                                String(
                                  item.id,
                                )
                                === line
                                  .productId,
                            );

                          const serialized =
                            product
                              ?.track_serial_numbers
                            ?? false;

                          const lineTotal =
                            Math.max(
                              0,
                              numeric(
                                line.quantity,
                              )
                              * numeric(
                                  line.unitPrice,
                                )
                              - numeric(
                                  line
                                    .discountAmount,
                                ),
                            );

                          const availableSerials =
                            serialOptions[
                              line.key
                            ] ?? [];

                          return (
                            <article
                              key={
                                line.key
                              }
                              className={
                                styles.lineCard
                              }
                            >
                              <div
                                className={
                                  styles.lineNumber
                                }
                              >
                                {index + 1}
                              </div>

                              <div
                                className={
                                  styles.lineGrid
                                }
                              >
                                <label
                                  className={
                                    styles
                                      .productField
                                  }
                                >
                                  Product *

                                  <div
                                    className={
                                      styles.searchableSelect
                                    }
                                  >
                                    <input
                                      type="text"
                                      autoComplete="off"
                                      placeholder="Search product code or name..."
                                      value={
                                        saleProductSearchOpenKey
                                          === line.key
                                          ? (
                                              saleProductSearch[
                                                line.key
                                              ]
                                              ?? ""
                                            )
                                          : (
                                              products.find(
                                                (item) =>
                                                  String(
                                                    item.id,
                                                  )
                                                  === line.productId,
                                              )
                                                ? `${
                                                    products.find(
                                                      (item) =>
                                                        String(
                                                          item.id,
                                                        )
                                                        === line.productId,
                                                    )?.product_code
                                                    ?? ""
                                                  } — ${
                                                    products.find(
                                                      (item) =>
                                                        String(
                                                          item.id,
                                                        )
                                                        === line.productId,
                                                    )?.name
                                                    ?? ""
                                                  }`
                                                : ""
                                            )
                                      }
                                      onFocus={() => {
                                        setSaleProductSearch({
                                          ...saleProductSearch,
                                          [line.key]:
                                            "",
                                        });

                                        setSaleProductSearchOpenKey(
                                          line.key,
                                        );

                                        void searchSaleProducts(
                                          "",
                                        );
                                      }}
                                      onChange={(event) => {
                                        const value =
                                          event.target.value;

                                        setSaleProductSearch({
                                          ...saleProductSearch,
                                          [line.key]:
                                            value,
                                        });

                                        setSaleProductSearchOpenKey(
                                          line.key,
                                        );

                                        void searchSaleProducts(
                                          value,
                                        );

                                        if (
                                          line.productId
                                        ) {
                                          void changeProduct(
                                            line,
                                            "",
                                          );
                                        }
                                      }}
                                      onBlur={() => {
                                        window.setTimeout(
                                          () => {
                                            setSaleProductSearchOpenKey(
                                              (
                                                current
                                              ) =>
                                                current
                                                === line.key
                                                  ? null
                                                  : current,
                                            );
                                          },
                                          150,
                                        );
                                      }}
                                    />

                                    {saleProductSearchOpenKey
                                      === line.key && (
                                      <div
                                        className={
                                          styles.searchableMenu
                                        }
                                      >
                                        {products.length > 0 ? (
                                          products.map(
                                            (item) => (
                                              <button
                                                key={
                                                  item.id
                                                }
                                                type="button"
                                                className={
                                                  styles.searchableOption
                                                }
                                                onMouseDown={(
                                                  event,
                                                ) => {
                                                  event.preventDefault();

                                                  setSaleProductSearch({
                                                    ...saleProductSearch,
                                                    [line.key]:
                                                      `${
                                                        item.product_code
                                                      } — ${
                                                        item.name
                                                      }`,
                                                  });

                                                  setSaleProductSearchOpenKey(
                                                    null,
                                                  );

                                                  void changeProduct(
                                                    line,
                                                    String(
                                                      item.id,
                                                    ),
                                                  );
                                                }}
                                              >
                                                <strong>
                                                  {
                                                    item.product_code
                                                  }
                                                  {" — "}
                                                  {
                                                    item.name
                                                  }
                                                </strong>

                                                <span>
                                                  Price:{" "}
                                                  {
                                                    item.selling_price
                                                  }
                                                  {item.track_serial_numbers
                                                    ? " — Serialized"
                                                    : ""
                                                  }
                                                </span>
                                              </button>
                                            ),
                                          )
                                        ) : (
                                          <div
                                            className={
                                              styles.searchableEmpty
                                            }
                                          >
                                            No products found.
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                </label>


                                <label>
                                  Warehouse *

                                  <select
                                    value={
                                      line
                                        .warehouseId
                                    }
                                    onChange={
                                      (event) =>
                                        void changeWarehouse(
                                          line,
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
                                            warehouse
                                              .code
                                          }
                                          {" — "}
                                          {
                                            warehouse
                                              .name
                                          }
                                        </option>
                                      ),
                                    )}
                                  </select>
                                </label>


                                {serialized ? (
                                  <label>
                                    Serial number *

                                    <select
                                      value={
                                        line
                                          .serialNumberId
                                      }
                                      disabled={
                                        !line
                                          .warehouseId
                                        || serialLoadingKey
                                          === line.key
                                      }
                                      onChange={
                                        (event) =>
                                          updateLine(
                                            line.key,
                                            {
                                              serialNumberId:
                                                event
                                                  .target
                                                  .value,
                                            },
                                          )
                                      }
                                    >
                                      <option value="">
                                        {serialLoadingKey
                                          === line.key
                                          ? "Loading serials..."
                                          : "Select serial"
                                        }
                                      </option>

                                      {availableSerials.map(
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
                                  </label>
                                ) : (
                                  <label>
                                    Quantity *

                                    <input
                                      type="number"
                                      min="0.001"
                                      step="0.001"
                                      value={
                                        line
                                          .quantity
                                      }
                                      onChange={
                                        (event) =>
                                          updateLine(
                                            line.key,
                                            {
                                              quantity:
                                                event
                                                  .target
                                                  .value,
                                            },
                                          )
                                      }
                                    />
                                  </label>
                                )}


                                <label>
                                  Unit price *

                                  <input
                                    type="number"
                                    min="0"
                                    step="0.01"
                                    value={
                                      line
                                        .unitPrice
                                    }
                                    onChange={
                                      (event) =>
                                        updateLine(
                                          line.key,
                                          {
                                            unitPrice:
                                              event
                                                .target
                                                .value,
                                          },
                                        )
                                    }
                                  />
                                </label>


                                <label>
                                  Line discount

                                  <input
                                    type="number"
                                    min="0"
                                    step="0.01"
                                    value={
                                      line
                                        .discountAmount
                                    }
                                    onChange={
                                      (event) =>
                                        updateLine(
                                          line.key,
                                          {
                                            discountAmount:
                                              event
                                                .target
                                                .value,
                                          },
                                        )
                                    }
                                  />
                                </label>


                                <label
                                  className={
                                    styles
                                      .descriptionField
                                  }
                                >
                                  Description

                                  <input
                                    type="text"
                                    maxLength={500}
                                    value={
                                      line
                                        .description
                                    }
                                    onChange={
                                      (event) =>
                                        updateLine(
                                          line.key,
                                          {
                                            description:
                                              event
                                                .target
                                                .value,
                                          },
                                        )
                                    }
                                  />
                                </label>
                              </div>

                              <div
                                className={
                                  styles.lineTotal
                                }
                              >
                                <span>
                                  Line total
                                </span>

                                <strong>
                                  {money(
                                    lineTotal,
                                  )}
                                </strong>
                              </div>

                              <button
                                type="button"
                                className={
                                  styles
                                    .removeLineButton
                                }
                                disabled={
                                  lines.length
                                  <= 1
                                }
                                onClick={() =>
                                  removeLine(
                                    line.key,
                                  )
                                }
                              >
                                <Trash2
                                  size={15}
                                />
                              </button>
                            </article>
                          );
                        },
                      )}
                    </div>
                  </section>


                  <section
                    className={
                      styles.formSection
                    }
                  >
                    <div
                      className={
                        styles.tradeInHeader
                      }
                    >
                      <div>
                        <h3>
                          Trade-in / Exchange
                        </h3>

                        <p>
                          Keep the old A/C allowance separate from normal sales discount.
                        </p>
                      </div>

                      <label
                        className={
                          styles.tradeInToggle
                        }
                      >
                        <input
                          type="checkbox"
                          checked={
                            salesTradeInEnabled
                          }
                          onChange={
                            (event) =>
                              setSalesTradeInEnabled(
                                event.target.checked,
                              )
                          }
                        />

                        Use trade-in
                      </label>
                    </div>

                    {salesTradeInEnabled && (
                      <div
                        className={
                          styles.totalsGrid
                        }
                      >
                        <label>
                          Brand

                          <input
                            value={
                              salesTradeIn.brand
                            }
                            onChange={
                              (event) =>
                                setSalesTradeIn({
                                  ...salesTradeIn,
                                  brand:
                                    event.target.value,
                                })
                            }
                          />
                        </label>

                        <label>
                          Model

                          <input
                            value={
                              salesTradeIn.model
                            }
                            onChange={
                              (event) =>
                                setSalesTradeIn({
                                  ...salesTradeIn,
                                  model:
                                    event.target.value,
                                })
                            }
                          />
                        </label>

                        <label>
                          Serial number

                          <input
                            value={
                              salesTradeIn
                                .serialNumber
                            }
                            onChange={
                              (event) =>
                                setSalesTradeIn({
                                  ...salesTradeIn,
                                  serialNumber:
                                    event.target.value,
                                })
                            }
                          />
                        </label>

                        <label>
                          Condition

                          <select
                            value={
                              salesTradeIn.condition
                            }
                            onChange={
                              (event) =>
                                setSalesTradeIn({
                                  ...salesTradeIn,
                                  condition:
                                    event.target.value,
                                })
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
                          Trade-in allowance

                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            value={
                              salesTradeIn.allowance
                            }
                            onChange={
                              (event) =>
                                setSalesTradeIn({
                                  ...salesTradeIn,
                                  allowance:
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
                          Old A/C details

                          <textarea
                            rows={2}
                            value={
                              salesTradeIn
                                .description
                            }
                            onChange={
                              (event) =>
                                setSalesTradeIn({
                                  ...salesTradeIn,
                                  description:
                                    event.target.value,
                                })
                            }
                          />
                        </label>
                      </div>
                    )}
                  </section>


                  <section
                    className={
                      styles.formSection
                    }
                  >
                    <h3>
                      Invoice totals
                    </h3>

                    <div
                      className={
                        styles.totalsGrid
                      }
                    >
                      <label>
                        Invoice discount

                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={
                            invoiceDiscount
                          }
                          onChange={
                            (event) =>
                              setInvoiceDiscount(
                                event
                                  .target
                                  .value,
                              )
                          }
                        />
                      </label>

                      <label>
                        Tax amount

                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={
                            taxAmount
                          }
                          onChange={
                            (event) =>
                              setTaxAmount(
                                event
                                  .target
                                  .value,
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
                          rows={3}
                          value={
                            notes
                          }
                          onChange={
                            (event) =>
                              setNotes(
                                event
                                  .target
                                  .value,
                              )
                          }
                        />
                      </label>
                    </div>

                    <div
                      className={
                        styles.totalSummary
                      }
                    >
                      <div>
                        <span>
                          Items subtotal
                        </span>

                        <strong>
                          {money(
                            calculatedSubtotal,
                          )}
                        </strong>
                      </div>

                      <div>
                        <span>
                          Invoice discount
                        </span>

                        <strong>
                          -
                          {money(
                            invoiceDiscount,
                          )}
                        </strong>
                      </div>

                      <div>
                        <span>
                          Tax
                        </span>

                        <strong>
                          {money(
                            taxAmount,
                          )}
                        </strong>
                      </div>

                      <div>
                        <span>
                          Sale total
                        </span>

                        <strong>
                          {money(
                            calculatedGrandTotal,
                          )}
                        </strong>
                      </div>

                      <div>
                        <span>
                          Trade-in allowance
                        </span>

                        <strong>
                          -{money(
                            calculatedTradeInAmount,
                          )}
                        </strong>
                      </div>

                      <div
                        className={
                          styles.grandTotal
                        }
                      >
                        <span>
                          Customer payable
                        </span>

                        <strong>
                          {money(
                            calculatedCustomerPayable,
                          )}
                        </strong>
                      </div>
                    </div>
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
                      closeNewSale
                    }
                  >
                    Cancel
                  </button>

                  <button
                    type="button"
                    className={
                      styles.primaryButton
                    }
                    disabled={
                      saving
                    }
                    onClick={() =>
                      void createDraft()
                    }
                  >
                    {saving
                      ? "Creating..."
                      : (
                        <>
                          Create draft

                          <ChevronRight
                            size={16}
                          />
                        </>
                      )
                    }
                  </button>
                </footer>
              </>
            ) : (
              <>
                <div
                  className={
                    styles.modalBody
                  }
                >
                  {createdDraft && (
                    <>
                      <section
                        className={
                          styles.reviewHero
                        }
                      >
                        <div
                          className={
                            styles.reviewIcon
                          }
                        >
                          <FileText
                            size={22}
                          />
                        </div>

                        <div>
                          <span>
                            Draft invoice
                          </span>

                          <h3>
                            {
                              createdDraft
                                .invoice_number
                            }
                          </h3>

                          <p>
                            Review the final
                            amount before
                            confirmation.
                          </p>
                        </div>

                        <strong>
                          {money(
                            createdDraft
                              .grand_total,
                          )}
                        </strong>
                      </section>

                      <section
                        className={
                          styles.reviewStats
                        }
                      >
                        <div>
                          <span>
                            Items
                          </span>

                          <strong>
                            {
                              createdDraft
                                .items.length
                            }
                          </strong>
                        </div>

                        <div>
                          <span>
                            Subtotal
                          </span>

                          <strong>
                            {money(
                              createdDraft
                                .subtotal,
                            )}
                          </strong>
                        </div>

                        <div>
                          <span>
                            Discount
                          </span>

                          <strong>
                            {money(
                              createdDraft
                                .discount_amount,
                            )}
                          </strong>
                        </div>

                        <div>
                          <span>
                            Balance after confirm
                          </span>

                          <strong>
                            {money(
                              initialPaymentEnabled
                                ? Math.max(
                                    0,
                                    numeric(
                                      createdDraft
                                        .balance_amount,
                                    )
                                    - numeric(
                                        initialPaymentAmount,
                                      ),
                                  )
                                : createdDraft
                                    .balance_amount,
                            )}
                          </strong>
                        </div>
                      </section>


                      <section
                        className={
                          styles.formSection
                        }
                      >
                        <label
                          className={
                            styles.paymentToggle
                          }
                        >
                          <input
                            type="checkbox"
                            checked={
                              initialPaymentEnabled
                            }
                            onChange={
                              (event) => {
                                const checked =
                                  event
                                    .target
                                    .checked;

                                setInitialPaymentEnabled(
                                  checked,
                                );

                                if (
                                  checked
                                  && !initialPaymentAmount
                                ) {
                                  setInitialPaymentAmount(
                                    createdDraft
                                      .balance_amount,
                                  );
                                }
                              }
                            }
                          />

                          <div>
                            <strong>
                              Receive initial payment
                            </strong>

                            <span>
                              Optional payment when
                              confirming this invoice.
                            </span>
                          </div>
                        </label>

                        {initialPaymentEnabled && (
                          <div
                            className={
                              styles.totalsGrid
                            }
                          >
                            <label>
                              Amount *

                              <input
                                type="number"
                                min="0.01"
                                step="0.01"
                                value={
                                  initialPaymentAmount
                                }
                                onChange={
                                  (event) =>
                                    setInitialPaymentAmount(
                                      event
                                        .target
                                        .value,
                                    )
                                }
                              />
                            </label>

                            <label>
                              Payment method

                              <select
                                value={
                                  initialPaymentMethod
                                }
                                onChange={
                                  (event) =>
                                    setInitialPaymentMethod(
                                      event
                                        .target
                                        .value,
                                    )
                                }
                              >
                                <option
                                  value="cash"
                                >
                                  Cash
                                </option>

                                <option
                                  value="card"
                                >
                                  Card
                                </option>

                                <option
                                  value="bank_transfer"
                                >
                                  Bank transfer
                                </option>

                                <option
                                  value="cheque"
                                >
                                  Cheque
                                </option>

                                <option
                                  value="mobile_payment"
                                >
                                  Mobile payment
                                </option>
                              </select>
                            </label>

                            <label>
                              Reference

                              <input
                                type="text"
                                maxLength={150}
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

                            <label>
                              Payment notes

                              <input
                                type="text"
                                value={
                                  paymentNotes
                                }
                                onChange={
                                  (event) =>
                                    setPaymentNotes(
                                      event
                                        .target
                                        .value,
                                    )
                                }
                              />
                            </label>
                          </div>
                        )}
                      </section>

                      <div
                        className={
                          styles.confirmWarning
                        }
                      >
                        <CircleAlert
                          size={17}
                        />

                        Confirming the invoice
                        posts the sale. Make sure
                        the customer, stock,
                        serial numbers and prices
                        are correct.
                      </div>
                    </>
                  )}

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
                      closeNewSale
                    }
                  >
                    Keep draft
                  </button>

                  <button
                    type="button"
                    className={
                      styles.primaryButton
                    }
                    disabled={
                      saving
                      || !createdDraft
                    }
                    onClick={() =>
                      void confirmDraft()
                    }
                  >
                    {saving
                      ? "Confirming..."
                      : (
                        <>
                          <Check
                            size={16}
                          />

                          Confirm sale
                        </>
                      )
                    }
                  </button>
                </footer>
              </>
            )}
          </section>
        </div>
      )}


      {detailOpen && (
        <div
          className={
            styles.modalBackdrop
          }
        >
          <aside
            className={
              styles.detailDrawer
            }
          >
            <header
              className={
                styles.modalHeader
              }
            >
              <div>
                <p className="eyebrow">
                  INVOICE DETAILS
                </p>

                <h2>
                  {selectedInvoice
                    ?.invoice_number
                    ?? "Sales invoice"
                  }
                </h2>
              </div>

              <button
                type="button"
                className={
                  styles.iconButton
                }
                onClick={() =>
                  setDetailOpen(
                    false,
                  )
                }
              >
                <X size={18} />
              </button>
            </header>

            {detailLoading ? (
              <div
                className={
                  styles.emptyState
                }
              >
                <div
                  className="loading-spinner"
                />

                Loading invoice...
              </div>
            ) : selectedInvoice ? (
              <div
                className={
                  styles.detailBody
                }
              >
                <section
                  className={
                    styles.customerCard
                  }
                >
                  <UserRound
                    size={20}
                  />

                  <div>
                    <span>
                      Customer
                    </span>

                    <strong>
                      {
                        selectedInvoice
                          .customer_name
                      }
                    </strong>

                    <small>
                      {
                        selectedInvoice
                          .customer_phone
                      }
                    </small>
                  </div>
                </section>


                <div
                  className={
                    styles.detailStats
                  }
                >
                  <div>
                    <span>
                      Grand total
                    </span>

                    <strong>
                      {money(
                        selectedInvoice
                          .grand_total,
                      )}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Paid
                    </span>

                    <strong>
                      {money(
                        selectedInvoice
                          .paid_amount,
                      )}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Balance
                    </span>

                    <strong>
                      {money(
                        selectedInvoice
                          .balance_amount,
                      )}
                    </strong>
                  </div>
                </div>


                {selectedInvoice.trade_ins
                  .length > 0 && (
                  <section
                    className={
                      styles.detailSection
                    }
                  >
                    <h3>
                      Trade-in details
                    </h3>

                    {selectedInvoice.trade_ins.map(
                      (tradeIn) => (
                        <article
                          key={
                            tradeIn.id
                          }
                          className={
                            styles.detailItem
                          }
                        >
                          <div>
                            <strong>
                              {[
                                tradeIn.brand,
                                tradeIn.model,
                              ]
                                .filter(Boolean)
                                .join(" ")
                                || "Old A/C unit"
                              }
                            </strong>

                            <span>
                              {tradeIn.serial_number
                                ? `Serial: ${tradeIn.serial_number}`
                                : "Serial not recorded"
                              }
                            </span>

                            {tradeIn.condition && (
                              <small>
                                Condition:{" "}
                                {
                                  tradeIn.condition
                                }
                              </small>
                            )}

                            {tradeIn.description && (
                              <small>
                                {
                                  tradeIn.description
                                }
                              </small>
                            )}
                          </div>

                          <strong>
                            -{money(
                              tradeIn
                                .allowance_amount,
                            )}
                          </strong>
                        </article>
                      ),
                    )}
                  </section>
                )}


                <section
                  className={
                    styles.detailSection
                  }
                >
                  <h3>
                    Invoice items
                  </h3>

                  {selectedInvoice.items.map(
                    (
                      item,
                      index,
                    ) => (
                      <article
                        key={
                          item.id
                        }
                        className={
                          styles.detailItem
                        }
                      >
                        <div>
                          <span>
                            Item {index + 1}
                          </span>

                          <strong>
                            {item.product_name
                              ?? `Product #${item.product_id}`
                            }
                          </strong>

                          {item.serial_number && (
                            <small>
                              Serial:
                              {" "}
                              {
                                item
                                  .serial_number
                              }
                            </small>
                          )}
                        </div>

                        <div>
                          <span>
                            {quantityLabel(
                              item.quantity,
                            )}
                            {" × "}
                            {money(
                              item.unit_price,
                            )}
                          </span>

                          <strong>
                            {money(
                              item.line_total,
                            )}
                          </strong>
                        </div>
                      </article>
                    ),
                  )}
                </section>


                <section
                  className={
                    styles.detailSection
                  }
                >
                  <h3>
                    Payments
                  </h3>

                  {selectedInvoice
                    .payments.length === 0
                    ? (
                      <p
                        className={
                          styles.mutedText
                        }
                      >
                        No payments recorded.
                      </p>
                    )
                    : selectedInvoice
                        .payments.map(
                          (payment) => (
                            <article
                              key={
                                payment.id
                              }
                              className={
                                styles.paymentRow
                              }
                            >
                              <div>
                                <strong>
                                  {
                                    payment
                                      .receipt_number
                                  }
                                </strong>

                                <span>
                                  {
                                    payment
                                      .payment_method
                                  }
                                </span>
                              </div>

                              <strong>
                                {money(
                                  payment.amount,
                                )}
                              </strong>
                            </article>
                          ),
                        )
                  }
                </section>


                <section
                  className={
                    styles.detailSection
                  }
                >
                  <h3>
                    Status
                  </h3>

                  <div
                    className={
                      styles.statusRow
                    }
                  >
                    <span
                      className={
                        styles.statusBadge
                      }
                    >
                      {statusText(
                        selectedInvoice
                          .invoice_status,
                      )}
                    </span>

                    <span
                      className={
                        selectedInvoice
                          .payment_status
                        === "paid"
                          ? styles
                              .paidBadge
                          : styles
                              .paymentBadge
                      }
                    >
                      {statusText(
                        selectedInvoice
                          .payment_status,
                      )}
                    </span>
                  </div>
                </section>
              </div>
            ) : (
              <div
                className={
                  styles.emptyState
                }
              >
                Invoice not available.
              </div>
            )}
          </aside>
        </div>
      )}
    </AppShell>
  );
}
