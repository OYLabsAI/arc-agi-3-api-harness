FROM python:3.12-slim-bookworm
WORKDIR /opt/oy-api
COPY requirements-linux.lock ./
RUN python -m pip install --no-cache-dir --require-hashes --only-binary=:all: -r requirements-linux.lock
COPY arc_harness ./arc_harness
COPY plans ./plans
COPY scripts ./scripts
COPY pyproject.toml requirements.lock ./
ENV PYTHONNOUSERSITE=1 PYTHON_DOTENV_DISABLED=1
CMD ["python", "-m", "arc_harness.api_run", "fixture", "--output", "/tmp/oy-api-check"]
