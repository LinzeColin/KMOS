# KMFA skills 云端运行容器（多架构：amd64=OVH/通用 VPS，arm64=Oracle A1；本机两架构均实测）
FROM python:3.12-slim-bookworm

ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    DWS_BIN=/usr/local/bin/dws

# flock 不是独立包（属基础镜像自带的 util-linux）——构建尾部有存在性断言
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      cron curl ca-certificates git tzdata procps \
      tesseract-ocr tesseract-ocr-chi-sim libgomp1 libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/* \
 && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
 && command -v flock

# 技能公共 Python 依赖（各技能自带 requirements 时在此汇总固定）
# OCR（SKL.0005）：rapidocr(PP-OCRv4/onnxruntime) 为主，tesseract 兜底 —— 均有 linux-arm64 轮子
RUN pip install --no-cache-dir openpyxl pyyaml requests \
      rapidocr-onnxruntime pillow pytesseract

# SKL.0005：资金周报 OCR 用 Python 助手替换 swift Vision（主工具零改动，经此环境变量换引擎；
# cron 不继承容器 ENV，run_skill.sh 内另有显式 export）。
# 部署后验收（代码已烧进镜像，无需卷挂载）：
#   docker compose exec skills python3 /opt/kmfa/KMOS/KMFA/skills/资金周报/tools/ocr_with_python.py --selftest
ENV KMFA_FUND_VISION_OCR_COMMAND="python3 /opt/kmfa/KMOS/KMFA/skills/资金周报/tools/ocr_with_python.py"

# build context = 仓根（compose）。运行脚本按仓根路径 COPY 到 /opt/runtime。
COPY KMFA/deploy/skills-runtime/install_dws.sh KMFA/deploy/skills-runtime/dws.sha256.lock* /opt/runtime/
RUN chmod +x /opt/runtime/install_dws.sh && /opt/runtime/install_dws.sh

COPY KMFA/deploy/skills-runtime/entrypoint.sh KMFA/deploy/skills-runtime/run_skill.sh KMFA/deploy/skills-runtime/healthcheck.sh KMFA/deploy/skills-runtime/test_send.sh KMFA/deploy/skills-runtime/crontab.txt /opt/runtime/
RUN chmod +x /opt/runtime/*.sh

# 自包含：把整个仓烧进镜像（Coolify 的 ./ 运行时挂载只含 compose、无代码——见 DT9 主机核验）。
# 放在末尾使代码层最后构建（缓存友好）；.dockerignore 已排除 .git/data.objects(120M)/node_modules 等。
# 每次 push→重 build 即更新代码，不依赖任何运行时卷挂载。
COPY . /opt/kmfa/KMOS

WORKDIR /opt/kmfa/KMOS
HEALTHCHECK --interval=5m --timeout=20s --start-period=1m \
  CMD /opt/runtime/healthcheck.sh || exit 1
ENTRYPOINT ["/opt/runtime/entrypoint.sh"]
