FROM node:22-bookworm

ENV NODE_ENV=production \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY package.json ./
RUN npm install

COPY requirements.txt ./
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .
RUN npm run build

EXPOSE 8080

CMD ["npm", "start"]