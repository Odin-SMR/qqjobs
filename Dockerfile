FROM python:3
COPY requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt
COPY src/microq_admin /app/microq_admin
WORKDIR /app
ENTRYPOINT ["python", "-mmicroq_admin"]
