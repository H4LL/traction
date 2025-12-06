#!/usr/bin/env node

/**
 * Simple cheqd registrar proxy for local network
 * Implements the two-step DID creation workflow required by cheqd plugin:
 * 1. First request: Return action state with signing request  
 * 2. Second request: Return finished state with DID document
 */

const http = require('http');
const { URL } = require('url');

const PORT = process.env.CHEQD_REGISTRAR_PORT || 9080;
const CHEQD_RPC_URL = process.env.CHEQD_REST_ENDPOINT || 'http://host.docker.internal:1317';

console.log(`Starting cheqd registrar proxy on port ${PORT}`);
console.log(`Proxying to local cheqd network at ${CHEQD_RPC_URL}`);

// Track ongoing jobs for the two-step workflow
const activeJobs = new Map();

const server = http.createServer(async (req, res) => {
    // Set CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    
    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }
    
    console.log(`${req.method} ${req.url}`);
    
    try {
        if (req.method === 'POST' && req.url.startsWith('/1.0/create')) {
            // Handle DID creation request
            let body = '';
            req.on('data', chunk => body += chunk);
            req.on('end', async () => {
                try {
                    const payload = JSON.parse(body);
                    console.log('Create DID request:', JSON.stringify(payload, null, 2));
                    
                    // Check if this is a signing submission (second step)
                    if (payload.jobId && payload.secret && payload.secret.signingResponse) {
                        console.log('Processing signing submission (step 2)');
                        
                        // Get the job info
                        const jobInfo = activeJobs.get(payload.jobId);
                        if (!jobInfo) {
                            console.error('Job not found:', payload.jobId);
                            res.writeHead(400);
                            res.end(JSON.stringify({ error: 'Job not found' }));
                            return;
                        }
                        
                        // Return finished state with DID document
                        const response = {
                            jobId: payload.jobId,
                            didState: {
                                state: "finished",
                                did: jobInfo.did,
                                didDocument: {
                                    "@context": ["https://www.w3.org/ns/did/v1"],
                                    id: jobInfo.did,
                                    controller: [jobInfo.did],
                                    verificationMethod: [{
                                        id: `${jobInfo.did}#key-1`,
                                        type: "Ed25519VerificationKey2020",
                                        controller: jobInfo.did,
                                        publicKeyMultibase: "z6MkrJVnaZkeFzdQyQSrS2WigqbsQV2BEi2Hn1vQTKMGb1nM"
                                    }],
                                    authentication: [`${jobInfo.did}#key-1`]
                                }
                            },
                            didRegistrationMetadata: {}
                        };
                        
                        // Clean up the job
                        activeJobs.delete(payload.jobId);
                        
                        res.setHeader('Content-Type', 'application/json');
                        res.writeHead(200);
                        res.end(JSON.stringify(response));
                        
                    } else {
                        console.log('Initial create request (step 1)');
                        
                        // First step: return action state with signing request
                        const mockDid = `did:cheqd:xanadu:${Date.now()}`;
                        const jobId = `job-${Date.now()}`;
                        const kidValue = `${mockDid}#key-1`;
                        
                        // Store job info for second step
                        activeJobs.set(jobId, { did: mockDid, created: Date.now() });
                        
                        const response = {
                            jobId: jobId,
                            didState: {
                                state: "action",
                                did: mockDid,
                                action: "signPayload",
                                signingRequest: {
                                    "signingRequest0": {
                                        kid: kidValue,
                                        serializedPayload: "VGVzdCBwYXlsb2Fk" // Base64 for "Test payload"
                                    }
                                }
                            },
                            didRegistrationMetadata: {}
                        };
                        
                        console.log('Returning action state with signing request');
                        res.setHeader('Content-Type', 'application/json');
                        res.writeHead(200);
                        res.end(JSON.stringify(response));
                    }
                    
                } catch (error) {
                    console.error('Error processing create request:', error);
                    res.writeHead(500);
                    res.end(JSON.stringify({ error: 'Internal server error' }));
                }
            });
            
        } else {
            // Default response for other endpoints
            res.writeHead(404);
            res.end(JSON.stringify({ error: 'Endpoint not found' }));
        }
        
    } catch (error) {
        console.error('Request error:', error);
        res.writeHead(500);
        res.end(JSON.stringify({ error: 'Internal server error' }));
    }
});

// Cleanup old jobs periodically (1 hour)
setInterval(() => {
    const now = Date.now();
    for (const [jobId, jobInfo] of activeJobs.entries()) {
        if (now - jobInfo.created > 60 * 60 * 1000) {
            console.log('Cleaning up expired job:', jobId);
            activeJobs.delete(jobId);
        }
    }
}, 10 * 60 * 1000); // Check every 10 minutes

server.listen(PORT, () => {
    console.log(`Cheqd registrar proxy listening on port ${PORT}`);
});