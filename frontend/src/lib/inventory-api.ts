import { api } from "@/lib/api";

import type {
  NormalizedMovementList,
  StockBalance,
  StockMovement,
  StockMovementListResponse,
  StockMovementType,
  Warehouse,
} from "@/types/inventory";


export type BalanceParams = {
  search?: string;

  warehouseId?: number | null;
  productId?: number | null;

  lowStockOnly?: boolean;
};


export type MovementParams = {
  page?: number;
  pageSize?: number;

  productId?: number | null;
  warehouseId?: number | null;
  serialNumberId?: number | null;

  movementType?:
    | StockMovementType
    | "";
};


export async function getWarehouses(
  isActive: boolean | null = true,
): Promise<Warehouse[]> {
  const response =
    await api.get<Warehouse[]>(
      "/inventory/warehouses",
      {
        params: {
          is_active:
            isActive === null
              ? undefined
              : isActive,
        },
      },
    );

  return response.data;
}


export async function getStockBalances(
  params: BalanceParams = {},
): Promise<StockBalance[]> {
  const response =
    await api.get<StockBalance[]>(
      "/inventory/balances",
      {
        params: {
          search:
            params.search
            || undefined,

          warehouse_id:
            params.warehouseId
            || undefined,

          product_id:
            params.productId
            || undefined,

          low_stock_only:
            params.lowStockOnly
            ?? false,
        },
      },
    );

  return response.data;
}


export async function getStockMovements(
  params: MovementParams = {},
): Promise<NormalizedMovementList> {
  const response =
    await api.get<
      StockMovementListResponse
      | StockMovement[]
    >(
      "/inventory/movements",
      {
        params: {
          page:
            params.page ?? 1,

          page_size:
            params.pageSize ?? 10,

          product_id:
            params.productId
            || undefined,

          warehouse_id:
            params.warehouseId
            || undefined,

          serial_number_id:
            params.serialNumberId
            || undefined,

          movement_type:
            params.movementType
            || undefined,
        },
      },
    );

  if (
    Array.isArray(
      response.data,
    )
  ) {
    return {
      items:
        response.data,

      total:
        response.data.length,

      page:
        1,

      page_size:
        response.data.length,

      total_pages:
        1,
    };
  }

  const raw =
    response.data;

  const items =
    raw.items
    ?? raw.movements
    ?? [];

  return {
    items,

    total:
      raw.total
      ?? items.length,

    page:
      raw.page
      ?? params.page
      ?? 1,

    page_size:
      raw.page_size
      ?? params.pageSize
      ?? 10,

    total_pages:
      raw.total_pages
      ?? (
        items.length > 0
          ? 1
          : 0
      ),
  };
}


export type SerialNumberParams = {
  search?: string;

  productId?: number | null;
  warehouseId?: number | null;

  serialStatus?: string;
};


export async function getSerialNumbers(
  params: SerialNumberParams = {},
): Promise<
  import("@/types/inventory").SerialNumberDetail[]
> {
  const response =
    await api.get<
      import("@/types/inventory").SerialNumberDetail[]
    >(
      "/inventory/serial-numbers",
      {
        params: {
          search:
            params.search
            || undefined,

          product_id:
            params.productId
            || undefined,

          warehouse_id:
            params.warehouseId
            || undefined,

          serial_status:
            params.serialStatus
            || undefined,
        },
      },
    );

  return response.data;
}


export async function getSerialNumber(
  serialNumberId: number,
): Promise<
  import("@/types/inventory").SerialNumberDetail
> {
  const response =
    await api.get<
      import("@/types/inventory").SerialNumberDetail
    >(
      `/inventory/serial-numbers/${serialNumberId}`,
    );

  return response.data;
}



// INVENTORY PHASE 3 - RECEIVE STOCK API

export async function receiveNonSerializedStock(
  payload:
    import("@/types/inventory")
      .NonSerializedReceivePayload,
): Promise<
  import("@/types/inventory")
    .StockReceiveResponse
> {
  const response =
    await api.post<
      import("@/types/inventory")
        .StockReceiveResponse
    >(
      "/inventory/receive/non-serialized",
      payload,
    );

  return response.data;
}


export async function receiveSerializedStock(
  payload:
    import("@/types/inventory")
      .SerializedReceivePayload,
): Promise<
  import("@/types/inventory")
    .StockReceiveResponse
> {
  const response =
    await api.post<
      import("@/types/inventory")
        .StockReceiveResponse
    >(
      "/inventory/receive/serialized",
      payload,
    );

  return response.data;
}


export async function adjustStock(
  payload:
    import("@/types/inventory")
      .StockAdjustmentPayload,
): Promise<
  import("@/types/inventory")
    .StockAdjustmentResult
> {
  const response =
    await api.post<
      import("@/types/inventory")
        .StockAdjustmentResult
    >(
      "/inventory/adjust",
      payload,
    );

  return response.data;
}


export async function transferNonSerializedStock(
  payload:
    import("@/types/inventory")
      .NonSerializedTransferPayload,
): Promise<
  import("@/types/inventory")
    .NonSerializedTransferResult
> {
  const response =
    await api.post<
      import("@/types/inventory")
        .NonSerializedTransferResult
    >(
      "/inventory/transfer/non-serialized",
      payload,
    );

  return response.data;
}


export async function transferSerializedStock(
  payload:
    import("@/types/inventory")
      .SerializedTransferPayload,
): Promise<
  import("@/types/inventory")
    .SerializedTransferResult
> {
  const response =
    await api.post<
      import("@/types/inventory")
        .SerializedTransferResult
    >(
      "/inventory/transfer/serialized",
      payload,
    );

  return response.data;
}
