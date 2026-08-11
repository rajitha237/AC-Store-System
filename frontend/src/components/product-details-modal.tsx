"use client";

import axios from "axios";

import {
  Barcode,
  Boxes,
  Building2,
  CircleAlert,
  Edit3,
  Package,
  Power,
  PowerOff,
  Save,
  ShieldCheck,
  Tag,
  X,
} from "lucide-react";

import {
  FormEvent,
  useEffect,
  useState,
} from "react";

import {
  deactivateProduct,
  getProduct,
  reactivateProduct,
  updateProduct,
} from "@/lib/catalog-api";

import type {
  Brand,
  Category,
  Product,
  ProductType,
  ProductUpdatePayload,
  Unit,
} from "@/types/catalog";

import styles from "@/app/catalog/catalog.module.css";


type Props = {
  productId: number;

  categories: Category[];
  brands: Brand[];
  units: Unit[];

  onClose: () => void;

  onChanged:
    () => Promise<void> | void;
};


type EditForm = {
  barcode: string;

  category_id: string;
  brand_id: string;
  unit_id: string;

  name: string;
  model_number: string;
  description: string;

  btu_capacity: string;

  product_type: ProductType;

  track_serial_numbers:
    boolean;

  purchase_cost: string;
  selling_price: string;
  minimum_selling_price:
    string;

  warranty_months: string;

  reorder_level: string;
  reorder_quantity: string;

  technical_notes: string;
};


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
    value:
      "installation_material",
    label:
      "Installation material",
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


function emptyForm():
  EditForm {
  return {
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
}


function productToForm(
  product: Product,
): EditForm {
  return {
    barcode:
      product.barcode ?? "",

    category_id:
      String(
        product.category_id,
      ),

    brand_id:
      product.brand_id
        ? String(
            product.brand_id,
          )
        : "",

    unit_id:
      String(
        product.unit_id,
      ),

    name:
      product.name,

    model_number:
      product.model_number ?? "",

    description:
      product.description ?? "",

    btu_capacity:
      product.btu_capacity
        !== null
        ? String(
            product.btu_capacity,
          )
        : "",

    product_type:
      product.product_type,

    track_serial_numbers:
      product
        .track_serial_numbers,

    purchase_cost:
      String(
        product.purchase_cost
        ?? "0.00",
      ),

    selling_price:
      String(
        product.selling_price
        ?? "0.00",
      ),

    minimum_selling_price:
      String(
        product
          .minimum_selling_price
        ?? "0.00",
      ),

    warranty_months:
      String(
        product.warranty_months
        ?? 0,
      ),

    reorder_level:
      String(
        product.reorder_level
        ?? "0.000",
      ),

    reorder_quantity:
      String(
        product.reorder_quantity
        ?? "0.000",
      ),

    technical_notes:
      product.technical_notes
      ?? "",
  };
}


function optional(
  value: string,
): string | null {
  const clean =
    value.trim();

  return clean || null;
}


function money(
  value:
    | string
    | number,
): string {
  const amount =
    Number(value ?? 0);

  if (
    !Number.isFinite(
      amount,
    )
  ) {
    return "LKR 0.00";
  }

  return new Intl.NumberFormat(
    "en-LK",
    {
      style: "currency",
      currency: "LKR",
      minimumFractionDigits: 2,
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
        part.charAt(0)
          .toUpperCase()
        + part.slice(1),
    )
    .join(" ");
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
      + "to update this product."
    );
  }

  if (
    error.response?.status
    === 404
  ) {
    return (
      "Product record "
      + "was not found."
    );
  }

  if (
    error.response?.status
    === 409
  ) {
    return (
      "A product with the same "
      + "barcode or unique value "
      + "already exists."
    );
  }

  return (
    "Unable to complete "
    + "the request."
  );
}


export function ProductDetailsModal({
  productId,
  categories,
  brands,
  units,
  onClose,
  onChanged,
}: Props) {
  const [
    product,
    setProduct,
  ] =
    useState<Product | null>(
      null,
    );

  const [
    form,
    setForm,
  ] =
    useState<EditForm>(
      emptyForm(),
    );

  const [
    loading,
    setLoading,
  ] =
    useState(true);

  const [
    editing,
    setEditing,
  ] =
    useState(false);

  const [
    saving,
    setSaving,
  ] =
    useState(false);

  const [
    changingStatus,
    setChangingStatus,
  ] =
    useState(false);

  const [
    error,
    setError,
  ] =
    useState("");


  useEffect(() => {
    let cancelled = false;

    const timer =
      window.setTimeout(
        () => {
          async function load() {
            setLoading(true);
            setError("");

            try {
              const response =
                await getProduct(
                  productId,
                );

              if (cancelled) {
                return;
              }

              setProduct(
                response,
              );

              setForm(
                productToForm(
                  response,
                ),
              );
            } catch (
              requestError
            ) {
              if (!cancelled) {
                setError(
                  apiError(
                    requestError,
                  ),
                );
              }
            } finally {
              if (!cancelled) {
                setLoading(
                  false,
                );
              }
            }
          }

          void load();
        },
        0,
      );

    return () => {
      cancelled = true;

      window.clearTimeout(
        timer,
      );
    };
  }, [productId]);


  const activeCategories =
    categories.filter(
      (item) =>
        item.is_active,
    );

  const activeBrands =
    brands.filter(
      (item) =>
        item.is_active,
    );

  const activeUnits =
    units.filter(
      (item) =>
        item.is_active,
    );


  function startEdit() {
    if (!product) {
      return;
    }

    setForm(
      productToForm(
        product,
      ),
    );

    setError("");
    setEditing(true);
  }


  function cancelEdit() {
    if (saving) {
      return;
    }

    if (product) {
      setForm(
        productToForm(
          product,
        ),
      );
    }

    setError("");
    setEditing(false);
  }


  async function submitEdit(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setError("");

    if (
      form.name
        .trim()
        .length < 2
    ) {
      setError(
        "Product name is required.",
      );

      return;
    }

    const categoryId =
      Number(
        form.category_id,
      );

    const unitId =
      Number(
        form.unit_id,
      );

    if (
      !Number.isInteger(
        categoryId,
      )
      || categoryId < 1
    ) {
      setError(
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
      setError(
        "Please select a unit.",
      );

      return;
    }

    const sellingPrice =
      Number(
        form.selling_price,
      );

    const minimumPrice =
      Number(
        form.minimum_selling_price,
      );

    if (
      minimumPrice
      > sellingPrice
    ) {
      setError(
        "Minimum selling price "
        + "cannot be higher than "
        + "selling price.",
      );

      return;
    }

    const brandId =
      form.brand_id
        ? Number(
            form.brand_id,
          )
        : null;

    const payload:
      ProductUpdatePayload = {
        barcode:
          optional(
            form.barcode,
          ),

        category_id:
          categoryId,

        brand_id:
          brandId,

        unit_id:
          unitId,

        name:
          form.name.trim(),

        model_number:
          optional(
            form.model_number,
          ),

        description:
          optional(
            form.description,
          ),

        btu_capacity:
          form.btu_capacity
            ? Number(
                form.btu_capacity,
              )
            : null,

        product_type:
          form.product_type,

        track_serial_numbers:
          form
            .track_serial_numbers,

        purchase_cost:
          form.purchase_cost
          || "0.00",

        selling_price:
          form.selling_price
          || "0.00",

        minimum_selling_price:
          form
            .minimum_selling_price
          || "0.00",

        warranty_months:
          Number(
            form.warranty_months
            || 0,
          ),

        reorder_level:
          form.reorder_level
          || "0.000",

        reorder_quantity:
          form.reorder_quantity
          || "0.000",

        technical_notes:
          optional(
            form.technical_notes,
          ),
      };

    setSaving(true);

    try {
      const updated =
        await updateProduct(
          productId,
          payload,
        );

      setProduct(
        updated,
      );

      setForm(
        productToForm(
          updated,
        ),
      );

      setEditing(false);

      await onChanged();
    } catch (
      requestError
    ) {
      setError(
        apiError(
          requestError,
        ),
      );
    } finally {
      setSaving(false);
    }
  }


  async function changeStatus() {
    if (!product) {
      return;
    }

    const activating =
      !product.is_active;

    const confirmed =
      window.confirm(
        activating
          ? (
            "Reactivate this product?"
          )
          : (
            "Deactivate this product? "
            + "It will remain available "
            + "for historical records."
          ),
      );

    if (!confirmed) {
      return;
    }

    setChangingStatus(
      true,
    );

    setError("");

    try {
      const updated =
        activating
          ? await reactivateProduct(
              product.id,
            )
          : await deactivateProduct(
              product.id,
            );

      setProduct(
        updated,
      );

      setForm(
        productToForm(
          updated,
        ),
      );

      setEditing(false);

      await onChanged();
    } catch (
      requestError
    ) {
      setError(
        apiError(
          requestError,
        ),
      );
    } finally {
      setChangingStatus(
        false,
      );
    }
  }


  const busy =
    loading
    || saving
    || changingStatus;


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
          "product-details-title"
        }
      >
        <header
          className={
            styles.detailHeader
          }
        >
          <div>
            <p className="eyebrow">
              PRODUCT PROFILE
            </p>

            <h2
              id="product-details-title"
            >
              {product
                ? product.name
                : "Product details"
              }
            </h2>

            {product && (
              <span
                className={
                  styles.productCode
                }
              >
                {
                  product.product_code
                }
              </span>
            )}
          </div>

          <button
            type="button"
            className={
              styles.closeButton
            }
            onClick={
              onClose
            }
            disabled={
              saving
              || changingStatus
            }
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </header>


        {loading ? (
          <div
            className={
              styles.detailLoading
            }
          >
            <div
              className="loading-spinner"
            />

            Loading product...
          </div>
        ) : !product ? (
          <div
            className={
              styles.detailLoading
            }
          >
            <CircleAlert
              size={28}
            />

            {error
              || (
                "Product could "
                + "not be loaded."
              )
            }
          </div>
        ) : (
          <>
            <div
              className={
                styles.profileSummary
              }
            >
              <div
                className={
                  styles.profileIcon
                }
              >
                <Package
                  size={25}
                />
              </div>

              <div
                className={
                  styles.profileIdentity
                }
              >
                <strong>
                  {product.name}
                </strong>

                <span>
                  {product.model_number
                    || "No model number"
                  }
                </span>
              </div>

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
            </div>


            <div
              className={
                styles.detailSummaryGrid
              }
            >
              <article>
                <span>
                  Purchase cost
                </span>

                <strong>
                  {money(
                    product.purchase_cost,
                  )}
                </strong>
              </article>

              <article>
                <span>
                  Selling price
                </span>

                <strong>
                  {money(
                    product.selling_price,
                  )}
                </strong>
              </article>

              <article>
                <span>
                  Minimum price
                </span>

                <strong>
                  {money(
                    product
                      .minimum_selling_price,
                  )}
                </strong>
              </article>
            </div>


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


            {editing ? (
              <form
                className={
                  styles.editForm
                }
                onSubmit={
                  submitEdit
                }
              >
                <section
                  className={
                    styles.detailSection
                  }
                >
                  <h3>
                    Product identity
                  </h3>

                  <div
                    className={
                      styles.detailFormGrid
                    }
                  >
                    <label
                      className={
                        styles.detailFullField
                      }
                    >
                      Product name *

                      <input
                        type="text"
                        required
                        minLength={2}
                        maxLength={200}
                        value={
                          form.name
                        }
                        onChange={
                          (event) =>
                            setForm({
                              ...form,
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
                          form.category_id
                        }
                        onChange={
                          (event) =>
                            setForm({
                              ...form,
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
                          form.brand_id
                        }
                        onChange={
                          (event) =>
                            setForm({
                              ...form,
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
                              {
                                brand.name
                              }
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
                          form.unit_id
                        }
                        onChange={
                          (event) =>
                            setForm({
                              ...form,
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
                      Product type

                      <select
                        value={
                          form.product_type
                        }
                        onChange={
                          (event) => {
                            const value =
                              event.target.value;

                            const selected =
                              productTypes.find(
                                (item) =>
                                  item.value
                                  === value,
                              );

                            setForm({
                              ...form,
                              product_type:
                                selected
                                  ? selected.value
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
                          form.barcode
                        }
                        onChange={
                          (event) =>
                            setForm({
                              ...form,
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
                          form.model_number
                        }
                        onChange={
                          (event) =>
                            setForm({
                              ...form,
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
                          form.btu_capacity
                        }
                        onChange={
                          (event) =>
                            setForm({
                              ...form,
                              btu_capacity:
                                event.target.value,
                            })
                        }
                      />
                    </label>

                    <label
                      className={
                        styles.detailFullField
                      }
                    >
                      Description

                      <textarea
                        rows={3}
                        value={
                          form.description
                        }
                        onChange={
                          (event) =>
                            setForm({
                              ...form,
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
                    styles.detailSection
                  }
                >
                  <h3>
                    Pricing
                  </h3>

                  <div
                    className={
                      styles.detailFormGrid
                    }
                  >
                    <label>
                      Purchase cost

                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={
                          form.purchase_cost
                        }
                        onChange={
                          (event) =>
                            setForm({
                              ...form,
                              purchase_cost:
                                event.target.value,
                            })
                        }
                      />
                    </label>

                    <label>
                      Selling price

                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={
                          form.selling_price
                        }
                        onChange={
                          (event) =>
                            setForm({
                              ...form,
                              selling_price:
                                event.target.value,
                            })
                        }
                      />
                    </label>

                    <label>
                      Minimum selling price

                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={
                          form
                            .minimum_selling_price
                        }
                        onChange={
                          (event) =>
                            setForm({
                              ...form,
                              minimum_selling_price:
                                event.target.value,
                            })
                        }
                      />
                    </label>

                    <label>
                      Warranty months

                      <input
                        type="number"
                        min="0"
                        max="120"
                        step="1"
                        value={
                          form.warranty_months
                        }
                        onChange={
                          (event) =>
                            setForm({
                              ...form,
                              warranty_months:
                                event.target.value,
                            })
                        }
                      />
                    </label>
                  </div>
                </section>


                <section
                  className={
                    styles.detailSection
                  }
                >
                  <h3>
                    Inventory settings
                  </h3>

                  <div
                    className={
                      styles.detailFormGrid
                    }
                  >
                    <label>
                      Reorder level

                      <input
                        type="number"
                        min="0"
                        step="0.001"
                        value={
                          form.reorder_level
                        }
                        onChange={
                          (event) =>
                            setForm({
                              ...form,
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
                          form.reorder_quantity
                        }
                        onChange={
                          (event) =>
                            setForm({
                              ...form,
                              reorder_quantity:
                                event.target.value,
                            })
                        }
                      />
                    </label>

                    <label
                      className={
                        styles.detailCheckbox
                      }
                    >
                      <input
                        type="checkbox"
                        checked={
                          form
                            .track_serial_numbers
                        }
                        onChange={
                          (event) =>
                            setForm({
                              ...form,
                              track_serial_numbers:
                                event.target.checked,
                            })
                        }
                      />

                      Track serial numbers
                    </label>

                    <label
                      className={
                        styles.detailFullField
                      }
                    >
                      Technical notes

                      <textarea
                        rows={4}
                        value={
                          form.technical_notes
                        }
                        onChange={
                          (event) =>
                            setForm({
                              ...form,
                              technical_notes:
                                event.target.value,
                            })
                        }
                      />
                    </label>
                  </div>
                </section>


                <div
                  className={
                    styles.detailActionBar
                  }
                >
                  <button
                    type="button"
                    className={
                      styles.secondaryAction
                    }
                    disabled={
                      saving
                    }
                    onClick={
                      cancelEdit
                    }
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    className={
                      styles.primaryAction
                    }
                    disabled={
                      saving
                    }
                  >
                    <Save size={17} />

                    {saving
                      ? "Saving..."
                      : "Save changes"
                    }
                  </button>
                </div>
              </form>
            ) : (
              <>
                <section
                  className={
                    styles.detailSection
                  }
                >
                  <h3>
                    Catalog information
                  </h3>

                  <div
                    className={
                      styles.infoGrid
                    }
                  >
                    <div>
                      <Package size={16} />

                      <span>
                        Product type
                      </span>

                      <strong>
                        {typeLabel(
                          product.product_type,
                        )}
                      </strong>
                    </div>

                    <div>
                      <Tag size={16} />

                      <span>
                        Category
                      </span>

                      <strong>
                        {
                          product.category
                            ?.name
                          || "—"
                        }
                      </strong>
                    </div>

                    <div>
                      <Building2
                        size={16}
                      />

                      <span>
                        Brand
                      </span>

                      <strong>
                        {
                          product.brand
                            ?.name
                          || "No brand"
                        }
                      </strong>
                    </div>

                    <div>
                      <Boxes size={16} />

                      <span>
                        Unit
                      </span>

                      <strong>
                        {
                          product.unit
                            ?.name
                          || "—"
                        }
                      </strong>
                    </div>
                  </div>
                </section>


                <section
                  className={
                    styles.detailSection
                  }
                >
                  <h3>
                    Product identifiers
                  </h3>

                  <div
                    className={
                      styles.infoGrid
                    }
                  >
                    <div>
                      <Barcode
                        size={16}
                      />

                      <span>
                        Barcode
                      </span>

                      <strong>
                        {product.barcode
                          || "—"
                        }
                      </strong>
                    </div>

                    <div>
                      <Package
                        size={16}
                      />

                      <span>
                        Model number
                      </span>

                      <strong>
                        {product.model_number
                          || "—"
                        }
                      </strong>
                    </div>

                    <div>
                      <ShieldCheck
                        size={16}
                      />

                      <span>
                        Serial tracking
                      </span>

                      <strong>
                        {product
                          .track_serial_numbers
                          ? "Enabled"
                          : "Disabled"
                        }
                      </strong>
                    </div>

                    <div>
                      <Package
                        size={16}
                      />

                      <span>
                        BTU capacity
                      </span>

                      <strong>
                        {product.btu_capacity
                          !== null
                          ? (
                            product.btu_capacity
                            + " BTU"
                          )
                          : "—"
                        }
                      </strong>
                    </div>
                  </div>
                </section>


                <section
                  className={
                    styles.detailSection
                  }
                >
                  <h3>
                    Inventory configuration
                  </h3>

                  <div
                    className={
                      styles.infoGrid
                    }
                  >
                    <div>
                      <Boxes size={16} />

                      <span>
                        Reorder level
                      </span>

                      <strong>
                        {
                          product.reorder_level
                        }
                      </strong>
                    </div>

                    <div>
                      <Boxes size={16} />

                      <span>
                        Reorder quantity
                      </span>

                      <strong>
                        {
                          product.reorder_quantity
                        }
                      </strong>
                    </div>

                    <div>
                      <ShieldCheck
                        size={16}
                      />

                      <span>
                        Warranty
                      </span>

                      <strong>
                        {
                          product.warranty_months
                        }{" "}
                        months
                      </strong>
                    </div>
                  </div>

                  {product.description && (
                    <div
                      className={
                        styles.notesCard
                      }
                    >
                      <span>
                        Description
                      </span>

                      <p>
                        {product.description}
                      </p>
                    </div>
                  )}

                  {product.technical_notes && (
                    <div
                      className={
                        styles.notesCard
                      }
                    >
                      <span>
                        Technical notes
                      </span>

                      <p>
                        {
                          product
                            .technical_notes
                        }
                      </p>
                    </div>
                  )}
                </section>


                <div
                  className={
                    styles.detailActionBar
                  }
                >
                  <button
                    type="button"
                    className={
                      product.is_active
                        ? styles.dangerAction
                        : styles.activateAction
                    }
                    disabled={
                      busy
                    }
                    onClick={
                      changeStatus
                    }
                  >
                    {product.is_active
                      ? (
                        <>
                          <PowerOff
                            size={17}
                          />
                          Deactivate
                        </>
                      )
                      : (
                        <>
                          <Power
                            size={17}
                          />
                          Reactivate
                        </>
                      )
                    }
                  </button>

                  <button
                    type="button"
                    className={
                      styles.primaryAction
                    }
                    disabled={
                      busy
                    }
                    onClick={
                      startEdit
                    }
                  >
                    <Edit3 size={17} />
                    Edit product
                  </button>
                </div>
              </>
            )}
          </>
        )}
      </section>
    </div>
  );
}
