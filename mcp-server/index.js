#!/usr/bin/env node

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createApiClient, createServer } from "./server.js";

const TOKEN = process.env.LETAGENTPAY_TOKEN;
const API_URL = process.env.LETAGENTPAY_API_URL || "https://api.letagentpay.com/api/v1";

if (!TOKEN) {
  console.error("LETAGENTPAY_TOKEN environment variable is required");
  process.exit(1);
}

const apiCall = createApiClient(TOKEN, API_URL);
const server = createServer(apiCall);

const transport = new StdioServerTransport();
await server.connect(transport);
