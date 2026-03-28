FROM node:20-alpine AS builder

WORKDIR /app

COPY apps/admin/package*.json ./
RUN npm ci

COPY apps/admin/ ./
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/build /usr/share/nginx/html
COPY apps/admin/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 5003

CMD ["nginx", "-g", "daemon off;"]
