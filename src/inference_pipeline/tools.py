"""
Tools for the Second Brain AI Assistant Agent.
Implements the three core tools: retriever, summarization, and help.
"""

from typing import Dict, Any, Optional
from langchain.tools import BaseTool
from pydantic import Field

from src.inference_pipeline.rag_engine import RAGEngine
from src.inference_pipeline.openai_service import OpenAIService
from src.utils.logger import LoggerMixin


class RetrieverTool(BaseTool, LoggerMixin):
    """Tool for retrieving information from the knowledge base using RAG."""
    
    name: str = "knowledge_base_search"
    description: str = """Use this tool to search for information in the user's knowledge base.
    Input should be a search query or question about the content.
    This tool performs semantic search and returns relevant information with sources."""
    
    rag_engine: RAGEngine = Field(default_factory=RAGEngine)
    
    class Config:
        arbitrary_types_allowed = True
    
    async def _arun(self, query: str) -> str:
        """Async implementation of the tool."""
        try:
            # Ensure RAG engine is set up
            if self.rag_engine.vector_store is None:
                await self.rag_engine.setup()
            
            # Process the query - now returns QueryResponse object
            result = await self.rag_engine.process_query(query)
            
            # Extract response from QueryResponse object
            response = result.response
            
            # Format sources from the new structure with URLs prominently displayed
            if result.sources:
                sources_with_urls = []
                for source in result.sources[:3]:  # Show top 3 sources
                    source_line = f"- **{source.title}**"
                    
                    # Add source type and document type
                    if hasattr(source, 'source_type') and hasattr(source, 'document_type'):
                        source_line += f" [{source.source_type.value}/{source.document_type.value}]"
                    
                    # Add URL prominently if available
                    if source.url:
                        source_line += f"\n  🔗 {str(source.url)}"
                    
                    # Add search strategies used
                    if hasattr(source, 'strategies_used') and source.strategies_used:
                        strategies = ", ".join(source.strategies_used)
                        source_line += f"\n  📊 Found via: {strategies}"
                    
                    sources_with_urls.append(source_line)
                
                # Add confidence score if available
                confidence_info = f" (Confidence: {result.confidence_score:.2f})" if result.confidence_score else ""
                
                # Add search strategy used
                strategy_info = f" via {result.search_strategy}" if result.search_strategy else ""
                
                response += f"\n\n📚 **Sources{confidence_info}{strategy_info}:**\n" + "\n\n".join(sources_with_urls)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error in retriever tool: {str(e)}")
            return f"Sorry, I encountered an error while searching: {str(e)}"
    
    def _run(self, query: str) -> str:
        """Sync wrapper - not implemented for async tool."""
        raise NotImplementedError("This tool only supports async operation")


class SummarizationTool(BaseTool, LoggerMixin):
    """Tool for summarizing content using OpenAI."""
    
    name: str = "summarize_content"
    description: str = """Use this tool to summarize long content or multiple documents.
    Input should be the text content you want to summarize.
    This tool creates concise summaries focusing on key points."""
    
    openai_service: OpenAIService = Field(default_factory=OpenAIService)
    
    class Config:
        arbitrary_types_allowed = True
    
    async def _arun(self, content: str) -> str:
        """Async implementation of the tool."""
        try:
            # Create summarization prompt
            prompt = f"""Please provide a concise summary of the following content, focusing on the key points and main ideas:

{content}

Summary:"""

            # Generate summary using OpenAI
            result = self.openai_service.generate_response(
                prompt=prompt,
                system_message="You are a helpful assistant that creates clear, concise summaries.",
                temperature=0.3,  # Lower temperature for more focused summaries
                max_tokens=500    # Limit summary length
            )
            
            return result["response"]
            
        except Exception as e:
            self.logger.error(f"Error in summarization tool: {str(e)}")
            return f"Sorry, I couldn't summarize the content: {str(e)}"
    
    def _run(self, content: str) -> str:
        """Sync wrapper - not implemented for async tool."""
        raise NotImplementedError("This tool only supports async operation")