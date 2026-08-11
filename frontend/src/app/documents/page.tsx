"use client";

import axios from "axios";

import {
  BadgeCheck,
  CircleAlert,
  Clock3,
  FileDown,
  FileText,
  Loader2,
  ReceiptText,
  Search,
  ShieldCheck,
} from "lucide-react";

import {
  FormEvent,
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
  clearAuthSession,
  getAccessToken,
  getStoredUser,
} from "@/lib/auth";

import {
  downloadPaymentReceiptPdf,
  downloadSalesInvoicePdf,
  saveDownloadedDocument,
} from "@/lib/documents-api";

import type {
  UserResponse,
} from "@/types/auth";

import type {
  DocumentDefinition,
  DocumentDownloadHistoryItem,
  DocumentKind,
} from "@/types/documents";

import styles from "./documents.module.css";


const DOCUMENTS:
DocumentDefinition[] = [
  {
    kind:
      "sales_invoice",

    title:
      "Sales Invoice PDF",

    shortTitle:
      "Sales Invoice",

    description:
      "Generate the official PDF "
      + "for an existing sales "
      + "invoice.",

    idLabel:
      "Invoice ID",

    idPlaceholder:
      "Enter invoice ID",

    permission:
      "sales.view",
  },

  {
    kind:
      "payment_receipt",

    title:
      "Payment Receipt PDF",

    shortTitle:
      "Payment Receipt",

    description:
      "Generate the official PDF "
      + "receipt for an existing "
      + "payment.",

    idLabel:
      "Payment ID",

    idPlaceholder:
      "Enter payment ID",

    permission:
      "payments.view",
  },
];


function errorMessage(
  error:
    unknown,
): string {
  if (
    !axios.isAxiosError(
      error,
    )
  ) {
    if (
      error instanceof Error
    ) {
      return error.message;
    }

    return (
      "Unable to download "
      + "the document."
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
    error.response?.status
    === 403
  ) {
    return (
      "Your account does not "
      + "have permission to "
      + "download this document."
    );
  }

  if (
    error.response?.status
    === 404
  ) {
    return (
      "The requested document "
      + "record was not found."
    );
  }

  return (
    "Unable to download "
    + "the document."
  );
}


function parseRecordId(
  value:
    string,
): number | null {
  const trimmed =
    value.trim();

  if (!trimmed) {
    return null;
  }

  const numeric =
    Number(trimmed);

  if (
    !Number.isInteger(
      numeric,
    )
    || numeric <= 0
  ) {
    return null;
  }

  return numeric;
}


function localTime(
  value:
    string,
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


export default function
DocumentsPage() {
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
    search,
    setSearch,
  ] =
    useState("");

  const [
    salesInvoiceId,
    setSalesInvoiceId,
  ] =
    useState("");

  const [
    paymentId,
    setPaymentId,
  ] =
    useState("");

  const [
    busyKind,
    setBusyKind,
  ] =
    useState<
      DocumentKind | null
    >(
      null,
    );

  const [
    error,
    setError,
  ] =
    useState("");

  const [
    success,
    setSuccess,
  ] =
    useState("");

  const [
    history,
    setHistory,
  ] =
    useState<
      DocumentDownloadHistoryItem[]
    >(
      [],
    );


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


  const filteredDocuments =
    useMemo(
      () => {
        const query =
          search
            .trim()
            .toLowerCase();

        if (!query) {
          return DOCUMENTS;
        }

        return DOCUMENTS.filter(
          (document) =>
            [
              document.title,
              document.shortTitle,
              document.description,
              document.permission,
            ]
              .join(" ")
              .toLowerCase()
              .includes(
                query,
              ),
        );
      },
      [search],
    );


  async function download(
    kind:
      DocumentKind,
  ) {
    const rawId =
      kind === "sales_invoice"
        ? salesInvoiceId
        : paymentId;

    const recordId =
      parseRecordId(
        rawId,
      );

    if (!recordId) {
      setSuccess("");

      setError(
        kind === "sales_invoice"
          ? (
              "Enter a valid positive "
              + "Sales Invoice ID."
            )
          : (
              "Enter a valid positive "
              + "Payment ID."
            ),
      );

      return;
    }

    setBusyKind(
      kind,
    );

    setError("");

    setSuccess("");

    try {
      const downloaded =
        kind === "sales_invoice"
          ? await downloadSalesInvoicePdf(
              recordId,
            )
          : await downloadPaymentReceiptPdf(
              recordId,
            );

      saveDownloadedDocument(
        downloaded,
      );

      const item:
        DocumentDownloadHistoryItem = {
          id:
            (
              `${kind}-`
              + `${recordId}-`
              + `${Date.now()}`
            ),

          kind,

          referenceId:
            recordId,

          filename:
            downloaded.filename,

          downloadedAt:
            new Date()
              .toISOString(),
        };

      setHistory(
        (current) =>
          [
            item,
            ...current,
          ].slice(
            0,
            8,
          ),
      );

      setSuccess(
        `${downloaded.filename} downloaded successfully.`,
      );
    } catch (
      requestError
    ) {
      setError(
        errorMessage(
          requestError,
        ),
      );
    } finally {
      setBusyKind(
        null,
      );
    }
  }


  function submitSales(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    void download(
      "sales_invoice",
    );
  }


  function submitPayment(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    void download(
      "payment_receipt",
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
            DOCUMENT CENTER
          </p>

          <h1>
            Documents
          </h1>

          <p>
            Download official PDF
            documents generated from
            confirmed AC Store sales
            and payment records.
          </p>
        </div>

        <div
          className={
            styles.securityBadge
          }
        >
          <ShieldCheck
            size={17}
          />

          Permission protected
        </div>
      </section>


      <section
        className={
          styles.summaryGrid
        }
      >
        <article>
          <FileText
            size={20}
          />

          <div>
            <span>
              Available document types
            </span>

            <strong>
              2
            </strong>
          </div>
        </article>

        <article>
          <ReceiptText
            size={20}
          />

          <div>
            <span>
              Sales document
            </span>

            <strong>
              Invoice PDF
            </strong>
          </div>
        </article>

        <article>
          <BadgeCheck
            size={20}
          />

          <div>
            <span>
              Payment document
            </span>

            <strong>
              Receipt PDF
            </strong>
          </div>
        </article>

        <article>
          <Clock3
            size={20}
          />

          <div>
            <span>
              Downloads this session
            </span>

            <strong>
              {history.length}
            </strong>
          </div>
        </article>
      </section>


      <section
        className={
          styles.searchCard
        }
      >
        <label>
          <Search
            size={16}
          />

          <input
            value={
              search
            }
            placeholder={
              "Search document type or permission..."
            }
            onChange={
              (event) =>
                setSearch(
                  event
                    .target
                    .value,
                )
            }
          />
        </label>
      </section>


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


      {success && (
        <div
          className={
            styles.successBanner
          }
        >
          <BadgeCheck
            size={17}
          />

          {success}
        </div>
      )}


      <section
        className={
          styles.documentGrid
        }
      >
        {filteredDocuments.map(
          (document) => {
            const isSales =
              document.kind
              === "sales_invoice";

            const value =
              isSales
                ? salesInvoiceId
                : paymentId;

            const busy =
              busyKind
              === document.kind;

            return (
              <article
                key={
                  document.kind
                }
                className={
                  styles.documentCard
                }
              >
                <header>
                  <div
                    className={
                      styles.documentIcon
                    }
                  >
                    {isSales ? (
                      <FileText
                        size={22}
                      />
                    ) : (
                      <ReceiptText
                        size={22}
                      />
                    )}
                  </div>

                  <div>
                    <p className="eyebrow">
                      PDF DOCUMENT
                    </p>

                    <h2>
                      {
                        document.title
                      }
                    </h2>
                  </div>
                </header>


                <p
                  className={
                    styles.description
                  }
                >
                  {
                    document
                      .description
                  }
                </p>


                <div
                  className={
                    styles.permissionRow
                  }
                >
                  <ShieldCheck
                    size={14}
                  />

                  Required permission

                  <code>
                    {
                      document
                        .permission
                    }
                  </code>
                </div>


                <form
                  onSubmit={
                    isSales
                      ? submitSales
                      : submitPayment
                  }
                  className={
                    styles.downloadForm
                  }
                >
                  <label>
                    {
                      document
                        .idLabel
                    }

                    <input
                      type="number"
                      min="1"
                      step="1"
                      value={
                        value
                      }
                      placeholder={
                        document
                          .idPlaceholder
                      }
                      onChange={
                        (event) => {
                          if (isSales) {
                            setSalesInvoiceId(
                              event
                                .target
                                .value,
                            );
                          } else {
                            setPaymentId(
                              event
                                .target
                                .value,
                            );
                          }
                        }
                      }
                    />
                  </label>

                  <button
                    type="submit"
                    disabled={
                      busyKind
                      !== null
                    }
                    className={
                      styles.primaryButton
                    }
                  >
                    {busy ? (
                      <Loader2
                        size={16}
                        className={
                          styles.spin
                        }
                      />
                    ) : (
                      <FileDown
                        size={16}
                      />
                    )}

                    {busy
                      ? "Generating PDF..."
                      : "Download PDF"
                    }
                  </button>
                </form>


                <footer>
                  <span>
                    Read-only document
                    generation
                  </span>

                  <span>
                    No record is modified
                  </span>
                </footer>
              </article>
            );
          },
        )}
      </section>


      {filteredDocuments.length
        === 0 && (
        <section
          className={
            styles.emptyState
          }
        >
          <Search size={28} />

          <strong>
            No document type found
          </strong>

          <span>
            Change the search term
            and try again.
          </span>
        </section>
      )}


      <section
        className={
          styles.historyCard
        }
      >
        <header>
          <div>
            <p className="eyebrow">
              SESSION ACTIVITY
            </p>

            <h2>
              Recent downloads
            </h2>
          </div>

          <span>
            Browser session only
          </span>
        </header>


        {history.length === 0 ? (
          <div
            className={
              styles.historyEmpty
            }
          >
            <Clock3
              size={25}
            />

            <span>
              Downloaded PDFs will
              appear here during this
              browser session.
            </span>
          </div>
        ) : (
          <div
            className={
              styles.historyList
            }
          >
            {history.map(
              (item) => (
                <div
                  key={
                    item.id
                  }
                >
                  <div
                    className={
                      styles.historyIcon
                    }
                  >
                    {item.kind
                      === "sales_invoice"
                      ? (
                        <FileText
                          size={16}
                        />
                      )
                      : (
                        <ReceiptText
                          size={16}
                        />
                      )
                    }
                  </div>

                  <div
                    className={
                      styles.historyMain
                    }
                  >
                    <strong>
                      {
                        item.filename
                      }
                    </strong>

                    <span>
                      {item.kind
                        === "sales_invoice"
                        ? "Invoice"
                        : "Payment"
                      }
                      {" ID #"}
                      {
                        item
                          .referenceId
                      }
                    </span>
                  </div>

                  <time>
                    {localTime(
                      item.downloadedAt,
                    )}
                  </time>
                </div>
              ),
            )}
          </div>
        )}
      </section>


      <section
        className={
          styles.notice
        }
      >
        <ShieldCheck
          size={17}
        />

        <div>
          <strong>
            Backend-contract aligned
          </strong>

          <p>
            This document center uses
            only the currently exposed
            Sales Invoice PDF and
            Payment Receipt PDF
            endpoints. Quotation and
            Job Card builders are not
            exposed by the current
            public document API and are
            therefore not invented in
            Phase 1.
          </p>
        </div>
      </section>
    </AppShell>
  );
}
