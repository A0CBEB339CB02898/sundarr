FROM node:22-alpine AS deps

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

FROM deps AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]
