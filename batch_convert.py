#!/usr/bin/env python3
"""
Batch MCP to Skill Converter
============================
批量转换 servers 目录下的所有 MCP 配置为 Claude Skills

用法:
    python batch_convert.py
"""

import json
import asyncio
import subprocess
import sys
from pathlib import Path
from typing import List, Dict
import time


class BatchConverter:
    """批量转换 MCP 配置为 Skills"""

    def __init__(self, servers_dir: str = "servers", output_base_dir: str = "skills",
                 mcp_config_file: str = "mcpservers.json"):
        self.servers_dir = Path(servers_dir)
        self.output_base_dir = Path(output_base_dir)
        self.mcp_config_file = Path(mcp_config_file)
        self.results: List[Dict] = []

    def split_mcpservers_json(self) -> int:
        """拆分 mcpservers.json 到 servers 目录"""
        if not self.mcp_config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.mcp_config_file}")

        print(f"\n[SPLIT] 拆分 {self.mcp_config_file} 到 {self.servers_dir}/")

        # 读取 mcpservers.json
        with open(self.mcp_config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        mcp_servers = data.get('mcpServers', {})
        if not mcp_servers:
            print(f"[WARN] 未找到 'mcpServers' 字段")
            return 0

        # 确保 servers 目录存在
        self.servers_dir.mkdir(parents=True, exist_ok=True)

        count = 0
        for server_name, server_config in mcp_servers.items():
            # 添加 name 字段
            server_config['name'] = server_name

            # 保存到单独文件
            output_file = self.servers_dir / f"{server_name}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(server_config, f, indent=2, ensure_ascii=False)

            print(f"   [OK] {server_name}.json")
            count += 1

        print(f"\n[DONE] 已拆分 {count} 个服务器配置到 {self.servers_dir}/")
        return count

    def get_server_configs(self) -> List[Path]:
        """获取 servers 目录下的所有 JSON 配置文件"""
        if not self.servers_dir.exists():
            raise FileNotFoundError(f"servers 目录不存在: {self.servers_dir}")

        configs = sorted(self.servers_dir.glob("*.json"))
        return configs

    def get_skill_name(self, config_path: Path) -> str:
        """从配置文件路径生成技能名称"""
        # context7.json -> skill-context7
        return f"skill-{config_path.stem}"

    def convert_single(self, config_path: Path) -> Dict:
        """转换单个配置文件"""
        skill_name = self.get_skill_name(config_path)
        output_dir = self.output_base_dir / skill_name

        print(f"\n{'='*60}")
        print(f"[CONVERT] 正在转换: {config_path.name}")
        print(f"   输出目录: {output_dir}")
        print(f"{'='*60}")

        # 读取配置验证格式
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if 'name' not in config:
                return {
                    "file": config_path.name,
                    "status": "error",
                    "message": "配置文件缺少 'name' 字段"
                }
        except json.JSONDecodeError as e:
            return {
                "file": config_path.name,
                "status": "error",
                "message": f"JSON 解析失败: {e}"
            }

        # 执行转换命令
        cmd = [
            sys.executable,
            "mcp_to_skill_v2.py",
            "--mcp-config", str(config_path),
            "--output-dir", str(output_dir)
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=120  # 2分钟超时
            )

            if result.returncode == 0:
                return {
                    "file": config_path.name,
                    "status": "success",
                    "skill": skill_name,
                    "output_dir": str(output_dir)
                }
            else:
                return {
                    "file": config_path.name,
                    "status": "error",
                    "message": result.stderr or result.stdout
                }

        except subprocess.TimeoutExpired:
            return {
                "file": config_path.name,
                "status": "timeout",
                "message": "转换超时 (120s)"
            }
        except Exception as e:
            return {
                "file": config_path.name,
                "status": "error",
                "message": str(e)
            }

    def run(self, dry_run: bool = False, skip_split: bool = False):
        """执行批量转换"""
        # 第一步：拆分 mcpservers.json
        if not skip_split:
            try:
                self.split_mcpservers_json()
            except FileNotFoundError:
                print(f"[WARN] {self.mcp_config_file} 不存在，跳过拆分步骤")
        else:
            print(f"[SKIP] 跳过拆分步骤")

        configs = self.get_server_configs()

        if not configs:
            print(f"[ERROR] 在 {self.servers_dir} 目录下未找到任何 .json 配置文件")
            return

        print(f"\n[FOUND] 发现 {len(configs)} 个 MCP 配置文件:")
        for c in configs:
            print(f"   - {c.name}")

        if dry_run:
            print("\n[PREVIEW] 预览模式 - 不会实际执行转换")
            for config in configs:
                skill_name = self.get_skill_name(config)
                output_dir = self.output_base_dir / skill_name
                print(f"   {config.name} -> {output_dir}")
            return

        # 确保输出目录存在
        self.output_base_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n[START] 开始批量转换...")
        start_time = time.time()

        for i, config_path in enumerate(configs, 1):
            result = self.convert_single(config_path)
            self.results.append(result)

            # 短暂延迟，避免资源占用过高
            if i < len(configs):
                time.sleep(0.5)

        elapsed = time.time() - start_time
        self.print_summary(elapsed)

    def print_summary(self, elapsed: float):
        """打印转换摘要"""
        print(f"\n{'='*60}")
        print(f"[SUMMARY] 转换摘要 (耗时 {elapsed:.1f} 秒)")
        print(f"{'='*60}")

        success_count = sum(1 for r in self.results if r["status"] == "success")
        error_count = sum(1 for r in self.results if r["status"] == "error")
        timeout_count = sum(1 for r in self.results if r["status"] == "timeout")

        print(f"\n[OK] 成功: {success_count}")
        print(f"[FAIL] 失败: {error_count}")
        print(f"[TIMEOUT] 超时: {timeout_count}")
        print(f"[TOTAL] 总计: {len(self.results)}")

        if success_count > 0:
            print(f"\n[SUCCESS] 成功转换的技能:")
            for r in self.results:
                if r["status"] == "success":
                    print(f"   - {r['skill']} ({r['output_dir']})")

        if error_count > 0 or timeout_count > 0:
            print(f"\n[FAILED] 转换失败的配置:")
            for r in self.results:
                if r["status"] in ["error", "timeout"]:
                    msg = r.get("message", "")[:50]
                    print(f"   - {r['file']}: {msg}")

        print(f"\n{'='*60}")
        if success_count > 0:
            print(f"\n[INSTALL] 安装技能到 Claude:")
            print(f"   Windows: xcopy /E /I /Y skills\\skill-* %USERPROFILE%\\.claude\\skills\\")
            print(f"   Linux/Mac: cp -r skills/skill-* ~/.claude/skills/")
        print(f"{'='*60}\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="批量转换 MCP 配置为 Claude Skills",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 执行批量转换（自动拆分 mcpservers.json）
    python batch_convert.py

    # 预览将要转换的文件
    python batch_convert.py --dry-run

    # 跳过拆分步骤（servers/ 目录已存在）
    python batch_convert.py --skip-split

    # 指定自定义目录
    python batch_convert.py --mcp-config my_config.json --servers-dir my_servers --output-dir my_skills
        """
    )

    parser.add_argument(
        "--mcp-config",
        default="mcpservers.json",
        help="MCP 服务器配置文件 (默认: mcpservers.json)"
    )
    parser.add_argument(
        "--servers-dir",
        default="servers",
        help="拆分后的配置文件目录 (默认: servers)"
    )
    parser.add_argument(
        "--output-dir",
        default="skills",
        help="技能输出目录 (默认: skills)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不实际执行转换"
    )
    parser.add_argument(
        "--skip-split",
        action="store_true",
        help="跳过拆分步骤，直接使用现有 servers/ 目录"
    )

    args = parser.parse_args()

    converter = BatchConverter(
        servers_dir=args.servers_dir,
        output_base_dir=args.output_dir,
        mcp_config_file=args.mcp_config
    )

    try:
        converter.run(dry_run=args.dry_run, skip_split=args.skip_split)
    except FileNotFoundError as e:
        print(f"[ERROR] 错误: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\n[INTERRUPTED] 用户中断转换")
        sys.exit(1)


if __name__ == "__main__":
    main()
