"""Offline regression tests: no network, DB, workers, or provider calls."""
import unittest
from backend.asset_forge.backend.content_stage_quality import assess_stage, VALID_STAGES

class StageQualityTests(unittest.TestCase):
    def test_c001_visual_requires_review(self):
        job = {"status": "READY_TO_PUBLISH", "qa_status": "PASS", "content_package": {
            "pipeline_route": "VISUAL", "asset_provider": "local_template",
            "asset_mode": "deterministic_fallback", "asset_storage_path": "c001/cover.png"}}
        result = assess_stage(job, "VISUAL")
        self.assertEqual((result.result, result.return_stage), ("REVIEW_REQUIRED", "VISUAL"))

    def test_3501740c_video_fallback_stops_render(self):
        job = {"qa_status": "PASS", "render_qa": {"status": "PASS"}, "content_package": {
            "pipeline_route": "VIDEO", "asset_provider": "local_template",
            "asset_mode": "deterministic_fallback", "asset_storage_path": "video/cover.png"}}
        self.assertEqual(assess_stage(job, "VISUAL").result, "FAIL")
        result = assess_stage(job, "VIDEO_RENDER")
        self.assertEqual((result.result, result.return_stage), ("BLOCKED", "VISUAL"))

    def test_missing_final_evidence_blocked(self):
        self.assertEqual(assess_stage({"content_package": {}}, "FINAL_QA").result, "BLOCKED")

    def test_stale_revision(self):
        job = {"current_input_sha256": "new", "current_output_sha256": "asset"}
        cert = {"stage": "VISUAL", "result": "PASS", "input_sha256": "old",
                "output_sha256": "asset", "validator_version": "v1", "reviewer": "owner"}
        self.assertEqual(assess_stage(job, "VISUAL", evidence=cert).result, "STALE")

    def test_advisory_evidence_pass(self):
        job = {"current_input_sha256": "a", "current_output_sha256": "b",
               "content_package": {"asset_storage_path": "a.png"}}
        cert = {"stage": "VISUAL", "result": "PASS", "input_sha256": "a",
                "output_sha256": "b", "validator_version": "v1", "reviewer": "owner"}
        self.assertEqual(assess_stage(job, "VISUAL", evidence=cert).result, "PASS")

    def test_unreviewed_visual_requires_review(self):
        job = {"current_input_sha256": "a", "current_output_sha256": "b",
               "content_package": {"asset_storage_path": "a.png"}}
        cert = {"stage": "VISUAL", "result": "PASS", "input_sha256": "a",
                "output_sha256": "b", "validator_version": "v1"}
        self.assertEqual(assess_stage(job, "VISUAL", evidence=cert).result, "REVIEW_REQUIRED")

    def test_semantic_fail(self):
        job = {"content_package": {"semantic_fidelity": {"status": "FAIL"}}}
        self.assertEqual(assess_stage(job, "CONTENT").result, "FAIL")

    def test_invalid_stage(self):
        with self.assertRaises(ValueError):
            assess_stage({}, "PUBLISH")

    def test_certificate_cannot_override_video_fallback(self):
        job = {"current_input_sha256": "a", "current_output_sha256": "b",
               "content_package": {"pipeline_route": "VIDEO", "asset_provider": "local_template",
                                   "asset_mode": "deterministic_fallback", "asset_storage_path": "a.png"}}
        cert = {"stage": "VISUAL", "result": "PASS", "input_sha256": "a",
                "output_sha256": "b", "validator_version": "v1", "reviewer": "owner"}
        self.assertEqual(assess_stage(job, "VISUAL", evidence=cert).result, "FAIL")

    def test_certificate_cannot_override_semantic_failure(self):
        job = {"current_input_sha256": "a", "current_output_sha256": "b",
               "content_package": {"semantic_fidelity": {"status": "FAIL"}}}
        cert = {"stage": "CONTENT", "result": "PASS", "input_sha256": "a",
                "output_sha256": "b", "validator_version": "v1"}
        self.assertEqual(assess_stage(job, "CONTENT", evidence=cert).result, "FAIL")

    def test_render_certificate_cannot_skip_visual(self):
        job = {"current_input_sha256": "a", "current_output_sha256": "b",
               "content_package": {"pipeline_route": "VIDEO", "asset_storage_path": "a.png"},
               "render_qa": {"status": "PASS"}}
        cert = {"stage": "VIDEO_RENDER", "result": "PASS", "input_sha256": "a",
                "output_sha256": "b", "validator_version": "v1", "reviewer": "owner"}
        self.assertEqual(assess_stage(job, "VIDEO_RENDER", evidence=cert).return_stage, "VISUAL")

    def test_evidence_stage_mismatch(self):
        self.assertEqual(assess_stage({}, "VISUAL", evidence={"stage": "AUDIO"}).result, "BLOCKED")

    def test_nonvideo_audio_not_applicable(self):
        job = {"content_package": {"pipeline_route": "TEXT"}}
        self.assertEqual(assess_stage(job, "AUDIO").reason_codes, ("STAGE_NOT_APPLICABLE",))

    def test_missing_evidence_hash(self):
        job = {"current_input_sha256": "a", "current_output_sha256": "b"}
        self.assertEqual(assess_stage(job, "VISUAL",
                         evidence={"stage": "VISUAL", "result": "PASS"}).result, "BLOCKED")


    def _cert(self, stage):
        return {"stage": stage, "result": "PASS", "input_sha256": "a",
                "output_sha256": "b", "validator_version": "v1", "reviewer": "owner"}

    def _job(self, **fields):
        return {"current_input_sha256": "a", "current_output_sha256": "b", **fields}

    def test_grounding_failure_cannot_be_overridden(self):
        job = self._job(content_package={"product_grounding_status": "FAILED"})
        self.assertEqual(assess_stage(job, "GROUNDING", evidence=self._cert("GROUNDING")).result, "FAIL")

    def test_grounding_missing_cannot_be_overridden(self):
        self.assertEqual(assess_stage(self._job(), "GROUNDING",
                         evidence=self._cert("GROUNDING")).result, "BLOCKED")

    def test_visual_gate_failure_cannot_be_overridden(self):
        job = self._job(content_package={"asset_storage_path": "a.png",
                                        "asset_quality_gate": {"result": "FAIL"}})
        self.assertEqual(assess_stage(job, "VISUAL", evidence=self._cert("VISUAL")).result, "FAIL")

    def test_visual_missing_asset_cannot_be_overridden(self):
        self.assertEqual(assess_stage(self._job(), "VISUAL",
                         evidence=self._cert("VISUAL")).result, "BLOCKED")

    def test_audio_failure_cannot_be_overridden(self):
        job = self._job(content_package={"pipeline_route": "VIDEO"},
                        audio_status="FAILED", audio_storage_path="audio.mp3")
        self.assertEqual(assess_stage(job, "AUDIO", evidence=self._cert("AUDIO")).result, "FAIL")

    def test_audio_missing_asset_cannot_be_overridden(self):
        job = self._job(content_package={"pipeline_route": "VIDEO"})
        self.assertEqual(assess_stage(job, "AUDIO", evidence=self._cert("AUDIO")).result, "BLOCKED")

    def test_render_missing_technical_qa_cannot_be_overridden(self):
        job = self._job(content_package={"pipeline_route": "VIDEO", "asset_storage_path": "a.png"})
        self.assertEqual(assess_stage(job, "VIDEO_RENDER", evidence=self._cert("VIDEO_RENDER"),
                         visual_evidence=self._cert("VISUAL")).result, "BLOCKED")

    def test_final_qa_certificate_cannot_claim_pass(self):
        self.assertEqual(assess_stage(self._job(), "FINAL_QA",
                         evidence=self._cert("FINAL_QA")).result, "BLOCKED")

    def test_content_missing_semantic_cannot_be_overridden(self):
        self.assertEqual(assess_stage(self._job(), "CONTENT",
                         evidence=self._cert("CONTENT")).result, "BLOCKED")

    def test_render_accepts_valid_upstream_visual_evidence(self):
        job = self._job(content_package={"pipeline_route": "VIDEO", "asset_storage_path": "a.png"},
                        render_qa={"status": "PASS"})
        result = assess_stage(job, "VIDEO_RENDER", evidence=self._cert("VIDEO_RENDER"),
                              visual_evidence=self._cert("VISUAL"))
        self.assertEqual(result.result, "PASS")

    def test_render_rejects_stale_visual_evidence(self):
        job = self._job(content_package={"pipeline_route": "VIDEO", "asset_storage_path": "a.png"},
                        render_qa={"status": "PASS"})
        stale = {**self._cert("VISUAL"), "input_sha256": "old"}
        self.assertEqual(assess_stage(job, "VIDEO_RENDER", evidence=self._cert("VIDEO_RENDER"),
                         visual_evidence=stale).return_stage, "VISUAL")

    def test_reason_codes_none_fails_closed(self):
        job = self._job(content_package={"asset_storage_path": "a.png"})
        cert = {**self._cert("VISUAL"), "reason_codes": None}
        self.assertEqual(assess_stage(job, "VISUAL", evidence=cert).result, "BLOCKED")

    def test_reason_codes_string_fails_closed(self):
        job = self._job(content_package={"asset_storage_path": "a.png"})
        cert = {**self._cert("VISUAL"), "reason_codes": "ERROR"}
        self.assertEqual(assess_stage(job, "VISUAL", evidence=cert).result, "BLOCKED")

    def test_reason_codes_list_passes(self):
        job = self._job(content_package={"asset_storage_path": "a.png"})
        cert = {**self._cert("VISUAL"), "reason_codes": ["OK"]}
        self.assertEqual(assess_stage(job, "VISUAL", evidence=cert).reason_codes, ("OK",))

if __name__ == "__main__":
    unittest.main()
