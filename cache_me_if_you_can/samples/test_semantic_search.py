#!/usr/bin/env python3
"""
Quick test script for semantic search functionality
Tests embedding generation and similarity calculation without full system
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Testing Semantic Search Components...")
print("=" * 60)

# Test 1: Import sentence-transformers
print("\n1. Testing sentence-transformers import...")
try:
    from sentence_transformers import SentenceTransformer
    print("   ✅ sentence-transformers imported successfully")
except ImportError as e:
    print(f"   ❌ Failed to import: {e}")
    sys.exit(1)

# Test 2: Load embedding model
print("\n2. Loading embedding model (this may take a moment on first run)...")
try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print(f"   ✅ Model loaded successfully")
    print(f"   📊 Vector dimension: {model.get_sentence_embedding_dimension()}")
except Exception as e:
    print(f"   ❌ Failed to load model: {e}")
    sys.exit(1)

# Test 3: Generate embeddings
print("\n3. Testing embedding generation...")
try:
    test_texts = [
        "Flight manifest - all passengers on a specific flight 115",
        "Give me the passenger details from flight 115",
        "Show me all passengers on flight 115",
        "Get airport information for JFK",
    ]
    
    embeddings = model.encode(test_texts)
    print(f"   ✅ Generated {len(embeddings)} embeddings")
    print(f"   📊 Shape: {embeddings.shape}")
except Exception as e:
    print(f"   ❌ Failed to generate embeddings: {e}")
    sys.exit(1)

# Test 4: Calculate similarities
print("\n4. Testing similarity calculations...")
try:
    import numpy as np
    
    def cosine_similarity(vec1, vec2):
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    print("\n   Similarity Matrix:")
    print("   " + "-" * 56)
    for i, text1 in enumerate(test_texts):
        for j, text2 in enumerate(test_texts):
            if i < j:
                sim = cosine_similarity(embeddings[i], embeddings[j])
                print(f"   [{i}] vs [{j}]: {sim:.3f}")
                print(f"      '{text1[:40]}...'")
                print(f"      '{text2[:40]}...'")
                print()
    
    print("   ✅ Similarity calculations working")
    
    # Highlight similar queries
    sim_1_2 = cosine_similarity(embeddings[0], embeddings[1])
    sim_1_3 = cosine_similarity(embeddings[0], embeddings[2])
    sim_1_4 = cosine_similarity(embeddings[0], embeddings[3])
    
    print("\n   Key Observations:")
    print(f"   • Queries 0-1 (similar): {sim_1_2:.3f} ✨")
    print(f"   • Queries 0-2 (similar): {sim_1_3:.3f} ✨")
    print(f"   • Queries 0-3 (different): {sim_1_4:.3f}")
    
    if sim_1_2 > 0.85 and sim_1_3 > 0.85:
        print("\n   ✅ Similar queries correctly identified (>0.85 threshold)")
    
except Exception as e:
    print(f"   ❌ Failed similarity test: {e}")
    sys.exit(1)

# Test 5: Test Valkey connection (optional)
print("\n5. Testing Valkey connection...")
try:
    try:
        import valkey
    except ImportError:
        import redis as valkey
    r = valkey.Valkey(host='localhost', port=6379, decode_responses=True)
    r.ping()
    print("   ✅ Valkey connection successful")
except Exception as e:
    print(f"   ⚠️  Redis/Valkey not available: {e}")
    print("   ℹ️  This is optional - semantic search will work without it")

# Summary
print("\n" + "=" * 60)
print("✅ All core components working!")
print("\nYou can now run:")
print("  uv run python samples/semantic_search.py --model codellama")
print("\nNote: First run with Ollama will download the model")
print("=" * 60)
