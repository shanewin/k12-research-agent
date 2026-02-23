FROM node:20-slim

WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the frontend code
COPY frontend/ .

# Expose the Vite port
EXPOSE 5173

# Command to run the development server
CMD ["npm", "run", "dev", "--", "--host"]
