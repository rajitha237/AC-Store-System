"use client";

import axios from "axios";

import {
  BadgeCheck,
  ChevronRight,
  CircleAlert,
  Eye,
  KeyRound,
  Loader2,
  LockKeyhole,
  RefreshCw,
  Search,
  ShieldCheck,
  UserCog,
  UsersRound,
  X,
} from "lucide-react";

import {
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
  getPermissions,
  getRole,
  getRoles,
} from "@/lib/access-control-api";

import type {
  UserResponse,
} from "@/types/auth";

import type {
  AccessControlRecord,
  AccessControlTab,
} from "@/types/access-control";

import styles from "./access-control.module.css";


function firstValue(
  record:
    AccessControlRecord,

  keys:
    string[],
): unknown {
  for (
    const key
    of keys
  ) {
    const value =
      record[key];

    if (
      value !== null
      && value !== undefined
      && value !== ""
    ) {
      return value;
    }
  }

  return undefined;
}


function textValue(
  record:
    AccessControlRecord,

  keys:
    string[],

  fallback =
    "—",
): string {
  const value =
    firstValue(
      record,
      keys,
    );

  if (
    value === null
    || value === undefined
  ) {
    return fallback;
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

  return fallback;
}


function idValue(
  record:
    AccessControlRecord,
): string {
  return textValue(
    record,
    [
      "id",
      "role_id",
      "permission_id",
      "code",
      "name",
    ],
    "",
  );
}


function displayName(
  record:
    AccessControlRecord,
): string {
  return textValue(
    record,
    [
      "display_name",
      "name",
      "role_name",
      "permission_name",
      "title",
      "code",
    ],
    "Unnamed record",
  );
}


function codeValue(
  record:
    AccessControlRecord,
): string {
  return textValue(
    record,
    [
      "code",
      "slug",
      "key",
      "name",
    ],
    "—",
  );
}


function descriptionValue(
  record:
    AccessControlRecord,
): string {
  return textValue(
    record,
    [
      "description",
      "notes",
      "summary",
    ],
    "No description provided.",
  );
}


function boolValue(
  record:
    AccessControlRecord,

  keys:
    string[],
): boolean | null {
  const value =
    firstValue(
      record,
      keys,
    );

  if (
    typeof value
    === "boolean"
  ) {
    return value;
  }

  if (
    value === 1
    || value === "1"
    || value === "true"
  ) {
    return true;
  }

  if (
    value === 0
    || value === "0"
    || value === "false"
  ) {
    return false;
  }

  return null;
}


function recordArray(
  record:
    AccessControlRecord,

  keys:
    string[],
): AccessControlRecord[] {
  for (
    const key
    of keys
  ) {
    const value =
      record[key];

    if (
      Array.isArray(
        value,
      )
    ) {
      return value.filter(
        (
          item,
        ): item is AccessControlRecord =>
          typeof item
            === "object"
          && item !== null
          && !Array.isArray(item),
      );
    }
  }

  return [];
}


function stringArray(
  record:
    AccessControlRecord,

  keys:
    string[],
): string[] {
  for (
    const key
    of keys
  ) {
    const value =
      record[key];

    if (
      Array.isArray(
        value,
      )
    ) {
      return value
        .map(
          (item) => {
            if (
              typeof item
              === "string"
              || typeof item
                === "number"
            ) {
              return String(item);
            }

            if (
              typeof item
                === "object"
              && item !== null
              && !Array.isArray(
                item,
              )
            ) {
              return codeValue(
                item as
                  AccessControlRecord,
              );
            }

            return "";
          },
        )
        .filter(Boolean);
    }
  }

  return [];
}


function permissionCodes(
  record:
    AccessControlRecord,
): string[] {
  const nested =
    recordArray(
      record,
      [
        "permissions",
        "role_permissions",
        "permission_items",
      ],
    );

  if (
    nested.length > 0
  ) {
    return nested
      .map(
        codeValue,
      )
      .filter(
        (value) =>
          value !== "—",
      );
  }

  return stringArray(
    record,
    [
      "permissions",
      "permission_codes",
      "role_permissions",
    ],
  );
}


function moduleFromPermission(
  record:
    AccessControlRecord,
): string {
  const explicit =
    textValue(
      record,
      [
        "module",
        "module_name",
        "group",
        "category",
        "resource",
      ],
      "",
    );

  if (explicit) {
    return explicit;
  }

  const code =
    codeValue(
      record,
    );

  if (
    code !== "—"
    && code.includes(".")
  ) {
    return (
      code.split(".")[0]
      || "General"
    );
  }

  return "General";
}


function pretty(
  value:
    string,
): string {
  return value
    .replace(
      /[._-]+/g,
      " ",
    )
    .replace(
      /\b\w/g,
      (character) =>
        character
          .toUpperCase(),
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
      "Unable to load "
      + "access-control data."
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
      "Your account does not have "
      + "permission to view "
      + "access control."
    );
  }

  return (
    "Unable to load "
    + "access-control data."
  );
}


function jsonText(
  value:
    unknown,
): string {
  try {
    return JSON.stringify(
      value,
      null,
      2,
    );
  } catch {
    return String(value);
  }
}


export default function
AccessControlPage() {
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
    tab,
    setTab,
  ] =
    useState<
      AccessControlTab
    >(
      "roles",
    );

  const [
    roles,
    setRoles,
  ] =
    useState<
      AccessControlRecord[]
    >(
      [],
    );

  const [
    permissions,
    setPermissions,
  ] =
    useState<
      AccessControlRecord[]
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
    search,
    setSearch,
  ] =
    useState("");

  const [
    moduleFilter,
    setModuleFilter,
  ] =
    useState("all");


  const [
    selectedRole,
    setSelectedRole,
  ] =
    useState<
      AccessControlRecord | null
    >(
      null,
    );

  const [
    detailOpen,
    setDetailOpen,
  ] =
    useState(false);

  const [
    detailLoading,
    setDetailLoading,
  ] =
    useState(false);


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
            roleData,
            permissionData,
          ] =
            await Promise.all([
              getRoles(),
              getPermissions(),
            ]);

          setRoles(
            roleData,
          );

          setPermissions(
            permissionData,
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


  const permissionModules =
    useMemo(
      () =>
        Array.from(
          new Set(
            permissions.map(
              moduleFromPermission,
            ),
          ),
        ).sort(
          (
            left,
            right,
          ) =>
            left.localeCompare(
              right,
            ),
        ),
      [permissions],
    );


  const filteredRoles =
    useMemo(
      () => {
        const query =
          search
            .trim()
            .toLowerCase();

        if (!query) {
          return roles;
        }

        return roles.filter(
          (role) =>
            [
              displayName(role),
              codeValue(role),
              descriptionValue(
                role,
              ),
              ...permissionCodes(
                role,
              ),
            ]
              .join(" ")
              .toLowerCase()
              .includes(
                query,
              ),
        );
      },
      [
        roles,
        search,
      ],
    );


  const filteredPermissions =
    useMemo(
      () => {
        const query =
          search
            .trim()
            .toLowerCase();

        return permissions.filter(
          (permission) => {
            const moduleName =
              moduleFromPermission(
                permission,
              );

            if (
              moduleFilter
                !== "all"
              && moduleName
                !== moduleFilter
            ) {
              return false;
            }

            if (!query) {
              return true;
            }

            return [
              displayName(
                permission,
              ),
              codeValue(
                permission,
              ),
              descriptionValue(
                permission,
              ),
              moduleName,
            ]
              .join(" ")
              .toLowerCase()
              .includes(
                query,
              );
          },
        );
      },
      [
        permissions,
        search,
        moduleFilter,
      ],
    );


  const rolePermissionTotal =
    useMemo(
      () =>
        roles.reduce(
          (
            total,
            role,
          ) =>
            total
            + permissionCodes(
                role,
              ).length,
          0,
        ),
      [roles],
    );


  async function
  openRole(
    role:
      AccessControlRecord,
  ) {
    setSelectedRole(
      role,
    );

    setDetailOpen(
      true,
    );

    setDetailLoading(
      true,
    );

    setError("");

    const roleId =
      idValue(
        role,
      );

    if (!roleId) {
      setDetailLoading(
        false,
      );

      return;
    }

    try {
      const detail =
        await getRole(
          roleId,
        );

      setSelectedRole(
        detail,
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
      setDetailLoading(
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
            ADMINISTRATION
          </p>

          <h1>
            Access Control
          </h1>

          <p>
            Inspect system roles,
            permissions and the
            permission assignments
            that protect AC Store
            operations.
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


      <section
        className={
          styles.summaryGrid
        }
      >
        <article>
          <UsersRound size={20} />

          <div>
            <span>
              Roles
            </span>

            <strong>
              {roles.length}
            </strong>
          </div>
        </article>

        <article>
          <KeyRound size={20} />

          <div>
            <span>
              Permissions
            </span>

            <strong>
              {permissions.length}
            </strong>
          </div>
        </article>

        <article>
          <ShieldCheck
            size={20}
          />

          <div>
            <span>
              Permission modules
            </span>

            <strong>
              {
                permissionModules
                  .length
              }
            </strong>
          </div>
        </article>

        <article>
          <BadgeCheck size={20} />

          <div>
            <span>
              Role assignments loaded
            </span>

            <strong>
              {rolePermissionTotal}
            </strong>
          </div>
        </article>
      </section>


      <section
        className={
          styles.controlCard
        }
      >
        <div
          className={
            styles.tabs
          }
        >
          <button
            type="button"
            className={
              tab === "roles"
                ? styles.activeTab
                : styles.tab
            }
            onClick={() =>
              setTab(
                "roles",
              )
            }
          >
            <UserCog size={15} />

            Roles
          </button>

          <button
            type="button"
            className={
              tab === "permissions"
                ? styles.activeTab
                : styles.tab
            }
            onClick={() =>
              setTab(
                "permissions",
              )
            }
          >
            <KeyRound size={15} />

            Permissions
          </button>
        </div>


        <div
          className={
            styles.filters
          }
        >
          <label
            className={
              styles.searchBox
            }
          >
            <Search size={16} />

            <input
              value={
                search
              }
              placeholder={
                tab === "roles"
                  ? "Search role, code or permission..."
                  : "Search permission, code or module..."
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

          {tab
            === "permissions" && (
            <select
              value={
                moduleFilter
              }
              onChange={
                (event) =>
                  setModuleFilter(
                    event
                      .target
                      .value,
                  )
              }
            >
              <option value="all">
                All modules
              </option>

              {permissionModules
                .map(
                  (moduleName) => (
                    <option
                      key={
                        moduleName
                      }
                      value={
                        moduleName
                      }
                    >
                      {pretty(
                        moduleName,
                      )}
                    </option>
                  ),
                )}
            </select>
          )}
        </div>
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


      <section
        className={
          styles.tableCard
        }
      >
        {loading ? (
          <div
            className={
              styles.emptyState
            }
          >
            <Loader2
              size={23}
              className={
                styles.spin
              }
            />

            Loading access control...
          </div>
        ) : tab === "roles" ? (
          filteredRoles.length
            === 0 ? (
            <div
              className={
                styles.emptyState
              }
            >
              <UsersRound
                size={31}
              />

              <strong>
                No roles found
              </strong>
            </div>
          ) : (
            <div
              className={
                styles.roleGrid
              }
            >
              {filteredRoles.map(
                (
                  role,
                  index,
                ) => {
                  const permissionsForRole =
                    permissionCodes(
                      role,
                    );

                  const system =
                    boolValue(
                      role,
                      [
                        "is_system",
                        "system_role",
                        "is_builtin",
                        "built_in",
                      ],
                    );

                  return (
                    <article
                      key={
                        idValue(role)
                        || `role-${index}`
                      }
                      className={
                        styles.roleCard
                      }
                    >
                      <header>
                        <div
                          className={
                            styles.roleIcon
                          }
                        >
                          <ShieldCheck
                            size={18}
                          />
                        </div>

                        <div>
                          <h2>
                            {displayName(
                              role,
                            )}
                          </h2>

                          <code>
                            {codeValue(
                              role,
                            )}
                          </code>
                        </div>
                      </header>

                      <p>
                        {descriptionValue(
                          role,
                        )}
                      </p>

                      <div
                        className={
                          styles.roleMeta
                        }
                      >
                        <span>
                          {
                            permissionsForRole
                              .length
                          }
                          {" permissions"}
                        </span>

                        {system
                          !== null && (
                          <span
                            className={
                              system
                                ? styles.systemBadge
                                : styles.customBadge
                            }
                          >
                            {system
                              ? "System role"
                              : "Custom role"
                            }
                          </span>
                        )}
                      </div>

                      <div
                        className={
                          styles.permissionPreview
                        }
                      >
                        {permissionsForRole
                          .slice(
                            0,
                            5,
                          )
                          .map(
                            (permission) => (
                              <span
                                key={
                                  permission
                                }
                              >
                                {
                                  permission
                                }
                              </span>
                            ),
                          )}

                        {permissionsForRole
                          .length > 5 && (
                          <span>
                            +
                            {
                              permissionsForRole
                                .length - 5
                            }
                            {" more"}
                          </span>
                        )}
                      </div>

                      <button
                        type="button"
                        className={
                          styles.viewButton
                        }
                        onClick={() =>
                          void openRole(
                            role,
                          )
                        }
                      >
                        <Eye size={15} />

                        View role

                        <ChevronRight
                          size={15}
                        />
                      </button>
                    </article>
                  );
                },
              )}
            </div>
          )
        ) : filteredPermissions
          .length === 0 ? (
          <div
            className={
              styles.emptyState
            }
          >
            <KeyRound
              size={31}
            />

            <strong>
              No permissions found
            </strong>
          </div>
        ) : (
          <div
            className={
              styles.tableWrap
            }
          >
            <table>
              <thead>
                <tr>
                  <th>
                    Permission
                  </th>

                  <th>
                    Code
                  </th>

                  <th>
                    Module
                  </th>

                  <th>
                    Description
                  </th>

                  <th>
                    Protection
                  </th>
                </tr>
              </thead>

              <tbody>
                {filteredPermissions
                  .map(
                    (
                      permission,
                      index,
                    ) => (
                      <tr
                        key={
                          idValue(
                            permission,
                          )
                          || `permission-${index}`
                        }
                      >
                        <td>
                          <strong>
                            {displayName(
                              permission,
                            )}
                          </strong>
                        </td>

                        <td>
                          <code>
                            {codeValue(
                              permission,
                            )}
                          </code>
                        </td>

                        <td>
                          <span
                            className={
                              styles.moduleBadge
                            }
                          >
                            {pretty(
                              moduleFromPermission(
                                permission,
                              ),
                            )}
                          </span>
                        </td>

                        <td
                          className={
                            styles.descriptionCell
                          }
                        >
                          {descriptionValue(
                            permission,
                          )}
                        </td>

                        <td>
                          <span
                            className={
                              styles.protectionBadge
                            }
                          >
                            <LockKeyhole
                              size={12}
                            />

                            Enforced
                          </span>
                        </td>
                      </tr>
                    ),
                  )}
              </tbody>
            </table>
          </div>
        )}
      </section>


      <section
        className={
          styles.readOnlyNotice
        }
      >
        <LockKeyhole
          size={17}
        />

        <div>
          <strong>
            Read-only access-control view
          </strong>

          <p>
            The current backend exposes
            role and permission inspection
            endpoints only. Phase 1 does
            not invent role-management
            write operations that are not
            present in the API contract.
          </p>
        </div>
      </section>


      {detailOpen
        && selectedRole && (
        <div
          className={
            styles.backdrop
          }
        >
          <aside
            className={
              styles.drawer
            }
          >
            <header
              className={
                styles.drawerHeader
              }
            >
              <div>
                <p className="eyebrow">
                  ROLE DETAILS
                </p>

                <h2>
                  {displayName(
                    selectedRole,
                  )}
                </h2>

                <code>
                  {codeValue(
                    selectedRole,
                  )}
                </code>
              </div>

              <button
                type="button"
                className={
                  styles.iconButton
                }
                onClick={() => {
                  setDetailOpen(
                    false,
                  );

                  setSelectedRole(
                    null,
                  );
                }}
              >
                <X size={18} />
              </button>
            </header>


            <div
              className={
                styles.drawerBody
              }
            >
              {detailLoading ? (
                <div
                  className={
                    styles.emptyState
                  }
                >
                  <Loader2
                    size={22}
                    className={
                      styles.spin
                    }
                  />

                  Loading role...
                </div>
              ) : (
                <>
                  <section
                    className={
                      styles.detailHero
                    }
                  >
                    <ShieldCheck
                      size={22}
                    />

                    <div>
                      <span>
                        Role description
                      </span>

                      <strong>
                        {descriptionValue(
                          selectedRole,
                        )}
                      </strong>
                    </div>
                  </section>


                  <section
                    className={
                      styles.detailSection
                    }
                  >
                    <div
                      className={
                        styles.sectionTitle
                      }
                    >
                      <h3>
                        Permissions
                      </h3>

                      <span>
                        {permissionCodes(
                          selectedRole,
                        ).length}
                        {" assigned"}
                      </span>
                    </div>

                    <div
                      className={
                        styles.permissionMatrix
                      }
                    >
                      {permissionCodes(
                        selectedRole,
                      ).length
                        === 0 ? (
                        <p
                          className={
                            styles.muted
                          }
                        >
                          No embedded permission
                          assignments were returned
                          for this role.
                        </p>
                      ) : (
                        permissionCodes(
                          selectedRole,
                        ).map(
                          (permission) => (
                            <div
                              key={
                                permission
                              }
                            >
                              <KeyRound
                                size={14}
                              />

                              <span>
                                {
                                  permission
                                }
                              </span>
                            </div>
                          ),
                        )
                      )}
                    </div>
                  </section>


                  <section
                    className={
                      styles.detailSection
                    }
                  >
                    <div
                      className={
                        styles.sectionTitle
                      }
                    >
                      <h3>
                        Raw backend record
                      </h3>

                      <span>
                        Diagnostic view
                      </span>
                    </div>

                    <pre
                      className={
                        styles.rawRecord
                      }
                    >
                      {jsonText(
                        selectedRole,
                      )}
                    </pre>
                  </section>
                </>
              )}
            </div>
          </aside>
        </div>
      )}
    </AppShell>
  );
}
