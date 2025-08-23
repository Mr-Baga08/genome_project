# frontend/Dockerfile
# Build stage
FROM node:18-alpine as build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --legacy-peer-deps
# Copy source code
COPY . .

# Build the application
ARG REACT_APP_API_URL=http://localhost:8000
ENV REACT_APP_API_URL=$REACT_APP_API_URL

RUN npm run build

# Start in development mode instead of building
EXPOSE 3000
CMD ["npm", "start"]

# # Production stage
# FROM nginx:alpine

# # Copy built application
# COPY --from=build /app/build /usr/share/nginx/html

# # Copy nginx configuration
# COPY nginx.conf /etc/nginx/nginx.conf

# # Expose port 80
# EXPOSE 80

# CMD ["nginx", "-g", "daemon off;"]
