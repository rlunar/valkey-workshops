"""
Semantic Search Core Module
Provides embedding-based similarity search with optional MMR reranking
"""

import os
import hashlib
from typing import List, Dict, Any, Optional
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


class SemanticSearch:
    """
    Core semantic search functionality using embeddings and vector similarity.
    
    Supports:
    - Embedding generation using SentenceTransformers
    - Vector similarity search (with Valkey/Redis vector search or brute force fallback)
    - MMR (Maximal Marginal Relevance) reranking for diversity
    - Cosine similarity calculations
    """
    
    def __init__(
        self,
        valkey_client: Optional[valkey.Valkey] = None,
        embedding_model: str = None,
        use_mmr: bool = False,
        mmr_lambda: float = 0.5,
        verbose: bool = False
    ):
        """
        Initialize semantic search.
        
        Args:
            valkey_client: Optional Valkey/Redis client. If None, creates a new one.
            embedding_model: Name of the SentenceTransformer model to use
            use_mmr: Whether to use MMR reranking for diversity
            mmr_lambda: MMR lambda parameter (0=diversity, 1=relevance)
            verbose: Enable verbose output
        """
        self.verbose = verbose
        
        # Use environment variables with fallbacks
        if embedding_model is None:
            embedding_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        
        # Connect to Valkey if not provided
        if valkey_client is None:
            valkey_host = os.getenv("VECTOR_HOST", "localhost")
            valkey_port = int(os.getenv("VECTOR_PORT", "6379"))
            
            if verbose:
                print(f"\n{'='*70}")
                print(f"Valkey Connection")
                print(f"{'='*70}")
                print(f"Host: {valkey_host}")
                print(f"Port: {valkey_port}")
            
            self.valkey_client = valkey.Valkey(
                host=valkey_host,
                port=valkey_port,
                decode_responses=False
            )
            
            # Test connection
            try:
                self.valkey_client.ping()
                if verbose:
                    print(f"✅ Connected successfully")
            except Exception as e:
                print(f"❌ Connection failed: {e}")
                raise
        else:
            self.valkey_client = valkey_client
        
        # Initialize embedding model
        if verbose:
            print(f"\n{'='*70}")
            print(f"Embedding Model")
            print(f"{'='*70}")
        print(f"Loading embedding model: {embedding_model}...")
        self.embedding_model = SentenceTransformer(embedding_model)
        self.vector_dim = self.embedding_model.get_sentence_embedding_dimension()
        print(f"✅ Embedding model loaded. Vector dimension: {self.vector_dim}")
        
        # MMR configuration
        self.use_mmr = use_mmr
        self.mmr_lambda = mmr_lambda
        
        if verbose:
            print(f"\n{'='*70}")
            print(f"Configuration")
            print(f"{'='*70}")
            print(f"Use MMR reranking: {use_mmr}")
            if use_mmr:
                print(f"MMR lambda (relevance/diversity): {mmr_lambda}")
    
    @staticmethod
    def hash_text(text: str) -> str:
        """Generate SHA1 hash of text"""
        return hashlib.sha1(text.encode('utf-8')).hexdigest()
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding vector for text"""
        return self.embedding_model.encode(text, convert_to_numpy=True)
    
    @staticmethod
    def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def mmr_rerank(
        self,
        query_embedding: np.ndarray,
        candidates: List[Dict],
        lambda_param: float = None,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Performs Maximal Marginal Relevance reranking to diversify results.
        
        MMR balances relevance to the query with diversity among selected results.
        
        Args:
            query_embedding: The query embedding vector
            candidates: List of candidate results with 'similarity' and 'embedding' keys
            lambda_param: Trade-off between relevance (1.0) and diversity (0.0). 
                         If None, uses self.mmr_lambda
            top_k: Number of results to return
            
        Returns:
            Reranked list of candidates
        """
        if lambda_param is None:
            lambda_param = self.mmr_lambda
        
        if not candidates or len(candidates) <= 1:
            return candidates[:top_k]
        
        # Extract embeddings from candidates
        candidate_embeddings = []
        for candidate in candidates:
            # If embedding is stored as bytes, convert it
            if 'embedding' in candidate:
                emb = candidate['embedding']
                if isinstance(emb, bytes):
                    emb = np.frombuffer(emb, dtype=np.float32)
                candidate_embeddings.append(emb)
            else:
                # If no embedding stored, we can't do MMR, return original
                return candidates[:top_k]
        
        selected_indices = []
        remaining_indices = list(range(len(candidates)))
        
        # Select first item with highest similarity to query
        first_idx = max(remaining_indices, key=lambda i: candidates[i]['similarity'])
        selected_indices.append(first_idx)
        remaining_indices.remove(first_idx)
        
        # Iteratively select remaining items
        while len(selected_indices) < min(top_k, len(candidates)) and remaining_indices:
            mmr_scores = []
            
            for idx in remaining_indices:
                # Relevance: similarity to query
                relevance = candidates[idx]['similarity']
                
                # Diversity: max similarity to already selected items (we want to minimize this)
                max_sim_to_selected = max(
                    self.cosine_similarity(
                        candidate_embeddings[idx],
                        candidate_embeddings[selected_idx]
                    )
                    for selected_idx in selected_indices
                )
                
                # MMR score: balance relevance and diversity
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim_to_selected
                mmr_scores.append((idx, mmr_score))
            
            # Select item with highest MMR score
            best_idx = max(mmr_scores, key=lambda x: x[1])[0]
            selected_indices.append(best_idx)
            remaining_indices.remove(best_idx)
        
        # Return reranked results
        return [candidates[i] for i in selected_indices]
    
    def search_similar(
        self,
        embedding: np.ndarray,
        index_name: str,
        key_prefix: str,
        k: int = 5,
        return_embeddings: bool = None
    ) -> List[Dict]:
        """
        Search for similar items using vector search or fallback to brute force.
        
        Args:
            embedding: Query embedding vector
            index_name: Name of the vector search index
            key_prefix: Prefix for keys to search (e.g., "embedding:prompt:")
            k: Number of results to return
            return_embeddings: Whether to include embeddings in results. 
                              If None, returns embeddings only if MMR is enabled.
            
        Returns:
            List of similar items with similarity scores
        """
        if return_embeddings is None:
            return_embeddings = self.use_mmr
        
        try:
            # Convert embedding to bytes
            embedding_bytes = embedding.astype(np.float32).tobytes()
            
            # Perform vector search - fetch more results if using MMR
            search_k = k * 3 if self.use_mmr else k
            
            # Use the Valkey Search Query API
            from valkey.commands.search.query import Query
            
            query_obj = (
                Query(f"*=>[KNN {search_k} @embedding $vec AS score]")
                .return_fields("*")  # Return all fields
                .dialect(2)
            )
            
            # Execute search with parameters
            results = self.valkey_client.ft(index_name).search(
                query_obj,
                {"vec": embedding_bytes}
            )
            
            if self.verbose:
                print(f"   Vector search executed: {results.total if hasattr(results, 'total') else 'unknown'} results")
            
            # Parse results from the Query API
            # Following the pattern from valkey_bundle_demo.py:
            # 1. Get document IDs from search results
            # 2. Fetch embeddings for each document
            # 3. Calculate cosine similarity manually
            similar_items = []
            if results and hasattr(results, 'docs'):
                candidate_ids = [doc.id if hasattr(doc, 'id') else str(doc) for doc in results.docs]
                
                if self.verbose:
                    print(f"   Found {len(candidate_ids)} candidate documents")
                
                # Fetch embeddings and other fields for all candidates
                for doc_id in candidate_ids:
                    # Fetch the full hash data for this document
                    hash_data = self.valkey_client.hgetall(doc_id)
                    if not hash_data:
                        if self.verbose:
                            print(f"   ⚠️  No hash data found for {doc_id}")
                        continue
                    
                    item = {}
                    candidate_embedding = None
                    
                    # Parse hash fields
                    for field_name, field_value in hash_data.items():
                        # Decode field name if bytes
                        if isinstance(field_name, bytes):
                            field_name = field_name.decode('utf-8')
                        
                        if field_name == "embedding" and field_value:
                            # Always get embedding to calculate similarity
                            candidate_embedding = np.frombuffer(field_value, dtype=np.float32)
                            if return_embeddings:
                                item['embedding'] = candidate_embedding
                        else:
                            # Decode bytes to string if needed
                            if isinstance(field_value, bytes):
                                item[field_name] = field_value.decode('utf-8')
                            else:
                                item[field_name] = field_value
                    
                    # Calculate cosine similarity manually
                    if candidate_embedding is not None:
                        similarity = self.cosine_similarity(embedding, candidate_embedding)
                        item['similarity'] = float(similarity)
                        
                        if self.verbose:
                            print(f"   Doc: {doc_id[:50]}... | Similarity: {similarity:.3f}")
                        
                        similar_items.append(item)
                    else:
                        if self.verbose:
                            print(f"   ⚠️  No embedding found for {doc_id}")
            
            # Apply MMR reranking if enabled
            if self.use_mmr and similar_items:
                similar_items = self.mmr_rerank(embedding, similar_items, top_k=k)
            else:
                similar_items = similar_items[:k]
            
            return similar_items
            
        except Exception as e:
            # Fallback to brute force search if vector search not available
            if self.verbose:
                print(f"   ⚠️  Vector search failed, using brute-force fallback")
                print(f"   Error: {type(e).__name__}: {str(e)}")
            return self._brute_force_search(embedding, key_prefix, k, return_embeddings)
    
    def _brute_force_search(
        self,
        embedding: np.ndarray,
        key_prefix: str,
        k: int = 5,
        return_embeddings: bool = True
    ) -> List[Dict]:
        """
        Fallback: Brute force similarity search when vector search unavailable.
        
        Args:
            embedding: Query embedding vector
            key_prefix: Prefix for keys to search
            k: Number of results to return
            return_embeddings: Whether to include embeddings in results
            
        Returns:
            List of similar items with similarity scores
        """
        try:
            similar_items = []
            
            # Get all keys with the prefix
            keys = list(self.valkey_client.scan_iter(f"{key_prefix}*", count=100))
            
            if not keys:
                return []
            
            # Calculate similarity for each
            for key in keys:
                try:
                    data = self.valkey_client.hgetall(key)
                    if not data:
                        continue
                    
                    # Parse stored data
                    item = {}
                    stored_embedding = None
                    
                    for field_name, field_value in data.items():
                        field_name = field_name.decode('utf-8') if isinstance(field_name, bytes) else field_name
                        
                        if field_name == 'embedding':
                            stored_embedding = np.frombuffer(field_value, dtype=np.float32)
                            if return_embeddings:
                                item['embedding'] = stored_embedding
                        else:
                            item[field_name] = (
                                field_value.decode('utf-8') if isinstance(field_value, bytes) else field_value
                            )
                    
                    if stored_embedding is not None:
                        # Calculate cosine similarity
                        similarity = self.cosine_similarity(embedding, stored_embedding)
                        item['similarity'] = float(similarity)
                        similar_items.append(item)
                        
                except Exception as e:
                    if self.verbose:
                        print(f"Warning: Error processing key {key}: {e}")
                    continue
            
            # Sort by similarity
            similar_items.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Apply MMR reranking if enabled
            if self.use_mmr and similar_items:
                return self.mmr_rerank(embedding, similar_items, top_k=k)
            
            return similar_items[:k]
            
        except Exception as e:
            if self.verbose:
                print(f"Warning: Brute force search failed: {e}")
            return []
    
    def create_vector_index(
        self,
        index_name: str,
        key_prefix: str,
        additional_fields: List[tuple] = None,
        verbose: bool = None
    ) -> bool:
        """
        Create a vector search index.
        
        Args:
            index_name: Name for the index
            key_prefix: Prefix for keys to index
            additional_fields: List of (field_name, field_type) tuples for additional fields
                              field_type can be "TAG", "TEXT", "NUMERIC", etc.
            verbose: Override instance verbose setting
            
        Returns:
            True if index was created or already exists, False otherwise
        """
        if verbose is None:
            verbose = self.verbose
        
        try:
            # Try to get index info
            info = self.valkey_client.execute_command("FT.INFO", index_name)
            if verbose:
                print(f"✅ Index '{index_name}' already exists")
            return True
        except valkey.ResponseError as e:
            # Index doesn't exist, try to create it
            error_msg = str(e).lower()
            if "unknown index" in error_msg or "not found" in error_msg:
                try:
                    if verbose:
                        print(f"Creating vector search index '{index_name}'...")
                        print(f"   Vector dimension: {self.vector_dim}")
                        print(f"   Distance metric: COSINE")
                        print(f"   Algorithm: HNSW")
                    
                    command_args = [
                        "FT.CREATE", index_name,
                        "ON", "HASH",
                        "PREFIX", "1", key_prefix,
                        "SCHEMA"
                    ]
                    
                    # Add additional fields if provided
                    if additional_fields:
                        for field_name, field_type in additional_fields:
                            command_args.extend([field_name, field_type])
                    
                    # Add embedding vector field
                    command_args.extend([
                        "embedding", "VECTOR", "HNSW", "6",
                        "TYPE", "FLOAT32",
                        "DIM", str(self.vector_dim),
                        "DISTANCE_METRIC", "COSINE"
                    ])
                    
                    self.valkey_client.execute_command(*command_args)
                    print(f"✅ Index '{index_name}' created successfully")
                    return True
                except Exception as create_error:
                    # Vector search not available
                    if verbose:
                        print(f"ℹ️  Vector search not available: {create_error}")
                        print(f"   Using brute-force similarity search")
                    return False
            else:
                # Some other error
                if verbose:
                    print(f"⚠️  Warning: Error checking index: {e}")
                return False
    
    def drop_index(self, index_name: str, verbose: bool = None) -> bool:
        """
        Drop a vector search index.
        
        Args:
            index_name: Name of the index to drop
            verbose: Override instance verbose setting
            
        Returns:
            True if index was dropped, False otherwise
        """
        if verbose is None:
            verbose = self.verbose
        
        try:
            self.valkey_client.execute_command("FT.DROPINDEX", index_name)
            if verbose:
                print(f"✅ Index '{index_name}' dropped successfully")
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "unknown index" in error_msg or "not found" in error_msg:
                if verbose:
                    print(f"ℹ️  Index '{index_name}' does not exist")
                return False
            else:
                if verbose:
                    print(f"⚠️  Warning: Could not drop index: {e}")
                return False
