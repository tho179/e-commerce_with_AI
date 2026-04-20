FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Sao chép file requirements vào trước
COPY requirements.txt /app/

# Chạy lệnh cài đặt với quyền ưu tiên
RUN python -m pip install --no-cache-dir --retries 20 --timeout 120 -r requirements.txt

COPY . /app/

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]