#!/usr/bin/env python3
"""判定社区树编译产物能否与一加 13T 出厂 vendor 模块配套。

判据来自设备本身：出厂 vendor_boot_a 内 514 个模块的 __versions 段。
全部一致才算 PASS；任何一项不符都说明 ABI 不匹配，不值得刷机。
"""
import json
import sys
from pathlib import Path

CRITICAL = ["walt_rq", "get_oplus_rq"]


def load_symvers(path):
    out = {}
    for line in Path(path).read_text(errors="replace").splitlines():
        f = line.split("\t")
        if len(f) >= 2:
            sym = f[1]
            mod = f[2] if len(f) > 2 else ""
            try:
                crc = int(f[0], 16)
            except ValueError:
                continue
            # 同一符号可能多个模块导出，取 vmlinux 的（module 为空）优先
            if sym not in out or not mod:
                out[sym] = crc
    return out


def main():
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    exp = json.loads(Path("expected-symbols.json").read_text(encoding="utf-8"))

    symvers = out_dir / "Module.symvers"
    if not symvers.exists():
        print("FAIL: 没有 Module.symvers，编译目标未产出符号表")
        print("提示: 用 target=all 而不是 vmlinux")
        return 2

    exports = load_symvers(symvers)
    print(f"本次编译导出符号数: {len(exports)}")
    print(f"设备要求符号数: {len(exp['missing_symbols'])}（同提交官方树缺失的部分）")
    print()

    # --- 1) CRC 比对 ---
    crc_ok = True
    print("== 关键符号 CRC ==")
    for sym, info in exp["crc_expectations"].items():
        want = int(info["expected"], 16)
        got = exports.get(sym)
        if got is None:
            print(f"  {sym:<16} 设备={info['expected']}  本次=缺失   -> 不存在")
            crc_ok = False
        elif got == want:
            print(f"  {sym:<16} 设备={info['expected']}  本次=0x{got:08x} -> 一致")
        else:
            print(f"  {sym:<16} 设备={info['expected']}  本次=0x{got:08x} -> 不一致")
            crc_ok = False

    # --- 2) 缺失符号补齐情况 ---
    need = [e["symbol"] for e in exp["missing_symbols"]]
    present = [s for s in need if s in exports]
    absent = [s for s in need if s not in exports]
    print()
    print("== 设备需要、官方树缺失的 258 个符号 ==")
    print(f"  本次已提供: {len(present)}/{len(need)}")
    print(f"  仍然缺失:   {len(absent)}")
    if absent:
        print("  前 25 个仍缺失:")
        for s in absent[:25]:
            print("   -", s)

    print()
    print("=" * 60)
    if crc_ok and not absent:
        print("判定: PASS —— ABI 与出厂模块一致，值得进一步刷机验证")
        return 0
    if crc_ok:
        print("判定: PARTIAL —— 关键 CRC 已一致，但仍有符号缺失")
        print("      说明调度器对上了，部分驱动框架仍缺，不能直接刷")
        return 1
    print("判定: FAIL —— CRC 不匹配，社区树版本与本固件不符，刷机必然失败")
    return 1


if __name__ == "__main__":
    sys.exit(main())
