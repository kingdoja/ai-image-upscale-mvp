FROM python:3.11-slim

WORKDIR /app/apps/api
COPY apps/api/pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir "fastapi==0.110.3" "starlette==0.37.2" "python-multipart==0.0.9" "httpx==0.27.2" "redis==5.0.8" "rq==1.16.2" "sqlalchemy==1.4.44" "pydantic==1.10.15" "pillow==10.4.0" "psycopg2-binary==2.9.9" "uvicorn[standard]==0.30.6"
COPY apps/api ./ 
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
