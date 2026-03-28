FROM node:20-alpine AS builder

WORKDIR /app

COPY apps/voice-chat/package*.json ./
RUN npm ci

COPY packages/ui-shared/ ../packages/ui-shared/
COPY apps/voice-chat/ .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/build /usr/share/nginx/html
COPY apps/voice-chat/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
