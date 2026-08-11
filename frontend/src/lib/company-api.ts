import {
  api,
} from "@/lib/api";

import type {
  BranchRecord,
  BranchUpdatePayload,
  CompanyRecord,
  CompanyUpdatePayload,
} from "@/types/company";


export async function
getCompany():
Promise<CompanyRecord> {
  const response =
    await api.get<
      CompanyRecord
    >(
      "/company",
    );

  return response.data;
}


export async function
updateCompany(
  payload:
    CompanyUpdatePayload,
): Promise<CompanyRecord> {
  const response =
    await api.patch<
      CompanyRecord
    >(
      "/company",
      payload,
    );

  return response.data;
}


export async function
getBranches():
Promise<BranchRecord[]> {
  const response =
    await api.get<
      BranchRecord[]
    >(
      "/company/branches",
    );

  return response.data;
}


export async function
updateBranch(
  branchId:
    string | number,

  payload:
    BranchUpdatePayload,
): Promise<BranchRecord> {
  const response =
    await api.patch<
      BranchRecord
    >(
      `/company/branches/${branchId}`,
      payload,
    );

  return response.data;
}
