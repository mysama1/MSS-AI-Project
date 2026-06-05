"""MIS-001 DEMO Status Check"""

from datetime import datetime, timedelta

class MISDemoStatus:
    """MIS系统DEMO状态检查"""

    def __init__(self):
        # DEMO启动时间（假设从5月17日19:00开始）
        self.demo_start = datetime(2026, 5, 17, 19, 0)
        self.demo_duration = timedelta(hours=72)
        self.demo_end = self.demo_start + self.demo_duration

        self.now = datetime.now()

    def check_status(self):
        """检查DEMO状态"""
        elapsed = self.now - self.demo_start
        remaining = self.demo_end - self.now
        progress = elapsed / self.demo_duration * 100

        print("="*60)
        print("MIS-001 DEMO STATUS")
        print("="*60)
        print(f"Start: {self.demo_start.strftime('%Y-%m-%d %H:%M')}")
        print(f"End: {self.demo_end.strftime('%Y-%m-%d %H:%M')}")
        print(f"Now: {self.now.strftime('%Y-%m-%d %H:%M')}")
        print(f"Elapsed: {elapsed.total_seconds()/3600:.1f} hours")
        print(f"Remaining: {remaining.total_seconds()/3600:.1f} hours")
        print(f"Progress: {progress:.1f}%")

        if self.now >= self.demo_end:
            print("\n[STATUS] DEMO COMPLETE")
            return 'COMPLETE'
        elif progress > 90:
            print("\n[STATUS] DEMO FINAL STAGE")
            return 'FINAL'
        elif progress > 50:
            print("\n[STATUS] DEMO RUNNING")
            return 'RUNNING'
        else:
            print("\n[STATUS] DEMO EARLY STAGE")
            return 'EARLY'

    def get_recommendations(self):
        """获取建议"""
        status = self.check_status()

        recommendations = {
            'COMPLETE': [
                "收集DEMO结果数据",
                "生成最终报告",
                "准备产品化方案",
            ],
            'FINAL': [
                "监控最后阶段指标",
                "准备数据收集",
                "预生成报告模板",
            ],
            'RUNNING': [
                "继续监控运行状态",
                "记录中期指标",
                "检查资源使用",
            ],
            'EARLY': [
                "确认系统初始化",
                "检查基础功能",
                "验证数据流",
            ],
        }

        print("\nRecommendations:")
        for rec in recommendations.get(status, []):
            print(f"  - {rec}")

        return recommendations.get(status, [])

if __name__ == "__main__":
    checker = MISDemoStatus()
    status = checker.check_status()
    checker.get_recommendations()
