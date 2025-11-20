"""
Semantic Search for NLP to SQL with Caching
Uses embeddings to find similar queries and caches results in Valkey/Redis
"""

import json
import hashlib
import time
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import numpy as np

# Import Valkey/Redis
try:
    import valkey as redis
except ImportError:
    import redis

# Import embedding model
from sentence_transformers import SentenceTransformer

# Import the NLP to SQL converter
sys.path.append(str(Path(__file__).parent))
from nlp_to_sql import NLPToSQL


class SemanticSQLCache:
    """
    Semantic search cache for SQL queries using embeddings and Valkey/Redis
    
    Key structure:
    - semantic:prompt:<hash>  -> db:query:<hash2>  (maps prompt to query result key)
    - db:query:<hash2>        -> {sql, time_taken, tokens, etc.}  (NLP result)
    - db:cache:<hash2>        -> <actual query result>  (SQL execution result)
    - embedding:prompt:<hash> -> <embedding vector>  (prompt embedding)
    """
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        embedding_model: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.70,
        ollama_model: str = "tinyllama"
    ):
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=False  # We'll handle encoding ourselves
        )
        
        # Initialize embedding model
        print(f"Loading embedding model: {embedding_model}...")
        self.embedding_model = SentenceTransformer(embedding_model)
        self.vector_dim = self.embedding_model.get_sentence_embedding_dimension()
        print(f"✅ Embedding model loaded. Vector dimension: {self.vector_dim}")
        
        # Initialize NLP to SQL converter
        self.nlp_converter = NLPToSQL(model=ollama_model)
        
        # Similarity threshold for considering queries as "similar"
        self.similarity_threshold = similarity_threshold
        
        # Create vector search index if it doesn't exist
        self._create_index()
    
    def _create_index(self):
        """Create vector search index for prompt embeddings"""
        index_name = "prompt_embeddings"
        
        try:
            # Try to get index info
            self.redis_client.execute_command("FT.INFO", index_name)
            print(f"✅ Index '{index_name}' already exists")
        except redis.ResponseError:
            # Index doesn't exist, create it
            try:
                print(f"Creating vector search index '{index_name}'...")
                self.redis_client.execute_command(
                    "FT.CREATE", index_name,
                    "ON", "HASH",
                    "PREFIX", "1", "embedding:prompt:",
                    "SCHEMA",
                    "prompt", "TAG",
                    "query_key", "TAG",
                    "embedding", "VECTOR", "HNSW", "6",
                        "TYPE", "FLOAT32",
                        "DIM", str(self.vector_dim),
                        "DISTANCE_METRIC", "COSINE"
                )
                print(f"✅ Index '{index_name}' created successfully")
            except Exception as e:
                print(f"⚠️  Warning: Could not create vector search index: {e}")
                print(f"   Semantic search will fall back to exact matching only")
                print(f"   To enable vector search, ensure Redis Stack or Valkey with search module is installed")
    
    def _hash_text(self, text: str) -> str:
        """Generate SHA1 hash of text"""
        return hashlib.sha1(text.encode('utf-8')).hexdigest()
    
    def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding vector for text"""
        return self.embedding_model.encode(text, convert_to_numpy=True)
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def _search_similar_prompts(self, embedding: np.ndarray, k: int = 5) -> List[Dict]:
        """Search for similar prompts using vector search or fallback to brute force"""
        try:
            # Convert embedding to bytes
            embedding_bytes = embedding.astype(np.float32).tobytes()
            
            # Perform vector search
            results = self.redis_client.execute_command(
                "FT.SEARCH", "prompt_embeddings",
                f"*=>[KNN {k} @embedding $vec AS score]",
                "PARAMS", "2", "vec", embedding_bytes,
                "SORTBY", "score",
                "DIALECT", "2",
                "RETURN", "3", "prompt", "query_key", "score"
            )
            
            # Parse results
            similar_prompts = []
            if results and len(results) > 1:
                num_results = results[0]
                for i in range(1, len(results), 2):
                    if i + 1 < len(results):
                        doc_id = results[i].decode('utf-8') if isinstance(results[i], bytes) else results[i]
                        fields = results[i + 1]
                        
                        # Parse fields
                        prompt = None
                        query_key = None
                        score = None
                        
                        for j in range(0, len(fields), 2):
                            field_name = fields[j].decode('utf-8') if isinstance(fields[j], bytes) else fields[j]
                            field_value = fields[j + 1]
                            
                            if field_name == "prompt":
                                prompt = field_value.decode('utf-8') if isinstance(field_value, bytes) else field_value
                            elif field_name == "query_key":
                                query_key = field_value.decode('utf-8') if isinstance(field_value, bytes) else field_value
                            elif field_name == "score":
                                score = float(field_value.decode('utf-8') if isinstance(field_value, bytes) else field_value)
                        
                        if prompt and query_key and score is not None:
                            # Convert distance to similarity (1 - distance for cosine)
                            similarity = 1 - score
                            similar_prompts.append({
                                "prompt": prompt,
                                "query_key": query_key,
                                "similarity": similarity
                            })
            
            return similar_prompts
            
        except Exception as e:
            # Fallback to brute force search if vector search not available
            return self._brute_force_search(embedding, k)
    
    def _brute_force_search(self, embedding: np.ndarray, k: int = 5) -> List[Dict]:
        """Fallback: Brute force similarity search when vector search unavailable"""
        try:
            similar_prompts = []
            
            # Get all embedding keys
            embedding_keys = list(self.redis_client.scan_iter("embedding:prompt:*", count=100))
            
            if not embedding_keys:
                return []
            
            # Calculate similarity for each
            for key in embedding_keys:
                try:
                    data = self.redis_client.hgetall(key)
                    if not data:
                        continue
                    
                    stored_prompt = data.get(b'prompt', b'').decode('utf-8')
                    stored_query_key = data.get(b'query_key', b'').decode('utf-8')
                    stored_embedding_bytes = data.get(b'embedding')
                    
                    if stored_embedding_bytes and stored_prompt and stored_query_key:
                        # Convert bytes back to numpy array
                        stored_embedding = np.frombuffer(stored_embedding_bytes, dtype=np.float32)
                        
                        # Calculate cosine similarity
                        similarity = self._cosine_similarity(embedding, stored_embedding)
                        
                        similar_prompts.append({
                            "prompt": stored_prompt,
                            "query_key": stored_query_key,
                            "similarity": float(similarity)
                        })
                except Exception as e:
                    continue
            
            # Sort by similarity and return top k
            similar_prompts.sort(key=lambda x: x['similarity'], reverse=True)
            return similar_prompts[:k]
            
        except Exception as e:
            print(f"Warning: Brute force search failed: {e}")
            return []

    
    def get_or_generate_sql(self, prompt: str, verbose: bool = True) -> Dict[str, Any]:
        """
        Get SQL for a prompt, using cache if similar query exists
        
        Returns:
            Dict with keys: sql, time_taken, tokens, cache_hit, similar_prompt, etc.
        """
        start_time = time.time()
        
        # Generate hash and embedding for the prompt
        prompt_hash = self._hash_text(prompt)
        prompt_embedding = self._generate_embedding(prompt)
        
        # Check if we have an exact match first
        semantic_key = f"semantic:prompt:{prompt_hash}"
        cached_query_key = self.redis_client.get(semantic_key)
        
        if cached_query_key:
            cached_query_key = cached_query_key.decode('utf-8')
            if verbose:
                print(f"🎯 Exact cache hit for prompt")
            
            # Get the cached query result
            query_data = self.redis_client.get(cached_query_key)
            if query_data:
                result = json.loads(query_data.decode('utf-8'))
                result['cache_hit'] = True
                result['cache_type'] = 'exact'
                result['lookup_time'] = round(time.time() - start_time, 3)
                return result
        
        # Search for similar prompts
        if verbose:
            print(f"🔍 Searching for similar prompts...")
        
        similar_prompts = self._search_similar_prompts(prompt_embedding, k=5)
        
        # Check if any similar prompt meets the threshold
        for similar in similar_prompts:
            if similar['similarity'] >= self.similarity_threshold:
                if verbose:
                    print(f"✨ Found similar prompt (similarity: {similar['similarity']:.3f})")
                    print(f"   Original: {similar['prompt']}")
                    print(f"   Current:  {prompt}")
                
                # Get the cached query result
                query_data = self.redis_client.get(similar['query_key'])
                if query_data:
                    result = json.loads(query_data.decode('utf-8'))
                    result['cache_hit'] = True
                    result['cache_type'] = 'semantic'
                    result['similarity'] = similar['similarity']
                    result['similar_prompt'] = similar['prompt']
                    result['lookup_time'] = round(time.time() - start_time, 3)
                    
                    # Also cache this exact prompt for future exact matches
                    self.redis_client.set(semantic_key, similar['query_key'])
                    
                    return result
        
        # No similar prompt found, generate new SQL
        if verbose:
            print(f"🤖 No similar prompt found. Generating new SQL with LLM...")
        
        result = self.nlp_converter.generate_sql(prompt)
        result['cache_hit'] = False
        result['lookup_time'] = round(time.time() - start_time, 3)
        
        # Cache the result
        sql_hash = self._hash_text(result['sql'])
        query_key = f"db:query:{sql_hash}"
        
        # Store the query result
        self.redis_client.set(query_key, json.dumps(result))
        
        # Store the semantic mapping
        self.redis_client.set(semantic_key, query_key)
        
        # Store the embedding for vector search
        embedding_key = f"embedding:prompt:{prompt_hash}"
        self.redis_client.hset(
            embedding_key,
            mapping={
                "prompt": prompt,
                "query_key": query_key,
                "embedding": prompt_embedding.astype(np.float32).tobytes()
            }
        )
        
        if verbose:
            print(f"💾 Cached result for future queries")
        
        return result
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        stats = {
            "total_prompts": len(self.redis_client.keys("semantic:prompt:*")),
            "total_queries": len(self.redis_client.keys("db:query:*")),
            "total_embeddings": len(self.redis_client.keys("embedding:prompt:*")),
        }
        return stats
    
    def clear_cache(self):
        """Clear all cached data"""
        print("Clearing cache...")
        
        # Delete all semantic keys
        for key in self.redis_client.scan_iter("semantic:prompt:*"):
            self.redis_client.delete(key)
        
        for key in self.redis_client.scan_iter("db:query:*"):
            self.redis_client.delete(key)
        
        for key in self.redis_client.scan_iter("embedding:prompt:*"):
            self.redis_client.delete(key)
        
        print("✅ Cache cleared")


def demo_mode(cache: SemanticSQLCache):
    """Run demo with test queries including similar ones"""
    print("\n" + "=" * 70)
    print("SEMANTIC SEARCH DEMO - Testing cache with similar queries")
    print("=" * 70 + "\n")
    
    test_queries = [
        # First query - will generate SQL
        "Flight manifest - all passengers on a specific flight 115",
        
        # Similar query - should hit semantic cache
        "Give me the passenger details from flight 115",
        
        # Another similar query
        "Show me all passengers on flight 115",
        
        # Different query
        "Get airport with geographic details by IATA code JFK",
        
        # Similar to previous
        "Show me airport information for JFK including location",
        
        # New query
        "How many bookings does passenger 1000 have?",
        
        # Exact repeat - should hit exact cache
        "How many bookings does passenger 1000 have?",
    ]
    
    total_time = 0
    cache_hits = 0
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: {query}")
        print("-" * 70)
        
        result = cache.get_or_generate_sql(query)
        
        print(f"\nGenerated SQL:\n{result['sql']};")
        
        # Display stats
        if result['cache_hit']:
            cache_hits += 1
            cache_type = result.get('cache_type', 'unknown')
            if cache_type == 'semantic':
                print(f"\n✨ SEMANTIC CACHE HIT (similarity: {result.get('similarity', 0):.3f})")
                print(f"   Similar to: {result.get('similar_prompt', 'N/A')}")
            else:
                print(f"\n🎯 EXACT CACHE HIT")
            print(f"   ⚡ Lookup time: {result['lookup_time']}s (saved ~{result.get('time_taken', 0)}s)")
        else:
            print(f"\n🤖 NEW QUERY - Generated by LLM")
            print(f"   ⏱️  Generation time: {result['time_taken']}s")
            print(f"   🔢 Tokens: {result['total_tokens']}")
        
        total_time += result.get('time_taken', 0) if not result['cache_hit'] else 0
        print()
    
    # Summary
    print("\n" + "=" * 70)
    print(f"📈 SUMMARY:")
    print(f"   Total queries: {len(test_queries)}")
    print(f"   Cache hits: {cache_hits} ({cache_hits/len(test_queries)*100:.1f}%)")
    print(f"   New generations: {len(test_queries) - cache_hits}")
    print(f"   Total LLM time: {total_time:.2f}s")
    print(f"   Average per new query: {total_time/(len(test_queries) - cache_hits):.2f}s" if cache_hits < len(test_queries) else "   N/A")
    
    # Cache stats
    stats = cache.get_cache_stats()
    print(f"\n📊 CACHE STATS:")
    print(f"   Cached prompts: {stats['total_prompts']}")
    print(f"   Cached queries: {stats['total_queries']}")
    print(f"   Embeddings stored: {stats['total_embeddings']}")
    print("=" * 70)


def interactive_mode(cache: SemanticSQLCache):
    """Run in interactive mode"""
    print("\n" + "=" * 70)
    print("INTERACTIVE MODE - Semantic Search SQL Cache")
    print("=" * 70)
    print("Enter your natural language queries (or 'quit' to exit)")
    print("Commands: 'stats' for cache stats, 'clear' to clear cache")
    print("=" * 70 + "\n")
    
    while True:
        try:
            query = input("\nYour query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if query.lower() == 'stats':
                stats = cache.get_cache_stats()
                print(f"\n📊 Cache Statistics:")
                print(f"   Cached prompts: {stats['total_prompts']}")
                print(f"   Cached queries: {stats['total_queries']}")
                print(f"   Embeddings: {stats['total_embeddings']}")
                continue
            
            if query.lower() == 'clear':
                cache.clear_cache()
                continue
            
            if not query:
                continue
            
            result = cache.get_or_generate_sql(query)
            
            print(f"\nGenerated SQL:\n{result['sql']};")
            
            if result['cache_hit']:
                cache_type = result.get('cache_type', 'unknown')
                if cache_type == 'semantic':
                    print(f"\n✨ Semantic cache hit (similarity: {result.get('similarity', 0):.3f})")
                else:
                    print(f"\n🎯 Exact cache hit")
                print(f"⚡ Lookup time: {result['lookup_time']}s")
            else:
                print(f"\n🤖 New query generated")
                print(f"⏱️  Time: {result['time_taken']}s | 🔢 Tokens: {result['total_tokens']}")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    """Main entry point"""
    print("=" * 70)
    print("Semantic Search SQL Cache with Vector Similarity")
    print("=" * 70)
    
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description="Semantic SQL cache with embeddings")
    parser.add_argument('--host', default='localhost', help='Redis/Valkey host')
    parser.add_argument('--port', type=int, default=6379, help='Redis/Valkey port')
    parser.add_argument('--model', default='tinyllama', help='Ollama model for SQL generation')
    parser.add_argument('--threshold', type=float, default=0.70, help='Similarity threshold (0-1)')
    parser.add_argument('--mode', choices=['demo', 'interactive'], default='demo', help='Run mode')
    parser.add_argument('--clear', action='store_true', help='Clear cache before starting')
    
    args = parser.parse_args()
    
    # Initialize cache
    try:
        cache = SemanticSQLCache(
            redis_host=args.host,
            redis_port=args.port,
            ollama_model=args.model,
            similarity_threshold=args.threshold
        )
        
        if args.clear:
            cache.clear_cache()
        
    except Exception as e:
        print(f"Error initializing cache: {e}")
        return
    
    # Run mode
    if args.mode == 'interactive':
        interactive_mode(cache)
    else:
        demo_mode(cache)


if __name__ == "__main__":
    main()
