FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1
WORKDIR /app
COPY requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps .
COPY app ./app
RUN useradd --create-home appuser && mkdir -p /workspace && chown appuser:appuser /workspace
USER appuser
ENV RETAIL_ROOT=/workspace
CMD ["python", "-m", "uvicorn", "retail.api:app", "--host", "0.0.0.0", "--port", "8000"]
