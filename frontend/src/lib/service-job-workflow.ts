import type {
  ServiceJobStatus,
} from "@/types/service-jobs";


export const
VALID_SERVICE_STATUS_TRANSITIONS:
Record<
  ServiceJobStatus,
  readonly ServiceJobStatus[]
> = {
  received: [
    "inspection",
    "cancelled",
  ],

  inspection: [
    "waiting_approval",
    "approved",
    "repairing",
    "cancelled",
  ],

  waiting_approval: [
    "approved",
    "cancelled",
  ],

  approved: [
    "repairing",
    "cancelled",
  ],

  repairing: [
    "testing",
    "cancelled",
  ],

  testing: [
    "repairing",
    "ready",
    "cancelled",
  ],

  ready: [
    "delivered",
    "repairing",
    "cancelled",
  ],

  delivered: [],

  cancelled: [],
};


const LABOUR_ALLOWED:
ReadonlySet<ServiceJobStatus> =
  new Set([
    "inspection",
    "approved",
    "repairing",
    "testing",
  ]);


const PARTS_ALLOWED:
ReadonlySet<ServiceJobStatus> =
  new Set([
    "approved",
    "repairing",
    "testing",
  ]);


export function
getValidServiceNextStatuses(
  status:
    ServiceJobStatus,
): readonly ServiceJobStatus[] {
  return (
    VALID_SERVICE_STATUS_TRANSITIONS[
      status
    ] ?? []
  );
}


export function
canChangeServiceStatus(
  currentStatus:
    ServiceJobStatus,

  nextStatus:
    ServiceJobStatus,
): boolean {
  return (
    getValidServiceNextStatuses(
      currentStatus,
    ).includes(
      nextStatus,
    )
  );
}


export function
canEditServiceJob(
  status:
    ServiceJobStatus,
): boolean {
  return (
    status !== "delivered"
    && status !== "cancelled"
  );
}


export function
canAddServiceLabour(
  status:
    ServiceJobStatus,
): boolean {
  return (
    LABOUR_ALLOWED
    .has(status)
  );
}


export function
canAddServicePart(
  status:
    ServiceJobStatus,
): boolean {
  return (
    PARTS_ALLOWED
    .has(status)
  );
}


export function
canManageServiceApproval(
  status:
    ServiceJobStatus,
): boolean {
  return (
    status
    === "waiting_approval"
  );
}


export function
canCreateServiceInvoice(
  status:
    ServiceJobStatus,

  relatedInvoiceId:
    number | null,
): boolean {
  return (
    status === "ready"
    && !relatedInvoiceId
  );
}


export function
requiresTestingResult(
  nextStatus:
    ServiceJobStatus,
): boolean {
  return (
    nextStatus === "ready"
  );
}


export function
serviceWorkflowMessage(
  status:
    ServiceJobStatus,
): string {
  switch (status) {
    case "received":
      return (
        "Start inspection before "
        + "diagnosis or repair work."
      );

    case "inspection":
      return (
        "Inspect the item, record "
        + "diagnosis and request "
        + "approval when required."
      );

    case "waiting_approval":
      return (
        "Customer approval is pending. "
        + "Use the Approval action "
        + "before repair work."
      );

    case "approved":
      return (
        "Approval is complete. "
        + "Repair work and stock parts "
        + "can now be recorded."
      );

    case "repairing":
      return (
        "Record work performed, labour "
        + "and parts, then move the job "
        + "to testing."
      );

    case "testing":
      return (
        "A testing result is required "
        + "before the job can be marked "
        + "Ready."
      );

    case "ready":
      return (
        "The job is ready for customer "
        + "collection. Create the service "
        + "invoice before delivery when "
        + "billing is required."
      );

    case "delivered":
      return (
        "This job is delivered and "
        + "locked from further editing."
      );

    case "cancelled":
      return (
        "This job is cancelled and "
        + "locked from further workflow "
        + "actions."
      );
  }
}
