FROM python:3-slim

RUN apt update && apt install -y python3-pip build-essential
RUN rm -rf /var/lib/apt/lists/

WORKDIR /norse

COPY . .

RUN pip3 install --upgrade pip
RUN pip3 install -e .