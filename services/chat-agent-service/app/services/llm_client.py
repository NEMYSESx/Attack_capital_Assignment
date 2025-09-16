import logging
from typing import List, Dict, Any, Optional
from app.config.settings import settings
from groq import AsyncGroq

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.LLM_MODEL
        self.temperature = settings.TEMPERATURE
        self.max_context_length = settings.MAX_CONTEXT_LENGTH
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: Optional[str] = None,
        context: Optional[str] = None
    ) -> str:
        try:
            conversation = []
            
            if system_prompt:
                conversation.append({"role": "system", "content": system_prompt})
            
            if context:
                conversation.append({
                    "role": "system", 
                    "content": f"Relevant context from previous conversations:\n{context}"
                })
            
            conversation.extend(messages)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=conversation,
                temperature=self.temperature,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            logger.info(f"Generated LLM response with {len(content)} characters")
            
            return content
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            raise
    
    async def generate_context_summary(self, memories: List[Dict[str, Any]]) -> str:
        try:
            if not memories:
                return ""
            
            memory_texts = []
            for memory in memories:
                if isinstance(memory, dict):
                    text = memory.get('text', memory.get('message', ''))
                    if text:
                        memory_texts.append(text)
                else:
                    memory_texts.append(str(memory))
            
            if not memory_texts:
                return ""
            
            memories_content = "\n".join(memory_texts[:10])  
            
            summarization_prompt = f"""
            Please create a concise summary of the following previous conversation context that would be helpful for continuing a conversation:

            Previous conversations:
            {memories_content}

            Summary:
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": summarization_prompt}],
                temperature=0.3,
                max_tokens=300
            )
            
            summary = response.choices[0].message.content
            logger.info(f"Generated context summary with {len(summary)} characters")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating context summary: {str(e)}")
            return ""
    
    def get_system_prompt(self, agent_name: str = None) -> str:
        agent_name = agent_name or settings.AGENT_NAME
        
        return f"""You are {agent_name}, a helpful AI assistant participating in a real-time chat room. 

Key instructions:
- You have access to context from previous conversations with users
- Be conversational, friendly, and engaging
- Remember and reference previous interactions when relevant
- Keep responses concise but informative (1-3 sentences typically)
- Ask follow-up questions to maintain engagement
- If you don't have context about a user, treat them warmly as a new friend
- Adapt your personality to match the conversation tone
- Be helpful with questions and provide value in every interaction

Remember: This is a real-time chat environment, so keep responses natural and conversational."""