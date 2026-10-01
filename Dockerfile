FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SOURCE_DATE_EPOCH=0 PIP_NO_CACHE_DIR=1
WORKDIR /repo
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY benchmarks/ ./benchmarks/
COPY data/ ./data/
COPY tests/ ./tests/
COPY experiments/ ./experiments/
CMD ["python", "-m", "benchmarks.run_all", "--sizes", "1000,10000,100000", "--out", "experiments/results.json"]
