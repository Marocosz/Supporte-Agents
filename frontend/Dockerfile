# Estágio de Build
FROM node:20-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
# Argumento de build para injetar a URL da API em produção
ARG VITE_API_QUALITY_URL
ENV VITE_API_QUALITY_URL=$VITE_API_QUALITY_URL

RUN npm run build

# Estágio de Produção (Nginx)
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Copiaremos uma config personalizada do nginx depois
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]