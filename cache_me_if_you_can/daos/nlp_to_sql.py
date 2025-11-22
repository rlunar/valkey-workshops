"""
Natural Language to SQL Query Generator
Uses Ollama with knowledge base context
"""

import json
import os
from pathlib import Path
import requests
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class NLPToSQL:
    def __init__(self, knowledge_base_path: str = None, model: str = None):
        # Use environment variables with fallbacks
        if knowledge_base_path is None:
            knowledge_base_path = os.getenv("KNOWLEDGE_BASE_PATH", "../knowledge_base")
        if model is None:
            model = os.getenv("OLLAMA_MODEL", "codellama")
        
        self.kb_path = Path(knowledge_base_path)
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.model = model
        self.context = self._load_knowledge_base()
        print(f"Loaded knowledge base from: {self.kb_path.absolute()}")
        print(f"Using model: {self.model}\n")
    
    def _load_knowledge_base(self) -> str:
        """Load and format knowledge base files into context string"""
        context_parts = []
        
        # Load overview
        overview_file = self.kb_path / "database_schema_overview.json"
        if overview_file.exists():
            with open(overview_file, 'r') as f:
                overview = json.load(f)
                context_parts.append("=== DATABASE OVERVIEW ===")
                context_parts.append(f"Database: {overview.get('database_name', 'N/A')}")
                context_parts.append(f"Description: {overview.get('description', 'N/A')}")
                
                # Add table summaries
                context_parts.append("\nTABLES:")
                for table in overview.get('tables', []):
                    context_parts.append(f"- {table['name']}: {table['description']}")
        
        # Load key table schemas
        important_tables = ['airport', 'flight', 'passenger', 'booking', 'airline']
        context_parts.append("\n=== KEY TABLE SCHEMAS ===")
        for table_name in important_tables:
            table_file = self.kb_path / f"{table_name}.json"
            if table_file.exists():
                with open(table_file, 'r') as f:
                    table_data = json.load(f)
                    context_parts.append(f"\n{table_name.upper()}:")
                    context_parts.append(f"Columns: {', '.join([col['name'] for col in table_data.get('columns', [])])}")
                    if table_data.get('foreign_keys'):
                        fk_list = [f"{fk['column']} -> {fk['references_table']}" for fk in table_data['foreign_keys']]
                        context_parts.append(f"Foreign Keys: {', '.join(fk_list)}")
        
        # Load NL to SQL guide (compact version)
        guide_file = self.kb_path / "nl_to_sql_guide.json"
        if guide_file.exists():
            with open(guide_file, 'r') as f:
                guide = json.load(f)
                context_parts.append("\n=== CONVERSION RULES ===")
                
                # Add join patterns
                if 'common_join_patterns' in guide:
                    context_parts.append("\nCommon Joins:")
                    for pattern_name, pattern in guide['common_join_patterns'].items():
                        context_parts.append(f"- {pattern_name}: {pattern['description']}")
                
                # Add important notes
                if 'important_notes' in guide:
                    context_parts.append("\nImportant Notes:")
                    if 'reserved_keywords' in guide['important_notes']:
                        context_parts.append(f"- {guide['important_notes']['reserved_keywords']['note']}")
        
        # Load examples (first 10 only to save context)
        examples_file = self.kb_path / "nl_sql_examples.json"
        if examples_file.exists():
            with open(examples_file, 'r') as f:
                examples_data = json.load(f)
                context_parts.append("\n=== EXAMPLE QUERIES ===")
                for example in examples_data.get('examples', [])[:10]:
                    context_parts.append(f"\nQ: {example['prompt']}")
                    context_parts.append(f"SQL: {example['sql']}")
        
        return "\n".join(context_parts)
    
    def _build_prompt(self, natural_language_query: str) -> str:
        """Build the prompt for the LLM"""
        prompt = f"""You are a SQL query generator for the Flughafen airport database.

{self.context}

IMPORTANT RULES:
1. Use backticks for reserved keywords: `from`, `to`
2. Use table aliases: a (airport), f (flight), p (passenger), b (booking), al (airline)
3. Use LEFT JOIN for optional relationships (airport_geo, passengerdetails)
4. Use INNER JOIN for required relationships
5. Always add LIMIT clause for queries that might return many rows
6. Return ONLY the SQL query, no explanations

Natural Language Query: {natural_language_query}

SQL Query:"""
        return prompt
    
    def generate_sql(self, natural_language_query: str) -> dict:
        """Generate SQL from natural language using Ollama
        
        Returns:
            dict with keys: sql, tokens, time_taken, eval_count, prompt_eval_count
        """
        prompt = self._build_prompt(natural_language_query)
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "top_k": 40
            }
        }
        
        try:
            start_time = time.time()
            response = requests.post(self.ollama_url, json=payload, timeout=120)
            response.raise_for_status()
            end_time = time.time()
            
            result = response.json()
            sql_query = result.get("response", "").strip()
            
            # Clean up the response
            sql_query = self._clean_sql(sql_query)
            
            # Extract token and timing information
            return {
                "sql": sql_query,
                "time_taken": round(end_time - start_time, 2),
                "prompt_eval_count": result.get("prompt_eval_count", 0),
                "eval_count": result.get("eval_count", 0),
                "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
                "eval_duration_ms": result.get("eval_duration", 0) / 1_000_000,  # Convert to ms
                "prompt_eval_duration_ms": result.get("prompt_eval_duration", 0) / 1_000_000,
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "sql": f"Error connecting to Ollama: {e}",
                "time_taken": 0,
                "prompt_eval_count": 0,
                "eval_count": 0,
                "total_tokens": 0,
                "eval_duration_ms": 0,
                "prompt_eval_duration_ms": 0,
            }
    
    def _clean_sql(self, sql: str) -> str:
        """Clean up generated SQL query"""
        # Remove markdown code blocks if present
        sql = sql.replace("```sql", "").replace("```", "")
        
        # Remove common prefixes
        prefixes = ["SQL Query:", "Query:", "SQL:"]
        for prefix in prefixes:
            if sql.startswith(prefix):
                sql = sql[len(prefix):].strip()
        
        # Remove trailing semicolon if present (we'll add it back)
        sql = sql.rstrip(";").strip()
        
        return sql


def interactive_mode(converter: NLPToSQL):
    """Run in interactive mode"""
    print("\n" + "=" * 60)
    print("INTERACTIVE MODE")
    print("=" * 60)
    print("Enter your natural language queries (or 'quit' to exit)")
    print("=" * 60 + "\n")
    
    while True:
        try:
            query = input("\nYour query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not query:
                continue
            
            print("\nGenerating SQL...")
            result = converter.generate_sql(query)
            
            print(f"\nGenerated SQL:\n{result['sql']};")
            print(f"\n📊 Stats:")
            print(f"   ⏱️  Time: {result['time_taken']}s")
            print(f"   🔢 Tokens: {result['total_tokens']} (prompt: {result['prompt_eval_count']}, response: {result['eval_count']})")
            print(f"   ⚡ Speed: {result['eval_count'] / result['time_taken']:.1f} tokens/s" if result['time_taken'] > 0 else "")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


def demo_mode(converter: NLPToSQL):
    """Run demo with test queries"""
    print("\n" + "=" * 60)
    print("DEMO MODE - Running test queries")
    print("=" * 60 + "\n")
    
    test_queries = [
        "Get airport with geographic details by IATA code JFK",
        "Show me all flights from JFK to LAX",
        "Find 10 passengers from United States",
        "How many bookings does passenger 1000 have?",
        "Flight manifest - all passengers on a specific flight 115",
    ]
    
    total_time = 0
    total_tokens = 0
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Natural Language: {query}")
        print("-" * 60)
        
        result = converter.generate_sql(query)
        print(f"Generated SQL:\n{result['sql']};")
        print(f"\n📊 Stats: ⏱️  {result['time_taken']}s | 🔢 {result['total_tokens']} tokens | ⚡ {result['eval_count'] / result['time_taken']:.1f} tokens/s")
        
        total_time += result['time_taken']
        total_tokens += result['total_tokens']
        print()
    
    print("\n" + "=" * 60)
    print(f"📈 SUMMARY: {len(test_queries)} queries in {total_time:.2f}s | {total_tokens} total tokens")
    print("=" * 60)


def main():
    """Main entry point"""
    print("=" * 60)
    print("Natural Language to SQL Query Generator")
    print("=" * 60)
    
    # Check for model argument
    model = "tinyllama"
    if len(sys.argv) > 1:
        model = sys.argv[1]
    
    # Initialize converter
    try:
        converter = NLPToSQL(model=model)
    except Exception as e:
        print(f"Error initializing converter: {e}")
        return
    
    # Check mode
    if len(sys.argv) > 2 and sys.argv[2] == "interactive":
        interactive_mode(converter)
    else:
        demo_mode(converter)
        
        # Offer interactive mode
        print("\n" + "=" * 60)
        response = input("Would you like to try interactive mode? (y/n): ").strip().lower()
        if response == 'y':
            interactive_mode(converter)


if __name__ == "__main__":
    main()
