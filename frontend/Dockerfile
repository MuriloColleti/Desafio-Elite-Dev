# Front-end React/Vite servido por Nginx.
#
# Só para o Compose local: na Vercel o build é feito pela própria plataforma, a
# partir do repositório, sem imagem.

FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# A URL da API entra em tempo de BUILD, não de execução: o Vite embute o valor
# no bundle. Trocar de API depois exige rebuildar.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
