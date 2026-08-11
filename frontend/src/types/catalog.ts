export type ProductType =
  | "equipment"
  | "spare_part"
  | "installation_material"
  | "accessory"
  | "consumable"
  | "service_item";


export type Category = {
  id: number;
  company_id?: number;
  code: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
};


export type Brand = {
  id: number;
  company_id?: number;
  code: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
};


export type Unit = {
  id: number;
  code: string;
  name: string;
  decimal_places: number;
  is_active: boolean;
};


export type Product = {
  id: number;
  company_id: number;
  product_code: string;

  barcode: string | null;

  category_id: number;
  brand_id: number | null;
  unit_id: number;

  name: string;
  model_number: string | null;
  description: string | null;

  btu_capacity: number | null;

  product_type: ProductType;

  track_serial_numbers: boolean;

  purchase_cost: string | number;
  selling_price: string | number;
  minimum_selling_price: string | number;

  warranty_months: number;

  reorder_level: string | number;
  reorder_quantity: string | number;

  image_path: string | null;
  technical_notes: string | null;

  is_active: boolean;

  created_by_id: number;
  updated_by_id: number | null;

  created_at: string;
  updated_at: string;

  category: Category;
  brand: Brand | null;
  unit: Unit;
};


export type ProductListResponse = {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};


export type ProductCreatePayload = {
  barcode?: string | null;

  category_id: number;
  brand_id?: number | null;
  unit_id: number;

  name: string;
  model_number?: string | null;
  description?: string | null;

  btu_capacity?: number | null;

  product_type: ProductType;

  track_serial_numbers: boolean;

  purchase_cost: string;
  selling_price: string;
  minimum_selling_price: string;

  warranty_months: number;

  reorder_level: string;
  reorder_quantity: string;

  image_path?: string | null;
  technical_notes?: string | null;
};


export type CategoryCreatePayload = {
  code: string;
  name: string;
  description?: string | null;
};


export type BrandCreatePayload = {
  code: string;
  name: string;
  description?: string | null;
};


export type ProductUpdatePayload = {
  barcode?: string | null;

  category_id?: number | null;
  brand_id?: number | null;
  unit_id?: number | null;

  name?: string | null;
  model_number?: string | null;
  description?: string | null;

  btu_capacity?: number | null;

  product_type?: ProductType | null;

  track_serial_numbers?: boolean | null;

  purchase_cost?: string | null;
  selling_price?: string | null;
  minimum_selling_price?: string | null;

  warranty_months?: number | null;

  reorder_level?: string | null;
  reorder_quantity?: string | null;

  image_path?: string | null;
  technical_notes?: string | null;

  is_active?: boolean | null;
};
