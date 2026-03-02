FROM node:20-alpine

WORKDIR /app

COPY services/ingest/package.json ./
COPY packages/common/typescript/ ../packages/common/typescript/
COPY packages/clients/ ../packages/clients/
RUN npm install

COPY services/ingest/ .

CMD ["node", "--import", "tsx", "src/index.ts"]
