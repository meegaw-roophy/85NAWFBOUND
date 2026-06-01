FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /srv/vektra

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /srv/vektra

EXPOSE 8001

CMD ["python", "manage.py", "runserver", "0.0.0.0:8001"]
