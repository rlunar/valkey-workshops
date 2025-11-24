def main():
    print("Hello from valkey-search-demo!")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
import os
import base64
import threading
import random
import numpy as np
import argparse
import json
import time

# Valkey imports
import valkey
from valkey.cluster import ValkeyCluster, ClusterNode
from valkey.commands.search.query import Query

# Flask imports
from flask import Flask, render_template, request, redirect, url_for, session, Response, stream_with_context

# --- App Initialization & Argument Parsing ---
app = Flask(__name__)
# Use parse_known_args to ensure Flask's own arguments don't cause an error
parser = argparse.ArgumentParser(description="Valkey VSS Demo with Flask and a configurable AI backend.")
parser.add_argument('--cluster', action='store_true', help="Enable cluster mode for connecting to a Valkey Cluster.")
cli_args, _ = parser.parse_known_args()


# --- CENTRALIZED FLASK CONFIGURATION ---
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-demo-purposes")
app.config['VALKEY_HOST'] = os.getenv("VALKEY_HOST", "localhost")
app.config['VALKEY_PORT'] = int(os.getenv("VALKEY_PORT", 6379))
app.config['VALKEY_IS_CLUSTER'] = cli_args.cluster
app.config['GCP_PROJECT'] = os.getenv("GCP_PROJECT")
app.config['GCP_LOCATION'] = "us-central1"
app.config['PLACEHOLDER_IMAGE_URL']="https://via.placeholder.com/300.png?text=No+Image"


# --- Dynamic AI Configuration ---
ai_client = None
# Priority order: AWS > GCP > LOCAL
if os.getenv("AWS_REGION"):
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    app.config['AI_MODE'] = "AWS"
    app.config['AWS_REGION'] = os.getenv("AWS_REGION")
    app.config['LLM_MODEL_NAME'] = "amazon.nova-pro-v1:0"
    app.config['EMBEDDING_MODEL_NAME'] = "amazon.titan-embed-text-v2:0"
    app.config['VECTOR_DIM'] = 1024
    print(f"--- AI Mode Detected: {app.config['AI_MODE']} ---")
    try:
        print(f"Initializing AWS Bedrock client for region '{app.config['AWS_REGION']}'...")
        ai_client = boto3.client(
            'bedrock-runtime',
            region_name=app.config['AWS_REGION']
        )
        
        # Test connection and validate permissions (Requirement 4.2)
        try:
            ai_client.list_foundation_models()
            print("✅ AWS Bedrock client initialized and credentials validated.")
        except ClientError as test_error:
            test_error_code = test_error.response.get('Error', {}).get('Code', 'Unknown')
            if test_error_code == 'AccessDeniedException':
                print(f"WARNING: AWS credentials lack Bedrock permissions. AI features will be mocked. Details: {test_error}")
                print("Please ensure your AWS credentials have bedrock:ListFoundationModels and bedrock:InvokeModel permissions.")
                ai_client = None
            else:
                # Re-raise for general handling below
                raise test_error
                
    except NoCredentialsError as e:
        print(f"WARNING: AWS credentials not found. AI features will be mocked. Details: {e}")
        print("Please ensure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set, or use IAM roles.")
        print("Alternatively, configure AWS CLI with 'aws configure' or use EC2 instance profiles.")
        ai_client = None
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        
        if error_code == 'UnauthorizedOperation':
            print(f"WARNING: AWS credentials lack necessary permissions. AI features will be mocked. Details: {error_message}")
            print("Please ensure your AWS credentials have bedrock:* permissions.")
        elif error_code == 'InvalidRegion':
            print(f"WARNING: Invalid AWS region '{app.config['AWS_REGION']}'. AI features will be mocked. Details: {error_message}")
            print("Please check that Bedrock is available in your specified region.")
        elif error_code == 'ServiceUnavailableException':
            print(f"WARNING: AWS Bedrock service unavailable. AI features will be mocked. Details: {error_message}")
            print("Service may be experiencing issues or not available in this region.")
        elif error_code == 'ThrottlingException':
            print(f"WARNING: AWS rate limiting during initialization. AI features will be mocked. Details: {error_message}")
        else:
            print(f"WARNING: AWS Bedrock client error ({error_code}). AI features will be mocked. Details: {error_message}")
        
        ai_client = None
        
    except Exception as e:
        # Handle network timeouts and other unexpected errors (Requirement 4.4)
        if hasattr(e, '__class__') and 'timeout' in e.__class__.__name__.lower():
            print(f"WARNING: Network timeout initializing AWS Bedrock client. AI features will be mocked. Details: {e}")
            print("Check network connectivity to AWS services.")
        else:
            print(f"WARNING: Unexpected error initializing AWS Bedrock client. AI features will be mocked. Details: {e}")
        
        ai_client = None

elif app.config.get('GCP_PROJECT'):
    from google import genai
    from google.genai import types
    app.config['AI_MODE'] = "GCP"
    app.config['LLM_MODEL_NAME'] = "gemini-1.5-flash-preview-0514"
    app.config['VECTOR_DIM'] = 768
    print(f"--- AI Mode Detected: {app.config['AI_MODE']} ---")
    try:
        print(f"Initializing google.genai client for project '{app.config['GCP_PROJECT']}'...")
        ai_client = genai.Client(
            project=app.config['GCP_PROJECT'],
            location=app.config['GCP_LOCATION']
        )
        print("✅ Google Genai client initialized.")
    except Exception as e:
        print(f"WARNING: Could not initialize Vertex AI client. AI features will be mocked. Details: {e}")
        ai_client = None

else:
    import ollama
    app.config['AI_MODE'] = "LOCAL"
    app.config['LLM_MODEL_NAME'] = "tinyllama"
    app.config['VECTOR_DIM'] = 384
    print(f"--- AI Mode Detected: {app.config['AI_MODE']} ---")
    try:
        print(f"Checking for local Ollama service with model '{app.config['LLM_MODEL_NAME']}'...")
        # The ollama library doesn't need a persistent client, but we can check for connectivity.
        ollama.list()
        ai_client = "Ollama Active" # Use a placeholder string to indicate Ollama is ready
        print("✅ Ollama service detected.")
    except Exception as e:
        print(f"WARNING: Could not connect to Ollama service. AI features will be mocked. Details: {e}")
        ai_client = None


# --- Valkey Client Initialization ---
def get_valkey_connection():
    is_cluster = app.config['VALKEY_IS_CLUSTER']
    host = app.config['VALKEY_HOST']
    port = app.config['VALKEY_PORT']
    print(f"Connecting to Valkey (Cluster mode: {is_cluster})...")
    try:
        if is_cluster:
            client = ValkeyCluster(startup_nodes=[ClusterNode(host=host, port=port)])
        else:
            client = valkey.Valkey(host=host, port=port)
        client.ping()
        print(f"Successfully connected to Valkey.")
        return client
    except Exception as e:
        print(f"FATAL: Could not connect to Valkey. Please check the server. Error: {e}")
        return None

valkey_client = get_valkey_connection()


# --- MMR Reranking Helper (No Changes) ---
def mmr_rerank(query_embedding, candidate_embeddings, lambda_param=0.7, top_n=5):
    """Performs Maximal Marginal Relevance reranking to diversify results."""
    if not candidate_embeddings:
        return []
    selected_indices = []
    candidate_indices = list(range(len(candidate_embeddings)))
    q_emb = query_embedding / np.linalg.norm(query_embedding)
    cand_embs = np.array(candidate_embeddings)
    cand_embs = cand_embs / np.linalg.norm(cand_embs, axis=1, keepdims=True)
    relevance_scores = cand_embs @ q_emb
    if candidate_indices:
        best_idx_pos = np.argmax(relevance_scores)
        selected_indices.append(candidate_indices.pop(best_idx_pos))
    while len(selected_indices) < top_n and candidate_indices:
        mmr_scores = {}
        selected_embeddings = cand_embs[selected_indices]
        for i in candidate_indices:
            relevance = relevance_scores[i]
            diversity = np.max(cand_embs[i] @ selected_embeddings.T)
            mmr_scores[i] = lambda_param * relevance - (1 - lambda_param) * diversity
        if not mmr_scores: break
        best_candidate_idx = max(mmr_scores, key=mmr_scores.get)
        selected_indices.append(best_candidate_idx)
        candidate_indices.remove(best_candidate_idx)
    return selected_indices


# --- Bloom Filter Helpers ---
def mark_product_viewed(user_id, product_id):
    """Mark a product as viewed by a user using Bloom filter."""
    bloom_key = f"viewed:{user_id}"
    try:
        valkey_client.bf().add(bloom_key, product_id)
    except Exception as e:
        print(f"WARNING: Failed to mark product {product_id} as viewed for user {user_id}: {e}")

def is_product_viewed(user_id, product_id):
    """Check if a product has been viewed by a user using Bloom filter."""
    bloom_key = f"viewed:{user_id}"
    try:
        return valkey_client.bf().exists(bloom_key, product_id)
    except Exception as e:
        print(f"WARNING: Failed to check if product {product_id} was viewed by user {user_id}: {e}")
        return False

def add_viewed_status_to_products(user_id, products):
    """Add 'viewed' status to a list of products for a user."""
    for product in products:
        product['viewed'] = is_product_viewed(user_id, product['id'])
    return products

# --- Data Helpers (No Changes) ---
def get_user_profile(user_id):
    if not user_id:
        return None
    # Get JSON data from Valkey
    data = valkey_client.execute_command("JSON.GET", f"user:{user_id}", "$")
    if not data:
        return None
    
    # Parse JSON response
    try:
        parsed_data = json.loads(data)[0]  # JSON.GET with $ returns array
        return {
            "id":        user_id,
            "name":      parsed_data.get('name', ''),
            "bio":       parsed_data.get('bio', ''),
            "avatar":    parsed_data.get('avatar', ''),
            "embedding": np.array(parsed_data.get('embedding', []), dtype=np.float32).tobytes(),
        }
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        print(f"WARNING: Failed to parse user profile JSON for {user_id}: {e}")
        return None


def get_products_by_ids(ids):
    if not ids:
        return []
    pipe = valkey_client.pipeline(transaction=False)
    for pid in ids:
        # Ensure the key is bytes, as hgetall expects byte strings
        key = pid if isinstance(pid, bytes) else pid.encode('utf-8')
        pipe.hgetall(key)
    results = pipe.execute()

    prods = []
    for data in results:
        if not data:
            continue
        thumbnail_url = data.get(b'image_url', b'').decode()
        if not thumbnail_url:
            thumbnail_url = app.config['PLACEHOLDER_IMAGE_URL']
        prods.append({
            "id":    data.get(b'id', b'').decode(),
            "name":  data.get(b'name', b'').decode(),
            "brand": data.get(b'brand', b'').decode(),
            "price": data.get(b'price', b'').decode(),
            "rating": data.get(b'rating', b'').decode(),
            "link":  data.get(b'link', b'').decode(),
            "thumbnail": thumbnail_url,
        })
    return prods


# --- AWS Error Handling Classes and Utilities ---
class AWSBedrockError(Exception):
    """Base exception for AWS Bedrock related errors."""
    pass


class AWSCredentialsError(AWSBedrockError):
    """Exception for AWS credential issues."""
    pass


class AWSRateLimitError(AWSBedrockError):
    """Exception for AWS rate limiting."""
    pass


class AWSServiceUnavailableError(AWSBedrockError):
    """Exception for AWS service unavailability."""
    pass


class AWSCircuitBreaker:
    """
    Simple circuit breaker to prevent cascading failures when AWS services are down.
    """
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.
        """
        import time
        
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
                print("INFO: AWS circuit breaker transitioning to HALF_OPEN state")
            else:
                raise AWSServiceUnavailableError("AWS circuit breaker is OPEN - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
                print("INFO: AWS circuit breaker reset to CLOSED state")
            return result
        except (AWSServiceUnavailableError, AWSCredentialsError) as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                print(f"WARNING: AWS circuit breaker opened after {self.failure_count} failures")
            
            raise e


# Global circuit breaker instance
aws_circuit_breaker = AWSCircuitBreaker()


def handle_aws_error(error, context="", user_name=None, product_name=None):
    """
    Centralized AWS error handling with proper logging and fallback mechanisms.
    
    Args:
        error: The exception that occurred
        context: Context string for logging (e.g., "Nova Pro generation", "Titan embedding")
        user_name: User name for fallback description generation
        product_name: Product name for fallback description generation
    
    Returns:
        Appropriate fallback response based on context
    """
    # Import AWS exceptions here to avoid import issues when AWS is not configured
    try:
        from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError
    except ImportError:
        print(f"WARNING: AWS libraries not available for error handling in {context}")
        if user_name and product_name:
            return get_aws_fallback_description(user_name, product_name)
        return None
    # Handle AWS credential errors (Requirement 4.2)
    if isinstance(error, NoCredentialsError):
        print(f"WARNING: AWS credentials not found for {context}. "
              f"Please ensure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set, or use IAM roles.")
        raise AWSCredentialsError(f"AWS credentials not found: {error}")
    # Handle endpoint connection errors (network issues)
    elif isinstance(error, EndpointConnectionError):
        print(f"WARNING: Cannot connect to AWS endpoint for {context}. "
              f"Check network connectivity and AWS region configuration. "
              f"Details: Connection failed")  # Don't expose full endpoint details
        raise AWSServiceUnavailableError(f"AWS endpoint connection failed")
    # Handle AWS client errors with specific error codes (Requirements 4.1, 4.3)
    elif isinstance(error, ClientError):
        error_code = error.response.get('Error', {}).get('Code', 'Unknown')
        # Sanitize error message to avoid exposing sensitive information (Requirement 4.5)
        error_message = error.response.get('Error', {}).get('Message', 'AWS service error')
        # Remove any potential sensitive information from error messages
        sanitized_message = _sanitize_error_message(error_message)
        if error_code == 'ThrottlingException':
            print(f"WARNING: AWS rate limiting encountered for {context}. "
                  f"Request will be retried with exponential backoff. Details: {sanitized_message}")
            raise AWSRateLimitError(f"AWS rate limiting: {sanitized_message}")
        elif error_code == 'ValidationException':
            print(f"WARNING: AWS validation error for {context}. "
                  f"Check request parameters. Details: {sanitized_message}")
        elif error_code == 'AccessDeniedException':
            print(f"WARNING: AWS access denied for {context}. "
                  f"Check IAM permissions for Bedrock services. Details: {sanitized_message}")
            raise AWSCredentialsError(f"AWS access denied: {sanitized_message}")
        elif error_code == 'ServiceUnavailableException':
            print(f"WARNING: AWS Bedrock service unavailable for {context}. "
                  f"Service may be experiencing issues. Details: {sanitized_message}")
            raise AWSServiceUnavailableError(f"AWS service unavailable: {sanitized_message}")
        elif error_code == 'ModelNotReadyException':
            print(f"WARNING: AWS model not ready for {context}. "
                  f"Model may be loading or unavailable in this region. Details: {sanitized_message}")
            raise AWSServiceUnavailableError(f"AWS model not ready: {sanitized_message}")
        elif error_code == 'InternalServerException':
            print(f"WARNING: AWS internal server error for {context}. "
                  f"Temporary service issue. Details: {sanitized_message}")
            raise AWSServiceUnavailableError(f"AWS internal error: {sanitized_message}")
        elif error_code == 'ResourceNotFoundException':
            print(f"WARNING: AWS resource not found for {context}. "
                  f"Model or resource may not exist in this region. Details: {sanitized_message}")
            raise AWSServiceUnavailableError(f"AWS resource not found: {sanitized_message}")
        elif error_code == 'ModelTimeoutException':
            print(f"WARNING: AWS model timeout for {context}. "
                  f"Model processing took too long. Details: {sanitized_message}")
            raise AWSServiceUnavailableError(f"AWS model timeout: {sanitized_message}")
        else:
            print(f"WARNING: AWS client error for {context}. "
                  f"Error code: {error_code}. Details: {sanitized_message}")
    # Handle JSON parsing errors
    elif isinstance(error, json.JSONDecodeError):
        print(f"WARNING: Failed to parse AWS response JSON for {context}. "
              f"Response may be malformed. Details: Invalid JSON response")
    # Handle network and timeout errors
    elif hasattr(error, '__class__') and 'timeout' in error.__class__.__name__.lower():
        print(f"WARNING: Network timeout for {context}. "
              f"Check network connectivity to AWS services. Details: Request timeout")
        raise AWSServiceUnavailableError(f"Network timeout")
    # Handle general exceptions
    else:
        print(f"WARNING: Unexpected error for {context}. Details: {type(error).__name__}")
    # Return appropriate fallback based on context
    if user_name and product_name:
        return get_aws_fallback_description(user_name, product_name)
    elif context == "embedding":
        return np.random.rand(app.config.get('VECTOR_DIM', 1024)).astype(np.float32).tolist()
    else:
        return None


def _sanitize_error_message(message):
    """
    Sanitize error messages to remove potentially sensitive information.
    
    Args:
        message: Original error message
    
    Returns:
        Sanitized error message without sensitive information
    """
    if not message:
        return "AWS service error"
    # Remove potential access keys, tokens, or other sensitive patterns
    import re
    # Remove AWS access key patterns
    message = re.sub(r'AKIA[0-9A-Z]{16}', '[ACCESS_KEY_REDACTED]', message)
    # Remove potential secret key patterns
    message = re.sub(r'[A-Za-z0-9/+=]{40}', '[SECRET_REDACTED]', message)
    # Remove session token patterns
    message = re.sub(r'[A-Za-z0-9/+=]{100,}', '[TOKEN_REDACTED]', message)
    # Remove IP addresses
    message = re.sub(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', '[IP_REDACTED]', message)
    # Remove potential ARNs with account numbers
    message = re.sub(r'arn:aws:[^:]*:[^:]*:\d{12}:[^:]*', '[ARN_REDACTED]', message)    
    return message


def retry_with_exponential_backoff(func, max_retries=3, base_delay=1.0):
    """
    Retry function with exponential backoff for handling rate limiting.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
    
    Returns:
        Function result or raises exception after max retries
    """
    import time
    import random
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except AWSRateLimitError as e:
            if attempt == max_retries:
                print(f"WARNING: Max retries ({max_retries}) exceeded for AWS rate limiting.")
                raise e
            
            # Add jitter to prevent thundering herd problem
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            print(f"INFO: Retrying AWS request in {delay:.1f} seconds (attempt {attempt + 1}/{max_retries + 1})")
            time.sleep(delay)
        except (AWSCredentialsError, AWSServiceUnavailableError):
            # Don't retry for credential or service unavailability errors
            raise
        except Exception as e:
            # Log unexpected errors but don't retry
            print(f"WARNING: Unexpected error in retry mechanism: {type(e).__name__}")
            raise


# --- AWS Bedrock Text Generation ---
def generate_with_nova_pro(client, prompt, user_name, product_name):
    """
    Generate personalized description using Amazon Nova Pro with comprehensive error handling.
    """
    if not client:
        print("WARNING: AWS Bedrock client not available, using fallback response.")
        return get_aws_fallback_description(user_name, product_name)
    
    def _generate():
        try:
            response = client.invoke_model(
                modelId=app.config['LLM_MODEL_NAME'],
                body=json.dumps({
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": 200,
                        "temperature": 0.7,
                        "topP": 0.9
                    }
                })
            )
            response_body = json.loads(response['body'].read())
            # Validate response structure
            if not response_body.get('results') or not response_body['results']:
                raise ValueError("Empty results in Nova Pro response")
            output_text = response_body['results'][0].get('outputText')
            if not output_text or not output_text.strip():
                raise ValueError("Empty output text in Nova Pro response")
            return output_text.strip()
        except (NoCredentialsError, ClientError, json.JSONDecodeError) as e:
            return handle_aws_error(e, "Nova Pro generation", user_name, product_name)
        except Exception as e:
            return handle_aws_error(e, "Nova Pro generation", user_name, product_name)
    
    try:
        # Use circuit breaker to prevent cascading failures
        def _generate_with_circuit_breaker():
            return aws_circuit_breaker.call(_generate)
        
        # Use retry mechanism for rate limiting (Requirement 4.3)
        return retry_with_exponential_backoff(_generate_with_circuit_breaker)
    except (AWSCredentialsError, AWSServiceUnavailableError, AWSRateLimitError):
        # All retry attempts failed, use fallback (Requirement 4.4)
        print(f"WARNING: All retry attempts failed for Nova Pro generation. Using fallback response.")
        return get_aws_fallback_description(user_name, product_name)
    except Exception as e:
        print(f"WARNING: Unexpected error in Nova Pro retry mechanism. Using fallback response. Details: {type(e).__name__}")
        return get_aws_fallback_description(user_name, product_name)


def get_aws_fallback_description(user_name, product_name):
    """
    Generate fallback description when AWS Bedrock is unavailable.
    Ensures application continues functioning (Requirement 4.4).
    """
    return (
        f"For an individual like {user_name}, the {product_name} "
        f"represents excellent value and quality, perfectly suited to your needs."
    )


# --- Async LLM Descriptions ---
def get_personalized_descriptions_async(user_profile, products):
    """
    Kicks off a SINGLE background thread that loops through products sequentially
    to generate and cache their descriptions using the configured AI backend.
    """
    def task():
        ## --- DELTA START ---
        if not ai_client:
            print(f"INFO: AI client ({app.config['AI_MODE']}) not available, skipping description generation.")
            return
        for product in products:
            cache_key = f"llm_cache:user:{user_profile['id']}:product:{product['id']}"
            if valkey_client.exists(cache_key):
                print(f"INFO: [Cache Hit] for {cache_key}")
                continue
            print(f"INFO: [Cache Miss] for {cache_key}. Calling {app.config['AI_MODE']}...")
            prompt = (
                f"You are a helpful and persuasive sales assistant. A user named {user_profile['name']} "
                f"is considering the product: '{product['name']}'. Their bio is: '{user_profile['bio']}'. "
                f"Write a short, personalized paragraph for this product that addresses their interests. No markdown."
            )
            desc = None

            try:
                if app.config['AI_MODE'] == "AWS":
                    desc = generate_with_nova_pro(ai_client, prompt, user_profile['name'], product['name'])
                elif app.config['AI_MODE'] == "GCP":
                    response = ai_client.generate_content(
                        model=app.config['LLM_MODEL_NAME'],
                        contents=[prompt]
                    )
                    desc = response.text if response and response.text else None
                elif app.config['AI_MODE'] == "LOCAL":
                    response = ollama.generate(
                        model=app.config['LLM_MODEL_NAME'],
                        prompt=prompt
                    )
                    desc = response['response'] if response and response['response'] else None
                if not desc: raise ValueError("Received empty response from LLM")
                print(f"INFO: [{app.config['AI_MODE']} Success] for {cache_key}")
            except Exception as e:
                # Enhanced error handling to continue processing other products (Requirement 4.5)
                print(f"WARNING: [{app.config['AI_MODE']} API Call Failed] for product {product['name']}. "
                      f"Continuing with other products. Details: {e}")
                if app.config['AI_MODE'] == "AWS":
                    desc = get_aws_fallback_description(user_profile['name'], product['name'])
                else:
                    desc = (
                        f"For an individual like {user_profile['name']}, the {product['name']} "
                        f"is a standout choice, aligning perfectly with your unique interests and needs."
                    )
                
                # Log that we're continuing with the next product
                print(f"INFO: Using fallback description for {product['name']}, continuing with batch processing.")
            valkey_client.set(cache_key, desc, ex=7200)
        ## --- DELTA END ---

    # Start the single background thread to run the task
    threading.Thread(target=task).start()


# --- Routes (No structural changes, but logic now depends on dynamic config) ---
@app.before_request
def check_connection():
    if not valkey_client:
        return "Error: Could not connect to Valkey. Please check the server and your connection settings.", 503


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        uid = request.form.get("user_id")
        # Simple validation, in a real app this would be a proper password check
        if uid and get_user_profile(uid):
            session["user_id"] = uid
            return redirect(url_for("home"))
        return render_template("login.html", error="Invalid user ID. Try 101 or 102.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@app.route("/home")
def home():
    uid = session.get("user_id")
    if not uid:
        return redirect(url_for("login"))
    user = get_user_profile(uid)
    # Get a small random sample of products for the homepage
    keys = list(valkey_client.scan_iter("product:*"))
    picks = random.sample(keys, min(5, len(keys)))
    products = get_products_by_ids(picks)
    if products:
        products = add_viewed_status_to_products(uid, products)
    if user and products:
        get_personalized_descriptions_async(user, products)
    return render_template("home.html", user=user, products=products)


@app.route("/search", methods=["POST"])
def search():
    uid = session.get("user_id")
    if not uid:
        return redirect(url_for("login"))
    user = get_user_profile(uid)
    query_text = request.form.get("query", "").strip()
    if not query_text:
        return redirect(url_for("home"))
    tags = query_text.lower().split()
    tag_filter = " ".join(f"@search_tags:{{{t}}}" for t in tags)
    q_str = f"({tag_filter})=>[KNN 25 @embedding $user_vec]"
    query_obj = (
        Query(q_str)
        .return_fields("id") # Only need the ID for the first pass
        .dialect(2)
    )
    res = valkey_client.ft("products").search(query_obj, {"user_vec": user["embedding"]})
    # Fetch embeddings for the candidates to perform reranking
    candidate_ids = [f"{doc.id}" for doc in res.docs]
    pipe = valkey_client.pipeline(transaction=False)
    for pid in candidate_ids:
        pipe.hget(pid.encode('utf-8'), b"embedding")
    embedding_blobs = pipe.execute()
    # Filter out any products without embeddings and convert blobs to numpy arrays
    valid_candidate_ids = [
        pid for pid, emb in zip(candidate_ids, embedding_blobs) if emb
    ]
    candidate_embs = [
        np.frombuffer(emb, dtype=np.float32)
        for emb in embedding_blobs if emb
    ]
    if valid_candidate_ids and candidate_embs:
        selected_indices = mmr_rerank(
            np.frombuffer(user["embedding"], dtype=np.float32),
            candidate_embs,
            lambda_param=0.7,
            top_n=5
        )
        final_ids = [valid_candidate_ids[i] for i in selected_indices]
        products = get_products_by_ids(final_ids)
    else:
        products = []

    if products:
        products = add_viewed_status_to_products(uid, products)
    if user and products:
        get_personalized_descriptions_async(user, products)
    return render_template("home.html", user=user, products=products, search_query=query_text)


@app.route("/stream/<cache_key>")
def stream(cache_key):
    """
    This endpoint checks the Valkey cache repeatedly and streams the result
    as soon as it's available using Server-Sent Events (SSE).
    """
    def generate():
        # Try to get the cached result for up to 20 seconds
        retries = 20
        while retries > 0:
            description = valkey_client.get(cache_key)
            if description:
                yield f"data: {json.dumps({'description': description.decode('utf-8')})}\n\n"
                return
            time.sleep(1)
            retries -= 1
        # If the key never appears, send a timeout message
        yield f"data: {json.dumps({'description': 'Could not generate a personalized description at this time.'})}\n\n"
    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/product/<product_id>")
def product_detail(product_id):
    uid = session.get("user_id")
    if not uid:
        return redirect(url_for("login"))
    user = get_user_profile(uid)
    key = f"product:{product_id}"
    items = get_products_by_ids([key])
    if not items:
        return "Not found", 404
    product = items[0]
    
    # Check if product was previously viewed before marking as viewed
    product['viewed'] = is_product_viewed(uid, product_id)
    
    # Mark this product as viewed
    mark_product_viewed(uid, product_id)
    
    cache_key = f"llm_cache:user:{uid}:product:{product_id}"
    desc = valkey_client.get(cache_key)
    if not valkey_client.exists(cache_key):
        get_personalized_descriptions_async(user, [product])
    product['personalized_description'] = desc.decode() if desc else "A great choice that combines quality and value."
    # Find similar products based on product embedding
    ft = valkey_client.ft("products")
    product_emb_bytes = valkey_client.hget(key.encode('utf-8'), "embedding")
    similar_products = []
    if product_emb_bytes:
        q_prod = (Query("*=>[KNN 6 @embedding $product_vec]").return_field("id").dialect(2))
        res_sim = ft.search(q_prod, {"product_vec": product_emb_bytes})
        sim_ids = [f"{d.id}" for d in res_sim.docs if d.id != key][:5] # Exclude self
        similar_products = get_products_by_ids(sim_ids)
        similar_products = add_viewed_status_to_products(uid, similar_products)
        get_personalized_descriptions_async(user, similar_products)
    # Find recommended products based on user embedding
    q_user = Query("*=>[KNN 25 @embedding $user_vec]").return_field("id").dialect(2)
    res_user = ft.search(q_user, {"user_vec": user["embedding"]})
    candidate_ids = []
    candidate_embs = []
    for d in res_user.docs:
        if d.id == key: # Exclude current product from recommendations
            continue
        pid = f"{d.id}"
        e = valkey_client.hget(pid.encode('utf-8'), "embedding")
        if e:
            candidate_ids.append(pid)
            candidate_embs.append(np.frombuffer(e, dtype=np.float32))
    if candidate_ids and candidate_embs:
        selected_indices = mmr_rerank(np.frombuffer(user["embedding"], dtype=np.float32), candidate_embs, top_n=5)
        recommended_ids = [candidate_ids[i] for i in selected_indices]
        recommended_products = get_products_by_ids(recommended_ids)
        recommended_products = add_viewed_status_to_products(uid, recommended_products)
        get_personalized_descriptions_async(user, recommended_products)
    else:
        recommended_products = []
    return render_template(
        "product_detail.html",
        user=user,
        product=product,
        llm_cache_key=cache_key,
        similar_products=similar_products,
        recommended_products=recommended_products
    )


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5001)