"use client";

import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  ClipboardCheck,
  Camera,
  ImagePlus,
  LoaderCircle,
  PenLine,
  MapPin,
  PackagePlus,
  Phone,
  RefreshCw,
  Trash2,
  UserRound,
  Wrench,
} from "lucide-react";
import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  useParams,
  useRouter,
} from "next/navigation";

import { writeTechnicianLocation } from "@/lib/technician-location-api";
import {
  getCurrentUser,
} from "@/lib/auth-api";
import {
  addServicePart,
  completeServiceJob,
  getServiceJob,
  uploadServiceCompletionEvidence,
} from "@/lib/service-jobs-api";

import {
  getProducts,
} from "@/lib/catalog-api";
import {
  getStockBalances,
  getWarehouses,
} from "@/lib/inventory-api";

import type {
  ServiceJobDetailResponse,
} from "@/types/service-jobs";

import styles from "./page.module.css";


type TechnicianPartProduct = {
  id: number;
  name: string;
  sku?: string | null;
  product_type?: string | null;
  is_active?: boolean;
};

type TechnicianPartWarehouse = {
  id: number;
  name: string;
  code?: string | null;
  is_active?: boolean;
};

type TechnicianPartBalance = {
  product_id: number;
  warehouse_id: number;
  quantity?: string | number;
  product_name?: string | null;
  product_sku?: string | null;
  warehouse_name?: string | null;
  quantity_available?:
    | string
    | number
    | null;
};




type TechnicianUser =
  Awaited<
    ReturnType<
      typeof getCurrentUser
    >
  >;


function normalizedRole(
  role: string | null | undefined,
): string {
  return (role ?? "")
    .trim()
    .toLowerCase()
    .replaceAll("-", "_")
    .replaceAll(" ", "_");
}


function isTechnicianRole(
  role: string | null | undefined,
): boolean {
  const value =
    normalizedRole(role);

  return (
    value === "technician"
    || value === "service_technician"
    || value.includes("technician")
  );
}


function statusLabel(
  value: string,
): string {
  return value
    .replaceAll("_", " ")
    .replace(
      /\b\w/g,
      (letter) =>
        letter.toUpperCase(),
    );
}


function displayValue(
  value:
    | string
    | number
    | null
    | undefined,
): string {
  if (
    value === null
    || value === undefined
    || value === ""
  ) {
    return "—";
  }

  return String(value);
}


function apiErrorMessage(
  error: unknown,
): string {
  if (
    error
    && typeof error === "object"
  ) {
    const candidate =
      error as {
        message?: string;
        detail?: string;
      };

    if (candidate.detail) {
      return candidate.detail;
    }

    if (candidate.message) {
      return candidate.message;
    }
  }

  return (
    "Something went wrong. "
    + "Please try again."
  );
}


export default function TechnicianJobPage() {
  const router = useRouter();
  const params = useParams<{
    jobId: string;
  }>();

  const jobId =
    Number(params.jobId);

  const [
    user,
    setUser,
  ] = useState<
    TechnicianUser | null
  >(null);

  const [
    job,
    setJob,
  ] = useState<
    ServiceJobDetailResponse | null
  >(null);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    refreshing,
    setRefreshing,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  const [
    actionMode,
    setActionMode,
  ] = useState<
    "part" | "complete" | null
  >(null);

  const [
    partSearch,
    setPartSearch,
  ] = useState("");

  const [
    partProducts,
    setPartProducts,
  ] = useState<
    TechnicianPartProduct[]
  >([]);

  const [
    partWarehouses,
    setPartWarehouses,
  ] = useState<
    TechnicianPartWarehouse[]
  >([]);

  const [
    partBalances,
    setPartBalances,
  ] = useState<
    TechnicianPartBalance[]
  >([]);

  const [
    partPickerLoading,
    setPartPickerLoading,
  ] = useState(false);

  const [
    productId,
    setProductId,
  ] = useState("");

  const [
    warehouseId,
    setWarehouseId,
  ] = useState("");

  const [
    quantity,
    setQuantity,
  ] = useState("1");

  const [
    unitPrice,
    setUnitPrice,
  ] = useState("");

  const [
    partNotes,
    setPartNotes,
  ] = useState("");

  const [
    partSaving,
    setPartSaving,
  ] = useState(false);

  const [
    jobResult,
    setJobResult,
  ] = useState("");

  const [
    completionNotes,
    setCompletionNotes,
  ] = useState("");

  const [
    completeSaving,
    setCompleteSaving,
  ] = useState(false);

  const [
    workPhotos,
    setWorkPhotos,
  ] = useState<File[]>([]);

  const [
    workPhotoPreviews,
    setWorkPhotoPreviews,
  ] = useState<string[]>([]);

  const [
    photoProcessing,
    setPhotoProcessing,
  ] = useState(false);

  const [
    cameraOpen,
    setCameraOpen,
  ] = useState(false);

  const [
    cameraStarting,
    setCameraStarting,
  ] = useState(false);

  const [
    cameraError,
    setCameraError,
  ] = useState("");

  const cameraVideoRef =
    useRef<HTMLVideoElement | null>(
      null,
    );

  const cameraStreamRef =
    useRef<MediaStream | null>(
      null,
    );

  function stopLiveCamera() {
    const stream =
      cameraStreamRef.current;

    if (stream) {
      for (
        const track
        of stream.getTracks()
      ) {
        track.stop();
      }
    }

    cameraStreamRef.current = null;

    if (cameraVideoRef.current) {
      cameraVideoRef.current.srcObject =
        null;
    }

    setCameraOpen(false);
    setCameraStarting(false);
  }


  async function startLiveCamera() {
    if (
      photoProcessing
      || workPhotos.length >= 5
    ) {
      return;
    }

    if (
      !navigator.mediaDevices
      || !navigator.mediaDevices.getUserMedia
    ) {
      setCameraError(
        "Live camera is not available on this device or browser.",
      );

      return;
    }

    try {
      stopLiveCamera();
      setCameraStarting(true);
      setCameraError("");

      const stream =
        await navigator.mediaDevices
          .getUserMedia({
            video: {
              facingMode: {
                ideal: "environment",
              },
            },
            audio: false,
          });

      cameraStreamRef.current =
        stream;

      setCameraOpen(true);

      await new Promise<void>(
        (resolve) => {
          requestAnimationFrame(
            () => resolve(),
          );
        },
      );

      const video =
        cameraVideoRef.current;

      if (!video) {
        throw new Error(
          "Unable to open the live camera preview.",
        );
      }

      video.srcObject = stream;

      await video.play();
    } catch (cameraRequestError) {
      stopLiveCamera();

      setCameraError(
        cameraRequestError
          instanceof Error
          && cameraRequestError.message
          ? cameraRequestError.message
          : "Unable to access the live camera.",
      );
    } finally {
      setCameraStarting(false);
    }
  }


  async function captureLivePhoto() {
    const video =
      cameraVideoRef.current;

    if (
      !video
      || video.videoWidth < 1
      || video.videoHeight < 1
    ) {
      setCameraError(
        "Camera is not ready yet. Try again.",
      );

      return;
    }

    if (workPhotos.length >= 5) {
      stopLiveCamera();
      return;
    }

    try {
      setPhotoProcessing(true);
      setCameraError("");

      const canvas =
        document.createElement(
          "canvas",
        );

      canvas.width =
        video.videoWidth;

      canvas.height =
        video.videoHeight;

      const context =
        canvas.getContext("2d");

      if (!context) {
        throw new Error(
          "Unable to capture the camera image.",
        );
      }

      context.drawImage(
        video,
        0,
        0,
        canvas.width,
        canvas.height,
      );

      const blob =
        await new Promise<Blob>(
          (resolve, reject) => {
            canvas.toBlob(
              (capturedBlob) => {
                if (capturedBlob) {
                  resolve(capturedBlob);
                  return;
                }

                reject(
                  new Error(
                    "Unable to capture the camera image.",
                  ),
                );
              },
              "image/jpeg",
              0.9,
            );
          },
        );

      const file =
        new File(
          [blob],
          "work-photo.jpg",
          {
            type: "image/jpeg",
          },
        );

      const compressed =
        await compressWorkPhoto(
          file,
        );

      const preview =
        await fileToDataUrl(
          compressed,
        );

      setWorkPhotos(
        (current) => [
          ...current,
          compressed,
        ].slice(0, 5),
      );

      setWorkPhotoPreviews(
        (current) => [
          ...current,
          preview,
        ].slice(0, 5),
      );

      stopLiveCamera();
    } catch (captureError) {
      setCameraError(
        captureError
          instanceof Error
          && captureError.message
          ? captureError.message
          : "Unable to capture the photo.",
      );
    } finally {
      setPhotoProcessing(false);
    }
  }


  const signatureCanvasRef =
    useRef<HTMLCanvasElement | null>(
      null,
    );

  const signatureDrawingRef =
    useRef(false);

  const [
    signatureHasInk,
    setSignatureHasInk,
  ] = useState(false);


  async function fileToDataUrl(
    file: Blob,
  ): Promise<string> {
    return await new Promise(
      (
        resolve,
        reject,
      ) => {
        const reader =
          new FileReader();

        reader.onload = () =>
          resolve(
            String(
              reader.result
              ?? "",
            ),
          );

        reader.onerror = () =>
          reject(
            new Error(
              "Unable to preview image.",
            ),
          );

        reader.readAsDataURL(
          file,
        );
      },
    );
  }


  async function compressWorkPhoto(
    file: File,
  ): Promise<File> {
    if (
      !file.type.startsWith(
        "image/",
      )
    ) {
      throw new Error(
        "Only image files are allowed.",
      );
    }

    const bitmap =
      await createImageBitmap(
        file,
      );

    const maxDimension = 1400;

    const scale =
      Math.min(
        1,
        maxDimension
        / Math.max(
          bitmap.width,
          bitmap.height,
        ),
      );

    const width =
      Math.max(
        1,
        Math.round(
          bitmap.width
          * scale,
        ),
      );

    const height =
      Math.max(
        1,
        Math.round(
          bitmap.height
          * scale,
        ),
      );

    const canvas =
      document.createElement(
        "canvas",
      );

    canvas.width = width;
    canvas.height = height;

    const context =
      canvas.getContext(
        "2d",
      );

    if (!context) {
      bitmap.close();

      throw new Error(
        "Unable to process photo.",
      );
    }

    context.drawImage(
      bitmap,
      0,
      0,
      width,
      height,
    );

    bitmap.close();

    const blob =
      await new Promise<Blob | null>(
        (resolve) =>
          canvas.toBlob(
            resolve,
            "image/jpeg",
            0.76,
          ),
      );

    if (!blob) {
      throw new Error(
        "Unable to compress photo.",
      );
    }

    if (
      blob.size
      > 1_450_000
    ) {
      throw new Error(
        "Photo is still too large after compression. Please take a lower resolution photo.",
      );
    }

    const safeName =
      file.name
        .replace(
          /\.[^/.]+$/,
          "",
        )
      || "work-photo";

    return new File(
      [blob],
      `${safeName}.jpg`,
      {
        type: "image/jpeg",
      },
    );
  }


  async function removeWorkPhoto(
    index: number,
  ) {
    const nextPhotos =
      workPhotos.filter(
        (
          _,
          photoIndex,
        ) =>
          photoIndex
          !== index,
      );

    setWorkPhotos(
      nextPhotos,
    );

    const previews =
      await Promise.all(
        nextPhotos.map(
          (
            photo,
          ) =>
            fileToDataUrl(
              photo,
            ),
        ),
      );

    setWorkPhotoPreviews(
      previews,
    );
  }


  function signaturePoint(
    event:
      React.PointerEvent<
        HTMLCanvasElement
      >,
  ) {
    const canvas =
      signatureCanvasRef
        .current;

    if (!canvas) {
      return null;
    }

    const rect =
      canvas
        .getBoundingClientRect();

    return {
      x:
        (
          event.clientX
          - rect.left
        )
        * (
          canvas.width
          / rect.width
        ),

      y:
        (
          event.clientY
          - rect.top
        )
        * (
          canvas.height
          / rect.height
        ),
    };
  }


  function startSignature(
    event:
      React.PointerEvent<
        HTMLCanvasElement
      >,
  ) {
    const canvas =
      signatureCanvasRef
        .current;

    const point =
      signaturePoint(
        event,
      );

    if (
      !canvas
      || !point
    ) {
      return;
    }

    const context =
      canvas.getContext(
        "2d",
      );

    if (!context) {
      return;
    }

    event.preventDefault();

    canvas.setPointerCapture(
      event.pointerId,
    );

    signatureDrawingRef
      .current = true;

    context.beginPath();

    context.moveTo(
      point.x,
      point.y,
    );

    context.lineWidth = 4;
    context.lineCap =
      "round";
    context.lineJoin =
      "round";
    context.strokeStyle =
      "#111827";
  }


  function drawSignature(
    event:
      React.PointerEvent<
        HTMLCanvasElement
      >,
  ) {
    if (
      !signatureDrawingRef
        .current
    ) {
      return;
    }

    const canvas =
      signatureCanvasRef
        .current;

    const point =
      signaturePoint(
        event,
      );

    if (
      !canvas
      || !point
    ) {
      return;
    }

    const context =
      canvas.getContext(
        "2d",
      );

    if (!context) {
      return;
    }

    event.preventDefault();

    context.lineTo(
      point.x,
      point.y,
    );

    context.stroke();

    setSignatureHasInk(
      true,
    );
  }


  function stopSignature(
    event:
      React.PointerEvent<
        HTMLCanvasElement
      >,
  ) {
    const canvas =
      signatureCanvasRef
        .current;

    signatureDrawingRef
      .current = false;

    if (
      canvas
      && canvas.hasPointerCapture(
        event.pointerId,
      )
    ) {
      canvas.releasePointerCapture(
        event.pointerId,
      );
    }
  }


  function clearSignature() {
    const canvas =
      signatureCanvasRef
        .current;

    if (!canvas) {
      return;
    }

    const context =
      canvas.getContext(
        "2d",
      );

    if (!context) {
      return;
    }

    context.clearRect(
      0,
      0,
      canvas.width,
      canvas.height,
    );

    setSignatureHasInk(
      false,
    );
  }


  async function signatureBlob():
    Promise<Blob> {
    const canvas =
      signatureCanvasRef
        .current;

    if (!canvas) {
      throw new Error(
        "Customer signature is required.",
      );
    }

    return await new Promise<
      Blob
    >(
      (
        resolve,
        reject,
      ) => {
        canvas.toBlob(
          (
            blob,
          ) => {
            if (!blob) {
              reject(
                new Error(
                  "Unable to save customer signature.",
                ),
              );

              return;
            }

            resolve(
              blob,
            );
          },
          "image/png",
        );
      },
    );
  }


  const refreshJob =
    useCallback(
      async (
        targetJobId: number,
      ) => {
        const detail =
          await getServiceJob(
            targetJobId,
          );

        setJob(detail);

        return detail;
      },
      [],
    );


  const loadPage =
    useCallback(
      async () => {
        if (
          !Number.isInteger(jobId)
          || jobId <= 0
        ) {
          setError(
            "Invalid service job.",
          );

          setLoading(false);
          return;
        }

        try {
          setError("");

          const currentUser =
            await getCurrentUser();

          if (
            !isTechnicianRole(
              currentUser.role,
            )
          ) {
            router.replace(
              "/dashboard",
            );

            return;
          }

          setUser(currentUser);

          const detail =
            await refreshJob(
              jobId,
            );

          const currentUserId =
            Number(currentUser.id);

          const assignedIds =
            [
              detail.technician_id,
              ...(
                (
                  detail as unknown as {
                    secondary_technician_ids?:
                      number[];
                  }
                )
                  .secondary_technician_ids
                ?? []
              ),
            ]
              .filter(
                (
                  value,
                ): value is number =>
                  typeof value
                  === "number",
              );

          if (
            !assignedIds.includes(
              currentUserId,
            )
          ) {
            setJob(null);

            setError(
              "This job is not assigned to you.",
            );

            return;
          }
        } catch (
          requestError
        ) {
          setError(
            apiErrorMessage(
              requestError,
            ),
          );
        } finally {
          setLoading(false);
        }
      },
      [
        jobId,
        refreshJob,
        router,
      ],
    );


  useEffect(() => {
    const timeout =
      window.setTimeout(
        () => {
          void loadPage();
        },
        0,
      );

    return () => {
      window.clearTimeout(
        timeout,
      );
    };
  }, [loadPage]);


  useEffect(() => {
    return () => {
      const stream =
        cameraStreamRef.current;

      if (!stream) {
        return;
      }

      for (
        const track
        of stream.getTracks()
      ) {
        track.stop();
      }

      cameraStreamRef.current = null;
    };
  }, []);


  // ACTIVE_JOB_LOCATION_ASSOCIATION_EFFECT
  useEffect(() => {
    if (
      !job
      || !user
      || !Number.isInteger(jobId)
      || jobId <= 0
      || !navigator.geolocation
    ) {
      return;
    }

    let active = true;

    const sendJobLocation = (
      position: GeolocationPosition,
    ) => {
      if (!active) {
        return;
      }

      void writeTechnicianLocation({
        service_job_id: jobId,
        latitude:
          Number(
            position.coords.latitude
              .toFixed(6),
          ),
        longitude:
          Number(
            position.coords.longitude
              .toFixed(6),
          ),
        accuracy_meters:
          Number(
            position.coords.accuracy
              .toFixed(2),
          ),
        client_recorded_at:
          new Date(
            position.timestamp,
          ).toISOString(),
        tracking_state: "active",
      }).catch(() => {
        // The persistent technician tracker
        // continues handling location status.
      });
    };

    navigator.geolocation.getCurrentPosition(
      sendJobLocation,
      () => {
        // Existing tracker UI reports
        // browser/device location failures.
      },
      {
        enableHighAccuracy: false,
        timeout: 60000,
        maximumAge: 60000,
      },
    );

    return () => {
      active = false;
    };
  }, [
    job,
    jobId,
    user,
  ]);


  const canComplete =
    useMemo(
      () =>
        Boolean(
          job
          && job.status !== "ready"
          && job.status !== "delivered"
          && job.status !== "cancelled",
        ),
      [job],
    );


  async function handleRefresh() {
    if (
      refreshing
      || !job
    ) {
      return;
    }

    try {
      setRefreshing(true);
      setError("");

      await refreshJob(
        job.id,
      );
    } catch (
      requestError
    ) {
      setError(
        apiErrorMessage(
          requestError,
        ),
      );
    } finally {
      setRefreshing(false);
    }
  }


  function openPartForm() {
    setError("");
    setActionMode("part");

    void loadPartPicker();
  }


  function openCompleteForm() {
    if (
      !job
      || !canComplete
    ) {
      return;
    }

    setError("");

    setJobResult(
      job.work_performed
      || job.testing_result
      || "",
    );

    setCompletionNotes("");
    setWorkPhotos([]);
    setWorkPhotoPreviews([]);
    setSignatureHasInk(false);

    window.setTimeout(
      () => {
        clearSignature();
      },
      0,
    );

    setActionMode("complete");
  }


  function closeAction() {
    if (
      partSaving
      || completeSaving
    ) {
      return;
    }

    stopLiveCamera();
    setCameraError("");
    setActionMode(null);
    setError("");
  }


  const selectedPartProduct =
    useMemo(
      () =>
        partProducts.find(
          (product) =>
            String(product.id)
            === productId,
        ) ?? null,
      [
        partProducts,
        productId,
      ],
    );

  const selectedPartBalance =
    useMemo(
      () =>
        partBalances.find(
          (balance) =>
            String(
              balance.product_id,
            ) === productId
            && String(
              balance.warehouse_id,
            ) === warehouseId,
        ) ?? null,
      [
        partBalances,
        productId,
        warehouseId,
      ],
    );

  const selectedAvailableQuantity =
    selectedPartBalance
      ? Number(
          selectedPartBalance
            .quantity_available
          ?? 0,
        )
      : 0;


  const selectedPartWarehouse =
    useMemo(
      () =>
        partWarehouses.find(
          (warehouse) =>
            String(
              warehouse.id,
            ) === warehouseId,
        ) ?? null,
      [
        partWarehouses,
        warehouseId,
      ],
    );


  function resolveTechnicianPart(
    nextProductId: string,
    products:
      TechnicianPartProduct[] =
        partProducts,
    warehouses:
      TechnicianPartWarehouse[] =
        partWarehouses,
    balances:
      TechnicianPartBalance[] =
        partBalances,
  ) {
    setProductId(
      nextProductId,
    );

    setWarehouseId("");
    setUnitPrice("");

    if (!nextProductId) {
      return;
    }

    const selectedProduct =
      products.find(
        (product) =>
          String(
            product.id,
          ) === nextProductId,
      );

    if (selectedProduct) {
      const productWithPrice =
        selectedProduct as unknown as {
          selling_price?:
            | string
            | number
            | null;
        };

      const sellingPrice =
        productWithPrice.selling_price;

      if (
        sellingPrice !== undefined
        && sellingPrice !== null
        && String(
          sellingPrice,
        ).trim() !== ""
      ) {
        setUnitPrice(
          String(
            sellingPrice,
          ),
        );
      }
    }

    const bestBalance =
      balances
        .filter(
          (balance) =>
            String(
              balance.product_id,
            ) === nextProductId
            && Number(
              balance.quantity_available
              ?? 0,
            ) > 0,
        )
        .sort(
          (
            first,
            second,
          ) =>
            Number(
              second.quantity_available
              ?? 0,
            )
            - Number(
              first.quantity_available
              ?? 0,
            ),
        )[0];

    if (!bestBalance) {
      return;
    }

    const selectedWarehouse =
      warehouses.find(
        (warehouse) =>
          warehouse.id
          === bestBalance
            .warehouse_id
          && warehouse.is_active
            !== false,
      );

    if (selectedWarehouse) {
      setWarehouseId(
        String(
          selectedWarehouse.id,
        ),
      );
    }
  }


  function selectTechnicianPart(
    nextProductId: string,
  ) {
    resolveTechnicianPart(
      nextProductId,
    );
  }


  async function loadPartPicker() {
    if (partPickerLoading) {
      return;
    }

    try {
      setPartPickerLoading(true);
      setError("");

      const cleanedSearch =
        partSearch
          .trim()
          .toLowerCase();

      const [
        searchedResponse,
        fallbackResponse,
        warehousesResponse,
        balancesResponse,
      ] =
        await Promise.all([
          getProducts({
            page: 1,
            pageSize: 100,
            search:
              partSearch.trim()
              || undefined,
          }),
          cleanedSearch
            ? getProducts({
                page: 1,
                pageSize: 100,
              })
            : Promise.resolve(null),
          getWarehouses(true),
          getStockBalances({}),
        ]);

      const extractProducts = (
        response: unknown,
      ) => {
        if (!response) {
          return [] as TechnicianPartProduct[];
        }

        const candidate =
          response as {
            items?:
              TechnicianPartProduct[];
            data?:
              TechnicianPartProduct[];
            results?:
              TechnicianPartProduct[];
          };

        return (
          candidate.items
          ?? candidate.data
          ?? candidate.results
          ?? []
        );
      };

      const searchedProducts =
        extractProducts(
          searchedResponse,
        );

      const fallbackProducts =
        extractProducts(
          fallbackResponse,
        );

      const combinedProducts =
        [
          ...searchedProducts,
          ...fallbackProducts,
        ];

      const uniqueProducts =
        Array.from(
          new Map(
            combinedProducts.map(
              (product) => [
                product.id,
                product,
              ],
            ),
          ).values(),
        );

      const activeProducts =
        uniqueProducts.filter(
          (product) =>
            product.is_active
            !== false,
        );

      const matchesSearch = (
        product:
          TechnicianPartProduct,
      ) => {
        if (!cleanedSearch) {
          return true;
        }

        const searchableProduct =
          product as unknown as {
            id: number;
            name?: string | null;
            sku?: string | null;
            product_code?:
              string | null;
            code?: string | null;
            barcode?: string | null;
          };

        const values = [
          searchableProduct.name,
          searchableProduct.sku,
          searchableProduct
            .product_code,
          searchableProduct.code,
          searchableProduct.barcode,
          String(
            searchableProduct.id,
          ),
          `prd-${String(
            searchableProduct.id,
          ).padStart(
            6,
            "0",
          )}`,
        ];

        return values.some(
          (value) =>
            String(
              value ?? "",
            )
              .toLowerCase()
              .includes(
                cleanedSearch,
              ),
        );
      };

      const matchedProducts =
        activeProducts.filter(
          matchesSearch,
        );

      const products =
        matchedProducts.length
          ? matchedProducts
          : searchedProducts.filter(
              (product) =>
                product.is_active
                !== false,
            );

      const warehouses =
        (
          warehousesResponse as TechnicianPartWarehouse[]
        ).filter(
          (warehouse) =>
            warehouse.is_active
            !== false,
        );

      const balances =
        balancesResponse as TechnicianPartBalance[];

      setPartProducts(
        products,
      );

      setPartWarehouses(
        warehouses,
      );

      setPartBalances(
        balances,
      );

      if (products.length === 1) {
        resolveTechnicianPart(
          String(
            products[0].id,
          ),
          products,
          warehouses,
          balances,
        );
      } else if (
        productId
        && products.some(
          (product) =>
            String(
              product.id,
            ) === productId,
        )
      ) {
        resolveTechnicianPart(
          productId,
          products,
          warehouses,
          balances,
        );
      } else {
        setProductId("");
        setWarehouseId("");
        setUnitPrice("");
      }

      if (
        cleanedSearch
        && products.length === 0
      ) {
        setError(
          "No matching parts found. Search by product name, SKU, product code, or product ID.",
        );
      }
    } catch (requestError) {
      setError(
        apiErrorMessage(
          requestError,
        ),
      );
    } finally {
      setPartPickerLoading(false);
    }
  }


  async function submitPart(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (
      partSaving
      || !job
    ) {
      return;
    }

    const parsedProductId =
      Number(productId);

    const parsedWarehouseId =
      Number(warehouseId);

    const cleanedQuantity =
      quantity.trim();

    if (
      !Number.isInteger(
        parsedProductId,
      )
      || parsedProductId <= 0
    ) {
      setError(
        "Enter a valid product ID.",
      );

      return;
    }

    if (
      !Number.isInteger(
        parsedWarehouseId,
      )
      || parsedWarehouseId <= 0
    ) {
      setError(
        "Enter a valid warehouse ID.",
      );

      return;
    }

    if (
      !cleanedQuantity
      || Number(cleanedQuantity)
        <= 0
    ) {
      setError(
        "Enter a valid quantity.",
      );

      return;
    }

    if (
      selectedPartBalance
      && Number(cleanedQuantity)
        > selectedAvailableQuantity
    ) {
      setError(
        "Requested quantity exceeds available stock.",
      );

      return;
    }

    try {
      setPartSaving(true);
      setError("");

      await addServicePart(
        job.id,
        {
          product_id:
            parsedProductId,

          warehouse_id:
            parsedWarehouseId,

          quantity:
            cleanedQuantity,

          unit_price:
            unitPrice.trim()
              || null,

          notes:
            partNotes.trim()
              || null,
        },
      );

      await refreshJob(
        job.id,
      );

      setPartSearch("");
      setProductId("");
      setWarehouseId("");
      setQuantity("1");
      setUnitPrice("");
      setPartNotes("");
      setActionMode(null);
    } catch (
      requestError
    ) {
      setError(
        apiErrorMessage(
          requestError,
        ),
      );
    } finally {
      setPartSaving(false);
    }
  }


  async function submitComplete(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (
      completeSaving
      || !job
      || !canComplete
    ) {
      return;
    }

    const result =
      jobResult.trim();

    if (!result) {
      setError(
        "Enter the job result.",
      );

      return;
    }

    if (
      result.length > 2000
    ) {
      setError(
        "Job result must be 2000 characters or less.",
      );

      return;
    }

    const notes =
      completionNotes.trim();

    if (
      notes.length > 1000
    ) {
      setError(
        "Completion notes must be 1000 characters or less.",
      );

      return;
    }

    if (
      workPhotos.length < 1
      || workPhotos.length > 5
    ) {
      setError(
        "Add between 1 and 5 work photos before completing the job.",
      );

      return;
    }

    if (!signatureHasInk) {
      setError(
        "Customer signature is required before completing the job.",
      );

      return;
    }

    try {
      setCompleteSaving(true);
      setError("");

      const customerSignature =
        await signatureBlob();

      await uploadServiceCompletionEvidence(
        job.id,
        workPhotos,
        customerSignature,
      );

      if (!navigator.geolocation) {
        throw new Error(
          "Current location is required to complete this job. Location services are not available on this device.",
        );
      }

      const completionPosition =
        await new Promise<GeolocationPosition>(
          (resolve, reject) => {
            navigator.geolocation.getCurrentPosition(
              resolve,
              reject,
              {
                enableHighAccuracy: false,
                timeout: 60000,
                maximumAge: 60000,
              },
            );
          },
        );

      await writeTechnicianLocation({
        service_job_id: job.id,
        latitude:
          Number(
            completionPosition.coords.latitude
              .toFixed(6),
          ),
        longitude:
          Number(
            completionPosition.coords.longitude
              .toFixed(6),
          ),
        accuracy_meters:
          Number(
            completionPosition.coords.accuracy
              .toFixed(2),
          ),
        client_recorded_at:
          new Date(
            completionPosition.timestamp,
          ).toISOString(),
        tracking_state: "active",
      });

      await completeServiceJob(
        job.id,
        {
          job_result:
            result,

          notes:
            notes || null,
        },
      );

      await refreshJob(
        job.id,
      );

      stopLiveCamera();
      setCameraError("");
      setActionMode(null);
      setCompletionNotes("");
      setWorkPhotos([]);
      setWorkPhotoPreviews([]);
      setSignatureHasInk(false);
    } catch (
      requestError
    ) {
      setError(
        apiErrorMessage(
          requestError,
        ),
      );
    } finally {
      setCompleteSaving(false);
    }
  }


  if (loading) {
    return (
      <main
        className={
          styles.page
        }
      >
        <div
          className={
            styles.centerState
          }
        >
          <LoaderCircle
            className={
              styles.spin
            }
            size={30}
          />

          <strong>
            Loading job
          </strong>

          <span>
            Preparing service details...
          </span>
        </div>
      </main>
    );
  }


  if (!job) {
    return (
      <main
        className={
          styles.page
        }
      >
        <div
          className={
            styles.centerState
          }
        >
          <AlertCircle
            size={34}
          />

          <strong>
            Job unavailable
          </strong>

          <span>
            {error
              || "Unable to open this job."}
          </span>

          <button
            type="button"
            className={
              styles.primaryButton
            }
            onClick={() =>
              router.push(
                "/technician",
              )
            }
          >
            Back to My Jobs
          </button>
        </div>
      </main>
    );
  }


  return (
    <main
      className={
        styles.page
      }
    >
      <header
        className={
          styles.header
        }
      >
        <button
          type="button"
          className={
            styles.iconButton
          }
          onClick={() =>
            router.push(
              "/technician",
            )
          }
          aria-label="Back to jobs"
        >
          <ArrowLeft
            size={20}
          />
        </button>

        <div
          className={
            styles.headerText
          }
        >
          <span>
            Technician Job
          </span>

          <strong>
            {job.job_number}
          </strong>
        </div>

        <button
          type="button"
          className={
            styles.iconButton
          }
          onClick={() =>
            void handleRefresh()
          }
          disabled={
            refreshing
          }
          aria-label="Refresh job"
        >
          <RefreshCw
            size={19}
            className={
              refreshing
                ? styles.spin
                : undefined
            }
          />
        </button>
      </header>


      <section
        className={
          styles.content
        }
      >
        {error ? (
          <div
            className={
              styles.errorBox
            }
          >
            <AlertCircle
              size={18}
            />

            <span>
              {error}
            </span>
          </div>
        ) : null}


        <section
          className={
            styles.heroCard
          }
        >
          <div
            className={
              styles.heroTop
            }
          >
            <div>
              <span
                className={
                  styles.eyebrow
                }
              >
                Current status
              </span>

              <h1>
                {statusLabel(
                  job.status,
                )}
              </h1>
            </div>

            <span
              className={
                styles.statusBadge
              }
            >
              {statusLabel(
                job.priority,
              )}
            </span>
          </div>

          <p>
            {job.complaint}
          </p>
        </section>


        <section
          className={
            styles.card
          }
        >
          <div
            className={
              styles.sectionTitle
            }
          >
            <UserRound
              size={18}
            />

            <strong>
              Customer
            </strong>
          </div>

          <div
            className={
              styles.detailGrid
            }
          >
            <div>
              <span>Name</span>
              <strong>
                {displayValue(
                  job.customer_name,
                )}
              </strong>
            </div>

            <div>
              <span>Phone</span>

              <strong>
                {displayValue(
                  job.customer_phone,
                )}
              </strong>
            </div>
          </div>

          {job.customer_phone ? (
            <a
              className={
                styles.callButton
              }
              href={
                `tel:${job.customer_phone}`
              }
            >
              <Phone
                size={17}
              />
              Call Customer
            </a>
          ) : null}
        </section>


        <section
          className={
            styles.card
          }
        >
          <div
            className={
              styles.sectionTitle
            }
          >
            <Wrench
              size={18}
            />

            <strong>
              Service Item
            </strong>
          </div>

          <div
            className={
              styles.detailGrid
            }
          >
            <div>
              <span>Product</span>
              <strong>
                {displayValue(
                  job.product_name,
                )}
              </strong>
            </div>

            <div>
              <span>Brand</span>
              <strong>
                {displayValue(
                  job.brand_name,
                )}
              </strong>
            </div>

            <div>
              <span>Model</span>
              <strong>
                {displayValue(
                  job.model_number,
                )}
              </strong>
            </div>

            <div>
              <span>Serial</span>
              <strong>
                {displayValue(
                  job.serial_number,
                )}
              </strong>
            </div>
          </div>
        </section>


        <section
          className={
            styles.card
          }
        >
          <div
            className={
              styles.sectionTitle
            }
          >
            <MapPin
              size={18}
            />

            <strong>
              Job Information
            </strong>
          </div>

          <div
            className={
              styles.stack
            }
          >
            <div>
              <span>
                Reported issue
              </span>

              <p>
                {displayValue(
                  job.reported_issue,
                )}
              </p>
            </div>

            {job.special_notes?.trim() ? (
              <div>
                <span>
                  Special Notes
                </span>

                <p>
                  {job.special_notes}
                </p>
              </div>
            ) : null}

            <div>
              <span>
                Diagnosis
              </span>

              <p>
                {displayValue(
                  job.technician_diagnosis,
                )}
              </p>
            </div>

            <div>
              <span>
                Work performed
              </span>

              <p>
                {displayValue(
                  job.work_performed,
                )}
              </p>
            </div>

            <div>
              <span>
                Testing result
              </span>

              <p>
                {displayValue(
                  job.testing_result,
                )}
              </p>
            </div>
          </div>
        </section>


        <section
          className={
            styles.card
          }
        >
          <div
            className={
              styles.sectionHeading
            }
          >
            <div
              className={
                styles.sectionTitle
              }
            >
              <PackagePlus
                size={18}
              />

              <strong>
                Parts Used
              </strong>
            </div>

            <button
              type="button"
              className={
                styles.smallButton
              }
              onClick={
                openPartForm
              }
            >
              Add Part
            </button>
          </div>

          {job.parts.length
            === 0 ? (
            <p
              className={
                styles.emptyText
              }
            >
              No parts added to this job.
            </p>
          ) : (
            <div
              className={
                styles.partList
              }
            >
              {job.parts.map(
                (part) => (
                  <article
                    key={
                      part.id
                    }
                    className={
                      styles.partRow
                    }
                  >
                    <div>
                      <strong>
                        Product #
                        {part.product_id}
                      </strong>

                      <span>
                        Warehouse #
                        {part.warehouse_id}
                      </span>
                    </div>

                    <strong>
                      Qty {part.quantity}
                    </strong>
                  </article>
                ),
              )}
            </div>
          )}
        </section>


        <section
          className={
            styles.completeCard
          }
        >
          <div
            className={
              styles.sectionTitle
            }
          >
            <ClipboardCheck
              size={19}
            />

            <strong>
              Finish Service
            </strong>
          </div>

          {canComplete ? (
            <>
              <p>
                Add any required parts first,
                then enter the final job result
                and complete the service.
              </p>

              <button
                type="button"
                className={
                  styles.completeButton
                }
                onClick={
                  openCompleteForm
                }
              >
                <CheckCircle2
                  size={18}
                />

                Enter Result & Complete
              </button>
            </>
          ) : (
            <div
              className={
                styles.completedState
              }
            >
              <CheckCircle2
                size={20}
              />

              <span>
                This job is currently{" "}
                <strong>
                  {statusLabel(
                    job.status,
                  )}
                </strong>.
              </span>
            </div>
          )}
        </section>


        <footer
          className={
            styles.footer
          }
        >
          Signed in as{" "}
          <strong>
            {
              (
                user as unknown as {
                  full_name?:
                    string | null;
                }
              )
                ?.full_name
              || `User #${user?.id}`
            }
          </strong>
        </footer>
      </section>


      {actionMode ? (
        <div
          className={
            styles.overlay
          }
          role="presentation"
        >
          <section
            className={
              styles.sheet
            }
          >
            <div
              className={
                styles.sheetHandle
              }
            />

            {actionMode
              === "part" ? (
              <form
                onSubmit={
                  submitPart
                }
              >
                <div
                  className={
                    styles.sheetTitle
                  }
                >
                  <PackagePlus
                    size={21}
                  />

                  <div>
                    <strong>
                      Add Part
                    </strong>

                    <span>
                      Add a part used for this job.
                    </span>
                  </div>
                </div>

                <label
                  className={
                    styles.field
                  }
                >
                  <span>
                    Search Part
                  </span>

                  <div
                    className={
                      styles.pickerSearchRow
                    }
                  >
                    <input
                      type="search"
                      value={
                        partSearch
                      }
                      onChange={(
                        event,
                      ) =>
                        setPartSearch(
                          event.target.value,
                        )
                      }
                      placeholder={
                        "Search by product name or SKU"
                      }
                    />

                    <button
                      type="button"
                      className={
                        styles.secondaryButton
                      }
                      disabled={
                        partPickerLoading
                      }
                      onClick={() =>
                        void loadPartPicker()
                      }
                    >
                      {partPickerLoading
                        ? "Loading..."
                        : "Search"}
                    </button>
                  </div>
                </label>

                <label
                  className={
                    styles.field
                  }
                >
                  <span>
                    Part *
                  </span>

                  <select
                    required
                    value={
                      productId
                    }
                    onChange={(
                      event,
                    ) =>
                      selectTechnicianPart(
                        event.target.value,
                      )
                    }
                  >
                    <option value="">
                      Select part
                    </option>

                    {partProducts.map(
                      (product) => (
                        <option
                          key={
                            product.id
                          }
                          value={
                            product.id
                          }
                        >
                          {product.name}
                          {product.sku
                            ? ` - ${product.sku}`
                            : ""}
                        </option>
                      ),
                    )}
                  </select>

                  {selectedPartProduct ? (
                    <small>
                      Selected:{" "}
                      {
                        selectedPartProduct
                          .name
                      }
                    </small>
                  ) : null}
                </label>

                <label
                  className={
                    styles.field
                  }
                >
                  <span>
                    Warehouse
                  </span>

                  <input
                    type="text"
                    readOnly
                    value={
                      selectedPartWarehouse
                        ? selectedPartWarehouse.name
                        : productId
                          ? "No warehouse with available stock"
                          : "Select a part first"
                    }
                  />

                  {selectedPartBalance ? (
                    <small>
                      Auto selected · Available stock:{" "}
                      {
                        selectedAvailableQuantity
                      }
                    </small>
                  ) : productId ? (
                    <small>
                      No available stock found for this part.
                    </small>
                  ) : (
                    <small>
                      Warehouse will be selected automatically.
                    </small>
                  )}
                </label>

                <label
                  className={
                    styles.field
                  }
                >
                  <span>
                    Quantity *
                  </span>

                  <input
                    type="number"
                    min="0.001"
                    step="0.001"
                    required
                    value={
                      quantity
                    }
                    onChange={(
                      event,
                    ) =>
                      setQuantity(
                        event.target.value,
                      )
                    }
                  />
                </label>

                <label
                  className={
                    styles.field
                  }
                >
                  <span>
                    Unit Price
                  </span>

                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={
                      unitPrice
                    }
                    readOnly
                    onChange={(
                      event,
                    ) =>
                      setUnitPrice(
                        event.target.value,
                      )
                    }
                  />

                  <small>
                    Selling price is filled automatically.
                  </small>
                </label>

                <label
                  className={
                    styles.field
                  }
                >
                  <span>
                    Notes
                  </span>

                  <textarea
                    rows={3}
                    value={
                      partNotes
                    }
                    onChange={(
                      event,
                    ) =>
                      setPartNotes(
                        event.target.value,
                      )
                    }
                  />
                </label>

                <div
                  className={
                    styles.sheetActions
                  }
                >
                  <button
                    type="button"
                    className={
                      styles.secondaryButton
                    }
                    onClick={
                      closeAction
                    }
                    disabled={
                      partSaving
                    }
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    className={
                      styles.primaryButton
                    }
                    disabled={
                      partSaving
                    }
                  >
                    {partSaving
                      ? "Adding..."
                      : "Add Part"}
                  </button>
                </div>
              </form>
            ) : (
              <form
                onSubmit={
                  submitComplete
                }
              >
                <div
                  className={
                    styles.sheetTitle
                  }
                >
                  <ClipboardCheck
                    size={21}
                  />

                  <div>
                    <strong>
                      Complete Job
                    </strong>

                    <span>
                      Enter the final service result.
                    </span>
                  </div>
                </div>

                <label
                  className={
                    styles.field
                  }
                >
                  <span>
                    Job Result *
                  </span>

                  <textarea
                    rows={6}
                    required
                    maxLength={2000}
                    value={
                      jobResult
                    }
                    onChange={(
                      event,
                    ) =>
                      setJobResult(
                        event.target.value,
                      )
                    }
                    placeholder={
                      "Example: Replaced capacitor and tested unit successfully."
                    }
                  />

                  <small>
                    {jobResult.length}/2000
                  </small>
                </label>

                <label
                  className={
                    styles.field
                  }
                >
                  <span>
                    Completion Notes
                  </span>

                  <textarea
                    rows={3}
                    maxLength={1000}
                    value={
                      completionNotes
                    }
                    onChange={(
                      event,
                    ) =>
                      setCompletionNotes(
                        event.target.value,
                      )
                    }
                  />

                  <small>
                    {completionNotes.length}/1000
                  </small>
                </label>

                <section
                  className={
                    styles.evidenceSection
                  }
                >
                  <div
                    className={
                      styles.evidenceHeading
                    }
                  >
                    <ImagePlus
                      size={20}
                    />

                    <div>
                      <strong>
                        Work Photos *
                      </strong>

                      <span>
                        Take 1 to 5 new photos of the completed work using the live camera.
                      </span>
                    </div>
                  </div>

                  <div
                    className={
                      styles.photoActionRow
                    }
                  >
                    <button
                      type="button"
                      className={
                        styles.photoButton
                      }
                      disabled={
                        photoProcessing
                        || cameraStarting
                        || workPhotos.length
                          >= 5
                      }
                      onClick={() =>
                        void startLiveCamera()
                      }
                    >
                      <Camera
                        size={18}
                      />

                      {cameraStarting
                        ? "Opening camera..."
                        : "Take photo"}
                    </button>
                  </div>

                  {cameraError ? (
                    <div
                      className={
                        styles.cameraError
                      }
                      role="alert"
                    >
                      {cameraError}
                    </div>
                  ) : null}

                  {cameraOpen ? (
                    <div
                      className={
                        styles.cameraPanel
                      }
                    >
                      <video
                        ref={
                          cameraVideoRef
                        }
                        className={
                          styles.cameraPreview
                        }
                        autoPlay
                        playsInline
                        muted
                      />

                      <div
                        className={
                          styles.cameraActions
                        }
                      >
                        <button
                          type="button"
                          className={
                            styles.photoButton
                          }
                          disabled={
                            photoProcessing
                          }
                          onClick={() =>
                            void captureLivePhoto()
                          }
                        >
                          <Camera
                            size={18}
                          />

                          Capture photo
                        </button>

                        <button
                          type="button"
                          className={
                            styles.secondaryButton
                          }
                          disabled={
                            photoProcessing
                          }
                          onClick={
                            stopLiveCamera
                          }
                        >
                          Cancel camera
                        </button>
                      </div>
                    </div>
                  ) : null}

                  <small
                    className={
                      styles.evidenceHint
                    }
                  >
                    {photoProcessing
                      ? "Processing photos..."
                      : `${workPhotos.length}/5 photos added`}
                  </small>

                  {workPhotoPreviews.length
                    > 0 ? (
                    <div
                      className={
                        styles.photoGrid
                      }
                    >
                      {workPhotoPreviews.map(
                        (
                          preview,
                          index,
                        ) => (
                          <div
                            className={
                              styles.photoPreview
                            }
                            key={
                              `${index}-${preview.length}`
                            }
                          >
                            <img
                              src={
                                preview
                              }
                              alt={
                                `Work photo ${index + 1}`
                              }
                            />

                            <button
                              type="button"
                              className={
                                styles.photoRemoveButton
                              }
                              onClick={() =>
                                void removeWorkPhoto(
                                  index,
                                )
                              }
                              disabled={
                                completeSaving
                              }
                              aria-label={
                                `Remove photo ${index + 1}`
                              }
                            >
                              <Trash2
                                size={16}
                              />
                            </button>
                          </div>
                        ),
                      )}
                    </div>
                  ) : null}
                </section>

                <section
                  className={
                    styles.evidenceSection
                  }
                >
                  <div
                    className={
                      styles.evidenceHeading
                    }
                  >
                    <PenLine
                      size={20}
                    />

                    <div>
                      <strong>
                        Customer Signature *
                      </strong>

                      <span>
                        Ask the customer to sign inside the box.
                      </span>
                    </div>
                  </div>

                  <canvas
                    ref={
                      signatureCanvasRef
                    }
                    width={700}
                    height={260}
                    className={
                      styles.signatureCanvas
                    }
                    onPointerDown={
                      startSignature
                    }
                    onPointerMove={
                      drawSignature
                    }
                    onPointerUp={
                      stopSignature
                    }
                    onPointerCancel={
                      stopSignature
                    }
                    onPointerLeave={
                      stopSignature
                    }
                  />

                  <div
                    className={
                      styles.signatureFooter
                    }
                  >
                    <span>
                      {signatureHasInk
                        ? "Signature captured"
                        : "Signature required"}
                    </span>

                    <button
                      type="button"
                      className={
                        styles.clearSignatureButton
                      }
                      onClick={
                        clearSignature
                      }
                      disabled={
                        completeSaving
                      }
                    >
                      Clear
                    </button>
                  </div>
                </section>

                <div
                  className={
                    styles.sheetActions
                  }
                >
                  <button
                    type="button"
                    className={
                      styles.secondaryButton
                    }
                    onClick={
                      closeAction
                    }
                    disabled={
                      completeSaving
                    }
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    className={
                      styles.completeButton
                    }
                    disabled={
                      completeSaving
                    }
                  >
                    {completeSaving
                      ? "Completing..."
                      : "Complete Job"}
                  </button>
                </div>
              </form>
            )}
          </section>
        </div>
      ) : null}
    </main>
  );
}
