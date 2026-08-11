import {
  api,
} from "@/lib/api";

import type {
  AccessControlCollection,
  AccessControlRecord,
} from "@/types/access-control";


function isRecord(
  value:
    unknown,
): value is
AccessControlRecord {
  return (
    typeof value
      === "object"
    && value !== null
    && !Array.isArray(value)
  );
}


function normalizeCollection(
  value:
    unknown,
): AccessControlCollection {
  if (Array.isArray(value)) {
    return value.filter(
      isRecord,
    );
  }

  if (!isRecord(value)) {
    return [];
  }

  const candidates = [
    value.items,
    value.roles,
    value.permissions,
    value.results,
    value.data,
  ];

  for (
    const candidate
    of candidates
  ) {
    if (
      Array.isArray(
        candidate,
      )
    ) {
      return candidate.filter(
        isRecord,
      );
    }
  }

  return [];
}


export async function
getPermissions():
Promise<
  AccessControlCollection
> {
  const response =
    await api.get<unknown>(
      "/access-control/permissions",
    );

  return normalizeCollection(
    response.data,
  );
}


export async function
getRoles():
Promise<
  AccessControlCollection
> {
  const response =
    await api.get<unknown>(
      "/access-control/roles",
    );

  return normalizeCollection(
    response.data,
  );
}


export async function
getRole(
  roleId:
    string | number,
): Promise<
  AccessControlRecord
> {
  const response =
    await api.get<unknown>(
      `/access-control/roles/${roleId}`,
    );

  if (
    !isRecord(
      response.data,
    )
  ) {
    throw new Error(
      "Role detail response "
      + "has an invalid format.",
    );
  }

  return response.data;
}
