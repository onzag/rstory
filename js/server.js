// due to python being a buggy mess with llama-ccp bindings we have to use nodejs server because it just doesn't work with python because
// python being utter garbage with native bindings, this server just forwards requests to python app
// create a simple server that loads the model and waits for requests
const os = require('os');

// change to websockets because streaming over http is a pain
const WebSocket = require('ws');

let MODEL = null;
let MODEL_PATH = ""
async function load_model(model) {
    console.log("Loading model:", model);
    if (MODEL_PATH === model && MODEL !== null) {
        console.log('Model already loaded');
        return;
    }

    if (MODEL !== null) {
        console.log('Unloading previous model');
        await MODEL.dispose();
        MODEL = null;
        MODEL_PATH = "";
    }

    const { getLlama } = await import('node-llama-cpp');
    const llama = await getLlama();
    
    console.log('GPU Support:', llama.gpu || 'Unknown');
    console.log('Build Info:', llama.buildInfo);
    
    const LLAMA_MODEL = await llama.loadModel({
        modelPath: model,
        nCtx: 1024 * 8,
        nGpuLayers: -1,
        nThreads: os.cpus().length,
        verbose: true,
        defaultContextFlashAttention: true,
    });
    MODEL = LLAMA_MODEL
    MODEL_PATH = model;

    // Create a simple HTTP server that takes a prompt and returns a response
    console.log('Model loaded successfully');
}

const wss = new WebSocket.Server({ port: 8000 });

async function generateCompletion(data, onToken, onDone, onError) {
    let prompt = data.prompt;
    let isDisposed = false;
    let isContextDisposed = false;
    let accumulatedText = "";
    let weDisposedOurselves = false;
    const { LlamaCompletion, LlamaText } = await import('node-llama-cpp');

    // fix potential missing newlines at end of prompt
    if (data.do_not_fix_newlines_at_end !== true)  {
        if (!prompt.endsWith('\n')) {
            prompt += '\n\n';
        } else if (!prompt.endsWith('\n\n')) {
            prompt += '\n';
        }
    }

    let context = null
    let completion = null;
    try {
        // Create context and completion for raw text
        context = await MODEL.createContext();
        completion = new LlamaCompletion({
            contextSequence: context.getSequence()
        });

        const basicConfig = {
            temperature: data.temperature || 0.9,
            topP: data.top_p || 0.95,
            repeatPenalty: {
                penalty: data.repeat_penalty || 1.1,
                frequencyPenalty: data.frequency_penalty || 0,
                presencePenalty: data.presence_penalty || 0,
            },
            customStopTriggers: data.stop || [],
            maxTokens: data.max_tokens || 512,
        }
        if (typeof data.max_paragraphs === "number") {
            console.log("Max paragraphs limit set to:", data.max_paragraphs);
        }
        if (typeof data.max_characters === "number") {
            console.log("Max characters limit set to:", data.max_characters);
        }
        console.log("Generation config:", basicConfig);
        await completion.generateCompletion(prompt, {
            ...basicConfig,
            onToken(tokens) {
                if (isDisposed || weDisposedOurselves) return;
                // Stream token-by-token for better responsiveness
                const text = MODEL.detokenize(tokens);
                try {
                    if (typeof data.max_paragraphs === "number") {
                        accumulatedText += text;
                        // count paragraphs
                        let paragraphCount = 0;
                            
                        for (let i = 0; i < accumulatedText.length; i++) {
                            if (accumulatedText[i] === '\n' && accumulatedText[i+1] === '\n') {
                                paragraphCount += 1;
                            }
                            if (paragraphCount >= data.max_paragraphs) {
                                console.log("Max paragraphs reached:", paragraphCount, "stopping completion early.");
                                // I think newlines are whole tokens, but just in case the text contains some text too
                                const potentialPartBeforeNew = text.split("\n")[0]
                                if (potentialPartBeforeNew.length > 0) {
                                    onToken(potentialPartBeforeNew);
                                }
                                weDisposedOurselves = true;
                                throw new Error("STOP_GENERATION");
                            }
                        }
                    }
                    if (typeof data.max_characters === "number" && !isDisposed) {
                        const characterCount = accumulatedText.length;
                        if (characterCount >= data.max_characters) {
                                // let's find if our text is finally finishing a paragraph
                            if (text.indexOf('\n') !== -1) {
                                console.log("Max characters reached:", characterCount, "stopping completion at this paragraph end.");
                                const potentialPartBeforeNew = text.split("\n")[0]
                                if (potentialPartBeforeNew.length > 0) {
                                    onToken(potentialPartBeforeNew);
                                }
                                weDisposedOurselves = true;
                                throw new Error("STOP_GENERATION");
                            }
                        }
                    }
                    if (!isDisposed) {
                        onToken(text);
                    }
                } catch (e) {
                    if (!weDisposedOurselves) {
                        console.log("Error in onToken callback:", e.message);
                    }
                    throw e;
                }
            }
        });
        if (completion !== null && !isDisposed) {
            // Extremely buggy behavior in llama-cpp bindings, no documentation on this, have to do try-catch everywhere
            try {
                isDisposed = true;
                await completion.dispose();
            } catch {
            }
        }
        if (context !== null && !isContextDisposed) {
            // Extremely buggy behavior in llama-cpp bindings, no documentation on this, have to do try-catch everywhere
            try {
                isContextDisposed = true;
                await context.dispose();
            } catch {
            }
        }
        onDone();
    } catch (e) {
        if (completion !== null && !isDisposed) {
            try {
                isDisposed = true;
                await completion.dispose();
            } catch {
            }
        }
        if (context !== null && !isContextDisposed) {
            try {
                isContextDisposed = true;
                await context.dispose();
            } catch {
            }
            
        }
        
        if (weDisposedOurselves) {
            onDone();
        } else {
            console.log(e.message);
            onError(e);
        }
    }
}

wss.on('connection', (ws) => {
    console.log('Client connected');
    
    ws.on('message', async (message) => {
        try {
            const data = JSON.parse(message);
            
            // Handle different actions
            if (data.action === 'load_model') {
                try {
                    await load_model(data.model_path);
                    ws.send(JSON.stringify({ type: 'model_loaded' }));
                } catch (e) {
                    console.log(e.message);
                    ws.send(JSON.stringify({ type: 'error', message: e.message }));
                }
            } 
            else if (data.action === 'generate') {
                if (!MODEL) {
                    ws.send(JSON.stringify({ type: 'error', message: 'Model not loaded' }));
                    return;
                }

                await generateCompletion(data, (text) => {
                    ws.send(JSON.stringify({ type: 'token', text }));
                }, () => {
                    ws.send(JSON.stringify({ type: 'done' }));
                }, (error) => {
                    ws.send(JSON.stringify({ type: 'error', message: error.message }));
                });

            } else if (data.action === 'count_tokens') {
                if (!MODEL) {
                    ws.send(JSON.stringify({ type: 'error', message: 'Model not loaded' }));
                    return;
                }
                const text = data.text;
                const tokens = MODEL.tokenize(text);
                ws.send(JSON.stringify({ type: 'token_count', n_tokens: tokens.length }));
            }
        } catch (e) {
            console.log(e.message);
            ws.send(JSON.stringify({ type: 'error', message: e.message }));
        }
    });
    
    ws.on('close', () => {
        console.log('Client disconnected');
    });
});

process.on('exit', (code) => {
    console.log('Process exiting with code:', code);
});

process.on('uncaughtException', (err) => {
    console.error('Uncaught exception:', err);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled rejection at:', promise, 'reason:', reason);
});

console.log('WebSocket server listening on port 8000');

// test with test file
// (async () => {
//     await load_model('E:\\llama\\test.gguf');
//     const fs = require('fs');
//     fscontent = fs.readFileSync('E:\\test_remove.txt', 'utf-8');
//     console.log(fscontent);
//     if (!fscontent.endsWith('\n')) {
//         fscontent += '\n\n';
//     } else if (!fscontent.endsWith('\n\n')) {
//         fscontent += '\n';
//     }
//     generateCompletion({prompt: fscontent, max_tokens: 512,
//         temperature: 1.0,
//         topP: 0.8,
//         repeat_penalty: 1,
//         frequency_penalty: 0,
//         presence_penalty: 0,
//         stop: [],
//         maxTokens: 8192
//     }, (text) => {
//         process.stdout.write(text);
//     }, () => {
//         console.log('\nGeneration complete');
//     }, (error) => {
//         console.log('Error during generation:', error.message);
//     });
// })();