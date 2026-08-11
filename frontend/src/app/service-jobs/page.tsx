"use client";

import axios from "axios";

import {
  BadgeCheck,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  ClipboardList,
  Eye,
  FileText,
  Loader2,
  PackagePlus,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  Wrench,
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
  getSalesCustomers,
  getSalesProducts,
  getSalesWarehouses,
} from "@/lib/sales-api";

import {
  addServiceLabour,
  addServicePart,
  createServiceInvoice,
  createServiceJob,
  getServiceJob,
  getServiceJobs,
  updateServiceApproval,
  updateServiceJob,
  updateServiceStatus,
} from "@/lib/service-jobs-api";

import {
  canAddServiceLabour,
  canAddServicePart,
  canChangeServiceStatus,
  canCreateServiceInvoice,
  canEditServiceJob,
  canManageServiceApproval,
  getValidServiceNextStatuses,
  requiresTestingResult,
  serviceWorkflowMessage,
} from "@/lib/service-job-workflow";


import type {
  UserResponse,
} from "@/types/auth";

import type {
  SalesCustomerOption,
  SalesProductOption,
  SalesWarehouseOption,
} from "@/types/sales";

import type {
  ApprovalStatus,
  ServiceJobCreate,
  ServiceJobDetailResponse,
  ServiceJobPriority,
  ServiceJobStatus,
  ServiceJobUpdate,
  ServiceType,
} from "@/types/service-jobs";

import styles from "./service-jobs.module.css";


const PAGE_SIZE = 20;


const EMPTY_CREATE:
ServiceJobCreate = {
  customer_id: 0,

  product_id:
    null,

  sold_serial_id:
    null,

  serial_number:
    null,

  secondary_serial_number:
    null,

  brand_name:
    null,

  model_number:
    null,

  item_color:
    null,

  service_type:
    "repair",

  priority:
    "normal",

  complaint:
    "",

  reported_issue:
    null,

  accessories_received:
    null,

  physical_condition:
    null,

  special_notes:
    null,

  technician_id:
    null,

  receiving_officer_id:
    null,

  is_warranty_job:
    false,

  related_invoice_id:
    null,

  estimated_cost:
    "0.00",

  expected_completion_date:
    null,
};


function numberValue(
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
      style:
        "currency",

      currency:
        "LKR",

      minimumFractionDigits:
        2,
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

  const parsed =
    new Date(value);

  if (
    Number.isNaN(
      parsed.getTime(),
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
  ).format(parsed);
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
  value:
    string,
): string | null {
  const result =
    value.trim();

  return (
    result.length > 0
      ? result
      : null
  );
}


function optionalPositiveId(
  value:
    string,
): number | null {
  if (!value) {
    return null;
  }

  const parsed =
    Number(value);

  return (
    Number.isInteger(parsed)
    && parsed > 0
      ? parsed
      : null
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
      + "for this service operation."
    );
  }

  return (
    "Unable to complete "
    + "the service operation."
  );
}


function asPriority(
  value:
    string,
): ServiceJobPriority {
  if (value === "low") {
    return "low";
  }

  if (value === "high") {
    return "high";
  }

  if (value === "urgent") {
    return "urgent";
  }

  return "normal";
}


function asServiceType(
  value:
    string,
): ServiceType {
  if (value === "warranty") {
    return "warranty";
  }

  if (
    value
    === "installation"
  ) {
    return "installation";
  }

  if (
    value
    === "maintenance"
  ) {
    return "maintenance";
  }

  if (
    value
    === "inspection"
  ) {
    return "inspection";
  }

  if (value === "other") {
    return "other";
  }

  return "repair";
}


function asStatus(
  value:
    string,
): ServiceJobStatus {
  const allowed:
    ServiceJobStatus[] = [
      "received",
      "inspection",
      "waiting_approval",
      "approved",
      "repairing",
      "testing",
      "ready",
      "delivered",
      "cancelled",
    ];

  return (
    allowed.find(
      (item) =>
        item === value,
    )
    ?? "received"
  );
}


function asApproval(
  value:
    string,
): ApprovalStatus {
  if (
    value
    === "pending"
  ) {
    return "pending";
  }

  if (
    value
    === "approved"
  ) {
    return "approved";
  }

  if (
    value
    === "rejected"
  ) {
    return "rejected";
  }

  return "not_required";
}


export default function ServiceJobsPage() {
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
    jobs,
    setJobs,
  ] =
    useState<
      ServiceJobDetailResponse[]
    >(
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
    useState("");

  const [
    typeFilter,
    setTypeFilter,
  ] =
    useState("");

  const [
    priorityFilter,
    setPriorityFilter,
  ] =
    useState("");

  const [
    warrantyOnly,
    setWarrantyOnly,
  ] =
    useState(false);


  const [
    selected,
    setSelected,
  ] =
    useState<
      ServiceJobDetailResponse
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
    createOpen,
    setCreateOpen,
  ] =
    useState(false);

  const [
    createForm,
    setCreateForm,
  ] =
    useState<ServiceJobCreate>(
      EMPTY_CREATE,
    );


  const [
    actionMode,
    setActionMode,
  ] =
    useState<
      | "edit"
      | "status"
      | "approval"
      | "labour"
      | "part"
      | "invoice"
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
    editTechnicianId,
    setEditTechnicianId,
  ] =
    useState("");

  const [
    editDiagnosis,
    setEditDiagnosis,
  ] =
    useState("");

  const [
    editWorkPerformed,
    setEditWorkPerformed,
  ] =
    useState("");

  const [
    editTestingResult,
    setEditTestingResult,
  ] =
    useState("");

  const [
    editWarrantyNotes,
    setEditWarrantyNotes,
  ] =
    useState("");

  const [
    editEstimatedCost,
    setEditEstimatedCost,
  ] =
    useState("0.00");

  const [
    editDiscount,
    setEditDiscount,
  ] =
    useState("0.00");

  const [
    editExpectedDate,
    setEditExpectedDate,
  ] =
    useState("");


  const [
    nextStatus,
    setNextStatus,
  ] =
    useState<ServiceJobStatus>(
      "inspection",
    );

  const [
    statusRemarks,
    setStatusRemarks,
  ] =
    useState("");


  const [
    approvalStatus,
    setApprovalStatus,
  ] =
    useState<ApprovalStatus>(
      "approved",
    );

  const [
    approvalRemarks,
    setApprovalRemarks,
  ] =
    useState("");


  const [
    labourDescription,
    setLabourDescription,
  ] =
    useState("");

  const [
    labourHours,
    setLabourHours,
  ] =
    useState("0.00");

  const [
    labourAmount,
    setLabourAmount,
  ] =
    useState("0.00");

  const [
    labourNotes,
    setLabourNotes,
  ] =
    useState("");


  const [
    partProductId,
    setPartProductId,
  ] =
    useState("");

  const [
    partWarehouseId,
    setPartWarehouseId,
  ] =
    useState("");

  const [
    partQuantity,
    setPartQuantity,
  ] =
    useState("1.000");

  const [
    partUnitPrice,
    setPartUnitPrice,
  ] =
    useState("");

  const [
    partNotes,
    setPartNotes,
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


  const loadJobs =
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
            await getServiceJobs({
              page,

              pageSize:
                PAGE_SIZE,

              search:
                search
                || undefined,

              jobStatus:
                statusFilter
                  ? asStatus(
                      statusFilter,
                    )
                  : "",

              serviceType:
                typeFilter
                  ? asServiceType(
                      typeFilter,
                    )
                  : "",

              priority:
                priorityFilter
                  ? asPriority(
                      priorityFilter,
                    )
                  : "",

              warrantyOnly,
            });

          setJobs(
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
        typeFilter,
        priorityFilter,
        warrantyOnly,
      ],
    );


  useEffect(() => {
    if (authLoading) {
      return;
    }

    const timer =
      window.setTimeout(
        () => {
          void loadJobs();
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
    loadJobs,
  ]);


  const summary =
    useMemo(
      () => ({
        received:
          jobs.filter(
            (job) =>
              job.status
              === "received",
          ).length,

        active:
          jobs.filter(
            (job) =>
              ![
                "delivered",
                "cancelled",
              ].includes(
                job.status,
              ),
          ).length,

        ready:
          jobs.filter(
            (job) =>
              job.status
              === "ready",
          ).length,
      }),
      [jobs],
    );


  async function loadLookups() {
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
  }


  async function openCreate() {
    setError("");

    try {
      await loadLookups();
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

    setCreateForm({
      ...EMPTY_CREATE,
    });

    setCreateOpen(
      true,
    );
  }


  async function openDetail(
    jobId:
      number,
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
      const detail =
        await getServiceJob(
          jobId,
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


  async function refreshDetail(
    jobId:
      number,
  ) {
    const detail =
      await getServiceJob(
        jobId,
      );

    setSelected(
      detail,
    );

    return detail;
  }


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


  async function submitCreate(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (
      createForm.customer_id
      <= 0
    ) {
      setError(
        "Select a customer.",
      );

      return;
    }

    if (
      createForm.complaint
        .trim()
        .length < 3
    ) {
      setError(
        "Complaint must contain "
        + "at least 3 characters.",
      );

      return;
    }

    setActionLoading(
      true,
    );

    setError("");

    try {
      const created =
        await createServiceJob({
          ...createForm,

          complaint:
            createForm
              .complaint
              .trim(),
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

      await loadJobs(
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


  function openEdit() {
    if (!selected) {
      return;
    }

    setEditTechnicianId(
      selected.technician_id
        ? String(
            selected
              .technician_id,
          )
        : "",
    );

    setEditDiagnosis(
      selected
        .technician_diagnosis
      ?? "",
    );

    setEditWorkPerformed(
      selected
        .work_performed
      ?? "",
    );

    setEditTestingResult(
      selected
        .testing_result
      ?? "",
    );

    setEditWarrantyNotes(
      selected
        .warranty_notes
      ?? "",
    );

    setEditEstimatedCost(
      selected
        .estimated_cost,
    );

    setEditDiscount(
      selected
        .discount_amount,
    );

    setEditExpectedDate(
      selected
        .expected_completion_date
      ?? "",
    );

    setActionMode(
      "edit",
    );
  }


  async function submitEdit() {
    if (!selected) {
      return;
    }

    const payload:
      ServiceJobUpdate = {
      technician_id:
        optionalPositiveId(
          editTechnicianId,
        ),

      technician_diagnosis:
        optionalText(
          editDiagnosis,
        ),

      work_performed:
        optionalText(
          editWorkPerformed,
        ),

      testing_result:
        optionalText(
          editTestingResult,
        ),

      warranty_notes:
        optionalText(
          editWarrantyNotes,
        ),

      estimated_cost:
        numberValue(
          editEstimatedCost,
        ).toFixed(2),

      discount_amount:
        numberValue(
          editDiscount,
        ).toFixed(2),

      expected_completion_date:
        optionalText(
          editExpectedDate,
        ),
    };

    setActionLoading(
      true,
    );

    setError("");

    try {
      const result =
        await updateServiceJob(
          selected.id,
          payload,
        );

      setSelected(
        result,
      );

      setActionMode(
        null,
      );

      await loadJobs(
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


  function openStatus() {
    if (!selected) {
      return;
    }

    const validNext =
      getValidServiceNextStatuses(
        asStatus(
          selected.status,
        ),
      );

    setNextStatus(
      validNext[0]
      ?? asStatus(
        selected.status,
      ),
    );

    setStatusRemarks(
      "",
    );

    setActionMode(
      "status",
    );
  }


  async function submitStatus() {
    if (!selected) {
      return;
    }

    const currentStatus =
      asStatus(
        selected.status,
      );

    if (
      !canChangeServiceStatus(
        currentStatus,
        nextStatus,
      )
    ) {
      setError(
        "That status transition is "
        + "not allowed from "
        + readable(
            currentStatus,
          )
        + ".",
      );

      return;
    }

    if (
      requiresTestingResult(
        nextStatus,
      )
      && !selected
        .testing_result
        ?.trim()
    ) {
      setError(
        "Enter the testing result "
        + "before marking this job Ready.",
      );

      return;
    }

    setActionLoading(
      true,
    );

    setError("");

    try {
      const result =
        await updateServiceStatus(
          selected.id,
          {
            new_status:
              nextStatus,

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

      await loadJobs(
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


  function openApproval() {
    if (!selected) {
      return;
    }

    setApprovalStatus(
      selected.approval_status
      === "rejected"
        ? "rejected"
        : "approved",
    );

    setApprovalRemarks(
      "",
    );

    setActionMode(
      "approval",
    );
  }


  async function submitApproval() {
    if (!selected) {
      return;
    }

    setActionLoading(
      true,
    );

    setError("");

    try {
      const result =
        await updateServiceApproval(
          selected.id,
          {
            approval_status:
              approvalStatus,

            remarks:
              optionalText(
                approvalRemarks,
              ),
          },
        );

      setSelected(
        result,
      );

      setActionMode(
        null,
      );

      await loadJobs(
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


  function openLabour() {
    setLabourDescription(
      "",
    );

    setLabourHours(
      "0.00",
    );

    setLabourAmount(
      "0.00",
    );

    setLabourNotes(
      "",
    );

    setActionMode(
      "labour",
    );
  }


  async function submitLabour() {
    if (!selected) {
      return;
    }

    if (
      labourDescription
        .trim()
        .length < 2
    ) {
      setError(
        "Labour description is required.",
      );

      return;
    }

    if (
      numberValue(
        labourAmount,
      ) < 0
    ) {
      setError(
        "Labour amount cannot be negative.",
      );

      return;
    }

    setActionLoading(
      true,
    );

    setError("");

    try {
      const result =
        await addServiceLabour(
          selected.id,
          {
            description:
              labourDescription
                .trim(),

            hours:
              numberValue(
                labourHours,
              ).toFixed(2),

            amount:
              numberValue(
                labourAmount,
              ).toFixed(2),

            notes:
              optionalText(
                labourNotes,
              ),
          },
        );

      setSelected(
        result,
      );

      setActionMode(
        null,
      );

      await loadJobs(
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


  async function openPart() {
    setError("");

    try {
      if (
        products.length === 0
        || warehouses.length === 0
      ) {
        await loadLookups();
      }
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

    setPartProductId(
      "",
    );

    setPartWarehouseId(
      "",
    );

    setPartQuantity(
      "1.000",
    );

    setPartUnitPrice(
      "",
    );

    setPartNotes(
      "",
    );

    setActionMode(
      "part",
    );
  }


  async function submitPart() {
    if (!selected) {
      return;
    }

    const productId =
      optionalPositiveId(
        partProductId,
      );

    const warehouseId =
      optionalPositiveId(
        partWarehouseId,
      );

    if (
      !productId
      || !warehouseId
    ) {
      setError(
        "Select product and warehouse.",
      );

      return;
    }

    if (
      numberValue(
        partQuantity,
      ) <= 0
    ) {
      setError(
        "Part quantity must be "
        + "greater than zero.",
      );

      return;
    }

    setActionLoading(
      true,
    );

    setError("");

    try {
      const result =
        await addServicePart(
          selected.id,
          {
            product_id:
              productId,

            warehouse_id:
              warehouseId,

            quantity:
              numberValue(
                partQuantity,
              ).toFixed(3),

            unit_price:
              partUnitPrice
                ? numberValue(
                    partUnitPrice,
                  ).toFixed(2)
                : null,

            notes:
              optionalText(
                partNotes,
              ),
          },
        );

      setSelected(
        result,
      );

      setActionMode(
        null,
      );

      await loadJobs(
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


  async function submitInvoice() {
    if (!selected) {
      return;
    }

    setActionLoading(
      true,
    );

    setError("");

    try {
      await createServiceInvoice(
        selected.id,
      );

      await refreshDetail(
        selected.id,
      );

      setActionMode(
        null,
      );

      await loadJobs(
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
            SERVICE
          </p>

          <h1>
            Service Jobs
          </h1>

          <p>
            Receive repair jobs,
            manage technician work,
            parts, labour, approvals,
            testing and customer delivery.
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

            New service job
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
              void loadJobs(
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
          <ClipboardList
            size={20}
          />

          <div>
            <span>
              Service jobs
            </span>

            <strong>
              {total}
            </strong>
          </div>
        </article>

        <article>
          <Wrench size={20} />

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
          <PackagePlus
            size={20}
          />

          <div>
            <span>
              Received
            </span>

            <strong>
              {summary.received}
            </strong>
          </div>
        </article>

        <article>
          <BadgeCheck
            size={20}
          />

          <div>
            <span>
              Ready
            </span>

            <strong>
              {summary.ready}
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
          <Search size={16} />

          <input
            value={
              searchInput
            }
            placeholder={
              "Job number, customer, phone, serial..."
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
                  .value,
              );
            }
          }
        >
          <option value="">
            All statuses
          </option>

          {[
            "received",
            "inspection",
            "waiting_approval",
            "approved",
            "repairing",
            "testing",
            "ready",
            "delivered",
            "cancelled",
          ].map(
            (value) => (
              <option
                key={value}
                value={value}
              >
                {readable(
                  value,
                )}
              </option>
            ),
          )}
        </select>

        <select
          value={
            typeFilter
          }
          onChange={
            (event) => {
              setPage(1);

              setTypeFilter(
                event
                  .target
                  .value,
              );
            }
          }
        >
          <option value="">
            All service types
          </option>

          {[
            "repair",
            "warranty",
            "installation",
            "maintenance",
            "inspection",
            "other",
          ].map(
            (value) => (
              <option
                key={value}
                value={value}
              >
                {readable(
                  value,
                )}
              </option>
            ),
          )}
        </select>

        <select
          value={
            priorityFilter
          }
          onChange={
            (event) => {
              setPage(1);

              setPriorityFilter(
                event
                  .target
                  .value,
              );
            }
          }
        >
          <option value="">
            All priorities
          </option>

          <option value="low">
            Low
          </option>

          <option value="normal">
            Normal
          </option>

          <option value="high">
            High
          </option>

          <option value="urgent">
            Urgent
          </option>
        </select>

        <label
          className={
            styles.checkFilter
          }
        >
          <input
            type="checkbox"
            checked={
              warrantyOnly
            }
            onChange={
              (event) => {
                setPage(1);

                setWarrantyOnly(
                  event
                    .target
                    .checked,
                );
              }
            }
          />

          Warranty only
        </label>
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
              size={23}
              className={
                styles.spin
              }
            />

            Loading service jobs...
          </div>
        ) : jobs.length === 0 ? (
          <div
            className={
              styles.emptyState
            }
          >
            <Wrench size={29} />

            <strong>
              No service jobs found
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
                    Job
                  </th>

                  <th>
                    Customer
                  </th>

                  <th>
                    Item
                  </th>

                  <th>
                    Type
                  </th>

                  <th>
                    Priority
                  </th>

                  <th>
                    Status
                  </th>

                  <th>
                    Amount
                  </th>

                  <th />
                </tr>
              </thead>

              <tbody>
                {jobs.map(
                  (job) => (
                    <tr
                      key={job.id}
                    >
                      <td>
                        <strong>
                          {
                            job
                              .job_number
                          }
                        </strong>

                        <small>
                          {dateTime(
                            job.received_at,
                          )}
                        </small>
                      </td>

                      <td>
                        <strong>
                          {
                            job
                              .customer_name
                          }
                        </strong>

                        <small>
                          {
                            job
                              .customer_phone
                          }
                        </small>
                      </td>

                      <td>
                        <span>
                          {job.product_name
                            || job.brand_name
                            || "Uncatalogued item"
                          }
                        </span>

                        <small>
                          {job.serial_number
                            || job.model_number
                            || "—"
                          }
                        </small>
                      </td>

                      <td>
                        {readable(
                          job.service_type,
                        )}
                      </td>

                      <td>
                        <span
                          className={
                            styles.priorityBadge
                          }
                        >
                          {readable(
                            job.priority,
                          )}
                        </span>
                      </td>

                      <td>
                        <span
                          className={
                            styles.statusBadge
                          }
                        >
                          {readable(
                            job.status,
                          )}
                        </span>
                      </td>

                      <td>
                        <strong>
                          {money(
                            job.final_amount,
                          )}
                        </strong>
                      </td>

                      <td>
                        <button
                          type="button"
                          className={
                            styles.iconButton
                          }
                          onClick={() =>
                            void openDetail(
                              job.id,
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
            Page {page}
            {" of "}
            {Math.max(
              1,
              totalPages,
            )}
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
      </section>


      {createOpen && (
        <div
          className={
            styles.backdrop
          }
        >
          <form
            className={
              styles.largeModal
            }
            onSubmit={
              submitCreate
            }
          >
            <header
              className={
                styles.modalHeader
              }
            >
              <div>
                <p className="eyebrow">
                  SERVICE INTAKE
                </p>

                <h2>
                  New service job
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
              <section
                className={
                  styles.formSection
                }
              >
                <h3>
                  Customer & item
                </h3>

                <div
                  className={
                    styles.formGrid
                  }
                >
                  <label>
                    Customer *

                    <select
                      required
                      value={
                        createForm
                          .customer_id
                      }
                      onChange={
                        (event) =>
                          setCreateForm({
                            ...createForm,

                            customer_id:
                              Number(
                                event
                                  .target
                                  .value,
                              ),
                          })
                      }
                    >
                      <option value={0}>
                        Select customer
                      </option>

                      {customers.map(
                        (customer) => (
                          <option
                            key={
                              customer.id
                            }
                            value={
                              customer.id
                            }
                          >
                            {"#"}
                            {
                              customer.id
                            }
                            {" — "}
                            {
                              customer
                                .full_name
                            }
                          </option>
                        ),
                      )}
                    </select>
                  </label>

                  <label>
                    Catalog product

                    <select
                      value={
                        createForm
                          .product_id
                        ?? ""
                      }
                      onChange={
                        (event) => {
                          const value =
                            optionalPositiveId(
                              event
                                .target
                                .value,
                            );

                          setCreateForm({
                            ...createForm,

                            product_id:
                              value,
                          });
                        }
                      }
                    >
                      <option value="">
                        Uncatalogued item
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
                    Serial number

                    <input
                      maxLength={150}
                      value={
                        createForm
                          .serial_number
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setCreateForm({
                            ...createForm,

                            serial_number:
                              optionalText(
                                event
                                  .target
                                  .value,
                              ),
                          })
                      }
                    />
                  </label>

                  <label>
                    Secondary serial

                    <input
                      maxLength={150}
                      value={
                        createForm
                          .secondary_serial_number
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setCreateForm({
                            ...createForm,

                            secondary_serial_number:
                              optionalText(
                                event
                                  .target
                                  .value,
                              ),
                          })
                      }
                    />
                  </label>

                  <label>
                    Brand

                    <input
                      maxLength={120}
                      value={
                        createForm
                          .brand_name
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setCreateForm({
                            ...createForm,

                            brand_name:
                              optionalText(
                                event
                                  .target
                                  .value,
                              ),
                          })
                      }
                    />
                  </label>

                  <label>
                    Model

                    <input
                      maxLength={120}
                      value={
                        createForm
                          .model_number
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setCreateForm({
                            ...createForm,

                            model_number:
                              optionalText(
                                event
                                  .target
                                  .value,
                              ),
                          })
                      }
                    />
                  </label>

                  <label>
                    Colour

                    <input
                      maxLength={80}
                      value={
                        createForm
                          .item_color
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setCreateForm({
                            ...createForm,

                            item_color:
                              optionalText(
                                event
                                  .target
                                  .value,
                              ),
                          })
                      }
                    />
                  </label>
                </div>
              </section>


              <section
                className={
                  styles.formSection
                }
              >
                <h3>
                  Service request
                </h3>

                <div
                  className={
                    styles.formGrid
                  }
                >
                  <label>
                    Service type

                    <select
                      value={
                        createForm
                          .service_type
                      }
                      onChange={
                        (event) =>
                          setCreateForm({
                            ...createForm,

                            service_type:
                              asServiceType(
                                event
                                  .target
                                  .value,
                              ),
                          })
                      }
                    >
                      <option value="repair">
                        Repair
                      </option>

                      <option value="warranty">
                        Warranty
                      </option>

                      <option value="installation">
                        Installation
                      </option>

                      <option value="maintenance">
                        Maintenance
                      </option>

                      <option value="inspection">
                        Inspection
                      </option>

                      <option value="other">
                        Other
                      </option>
                    </select>
                  </label>

                  <label>
                    Priority

                    <select
                      value={
                        createForm
                          .priority
                      }
                      onChange={
                        (event) =>
                          setCreateForm({
                            ...createForm,

                            priority:
                              asPriority(
                                event
                                  .target
                                  .value,
                              ),
                          })
                      }
                    >
                      <option value="low">
                        Low
                      </option>

                      <option value="normal">
                        Normal
                      </option>

                      <option value="high">
                        High
                      </option>

                      <option value="urgent">
                        Urgent
                      </option>
                    </select>
                  </label>

                  <label>
                    Estimated cost

                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={
                        createForm
                          .estimated_cost
                      }
                      onChange={
                        (event) =>
                          setCreateForm({
                            ...createForm,

                            estimated_cost:
                              event
                                .target
                                .value,
                          })
                      }
                    />
                  </label>

                  <label>
                    Expected completion

                    <input
                      type="date"
                      value={
                        createForm
                          .expected_completion_date
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setCreateForm({
                            ...createForm,

                            expected_completion_date:
                              optionalText(
                                event
                                  .target
                                  .value,
                              ),
                          })
                      }
                    />
                  </label>

                  <label>
                    Technician ID

                    <input
                      type="number"
                      min="1"
                      value={
                        createForm
                          .technician_id
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setCreateForm({
                            ...createForm,

                            technician_id:
                              optionalPositiveId(
                                event
                                  .target
                                  .value,
                              ),
                          })
                      }
                    />
                  </label>

                  <label>
                    Related invoice ID

                    <input
                      type="number"
                      min="1"
                      value={
                        createForm
                          .related_invoice_id
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setCreateForm({
                            ...createForm,

                            related_invoice_id:
                              optionalPositiveId(
                                event
                                  .target
                                  .value,
                              ),
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
                        createForm
                          .is_warranty_job
                      }
                      onChange={
                        (event) =>
                          setCreateForm({
                            ...createForm,

                            is_warranty_job:
                              event
                                .target
                                .checked,
                          })
                      }
                    />

                    Warranty job
                  </label>

                  <label
                    className={
                      styles.fullField
                    }
                  >
                    Complaint *

                    <textarea
                      required
                      minLength={3}
                      maxLength={5000}
                      rows={4}
                      value={
                        createForm
                          .complaint
                      }
                      onChange={
                        (event) =>
                          setCreateForm({
                            ...createForm,

                            complaint:
                              event
                                .target
                                .value,
                          })
                      }
                    />
                  </label>

                  <label
                    className={
                      styles.fullField
                    }
                  >
                    Reported issue

                    <textarea
                      rows={3}
                      value={
                        createForm
                          .reported_issue
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setCreateForm({
                            ...createForm,

                            reported_issue:
                              optionalText(
                                event
                                  .target
                                  .value,
                              ),
                          })
                      }
                    />
                  </label>

                  <label>
                    Accessories received

                    <textarea
                      rows={3}
                      value={
                        createForm
                          .accessories_received
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setCreateForm({
                            ...createForm,

                            accessories_received:
                              optionalText(
                                event
                                  .target
                                  .value,
                              ),
                          })
                      }
                    />
                  </label>

                  <label>
                    Physical condition

                    <textarea
                      rows={3}
                      value={
                        createForm
                          .physical_condition
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setCreateForm({
                            ...createForm,

                            physical_condition:
                              optionalText(
                                event
                                  .target
                                  .value,
                              ),
                          })
                      }
                    />
                  </label>

                  <label
                    className={
                      styles.fullField
                    }
                  >
                    Special notes

                    <textarea
                      rows={3}
                      value={
                        createForm
                          .special_notes
                        ?? ""
                      }
                      onChange={
                        (event) =>
                          setCreateForm({
                            ...createForm,

                            special_notes:
                              optionalText(
                                event
                                  .target
                                  .value,
                              ),
                          })
                      }
                    />
                  </label>
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
                  actionLoading
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
                type="submit"
                className={
                  styles.primaryButton
                }
                disabled={
                  actionLoading
                }
              >
                {actionLoading
                  ? "Creating..."
                  : "Create service job"
                }
              </button>
            </footer>
          </form>
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
                  SERVICE JOB
                </p>

                <h2>
                  {selected
                    ?.job_number
                    ?? "Service job"
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
                  className={
                    styles.spin
                  }
                  size={22}
                />

                Loading job...
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
                      styles.heroGrid
                    }
                  >
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

                      <small>
                        {
                          selected
                            .customer_phone
                        }
                      </small>
                    </div>

                    <div>
                      <span>
                        Item
                      </span>

                      <strong>
                        {selected.product_name
                          || selected.brand_name
                          || "Uncatalogued"
                        }
                      </strong>

                      <small>
                        {selected.serial_number
                          || selected.model_number
                          || "—"
                        }
                      </small>
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
                        Service
                      </span>

                      <strong>
                        {readable(
                          selected
                            .service_type,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Priority
                      </span>

                      <strong>
                        {readable(
                          selected.priority,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Approval
                      </span>

                      <strong>
                        {readable(
                          selected
                            .approval_status,
                        )}
                      </strong>
                    </div>
                  </section>


                  <section
                    className={
                      styles.financeGrid
                    }
                  >
                    <div>
                      <span>
                        Estimate
                      </span>

                      <strong>
                        {money(
                          selected
                            .estimated_cost,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Labour
                      </span>

                      <strong>
                        {money(
                          selected
                            .labour_total,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Parts
                      </span>

                      <strong>
                        {money(
                          selected
                            .parts_total,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Discount
                      </span>

                      <strong>
                        {money(
                          selected
                            .discount_amount,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Final amount
                      </span>

                      <strong>
                        {money(
                          selected
                            .final_amount,
                        )}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Invoice
                      </span>

                      <strong>
                        {selected
                          .related_invoice_id
                          ? `#${selected.related_invoice_id}`
                          : "Not created"
                        }
                      </strong>
                    </div>
                  </section>


                  <section
                    className={
                      styles.workflowCard
                    }
                  >
                    <div
                      className={
                        styles.workflowTitle
                      }
                    >
                      <Wrench
                        size={16}
                      />

                      <div>
                        <strong>
                          Workflow guidance
                        </strong>

                        <p>
                          {serviceWorkflowMessage(
                            asStatus(
                              selected.status,
                            ),
                          )}
                        </p>
                      </div>
                    </div>

                    <div
                      className={
                        styles.workflowMeta
                      }
                    >
                      <div>
                        <span>
                          Next allowed statuses
                        </span>

                        <strong>
                          {getValidServiceNextStatuses(
                            asStatus(
                              selected.status,
                            ),
                          ).length > 0
                            ? getValidServiceNextStatuses(
                                asStatus(
                                  selected.status,
                                ),
                              )
                                .map(
                                  readable,
                                )
                                .join(", ")
                            : "No further transitions"
                          }
                        </strong>
                      </div>

                      <div>
                        <span>
                          Labour
                        </span>

                        <strong>
                          {canAddServiceLabour(
                            asStatus(
                              selected.status,
                            ),
                          )
                            ? "Allowed"
                            : "Locked"
                          }
                        </strong>
                      </div>

                      <div>
                        <span>
                          Parts
                        </span>

                        <strong>
                          {canAddServicePart(
                            asStatus(
                              selected.status,
                            ),
                          )
                            ? "Allowed"
                            : "Locked"
                          }
                        </strong>
                      </div>

                      <div>
                        <span>
                          Warranty
                        </span>

                        <strong>
                          {!selected
                            .is_warranty_job
                            ? "Not a warranty job"
                            : selected
                                .warranty_verified
                              ? "Verified"
                              : "Manual verification"
                          }
                        </strong>
                      </div>
                    </div>

                    {selected
                      .is_warranty_job
                      && selected
                        .warranty_notes && (
                      <p
                        className={
                          styles.workflowNote
                        }
                      >
                        {
                          selected
                            .warranty_notes
                        }
                      </p>
                    )}
                  </section>


                  <section
                    className={
                      styles.detailSection
                    }
                  >
                    <h3>
                      Customer complaint
                    </h3>

                    <p>
                      {
                        selected
                          .complaint
                      }
                    </p>

                    {selected
                      .reported_issue && (
                      <p>
                        <strong>
                          Reported:
                        </strong>
                        {" "}
                        {
                          selected
                            .reported_issue
                        }
                      </p>
                    )}
                  </section>


                  <section
                    className={
                      styles.detailSection
                    }
                  >
                    <div
                      className={
                        styles.sectionHeader
                      }
                    >
                      <h3>
                        Technician work
                      </h3>

                      {canEditServiceJob(
                        asStatus(
                          selected.status,
                        ),
                      ) && (
                        <button
                          type="button"
                          className={
                            styles.smallButton
                          }
                          onClick={
                            openEdit
                          }
                        >
                          <Pencil
                            size={14}
                          />

                          Edit
                        </button>
                      )}
                    </div>

                    <div
                      className={
                        styles.notesGrid
                      }
                    >
                      <div>
                        <span>
                          Technician
                        </span>

                        <strong>
                          {selected
                            .technician_name
                            || (
                              selected
                                .technician_id
                                ? `User #${selected.technician_id}`
                                : "Not assigned"
                            )}
                        </strong>
                      </div>

                      <div>
                        <span>
                          Diagnosis
                        </span>

                        <strong>
                          {selected
                            .technician_diagnosis
                            || "—"}
                        </strong>
                      </div>

                      <div>
                        <span>
                          Work performed
                        </span>

                        <strong>
                          {selected
                            .work_performed
                            || "—"}
                        </strong>
                      </div>

                      <div>
                        <span>
                          Testing result
                        </span>

                        <strong>
                          {selected
                            .testing_result
                            || "—"}
                        </strong>
                      </div>
                    </div>
                  </section>


                  <section
                    className={
                      styles.detailSection
                    }
                  >
                    <div
                      className={
                        styles.sectionHeader
                      }
                    >
                      <h3>
                        Labour
                      </h3>

                      {canAddServiceLabour(
                        asStatus(
                          selected.status,
                        ),
                      ) && (
                        <button
                          type="button"
                          className={
                            styles.smallButton
                          }
                          onClick={
                            openLabour
                          }
                        >
                          <Plus
                            size={14}
                          />

                          Add labour
                        </button>
                      )}
                    </div>

                    {selected
                      .labour_items.length
                      === 0 ? (
                      <p
                        className={
                          styles.muted
                        }
                      >
                        No labour added.
                      </p>
                    ) : (
                      selected
                        .labour_items
                        .map(
                          (labour) => (
                            <article
                              key={
                                labour.id
                              }
                              className={
                                styles.lineCard
                              }
                            >
                              <div>
                                <strong>
                                  {
                                    labour
                                      .description
                                  }
                                </strong>

                                <small>
                                  {
                                    labour.hours
                                  }
                                  {" hours"}
                                </small>
                              </div>

                              <strong>
                                {money(
                                  labour
                                    .amount,
                                )}
                              </strong>
                            </article>
                          ),
                        )
                    )}
                  </section>


                  <section
                    className={
                      styles.detailSection
                    }
                  >
                    <div
                      className={
                        styles.sectionHeader
                      }
                    >
                      <h3>
                        Parts
                      </h3>

                      {canAddServicePart(
                        asStatus(
                          selected.status,
                        ),
                      ) && (
                        <button
                          type="button"
                          className={
                            styles.smallButton
                          }
                          onClick={() =>
                            void openPart()
                          }
                        >
                          <Plus
                            size={14}
                          />

                          Add part
                        </button>
                      )}
                    </div>

                    {selected.parts.length
                      === 0 ? (
                      <p
                        className={
                          styles.muted
                        }
                      >
                        No parts issued.
                      </p>
                    ) : (
                      selected.parts.map(
                        (part) => (
                          <article
                            key={
                              part.id
                            }
                            className={
                              styles.lineCard
                            }
                          >
                            <div>
                              <strong>
                                Product #
                                {
                                  part
                                    .product_id
                                }
                              </strong>

                              <small>
                                Qty{" "}
                                {
                                  part
                                    .quantity
                                }
                                {" • Warehouse #"}
                                {
                                  part
                                    .warehouse_id
                                }
                              </small>
                            </div>

                            <strong>
                              {money(
                                part
                                  .line_total,
                              )}
                            </strong>
                          </article>
                        ),
                      )
                    )}
                  </section>


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

                              <small>
                                {history
                                  .remarks
                                  || "No remarks"
                                }
                              </small>
                            </div>

                            <span>
                              {dateTime(
                                history
                                  .created_at,
                              )}
                            </span>
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
                  {getValidServiceNextStatuses(
                    asStatus(
                      selected.status,
                    ),
                  ).length > 0 && (
                    <button
                      type="button"
                      onClick={
                        openStatus
                      }
                    >
                      <Settings2
                        size={15}
                      />

                      Change status
                    </button>
                  )}

                  {canManageServiceApproval(
                    asStatus(
                      selected.status,
                    ),
                  ) && (
                    <button
                      type="button"
                      onClick={
                        openApproval
                      }
                    >
                      <ShieldCheck
                        size={15}
                      />

                      Approval
                    </button>
                  )}

                  {canCreateServiceInvoice(
                    asStatus(
                      selected.status,
                    ),
                    selected.related_invoice_id,
                  ) && (
                    <button
                      type="button"
                      className={
                        styles.primaryButton
                      }
                      onClick={() =>
                        setActionMode(
                          "invoice",
                        )
                      }
                    >
                      <FileText
                        size={15}
                      />

                      Create invoice
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
                  SERVICE ACTION
                </p>

                <h2>
                  {actionMode
                    === "edit"
                    ? "Update service job"
                    : actionMode
                        === "status"
                      ? "Change job status"
                      : actionMode
                          === "approval"
                        ? "Service approval"
                        : actionMode
                            === "labour"
                          ? "Add labour"
                          : actionMode
                              === "part"
                            ? "Issue service part"
                            : "Create service invoice"
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
                === "edit" && (
                <>
                  <label>
                    Technician ID

                    <input
                      type="number"
                      min="1"
                      value={
                        editTechnicianId
                      }
                      onChange={
                        (event) =>
                          setEditTechnicianId(
                            event
                              .target
                              .value,
                          )
                      }
                    />
                  </label>

                  <label>
                    Diagnosis

                    <textarea
                      rows={4}
                      value={
                        editDiagnosis
                      }
                      onChange={
                        (event) =>
                          setEditDiagnosis(
                            event
                              .target
                              .value,
                          )
                      }
                    />
                  </label>

                  <label>
                    Work performed

                    <textarea
                      rows={4}
                      value={
                        editWorkPerformed
                      }
                      onChange={
                        (event) =>
                          setEditWorkPerformed(
                            event
                              .target
                              .value,
                          )
                      }
                    />
                  </label>

                  <label>
                    Testing result

                    <textarea
                      rows={4}
                      value={
                        editTestingResult
                      }
                      onChange={
                        (event) =>
                          setEditTestingResult(
                            event
                              .target
                              .value,
                          )
                      }
                    />
                  </label>

                  <label>
                    Warranty notes

                    <textarea
                      rows={3}
                      value={
                        editWarrantyNotes
                      }
                      onChange={
                        (event) =>
                          setEditWarrantyNotes(
                            event
                              .target
                              .value,
                          )
                      }
                    />
                  </label>

                  <div
                    className={
                      styles.twoFields
                    }
                  >
                    <label>
                      Estimated cost

                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={
                          editEstimatedCost
                        }
                        onChange={
                          (event) =>
                            setEditEstimatedCost(
                              event
                                .target
                                .value,
                            )
                        }
                      />
                    </label>

                    <label>
                      Discount

                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={
                          editDiscount
                        }
                        onChange={
                          (event) =>
                            setEditDiscount(
                              event
                                .target
                                .value,
                            )
                        }
                      />
                    </label>
                  </div>

                  <label>
                    Expected completion

                    <input
                      type="date"
                      value={
                        editExpectedDate
                      }
                      onChange={
                        (event) =>
                          setEditExpectedDate(
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
                        nextStatus
                      }
                      onChange={
                        (event) =>
                          setNextStatus(
                            asStatus(
                              event
                                .target
                                .value,
                            ),
                          )
                      }
                    >
                      {getValidServiceNextStatuses(
                        asStatus(
                          selected.status,
                        ),
                      ).map(
                        (value) => (
                          <option
                            key={value}
                            value={value}
                          >
                            {readable(
                              value,
                            )}
                          </option>
                        ),
                      )}
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


              {actionMode
                === "approval" && (
                <>
                  <label>
                    Approval decision

                    <select
                      value={
                        approvalStatus
                      }
                      onChange={
                        (event) =>
                          setApprovalStatus(
                            asApproval(
                              event
                                .target
                                .value,
                            ),
                          )
                      }
                    >
                      <option value="approved">
                        Approved
                      </option>

                      <option value="rejected">
                        Rejected
                      </option>

                      <option value="pending">
                        Pending
                      </option>
                    </select>
                  </label>

                  <label>
                    Remarks

                    <textarea
                      rows={4}
                      value={
                        approvalRemarks
                      }
                      onChange={
                        (event) =>
                          setApprovalRemarks(
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
                === "labour" && (
                <>
                  <label>
                    Description *

                    <input
                      minLength={2}
                      value={
                        labourDescription
                      }
                      onChange={
                        (event) =>
                          setLabourDescription(
                            event
                              .target
                              .value,
                          )
                      }
                    />
                  </label>

                  <div
                    className={
                      styles.twoFields
                    }
                  >
                    <label>
                      Hours

                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={
                          labourHours
                        }
                        onChange={
                          (event) =>
                            setLabourHours(
                              event
                                .target
                                .value,
                            )
                        }
                      />
                    </label>

                    <label>
                      Amount

                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={
                          labourAmount
                        }
                        onChange={
                          (event) =>
                            setLabourAmount(
                              event
                                .target
                                .value,
                            )
                        }
                      />
                    </label>
                  </div>

                  <label>
                    Notes

                    <textarea
                      rows={3}
                      value={
                        labourNotes
                      }
                      onChange={
                        (event) =>
                          setLabourNotes(
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
                === "part" && (
                <>
                  <label>
                    Product *

                    <select
                      value={
                        partProductId
                      }
                      onChange={
                        (event) => {
                          const value =
                            event
                              .target
                              .value;

                          setPartProductId(
                            value,
                          );

                          const product =
                            products.find(
                              (item) =>
                                String(
                                  item.id,
                                )
                                === value,
                            );

                          if (
                            product
                            && !partUnitPrice
                          ) {
                            setPartUnitPrice(
                              String(
                                product
                                  .selling_price,
                              ),
                            );
                          }
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
                    Warehouse *

                    <select
                      value={
                        partWarehouseId
                      }
                      onChange={
                        (event) =>
                          setPartWarehouseId(
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

                  <div
                    className={
                      styles.twoFields
                    }
                  >
                    <label>
                      Quantity *

                      <input
                        type="number"
                        min="0.001"
                        step="0.001"
                        value={
                          partQuantity
                        }
                        onChange={
                          (event) =>
                            setPartQuantity(
                              event
                                .target
                                .value,
                            )
                        }
                      />
                    </label>

                    <label>
                      Unit price

                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={
                          partUnitPrice
                        }
                        onChange={
                          (event) =>
                            setPartUnitPrice(
                              event
                                .target
                                .value,
                            )
                        }
                      />
                    </label>
                  </div>

                  <label>
                    Notes

                    <textarea
                      rows={3}
                      value={
                        partNotes
                      }
                      onChange={
                        (event) =>
                          setPartNotes(
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
                === "invoice" && (
                <div
                  className={
                    styles.infoBox
                  }
                >
                  <FileText
                    size={19}
                  />

                  <div>
                    <strong>
                      Create sales invoice
                    </strong>

                    <p>
                      The service bill will be
                      generated from the labour,
                      parts and final service
                      amount for{" "}
                      {
                        selected
                          .job_number
                      }.
                    </p>
                  </div>
                </div>
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
                === "edit" && (
                <button
                  type="button"
                  className={
                    styles.primaryButton
                  }
                  disabled={
                    actionLoading
                  }
                  onClick={() =>
                    void submitEdit()
                  }
                >
                  Save changes
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
                    void submitStatus()
                  }
                >
                  Update status
                </button>
              )}

              {actionMode
                === "approval" && (
                <button
                  type="button"
                  className={
                    styles.primaryButton
                  }
                  disabled={
                    actionLoading
                  }
                  onClick={() =>
                    void submitApproval()
                  }
                >
                  Save approval
                </button>
              )}

              {actionMode
                === "labour" && (
                <button
                  type="button"
                  className={
                    styles.primaryButton
                  }
                  disabled={
                    actionLoading
                  }
                  onClick={() =>
                    void submitLabour()
                  }
                >
                  Add labour
                </button>
              )}

              {actionMode
                === "part" && (
                <button
                  type="button"
                  className={
                    styles.primaryButton
                  }
                  disabled={
                    actionLoading
                  }
                  onClick={() =>
                    void submitPart()
                  }
                >
                  Issue part
                </button>
              )}

              {actionMode
                === "invoice" && (
                <button
                  type="button"
                  className={
                    styles.primaryButton
                  }
                  disabled={
                    actionLoading
                  }
                  onClick={() =>
                    void submitInvoice()
                  }
                >
                  {actionLoading
                    ? "Creating..."
                    : "Create invoice"
                  }
                </button>
              )}
            </footer>
          </section>
        </div>
      )}
    </AppShell>
  );
}
