"use client";

import axios from "axios";

import {
  Building2,
  CircleAlert,
  Eye,
  Landmark,
  Loader2,
  MapPin,
  Pencil,
  RefreshCw,
  Save,
  Store,
  X,
} from "lucide-react";

import {
  FormEvent,
  useCallback,
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
  getBranches,
  getCompany,
  updateBranch,
  updateCompany,
} from "@/lib/company-api";

import type {
  UserResponse,
} from "@/types/auth";

import type {
  BranchRecord,
  CompanyRecord,
} from "@/types/company";

import styles from "./company.module.css";


function text(
  value:
    unknown,
): string {
  if (
    value === null
    || value === undefined
  ) {
    return "";
  }

  if (
    typeof value
    === "string"
    || typeof value
      === "number"
    || typeof value
      === "boolean"
  ) {
    return String(value);
  }

  return "";
}


function pretty(
  value:
    string,
): string {
  return value
    .replace(
      /_/g,
      " ",
    )
    .replace(
      /\b\w/g,
      (letter) =>
        letter.toUpperCase(),
    );
}


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
      "Unable to complete "
      + "company operation."
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
      + "have permission for "
      + "company settings."
    );
  }

  return (
    "Unable to complete "
    + "company operation."
  );
}


function recordId(
  record:
    BranchRecord,
): string {
  return text(
    record.id
    ?? record.branch_id
    ?? record.code
    ?? "",
  );
}


function displayName(
  record:
    CompanyRecord
    | BranchRecord,
): string {
  return text(
    record.name
    ?? record.company_name
    ?? record.branch_name
    ?? record.display_name
    ?? record.code
    ?? "Unnamed",
  );
}


function editableEntries(
  record:
    CompanyRecord
    | BranchRecord,
): [
  string,
  unknown,
][] {
  const ignored =
    new Set([
      "id",
      "company_id",
      "branch_id",
      "created_at",
      "updated_at",
      "created_by_id",
      "updated_by_id",
    ]);

  return Object
    .entries(record)
    .filter(
      ([key, value]) =>
        !ignored.has(key)
        && (
          value === null
          || typeof value
            === "string"
          || typeof value
            === "number"
          || typeof value
            === "boolean"
        ),
    );
}


export default function
CompanyPage() {
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
    company,
    setCompany,
  ] =
    useState<
      CompanyRecord | null
    >(
      null,
    );

  const [
    branches,
    setBranches,
  ] =
    useState<
      BranchRecord[]
    >(
      [],
    );

  const [
    loading,
    setLoading,
  ] =
    useState(true);

  const [
    refreshing,
    setRefreshing,
  ] =
    useState(false);

  const [
    error,
    setError,
  ] =
    useState("");


  const [
    editorType,
    setEditorType,
  ] =
    useState<
      "company"
      | "branch"
      | null
    >(
      null,
    );

  const [
    editingRecord,
    setEditingRecord,
  ] =
    useState<
      CompanyRecord
      | BranchRecord
      | null
    >(
      null,
    );

  const [
    form,
    setForm,
  ] =
    useState<
      Record<
        string,
        string | boolean
      >
    >(
      {},
    );

  const [
    saving,
    setSaving,
  ] =
    useState(false);

  const [
    formError,
    setFormError,
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


  const loadData =
    useCallback(
      async (
        refresh = false,
      ) => {
        if (refresh) {
          setRefreshing(
            true,
          );
        } else {
          setLoading(
            true,
          );
        }

        setError("");

        try {
          const [
            companyResult,
            branchResult,
          ] =
            await Promise.all([
              getCompany(),
              getBranches(),
            ]);

          setCompany(
            companyResult,
          );

          setBranches(
            branchResult,
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
          setLoading(
            false,
          );

          setRefreshing(
            false,
          );
        }
      },
      [],
    );


  useEffect(() => {
    if (authLoading) {
      return;
    }

    const timer =
      window.setTimeout(
        () => {
          void loadData();
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
    loadData,
  ]);


  const companyFields =
    useMemo(
      () =>
        company
          ? editableEntries(
              company,
            )
          : [],
      [company],
    );


  function openEditor(
    type:
      "company"
      | "branch",

    record:
      CompanyRecord
      | BranchRecord,
  ) {
    const nextForm:
      Record<
        string,
        string | boolean
      > = {};

    for (
      const [
        key,
        value,
      ]
      of editableEntries(
        record,
      )
    ) {
      if (
        typeof value
        === "boolean"
      ) {
        nextForm[key] =
          value;
      } else {
        nextForm[key] =
          text(value);
      }
    }

    setEditorType(
      type,
    );

    setEditingRecord(
      record,
    );

    setForm(
      nextForm,
    );

    setFormError(
      "",
    );
  }


  function closeEditor() {
    if (saving) {
      return;
    }

    setEditorType(
      null,
    );

    setEditingRecord(
      null,
    );

    setForm(
      {},
    );

    setFormError(
      "",
    );
  }


  async function submitEditor(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (
      !editorType
      || !editingRecord
    ) {
      return;
    }

    setSaving(
      true,
    );

    setFormError(
      "",
    );

    try {
      const original =
        editingRecord;

      const payload:
        Record<
          string,
          unknown
        > = {};

      for (
        const [
          key,
          value,
        ]
        of Object.entries(
          form,
        )
      ) {
        const originalValue =
          original[key];

        if (
          typeof originalValue
          === "number"
        ) {
          const numeric =
            Number(value);

          payload[key] =
            Number.isFinite(
              numeric,
            )
              ? numeric
              : originalValue;
        } else {
          payload[key] =
            value === ""
              ? null
              : value;
        }
      }

      if (
        editorType
        === "company"
      ) {
        const result =
          await updateCompany(
            payload,
          );

        setCompany(
          result,
        );
      } else {
        const branchId =
          recordId(
            editingRecord,
          );

        if (!branchId) {
          throw new Error(
            "Branch identifier "
            + "was not returned "
            + "by the backend."
          );
        }

        const result =
          await updateBranch(
            branchId,
            payload,
          );

        setBranches(
          (current) =>
            current.map(
              (branch) =>
                recordId(branch)
                === branchId
                  ? result
                  : branch,
            ),
        );
      }

      closeEditor();

      await loadData(
        true,
      );
    } catch (
      requestError
    ) {
      setFormError(
        errorMessage(
          requestError,
        ),
      );
    } finally {
      setSaving(
        false,
      );
    }
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
            ORGANIZATION
          </p>

          <h1>
            Company Settings
          </h1>

          <p>
            Review and maintain the
            business profile and branch
            information used across
            sales, inventory, documents
            and service operations.
          </p>
        </div>

        <button
          type="button"
          className={
            styles.secondaryButton
          }
          disabled={
            refreshing
          }
          onClick={() =>
            void loadData(
              true,
            )
          }
        >
          <RefreshCw
            size={16}
            className={
              refreshing
                ? styles.spin
                : undefined
            }
          />

          Refresh
        </button>
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


      {loading ? (
        <section
          className={
            styles.loadingCard
          }
        >
          <Loader2
            size={23}
            className={
              styles.spin
            }
          />

          Loading company settings...
        </section>
      ) : (
        <>
          <section
            className={
              styles.companyCard
            }
          >
            <header>
              <div
                className={
                  styles.companyIcon
                }
              >
                <Building2
                  size={22}
                />
              </div>

              <div>
                <p className="eyebrow">
                  COMPANY PROFILE
                </p>

                <h2>
                  {company
                    ? displayName(
                        company,
                      )
                    : "Company"
                  }
                </h2>
              </div>

              {company && (
                <button
                  type="button"
                  className={
                    styles.primaryButton
                  }
                  onClick={() =>
                    openEditor(
                      "company",
                      company,
                    )
                  }
                >
                  <Pencil
                    size={15}
                  />

                  Edit company
                </button>
              )}
            </header>


            {company ? (
              <div
                className={
                  styles.fieldGrid
                }
              >
                {companyFields.map(
                  ([
                    key,
                    value,
                  ]) => (
                    <div
                      key={key}
                    >
                      <span>
                        {pretty(key)}
                      </span>

                      <strong>
                        {text(value)
                          || "—"
                        }
                      </strong>
                    </div>
                  ),
                )}
              </div>
            ) : (
              <div
                className={
                  styles.emptyState
                }
              >
                No company record returned.
              </div>
            )}
          </section>


          <section
            className={
              styles.branchSection
            }
          >
            <header
              className={
                styles.sectionHeader
              }
            >
              <div>
                <p className="eyebrow">
                  LOCATIONS
                </p>

                <h2>
                  Branches
                </h2>
              </div>

              <span>
                {branches.length}
                {" branches"}
              </span>
            </header>


            {branches.length
              === 0 ? (
              <div
                className={
                  styles.emptyState
                }
              >
                <Store
                  size={30}
                />

                No branches returned.
              </div>
            ) : (
              <div
                className={
                  styles.branchGrid
                }
              >
                {branches.map(
                  (
                    branch,
                    index,
                  ) => (
                    <article
                      key={
                        recordId(branch)
                        || `branch-${index}`
                      }
                      className={
                        styles.branchCard
                      }
                    >
                      <header>
                        <div
                          className={
                            styles.branchIcon
                          }
                        >
                          <Store
                            size={18}
                          />
                        </div>

                        <div>
                          <h3>
                            {displayName(
                              branch,
                            )}
                          </h3>

                          <small>
                            {text(
                              branch.code
                              ?? branch.branch_code
                              ?? branch.id,
                            )}
                          </small>
                        </div>
                      </header>


                      <div
                        className={
                          styles.branchFields
                        }
                      >
                        {editableEntries(
                          branch,
                        )
                          .slice(
                            0,
                            8,
                          )
                          .map(
                            ([
                              key,
                              value,
                            ]) => (
                              <div
                                key={key}
                              >
                                <span>
                                  {pretty(
                                    key,
                                  )}
                                </span>

                                <strong>
                                  {text(
                                    value,
                                  )
                                    || "—"
                                  }
                                </strong>
                              </div>
                            ),
                          )}
                      </div>


                      <button
                        type="button"
                        className={
                          styles.branchButton
                        }
                        onClick={() =>
                          openEditor(
                            "branch",
                            branch,
                          )
                        }
                      >
                        <Pencil
                          size={14}
                        />

                        Edit branch
                      </button>
                    </article>
                  ),
                )}
              </div>
            )}
          </section>
        </>
      )}


      {editorType
        && editingRecord && (
        <div
          className={
            styles.backdrop
          }
        >
          <form
            className={
              styles.modal
            }
            onSubmit={
              submitEditor
            }
          >
            <header
              className={
                styles.modalHeader
              }
            >
              <div>
                <p className="eyebrow">
                  {editorType
                    === "company"
                    ? "EDIT COMPANY"
                    : "EDIT BRANCH"
                  }
                </p>

                <h2>
                  {displayName(
                    editingRecord,
                  )}
                </h2>
              </div>

              <button
                type="button"
                className={
                  styles.iconButton
                }
                disabled={
                  saving
                }
                onClick={
                  closeEditor
                }
              >
                <X size={18} />
              </button>
            </header>


            <div
              className={
                styles.modalBody
              }
            >
              <div
                className={
                  styles.formGrid
                }
              >
                {Object.entries(
                  form,
                ).map(
                  ([
                    key,
                    value,
                  ]) => (
                    <label
                      key={key}
                    >
                      {pretty(key)}

                      {typeof value
                        === "boolean" ? (
                        <input
                          type="checkbox"
                          checked={
                            value
                          }
                          onChange={
                            (event) =>
                              setForm(
                                (
                                  current,
                                ) => ({
                                  ...current,

                                  [key]:
                                    event
                                      .target
                                      .checked,
                                }),
                              )
                          }
                        />
                      ) : (
                        <input
                          value={
                            value
                          }
                          onChange={
                            (event) =>
                              setForm(
                                (
                                  current,
                                ) => ({
                                  ...current,

                                  [key]:
                                    event
                                      .target
                                      .value,
                                }),
                              )
                          }
                        />
                      )}
                    </label>
                  ),
                )}
              </div>


              {formError && (
                <div
                  className={
                    styles.errorBanner
                  }
                >
                  <CircleAlert
                    size={17}
                  />

                  {formError}
                </div>
              )}
            </div>


            <footer
              className={
                styles.modalFooter
              }
            >
              <button
                type="button"
                className={
                  styles.secondaryButton
                }
                disabled={
                  saving
                }
                onClick={
                  closeEditor
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
                  saving
                }
              >
                {saving ? (
                  <Loader2
                    size={16}
                    className={
                      styles.spin
                    }
                  />
                ) : (
                  <Save size={16} />
                )}

                {saving
                  ? "Saving..."
                  : "Save changes"
                }
              </button>
            </footer>
          </form>
        </div>
      )}
    </AppShell>
  );
}
