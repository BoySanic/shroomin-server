FROM debian:trixie-slim


RUN apt-get update
RUN apt-get install python3 python3-pip -y

WORKDIR /checker

RUN pip install --no-cache-dir  --break-system-packages psycopg2-binary
COPY /seedCheck.py /checker
COPY /sizeCheck /checker
CMD ["python3", "seedCheck.py"]