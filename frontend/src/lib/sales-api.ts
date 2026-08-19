import { api } from "@/lib/api";

import type {
  SalesCustomerOption,
  SalesInvoiceConfirmRequest,
  SalesInvoiceCreate,
  SalesInvoiceDetailResponse,
  SalesInvoiceListParams,
  SalesInvoiceListResponse,
  SalesInvoiceResponse,
  SalesProductOption,
  SalesSerialOption,
  SalesWarehouseOption,
} from "@/types/sales";


type UnknownRecord =
  Record<string, unknown>;


function asRecord(
  value: unknown,
): UnknownRecord {
  if (
    value !== null
    && typeof value === "object"
    && !Array.isArray(value)
  ) {
    return value as UnknownRecord;
  }

  return {};
}


function asArray(
  value: unknown,
): unknown[] {
  if (Array.isArray(value)) {
    return value;
  }

  const record =
    asRecord(value);

  if (
    Array.isArray(
      record.items,
    )
  ) {
    return record.items;
  }

  return [];
}


function asString(
  value: unknown,
  fallback = "",
): string {
  return (
    typeof value === "string"
      ? value
      : fallback
  );
}


function asNumber(
  value: unknown,
): number {
  const number =
    Number(value);

  return (
    Number.isFinite(number)
      ? number
      : 0
  );
}


function asBoolean(
  value: unknown,
  fallback = false,
): boolean {
  return (
    typeof value === "boolean"
      ? value
      : fallback
  );
}


export async function getSalesInvoices(
  params:
    SalesInvoiceListParams = {},
): Promise<SalesInvoiceListResponse> {
  const response =
    await api.get<
      SalesInvoiceListResponse
    >(
      "/sales/invoices",
      {
        params: {
          page:
            params.page
            ?? 1,

          page_size:
            params.pageSize
            ?? 20,

          search:
            params.search
            || undefined,

          invoice_status:
            params.invoiceStatus
            || undefined,

          payment_status:
            params.paymentStatus
            || undefined,
        },
      },
    );

  return response.data;
}


export async function getSalesInvoice(
  invoiceId: number,
): Promise<SalesInvoiceDetailResponse> {
  const response =
    await api.get<
      SalesInvoiceDetailResponse
    >(
      `/sales/invoices/${invoiceId}`,
    );

  return response.data;
}


export async function createSalesInvoice(
  payload:
    SalesInvoiceCreate,
): Promise<SalesInvoiceResponse> {
  const response =
    await api.post<
      SalesInvoiceResponse
    >(
      "/sales/invoices",
      payload,
    );

  return response.data;
}


export async function confirmSalesInvoice(
  invoiceId: number,
  payload:
    SalesInvoiceConfirmRequest,
): Promise<SalesInvoiceDetailResponse> {
  const response =
    await api.post<
      SalesInvoiceDetailResponse
    >(
      `/sales/invoices/${invoiceId}/confirm`,
      payload,
    );

  return response.data;
}


export async function getSalesCustomers(
  search?: string,
): Promise<SalesCustomerOption[]> {
  const response =
    await api.get<unknown>(
      "/customers",
      {
        params: {
          page: 1,
          page_size: 100,
          is_active: true,
          search:
            search?.trim()
            || undefined,
        },
      },
    );

  return asArray(
    response.data,
  ).map(
    (raw) => {
      const item =
        asRecord(raw);

      return {
        id:
          asNumber(
            item.id,
          ),

        customer_code:
          asString(
            item.customer_code,
          )
          || null,

        full_name:
          asString(
            item.full_name,
            "Unnamed customer",
          ),

        phone:
          (
            asString(
              item.phone,
            )
            || null
          ),

        mobile_number:
          (
            asString(
              item.mobile_number,
            )
            || null
          ),

        nic_number:
          (
            asString(
              item.nic_number,
            )
            || null
          ),

        customer_type:
          asString(
            item.customer_type,
          ),

        credit_status:
          asString(
            item.credit_status,
          ),

        is_active:
          asBoolean(
            item.is_active,
            true,
          ),
      };
    },
  ).filter(
    (item) =>
      item.id > 0
      && item.is_active,
  );
}


export async function getSalesProducts(
  search?: string,
): Promise<SalesProductOption[]> {
  const response =
    await api.get<unknown>(
      "/catalog/products",
      {
        params: {
          page: 1,
          page_size: 100,
          is_active: true,
          search:
            search?.trim()
            || undefined,
        },
      },
    );

  return asArray(
    response.data,
  ).map(
    (raw) => {
      const item =
        asRecord(raw);

      return {
        id:
          asNumber(
            item.id,
          ),

        product_code:
          asString(
            item.product_code,
          ),

        name:
          asString(
            item.name,
            "Unnamed product",
          ),

        selling_price:
          typeof item.selling_price
            === "number"
            || typeof item.selling_price
              === "string"
              ? item.selling_price
              : 0,

        minimum_selling_price:
          typeof item.minimum_selling_price
            === "number"
            || typeof item.minimum_selling_price
              === "string"
              ? item.minimum_selling_price
              : null,

        track_serial_numbers:
          asBoolean(
            item.track_serial_numbers,
          ),

        is_active:
          asBoolean(
            item.is_active,
            true,
          ),
      };
    },
  ).filter(
    (item) =>
      item.id > 0
      && item.is_active,
  );
}


export async function getSalesWarehouses():
Promise<SalesWarehouseOption[]> {
  const response =
    await api.get<unknown>(
      "/inventory/warehouses",
      {
        params: {
          active_only:
            true,
        },
      },
    );

  return asArray(
    response.data,
  ).map(
    (raw) => {
      const item =
        asRecord(raw);

      return {
        id:
          asNumber(
            item.id,
          ),

        branch_id:
          asNumber(
            item.branch_id,
          ),

        code:
          asString(
            item.code,
          ),

        name:
          asString(
            item.name,
            "Warehouse",
          ),

        is_active:
          asBoolean(
            item.is_active,
            true,
          ),
      };
    },
  ).filter(
    (item) =>
      item.id > 0
      && item.is_active,
  );
}


export async function getAvailableSalesSerials(
  productId: number,
  warehouseId: number,
): Promise<SalesSerialOption[]> {
  const response =
    await api.get<unknown>(
      "/inventory/serial-numbers",
      {
        params: {
          product_id:
            productId,

          warehouse_id:
            warehouseId,

          serial_status:
            "available",
        },
      },
    );

  return asArray(
    response.data,
  ).map(
    (raw) => {
      const item =
        asRecord(raw);

      const warehouseValue =
        item.warehouse_id;

      return {
        id:
          asNumber(
            item.id,
          ),

        serial_number:
          asString(
            item.serial_number,
          ),

        product_id:
          asNumber(
            item.product_id,
          ),

        warehouse_id:
          warehouseValue
          == null
            ? null
            : asNumber(
                warehouseValue,
              ),

        status:
          asString(
            item.status,
          ),

        current_customer_id:
          item.current_customer_id
          == null
            ? null
            : asNumber(
                item.current_customer_id,
              ),
      };
    },
  ).filter(
    (item) =>
      item.id > 0
      && item.status
        === "available"
      && item.product_id
        === productId
      && item.warehouse_id
        === warehouseId
      && item.current_customer_id
        == null,
  );
}
