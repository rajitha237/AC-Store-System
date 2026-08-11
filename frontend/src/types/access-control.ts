export type AccessControlRecord =
  Record<
    string,
    unknown
  >;


export type AccessControlCollection =
  AccessControlRecord[];


export type AccessControlTab =
  | "roles"
  | "permissions";
