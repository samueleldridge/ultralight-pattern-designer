FROM node:20-alpine

WORKDIR /app

# Install dependencies (using install instead of ci for better compatibility)
COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps

# Copy app
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
