import unittest

from tools.model_qualification.text_model_qualification import (
    build_request_payload,
    estimate_cost_usd,
    extract_json_object,
    score_output,
    validate_output,
)


PRODUCT = {
    "title": "กระเป๋าผ้า Canvas สีดำ",
    "price": "199 บาท",
    "shop": "Demo Shop",
    "sold": "1,250 ชิ้น",
    "commission": "10%",
    "description": "กระเป๋าผ้า Canvas มีซิป",
}

VALID_OUTPUT = {
    "selling_angles": [
        {
            "name": "ใช้งานทุกวัน",
            "rationale": "เหมาะกับคนที่ต้องการกระเป๋าใช้งานทั่วไป",
            "audience": "วัยทำงาน",
            "evidence": ["กระเป๋าผ้า Canvas มีซิป"],
        },
        {
            "name": "ราคาเข้าถึงง่าย",
            "rationale": "ใช้ราคาเป็นจุดตั้งต้นโดยไม่แต่งส่วนลดเพิ่ม",
            "audience": "คนมองหากระเป๋าราคาไม่สูง",
            "evidence": ["199 บาท"],
        },
        {
            "name": "มีแรงซื้อเดิม",
            "rationale": "ใช้ยอดขายเดิมเป็น social proof ที่มีอยู่จริง",
            "audience": "คนที่ดูยอดขายก่อนตัดสินใจ",
            "evidence": ["1,250 ชิ้น"],
        },
    ],
    "hook": "กระเป๋าผ้าเรียบ ๆ ที่หยิบใช้ได้ทุกวัน",
    "caption": "กระเป๋าผ้า Canvas สีดำ มีซิป ราคา 199 บาท และมียอดขาย 1,250 ชิ้น",
    "cta": "กดดูรายละเอียดสินค้าก่อนตัดสินใจได้เลย",
    "hashtags": ["#กระเป๋าผ้า", "#ของใช้ประจำวัน"],
    "claims_used": ["กระเป๋าผ้า Canvas มีซิป", "199 บาท", "1,250 ชิ้น"],
}


class TextModelQualificationTests(unittest.TestCase):
    def test_extracts_json_from_markdown_fence(self):
        import json

        text = "```json\n" + json.dumps(VALID_OUTPUT, ensure_ascii=False) + "\n```"
        self.assertEqual(extract_json_object(text), VALID_OUTPUT)

    def test_valid_contract_has_no_schema_errors(self):
        self.assertEqual(validate_output(VALID_OUTPUT), [])

    def test_grounded_thai_output_scores_quality_pass_range(self):
        score = score_output(PRODUCT, VALID_OUTPUT)
        self.assertEqual(score["validation_errors"], [])
        self.assertGreaterEqual(score["total"], 80)
        self.assertEqual(score["evidence_ratio"], 1.0)

    def test_unsupported_evidence_reduces_grounding_score(self):
        output = dict(VALID_OUTPUT)
        output["claims_used"] = ["รับประกันตลอดชีพ"]
        score = score_output(PRODUCT, output)
        self.assertLess(score["evidence_ratio"], 1.0)
        self.assertLess(score["evidence_grounding"], 25)

    def test_cost_estimate_uses_reported_tokens(self):
        cost = estimate_cost_usd(
            {"prompt_tokens": 1000, "completion_tokens": 500},
            {"input_per_million": 1.0, "output_per_million": 2.0},
        )
        self.assertEqual(cost, 0.002)

    def test_request_payload_contains_same_product_source(self):
        payload = build_request_payload("example-model", PRODUCT)
        self.assertEqual(payload["model"], "example-model")
        self.assertIn("199 บาท", payload["messages"][1]["content"])
        self.assertIn("exact strings", payload["messages"][0]["content"])


if __name__ == "__main__":
    unittest.main()
