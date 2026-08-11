"use client";

import axios from "axios";

import {
  AlertTriangle,
  ArrowDownLeft,
  ArrowUpRight,
  Barcode,
  Boxes,
  Building2,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  History,
  PackageCheck,
  PackagePlus,
  RefreshCw,
  Search,
  Warehouse as WarehouseIcon,
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
  InventoryDetailDrawer,
} from "@/components/inventory-detail-drawer";

import {
  ReceiveStockModal,
} from "@/components/receive-stock-modal";

import {
  InventoryPhase4Actions,
} from "@/components/inventory-phase4-actions";

import {
  getStockBalances,
  getStockMovements,
  getWarehouses,
} from "@/lib/inventory-api";

import {
  clearAuthSession,
  getAccessToken,
  getStoredUser,
} from "@/lib/auth";

import type {
  NormalizedMovementList,
  StockBalance,
  StockMovementType,
  Warehouse,
} from "@/types/inventory";

import type {
  UserResponse,
} from "@/types/auth";

import styles from "./inventory.module.css";


const MOVEMENT_PAGE_SIZE =
  8;


const movementTypes: {
  value: StockMovementType;
  label: string;
}[] = [
  {
    value:
      "opening_balance",
    label:
      "Opening balance",
  },
  {
    value:
      "purchase_receipt",
    label:
      "Purchase receipt",
  },
  {
    value:
      "sale_issue",
    label:
      "Sale issue",
  },
  {
    value:
      "sale_return",
    label:
      "Sale return",
  },
  {
    value:
      "sale_return_reversal",
    label:
      "Return reversal",
  },
  {
    value:
      "replacement_issue",
    label:
      "Replacement issue",
  },
  {
    value:
      "supplier_return",
    label:
      "Supplier return",
  },
  {
    value:
      "service_usage",
    label:
      "Service usage",
  },
  {
    value:
      "adjustment_increase",
    label:
      "Adjustment increase",
  },
  {
    value:
      "adjustment_decrease",
    label:
      "Adjustment decrease",
  },
  {
    value:
      "transfer_in",
    label:
      "Transfer in",
  },
  {
    value:
      "transfer_out",
    label:
      "Transfer out",
  },
  {
    value:
      "write_off",
    label:
      "Write off",
  },
];


function numeric(
  value:
    | string
    | number
    | null
    | undefined,
): number {
  const parsed =
    Number(value ?? 0);

  return Number.isFinite(
    parsed,
  )
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


function movementLabel(
  value: string,
): string {
  return value
    .split("_")
    .map(
      (part) =>
        part
          .charAt(0)
          .toUpperCase()
        + part.slice(1),
    )
    .join(" ");
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
      + "to view inventory data."
    );
  }

  return (
    "Unable to load "
    + "inventory data."
  );
}


export default function InventoryPage() {
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
    warehouses,
    setWarehouses,
  ] =
    useState<Warehouse[]>(
      [],
    );

  const [
    balances,
    setBalances,
  ] =
    useState<
      StockBalance[]
    >(
      [],
    );

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
      page_size:
        MOVEMENT_PAGE_SIZE,
      total_pages: 0,
    });


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
    warehouseId,
    setWarehouseId,
  ] =
    useState("");

  const [
    lowStockOnly,
    setLowStockOnly,
  ] =
    useState(false);


  const [
    movementPage,
    setMovementPage,
  ] =
    useState(1);

  const [
    movementType,
    setMovementType,
  ] =
    useState<
      StockMovementType
      | ""
    >("");

  const [
    selectedBalance,
    setSelectedBalance,
  ] =
    useState<
      StockBalance | null
    >(
      null,
    );

  const [
    receiveStockOpen,
    setReceiveStockOpen,
  ] =
    useState(false);


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


  const loadInventory =
    useCallback(
      async (
        showRefresh:
          boolean = false,
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
          const selectedWarehouse =
            warehouseId
              ? Number(
                  warehouseId,
                )
              : null;

          const [
            warehouseData,
            balanceData,
            movementData,
          ] =
            await Promise.all([
              getWarehouses(
                true,
              ),

              getStockBalances({
                search,

                warehouseId:
                  selectedWarehouse,

                lowStockOnly,
              }),

              getStockMovements({
                page:
                  movementPage,

                pageSize:
                  MOVEMENT_PAGE_SIZE,

                warehouseId:
                  selectedWarehouse,

                movementType,
              }),
            ]);

          setWarehouses(
            warehouseData,
          );

          setBalances(
            balanceData,
          );

          setMovements(
            movementData,
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
        search,
        warehouseId,
        lowStockOnly,
        movementPage,
        movementType,
      ],
    );


  useEffect(() => {
    if (authLoading) {
      return;
    }

    const timer =
      window.setTimeout(
        () => {
          void loadInventory();
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
    loadInventory,
  ]);


  const totalOnHand =
    useMemo(
      () =>
        balances.reduce(
          (
            total,
            item,
          ) =>
            total
            + numeric(
                item
                  .quantity_on_hand,
              ),
          0,
        ),
      [balances],
    );


  const totalAvailable =
    useMemo(
      () =>
        balances.reduce(
          (
            total,
            item,
          ) =>
            total
            + numeric(
                item
                  .quantity_available,
              ),
          0,
        ),
      [balances],
    );


  const lowStockCount =
    useMemo(
      () =>
        balances.filter(
          (item) =>
            item.is_low_stock,
        ).length,
      [balances],
    );


  const inventoryValue =
    useMemo(
      () =>
        balances.reduce(
          (
            total,
            item,
          ) =>
            total
            + (
              numeric(
                item.quantity_on_hand,
              )
              * numeric(
                  item.average_cost,
                )
            ),
          0,
        ),
      [balances],
    );


  const uniqueProducts =
    useMemo(
      () =>
        new Set(
          balances.map(
            (item) =>
              item.product_id,
          ),
        ).size,
      [balances],
    );


  function submitSearch(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

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
    setSearchInput(
      "",
    );

    setSearch(
      "",
    );

    setWarehouseId(
      "",
    );

    setLowStockOnly(
      false,
    );

    setMovementType(
      "",
    );

    setMovementPage(
      1,
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
            INVENTORY
          </p>

          <h1>
            Stock overview
          </h1>

          <p>
            Monitor stock balances,
            warehouses, low-stock items
            and recent movements.
          </p>
        </div>

        <div
          className={
            styles.inventoryHeaderActions
          }
        >
          <button
            type="button"
            className={
              styles.receiveStockButton
            }
            onClick={() =>
              setReceiveStockOpen(
                true,
              )
            }
          >
            <PackagePlus
              size={17}
            />

            Receive stock
          </button>

          <InventoryPhase4Actions
            warehouses={
              warehouses
            }
            onChanged={async () => {
              setMovementPage(
                1,
              );

              await loadInventory(
                true,
              );
            }}
          />

          <button
            type="button"
            className={
              styles.refreshButton
            }
            disabled={
              refreshing
            }
            onClick={() =>
              void loadInventory(
                true,
              )
            }
          >
            <RefreshCw
              size={17}
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
            <Boxes size={20} />
          </div>

          <div>
            <span>
              Stock items
            </span>

            <strong>
              {uniqueProducts}
            </strong>
          </div>
        </article>

        <article>
          <div
            className={
              styles.summaryIcon
            }
          >
            <PackageCheck
              size={20}
            />
          </div>

          <div>
            <span>
              On hand
            </span>

            <strong>
              {quantity(
                totalOnHand,
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
            <WarehouseIcon
              size={20}
            />
          </div>

          <div>
            <span>
              Available
            </span>

            <strong>
              {quantity(
                totalAvailable,
              )}
            </strong>
          </div>
        </article>

        <article
          className={
            lowStockCount > 0
              ? styles.warningCard
              : undefined
          }
        >
          <div
            className={
              styles.summaryIcon
            }
          >
            <AlertTriangle
              size={20}
            />
          </div>

          <div>
            <span>
              Low stock
            </span>

            <strong>
              {lowStockCount}
            </strong>
          </div>
        </article>

        <article>
          <div
            className={
              styles.summaryIcon
            }
          >
            <Building2
              size={20}
            />
          </div>

          <div>
            <span>
              Warehouses
            </span>

            <strong>
              {
                warehouses.length
              }
            </strong>
          </div>
        </article>
      </section>


      <section
        className={
          styles.valueStrip
        }
      >
        <div>
          <span>
            Estimated stock value
          </span>

          <strong>
            {money(
              inventoryValue,
            )}
          </strong>
        </div>

        <div>
          <span>
            Balance rows
          </span>

          <strong>
            {
              balances.length
            }
          </strong>
        </div>

        <div>
          <span>
            Recent movements
          </span>

          <strong>
            {
              movements.total
            }
          </strong>
        </div>
      </section>


      <section
        className={
          styles.panel
        }
      >
        <div
          className={
            styles.panelTitle
          }
        >
          <div>
            <p className="eyebrow">
              STOCK
            </p>

            <h2>
              Stock balances
            </h2>
          </div>
        </div>


        <div
          className={
            styles.toolbar
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
            <div
              className={
                styles.searchBox
              }
            >
              <Search size={18} />

              <input
                type="search"
                maxLength={100}
                value={
                  searchInput
                }
                placeholder={
                  "Search product "
                  + "name or code"
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
            </div>

            <button
              type="submit"
              className={
                styles.searchButton
              }
            >
              Search
            </button>
          </form>


          <div
            className={
              styles.filters
            }
          >
            <select
              value={
                warehouseId
              }
              onChange={
                (event) => {
                  setWarehouseId(
                    event
                      .target
                      .value,
                  );

                  setMovementPage(
                    1,
                  );
                }
              }
            >
              <option value="">
                All warehouses
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
                    {warehouse.code}
                    {" — "}
                    {warehouse.name}
                  </option>
                ),
              )}
            </select>


            <label
              className={
                styles.lowStockToggle
              }
            >
              <input
                type="checkbox"
                checked={
                  lowStockOnly
                }
                onChange={
                  (event) =>
                    setLowStockOnly(
                      event
                        .target
                        .checked,
                    )
                }
              />

              Low stock only
            </label>


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
          </div>
        </div>


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


        <div
          className={
            styles.tableWrapper
          }
        >
          <table
            className={
              styles.table
            }
          >
            <thead>
              <tr>
                <th>
                  Product
                </th>

                <th>
                  Warehouse
                </th>

                <th>
                  On hand
                </th>

                <th>
                  Reserved
                </th>

                <th>
                  Available
                </th>

                <th>
                  Average cost
                </th>

                <th>
                  Reorder
                </th>

                <th>
                  Tracking
                </th>

                <th>
                  Status
                </th>
              </tr>
            </thead>

            <tbody>
              {loading ? (
                <tr>
                  <td
                    colSpan={9}
                  >
                    <div
                      className={
                        styles.tableState
                      }
                    >
                      <div
                        className="loading-spinner"
                      />

                      Loading inventory...
                    </div>
                  </td>
                </tr>
              ) : balances.length
                === 0 ? (
                <tr>
                  <td
                    colSpan={9}
                  >
                    <div
                      className={
                        styles.emptyState
                      }
                    >
                      <Boxes
                        size={30}
                      />

                      <strong>
                        No stock balances found
                      </strong>

                      <p>
                        Receive stock or
                        change the current
                        filters.
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                balances.map(
                  (item) => (
                    <tr
                      key={
                        item.id
                      }
                      className={
                        styles.clickableStockRow
                      }
                      onClick={() =>
                        setSelectedBalance(
                          item,
                        )
                      }
                    >
                      <td>
                        <div
                          className={
                            styles.productCell
                          }
                        >
                          <div
                            className={
                              styles.productIcon
                            }
                          >
                            <Boxes
                              size={17}
                            />
                          </div>

                          <div>
                            <strong
                              className={
                                styles.stockProductLink
                              }
                            >
                              {
                                item.product_name
                              }
                            </strong>

                            <span>
                              {
                                item.product_code
                              }
                            </span>
                          </div>
                        </div>
                      </td>

                      <td>
                        <div
                          className={
                            styles.warehouseCell
                          }
                        >
                          <strong>
                            {
                              item.warehouse_code
                            }
                          </strong>

                          <span>
                            {
                              item.warehouse_name
                            }
                          </span>
                        </div>
                      </td>

                      <td>
                        <strong>
                          {quantity(
                            item
                              .quantity_on_hand,
                          )}
                        </strong>
                      </td>

                      <td>
                        {quantity(
                          item
                            .quantity_reserved,
                        )}
                      </td>

                      <td>
                        <strong
                          className={
                            styles.availableQuantity
                          }
                        >
                          {quantity(
                            item
                              .quantity_available,
                          )}
                        </strong>
                      </td>

                      <td>
                        <span
                          className={
                            styles.money
                          }
                        >
                          {money(
                            item.average_cost,
                          )}
                        </span>
                      </td>

                      <td>
                        {quantity(
                          item.reorder_level,
                        )}
                      </td>

                      <td>
                        <span
                          className={
                            item
                              .track_serial_numbers
                              ? styles.serialBadge
                              : styles.standardBadge
                          }
                        >
                          <Barcode
                            size={13}
                          />

                          {item
                            .track_serial_numbers
                            ? "Serialized"
                            : "Standard"
                          }
                        </span>
                      </td>

                      <td>
                        <span
                          className={
                            item.is_low_stock
                              ? styles.lowBadge
                              : styles.okBadge
                          }
                        >
                          {item.is_low_stock
                            ? "Low stock"
                            : "Healthy"
                          }
                        </span>
                      </td>
                    </tr>
                  ),
                )
              )}
            </tbody>
          </table>
        </div>
      </section>


      <section
        className={
          styles.panel
        }
      >
        <div
          className={
            styles.movementHeader
          }
        >
          <div>
            <p className="eyebrow">
              ACTIVITY
            </p>

            <h2>
              Stock movements
            </h2>

            <p>
              Latest inventory
              movement records.
            </p>
          </div>

          <select
            value={
              movementType
            }
            onChange={
              (event) => {
                const value =
                  event
                    .target
                    .value;

                const selected =
                  movementTypes.find(
                    (item) =>
                      item.value
                      === value,
                  );

                setMovementType(
                  selected
                    ? selected.value
                    : "",
                );

                setMovementPage(
                  1,
                );
              }
            }
          >
            <option value="">
              All movement types
            </option>

            {movementTypes.map(
              (item) => (
                <option
                  key={
                    item.value
                  }
                  value={
                    item.value
                  }
                >
                  {item.label}
                </option>
              ),
            )}
          </select>
        </div>


        <div
          className={
            styles.movementList
          }
        >
          {loading ? (
            <div
              className={
                styles.movementState
              }
            >
              Loading movements...
            </div>
          ) : movements.items.length
            === 0 ? (
            <div
              className={
                styles.movementState
              }
            >
              <History
                size={26}
              />

              <strong>
                No movements found
              </strong>

              <span>
                Stock movements will
                appear here.
              </span>
            </div>
          ) : (
            movements.items.map(
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
                      styles.movementRow
                    }
                  >
                    <div
                      className={
                        positive
                          ? styles.movementIconPositive
                          : styles.movementIconNegative
                      }
                    >
                      {positive
                        ? (
                          <ArrowDownLeft
                            size={17}
                          />
                        )
                        : (
                          <ArrowUpRight
                            size={17}
                          />
                        )
                      }
                    </div>

                    <div
                      className={
                        styles.movementMain
                      }
                    >
                      <strong>
                        {movementLabel(
                          movement
                            .movement_type,
                        )}
                      </strong>

                      <span>
                        Product #
                        {
                          movement.product_id
                        }
                        {" • "}
                        Warehouse #
                        {
                          movement.warehouse_id
                        }
                      </span>
                    </div>

                    <div
                      className={
                        styles.movementReference
                      }
                    >
                      <strong>
                        {movement
                          .reference_id
                          || "—"
                        }
                      </strong>

                      <span>
                        {movement
                          .reference_type
                          || "No reference"
                        }
                      </span>
                    </div>

                    <div
                      className={
                        styles.movementAmount
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

                    <div
                      className={
                        styles.movementDate
                      }
                    >
                      {
                        formatDate(
                          movement
                            .movement_date,
                        )
                      }
                    </div>
                  </article>
                );
              },
            )
          )}
        </div>


        <div
          className={
            styles.pagination
          }
        >
          <span>
            Page{" "}
            {movements.page} of{" "}
            {Math.max(
              movements.total_pages,
              1,
            )}
          </span>

          <div>
            <button
              type="button"
              disabled={
                loading
                || movementPage
                  <= 1
              }
              onClick={() =>
                setMovementPage(
                  (current) =>
                    Math.max(
                      1,
                      current - 1,
                    ),
                )
              }
            >
              <ChevronLeft
                size={16}
              />

              Previous
            </button>

            <button
              type="button"
              disabled={
                loading
                || movements.total_pages
                  === 0
                || movementPage
                  >= movements.total_pages
              }
              onClick={() =>
                setMovementPage(
                  (current) =>
                    current + 1,
                )
              }
            >
              Next

              <ChevronRight
                size={16}
              />
            </button>
          </div>
        </div>
      </section>
      {receiveStockOpen && (
        <ReceiveStockModal
          warehouses={
            warehouses
          }
          onClose={() =>
            setReceiveStockOpen(
              false,
            )
          }
          onReceived={async () => {
            setMovementPage(
              1,
            );

            await loadInventory(
              true,
            );
          }}
        />
      )}

      {selectedBalance !== null && (
        <InventoryDetailDrawer
          balance={
            selectedBalance
          }
          onClose={() =>
            setSelectedBalance(
              null,
            )
          }
        />
      )}
    </AppShell>
  );
}
