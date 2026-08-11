export type AuditJsonValue =
  | null
  | boolean
  | number
  | string
  | AuditJsonValue[]
  | {
      [
        key: string
      ]:
        AuditJsonValue;
    };


export type AuditLogResponse = {
  id:
    number;

  user_id:
    number | null;

  username:
    string | null;

  user_full_name:
    string | null;

  action:
    string;

  module:
    string;

  entity_type:
    string;

  entity_id:
    number | null;

  entity_reference:
    string | null;

  description:
    string;

  before_data?:
    unknown;

  after_data?:
    unknown;

  metadata?:
    unknown;

  ip_address:
    string | null;

  created_at:
    string;
};


export type AuditLogListResponse = {
  items:
    AuditLogResponse[];

  total:
    number;

  page:
    number;

  page_size:
    number;

  total_pages:
    number;
};


export type AuditLogListParams = {
  page?:
    number;

  pageSize?:
    number;

  search?:
    string;

  module?:
    string;

  action?:
    string;

  entityType?:
    string;

  entityId?:
    number;

  userId?:
    number;

  dateFrom?:
    string;

  dateTo?:
    string;
};
