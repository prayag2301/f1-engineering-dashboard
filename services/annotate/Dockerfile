FROM node:20-alpine

WORKDIR /app

COPY services/annotate/package.json ./
COPY packages/common/typescript/ ../packages/common/typescript/
COPY packages/clients/ ../packages/clients/
RUN npm install

COPY services/annotate/ .

CMD ["node", "--import", "tsx", "src/index.ts"]
