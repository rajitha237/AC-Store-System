import { api } from "@/lib/api";

import type {
  Customer,
  CustomerCreatePayload,
  CustomerListResponse,
  CustomerUpdatePayload,
} from "@/types/customer";


export type CustomerListParams = {
  page?: number;
  pageSize?: number;
  search?: string;
  customerType?: string;
  customerStatus?: string;
};


export async function getCustomers(
  params: CustomerListParams,
): Promise<CustomerListResponse> {
  const response =
    await api.get<CustomerListResponse>(
      "/customers",
      {
        params: {
          page:
            params.page ?? 1,

          page_size:
            params.pageSize ?? 20,

          search:
            params.search || undefined,

          customer_type:
            params.customerType || undefined,

          customer_status:
            params.customerStatus || undefined,
        },
      },
    );

  return response.data;
}


export async function createCustomer(
  payload: CustomerCreatePayload,
): Promise<Customer> {
  const response =
    await api.post<Customer>(
      "/customers",
      payload,
    );

  return response.data;
}


export async function getCustomer(
  customerId: number,
): Promise<Customer> {
  const response =
    await api.get<Customer>(
      `/customers/${customerId}`,
    );

  return response.data;
}


export async function updateCustomer(
  customerId: number,
  payload: CustomerUpdatePayload,
): Promise<Customer> {
  const response =
    await api.patch<Customer>(
      `/customers/${customerId}`,
      payload,
    );

  return response.data;
}


export async function deactivateCustomer(
  customerId: number,
): Promise<Customer> {
  const response =
    await api.delete<Customer>(
      `/customers/${customerId}`,
    );

  return response.data;
}


export async function reactivateCustomer(
  customerId: number,
): Promise<Customer> {
  return updateCustomer(
    customerId,
    {
      status: "active",
    },
  );
}
