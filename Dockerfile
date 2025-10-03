FROM python:3.11-slim

WORKDIR /app

COPY . /app
COPY ./app/static /app/static

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
