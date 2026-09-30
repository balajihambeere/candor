export type Reason = {
  rule_id: string;
  evaluated_value: number | boolean;
  threshold: number | boolean;
  comparator: string;
  passed: boolean;
};

export type Trace = {
  determinative_reasons: string[];
  verification_status: "verified" | "unresolved";
  counterfactual_log: Array<{
    rule_id: string;
    neutralized_other_reasons: string[];
    still_denied: boolean;
  }>;
};

export type Justification = {
  sentence: string;
  boundary_line: string;
  faithfulness_check_passed: boolean;
  plain_language_check_passed: boolean;
  status: "verified" | "failed_review";
};

export type Decision = {
  id: string;
  case_id: string;
  verdict: "approved" | "denied";
  reasons: Reason[];
  trace: Trace;
  justification: Justification;
  needs_review: boolean;
  created_at: string;
};

export type ReviewItem = {
  id: string;
  decision_id: string;
  reason: "trace_unresolved" | "justify_faithfulness_failed" | "justify_plain_language_failed";
  status: "pending" | "resolved";
  assigned_to: string | null;
  resolution_notes: string | null;
  resolved_at: string | null;
  created_at: string;
};

export type Disclosure = {
  id: string;
  decision_id: string;
  channel: "call" | "email" | "chat";
  disclosed_by: string;
  disclosed_at: string;
  delay_owned: boolean;
  sentence_sent: string;
  customer_response: string | null;
  held_up: boolean | null;
};
