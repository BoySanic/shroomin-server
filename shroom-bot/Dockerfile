from debian:trixie-slim

RUN apt-get update && apt-get install python3 python3-pip -y

RUN groupadd -g 1000 shroom && \
    useradd -m -u 1000 -g shroom shroom

RUN mkdir /shroom

WORKDIR /shroom
RUN python3 -m pip install -U discord.py requests --break-system-packages
COPY sizeCheck /shroom
COPY bot.py /shroom
RUN chown shroom:shroom /shroom




CMD ["python3", "bot.py"]