export type FinancialReportPeriod = {
  date_from: string;
  date_to: string;
};

export type ProfitAndLossSummary = {
  gross_sales: string;
  sales_credits: string;
  net_revenue: string;
  cost_of_goods_sold: string;
  gross_profit: string;
  operating_expenses: string;
  net_profit: string;
};

export type CashFlowSummary = {
  customer_collections: string;
  manual_cash_in: string;
  total_cash_in: string;
  supplier_payments: string;
  manual_cash_out: string;
  total_cash_out: string;
  net_cash_flow: string;
};

export type PurchasingSummary = {
  supplier_invoices: string;
  supplier_payments: string;
};

export type ReceivablesSummary = {
  customer_receivables: string;
  supplier_payables: string;
};

export type FinancialReportsSummary = {
  period: FinancialReportPeriod;
  profit_and_loss: ProfitAndLossSummary;
  cash_flow: CashFlowSummary;
  purchasing: PurchasingSummary;
  receivables: ReceivablesSummary;
};
