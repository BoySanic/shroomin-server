from debian:trixie-slim

RUN apt-get update && apt-get install postgresql-client -y
RUN mkdir /mkproject

COPY init.sql /mkproject
COPY mkproject-stage1.sh /mkproject
WORKDIR /mkproject

CMD ["sh", "mkproject-stage1.sh"]