"""
Semantic Search for NLP to SQL with Caching
Uses embeddings to find similar queries and caches results in Valkey/Redis
"""

import json
import hashlib
import time
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Valkey/Redis
try:
    import valkey
except ImportError:
    import redis as valkey

# Import embedding model
from sentence_transformers import SentenceTransformer

# Add parent directory to path to import from daos
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the Semantic SQL Cache
from daos.semantic_cache import SemanticSQLCache


def demo_mode(cache: SemanticSQLCache, verbose: bool = False):
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
        print(f"\n{'='*70}")
        print(f"Query #{i}: {query}")
        print('='*70)
        
        # Generate hash for this prompt
        prompt_hash = cache._hash_text(query)
        
        if verbose:
            print(f"\n🔑 Key Information:")
            print(f"   Prompt hash: {prompt_hash[:16]}...")
            print(f"   Semantic key: semantic:prompt:{prompt_hash[:16]}...")
            print(f"   Embedding key: embedding:prompt:{prompt_hash[:16]}...")
        
        result = cache.get_or_generate_sql(query, verbose=False)
        
        # Display cache hit/miss reason
        print(f"\n{'─'*70}")
        if result['cache_hit']:
            cache_hits += 1
            cache_type = result.get('cache_type', 'unknown')
            
            if cache_type == 'semantic':
                similarity = result.get('similarity', 0)
                similar_prompt = result.get('similar_prompt', 'N/A')
                
                print(f"✨ SEMANTIC CACHE HIT")
                print(f"{'─'*70}")
                print(f"   Reason: Found similar query in cache")
                print(f"   Similarity score: {similarity:.4f} (threshold: {cache.similarity_threshold})")
                print(f"   Match quality: {'Excellent' if similarity > 0.9 else 'Good' if similarity > 0.8 else 'Acceptable'}")
                
                if verbose:
                    # Show embedding comparison
                    current_embedding = cache._generate_embedding(query)
                    similar_embedding = cache._generate_embedding(similar_prompt)
                    print(f"\n   📊 Embedding Details:")
                    print(f"      Current embedding: [{', '.join([f'{x:.3f}' for x in current_embedding[:5]])}...]")
                    print(f"      Similar embedding: [{', '.join([f'{x:.3f}' for x in similar_embedding[:5]])}...]")
                    print(f"      Vector dimension: {len(current_embedding)}")
                    print(f"      Cosine similarity: {similarity:.4f}")
                
                print(f"\n   📝 Matched Query:")
                print(f"      Original: \"{similar_prompt}\"")
                print(f"      Current:  \"{query}\"")
                
                print(f"\n   ⚡ Performance:")
                print(f"      Lookup time: {result['lookup_time']:.3f}s")
                print(f"      Saved ~{result.get('time_taken', 0):.1f}s of LLM generation")
                
            else:  # exact match
                print(f"🎯 EXACT CACHE HIT")
                print(f"{'─'*70}")
                print(f"   Reason: Exact same query seen before")
                print(f"   Match type: Hash-based exact match")
                print(f"   Lookup time: {result['lookup_time']:.3f}s (instant)")
                
                if verbose:
                    print(f"\n   🔑 Cache Keys:")
                    semantic_key = f"semantic:prompt:{prompt_hash}"
                    print(f"      Semantic key: {semantic_key[:40]}...")
                    cached_query_key = cache.valkey_client.get(semantic_key)
                    if cached_query_key:
                        print(f"      Query key: {cached_query_key.decode('utf-8')[:40]}...")
        else:
            print(f"🤖 CACHE MISS - New Query")
            print(f"{'─'*70}")
            print(f"   Reason: No similar queries found in cache")
            print(f"   Similarity threshold: {cache.similarity_threshold}")
            print(f"   Action: Generating SQL with LLM ({result.get('model', 'unknown')} model)")
            
            print(f"\n   ⏱️  Generation Stats:")
            print(f"      Time taken: {result['time_taken']:.2f}s")
            print(f"      Tokens used: {result['total_tokens']}")
            print(f"      Prompt tokens: {result.get('prompt_tokens', 'N/A')}")
            print(f"      Response tokens: {result.get('eval_tokens', 'N/A')}")
            
            if verbose:
                print(f"\n   💾 Caching for future:")
                print(f"      Storing embedding vector ({cache.vector_dim} dimensions)")
                print(f"      Creating semantic mapping")
                print(f"      Enabling similarity search for future queries")
        
        print(f"\n📄 Generated SQL:")
        print(f"{'─'*70}")
        print(f"{result['sql']};")
        
        total_time += result.get('time_taken', 0) if not result['cache_hit'] else 0
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📈 DEMO SUMMARY")
    print(f"{'='*70}")
    print(f"   Total queries: {len(test_queries)}")
    print(f"   Cache hits: {cache_hits} ({cache_hits/len(test_queries)*100:.1f}%)")
    print(f"   Cache misses: {len(test_queries) - cache_hits}")
    print(f"   Total LLM time: {total_time:.2f}s")
    if cache_hits < len(test_queries):
        print(f"   Average per new query: {total_time/(len(test_queries) - cache_hits):.2f}s")
    
    # Cache stats
    stats = cache.get_cache_stats()
    print(f"\n📊 CACHE STATISTICS")
    print(f"{'='*70}")
    print(f"   Cached prompts: {stats['total_prompts']}")
    print(f"   Cached queries: {stats['total_queries']}")
    print(f"   Embeddings stored: {stats['total_embeddings']}")
    print(f"   Cache efficiency: {cache_hits/len(test_queries)*100:.1f}%")
    print(f"   Time saved: ~{sum([result.get('time_taken', 0) for result in [cache.get_or_generate_sql(q, verbose=False) for q in test_queries] if result.get('cache_hit')]):.1f}s")
    print('='*70)


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
    parser.add_argument(
        '--host', 
        default=os.getenv('VECTOR_HOST', 'localhost'), 
        help='Valkey host (default: from VECTOR_HOST env or localhost)'
    )
    parser.add_argument(
        '--port', 
        type=int, 
        default=int(os.getenv('VECTOR_PORT', '6379')), 
        help='Valkey port (default: from VECTOR_PORT env or 6379)'
    )
    parser.add_argument(
        '--model', 
        default=os.getenv('OLLAMA_MODEL', 'codellama'), 
        help='Ollama model for SQL generation (default: from OLLAMA_MODEL env or codellama)'
    )
    parser.add_argument(
        '--threshold', 
        type=float, 
        default=float(os.getenv('SIMILARITY_THRESHOLD', '0.70')), 
        help='Similarity threshold 0-1 (default: from SIMILARITY_THRESHOLD env or 0.70)'
    )
    parser.add_argument('--mode', choices=['demo', 'interactive'], default='demo', help='Run mode')
    parser.add_argument('--clear', action='store_true', help='Clear cache before starting')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output with connection details and embeddings')
    
    args = parser.parse_args()
    
    # Initialize cache
    try:
        cache = SemanticSQLCache(
            valkey_host=args.host,
            valkey_port=args.port,
            ollama_model=args.model,
            similarity_threshold=args.threshold,
            verbose=args.verbose
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
        demo_mode(cache, verbose=args.verbose)


if __name__ == "__main__":
    main()
