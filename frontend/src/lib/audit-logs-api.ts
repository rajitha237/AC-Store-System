import {
  api,
} from "@/lib/api";

import type {
  AuditLogListParams,
  AuditLogListResponse,
} from "@/types/audit-logs";


export async function getAuditLogs(
  params:
    AuditLogListParams = {},
): Promise<
  AuditLogListResponse
> {
  const response =
    await api.get<
      AuditLogListResponse
    >(
      "/audit-logs",
      {
        params: {
          page:
            params.page
            ?? 1,

          page_size:
            params.pageSize
            ?? 20,

          search:
            params.search
            || undefined,

          module:
            params.module
            || undefined,

          action:
            params.action
            || undefined,

          entity_type:
            params.entityType
            || undefined,

          entity_id:
            params.entityId,

          user_id:
            params.userId,

          date_from:
            params.dateFrom
            || undefined,

          date_to:
            params.dateTo
            || undefined,
        },
      },
    );

  return response.data;
}
