export interface Point2D {
  x: number;
  y: number;
}

export interface BoundingBox {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
  width?: number;
  height?: number;
}

export interface ImageMetadata {
  width: number;
  height: number;
  file_size_bytes: number;
  image_format: string;
}

export interface ImageQualityMetrics {
  blur_laplacian_variance: number;
  is_blurry: boolean;
  brightness_mean: number;
  contrast_std: number;
  clipping_low_pct: number;
  clipping_high_pct: number;
  is_under_exposed: boolean;
  is_over_exposed: boolean;
  quality_warnings: string[];
}

export interface FusedDeclaration {
  declaration_id: string;
  declaration_type: string;
  display_title: string;
  raw_text: string;
  normalized_data?: any;
  combined_confidence: number;
  bounding_box: BoundingBox;
  polygon: Point2D[];
  provenance_notes: string[];
}

export interface RuleProvenance {
  rule_id: string;
  statute_name: string;
  rule_reference: string;
  title: string;
  summary: string;
}

export interface FieldComplianceAssessment {
  assessment_id: string;
  rule: RuleProvenance;
  status: "compliant" | "non_compliant" | "flagged_for_review" | "not_applicable";
  evidence_declaration_id?: string;
  findings: string[];
  cautions_and_recommendations: string[];
  cautious_disclaimer: string;
}

export interface OverallComplianceReport {
  overall_status: "compliant" | "non_compliant" | "flagged_for_review" | "not_applicable";
  total_rules_evaluated: number;
  compliant_count: number;
  non_compliant_count: number;
  flagged_count: number;
  assessments: FieldComplianceAssessment[];
  legal_disclaimer: string;
  evaluation_time_ms: number;
}

export interface InspectionData {
  id: string;
  filename: string;
  category?: string;
  status: string;
  metadata: ImageMetadata;
  quality: ImageQualityMetrics;
  timing_ms: {
    total_pipeline_ms: number;
    nlp_extraction_ms: number;
    fusion_ms: number;
    compliance_ms: number;
  };
  ocr_summary: {
    total_blocks: number;
    high_confidence_blocks: number;
    average_confidence: number;
  };
  fused_declarations: FusedDeclaration[];
  compliance_report: OverallComplianceReport;
  image_url: string;
  annotated_url: string;
}

export interface SampleImage {
  filename: string;
  relative_path: string;
  category: string;
  size_bytes: number;
}
