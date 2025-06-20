FROM python:3.11

ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV TZ=Asia/Almaty

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    cmake \
    libgl1-mesa-glx

RUN pip install --upgrade pip

COPY /backend/requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

# Add an entrypoint script
COPY docker/dev/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]