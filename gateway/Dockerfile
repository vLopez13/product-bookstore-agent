# gateway/Dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files and install
COPY package*.json ./
RUN npm install

# Copy the gateway code
COPY server.js .
COPY startAgentStream.js . 
COPY email_login.js . 
EXPOSE 3000

CMD ["node", "server.js"]