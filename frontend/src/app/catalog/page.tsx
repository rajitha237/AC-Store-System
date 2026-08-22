"use client";

import axios from "axios";

import {
  Barcode,
  Boxes,
  Building2,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Layers3,
  Package,
  Plus,
  Search,
  Tag,
  X,
} from "lucide-react";

import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import {
  ProductDetailsModal,
} from "@/components/product-details-modal";

import {
  createBrand,
  createCategory,
  createProduct,
  getBrands,
  getCategories,
  getProducts,
  getUnits,
} from "@/lib/catalog-api";

import {
  clearAuthSession,
  getAccessToken,
  getStoredUser,
} from "@/lib/auth";

import type {
  Brand,
  Category,
  ProductCreatePayload,
  ProductListResponse,
  ProductType,
  Unit,
} from "@/types/catalog";

import type {
  UserResponse,
} from "@/types/auth";

import styles from "./catalog.module.css";


const PAGE_SIZE = 10;


const productTypes: {
  value: ProductType;
  label: string;
}[] = [
  {
    value: "equipment",
    label: "Equipment",
  },
  {
    value: "spare_part",
    label: "Spare part",
  },
  {
    value: "installation_material",
    label: "Installation material",
  },
  {
    value: "accessory",
    label: "Accessory",
  },
  {
    value: "consumable",
    label: "Consumable",
  },
  {
    value: "service_item",
    label: "Service item",
  },
];


type ProductForm = {
  barcode: string;

  category_id: string;
  brand_id: string;
  unit_id: string;

  name: string;
  model_number: string;
  description: string;

  btu_capacity: string;

  product_type: ProductType;

  track_serial_numbers: boolean;

  purchase_cost: string;
  selling_price: string;
  minimum_selling_price: string;

  warranty_months: string;

  reorder_level: string;
  reorder_quantity: string;

  technical_notes: string;
};


type LookupForm = {
  code: string;
  name: string;
  description: string;
};


const emptyProductForm:
  ProductForm = {
    barcode: "",

    category_id: "",
    brand_id: "",
    unit_id: "",

    name: "",
    model_number: "",
    description: "",

    btu_capacity: "",

    product_type:
      "equipment",

    track_serial_numbers:
      false,

    purchase_cost:
      "0.00",

    selling_price:
      "0.00",

    minimum_selling_price:
      "0.00",

    warranty_months:
      "0",

    reorder_level:
      "0.000",

    reorder_quantity:
      "0.000",

    technical_notes:
      "",
  };


const emptyLookupForm:
  LookupForm = {
    code: "",
    name: "",
    description: "",
  };


function optional(
  value: string,
): string | null {
  const clean =
    value.trim();

  return clean || null;
}


function formatMoney(
  value: string | number,
): string {
  const amount =
    Number(value ?? 0);

  if (!Number.isFinite(amount)) {
    return "LKR 0.00";
  }

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
  ).format(amount);
}


function typeLabel(
  value: string,
): string {
  return value
    .split("_")
    .map(
      (part) =>
        part.charAt(0).toUpperCase()
        + part.slice(1),
    )
    .join(" ");
}


function apiError(
  error: unknown,
): string {
  if (!axios.isAxiosError(error)) {
    return (
      "Something went wrong. "
      + "Please try again."
    );
  }

  const detail =
    error.response?.data?.detail;

  if (
    typeof detail === "string"
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
    error.response?.status === 403
  ) {
    return (
      "You do not have permission "
      + "to perform this action."
    );
  }

  if (
    error.response?.status === 409
  ) {
    return (
      "A record with the same "
      + "code or barcode already exists."
    );
  }

  return (
    "Unable to complete the request."
  );
}


export default function CatalogPage() {
  const router =
    useRouter();

  const [
    user,
    setUser,
  ] =
    useState<UserResponse | null>(
      null,
    );

  const [
    authLoading,
    setAuthLoading,
  ] =
    useState(true);


  const [
    data,
    setData,
  ] =
    useState<ProductListResponse>({
      items: [],
      total: 0,
      page: 1,
      page_size: PAGE_SIZE,
      total_pages: 0,
    });

  const [
    categories,
    setCategories,
  ] =
    useState<Category[]>([]);

  const [
    brands,
    setBrands,
  ] =
    useState<Brand[]>([]);

  const [
    units,
    setUnits,
  ] =
    useState<Unit[]>([]);


  const [
    page,
    setPage,
  ] =
    useState(1);

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
    productType,
    setProductType,
  ] =
    useState<ProductType | "">(
      "",
    );

  const [
    serialFilter,
    setSerialFilter,
  ] =
    useState<
      "true"
      | "false"
      | ""
    >("");


  const [
    loading,
    setLoading,
  ] =
    useState(true);

  const [
    lookupLoading,
    setLookupLoading,
  ] =
    useState(true);

  const [
    error,
    setError,
  ] =
    useState("");


  const [
    productModalOpen,
    setProductModalOpen,
  ] =
    useState(false);

  const [
    productForm,
    setProductForm,
  ] =
    useState<ProductForm>(
      emptyProductForm,
    );

  const [
    productSaving,
    setProductSaving,
  ] =
    useState(false);

  const [
    productError,
    setProductError,
  ] =
    useState("");

  const [
    selectedProductId,
    setSelectedProductId,
  ] =
    useState<number | null>(
      null,
    );


  const [
    lookupMode,
    setLookupMode,
  ] =
    useState<
      "category"
      | "brand"
      | null
    >(null);

  const [
    lookupForm,
    setLookupForm,
  ] =
    useState<LookupForm>(
      emptyLookupForm,
    );

  const [
    lookupSaving,
    setLookupSaving,
  ] =
    useState(false);

  const [
    lookupError,
    setLookupError,
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


  const loadLookups =
    useCallback(
      async () => {
        setLookupLoading(
          true,
        );

        try {
          const [
            categoryData,
            brandData,
            unitData,
          ] =
            await Promise.all([
              getCategories(),
              getBrands(),
              getUnits(),
            ]);

          setCategories(
            categoryData,
          );

          setBrands(
            brandData,
          );

          setUnits(
            unitData,
          );
        } catch (requestError) {
          setError(
            apiError(
              requestError,
            ),
          );
        } finally {
          setLookupLoading(
            false,
          );
        }
      },
      [],
    );


  const loadProducts =
    useCallback(
      async () => {
        setLoading(
          true,
        );

        setError(
          "",
        );

        try {
          const response =
            await getProducts({
              page,

              pageSize:
                PAGE_SIZE,

              search,

              productType,

              trackSerialNumbers:
                serialFilter,
            });

          setData(
            response,
          );
        } catch (requestError) {
          setError(
            apiError(
              requestError,
            ),
          );
        } finally {
          setLoading(
            false,
          );
        }
      },
      [
        page,
        search,
        productType,
        serialFilter,
      ],
    );


  useEffect(() => {
    if (authLoading) {
      return;
    }

    const timer =
      window.setTimeout(
        () => {
          void Promise.all([
            loadProducts(),
            loadLookups(),
          ]);
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
    loadLookups,
    loadProducts,
  ]);


  const activeCategories =
    useMemo(
      () =>
        categories.filter(
          (item) =>
            item.is_active,
        ),
      [categories],
    );


  const activeBrands =
    useMemo(
      () =>
        brands.filter(
          (item) =>
            item.is_active,
        ),
      [brands],
    );


  const activeUnits =
    useMemo(
      () =>
        units.filter(
          (item) =>
            item.is_active,
        ),
      [units],
    );


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
        .slice(0, 100),
    );
  }


  function clearFilters() {
    setSearchInput(
      "",
    );

    setSearch(
      "",
    );

    setProductType(
      "",
    );

    setSerialFilter(
      "",
    );

    setPage(
      1,
    );
  }


  function openProductModal() {
    const firstCategory =
      activeCategories[0];

    const firstUnit =
      activeUnits[0];

    setProductForm({
      ...emptyProductForm,

      category_id:
        firstCategory
          ? String(
              firstCategory.id,
            )
          : "",

      unit_id:
        firstUnit
          ? String(
              firstUnit.id,
            )
          : "",
    });

    setProductError(
      "",
    );

    setProductModalOpen(
      true,
    );
  }


  function closeProductModal() {
    if (productSaving) {
      return;
    }

    setProductModalOpen(
      false,
    );

    setProductError(
      "",
    );
  }


  async function submitProduct(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setProductError(
      "",
    );

    if (
      productForm.name
        .trim()
        .length < 2
    ) {
      setProductError(
        "Product name is required.",
      );

      return;
    }

    const categoryId =
      Number(
        productForm.category_id,
      );

    const unitId =
      Number(
        productForm.unit_id,
      );

    if (
      !Number.isInteger(
        categoryId,
      )
      || categoryId < 1
    ) {
      setProductError(
        "Please select a category.",
      );

      return;
    }

    if (
      !Number.isInteger(
        unitId,
      )
      || unitId < 1
    ) {
      setProductError(
        "Please select a unit.",
      );

      return;
    }

    const sellingPrice =
      Number(
        productForm.selling_price,
      );

    const minimumPrice =
      Number(
        productForm.minimum_selling_price,
      );

    if (
      minimumPrice
      > sellingPrice
    ) {
      setProductError(
        "Minimum selling price cannot "
        + "be higher than selling price.",
      );

      return;
    }

    const brandId =
      productForm.brand_id
        ? Number(
            productForm.brand_id,
          )
        : null;

    const payload:
      ProductCreatePayload = {
        barcode:
          optional(
            productForm.barcode,
          ),

        category_id:
          categoryId,

        brand_id:
          brandId,

        unit_id:
          unitId,

        name:
          productForm.name.trim(),

        model_number:
          optional(
            productForm.model_number,
          ),

        description:
          optional(
            productForm.description,
          ),

        btu_capacity:
          productForm.btu_capacity
            ? Number(
                productForm.btu_capacity,
              )
            : null,

        product_type:
          productForm.product_type,

        track_serial_numbers:
          productForm
            .track_serial_numbers,

        purchase_cost:
          productForm.purchase_cost
          || "0.00",

        selling_price:
          productForm.selling_price
          || "0.00",

        minimum_selling_price:
          productForm
            .minimum_selling_price
          || "0.00",

        warranty_months:
          Number(
            productForm
              .warranty_months
            || 0,
          ),

        reorder_level:
          productForm.reorder_level
          || "0.000",

        reorder_quantity:
          productForm
            .reorder_quantity
          || "0.000",

        image_path:
          null,

        technical_notes:
          optional(
            productForm
              .technical_notes,
          ),
      };

    setProductSaving(
      true,
    );

    try {
      await createProduct(
        payload,
      );

      setProductModalOpen(
        false,
      );

      setPage(
        1,
      );

      await Promise.all([
        loadProducts(),
        loadLookups(),
      ]);
    } catch (requestError) {
      setProductError(
        apiError(
          requestError,
        ),
      );
    } finally {
      setProductSaving(
        false,
      );
    }
  }


  function openLookup(
    mode:
      | "category"
      | "brand",
  ) {
    setLookupMode(
      mode,
    );

    setLookupForm(
      emptyLookupForm,
    );

    setLookupError(
      "",
    );
  }


  function closeLookup() {
    if (lookupSaving) {
      return;
    }

    setLookupMode(
      null,
    );

    setLookupError(
      "",
    );
  }


  async function submitLookup(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (!lookupMode) {
      return;
    }

    setLookupError(
      "",
    );

    if (
      lookupForm.code
        .trim()
        .length < 1
    ) {
      setLookupError(
        "Code is required.",
      );

      return;
    }

    if (
      lookupForm.name
        .trim()
        .length < 2
    ) {
      setLookupError(
        "Name is required.",
      );

      return;
    }

    setLookupSaving(
      true,
    );

    try {
      const payload = {
        code:
          lookupForm.code.trim(),

        name:
          lookupForm.name.trim(),

        description:
          optional(
            lookupForm.description,
          ),
      };

      if (
        lookupMode === "category"
      ) {
        await createCategory(
          payload,
        );
      } else {
        await createBrand(
          payload,
        );
      }

      setLookupMode(
        null,
      );

      await loadLookups();
    } catch (requestError) {
      setLookupError(
        apiError(
          requestError,
        ),
      );
    } finally {
      setLookupSaving(
        false,
      );
    }
  }


  if (
    authLoading
    || !user
  ) {
    return (
      <main className="page-center">
        <div className="loading-spinner" />
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
            CATALOG
          </p>

          <h1>
            Products
          </h1>

          <p>
            Manage product catalog,
            pricing, serial tracking
            and stock configuration.
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
              styles.secondaryButton
            }
            onClick={() =>
              openLookup(
                "category",
              )
            }
          >
            <Layers3 size={17} />
            Category
          </button>

          <button
            type="button"
            className={
              styles.secondaryButton
            }
            onClick={() =>
              openLookup(
                "brand",
              )
            }
          >
            <Tag size={17} />
            Brand
          </button>

          <button
            type="button"
            className={
              styles.primaryButton
            }
            disabled={
              lookupLoading
              || activeCategories.length
                === 0
              || activeUnits.length
                === 0
            }
            onClick={
              openProductModal
            }
          >
            <Plus size={18} />
            Add product
          </button>
        </div>
      </section>


      <section
        className={
          styles.summaryGrid
        }
      >
        <article>
          <Package size={20} />

          <div>
            <span>
              Products
            </span>

            <strong>
              {data.total}
            </strong>
          </div>
        </article>

        <article>
          <Layers3 size={20} />

          <div>
            <span>
              Categories
            </span>

            <strong>
              {
                activeCategories.length
              }
            </strong>
          </div>
        </article>

        <article>
          <Building2 size={20} />

          <div>
            <span>
              Brands
            </span>

            <strong>
              {
                activeBrands.length
              }
            </strong>
          </div>
        </article>

        <article>
          <Boxes size={20} />

          <div>
            <span>
              Units
            </span>

            <strong>
              {
                activeUnits.length
              }
            </strong>
          </div>
        </article>
      </section>


      {(
        activeCategories.length === 0
        || activeUnits.length === 0
      ) && !lookupLoading && (
        <div
          className={
            styles.warningBanner
          }
        >
          <CircleAlert
            size={17}
          />

          {activeCategories.length
          === 0
            ? (
              "Create at least one active "
              + "category before adding products."
            )
            : (
              "No active units are available. "
              + "Check backend seed data."
            )
          }
        </div>
      )}


      <section
        className={
          styles.panel
        }
      >
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
                  "Search name, code, "
                  + "barcode or model"
                }
                onChange={
                  (event) =>
                    setSearchInput(
                      event.target.value,
                    )
                }
              />
            </div>

            <button
              type="submit"
              className={
                styles.darkButton
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
                productType
              }
              onChange={
                (event) => {
                  const value =
                    event.target.value;

                  const next:
                    ProductType | "" =
                    productTypes.some(
                      (item) =>
                        item.value
                        === value,
                    )
                      ? (value as ProductType)
                      : "";

                  setPage(
                    1,
                  );

                  setProductType(
                    next,
                  );
                }
              }
            >
              <option value="">
                All types
              </option>

              {productTypes.map(
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

            <select
              value={
                serialFilter
              }
              onChange={
                (event) => {
                  const value =
                    event.target.value;

                  setPage(
                    1,
                  );

                  setSerialFilter(
                    value === "true"
                      ? "true"
                      : value === "false"
                        ? "false"
                        : "",
                  );
                }
              }
            >
              <option value="">
                All tracking
              </option>

              <option value="true">
                Serialized
              </option>

              <option value="false">
                Non-serialized
              </option>
            </select>

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
                  Category / Brand
                </th>

                <th>
                  Type
                </th>

                <th>
                  Selling price
                </th>

                <th>
                  Serial tracking
                </th>

                <th>
                  Status
                </th>
              </tr>
            </thead>

            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6}>
                    <div
                      className={
                        styles.tableState
                      }
                    >
                      <div
                        className="loading-spinner"
                      />

                      Loading products...
                    </div>
                  </td>
                </tr>
              ) : data.items.length
                === 0 ? (
                <tr>
                  <td colSpan={6}>
                    <div
                      className={
                        styles.emptyState
                      }
                    >
                      <Package size={30} />

                      <strong>
                        No products found
                      </strong>

                      <p>
                        Add a product or
                        change the current
                        filters.
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                data.items.map(
                  (product) => (
                    <tr
                      key={
                        product.id
                      }
                      className={
                        styles.clickableRow
                      }
                      onClick={() =>
                        setSelectedProductId(
                          product.id,
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
                            <Package
                              size={18}
                            />
                          </div>

                          <div>
                            <strong
                              className={
                                styles.productNameLink
                              }
                            >
                              {product.name}
                            </strong>

                            <span>
                              {
                                product.product_code
                              }
                            </span>

                            <small>
                              {product.model_number
                                || product.barcode
                                || "No model/barcode"
                              }
                            </small>
                          </div>
                        </div>
                      </td>

                      <td>
                        <div
                          className={
                            styles.metaCell
                          }
                        >
                          <strong>
                            {
                              product.category
                                ?.name
                              || "—"
                            }
                          </strong>

                          <span>
                            {
                              product.brand
                                ?.name
                              || "No brand"
                            }
                          </span>
                        </div>
                      </td>

                      <td>
                        <span
                          className={
                            styles.typeBadge
                          }
                        >
                          {typeLabel(
                            product.product_type,
                          )}
                        </span>
                      </td>

                      <td>
                        <strong
                          className={
                            styles.price
                          }
                        >
                          {formatMoney(
                            product.selling_price,
                          )}
                        </strong>
                      </td>

                      <td>
                        <span
                          className={
                            product
                              .track_serial_numbers
                              ? styles.serialBadge
                              : styles.normalBadge
                          }
                        >
                          <Barcode
                            size={13}
                          />

                          {
                            product
                              .track_serial_numbers
                              ? "Serialized"
                              : "Standard"
                          }
                        </span>
                      </td>

                      <td>
                        <span
                          className={
                            product.is_active
                              ? styles.activeBadge
                              : styles.inactiveBadge
                          }
                        >
                          {product.is_active
                            ? "Active"
                            : "Inactive"
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


        <div
          className={
            styles.pagination
          }
        >
          <span>
            Page {data.page} of{" "}
            {Math.max(
              data.total_pages,
              1,
            )}
          </span>

          <div>
            <button
              type="button"
              disabled={
                loading
                || page <= 1
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
                size={16}
              />

              Previous
            </button>

            <button
              type="button"
              disabled={
                loading
                || data.total_pages
                  === 0
                || page
                  >= data.total_pages
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
                size={16}
              />
            </button>
          </div>
        </div>
      </section>


      {selectedProductId !== null && (
        <ProductDetailsModal
          productId={
            selectedProductId
          }
          categories={
            categories
          }
          brands={
            brands
          }
          units={
            units
          }
          onClose={() =>
            setSelectedProductId(
              null,
            )
          }
          onChanged={async () => {
            await Promise.all([
              loadProducts(),
              loadLookups(),
            ]);
          }}
        />
      )}

      {productModalOpen && (
        <div
          className={
            styles.modalBackdrop
          }
        >
          <section
            className={
              styles.modal
            }
            role="dialog"
            aria-modal="true"
            aria-labelledby={
              "add-product-title"
            }
          >
            <header
              className={
                styles.modalHeader
              }
            >
              <div>
                <p className="eyebrow">
                  NEW PRODUCT
                </p>

                <h2
                  id="add-product-title"
                >
                  Add product
                </h2>

                <p>
                  Create a product for
                  inventory, sales and
                  service operations.
                </p>
              </div>

              <button
                type="button"
                className={
                  styles.closeButton
                }
                disabled={
                  productSaving
                }
                onClick={
                  closeProductModal
                }
              >
                <X size={20} />
              </button>
            </header>


            <form
              className={
                styles.form
              }
              onSubmit={
                submitProduct
              }
            >
              <section
                className={
                  styles.formSection
                }
              >
                <h3>
                  Product identity
                </h3>

                <div
                  className={
                    styles.formGrid
                  }
                >
                  <label
                    className={
                      styles.fullField
                    }
                  >
                    Product name *

                    <input
                      type="text"
                      required
                      minLength={2}
                      maxLength={200}
                      value={
                        productForm.name
                      }
                      onChange={
                        (event) =>
                          setProductForm({
                            ...productForm,
                            name:
                              event.target.value,
                          })
                      }
                    />
                  </label>

                  <label>
                    Category *

                    <select
                      required
                      value={
                        productForm
                          .category_id
                      }
                      onChange={
                        (event) =>
                          setProductForm({
                            ...productForm,
                            category_id:
                              event.target.value,
                          })
                      }
                    >
                      <option value="">
                        Select category
                      </option>

                      {activeCategories.map(
                        (category) => (
                          <option
                            key={
                              category.id
                            }
                            value={
                              category.id
                            }
                          >
                            {
                              category.name
                            }
                          </option>
                        ),
                      )}
                    </select>
                  </label>

                  <label>
                    Brand

                    <select
                      value={
                        productForm.brand_id
                      }
                      onChange={
                        (event) =>
                          setProductForm({
                            ...productForm,
                            brand_id:
                              event.target.value,
                          })
                      }
                    >
                      <option value="">
                        No brand
                      </option>

                      {activeBrands.map(
                        (brand) => (
                          <option
                            key={
                              brand.id
                            }
                            value={
                              brand.id
                            }
                          >
                            {brand.name}
                          </option>
                        ),
                      )}
                    </select>
                  </label>

                  <label>
                    Unit *

                    <select
                      required
                      value={
                        productForm.unit_id
                      }
                      onChange={
                        (event) =>
                          setProductForm({
                            ...productForm,
                            unit_id:
                              event.target.value,
                          })
                      }
                    >
                      <option value="">
                        Select unit
                      </option>

                      {activeUnits.map(
                        (unit) => (
                          <option
                            key={
                              unit.id
                            }
                            value={
                              unit.id
                            }
                          >
                            {unit.name}
                            {" "}
                            ({unit.code})
                          </option>
                        ),
                      )}
                    </select>
                  </label>

                  <label>
                    Product type *

                    <select
                      value={
                        productForm
                          .product_type
                      }
                      onChange={
                        (event) => {
                          const value =
                            event.target.value;

                          const valid =
                            productTypes.find(
                              (item) =>
                                item.value
                                === value,
                            );

                          setProductForm({
                            ...productForm,
                            product_type:
                              valid
                                ? valid.value
                                : "equipment",
                          });
                        }
                      }
                    >
                      {productTypes.map(
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
                  </label>

                  <label>
                    Barcode

                    <input
                      type="text"
                      maxLength={100}
                      value={
                        productForm.barcode
                      }
                      onChange={
                        (event) =>
                          setProductForm({
                            ...productForm,
                            barcode:
                              event.target.value,
                          })
                      }
                    />
                  </label>

                  <label>
                    Model number

                    <input
                      type="text"
                      maxLength={100}
                      value={
                        productForm
                          .model_number
                      }
                      onChange={
                        (event) =>
                          setProductForm({
                            ...productForm,
                            model_number:
                              event.target.value,
                          })
                      }
                    />
                  </label>

                  <label>
                    BTU capacity

                    <input
                      type="number"
                      min="0"
                      max="1000000"
                      step="1"
                      value={
                        productForm
                          .btu_capacity
                      }
                      onChange={
                        (event) =>
                          setProductForm({
                            ...productForm,
                            btu_capacity:
                              event.target.value,
                          })
                      }
                    />
                  </label>

                  <label
                    className={
                      styles.fullField
                    }
                  >
                    Description

                    <textarea
                      rows={3}
                      value={
                        productForm
                          .description
                      }
                      onChange={
                        (event) =>
                          setProductForm({
                            ...productForm,
                            description:
                              event.target.value,
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
                  Pricing
                </h3>

                <div
                  className={
                    styles.formGrid
                  }
                >
                  <label>
                    Purchase cost

                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={
                        productForm
                          .purchase_cost
                      }
                      onChange={
                        (event) =>
                          setProductForm({
                            ...productForm,
                            purchase_cost:
                              event.target.value,
                          })
                      }
                    />
                  </label>

                  <label>
                    Selling price *

                    <input
                      type="number"
                      required
                      min="0"
                      step="0.01"
                      value={
                        productForm
                          .selling_price
                      }
                      onChange={
                        (event) =>
                          setProductForm({
                            ...productForm,
                            selling_price:
                              event.target.value,
                          })
                      }
                    />
                  </label>

                  <label>
                    Minimum selling price *

                    <input
                      type="number"
                      required
                      min="0"
                      step="0.01"
                      value={
                        productForm
                          .minimum_selling_price
                      }
                      onChange={
                        (event) =>
                          setProductForm({
                            ...productForm,
                            minimum_selling_price:
                              event.target.value,
                          })
                      }
                    />
                  </label>

                  <label>
                    Warranty years

                    <input
                      type="number"
                      min="0"
                      max="10"
                      step="0.5"
                      value={
                        productForm
                          .warranty_months
                          ? String(
                              Number(
                                productForm
                                  .warranty_months,
                              ) / 12,
                            )
                          : "0"
                      }
                      onChange={
                        (event) => {
                          const years =
                            Number(
                              event.target.value
                              || 0,
                            );

                          setProductForm({
                            ...productForm,
                            warranty_months:
                              String(
                                Math.round(
                                  years * 12,
                                ),
                              ),
                          });
                        }
                      }
                    />

                    <small>
                      Enter warranty in years.
                      1 year = 12 months.
                    </small>
                  </label>
                </div>
              </section>


              <section
                className={
                  styles.formSection
                }
              >
                <h3>
                  Inventory settings
                </h3>

                <div
                  className={
                    styles.formGrid
                  }
                >
                  <label>
                    Reorder level

                    <input
                      type="number"
                      min="0"
                      step="0.001"
                      value={
                        productForm
                          .reorder_level
                      }
                      onChange={
                        (event) =>
                          setProductForm({
                            ...productForm,
                            reorder_level:
                              event.target.value,
                          })
                      }
                    />
                  </label>

                  <label>
                    Reorder quantity

                    <input
                      type="number"
                      min="0"
                      step="0.001"
                      value={
                        productForm
                          .reorder_quantity
                      }
                      onChange={
                        (event) =>
                          setProductForm({
                            ...productForm,
                            reorder_quantity:
                              event.target.value,
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
                        productForm
                          .track_serial_numbers
                      }
                      onChange={
                        (event) =>
                          setProductForm({
                            ...productForm,
                            track_serial_numbers:
                              event.target.checked,
                          })
                      }
                    />

                    Track serial numbers
                  </label>

                  <label
                    className={
                      styles.fullField
                    }
                  >
                    Technical notes

                    <textarea
                      rows={4}
                      value={
                        productForm
                          .technical_notes
                      }
                      onChange={
                        (event) =>
                          setProductForm({
                            ...productForm,
                            technical_notes:
                              event.target.value,
                          })
                      }
                    />
                  </label>
                </div>
              </section>


              {productError && (
                <div
                  className={
                    styles.formError
                  }
                >
                  <CircleAlert
                    size={17}
                  />

                  {productError}
                </div>
              )}


              <footer
                className={
                  styles.modalFooter
                }
              >
                <button
                  type="button"
                  className={
                    styles.cancelButton
                  }
                  disabled={
                    productSaving
                  }
                  onClick={
                    closeProductModal
                  }
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className={
                    styles.saveButton
                  }
                  disabled={
                    productSaving
                  }
                >
                  {productSaving
                    ? "Saving..."
                    : "Create product"
                  }
                </button>
              </footer>
            </form>
          </section>
        </div>
      )}


      {lookupMode && (
        <div
          className={
            styles.modalBackdrop
          }
        >
          <section
            className={
              styles.smallModal
            }
            role="dialog"
            aria-modal="true"
          >
            <header
              className={
                styles.modalHeader
              }
            >
              <div>
                <p className="eyebrow">
                  CATALOG LOOKUP
                </p>

                <h2>
                  Add{" "}
                  {lookupMode}
                </h2>
              </div>

              <button
                type="button"
                className={
                  styles.closeButton
                }
                disabled={
                  lookupSaving
                }
                onClick={
                  closeLookup
                }
              >
                <X size={20} />
              </button>
            </header>

            <form
              className={
                styles.lookupForm
              }
              onSubmit={
                submitLookup
              }
            >
              <label>
                Code *

                <input
                  type="text"
                  required
                  value={
                    lookupForm.code
                  }
                  placeholder={
                    lookupMode
                    === "category"
                      ? "SPLIT-AC"
                      : "DAIKIN"
                  }
                  onChange={
                    (event) =>
                      setLookupForm({
                        ...lookupForm,
                        code:
                          event.target.value,
                      })
                  }
                />
              </label>

              <label>
                Name *

                <input
                  type="text"
                  required
                  minLength={2}
                  value={
                    lookupForm.name
                  }
                  onChange={
                    (event) =>
                      setLookupForm({
                        ...lookupForm,
                        name:
                          event.target.value,
                      })
                  }
                />
              </label>

              <label>
                Description

                <textarea
                  rows={4}
                  value={
                    lookupForm
                      .description
                  }
                  onChange={
                    (event) =>
                      setLookupForm({
                        ...lookupForm,
                        description:
                          event.target.value,
                      })
                  }
                />
              </label>

              {lookupError && (
                <div
                  className={
                    styles.formError
                  }
                >
                  <CircleAlert
                    size={17}
                  />

                  {lookupError}
                </div>
              )}

              <footer
                className={
                  styles.modalFooter
                }
              >
                <button
                  type="button"
                  className={
                    styles.cancelButton
                  }
                  disabled={
                    lookupSaving
                  }
                  onClick={
                    closeLookup
                  }
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className={
                    styles.saveButton
                  }
                  disabled={
                    lookupSaving
                  }
                >
                  {lookupSaving
                    ? "Saving..."
                    : "Create"
                  }
                </button>
              </footer>
            </form>
          </section>
        </div>
      )}
    </AppShell>
  );
}
