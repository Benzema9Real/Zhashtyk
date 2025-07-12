FROM python:3.10.12

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config

RUN pip install -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=fund4pro.settings

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
