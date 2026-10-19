# OnePlus 13T 内核 ABI 探测

在免费 GitHub runner 上编译社区内核树，判定它的 ABI 能否与一加 13T（PKX110）出厂 vendor 模块配套。

**只做离线判定，不涉及任何设备操作。**

## 为什么需要这个

官方 OSS 源码编出的内核在这台机器上无法启动。原因已定位：

- 出厂 `vendor_boot_a` 内 514 个模块需要 **258 个符号**，官方 OSS 源码里**根本不存在**（`tp_*` 触控框架、`cam_*`、`synx_*`、`hdcp*`、`mmrm_*`、`zs_*_oplus` 等）
- 其中 `msm_drm.ko`（显示核心）依赖 `synx_*`/`hdcp*`/`mmrm_*`，加载失败即无显示
- 两处同名符号 CRC 漂移：`walt_rq`、`get_oplus_rq`，指向私有的 `CONFIG_HMBIRD_SCHED`

社区树 `cctv18/android_kernel_common_oneplus_sm8750` 的 `kernel/sched/hmbird/` 有 11 个实现文件，
而官方树 grep `HMBIRD_SCHED` 为 0。所以值得一试：HMBIRD 是 sm8750 **芯片级**调度器，
一加 13 与 13T 同芯片，实现可能正好对上。

## 判据

期望值全部提取自**设备本身**，见 `expected-symbols.json`：

| 符号 | 出厂模块期望 CRC |
|---|---|
| `walt_rq` | `0xaf4e0da5` |
| `get_oplus_rq` | `0xfcc2a2c2` |

外加 258 个必须在场的符号清单。

## 判定标准

- **PASS** — CRC 全一致且 258 个符号齐全 → 值得进一步刷机验证
- **PARTIAL** — CRC 一致但仍有符号缺失 → 调度器对上了，驱动框架还缺，不能刷
- **FAIL** — CRC 不一致 → 社区树版本与本固件不符，刷机必然失败

## 用法

Actions 页面手动触发 `crc-probe`，可改分支与编译目标。

产物 `crc-probe-result` 含 `Module.symvers`、`.config`、`vmlinux`，保留 7 天。

本地复现：

```bash
python3 check_crc.py /path/to/out
```

## 说明

- 用的是社区树的 `gki_defconfig` 加注入 `CONFIG_HMBIRD_SCHED=y`，不是设备完整配置。
  CRC 只取决于结构体定义与相关 Kconfig，因此足够用于 ABI 判定。
- 本仓库不提供可刷入镜像，也不代表任何设备已被改动。
