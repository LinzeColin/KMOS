<!-- 本文件由 KMFA/tools/build_tools_index.py 生成。请勿手写——下次生成会覆盖。 -->

# KMFA/tools 导航索引

**先读这里，不要列目录。** 列 `KMFA/tools` 要 ≈16500 tokens，读这份 ≈500。

## 一、别看的那部分

- `KMFA/tools/` 里有 **683** 个 `v013_*` / `v014_*` / `check_v01*_*` 开头的文件，是**已完成阶段的冻结校验器**。
- `KMFA/tests/` 里有 **350** 个对应的 `test_v01*` 测试。
- 它们近 30 天零改动。**除非你在查某个具体阶段的历史结论，否则不要浏览它们**；
  要找就用精确文件名 grep，不要列目录、不要通配。
- 为什么不删：`KMFA/tests` 里的测试真的 `from KMFA.tools.check_v01... import`，
  移动会断 import，删除会连带断掉治理证据链。

## 二、日常要用的部分

### 顶层活跃脚本（168 个）

- `a0_authority_baseline_lock.py`
- `a0_file_register.py`
- `a0_golden_fixture.py`
- `a0_zero_delta_cloud.py`
- `access_security_policy.py`
- `amount_tools.py`
- `app_state_backup.py`
- `build_tools_index.py`
- `business_entity_model.py`
- `check_a0_authority_baseline_lock.py`
- `check_a0_file_registration.py`
- `check_a0_golden_fixture.py`
- `check_baseline_slices.py`
- `check_final_no_go_backup_upload.py`
- `check_g5_exit.py`
- `check_lineage_completeness.py`
- `check_lineage_public_safe.py`
- `check_lineage_report_gate.py`
- `check_no_float_money.py`
- `check_part1_stages_01_03_review.py`
- `check_part2_stages_04_06_review.py`
- `check_part3_stages_07_09_review.py`
- `check_part4_stages_10_12_review.py`
- `check_part5_stages_13_15_review.py`
- `check_part6_stages_16_18_review.py`
- `check_report_grade_gate.py`
- `check_required_html.py`
- `check_s05_p2_completion_gate.py`
- `check_s05_p2_excel_owner_decision.py`
- `check_s05_p2_owner_decision_intake.py`
- `check_s05_p2_owner_decision_templates.py`
- `check_s06_p2_difference_queue.py`
- `check_s06_p3_validation_evidence.py`
- `check_s07_p1_finance_file_adapter.py`
- `check_s07_p2_wps_file_adapter.py`
- `check_s07_p3_redcircle_postponement.py`
- `check_s08_p1_project_composite_key.py`
- `check_s08_p2_business_entity_model.py`
- `check_s08_p3_entity_matching_quality.py`
- `check_s09_p1_project_cost_fact_layer.py`
- `check_s09_p2_margin_cash_margin.py`
- `check_s09_p3_scope_reconciliation.py`
- `check_s09_stage_review.py`
- `check_s10_p1_report_templates.py`
- `check_s10_p2_report_grade_runtime.py`
- `check_s10_p3_report_export.py`
- `check_s10_stage_review.py`
- `check_s11_p1_home_navigation.py`
- `check_s11_p2_source_check_board.py`
- `check_s11_p3_project_cost_page.py`
- `check_s11_stage_review.py`
- `check_s12_p1_manual_resolution_events.py`
- `check_s12_p2_manual_impact_preview.py`
- `check_s12_p3_manual_rerun_mechanism.py`
- `check_s12_stage_review.py`
- `check_s13_p1_financial_operating_report.py`
- `check_s13_p2_collection_receivable_aging.py`
- `check_s13_p3_cross_table_review.py`
- `check_s13_stage_review.py`
- `check_s14_p1_fund_cash_loan_plan.py`
- `check_s14_p2_invoice_tax_plan.py`
- `check_s14_p3_policy_evidence_plan.py`
- `check_s14_stage_review.py`
- `check_s15_p1_performance_fact_fields.py`
- `check_s15_p2_performance_review_list.py`
- `check_s15_p3_salary_boundary.py`
- `check_s15_stage_review.py`
- `check_s16_p1_subcontract_procurement.py`
- `check_s16_p2_project_status_lifecycle.py`
- `check_s16_p3_customer_business_analysis.py`
- `check_s16_stage_review.py`
- `check_s17_p1_access_security.py`
- `check_s17_p2_notifications.py`
- `check_s17_p3_operations_sop.py`
- `check_s17_stage_review.py`
- `check_s18_p1_precision_stress.py`
- `check_s18_p2_full_regression_acceptance.py`
- `check_s18_p3_integration_preparation.py`
- `check_s18_stage_review.py`
- `check_s24_stage_review.py`
- `check_whole_project_final_review.py`
- `check_worktree_cleanup.py`
- `collection_receivable_aging.py`
- `cross_source_difference_queue.py`
- `cross_table_review.py`
- `customer_business_analysis.py`
- `data_source_matrix.py`
- `data_source_panel.py`
- `entity_matching_quality.py`
- `evidence_check.py`
- `facts_from_staging.py`
- `field_standardization.py`
- `file_import_register.py`
- `finance_file_adapter.py`
- `financial_operating_report.py`
- `full_library_archive.py`
- `full_regression_acceptance.py`
- `fund_cash_loan_plan.py`
- `gate_runner.py`
- `generate_tool_test_report.py`
- `goods_movement_extract.py`
- `home_navigation_runtime.py`
- `immutability_policy_check.py`
- `integration_preparation.py`
- `invoice_lines_extract.py`
- `invoice_raw_extract.py`
- `invoice_tax_plan.py`
- `kingdee_extract.py`
- `kingdee_ledger_reclass.py`
- `kingdee_unpack.py`
- `kingdee_voucher_extract.py`
- `kingdee_xls_extract.py`
- `lineage_commit_message.py`
- `lineage_graph.py`
- `loan_register_extract.py`
- `manual_impact_preview.py`
- `manual_rerun_mechanism.py`
- `manual_resolution_events.py`
- `material_matcher.py`
- `metadata_protocol_check.py`
- `no_omission_check.py`
- `notification_reminders.py`
- `op_indicators_extract.py`
- `op_monthly_extract.py`
- `operations_sop.py`
- `performance_fact_fields.py`
- `performance_review_list.py`
- `performance_salary_boundary.py`
- `personal_advance_extract.py`
- `pick_coldstart_retries.py`
- `pick_stalest_skill.py`
- `policy_evidence_plan.py`
- `precision_stress_validation.py`
- `preview_s05_p2_owner_decision_application.py`
- `private_db_access.py`
- `project_composite_key.py`
- `project_cost_fact_layer.py`
- `project_cost_page_runtime.py`
- `project_margin_cash_margin.py`
- `project_scope_reconciliation.py`
- `project_status_lifecycle.py`
- `recon_batch.py`
- `recon_common.py`
- `redcircle_postponement_policy.py`
- `register_kmdb_batch.py`
- `report_export_runtime.py`
- `report_flow_state.py`
- `report_grade_runtime.py`
- `report_templates.py`
- `row_matcher.py`
- `should_request_dws_auth.py`
- `sign_g5.py`
- `skill_failure_code.py`
- `skill_ledger_uplink.py`
- `source_check_board_runtime.py`
- `source_check_matrix.py`
- `source_priority.py`
- `staging_db.py`
- `staging_extract.py`
- `staging_inventory.py`
- `staging_quality.py`
- `subcontract_procurement_aggregation.py`
- `subject_code_map_extract.py`
- `tax_composition_extract.py`
- `upload_quality_receipt.py`
- `validation_evidence_output.py`
- `wps_file_adapter.py`
- `zero_delta_validator.py`

### 按子目录

- **`automation/`** —— 4 个：`backup_dws_output_manifest.py`、`check_kmfa_automation_schedules.py`、`dws_auth_keepalive.py`、`dws_data_auth_request.py`
- **`daily_routine_check/`** —— 11 个：`__init__.py`、`archive_reader.py`、`cash_classifier.py`、`config_loader.py`、`git_autosync.py`、`healthcheck.py`、`ledger.py`、`main.py`…
- **`dingtalk_attendance/`** —— 35 个：`__init__.py`、`anomaly_rules.py`、`attendance_collect.py`、`automatic_closure.py`、`check_dingtalk_attendance.py`、`check_s19_dingtalk_attendance.py`、`cleanup_runtime.py`、`collection_integrity.py`…
- **`project_cost/`** —— 7 个：`account_map.py`、`build_customer_margin.py`、`build_project_margin.py`、`build_recent_completed.py`、`input_matrix.py`、`render_report.py`、`rollup.py`

### 活跃测试

`KMFA/tests/` 里非 `test_v01*` 的共 **120** 个。

---

统计：tools 共 908 个 .py（冻结 683 / 活跃 225），tests 冻结 350 / 活跃 120。
