"use client";

import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  ClipboardCheck,
  LoaderCircle,
  MapPin,
  PackagePlus,
  Phone,
  RefreshCw,
  UserRound,
  Wrench,
} from "lucide-react";
import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  useParams,
  useRouter,
} from "next/navigation";

import { writeTechnicianLocation } from "@/lib/technician-location-api";
import {
  getCurrentUser,
} from "@/lib/auth-api";
import {
  addServicePart,
  completeServiceJob,
  getServiceJob,
} from "@/lib/service-jobs-api";

import {
  getProducts,
} from "@/lib/catalog-api";
import {
  getStockBalances,
  getWarehouses,
} from "@/lib/inventory-api";

import type {
  ServiceJobDetailResponse,
} from "@/types/service-jobs";

import styles from "./page.module.css";


type TechnicianPartProduct = {
  id: number;
  name: string;
  sku?: string | null;
  product_type?: string | null;
  is_active?: boolean;
};

type TechnicianPartWarehouse = {
  id: number;
  name: string;
  code?: string | null;
  is_active?: boolean;
};

type TechnicianPartBalance = {
  product_id: number;
  warehouse_id: number;
  quantity?: string | number;
  available_quantity?: string | number;
  product_name?: string | null;
  product_sku?: string | null;
  warehouse_name?: string | null;
};




type TechnicianUser =
  Awaited<
    ReturnType<
      typeof getCurrentUser
    >
  >;


function normalizedRole(
  role: string | null | undefined,
): string {
  return (role ?? "")
    .trim()
    .toLowerCase()
    .replaceAll("-", "_")
    .replaceAll(" ", "_");
}


function isTechnicianRole(
  role: string | null | undefined,
): boolean {
  const value =
    normalizedRole(role);

  return (
    value === "technician"
    || value === "service_technician"
    || value.includes("technician")
  );
}


function statusLabel(
  value: string,
): string {
  return value
    .replaceAll("_", " ")
    .replace(
      /\b\w/g,
      (letter) =>
        letter.toUpperCase(),
    );
}


function displayValue(
  value:
    | string
    | number
    | null
    | undefined,
): string {
  if (
    value === null
    || value === undefined
    || value === ""
  ) {
    return "—";
  }

  return String(value);
}


function apiErrorMessage(
  error: unknown,
): string {
  if (
    error
    && typeof error === "object"
  ) {
    const candidate =
      error as {
        message?: string;
        detail?: string;
      };

    if (candidate.detail) {
      return candidate.detail;
    }

    if (candidate.message) {
      return candidate.message;
    }
  }

  return (
    "Something went wrong. "
    + "Please try again."
  );
}


export default function TechnicianJobPage() {
  const router = useRouter();
  const params = useParams<{
    jobId: string;
  }>();

  const jobId =
    Number(params.jobId);

  const [
    user,
    setUser,
  ] = useState<
    TechnicianUser | null
  >(null);

  const [
    job,
    setJob,
  ] = useState<
    ServiceJobDetailResponse | null
  >(null);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    refreshing,
    setRefreshing,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  const [
    actionMode,
    setActionMode,
  ] = useState<
    "part" | "complete" | null
  >(null);

  const [
    partSearch,
    setPartSearch,
  ] = useState("");

  const [
    partProducts,
    setPartProducts,
  ] = useState<
    TechnicianPartProduct[]
  >([]);

  const [
    partWarehouses,
    setPartWarehouses,
  ] = useState<
    TechnicianPartWarehouse[]
  >([]);

  const [
    partBalances,
    setPartBalances,
  ] = useState<
    TechnicianPartBalance[]
  >([]);

  const [
    partPickerLoading,
    setPartPickerLoading,
  ] = useState(false);

  const [
    productId,
    setProductId,
  ] = useState("");

  const [
    warehouseId,
    setWarehouseId,
  ] = useState("");

  const [
    quantity,
    setQuantity,
  ] = useState("1");

  const [
    unitPrice,
    setUnitPrice,
  ] = useState("");

  const [
    partNotes,
    setPartNotes,
  ] = useState("");

  const [
    partSaving,
    setPartSaving,
  ] = useState(false);

  const [
    jobResult,
    setJobResult,
  ] = useState("");

  const [
    completionNotes,
    setCompletionNotes,
  ] = useState("");

  const [
    completeSaving,
    setCompleteSaving,
  ] = useState(false);


  const refreshJob =
    useCallback(
      async (
        targetJobId: number,
      ) => {
        const detail =
          await getServiceJob(
            targetJobId,
          );

        setJob(detail);

        return detail;
      },
      [],
    );


  const loadPage =
    useCallback(
      async () => {
        if (
          !Number.isInteger(jobId)
          || jobId <= 0
        ) {
          setError(
            "Invalid service job.",
          );

          setLoading(false);
          return;
        }

        try {
          setError("");

          const currentUser =
            await getCurrentUser();

          if (
            !isTechnicianRole(
              currentUser.role,
            )
          ) {
            router.replace(
              "/dashboard",
            );

            return;
          }

          setUser(currentUser);

          const detail =
            await refreshJob(
              jobId,
            );

          const currentUserId =
            Number(currentUser.id);

          const assignedIds =
            [
              detail.technician_id,
              ...(
                (
                  detail as unknown as {
                    secondary_technician_ids?:
                      number[];
                  }
                )
                  .secondary_technician_ids
                ?? []
              ),
            ]
              .filter(
                (
                  value,
                ): value is number =>
                  typeof value
                  === "number",
              );

          if (
            !assignedIds.includes(
              currentUserId,
            )
          ) {
            setJob(null);

            setError(
              "This job is not assigned to you.",
            );

            return;
          }
        } catch (
          requestError
        ) {
          setError(
            apiErrorMessage(
              requestError,
            ),
          );
        } finally {
          setLoading(false);
        }
      },
      [
        jobId,
        refreshJob,
        router,
      ],
    );


  useEffect(() => {
    const timeout =
      window.setTimeout(
        () => {
          void loadPage();
        },
        0,
      );

    return () => {
      window.clearTimeout(
        timeout,
      );
    };
  }, [loadPage]);


  // ACTIVE_JOB_LOCATION_ASSOCIATION_EFFECT
  useEffect(() => {
    if (
      !job
      || !user
      || !Number.isInteger(jobId)
      || jobId <= 0
      || !navigator.geolocation
    ) {
      return;
    }

    let active = true;

    const sendJobLocation = (
      position: GeolocationPosition,
    ) => {
      if (!active) {
        return;
      }

      void writeTechnicianLocation({
        service_job_id: jobId,
        latitude:
          position.coords.latitude,
        longitude:
          position.coords.longitude,
        accuracy_meters:
          position.coords.accuracy,
        client_recorded_at:
          new Date(
            position.timestamp,
          ).toISOString(),
        tracking_state: "active",
      }).catch(() => {
        // The persistent technician tracker
        // continues handling location status.
      });
    };

    navigator.geolocation.getCurrentPosition(
      sendJobLocation,
      () => {
        // Existing tracker UI reports
        // browser/device location failures.
      },
      {
        enableHighAccuracy: true,
        timeout: 20000,
        maximumAge: 15000,
      },
    );

    return () => {
      active = false;
    };
  }, [
    job,
    jobId,
    user,
  ]);


  const canComplete =
    useMemo(
      () =>
        Boolean(
          job
          && job.status !== "ready"
          && job.status !== "delivered"
          && job.status !== "cancelled",
        ),
      [job],
    );


  async function handleRefresh() {
    if (
      refreshing
      || !job
    ) {
      return;
    }

    try {
      setRefreshing(true);
      setError("");

      await refreshJob(
        job.id,
      );
    } catch (
      requestError
    ) {
      setError(
        apiErrorMessage(
          requestError,
        ),
      );
    } finally {
      setRefreshing(false);
    }
  }


  function openPartForm() {
    setError("");
    setActionMode("part");

    void loadPartPicker();
  }


  function openCompleteForm() {
    if (
      !job
      || !canComplete
    ) {
      return;
    }

    setError("");

    setJobResult(
      job.work_performed
      || job.testing_result
      || "",
    );

    setCompletionNotes("");
    setActionMode("complete");
  }


  function closeAction() {
    if (
      partSaving
      || completeSaving
    ) {
      return;
    }

    setActionMode(null);
    setError("");
  }


  const selectedPartProduct =
    useMemo(
      () =>
        partProducts.find(
          (product) =>
            String(product.id)
            === productId,
        ) ?? null,
      [
        partProducts,
        productId,
      ],
    );

  const selectedPartBalance =
    useMemo(
      () =>
        partBalances.find(
          (balance) =>
            String(
              balance.product_id,
            ) === productId
            && String(
              balance.warehouse_id,
            ) === warehouseId,
        ) ?? null,
      [
        partBalances,
        productId,
        warehouseId,
      ],
    );

  const selectedAvailableQuantity =
    selectedPartBalance
      ? Number(
          selectedPartBalance
            .available_quantity
          ?? selectedPartBalance
            .quantity
          ?? 0,
        )
      : 0;


  async function loadPartPicker() {
    if (partPickerLoading) {
      return;
    }

    try {
      setPartPickerLoading(true);
      setError("");

      const productResponse =
        await getProducts({
          page: 1,
          pageSize: 100,
          search:
            partSearch.trim()
            || undefined,
        });

      const productCandidate =
        productResponse as unknown as {
          items?: TechnicianPartProduct[];
          data?: TechnicianPartProduct[];
          results?: TechnicianPartProduct[];
        };

      const products =
        productCandidate.items
        ?? productCandidate.data
        ?? productCandidate.results
        ?? [];

      const warehouses =
        await getWarehouses(true);

      const balances =
        await getStockBalances({
          search:
            partSearch.trim()
            || undefined,
        });

      setPartProducts(
        products.filter(
          (product) =>
            product.is_active
            !== false,
        ),
      );

      setPartWarehouses(
        (
          warehouses as TechnicianPartWarehouse[]
        ).filter(
          (warehouse) =>
            warehouse.is_active
            !== false,
        ),
      );

      setPartBalances(
        balances as TechnicianPartBalance[],
      );
    } catch (requestError) {
      setError(
        apiErrorMessage(
          requestError,
        ),
      );
    } finally {
      setPartPickerLoading(false);
    }
  }


  async function submitPart(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (
      partSaving
      || !job
    ) {
      return;
    }

    const parsedProductId =
      Number(productId);

    const parsedWarehouseId =
      Number(warehouseId);

    const cleanedQuantity =
      quantity.trim();

    if (
      !Number.isInteger(
        parsedProductId,
      )
      || parsedProductId <= 0
    ) {
      setError(
        "Enter a valid product ID.",
      );

      return;
    }

    if (
      !Number.isInteger(
        parsedWarehouseId,
      )
      || parsedWarehouseId <= 0
    ) {
      setError(
        "Enter a valid warehouse ID.",
      );

      return;
    }

    if (
      !cleanedQuantity
      || Number(cleanedQuantity)
        <= 0
    ) {
      setError(
        "Enter a valid quantity.",
      );

      return;
    }

    if (
      selectedPartBalance
      && Number(cleanedQuantity)
        > selectedAvailableQuantity
    ) {
      setError(
        "Requested quantity exceeds available stock.",
      );

      return;
    }

    try {
      setPartSaving(true);
      setError("");

      await addServicePart(
        job.id,
        {
          product_id:
            parsedProductId,

          warehouse_id:
            parsedWarehouseId,

          quantity:
            cleanedQuantity,

          unit_price:
            unitPrice.trim()
              || null,

          notes:
            partNotes.trim()
              || null,
        },
      );

      await refreshJob(
        job.id,
      );

      setPartSearch("");
      setProductId("");
      setWarehouseId("");
      setQuantity("1");
      setUnitPrice("");
      setPartNotes("");
      setActionMode(null);
    } catch (
      requestError
    ) {
      setError(
        apiErrorMessage(
          requestError,
        ),
      );
    } finally {
      setPartSaving(false);
    }
  }


  async function submitComplete(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (
      completeSaving
      || !job
      || !canComplete
    ) {
      return;
    }

    const result =
      jobResult.trim();

    if (!result) {
      setError(
        "Enter the job result.",
      );

      return;
    }

    if (
      result.length > 2000
    ) {
      setError(
        "Job result must be 2000 characters or less.",
      );

      return;
    }

    const notes =
      completionNotes.trim();

    if (
      notes.length > 1000
    ) {
      setError(
        "Completion notes must be 1000 characters or less.",
      );

      return;
    }

    try {
      setCompleteSaving(true);
      setError("");

      await completeServiceJob(
        job.id,
        {
          job_result:
            result,

          notes:
            notes || null,
        },
      );

      await refreshJob(
        job.id,
      );

      setActionMode(null);
      setCompletionNotes("");
    } catch (
      requestError
    ) {
      setError(
        apiErrorMessage(
          requestError,
        ),
      );
    } finally {
      setCompleteSaving(false);
    }
  }


  if (loading) {
    return (
      <main
        className={
          styles.page
        }
      >
        <div
          className={
            styles.centerState
          }
        >
          <LoaderCircle
            className={
              styles.spin
            }
            size={30}
          />

          <strong>
            Loading job
          </strong>

          <span>
            Preparing service details...
          </span>
        </div>
      </main>
    );
  }


  if (!job) {
    return (
      <main
        className={
          styles.page
        }
      >
        <div
          className={
            styles.centerState
          }
        >
          <AlertCircle
            size={34}
          />

          <strong>
            Job unavailable
          </strong>

          <span>
            {error
              || "Unable to open this job."}
          </span>

          <button
            type="button"
            className={
              styles.primaryButton
            }
            onClick={() =>
              router.push(
                "/technician",
              )
            }
          >
            Back to My Jobs
          </button>
        </div>
      </main>
    );
  }


  return (
    <main
      className={
        styles.page
      }
    >
      <header
        className={
          styles.header
        }
      >
        <button
          type="button"
          className={
            styles.iconButton
          }
          onClick={() =>
            router.push(
              "/technician",
            )
          }
          aria-label="Back to jobs"
        >
          <ArrowLeft
            size={20}
          />
        </button>

        <div
          className={
            styles.headerText
          }
        >
          <span>
            Technician Job
          </span>

          <strong>
            {job.job_number}
          </strong>
        </div>

        <button
          type="button"
          className={
            styles.iconButton
          }
          onClick={() =>
            void handleRefresh()
          }
          disabled={
            refreshing
          }
          aria-label="Refresh job"
        >
          <RefreshCw
            size={19}
            className={
              refreshing
                ? styles.spin
                : undefined
            }
          />
        </button>
      </header>


      <section
        className={
          styles.content
        }
      >
        {error ? (
          <div
            className={
              styles.errorBox
            }
          >
            <AlertCircle
              size={18}
            />

            <span>
              {error}
            </span>
          </div>
        ) : null}


        <section
          className={
            styles.heroCard
          }
        >
          <div
            className={
              styles.heroTop
            }
          >
            <div>
              <span
                className={
                  styles.eyebrow
                }
              >
                Current status
              </span>

              <h1>
                {statusLabel(
                  job.status,
                )}
              </h1>
            </div>

            <span
              className={
                styles.statusBadge
              }
            >
              {statusLabel(
                job.priority,
              )}
            </span>
          </div>

          <p>
            {job.complaint}
          </p>
        </section>


        <section
          className={
            styles.card
          }
        >
          <div
            className={
              styles.sectionTitle
            }
          >
            <UserRound
              size={18}
            />

            <strong>
              Customer
            </strong>
          </div>

          <div
            className={
              styles.detailGrid
            }
          >
            <div>
              <span>Name</span>
              <strong>
                {displayValue(
                  job.customer_name,
                )}
              </strong>
            </div>

            <div>
              <span>Phone</span>

              <strong>
                {displayValue(
                  job.customer_phone,
                )}
              </strong>
            </div>
          </div>

          {job.customer_phone ? (
            <a
              className={
                styles.callButton
              }
              href={
                `tel:${job.customer_phone}`
              }
            >
              <Phone
                size={17}
              />
              Call Customer
            </a>
          ) : null}
        </section>


        <section
          className={
            styles.card
          }
        >
          <div
            className={
              styles.sectionTitle
            }
          >
            <Wrench
              size={18}
            />

            <strong>
              Service Item
            </strong>
          </div>

          <div
            className={
              styles.detailGrid
            }
          >
            <div>
              <span>Product</span>
              <strong>
                {displayValue(
                  job.product_name,
                )}
              </strong>
            </div>

            <div>
              <span>Brand</span>
              <strong>
                {displayValue(
                  job.brand_name,
                )}
              </strong>
            </div>

            <div>
              <span>Model</span>
              <strong>
                {displayValue(
                  job.model_number,
                )}
              </strong>
            </div>

            <div>
              <span>Serial</span>
              <strong>
                {displayValue(
                  job.serial_number,
                )}
              </strong>
            </div>
          </div>
        </section>


        <section
          className={
            styles.card
          }
        >
          <div
            className={
              styles.sectionTitle
            }
          >
            <MapPin
              size={18}
            />

            <strong>
              Job Information
            </strong>
          </div>

          <div
            className={
              styles.stack
            }
          >
            <div>
              <span>
                Reported issue
              </span>

              <p>
                {displayValue(
                  job.reported_issue,
                )}
              </p>
            </div>

            <div>
              <span>
                Diagnosis
              </span>

              <p>
                {displayValue(
                  job.technician_diagnosis,
                )}
              </p>
            </div>

            <div>
              <span>
                Work performed
              </span>

              <p>
                {displayValue(
                  job.work_performed,
                )}
              </p>
            </div>

            <div>
              <span>
                Testing result
              </span>

              <p>
                {displayValue(
                  job.testing_result,
                )}
              </p>
            </div>
          </div>
        </section>


        <section
          className={
            styles.card
          }
        >
          <div
            className={
              styles.sectionHeading
            }
          >
            <div
              className={
                styles.sectionTitle
              }
            >
              <PackagePlus
                size={18}
              />

              <strong>
                Parts Used
              </strong>
            </div>

            <button
              type="button"
              className={
                styles.smallButton
              }
              onClick={
                openPartForm
              }
            >
              Add Part
            </button>
          </div>

          {job.parts.length
            === 0 ? (
            <p
              className={
                styles.emptyText
              }
            >
              No parts added to this job.
            </p>
          ) : (
            <div
              className={
                styles.partList
              }
            >
              {job.parts.map(
                (part) => (
                  <article
                    key={
                      part.id
                    }
                    className={
                      styles.partRow
                    }
                  >
                    <div>
                      <strong>
                        Product #
                        {part.product_id}
                      </strong>

                      <span>
                        Warehouse #
                        {part.warehouse_id}
                      </span>
                    </div>

                    <strong>
                      Qty {part.quantity}
                    </strong>
                  </article>
                ),
              )}
            </div>
          )}
        </section>


        <section
          className={
            styles.completeCard
          }
        >
          <div
            className={
              styles.sectionTitle
            }
          >
            <ClipboardCheck
              size={19}
            />

            <strong>
              Finish Service
            </strong>
          </div>

          {canComplete ? (
            <>
              <p>
                Add any required parts first,
                then enter the final job result
                and complete the service.
              </p>

              <button
                type="button"
                className={
                  styles.completeButton
                }
                onClick={
                  openCompleteForm
                }
              >
                <CheckCircle2
                  size={18}
                />

                Enter Result & Complete
              </button>
            </>
          ) : (
            <div
              className={
                styles.completedState
              }
            >
              <CheckCircle2
                size={20}
              />

              <span>
                This job is currently{" "}
                <strong>
                  {statusLabel(
                    job.status,
                  )}
                </strong>.
              </span>
            </div>
          )}
        </section>


        <footer
          className={
            styles.footer
          }
        >
          Signed in as{" "}
          <strong>
            {
              (
                user as unknown as {
                  full_name?:
                    string | null;
                }
              )
                ?.full_name
              || `User #${user?.id}`
            }
          </strong>
        </footer>
      </section>


      {actionMode ? (
        <div
          className={
            styles.overlay
          }
          role="presentation"
        >
          <section
            className={
              styles.sheet
            }
          >
            <div
              className={
                styles.sheetHandle
              }
            />

            {actionMode
              === "part" ? (
              <form
                onSubmit={
                  submitPart
                }
              >
                <div
                  className={
                    styles.sheetTitle
                  }
                >
                  <PackagePlus
                    size={21}
                  />

                  <div>
                    <strong>
                      Add Part
                    </strong>

                    <span>
                      Add a part used for this job.
                    </span>
                  </div>
                </div>

                <label
                  className={
                    styles.field
                  }
                >
                  <span>
                    Search Part
                  </span>

                  <div
                    className={
                      styles.pickerSearchRow
                    }
                  >
                    <input
                      type="search"
                      value={
                        partSearch
                      }
                      onChange={(
                        event,
                      ) =>
                        setPartSearch(
                          event.target.value,
                        )
                      }
                      placeholder={
                        "Search by product name or SKU"
                      }
                    />

                    <button
                      type="button"
                      className={
                        styles.secondaryButton
                      }
                      disabled={
                        partPickerLoading
                      }
                      onClick={() =>
                        void loadPartPicker()
                      }
                    >
                      {partPickerLoading
                        ? "Loading..."
                        : "Search"}
                    </button>
                  </div>
                </label>

                <label
                  className={
                    styles.field
                  }
                >
                  <span>
                    Part *
                  </span>

                  <select
                    required
                    value={
                      productId
                    }
                    onChange={(
                      event,
                    ) => {
                      setProductId(
                        event.target.value,
                      );

                      setWarehouseId("");
                    }}
                  >
                    <option value="">
                      Select part
                    </option>

                    {partProducts.map(
                      (product) => (
                        <option
                          key={
                            product.id
                          }
                          value={
                            product.id
                          }
                        >
                          {product.name}
                          {product.sku
                            ? ` - ${product.sku}`
                            : ""}
                        </option>
                      ),
                    )}
                  </select>

                  {selectedPartProduct ? (
                    <small>
                      Selected:{" "}
                      {
                        selectedPartProduct
                          .name
                      }
                    </small>
                  ) : null}
                </label>

                <label
                  className={
                    styles.field
                  }
                >
                  <span>
                    Select Warehouse *
                  </span>

                  <select
                    required
                    value={
                      warehouseId
                    }
                    disabled={
                      !productId
                    }
                    onChange={(
                      event,
                    ) =>
                      setWarehouseId(
                        event.target.value,
                      )
                    }
                  >
                    <option value="">
                      Select warehouse
                    </option>

                    {partWarehouses
                      .filter(
                        (warehouse) =>
                          partBalances.some(
                            (balance) =>
                              String(
                                balance.product_id,
                              ) === productId
                              && balance.warehouse_id
                                === warehouse.id
                              && Number(
                                balance.available_quantity
                                ?? balance.quantity
                                ?? 0,
                              ) > 0,
                          ),
                      )
                      .map(
                        (warehouse) => {
                          const balance =
                            partBalances.find(
                              (item) =>
                                String(
                                  item.product_id,
                                ) === productId
                                && item.warehouse_id
                                  === warehouse.id,
                            );

                          const available =
                            Number(
                              balance
                                ?.available_quantity
                              ?? balance
                                ?.quantity
                              ?? 0,
                            );

                          return (
                            <option
                              key={
                                warehouse.id
                              }
                              value={
                                warehouse.id
                              }
                            >
                              {warehouse.name}
                              {" - Stock: "}
                              {available}
                            </option>
                          );
                        },
                      )}
                  </select>

                  {productId
                  && partWarehouses.length
                    > 0
                  && !partWarehouses.some(
                    (warehouse) =>
                      partBalances.some(
                        (balance) =>
                          String(
                            balance.product_id,
                          ) === productId
                          && balance.warehouse_id
                            === warehouse.id
                          && Number(
                            balance.available_quantity
                            ?? balance.quantity
                            ?? 0,
                          ) > 0,
                      ),
                  ) ? (
                    <small>
                      No available stock found
                      for this part.
                    </small>
                  ) : null}

                  {warehouseId ? (
                    <small>
                      Available stock:{" "}
                      {
                        selectedAvailableQuantity
                      }
                    </small>
                  ) : null}
                </label>

                <label
                  className={
                    styles.field
                  }
                >
                  <span>
                    Quantity *
                  </span>

                  <input
                    type="number"
                    min="0.001"
                    step="0.001"
                    required
                    value={
                      quantity
                    }
                    onChange={(
                      event,
                    ) =>
                      setQuantity(
                        event.target.value,
                      )
                    }
                  />
                </label>

                <label
                  className={
                    styles.field
                  }
                >
                  <span>
                    Unit Price
                  </span>

                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={
                      unitPrice
                    }
                    onChange={(
                      event,
                    ) =>
                      setUnitPrice(
                        event.target.value,
                      )
                    }
                  />
                </label>

                <label
                  className={
                    styles.field
                  }
                >
                  <span>
                    Notes
                  </span>

                  <textarea
                    rows={3}
                    value={
                      partNotes
                    }
                    onChange={(
                      event,
                    ) =>
                      setPartNotes(
                        event.target.value,
                      )
                    }
                  />
                </label>

                <div
                  className={
                    styles.sheetActions
                  }
                >
                  <button
                    type="button"
                    className={
                      styles.secondaryButton
                    }
                    onClick={
                      closeAction
                    }
                    disabled={
                      partSaving
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
                      partSaving
                    }
                  >
                    {partSaving
                      ? "Adding..."
                      : "Add Part"}
                  </button>
                </div>
              </form>
            ) : (
              <form
                onSubmit={
                  submitComplete
                }
              >
                <div
                  className={
                    styles.sheetTitle
                  }
                >
                  <ClipboardCheck
                    size={21}
                  />

                  <div>
                    <strong>
                      Complete Job
                    </strong>

                    <span>
                      Enter the final service result.
                    </span>
                  </div>
                </div>

                <label
                  className={
                    styles.field
                  }
                >
                  <span>
                    Job Result *
                  </span>

                  <textarea
                    rows={6}
                    required
                    maxLength={2000}
                    value={
                      jobResult
                    }
                    onChange={(
                      event,
                    ) =>
                      setJobResult(
                        event.target.value,
                      )
                    }
                    placeholder={
                      "Example: Replaced capacitor and tested unit successfully."
                    }
                  />

                  <small>
                    {jobResult.length}/2000
                  </small>
                </label>

                <label
                  className={
                    styles.field
                  }
                >
                  <span>
                    Completion Notes
                  </span>

                  <textarea
                    rows={3}
                    maxLength={1000}
                    value={
                      completionNotes
                    }
                    onChange={(
                      event,
                    ) =>
                      setCompletionNotes(
                        event.target.value,
                      )
                    }
                  />

                  <small>
                    {completionNotes.length}/1000
                  </small>
                </label>

                <div
                  className={
                    styles.sheetActions
                  }
                >
                  <button
                    type="button"
                    className={
                      styles.secondaryButton
                    }
                    onClick={
                      closeAction
                    }
                    disabled={
                      completeSaving
                    }
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    className={
                      styles.completeButton
                    }
                    disabled={
                      completeSaving
                    }
                  >
                    {completeSaving
                      ? "Completing..."
                      : "Complete Job"}
                  </button>
                </div>
              </form>
            )}
          </section>
        </div>
      ) : null}
    </main>
  );
}
