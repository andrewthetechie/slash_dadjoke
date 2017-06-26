FROM python:2.7.13-slim
COPY app.py /app.py
COPY jokes.txt /jokes.txt
RUN pip install bottle requests

EXPOSE 5000

ENTRYPOINT python /app.py