FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY node.py .

RUN mkdir -p /app/data

EXPOSE 18018

CMD ["python", "node.py"]