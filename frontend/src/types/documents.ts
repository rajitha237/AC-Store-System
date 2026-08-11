export type DocumentKind =
  | "sales_invoice"
  | "payment_receipt";


export type DocumentDefinition = {
  kind:
    DocumentKind;

  title:
    string;

  shortTitle:
    string;

  description:
    string;

  idLabel:
    string;

  idPlaceholder:
    string;

  permission:
    string;
};


export type DownloadedDocument = {
  blob:
    Blob;

  filename:
    string;
};


export type DocumentDownloadHistoryItem = {
  id:
    string;

  kind:
    DocumentKind;

  referenceId:
    number;

  filename:
    string;

  downloadedAt:
    string;
};
