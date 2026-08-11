import { api } from "@/lib/api";

import type {
  Brand,
  BrandCreatePayload,
  Category,
  CategoryCreatePayload,
  Product,
  ProductCreatePayload,
  ProductListResponse,
  ProductType,
  Unit,
} from "@/types/catalog";


export type ProductListParams = {
  page?: number;
  pageSize?: number;

  search?: string;

  productType?: ProductType | "";

  trackSerialNumbers?:
    | "true"
    | "false"
    | "";
};


export async function getCategories(
  search = "",
): Promise<Category[]> {
  const response =
    await api.get<Category[]>(
      "/catalog/categories",
      {
        params: {
          search:
            search || undefined,
        },
      },
    );

  return response.data;
}


export async function createCategory(
  payload: CategoryCreatePayload,
): Promise<Category> {
  const response =
    await api.post<Category>(
      "/catalog/categories",
      payload,
    );

  return response.data;
}


export async function getBrands(
  search = "",
): Promise<Brand[]> {
  const response =
    await api.get<Brand[]>(
      "/catalog/brands",
      {
        params: {
          search:
            search || undefined,
        },
      },
    );

  return response.data;
}


export async function createBrand(
  payload: BrandCreatePayload,
): Promise<Brand> {
  const response =
    await api.post<Brand>(
      "/catalog/brands",
      payload,
    );

  return response.data;
}


export async function getUnits():
  Promise<Unit[]> {
  const response =
    await api.get<Unit[]>(
      "/catalog/units",
    );

  return response.data;
}


export async function getProducts(
  params: ProductListParams,
): Promise<ProductListResponse> {
  const response =
    await api.get<ProductListResponse>(
      "/catalog/products",
      {
        params: {
          page:
            params.page ?? 1,

          page_size:
            params.pageSize ?? 10,

          search:
            params.search || undefined,

          product_type:
            params.productType || undefined,

          track_serial_numbers:
            params.trackSerialNumbers
            || undefined,
        },
      },
    );

  return response.data;
}


export async function createProduct(
  payload: ProductCreatePayload,
): Promise<Product> {
  const response =
    await api.post<Product>(
      "/catalog/products",
      payload,
    );

  return response.data;
}


export async function getProduct(
  productId: number,
): Promise<Product> {
  const response =
    await api.get<Product>(
      `/catalog/products/${productId}`,
    );

  return response.data;
}


export async function updateProduct(
  productId: number,
  payload: import("@/types/catalog").ProductUpdatePayload,
): Promise<Product> {
  const response =
    await api.patch<Product>(
      `/catalog/products/${productId}`,
      payload,
    );

  return response.data;
}


export async function deactivateProduct(
  productId: number,
): Promise<Product> {
  const response =
    await api.delete<Product>(
      `/catalog/products/${productId}`,
    );

  return response.data;
}


export async function reactivateProduct(
  productId: number,
): Promise<Product> {
  return updateProduct(
    productId,
    {
      is_active: true,
    },
  );
}
