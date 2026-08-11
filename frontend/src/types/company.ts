export type CompanyRecord =
  Record<
    string,
    unknown
  >;


export type BranchRecord =
  Record<
    string,
    unknown
  >;


export type CompanyUpdatePayload =
  Record<
    string,
    unknown
  >;


export type BranchUpdatePayload =
  Record<
    string,
    unknown
  >;


export type CompanyFieldDefinition = {
  name:
    string;

  type:
    string | null;

  format:
    string | null;

  required:
    boolean;

  editable:
    boolean;
};
