import {
  api,
} from "@/lib/api";

import type {
  SmsNotificationListParams,
  SmsNotificationListResponse,
} from "@/types/sms-center";


export async function getSmsNotifications(
  params:
    SmsNotificationListParams = {},
): Promise<
  SmsNotificationListResponse
> {
  const response =
    await api.get<
      SmsNotificationListResponse
    >(
      "/sms-center",
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

          status:
            params.status
            || undefined,

          recipient_type:
            params.recipientType
            || undefined,

          event_type:
            params.eventType
            || undefined,

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
