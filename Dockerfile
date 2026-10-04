FROM python:3.13-slim
COPY src/giad_agents /opt/giad-agents/giad_agents
COPY LICENSE NOTICE /opt/giad-agents/
ENV PYTHONPATH=/opt/giad-agents PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 65532:65532
WORKDIR /tmp
