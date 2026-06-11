FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY backend/ ./backend/
COPY data/ ./data/

# 创建数据目录
RUN mkdir -p /app/data/vector_db /app/data/docs /app/data/rag_data/vector_db /app/data/rag_data/docs

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
