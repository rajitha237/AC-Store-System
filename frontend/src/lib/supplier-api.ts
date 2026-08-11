import {
  api,
} from "@/lib/api";

import type {
  Supplier,
  SupplierCreatePayload,
  SupplierListParams,
  SupplierListResponse,
  SupplierUpdatePayload,
} from "@/types/supplier";


export async function getSuppliers(
  params:
    SupplierListParams = {},
): Promise<
  SupplierListResponse
> {
  const response =
    await api.get<
      SupplierListResponse
    >(
      "/suppliers",
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

          is_active:
            params.isActive,
        },
      },
    );

  return response.data;
}


export async function getSupplier(
  supplierId:
    number,
): Promise<Supplier> {
  const response =
    await api.get<Supplier>(
      `/suppliers/${supplierId}`,
    );

  return response.data;
}


export async function createSupplier(
  payload:
    SupplierCreatePayload,
): Promise<Supplier> {
  const response =
    await api.post<Supplier>(
      "/suppliers",
      payload,
    );

  return response.data;
}


export async function updateSupplier(
  supplierId:
    number,

  payload:
    SupplierUpdatePayload,
): Promise<Supplier> {
  const response =
    await api.patch<Supplier>(
      `/suppliers/${supplierId}`,
      payload,
    );

  return response.data;
}


export async function deactivateSupplier(
  supplierId:
    number,
): Promise<Supplier> {
  const response =
    await api.delete<Supplier>(
      `/suppliers/${supplierId}`,
    );

  return response.data;
}


export async function activateSupplier(
  supplierId:
    number,
): Promise<Supplier> {
  return updateSupplier(
    supplierId,
    {
      is_active:
        true,
    },
  );
}
