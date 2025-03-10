"""
LLM module for OllamaSonar.
Handles interactions with the language model for summarization and synthesis.
"""

import time
import re
import requests
from urllib.parse import urlparse
from langchain_ollama import OllamaLLM
import sys
import os
import asyncio

class LLMProcessor:
    """Processor for LLM operations like summarization and synthesis."""
    
    def __init__(self, model="gemma2:2b"):
        # Check if Ollama is running and model is available
        self._check_ollama_model(model)
        self.model_name = model
        self.llm = OllamaLLM(model=model)
        
    def _check_ollama_model(self, model):
        """Check if Ollama is running and the model is available"""
        try:
            # Check if Ollama is running
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code != 200:
                print(f"❌ Error: Ollama server is not responding properly. Status code: {response.status_code}")
                print("Please make sure Ollama is running with 'ollama serve'")
                return False
                
            # Check if the model is available
            models = response.json()
            model_available = any(m.get('name') == model for m in models)
            
            if not model_available:
                print(f"⚠️ Warning: Model '{model}' is not available in Ollama.")
                print(f"Attempting to pull model '{model}'...")
                
                # Try to pull the model
                pull_response = requests.post(
                    "http://localhost:11434/api/pull",
                    json={"name": model},
                    timeout=10
                )
                
                if pull_response.status_code != 200:
                    print(f"❌ Error: Failed to pull model '{model}'. Please pull it manually with 'ollama pull {model}'")
                    return False
                else:
                    print(f"✅ Successfully pulled model '{model}'")
            
            return True
            
        except requests.exceptions.ConnectionError:
            print("❌ Error: Cannot connect to Ollama server at http://localhost:11434")
            print("Please make sure Ollama is running with 'ollama serve'")
            return False
        except Exception as e:
            print(f"❌ Error checking Ollama model: {str(e)}")
            return False
        
    def summarize_source(self, source_data):
        """Summarize a single source using chain of thought reasoning."""
        try:
            date_info = f"Published: {source_data.get('date', 'Unknown date')}" if source_data.get('date') else ""
            retrieved = f"Retrieved: {source_data.get('timestamp', 'Unknown time')}"
            domain = source_data.get('domain', urlparse(source_data['url']).netloc)
            
            prompt = f"""
You are an analytical research assistant. Think step-by-step about the content before extracting the most important information.

Source: {source_data['title']} ({source_data['url']})
Domain: {domain}
{date_info}
{retrieved}

Content:
{source_data['content']}

Follow this chain of thought process:

Step 1: Identify the main topic and key entities in this content. Justify why they are important.
Step 2: Determine the timeframe of the information (how recent is it?). Explain its relevance.
Step 3: Extract the most significant facts, figures, and quantitative data.
Step 4: Evaluate the reliability of this information source. Rank it on a scale from 1-5 (1 = low credibility, 5 = high credibility).
Step 5: Connect different pieces of information to form a coherent understanding.

After completing your analysis, provide:
1. Your chain of thought reasoning (start with "REASONING:").
2. A concise summary with 4-5 bullet points (start with "SUMMARY:") with:
   - Newest and most relevant information
   - Significant facts and figures
   - Maximum 3 lines per bullet point
   - Prioritized quantitative data and specific details
   - Source credibility ranking (from Step 4)

Ensure clarity and conciseness.
            """
            response = self.llm.invoke(prompt)
            
            # Extract structured output using regex
            reasoning_match = re.search(r"REASONING:(.*?)(?=SUMMARY:|$)", response, re.DOTALL)
            summary_match = re.search(r"SUMMARY:(.*)", response, re.DOTALL)
            
            reasoning = reasoning_match.group(1).strip() if reasoning_match else "No detailed reasoning provided."
            summary = summary_match.group(1).strip() if summary_match else response  # Fallback: use full response

            return {
                "url": source_data['url'],
                "title": source_data['title'],
                "date": source_data.get('date', 'Unknown date'),
                "domain": domain,
                "retrieved": source_data.get('timestamp', 'Unknown time'),
                "reasoning": reasoning,
                "summary": summary
            }
        except Exception as e:
            print(f"❌ Error summarizing source: {str(e)}")
            # Return a minimal result to avoid breaking the pipeline
            return {
                "url": source_data.get('url', 'Unknown URL'),
                "title": source_data.get('title', 'Unknown Title'),
                "date": source_data.get('date', 'Unknown date'),
                "domain": source_data.get('domain', 'Unknown domain'),
                "retrieved": source_data.get('timestamp', 'Unknown time'),
                "reasoning": f"Error processing this source: {str(e)}",
                "summary": "This source could not be processed due to an error."
            }

    def synthesize_information(self, query, source_summaries):
        """Synthesize information using chain of thought reasoning."""
        try:
            # Include both reasoning and summary from each source
            sources_text = "\n\n".join([
                f"Source {idx+1}: {s['title']} (Credibility: {self.extract_credibility_score(s.get('reasoning', ''))})\n{s.get('reasoning', s['summary'])}"
                for idx, s in enumerate(source_summaries)
            ])
            
            prompt = f"""
You are a research synthesizer using chain of thought reasoning. Analyze multiple sources to create a comprehensive understanding.

Query: {query}
Time: {time.strftime("%Y-%m-%d %H:%M:%S")}

Source Summaries:
{sources_text}

Follow this chain of thought process:

Step 1: Identify common themes and patterns across all sources. Justify why these themes are relevant.
Step 2: Note any contradictions or inconsistencies between sources. Explain their impact.
Step 3: Evaluate the reliability and recency of each source. Rank them (1 = low, 5 = high) and explain why.
Step 4: Connect related information across sources to generate deeper insights.
Step 5: Identify gaps in the information that might affect conclusions.
Step 6: Determine the most important findings that directly answer the query.

After completing your analysis, provide:
1. Your chain of thought reasoning (start with "REASONING:").
2. A concise answer to the query (start with "ANSWER:") with:
   - Key Finding (1-2 sentences)
   - Supporting Points (3-4 bullet points)
   - Bottom Line (1 sentence)

Keep the final answer under 250 words. Focus only on the most recent and relevant information.
            """
            response = self.llm.invoke(prompt)

            # Extract structured output using regex
            reasoning_match = re.search(r"REASONING:(.*?)(?=ANSWER:|$)", response, re.DOTALL)
            answer_match = re.search(r"ANSWER:(.*)", response, re.DOTALL)
            
            reasoning = reasoning_match.group(1).strip() if reasoning_match else "No detailed reasoning provided."
            answer = answer_match.group(1).strip() if answer_match else response  # Fallback: use full response

            return {
                "query": query,
                "reasoning": reasoning,
                "answer": answer
            }
        except Exception as e:
            print(f"❌ Error synthesizing information: {str(e)}")
            # Return a minimal result to avoid breaking the pipeline
            return {
                "query": query,
                "reasoning": f"Error synthesizing information: {str(e)}",
                "answer": f"I apologize, but I encountered an error while processing the research results. The error was: {str(e)}. Please try again or modify your query."
            }

    def extract_credibility_score(self, reasoning_text):
        """Extracts and returns the credibility score from the reasoning text."""
        try:
            # Look for explicit credibility score mentions
            score_patterns = [
                r"credibility.*?(\d+)/5",
                r"credibility.*?(\d+) out of 5",
                r"rank.*?(\d+)/5",
                r"rank.*?(\d+) out of 5",
                r"score.*?(\d+)/5",
                r"score.*?(\d+) out of 5",
                r"reliability.*?(\d+)/5",
                r"reliability.*?(\d+) out of 5"
            ]
            
            for pattern in score_patterns:
                match = re.search(pattern, reasoning_text.lower())
                if match:
                    return match.group(1)
            
            # If no explicit score, look for the evaluation statement
            match = re.search(r"Step 4:.*?(\d+)[\s\.]", reasoning_text)
            if match:
                return match.group(1)
                
            return "3"  # Default to middle score if no score found
        except Exception:
            return "3"  # Default to middle score on error

    # Add this method to process multiple prompts concurrently
    async def process_multiple_prompts(self, prompts_list):
        """Process multiple prompts concurrently"""
        tasks = []
        for prompt in prompts_list:
            tasks.append(self.process_prompt_async(prompt))
        
        return await asyncio.gather(*tasks)

    # Add an async version of process_prompt
    async def process_prompt_async(self, prompt):
        """Process a prompt asynchronously"""
        # Create a wrapper for the synchronous method
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.process_prompt, prompt)
