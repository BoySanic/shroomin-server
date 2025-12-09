FROM debian:trixie-slim


RUN apt-get update
RUN apt-get install python3 python3-pip -y

RUN groupadd -g 1000 shroom && \
    useradd -m -u 1000 -g shroom shroom

RUN mkdir /server

WORKDIR /server

RUN pip install --no-cache-dir  --break-system-packages fastapi uvicorn psycopg2-binary pycryptodome cryptography
RUN chown shroom:shroom -R /server
COPY /server.py /server
CMD uvicorn server:app --host 0.0.0.0 --port ${WEBSERVER_PORT}