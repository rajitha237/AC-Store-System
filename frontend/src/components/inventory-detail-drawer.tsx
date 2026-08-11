"use client";

import axios from "axios";

import {
  AlertTriangle,
  ArrowDownLeft,
  ArrowUpRight,
  Barcode,
  Boxes,
  Building2,
  CircleAlert,
  History,
  PackageCheck,
  RefreshCw,
  ShieldCheck,
  Warehouse as WarehouseIcon,
  X,
} from "lucide-react";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getSerialNumbers,
  getStockMovements,
} from "@/lib/inventory-api";

import type {
  NormalizedMovementList,
  SerialNumberDetail,
  StockBalance,
} from "@/types/inventory";

import styles from "@/app/inventory/inventory.module.css";


type Props = {
  balance: StockBalance;

  onClose: () => void;
};


function numeric(
  value:
    | string
    | number
    | null
    | undefined,
): number {
  const parsed =
    Number(value ?? 0);

  return Number.isFinite(parsed)
    ? parsed
    : 0;
}


function quantity(
  value:
    | string
    | number,
): string {
  return new Intl.NumberFormat(
    "en-LK",
    {
      minimumFractionDigits:
        0,

      maximumFractionDigits:
        3,
    },
  ).format(
    numeric(value),
  );
}


function money(
  value:
    | string
    | number,
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
    numeric(value),
  );
}


function label(
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


function dateTime(
  value:
    | string
    | null
    | undefined,
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


function simpleDate(
  value:
    | string
    | null
    | undefined,
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
    },
  ).format(date);
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
      + "to view inventory details."
    );
  }

  return (
    "Unable to load "
    + "inventory details."
  );
}


export function InventoryDetailDrawer({
  balance,
  onClose,
}: Props) {
  const [
    movements,
    setMovements,
  ] =
    useState<
      NormalizedMovementList
    >({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
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


  const loadDetail =
    useCallback(
      async (
        refresh =
          false,
      ) => {
        if (refresh) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }

        setError("");

        try {
          const movementPromise =
            getStockMovements({
              page: 1,
              pageSize: 20,

              productId:
                balance.product_id,

              warehouseId:
                balance.warehouse_id,
            });

          const serialPromise =
            balance
              .track_serial_numbers
              ? getSerialNumbers({
                  productId:
                    balance.product_id,

                  warehouseId:
                    balance.warehouse_id,
                })
              : Promise.resolve(
                  [] as SerialNumberDetail[],
                );

          const [
            movementData,
            serialData,
          ] =
            await Promise.all([
              movementPromise,
              serialPromise,
            ]);

          setMovements(
            movementData,
          );

          setSerials(
            serialData,
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
          setRefreshing(false);
        }
      },
      [
        balance.product_id,
        balance.warehouse_id,
        balance.track_serial_numbers,
      ],
    );


  useEffect(() => {
    const timer =
      window.setTimeout(
        () => {
          void loadDetail();
        },
        0,
      );

    return () => {
      window.clearTimeout(
        timer,
      );
    };
  }, [loadDetail]);


  const stockValue =
    useMemo(
      () =>
        numeric(
          balance.quantity_on_hand,
        )
        * numeric(
            balance.average_cost,
          ),
      [
        balance.quantity_on_hand,
        balance.average_cost,
      ],
    );


  return (
    <div
      className={
        styles.detailBackdrop
      }
    >
      <section
        className={
          styles.detailDrawer
        }
        role="dialog"
        aria-modal="true"
        aria-labelledby={
          "inventory-detail-title"
        }
      >
        <header
          className={
            styles.detailHeader
          }
        >
          <div>
            <p className="eyebrow">
              INVENTORY DETAIL
            </p>

            <h2
              id="inventory-detail-title"
            >
              {
                balance.product_name
              }
            </h2>

            <span
              className={
                styles.detailProductCode
              }
            >
              {
                balance.product_code
              }
            </span>
          </div>

          <div
            className={
              styles.detailHeaderActions
            }
          >
            <button
              type="button"
              className={
                styles.detailIconButton
              }
              disabled={
                refreshing
              }
              onClick={() =>
                void loadDetail(
                  true,
                )
              }
              aria-label="Refresh inventory detail"
            >
              <RefreshCw
                size={18}
                className={
                  refreshing
                    ? styles.spin
                    : undefined
                }
              />
            </button>

            <button
              type="button"
              className={
                styles.detailIconButton
              }
              onClick={
                onClose
              }
              aria-label="Close"
            >
              <X size={19} />
            </button>
          </div>
        </header>


        <div
          className={
            styles.detailIdentity
          }
        >
          <div
            className={
              styles.detailProductIcon
            }
          >
            <Boxes size={24} />
          </div>

          <div>
            <strong>
              {
                balance.product_name
              }
            </strong>

            <span>
              {
                balance.warehouse_code
              }
              {" • "}
              {
                balance.warehouse_name
              }
            </span>
          </div>

          <span
            className={
              balance.is_low_stock
                ? styles.lowBadge
                : styles.okBadge
            }
          >
            {balance.is_low_stock
              ? "Low stock"
              : "Healthy"
            }
          </span>
        </div>


        <div
          className={
            styles.detailMetricGrid
          }
        >
          <article>
            <PackageCheck
              size={17}
            />

            <span>
              On hand
            </span>

            <strong>
              {quantity(
                balance
                  .quantity_on_hand,
              )}
            </strong>
          </article>

          <article>
            <ShieldCheck
              size={17}
            />

            <span>
              Reserved
            </span>

            <strong>
              {quantity(
                balance
                  .quantity_reserved,
              )}
            </strong>
          </article>

          <article>
            <Boxes size={17} />

            <span>
              Available
            </span>

            <strong>
              {quantity(
                balance
                  .quantity_available,
              )}
            </strong>
          </article>

          <article>
            <AlertTriangle
              size={17}
            />

            <span>
              Reorder level
            </span>

            <strong>
              {quantity(
                balance
                  .reorder_level,
              )}
            </strong>
          </article>
        </div>


        <section
          className={
            styles.detailSection
          }
        >
          <h3>
            Stock information
          </h3>

          <div
            className={
              styles.detailInfoGrid
            }
          >
            <div>
              <Building2
                size={16}
              />

              <span>
                Warehouse
              </span>

              <strong>
                {
                  balance.warehouse_name
                }
              </strong>

              <small>
                {
                  balance.warehouse_code
                }
              </small>
            </div>

            <div>
              <WarehouseIcon
                size={16}
              />

              <span>
                Average cost
              </span>

              <strong>
                {money(
                  balance.average_cost,
                )}
              </strong>
            </div>

            <div>
              <PackageCheck
                size={16}
              />

              <span>
                Estimated value
              </span>

              <strong>
                {money(
                  stockValue,
                )}
              </strong>
            </div>

            <div>
              <Barcode
                size={16}
              />

              <span>
                Tracking
              </span>

              <strong>
                {balance
                  .track_serial_numbers
                  ? "Serialized"
                  : "Standard stock"
                }
              </strong>
            </div>
          </div>
        </section>


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


        {balance
          .track_serial_numbers && (
          <section
            className={
              styles.detailSection
            }
          >
            <div
              className={
                styles.detailSectionHeader
              }
            >
              <div>
                <h3>
                  Serial numbers
                </h3>

                <p>
                  Units currently associated
                  with this product and warehouse.
                </p>
              </div>

              <span
                className={
                  styles.detailCountBadge
                }
              >
                {serials.length}
              </span>
            </div>


            {loading ? (
              <div
                className={
                  styles.detailLoadingState
                }
              >
                Loading serial numbers...
              </div>
            ) : serials.length
              === 0 ? (
              <div
                className={
                  styles.detailEmptyState
                }
              >
                <Barcode
                  size={25}
                />

                <strong>
                  No serials in this warehouse
                </strong>

                <span>
                  Serialized stock received
                  into this warehouse will
                  appear here.
                </span>
              </div>
            ) : (
              <div
                className={
                  styles.serialList
                }
              >
                {serials.map(
                  (serial) => (
                    <article
                      key={
                        serial.id
                      }
                      className={
                        styles.serialRow
                      }
                    >
                      <div
                        className={
                          styles.serialIcon
                        }
                      >
                        <Barcode
                          size={16}
                        />
                      </div>

                      <div
                        className={
                          styles.serialMain
                        }
                      >
                        <strong>
                          {
                            serial.serial_number
                          }
                        </strong>

                        <span>
                          Serial #
                          {serial.id}
                        </span>
                      </div>

                      <div
                        className={
                          styles.serialWarranty
                        }
                      >
                        <span>
                          Warranty end
                        </span>

                        <strong>
                          {simpleDate(
                            serial
                              .warranty_end_date,
                          )}
                        </strong>
                      </div>

                      <span
                        className={
                          serial.status
                          === "available"
                            ? styles.serialAvailable
                            : styles.serialStatus
                        }
                      >
                        {label(
                          serial.status,
                        )}
                      </span>
                    </article>
                  ),
                )}
              </div>
            )}
          </section>
        )}


        <section
          className={
            styles.detailSection
          }
        >
          <div
            className={
              styles.detailSectionHeader
            }
          >
            <div>
              <h3>
                Product movements
              </h3>

              <p>
                Recent movement history
                for this product in this
                warehouse.
              </p>
            </div>

            <span
              className={
                styles.detailCountBadge
              }
            >
              {
                movements.total
              }
            </span>
          </div>


          {loading ? (
            <div
              className={
                styles.detailLoadingState
              }
            >
              Loading movements...
            </div>
          ) : movements.items.length
            === 0 ? (
            <div
              className={
                styles.detailEmptyState
              }
            >
              <History
                size={25}
              />

              <strong>
                No movements found
              </strong>

              <span>
                Stock activity for this
                product will appear here.
              </span>
            </div>
          ) : (
            <div
              className={
                styles.detailMovementList
              }
            >
              {movements.items.map(
                (movement) => {
                  const qty =
                    numeric(
                      movement.quantity,
                    );

                  const positive =
                    qty > 0;

                  return (
                    <article
                      key={
                        movement.id
                      }
                      className={
                        styles.detailMovementRow
                      }
                    >
                      <div
                        className={
                          positive
                            ? styles
                                .movementIconPositive
                            : styles
                                .movementIconNegative
                        }
                      >
                        {positive
                          ? (
                            <ArrowDownLeft
                              size={16}
                            />
                          )
                          : (
                            <ArrowUpRight
                              size={16}
                            />
                          )
                        }
                      </div>

                      <div
                        className={
                          styles
                            .detailMovementMain
                        }
                      >
                        <strong>
                          {label(
                            movement
                              .movement_type,
                          )}
                        </strong>

                        <span>
                          {
                            movement
                              .reference_type
                            || "No reference type"
                          }
                          {" • "}
                          {
                            movement
                              .reference_id
                            || "No reference"
                          }
                        </span>
                      </div>

                      <div
                        className={
                          styles
                            .detailMovementQty
                        }
                      >
                        <strong
                          className={
                            positive
                              ? styles.positive
                              : styles.negative
                          }
                        >
                          {positive
                            ? "+"
                            : ""
                          }
                          {quantity(
                            qty,
                          )}
                        </strong>

                        <span>
                          {money(
                            movement.unit_cost,
                          )}
                        </span>
                      </div>

                      <time
                        className={
                          styles
                            .detailMovementDate
                        }
                      >
                        {dateTime(
                          movement
                            .movement_date,
                        )}
                      </time>
                    </article>
                  );
                },
              )}
            </div>
          )}
        </section>
      </section>
    </div>
  );
}
