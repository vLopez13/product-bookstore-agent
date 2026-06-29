require('dotenv').config();
const express = require('express');
const axios = require('axios');

const app = express();
app.use(express.json());

const FASTAPI_URL = process.env.FASTAPI_SERVICE_URL || 'http://localhost:8000';

// 1. Health Check Route
app.get('/gateway-health', async (req, res) => {
    try {
        // Ping our Python backend to check overall system status
        const response = await axios.get(`${FASTAPI_URL}/`);
        res.json({
            gateway: "online",
            fastapi_microservice: response.data
        });
    } catch (error) {
        res.status(502).json({
            gateway: "online",
            fastapi_microservice: "offline or unreachable"
        });
    }
});
app.post('/api/store/ai-search-stream', async (req, res) => {
    try {
        const { query } = req.body;
        if (!query) {
            return res.status(400).json({ error: "Query is required." });
        }
        res.setHeader('Content-Type', 'text/event-stream');
        res.setHeader('Cache-Control', 'no-cache');
        res.setHeader('Connection', 'keep-alive');

        const response = await axios({
            method: 'post',
            url: `${FASTAPI_URL}/products/ai-search-stream`,
            data: { query },
            responseType: 'stream'
        });

        response.data.on('data', (chunk) => {
            res.write(chunk);
        });
        response.data.on('end', () => {
            res.end();
        });
    } catch (error) {
        console.error("Streaming error encountered:", error.message);

        if (!res.headersSent) {
            res.status(500).json({ error: "Failed to initialize AI streaming agent" });
        } else {
            res.write(`data: ${JSON.stringify({ status: "error", message: "Stream interrupted" })}\n\n`);
            res.end();
        }
    }
});
app.get('/api/store/products/:id', async (req, res) => {
    try {
        const response = await axios.get(`${FASTAPI_URL}/products/${req.params.id}`);
        res.json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json({
            error: error.response?.data?.detail || "Product look-up failed"
        });
    }
});
app.post('/api/store/orders', async (req, res) => {
    try {
        const response = await axios.post(`${FASTAPI_URL}/createorder/`, req.body);
        res.status(201).json({
            success: true,
            order: response.data
        });
    } catch (error) {
        res.status(error.response?.status || 500).json({
            error: error.response?.data?.detail || "Order execution failed"
        });
    }
});
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`🚀 Node.js Bookstore Gateway active on port ${PORT}`);
});