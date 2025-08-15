FROM python:3.12-slim

RUN apt-get update && apt-get install -y curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
RUN which node || which nodejs
RUN node -v || nodejs -v
RUN which npm
RUN npm -v

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

WORKDIR /all_folders_from_the_app/app

RUN pip install --upgrade pip

COPY ./app/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY ./app/theme ./theme
RUN cd theme/static_src && npm install
RUN cd theme/static_src && npm run build



# Path to entrypoint
COPY ./app/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
