FROM python:3.10-slim

RUN apt update && apt install -y ffmpeg libespeak1
WORKDIR /app

COPY ./main.py /app
COPY ./utils/ /app/utils
COPY ./integrations/ /app/integrations
COPY ./app/ /app/app
COPY ./requirements.txt /app

RUN ls /app

RUN mkdir db_data

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
CMD [ "python3", "-u", "/app/main.py" ]
