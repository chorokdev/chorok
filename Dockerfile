FROM python:3.9.7

WORKDIR /app

RUN apt-get update && apt-get install --no-install-recommends -y pkg-config ffmpeg libavformat-dev \
                              libavcodec-dev libavdevice-dev libavutil-dev libswscale-dev libavresample-dev libavfilter-dev \
                              gcc libopus-dev python3-dev libnacl-dev git
RUN git config --global credential.helper store

COPY . .
RUN mv config.inc.json config.json
RUN python3 -m pip install -U pip && python3 -m pip install -r requirements.txt

CMD ["python3", "main.py", "production"]