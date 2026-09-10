"""考勤异常简报线。与工资线（stage2 / views_payroll_baseline）完全隔离，只读不写其数据。

设计红线：
  1. 运行期零模型调用 —— OCR 走 macOS 系统 Vision 框架，不是 API。
  2. 一条命令跑完，调度方只设 KMFA_RUN_SLOT，不传业务参数、不做判断。
  3. 所有持久化落 SMB；本机只有 /tmp 的 pid 锁与跑完即删的临时目录。
  4. fail-closed —— 任一闸门不过就降级说明，绝不猜测、绝不补零。
"""
__version__ = "0.1.0"
