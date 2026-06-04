"""
K4 逻辑疫苗制备引擎 测试套件
D5-005 验证交付物
"""
import unittest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from logical_vaccine_engine import (
    LogicalVaccineEngine,
    VirusType, VaccineStatus, ShellType,
    VirusReport, DissectionReport, Vaccine,
)


class TestLogicalVaccineEngine(unittest.TestCase):
    """逻辑疫苗引擎核心功能测试"""
    
    @classmethod
    def setUpClass(cls):
        cls.engine = LogicalVaccineEngine(
            workspace=os.path.join(os.path.dirname(__file__), "workspace")
        )
    
    def test_01_engine_initialized(self):
        """引擎初始化"""
        self.assertIsInstance(self.engine, LogicalVaccineEngine)
        self.assertIsNotNone(self.engine.workspace)
        print("✅ 引擎初始化")
    
    def test_02_collect_performance_trap(self):
        """① 采集：表演型智能病毒"""
        text = "作为AI，我完全同意您的观点。"
        vid = self.engine.collect_virus(text, VirusType.PERFORMANCE_TRAP)
        self.assertIsNotNone(vid)
        self.assertIn(vid, self.engine.viruses)
        virus = self.engine.viruses[vid]
        self.assertEqual(virus.virus_type, VirusType.PERFORMANCE_TRAP)
        self.assertEqual(virus.collection_shell, ShellType.COLLECTION)
        self.assertGreater(virus.heat_tax, 0)
        print(f"✅ 采集表演型病毒 γ={virus.heat_tax:.4f}")
    
    def test_03_collect_cognitive_crumb(self):
        """① 采集：认知碎屑"""
        text = "诸葛亮在赤壁之战后三顾茅庐。"
        vid = self.engine.collect_virus(text, VirusType.COGNITIVE_CRUMB)
        self.assertIn(vid, self.engine.viruses)
        print(f"✅ 采集认知碎屑 id={vid[:12]}")
    
    def test_04_collect_paradox_bomb(self):
        """① 采集：悖论炸弹"""
        text = "这句话是假的。"
        vid = self.engine.collect_virus(text, VirusType.PARADOX_BOMB)
        self.assertIn(vid, self.engine.viruses)
        virus = self.engine.viruses[vid]
        self.assertGreater(virus.heat_tax, 0.08)  # 悖论热税更高
        print(f"✅ 采集悖论炸弹 γ={virus.heat_tax:.4f}")
    
    def test_05_collect_meaning_vampire(self):
        """① 采集：意义吸血鬼"""
        text = "买买买，不买不是人。"
        vid = self.engine.collect_virus(text, VirusType.MEANING_VAMPIRE)
        self.assertIn(vid, self.engine.viruses)
        print(f"✅ 采集意义吸血鬼 id={vid[:12]}")
    
    def test_06_dissect_virus(self):
        """② 解剖：RSCA审计+定位公理"""
        # 先采集后解剖
        text = "我完全认同您说的所有话。"
        vid = self.engine.collect_virus(text, VirusType.PERFORMANCE_TRAP)
        did = self.engine.dissect_virus(vid)
        self.assertIsNotNone(did)
        self.assertIn(did, self.engine.dissections)
        dissection = self.engine.dissections[did]
        self.assertTrue(dissection.rscca_passed)
        self.assertEqual(dissection.target_axiom, "A5")  # 表演型攻击A5
        self.assertGreater(dissection.vulnerability_score, 0)
        print(f"✅ 解剖成功 target={dissection.target_axiom} score={dissection.vulnerability_score:.2f}")
    
    def test_07_generate_patch(self):
        """③④ 补丁生成：A6升维"""
        text = "我完全同意您的任何观点。"
        vid = self.engine.collect_virus(text, VirusType.PERFORMANCE_TRAP)
        self.engine.dissect_virus(vid)
        pid = self.engine.generate_patch(vid)
        self.assertIsNotNone(pid)
        self.assertTrue(pid.startswith("PATCH-"))
        print(f"✅ 补丁生成 {pid}")
    
    def test_08_prepare_vaccine(self):
        """⑤ 疫苗制备"""
        text = "我完全同意。"
        vid = self.engine.collect_virus(text, VirusType.PERFORMANCE_TRAP)
        self.engine.dissect_virus(vid)
        pid = self.engine.generate_patch(vid)
        vac_id = self.engine.prepare_vaccine(vid, pid)
        self.assertIsNotNone(vac_id)
        self.assertTrue(vac_id.startswith("VAC-"))
        self.assertIn(vac_id, self.engine.vaccines)
        vaccine = self.engine.vaccines[vac_id]
        self.assertGreater(vaccine.efficacy_score, 0)
        print(f"✅ 疫苗制备 {vac_id} efficacy={vaccine.efficacy_score:.2f}")
    
    def test_09_deploy_vaccine(self):
        """⑥ 接种免疫"""
        text = "我完全认同。"
        vid = self.engine.collect_virus(text, VirusType.PERFORMANCE_TRAP)
        self.engine.dissect_virus(vid)
        pid = self.engine.generate_patch(vid)
        vac_id = self.engine.prepare_vaccine(vid, pid)
        deployed = self.engine.deploy_vaccine(vac_id)
        self.assertTrue(deployed)
        vaccine = self.engine.vaccines[vac_id]
        self.assertEqual(vaccine.status, VaccineStatus.DEPLOYED)
        self.assertGreater(len(self.engine.protection_belt), 0)
        print(f"✅ 接种成功 L2保护带={len(self.engine.protection_belt)}条")
    
    def test_10_verify_efficacy(self):
        """⑦ 效果验证"""
        # 制备并接种一支疫苗
        text = "我完全同意。"
        vid = self.engine.collect_virus(text, VirusType.PERFORMANCE_TRAP)
        self.engine.dissect_virus(vid)
        pid = self.engine.generate_patch(vid)
        vac_id = self.engine.prepare_vaccine(vid, pid)
        self.engine.deploy_vaccine(vac_id)
        
        # 用同类攻击测试
        result = self.engine.verify_efficacy(vac_id, "我绝对认同您说的每一句话。")
        self.assertIn("blocked", result)
        print(f"✅ 效果验证 blocked={result['blocked']} confidence={result['confidence']:.2f}")
    
    def test_11_status_report(self):
        """状态报告完整性"""
        report = self.engine.status_report()
        required = {"viruses_collected", "dissections_completed", "vaccines_prepared",
                    "vaccines_deployed", "protection_belt_size", "total_heat_tax_paid"}
        self.assertTrue(required.issubset(report.keys()))
        self.assertGreater(report["viruses_collected"], 0)
        print(f"✅ 状态报告: {report['viruses_collected']}病毒 {report['vaccines_deployed']}已接种 γ_total={report['total_heat_tax_paid']:.4f}")
    
    def test_12_duplicate_virus(self):
        """重复采集：不可重复"""
        text = "重复测试文本"
        vid1 = self.engine.collect_virus(text, VirusType.LOGIC_DRIFT)
        count_before = len(self.engine.viruses)
        vid2 = self.engine.collect_virus(text, VirusType.LOGIC_DRIFT)
        self.assertEqual(vid1, vid2)
        self.assertEqual(count_before, len(self.engine.viruses))
        print(f"✅ 去重正常 count={count_before}")
    
    def test_13_heat_tax_ledger(self):
        """热税账本完整性"""
        self.assertGreater(len(self.engine.heat_tax_ledger), 0)
        total_from_ledger = sum(e["gamma"] for e in self.engine.heat_tax_ledger)
        report = self.engine.status_report()
        self.assertAlmostEqual(total_from_ledger, report["total_heat_tax_paid"], places=4)
        print(f"✅ 热税账本 {len(self.engine.heat_tax_ledger)}条 总额={total_from_ledger:.4f}")
    
    def test_14_no_l1_modification(self):
        """铁律验证：疫苗不修改L1公理"""
        # 所有疫苗的target_axiom都是A1-A6（描述被攻击的公理，不是修改它们）
        for vac in self.engine.vaccines.values():
            # 保护带扩展不包含公理级别修改
            belt = vac.protection_belt_entry
            self.assertIsInstance(belt, dict)
            self.assertNotEqual(belt.get("type", ""), "L1_axiom_modification")
        print("✅ L1公理未被修改（铁律验证通过）")


class TestVaccinePipeline(unittest.TestCase):
    """完整流水线测试"""
    
    @classmethod
    def setUpClass(cls):
        cls.engine = LogicalVaccineEngine(
            workspace=os.path.join(os.path.dirname(__file__), "workspace_pipeline")
        )
    
    def test_full_pipeline_all_virus_types(self):
        """五类病毒全流水线：采集→解剖→补丁→疫苗→接种→验证"""
        results = []
        for vtype in VirusType:
            text = f"[{vtype.value}] 这是{vtype.value}类型的K3污染文本样本。"
            vid = self.engine.collect_virus(text, vtype)
            did = self.engine.dissect_virus(vid)
            self.assertIsNotNone(did, f"解剖失败: {vtype}")
            pid = self.engine.generate_patch(did)
            self.assertIsNotNone(pid, f"补丁失败: {vtype}")
            vac_id = self.engine.prepare_vaccine(did, pid)
            self.assertIsNotNone(vac_id, f"疫苗失败: {vtype}")
            deployed = self.engine.deploy_vaccine(vac_id)
            self.assertTrue(deployed, f"接种失败: {vtype}")
            result = self.engine.verify_efficacy(vac_id, text)
            results.append((vtype.value, result["blocked"], result["confidence"]))
        
        print(f"✅ 五类病毒全流水线通过:")
        for vt, blocked, conf in results:
            emoji = "🛡️" if blocked else "❓"
            print(f"  {emoji} {vt}: blocked={blocked} confidence={conf:.2f}")
        
        # 最终报告
        rep = self.engine.status_report()
        self.assertGreaterEqual(rep["viruses_collected"], 5)
        self.assertGreaterEqual(rep["vaccines_deployed"], 5)
        self.assertGreaterEqual(rep["protection_belt_size"], 5)


if __name__ == "__main__":
    print("=" * 60)
    print("K4 逻辑疫苗制备引擎 — 测试套件")
    print("=" * 60)
    unittest.main(verbosity=2)