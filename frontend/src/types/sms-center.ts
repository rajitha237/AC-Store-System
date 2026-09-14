export type SmsNotificationSummary = {
  total: number;
  sent: number;
  pending: number;
  processing: number;
  failed: number;
  cancelled: number;
  today_sent: number;
};


export type SmsNotification = {
  id: number;

  recipient_type: string;
  recipient_name: string | null;
  recipient_phone: string;

  event_type: string;

  job_card_id: number | null;
  job_number: string | null;

  customer_id: number | null;
  customer_number: string | null;

  message: string;
  status: string;

  attempt_count: number;

  provider_message_id:
    string | null;

  last_error:
    string | null;

  scheduled_for:
    string | null;

  sent_at:
    string | null;

  created_at:
    string;
};


export type SmsNotificationListResponse = {
  items: SmsNotification[];

  total: number;
  page: number;
  page_size: number;
  total_pages: number;

  summary:
    SmsNotificationSummary;
};


export type SmsNotificationListParams = {
  page?: number;
  pageSize?: number;

  search?: string;

  status?: string;
  recipientType?: string;
  eventType?: string;

  dateFrom?: string;
  dateTo?: string;
};
