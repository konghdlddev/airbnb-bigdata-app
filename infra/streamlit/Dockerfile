FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PATH="$JAVA_HOME/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre-headless \
    bash \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/app

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

EXPOSE 8501
