"use client";

import axios from "axios";

import {
  Check,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  ClipboardCheck,
  Eye,
  Loader2,
  PackageCheck,
  Plus,
  RefreshCw,
  RotateCcw,
  Search,
  ShieldCheck,
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
  getSalesInvoice,
  getSalesInvoices,
  getSalesProducts,
  getSalesWarehouses,
  getAvailableSalesSerials,
} from "@/lib/sales-api";

import {
  approveReturn,
  changeReturnStatus,
  createReturn,
  getReturn,
  getReturnableInvoice,
  getReturns,
  inspectReturn,
  processReturn,
  setReplacementItem,
} from "@/lib/returns-api";

import type {
  UserResponse,
} from "@/types/auth";

import type {
  SalesInvoiceDetailResponse,
  SalesInvoiceResponse,
  SalesProductOption,
  SalesSerialOption,
  SalesWarehouseOption,
} from "@/types/sales";

import type {
  ReturnDraftItem,
  ReturnItemCondition,
  ReturnResolution,
  ReturnStatus,
  ReturnableInvoiceResponse,
  SalesReturnDetailResponse,
  SalesReturnListResponse,
} from "@/types/returns";

import styles from "./returns.module.css";


const PAGE_SIZE = 20;


const emptyList:
SalesReturnListResponse = {
  items: [],
  total: 0,
  page: 1,
  page_size: PAGE_SIZE,
  total_pages: 0,
};


function numberValue(
  value:
    | string
    | number
    | null
    | undefined,
): number {
  const result =
    Number(value);

  return (
    Number.isFinite(result)
      ? result
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
    numberValue(value),
  );
}


function quantity(
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
    numberValue(value),
  );
}


function dateTime(
  value:
    string | null,
): string {
  if (!value) {
    return "—";
  }

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


function readable(
  value:
    string | null | undefined,
): string {
  if (!value) {
    return "—";
  }

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


function optionalText(
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
      + "for this return operation."
    );
  }

  return (
    "Unable to complete "
    + "the return operation."
  );
}


export default function ReturnsPage() {
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
    returns,
    setReturns,
  ] =
    useState<
      SalesReturnListResponse
    >(
      emptyList,
    );

  const [
    page,
    setPage,
  ] =
    useState(1);

  const [
    search,
    setSearch,
  ] =
    useState("");

  const [
    searchInput,
    setSearchInput,
  ] =
    useState("");

  const [
    statusFilter,
    setStatusFilter,
  ] =
    useState("");

  const [
    resolutionFilter,
    setResolutionFilter,
  ] =
    useState("");

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
    selected,
    setSelected,
  ] =
    useState<
      SalesReturnDetailResponse
      | null
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
    createOpen,
    setCreateOpen,
  ] =
    useState(false);

  const [
    invoiceSearch,
    setInvoiceSearch,
  ] =
    useState("");

  const [
    invoiceSearchResults,
    setInvoiceSearchResults,
  ] =
    useState<
      SalesInvoiceResponse[]
    >([]);

  const [
    invoiceSearchLoading,
    setInvoiceSearchLoading,
  ] =
    useState(false);


  const [
    invoice,
    setInvoice,
  ] =
    useState<
      SalesInvoiceDetailResponse
      | null
    >(
      null,
    );

  const [
    invoiceLoading,
    setInvoiceLoading,
  ] =
    useState(false);

  const [
    returnReason,
    setReturnReason,
  ] =
    useState("");

  const [
    returnEligibility,
    setReturnEligibility,
  ] =
    useState<
      ReturnableInvoiceResponse
      | null
    >(null);


  const [
    draftItems,
    setDraftItems,
  ] =
    useState<
      ReturnDraftItem[]
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
    actionMode,
    setActionMode,
  ] =
    useState<
      | "inspect"
      | "approve"
      | "reject"
      | "replacement"
      | "status"
      | null
    >(
      null,
    );

  const [
    actionLoading,
    setActionLoading,
  ] =
    useState(false);

  const [
    inspectionNotes,
    setInspectionNotes,
  ] =
    useState("");

  const [
    approvalResolution,
    setApprovalResolution,
  ] =
    useState<
      ReturnResolution
    >(
      "refund",
    );

  const [
    approvalNotes,
    setApprovalNotes,
  ] =
    useState("");

  const [
    refundAmount,
    setRefundAmount,
  ] =
    useState("0.00");


  const [
    replacementReturnItemId,
    setReplacementReturnItemId,
  ] =
    useState("");

  const [
    replacementProductId,
    setReplacementProductId,
  ] =
    useState("");

  const [
    replacementProductSearch,
    setReplacementProductSearch,
  ] =
    useState("");

  const [
    replacementWarehouseId,
    setReplacementWarehouseId,
  ] =
    useState("");

  const [
    replacementSerialId,
    setReplacementSerialId,
  ] =
    useState("");

  const [
    replacementNotes,
    setReplacementNotes,
  ] =
    useState("");

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
    replacementSerials,
    setReplacementSerials,
  ] =
    useState<
      SalesSerialOption[]
    >(
      [],
    );

  const [
    serialLoading,
    setSerialLoading,
  ] =
    useState(false);


  const [
    manualStatus,
    setManualStatus,
  ] =
    useState<
      ReturnStatus
    >(
      "cancelled",
    );

  const [
    statusRemarks,
    setStatusRemarks,
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


  const loadReturns =
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
            await getReturns({
              page,
              pageSize:
                PAGE_SIZE,

              search:
                search
                || undefined,

              returnStatus:
                statusFilter
                || undefined,

              resolution:
                resolutionFilter
                || undefined,
            });

          setReturns(
            result,
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
        statusFilter,
        resolutionFilter,
      ],
    );


  useEffect(() => {
    if (authLoading) {
      return;
    }

    const timer =
      window.setTimeout(
        () => {
          void loadReturns();
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
    loadReturns,
  ]);


  const summary =
    useMemo(
      () => {
        const requested =
          returns.items.filter(
            (item) =>
              item.status
              === "requested",
          ).length;

        const approved =
          returns.items.filter(
            (item) =>
              item.status
              === "approved",
          ).length;

        const completed =
          returns.items.filter(
            (item) =>
              item.status
              === "completed",
          ).length;

        return {
          requested,
          approved,
          completed,
        };
      },
      [returns.items],
    );


  async function refreshDetail(
    returnId: number,
  ) {
    const detail =
      await getReturn(
        returnId,
      );

    setSelected(
      detail,
    );

    return detail;
  }


  async function openDetail(
    returnId: number,
  ) {
    setDetailOpen(
      true,
    );

    setDetailLoading(
      true,
    );

    setSelected(
      null,
    );

    setError("");

    try {
      await refreshDetail(
        returnId,
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


  async function openCreate() {
    setError("");

    try {
      const warehouseData =
        await getSalesWarehouses();

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

      return;
    }

    setInvoiceSearch("");
    setInvoiceSearchResults([]);
    setInvoice(null);
    setReturnEligibility(null);
    setDraftItems([]);
    setReturnReason("");
    setCreateOpen(true);
  }


  async function searchInvoicesForReturn(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const search =
      invoiceSearch.trim();

    if (search.length < 2) {
      setError(
        "Enter at least 2 characters "
        + "of the invoice number.",
      );

      return;
    }

    setInvoiceSearchLoading(true);
    setError("");

    try {
      const result =
        await getSalesInvoices({
          page: 1,
          pageSize: 20,
          search,
        });

      const eligibleInvoices =
        result.items.filter(
          (item) =>
            item.invoice_status
              === "confirmed"
            || item.invoice_status
              === "returned",
        );

      setInvoiceSearchResults(
        eligibleInvoices,
      );

      if (
        eligibleInvoices.length === 0
      ) {
        setError(
          "No confirmed or returned "
          + "invoices matched that search.",
        );
      }
    } catch (err) {
      setError(
        apiError(
          err,
        ),
      );
    } finally {
      setInvoiceSearchLoading(false);
    }
  }


  async function selectInvoiceForReturn(
    selectedInvoiceId: number,
  ) {
    setInvoiceSearchResults([]);

    setInvoiceLoading(true);
    setError("");

    try {
      const [
        result,
        eligibility,
      ] =
        await Promise.all([
          getSalesInvoice(
            selectedInvoiceId,
          ),
          getReturnableInvoice(
            selectedInvoiceId,
          ),
        ]);

      if (
        result.invoice_status
          !== "confirmed"
        && result.invoice_status
          !== "returned"
      ) {
        setInvoice(null);
        setDraftItems([]);

        setError(
          "Returns can only be created "
          + "for a confirmed or "
          + "previously returned invoice.",
        );

        return;
      }

      setInvoice(result);
      setReturnEligibility(
        eligibility,
      );

      setDraftItems(
        result.items.map(
          (item) => {
            const eligibilityItem =
              eligibility.items.find(
                (candidate) =>
                  candidate
                    .invoice_item_id
                  === item.id,
              );

            const remainingQuantity =
              eligibilityItem
                ?.remaining_quantity
              ?? "0.000";

            return {
              invoiceItemId:
                item.id,

              selected:
                false,

              quantity:
                (
                  eligibilityItem
                    ?.serial_number_id
                  ?? item.serial_number_id
                )
                  ? (
                      eligibilityItem
                        ?.is_returnable
                        ? "1.000"
                        : "0.000"
                    )
                  : remainingQuantity,

              condition:
                "good",

              reason:
                "",

              destinationWarehouseId:
                "",
            };
          },
        ),
      );
    } catch (err) {
      setInvoice(null);
      setReturnEligibility(null);
      setDraftItems([]);

      setError(
        apiError(
          err,
        ),
      );
    } finally {
      setInvoiceLoading(false);
    }
  }


  function updateDraftItem(
    invoiceItemId: number,

    patch:
      Partial<ReturnDraftItem>,
  ) {
    setDraftItems(
      (current) =>
        current.map(
          (item) =>
            item.invoiceItemId
            === invoiceItemId
              ? {
                  ...item,
                  ...patch,
                }
              : item,
        ),
    );
  }


  async function submitReturn() {
    if (!invoice) {
      setError(
        "Load an invoice first.",
      );

      return;
    }

    if (
      returnReason
        .trim()
        .length < 3
    ) {
      setError(
        "Return reason must contain "
        + "at least 3 characters.",
      );

      return;
    }

    const selectedItems =
      draftItems.filter(
        (item) =>
          item.selected,
      );

    if (
      selectedItems.length === 0
    ) {
      setError(
        "Select at least one "
        + "invoice item.",
      );

      return;
    }

    for (
      const item
      of selectedItems
    ) {
      if (
        numberValue(
          item.quantity,
        ) <= 0
      ) {
        setError(
          "Return quantity must "
          + "be greater than zero.",
        );

        return;
      }
    }

    if (!returnEligibility) {
      setError(
        "Return availability could "
        + "not be verified. Reload "
        + "the invoice and try again.",
      );

      return;
    }

    for (
      const item
      of selectedItems
    ) {
      const eligibilityItem =
        returnEligibility.items.find(
          (candidate) =>
            candidate
              .invoice_item_id
            === item.invoiceItemId,
        );

      if (
        !eligibilityItem
        || !eligibilityItem
          .is_returnable
      ) {
        setError(
          "One of the selected items "
          + "is no longer returnable.",
        );

        return;
      }

      if (
        numberValue(
          item.quantity,
        )
        >
        numberValue(
          eligibilityItem
            .remaining_quantity,
        )
      ) {
        setError(
          "Return quantity exceeds "
          + "the available returnable "
          + "quantity.",
        );

        return;
      }

      const invoiceItem =
        invoice.items.find(
          (candidate) =>
            candidate.id
            === item.invoiceItemId,
        );

      if (
        invoiceItem
          ?.serial_number_id
        && numberValue(
          item.quantity,
        ) !== 1
      ) {
        setError(
          "Serialized return quantity "
          + "must be exactly 1.",
        );

        return;
      }
    }

    setActionLoading(
      true,
    );

    setError("");

    try {
      const created =
        await createReturn({
          invoice_id:
            invoice.id,

          return_type:
            "sales_return",

          reason:
            returnReason.trim(),

          items:
            selectedItems.map(
              (item) => ({
                invoice_item_id:
                  item.invoiceItemId,

                quantity:
                  item.quantity,

                condition:
                  item.condition,

                reason:
                  optionalText(
                    item.reason,
                  ),

                destination_warehouse_id:
                  item
                    .destinationWarehouseId
                    ? Number(
                        item
                          .destinationWarehouseId,
                      )
                    : null,
              }),
            ),
        });

      setCreateOpen(
        false,
      );

      setSelected(
        created,
      );

      setDetailOpen(
        true,
      );

      await loadReturns(
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
    } finally {
      setActionLoading(
        false,
      );
    }
  }


  async function submitInspection() {
    if (!selected) {
      return;
    }

    if (
      inspectionNotes
        .trim()
        .length < 3
    ) {
      setError(
        "Inspection notes must contain "
        + "at least 3 characters.",
      );

      return;
    }

    setActionLoading(
      true,
    );

    setError("");

    try {
      const result =
        await inspectReturn(
          selected.id,
          {
            inspection_notes:
              inspectionNotes.trim(),
          },
        );

      setSelected(
        result,
      );

      setActionMode(
        null,
      );

      setInspectionNotes(
        "",
      );

      await loadReturns(
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
    } finally {
      setActionLoading(
        false,
      );
    }
  }


  async function submitApproval(
    approved:
      boolean,
  ) {
    if (!selected) {
      return;
    }

    let resolution:
      ReturnResolution;

    let amount =
      "0.00";

    if (approved) {
      resolution =
        approvalResolution;

      if (
        resolution
        === "refund"
      ) {
        const parsed =
          numberValue(
            refundAmount,
          );

        if (parsed < 0) {
          setError(
            "Refund amount cannot "
            + "be negative.",
          );

          return;
        }

        amount =
          parsed.toFixed(2);
      }
    } else {
      resolution =
        "rejected";
    }

    setActionLoading(
      true,
    );

    setError("");

    try {
      const result =
        await approveReturn(
          selected.id,
          {
            approved,

            resolution,

            approval_notes:
              optionalText(
                approvalNotes,
              ),

            refund_amount:
              amount,
          },
        );

      setSelected(
        result,
      );

      setActionMode(
        null,
      );

      setApprovalNotes(
        "",
      );

      setRefundAmount(
        "0.00",
      );

      await loadReturns(
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
    } finally {
      setActionLoading(
        false,
      );
    }
  }


  async function submitProcess() {
    if (!selected) {
      return;
    }

    setActionLoading(
      true,
    );

    setError("");

    try {
      const result =
        await processReturn(
          selected.id,
        );

      setSelected(
        result,
      );

      await loadReturns(
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
    } finally {
      setActionLoading(
        false,
      );
    }
  }


  async function loadAllReplacementProducts() {
    const allProducts:
      SalesProductOption[] = [];

    let productPage = 1;

    while (true) {
      const pageProducts =
        await getSalesProducts(
          undefined,
          productPage,
        );

      allProducts.push(
        ...pageProducts,
      );

      if (
        pageProducts.length
        < 100
      ) {
        break;
      }

      productPage += 1;
    }

    const uniqueProducts =
      Array.from(
        new Map(
          allProducts.map(
            (product) => [
              product.id,
              product,
            ],
          ),
        ).values(),
      );

    return uniqueProducts.sort(
      (a, b) =>
        (
          a.product_code
          + " "
          + a.name
        ).localeCompare(
          b.product_code
          + " "
          + b.name,
        ),
    );
  }


  async function openReplacement() {
    if (!selected) {
      return;
    }

    setError("");

    try {
      const [
        productData,
        warehouseData,
      ] =
        await Promise.all([
          loadAllReplacementProducts(),
          getSalesWarehouses(),
        ]);

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

      return;
    }

    setReplacementReturnItemId(
      selected.items[0]
        ? String(
            selected.items[0].id,
          )
        : "",
    );

    setReplacementProductId(
      "",
    );

    setReplacementProductSearch(
      "",
    );

    setReplacementWarehouseId(
      "",
    );

    setReplacementSerialId(
      "",
    );

    setReplacementSerials(
      [],
    );

    setReplacementNotes(
      "",
    );

    setActionMode(
      "replacement",
    );
  }


  async function loadReplacementSerials(
    productId:
      string,

    warehouseId:
      string,
  ) {
    setReplacementSerialId(
      "",
    );

    setReplacementSerials(
      [],
    );

    if (
      !productId
      || !warehouseId
    ) {
      return;
    }

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
    ) {
      return;
    }

    setSerialLoading(
      true,
    );

    try {
      const values =
        await getAvailableSalesSerials(
          Number(
            productId,
          ),
          Number(
            warehouseId,
          ),
        );

      setReplacementSerials(
        values,
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
      setSerialLoading(
        false,
      );
    }
  }


  async function submitReplacement() {
    if (!selected) {
      return;
    }

    if (
      !replacementReturnItemId
      || !replacementProductId
      || !replacementWarehouseId
    ) {
      setError(
        "Select return item, product "
        + "and warehouse.",
      );

      return;
    }

    const product =
      products.find(
        (item) =>
          String(
            item.id,
          )
          === replacementProductId,
      );

    if (
      product
        ?.track_serial_numbers
      && !replacementSerialId
    ) {
      setError(
        "Select an available serial "
        + "number for this product.",
      );

      return;
    }

    setActionLoading(
      true,
    );

    setError("");

    try {
      const result =
        await setReplacementItem(
          selected.id,
          {
            return_item_id:
              Number(
                replacementReturnItemId,
              ),

            replacement_product_id:
              Number(
                replacementProductId,
              ),

            replacement_serial_number_id:
              replacementSerialId
                ? Number(
                    replacementSerialId,
                  )
                : null,

            warehouse_id:
              Number(
                replacementWarehouseId,
              ),

            notes:
              optionalText(
                replacementNotes,
              ),
          },
        );

      setSelected(
        result,
      );

      setActionMode(
        null,
      );

      await loadReturns(
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
    } finally {
      setActionLoading(
        false,
      );
    }
  }


  async function submitStatusChange() {
    if (!selected) {
      return;
    }

    setActionLoading(
      true,
    );

    setError("");

    try {
      const result =
        await changeReturnStatus(
          selected.id,
          {
            new_status:
              manualStatus,

            remarks:
              optionalText(
                statusRemarks,
              ),
          },
        );

      setSelected(
        result,
      );

      setActionMode(
        null,
      );

      setStatusRemarks(
        "",
      );

      await loadReturns(
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
    } finally {
      setActionLoading(
        false,
      );
    }
  }


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
          150,
        ),
    );
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
            Returns
          </h1>

          <p>
            Manage customer return
            requests, inspection,
            approval, refunds and
            replacement stock.
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
            onClick={() =>
              void openCreate()
            }
          >
            <Plus size={17} />

            New return
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
              void loadReturns(
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
        </div>
      </section>


      <section
        className={
          styles.summaryGrid
        }
      >
        <article>
          <RotateCcw
            size={20}
          />

          <div>
            <span>
              Returns
            </span>

            <strong>
              {returns.total}
            </strong>
          </div>
        </article>

        <article>
          <ClipboardCheck
            size={20}
          />

          <div>
            <span>
              Requested
            </span>

            <strong>
              {summary.requested}
            </strong>
          </div>
        </article>

        <article>
          <ShieldCheck
            size={20}
          />

          <div>
            <span>
              Approved
            </span>

            <strong>
              {summary.approved}
            </strong>
          </div>
        </article>

        <article>
          <PackageCheck
            size={20}
          />

          <div>
            <span>
              Completed
            </span>

            <strong>
              {summary.completed}
            </strong>
          </div>
        </article>
      </section>


      <section
        className={
          styles.filters
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
          <Search
            size={16}
          />

          <input
            value={
              searchInput
            }
            placeholder={
              "Return number, invoice or customer..."
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
            statusFilter
          }
          onChange={
            (event) => {
              setPage(1);

              setStatusFilter(
                event
                  .target
                  .value,
              );
            }
          }
        >
          <option value="">
            All statuses
          </option>

          <option value="requested">
            Requested
          </option>

          <option value="inspected">
            Inspected
          </option>

          <option value="approved">
            Approved
          </option>

          <option value="rejected">
            Rejected
          </option>

          <option value="completed">
            Completed
          </option>
        </select>

        <select
          value={
            resolutionFilter
          }
          onChange={
            (event) => {
              setPage(1);

              setResolutionFilter(
                event
                  .target
                  .value,
              );
            }
          }
        >
          <option value="">
            All resolutions
          </option>

          <option value="pending">
            Pending
          </option>

          <option value="refund">
            Refund
          </option>

          <option value="replacement">
            Replacement
          </option>

          <option value="rejected">
            Rejected
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
              size={22}
              className={
                styles.spin
              }
            />

            Loading returns...
          </div>
        ) : returns.items.length
          === 0 ? (
          <div
            className={
              styles.emptyState
            }
          >
            <RotateCcw
              size={28}
            />

            <strong>
              No returns found
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
                    Return
                  </th>

                  <th>
                    Invoice
                  </th>

                  <th>
                    Customer
                  </th>

                  <th>
                    Date
                  </th>

                  <th>
                    Amount
                  </th>

                  <th>
                    Status
                  </th>

                  <th>
                    Resolution
                  </th>

                  <th />
                </tr>
              </thead>

              <tbody>
                {returns.items.map(
                  (item) => (
                    <tr
                      key={
                        item.id
                      }
                    >
                      <td>
                        <strong>
                          {
                            item
                              .return_number
                          }
                        </strong>
                      </td>

                      <td>
                        {
                          item
                            .invoice_number
                        }
                      </td>

                      <td>
                        {
                          item
                            .customer_name
                        }
                      </td>

                      <td>
                        {dateTime(
                          item.created_at,
                        )}
                      </td>

                      <td>
                        {money(
                          item.subtotal,
                        )}
                      </td>

                      <td>
                        <span
                          className={
                            styles.badge
                          }
                        >
                          {readable(
                            item.status,
                          )}
                        </span>
                      </td>

                      <td>
                        <span
                          className={
                            styles
                              .resolutionBadge
                          }
                        >
                          {readable(
                            item.resolution,
                          )}
                        </span>
                      </td>

                      <td>
                        <button
                          type="button"
                          className={
                            styles.iconButton
                          }
                          onClick={() =>
                            void openDetail(
                              item.id,
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
            Page {returns.page}
            {" of "}
            {Math.max(
              1,
              returns.total_pages,
            )}
          </span>

          <button
            type="button"
            disabled={
              page
              >= returns.total_pages
              || returns.total_pages
                === 0
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
      </section>


      {createOpen && (
        <div
          className={
            styles.backdrop
          }
        >
          <section
            className={
              styles.modalLarge
            }
          >
            <header
              className={
                styles.modalHeader
              }
            >
              <div>
                <p className="eyebrow">
                  SALES RETURN
                </p>

                <h2>
                  New return request
                </h2>
              </div>

              <button
                type="button"
                className={
                  styles.iconButton
                }
                onClick={() =>
                  setCreateOpen(
                    false,
                  )
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
              <form
                className={
                  styles.invoiceLookup
                }
                onSubmit={
                  searchInvoicesForReturn
                }
              >
                <label>
                  Search invoice number

                  <input
                    type="search"
                    placeholder="Example: INV-000123"
                    autoComplete="off"
                    value={
                      invoiceSearch
                    }
                    onChange={
                      (event) =>
                        setInvoiceSearch(
                          event.target.value,
                        )
                    }
                  />
                </label>

                <button
                  type="submit"
                  className={
                    styles.secondaryButton
                  }
                  disabled={
                    invoiceSearchLoading
                  }
                >
                  {invoiceSearchLoading
                    ? "Searching..."
                    : "Search invoice"
                  }
                </button>
              </form>

              {invoiceSearchResults.length
                > 0 && (
                <div
                  className={
                    styles.itemList
                  }
                >
                  {invoiceSearchResults.map(
                    (item) => (
                      <button
                        key={
                          item.id
                        }
                        type="button"
                        className={
                          styles.secondaryButton
                        }
                        disabled={
                          invoiceLoading
                        }
                        onClick={() =>
                          void selectInvoiceForReturn(
                            item.id,
                          )
                        }
                      >
                        {item.invoice_number}
                        {" · "}
                        {item.invoice_date}
                        {" · LKR "}
                        {item.grand_total}
                      </button>
                    ),
                  )}
                </div>
              )}

              {invoice && (
                <>
                  <section
                    className={
                      styles.invoiceCard
                    }
                  >
                    <div>
                      <span>
                        Invoice
                      </span>

                      <strong>
                        {
                          invoice
                            .invoice_number
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        Customer
                      </span>

                      <strong>
                        {
                          invoice
                            .customer_name
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        Total
                      </span>

                      <strong>
                        {money(
                          invoice
                            .grand_total,
                        )}
                      </strong>
                    </div>
                  </section>


                  <section
                    className={
                      styles.formSection
                    }
                  >
                    <h3>
                      Return items
                    </h3>

                    <div
                      className={
                        styles.itemList
                      }
                    >
                      {invoice.items.map(
                        (
                          invoiceItem,
                        ) => {
                          const draft =
                            draftItems.find(
                              (item) =>
                                item
                                  .invoiceItemId
                                === invoiceItem.id,
                            );

                          if (!draft) {
                            return null;
                          }

                          const eligibilityItem =
                            returnEligibility
                              ?.items.find(
                                (item) =>
                                  item
                                    .invoice_item_id
                                  === invoiceItem.id,
                              );

                          const isReturnable =
                            Boolean(
                              eligibilityItem
                                ?.is_returnable,
                            );

                          return (
                            <article
                              key={
                                invoiceItem.id
                              }
                              className={
                                draft.selected
                                  ? styles
                                      .returnItemSelected
                                  : styles
                                      .returnItem
                              }
                            >
                              <label
                                className={
                                  styles
                                    .itemCheck
                                }
                              >
                                <input
                                  type="checkbox"
                                  checked={
                                    draft
                                      .selected
                                  }
                                  disabled={
                                    !isReturnable
                                  }
                                  onChange={
                                    (event) =>
                                      updateDraftItem(
                                        invoiceItem.id,
                                        {
                                          selected:
                                            event
                                              .target
                                              .checked,
                                        },
                                      )
                                  }
                                />

                                <div>
                                  <strong>
                                    {invoiceItem
                                      .product_name
                                      ?? `Product #${invoiceItem.product_id}`
                                    }
                                  </strong>

                                  <span>
                                    Sold:
                                    {" "}
                                    {quantity(
                                      invoiceItem
                                        .quantity,
                                    )}

                                    {" • Returned: "}

                                    {quantity(
                                      eligibilityItem
                                        ?.already_returned_quantity
                                      ?? "0.000",
                                    )}

                                    {" • Available: "}

                                    {quantity(
                                      eligibilityItem
                                        ?.remaining_quantity
                                      ?? "0.000",
                                    )}

                                    {" • "}

                                    {money(
                                      invoiceItem
                                        .line_total,
                                    )}
                                  </span>

                                  {!isReturnable
                                    && eligibilityItem
                                      ?.block_reason && (
                                    <small>
                                      {
                                        eligibilityItem
                                          .block_reason
                                      }
                                    </small>
                                  )}

                                  {(
                                    eligibilityItem
                                      ?.serial_number
                                    ?? invoiceItem
                                      .serial_number
                                  ) && (
                                    <small>
                                      Serial:
                                      {" "}
                                      {
                                        eligibilityItem
                                          ?.serial_number
                                        ?? invoiceItem
                                          .serial_number
                                      }
                                    </small>
                                  )}
                                </div>
                              </label>

                              {draft.selected && (
                                <div
                                  className={
                                    styles
                                      .itemFields
                                  }
                                >
                                  <label>
                                    Quantity

                                    <input
                                      type="number"
                                      min="0.001"
                                      max={
                                        eligibilityItem
                                          ?.remaining_quantity
                                        ?? "0.000"
                                      }
                                      step="0.001"
                                      value={
                                        draft
                                          .quantity
                                      }
                                      disabled={
                                        !isReturnable
                                        || Boolean(
                                          eligibilityItem
                                            ?.serial_number_id
                                          ?? invoiceItem
                                            .serial_number_id,
                                        )
                                      }
                                      onChange={
                                        (event) =>
                                          updateDraftItem(
                                            invoiceItem.id,
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

                                  <label>
                                    Condition

                                    <select
                                      value={
                                        draft
                                          .condition
                                      }
                                      onChange={
                                        (event) => {
                                          const value =
                                            event
                                              .target
                                              .value;

                                          const condition:
                                            ReturnItemCondition =
                                              value
                                              === "damaged"
                                                ? "damaged"
                                                : value
                                                  === "faulty"
                                                  ? "faulty"
                                                  : value
                                                    === "opened"
                                                    ? "opened"
                                                    : "good";

                                          updateDraftItem(
                                            invoiceItem.id,
                                            {
                                              condition,
                                            },
                                          );
                                        }
                                      }
                                    >
                                      <option
                                        value="good"
                                      >
                                        Good
                                      </option>

                                      <option
                                        value="opened"
                                      >
                                        Opened
                                      </option>

                                      <option
                                        value="faulty"
                                      >
                                        Faulty
                                      </option>

                                      <option
                                        value="damaged"
                                      >
                                        Damaged
                                      </option>
                                    </select>
                                  </label>

                                  <label>
                                    Destination warehouse

                                    <select
                                      value={
                                        draft
                                          .destinationWarehouseId
                                      }
                                      onChange={
                                        (event) =>
                                          updateDraftItem(
                                            invoiceItem.id,
                                            {
                                              destinationWarehouseId:
                                                event
                                                  .target
                                                  .value,
                                            },
                                          )
                                      }
                                    >
                                      <option value="">
                                        Auto/default
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

                                  <label
                                    className={
                                      styles
                                        .fullField
                                    }
                                  >
                                    Item reason

                                    <input
                                      value={
                                        draft.reason
                                      }
                                      onChange={
                                        (event) =>
                                          updateDraftItem(
                                            invoiceItem.id,
                                            {
                                              reason:
                                                event
                                                  .target
                                                  .value,
                                            },
                                          )
                                      }
                                    />
                                  </label>
                                </div>
                              )}
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
                    <label>
                      Overall return reason *

                      <textarea
                        rows={3}
                        minLength={3}
                        required
                        value={
                          returnReason
                        }
                        onChange={
                          (event) =>
                            setReturnReason(
                              event
                                .target
                                .value,
                            )
                        }
                      />
                    </label>
                  </section>
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
                onClick={() =>
                  setCreateOpen(
                    false,
                  )
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
                  actionLoading
                  || !invoice
                }
                onClick={() =>
                  void submitReturn()
                }
              >
                {actionLoading
                  ? "Creating..."
                  : "Create return"
                }
              </button>
            </footer>
          </section>
        </div>
      )}


      {detailOpen && (
        <div
          className={
            styles.backdrop
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
                  RETURN DETAILS
                </p>

                <h2>
                  {selected
                    ?.return_number
                    ?? "Return"
                  }
                </h2>
              </div>

              <button
                type="button"
                className={
                  styles.iconButton
                }
                onClick={() => {
                  setDetailOpen(
                    false,
                  );

                  setSelected(
                    null,
                  );
                }}
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
                <Loader2
                  size={22}
                  className={
                    styles.spin
                  }
                />

                Loading return...
              </div>
            ) : selected && (
              <>
                <div
                  className={
                    styles.detailBody
                  }
                >
                  <section
                    className={
                      styles.detailHero
                    }
                  >
                    <div>
                      <span>
                        Invoice
                      </span>

                      <strong>
                        {
                          selected
                            .invoice_number
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        Customer
                      </span>

                      <strong>
                        {
                          selected
                            .customer_name
                        }
                      </strong>
                    </div>

                    <div>
                      <span>
                        Return value
                      </span>

                      <strong>
                        {money(
                          selected
                            .subtotal,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Status
                      </span>

                      <strong>
                        {readable(
                          selected.status,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Resolution
                      </span>

                      <strong>
                        {readable(
                          selected
                            .resolution,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Refund
                      </span>

                      <strong>
                        {money(
                          selected
                            .refund_amount,
                        )}
                      </strong>
                    </div>
                  </section>


                  <section
                    className={
                      styles.detailSection
                    }
                  >
                    <h3>
                      Reason
                    </h3>

                    <p>
                      {selected.reason}
                    </p>
                  </section>


                  <section
                    className={
                      styles.detailSection
                    }
                  >
                    <h3>
                      Returned items
                    </h3>

                    {selected.items.map(
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
                              Product #
                              {
                                item
                                  .product_id
                              }
                            </strong>

                            <small>
                              {readable(
                                item.condition,
                              )}
                            </small>

                            {item.serial_number && (
                              <small>
                                Serial:
                                {" "}
                                {item.serial_number}
                              </small>
                            )}
                          </div>

                          <div>
                            <span>
                              {quantity(
                                item.quantity,
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


                  {(selected
                    .inspection_notes
                    || selected
                      .approval_notes) && (
                    <section
                      className={
                        styles
                          .detailSection
                      }
                    >
                      <h3>
                        Review notes
                      </h3>

                      {selected
                        .inspection_notes && (
                        <p>
                          <strong>
                            Inspection:
                          </strong>
                          {" "}
                          {
                            selected
                              .inspection_notes
                          }
                        </p>
                      )}

                      {selected
                        .approval_notes && (
                        <p>
                          <strong>
                            Approval:
                          </strong>
                          {" "}
                          {
                            selected
                              .approval_notes
                          }
                        </p>
                      )}
                    </section>
                  )}


                  <section
                    className={
                      styles.detailSection
                    }
                  >
                    <h3>
                      Status history
                    </h3>

                    {selected
                      .status_history.map(
                        (history) => (
                          <article
                            key={
                              history.id
                            }
                            className={
                              styles.historyRow
                            }
                          >
                            <div>
                              <strong>
                                {readable(
                                  history
                                    .old_status,
                                )}
                                {" → "}
                                {readable(
                                  history
                                    .new_status,
                                )}
                              </strong>

                              <span>
                                {
                                  history
                                    .remarks
                                  || "No remarks"
                                }
                              </span>
                            </div>

                            <small>
                              {dateTime(
                                history
                                  .created_at,
                              )}
                            </small>
                          </article>
                        ),
                      )}
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
                    styles.actionBar
                  }
                >
                  {selected.status
                    === "requested" && (
                    <button
                      type="button"
                      onClick={() => {
                        setInspectionNotes(
                          "",
                        );

                        setActionMode(
                          "inspect",
                        );
                      }}
                    >
                      Inspect
                    </button>
                  )}

                  {[
                    "inspected",
                    "waiting_approval",
                  ].includes(
                    selected.status,
                  ) && (
                    <>
                      <button
                        type="button"
                        onClick={() => {
                          setApprovalResolution(
                            "refund",
                          );

                          setRefundAmount(
                            selected.subtotal,
                          );

                          setApprovalNotes(
                            "",
                          );

                          setActionMode(
                            "approve",
                          );
                        }}
                      >
                        Approve
                      </button>

                      <button
                        type="button"
                        className={
                          styles.dangerButton
                        }
                        onClick={() => {
                          setApprovalNotes(
                            "",
                          );

                          setActionMode(
                            "reject",
                          );
                        }}
                      >
                        Reject
                      </button>
                    </>
                  )}

                  {selected.status
                    === "approved"
                    && selected.resolution
                      === "replacement" && (
                    <button
                      type="button"
                      onClick={() =>
                        void openReplacement()
                      }
                    >
                      Set replacement
                    </button>
                  )}

                                    {selected.status
                    === "approved"
                    && selected.resolution
                      === "refund" && (
                    <button
                      type="button"
                      className={
                        styles.primaryButton
                      }
                      disabled={
                        actionLoading
                      }
                      onClick={() => {
                        router.push(
                          `/credit-notes?returnId=${selected.id}`,
                        );
                      }}
                    >
                      Continue refund
                    </button>
                  )}

{selected.status
                    === "approved"
                    && selected.resolution
                      === "warranty_service" && (
                    <button
                      type="button"
                      className={
                        styles.primaryButton
                      }
                      disabled={
                        actionLoading
                      }
                      onClick={() =>
                        void submitProcess()
                      }
                    >
                      {actionLoading
                        ? "Processing..."
                        : "Process return"
                      }
                    </button>
                  )}


                </footer>
              </>
            )}
          </aside>
        </div>
      )}


      {actionMode && selected && (
        <div
          className={
            styles.actionBackdrop
          }
        >
          <section
            className={
              styles.actionModal
            }
          >
            <header
              className={
                styles.modalHeader
              }
            >
              <div>
                <p className="eyebrow">
                  RETURN ACTION
                </p>

                <h2>
                  {actionMode
                    === "inspect"
                    ? "Inspect return"
                    : actionMode
                        === "approve"
                      ? "Approve return"
                      : actionMode
                          === "reject"
                        ? "Reject return"
                        : actionMode
                            === "replacement"
                          ? "Set replacement"
                          : "Return action"
                  }
                </h2>
              </div>

              <button
                type="button"
                className={
                  styles.iconButton
                }
                onClick={() =>
                  setActionMode(
                    null,
                  )
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
              {actionMode
                === "inspect" && (
                <label>
                  Inspection notes *

                  <textarea
                    rows={5}
                    minLength={3}
                    value={
                      inspectionNotes
                    }
                    onChange={
                      (event) =>
                        setInspectionNotes(
                          event
                            .target
                            .value,
                        )
                    }
                  />
                </label>
              )}


              {(actionMode
                === "approve"
                || actionMode
                  === "reject") && (
                <>
                  {actionMode
                    === "approve" && (
                    <>
                      <label>
                        Resolution

                        <select
                          value={
                            approvalResolution
                          }
                          onChange={
                            (event) => {
                              const value =
                                event
                                  .target
                                  .value;

                              setApprovalResolution(
                                value
                                === "replacement"
                                  ? "replacement"
                                  : "refund",
                              );
                            }
                          }
                        >
                          <option
                            value="refund"
                          >
                            Refund
                          </option>

                          <option
                            value="replacement"
                          >
                            Replacement
                          </option>
                        </select>
                      </label>

                      {approvalResolution
                        === "refund" && (
                        <label>
                          Refund amount

                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            value={
                              refundAmount
                            }
                            onChange={
                              (event) =>
                                setRefundAmount(
                                  event
                                    .target
                                    .value,
                                )
                            }
                          />
                        </label>
                      )}
                    </>
                  )}

                  <label>
                    Approval notes

                    <textarea
                      rows={4}
                      value={
                        approvalNotes
                      }
                      onChange={
                        (event) =>
                          setApprovalNotes(
                            event
                              .target
                              .value,
                          )
                      }
                    />
                  </label>
                </>
              )}


              {actionMode
                === "replacement" && (
                <>
                  <label>
                    Returned item

                    <select
                      value={
                        replacementReturnItemId
                      }
                      onChange={
                        (event) =>
                          setReplacementReturnItemId(
                            event
                              .target
                              .value,
                          )
                      }
                    >
                      {selected.items.map(
                        (item) => (
                          <option
                            key={
                              item.id
                            }
                            value={
                              item.id
                            }
                          >
                            Return item #
                            {item.id}
                            {" — Product #"}
                            {
                              item.product_id
                            }
                            {item.serial_number
                              ? (
                                  " — Serial: "
                                  + item.serial_number
                                )
                              : ""}
                          </option>
                        ),
                      )}
                    </select>
                  </label>

                  <label>
                    Search replacement product

                    <input
                      type="search"
                      placeholder="Search by product code or name..."
                      value={
                        replacementProductSearch
                      }
                      onChange={
                        (event) =>
                          setReplacementProductSearch(
                            event.target.value,
                          )
                      }
                      autoComplete="off"
                    />
                  </label>

                  <label>
                    Replacement product

                    <select
                      size={
                        replacementProductSearch
                          .trim()
                          ? Math.min(
                              Math.max(
                                products.filter(
                                  (product) => {
                                    const query =
                                      replacementProductSearch
                                        .trim()
                                        .toLowerCase();

                                    return (
                                      product
                                        .product_code
                                        .toLowerCase()
                                        .includes(
                                          query,
                                        )
                                      || product
                                        .name
                                        .toLowerCase()
                                        .includes(
                                          query,
                                        )
                                    );
                                  },
                                ).length,
                                2,
                              ),
                              8,
                            )
                          : 1
                      }
                      value={
                        replacementProductId
                      }
                      onChange={
                        (event) => {
                          const productId =
                            event
                              .target
                              .value;

                          setReplacementProductId(
                            productId,
                          );

                          void loadReplacementSerials(
                            productId,
                            replacementWarehouseId,
                          );
                        }
                      }
                    >
                      <option value="">
                        Select product
                      </option>

                      {products
                        .filter(
                          (product) => {
                            const query =
                              replacementProductSearch
                                .trim()
                                .toLowerCase();

                            if (!query) {
                              return true;
                            }

                            return (
                              product
                                .product_code
                                .toLowerCase()
                                .includes(
                                  query,
                                )
                              || product
                                .name
                                .toLowerCase()
                                .includes(
                                  query,
                                )
                            );
                          },
                        )
                        .map(
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
                    Warehouse

                    <select
                      value={
                        replacementWarehouseId
                      }
                      onChange={
                        (event) => {
                          const warehouseId =
                            event
                              .target
                              .value;

                          setReplacementWarehouseId(
                            warehouseId,
                          );

                          void loadReplacementSerials(
                            replacementProductId,
                            warehouseId,
                          );
                        }
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

                  {products.find(
                    (item) =>
                      String(
                        item.id,
                      )
                      === replacementProductId,
                  )?.track_serial_numbers && (
                    <label>
                      Replacement serial

                      <select
                        disabled={
                          serialLoading
                        }
                        value={
                          replacementSerialId
                        }
                        onChange={
                          (event) =>
                            setReplacementSerialId(
                              event
                                .target
                                .value,
                            )
                        }
                      >
                        <option value="">
                          {serialLoading
                            ? "Loading..."
                            : "Select serial"
                          }
                        </option>

                        {replacementSerials.map(
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
                  )}

                  <label>
                    Notes

                    <textarea
                      rows={3}
                      value={
                        replacementNotes
                      }
                      onChange={
                        (event) =>
                          setReplacementNotes(
                            event
                              .target
                              .value,
                          )
                      }
                    />
                  </label>
                </>
              )}


              {actionMode
                === "status" && (
                <>
                  <label>
                    New status

                    <select
                      value={
                        manualStatus
                      }
                      onChange={
                        (event) => {
                          const value =
                            event
                              .target
                              .value;

                          setManualStatus(
                            value
                            === "requested"
                              ? "requested"
                              : value
                                === "inspected"
                                ? "inspected"
                                : value
                                  === "approved"
                                  ? "approved"
                                  : value
                                    === "rejected"
                                    ? "rejected"
                                    : value
                                      === "completed"
                                      ? "completed"
                                      : "cancelled",
                          );
                        }
                      }
                    >
                      <option
                        value="cancelled"
                      >
                        Cancelled
                      </option>

                      <option
                        value="requested"
                      >
                        Requested
                      </option>

                      <option
                        value="inspected"
                      >
                        Inspected
                      </option>

                      <option
                        value="approved"
                      >
                        Approved
                      </option>

                      <option
                        value="rejected"
                      >
                        Rejected
                      </option>

                      <option
                        value="completed"
                      >
                        Completed
                      </option>
                    </select>
                  </label>

                  <label>
                    Remarks

                    <textarea
                      rows={4}
                      value={
                        statusRemarks
                      }
                      onChange={
                        (event) =>
                          setStatusRemarks(
                            event
                              .target
                              .value,
                          )
                      }
                    />
                  </label>
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
                  actionLoading
                }
                onClick={() =>
                  setActionMode(
                    null,
                  )
                }
              >
                Cancel
              </button>

              {actionMode
                === "inspect" && (
                <button
                  type="button"
                  className={
                    styles.primaryButton
                  }
                  disabled={
                    actionLoading
                  }
                  onClick={() =>
                    void submitInspection()
                  }
                >
                  Confirm inspection
                </button>
              )}

              {actionMode
                === "approve" && (
                <button
                  type="button"
                  className={
                    styles.primaryButton
                  }
                  disabled={
                    actionLoading
                  }
                  onClick={() =>
                    void submitApproval(
                      true,
                    )
                  }
                >
                  <Check size={16} />

                  Approve
                </button>
              )}

              {actionMode
                === "reject" && (
                <button
                  type="button"
                  className={
                    styles.dangerButton
                  }
                  disabled={
                    actionLoading
                  }
                  onClick={() =>
                    void submitApproval(
                      false,
                    )
                  }
                >
                  Reject
                </button>
              )}

              {actionMode
                === "replacement" && (
                <button
                  type="button"
                  className={
                    styles.primaryButton
                  }
                  disabled={
                    actionLoading
                  }
                  onClick={() =>
                    void submitReplacement()
                  }
                >
                  Set replacement
                </button>
              )}

              {actionMode
                === "status" && (
                <button
                  type="button"
                  className={
                    styles.primaryButton
                  }
                  disabled={
                    actionLoading
                  }
                  onClick={() =>
                    void submitStatusChange()
                  }
                >
                  Update status
                </button>
              )}
            </footer>
          </section>
        </div>
      )}
    </AppShell>
  );
}
