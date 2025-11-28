# Estágio de Build
FROM node:20-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .

# --- VARIÁVEIS DE AMBIENTE (ARGS) ---
ARG VITE_API_QUALITY_URL
ENV VITE_API_QUALITY_URL=$VITE_API_QUALITY_URL

# ADICIONE ISTO AQUI:
ARG VITE_API_DOCS_URL
ENV VITE_API_DOCS_URL=$VITE_API_DOCS_URL
# ------------------------------------

RUN npm run build

# Estágio de Produção (Nginx)
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]