async function startAgentStream() {
    const response = await fetch('http://localhost:3000/api/store/ai-search-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: "I want to learn about LangChain agents" })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunkText = decoder.decode(value);
        
        // Parse out the SSE 'data: ' prefix
        const lines = chunkText.split('\n');
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const dataStr = line.replace('data: ', '').trim();
                if (dataStr === '[DONE]') {
                    console.log("Agent has finished execution.");
                    return;
                }
                
                try {
                    const agentStep = JSON.parse(dataStr);
                    
                    // Here is where you capture everything the agent goes through:
                    if (agentStep.status === 'thinking') {
                        console.log(`Agent Thought: ${agentStep.message}`);
                    } else if (agentStep.status === 'tool_call') {
                        console.log(`Tool Triggered: [${agentStep.tool}] -> ${agentStep.message}`);
                    } else if (agentStep.status === 'text') {
                        process.stdout.write(agentStep.chunk); // Renders the final answer chunk by chunk
                    }
                } catch (e) {
                    // Handle incomplete line splits if chunks got mashed together
                }
            }
        }
    }
}