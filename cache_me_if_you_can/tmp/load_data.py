#!/usr/bin/env python3
import os
import re
import argparse
import sys
import json
import hashlib
import base64
from datetime import datetime, timedelta
import pandas as pd
from tqdm import tqdm
import random
import numpy as np

# Valkey imports for both modes
import valkey
from valkey.cluster import ValkeyCluster, ClusterNode


# --- Argument Parsing ---
parser = argparse.ArgumentParser(
    description="Load product data and generate embeddings, using Vertex AI if configured, otherwise falling back to a local model.",
    formatter_class=argparse.RawTextHelpFormatter
)
parser.add_argument('--host', type=str, default=os.getenv("VALKEY_HOST", "localhost"), help="IP address or hostname of the Valkey server or a cluster entrypoint.")
parser.add_argument('--port', type=int, default=int(os.getenv("VALKEY_PORT", 6379)), help="Port number of the Valkey server or a cluster entrypoint.")
parser.add_argument('--cluster', action='store_true', help="Enable cluster mode for connecting to a Valkey Cluster.")
# GCP Project is now optional. If not provided, the script will use the local fallback.
parser.add_argument('--project', type=str, default=os.getenv("GCP_PROJECT"), help="[Optional] Your Google Cloud Project ID. If not set, a local model will be used.")
parser.add_argument('--location', type=str, default="us-central1", help="The GCP region for your Vertex AI job.")
# AWS Region for explicit AWS mode selection
parser.add_argument('--aws-region', type=str, default=os.getenv("AWS_REGION"), help="[Optional] AWS region for Bedrock. If set, AWS Bedrock will be used for embeddings.")
parser.add_argument('--flush', action='store_true', help="Flush all data from the Valkey server before loading new data.")
args = parser.parse_args()


# --- Configuration ---
VALKEY_HOST = args.host
VALKEY_PORT = args.port
IS_CLUSTER = args.cluster
FLUSH_DATA = args.flush
DATA_DIR = "data"
BATCH_SIZE = 100
INDEX_NAME = "products"
DOC_PREFIX = f"product:"
DISTANCE_METRIC = "COSINE"
REGIONS = ["NA", "EU", "ASIA", "LATAM"]
STOP_WORDS = set(["a", "about", "all", "an", "and", "any", "are", "as", "at", "be", "but", "by", "for", "from", "how", "i", "in", "is", "it", "of", "on", "or", "s", "t", "that", "the", "this", "to", "was", "what", "when", "where", "who", "will", "with", "storage", "ram", "gb", "mah", "mm", "hz", "with", "cm"])


# --- Dynamic AI Configuration ---
AI_MODE = None
MODEL_NAME = None
EMBEDDING_MODEL_NAME = None
VECTOR_DIM = None
model = None # This will hold either the AWS, GCP or local model client
bedrock_client = None # AWS Bedrock client


# Priority order: AWS > GCP > LOCAL
# Check for AWS configuration first (either via --aws-region argument or AWS_REGION environment variable)
if args.aws_region or os.getenv("AWS_REGION"):
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        AI_MODE = "AWS"
        AWS_REGION = args.aws_region or os.getenv("AWS_REGION")
        EMBEDDING_MODEL_NAME = "amazon.titan-embed-text-v2:0"
        VECTOR_DIM = 1024 # Titan Text Embeddings v2 has 1024 dimensions
        print(f"AWS Bedrock configuration detected. Region: {AWS_REGION}")
        print(f"AWS embedding model: {EMBEDDING_MODEL_NAME}, Vector dimension: {VECTOR_DIM}")
        if args.aws_region:
            print(f"AWS region explicitly set via --aws-region argument: {args.aws_region}")
        else:
            print(f"AWS region detected from AWS_REGION environment variable: {os.getenv('AWS_REGION')}")
    except ImportError as e:
        print(f"ERROR: boto3 library not found. Please install boto3 to use AWS Bedrock. Details: {e}")
        print("Falling back to LOCAL mode.")
        from sentence_transformers import SentenceTransformer
        AI_MODE = "LOCAL"
        MODEL_NAME = "all-MiniLM-L6-v2"
        VECTOR_DIM = 384 # all-MiniLM-L6-v2 model has 384 dimensions
elif args.project:
    try:
        import vertexai
        from vertexai.language_models import TextEmbeddingModel
        AI_MODE = "GCP"
        GCP_PROJECT = args.project
        GCP_LOCATION = args.location
        MODEL_NAME = "text-embedding-004"
        VECTOR_DIM = 768 # text-embedding-004 model has 768 dimensions
        print(f"GCP Vertex AI configuration detected. Project: {GCP_PROJECT}, Location: {GCP_LOCATION}")
        print(f"GCP embedding model: {MODEL_NAME}, Vector dimension: {VECTOR_DIM}")
    except ImportError as e:
        print(f"ERROR: vertexai library not found. Please install google-cloud-aiplatform to use GCP. Details: {e}")
        print("Falling back to LOCAL mode.")
        from sentence_transformers import SentenceTransformer
        AI_MODE = "LOCAL"
        MODEL_NAME = "all-MiniLM-L6-v2"
        VECTOR_DIM = 384 # all-MiniLM-L6-v2 model has 384 dimensions
else:
    from sentence_transformers import SentenceTransformer
    AI_MODE = "LOCAL"
    MODEL_NAME = "all-MiniLM-L6-v2"
    VECTOR_DIM = 384 # all-MiniLM-L6-v2 model has 384 dimensions
    print(f"LOCAL mode configuration detected. Model: {MODEL_NAME}, Vector dimension: {VECTOR_DIM}")


# --- Helper Functions (no changes) ---
def generate_tags(text: str, separator: str = ',') -> str:
    if not isinstance(text, str): return ""
    text = text.lower()
    text = re.sub(r'\(|\)|,|\.', ' ', text)
    text = re.sub(r'[^\w\s-]', '', text)
    words = re.split(r'[\s-]+', text)
    unique_words = {word for word in words if word and word not in STOP_WORDS and not word.isdigit()}
    return separator.join(sorted(list(unique_words)))


def extract_brand(name: str) -> str:
    if not isinstance(name, str): return "Unknown"
    return name.split(' ')[0]


def clean_numeric(val, to_type=float):
    if not isinstance(val, str): val = str(val)
    numeric_part = re.findall(r'[\d\.]+', val.replace(',', ''))
    try:
        return to_type(numeric_part[0]) if numeric_part else 0
    except (ValueError, IndexError): return 0


def generate_avatar_data_uri(user_id: str) -> str:
    m = hashlib.md5()
    m.update(user_id.encode('utf-8'))
    digest = m.digest()
    hue = int(digest[0]) * 360 // 256
    fg_color = f"hsl({hue}, 55%, 50%)"
    bg_color = "hsl(0, 0%, 94%)"
    svg = f'<svg viewBox="0 0 80 80" width="80" height="80" xmlns="http://www.w3.org/2000/svg"><rect width="80" height="80" fill="{bg_color}" />'
    for y in range(5):
        for x in range(3):
            bit_index = (y * 3 + x) % (len(digest) * 8)
            byte_index, inner_bit_index = divmod(bit_index, 8)
            if (digest[byte_index] >> inner_bit_index) & 1:
                svg += f'<rect x="{x*16}" y="{y*16}" width="16" height="16" fill="{fg_color}" />'
                if x < 2:
                    svg += f'<rect x="{(4-x)*16}" y="{y*16}" width="16" height="16" fill="{fg_color}" />'
    svg += '</svg>'
    b64_svg = base64.b64encode(svg.encode('utf-8')).decode('utf-8')
    return f"data:image/svg+xml;base64,{b64_svg}"


def handle_aws_embedding_error(error, context="embedding generation"):
    """
    Centralized AWS error handling for embedding generation with proper logging.
    
    Args:
        error: The exception that occurred
        context: Context string for logging
    
    Returns:
        None (error is logged, fallback handled by caller)
    """
    # Import additional AWS exceptions
    try:
        from botocore.exceptions import EndpointConnectionError
    except ImportError:
        EndpointConnectionError = None
    
    # Handle AWS credential errors (Requirement 4.2)
    if isinstance(error, NoCredentialsError):
        print(f"WARNING: AWS credentials not found for {context}. "
              f"Please ensure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set, or use IAM roles. "
              f"Details: Credentials not available")  # Don't expose full credential error
        return
    
    # Handle endpoint connection errors (network issues)
    elif EndpointConnectionError and isinstance(error, EndpointConnectionError):
        print(f"WARNING: Cannot connect to AWS endpoint for {context}. "
              f"Check network connectivity and AWS region configuration. "
              f"Details: Connection failed")  # Don't expose full endpoint details
        return
    
    # Handle AWS client errors with specific error codes (Requirements 4.1, 4.3)
    elif isinstance(error, ClientError):
        error_code = error.response.get('Error', {}).get('Code', 'Unknown')
        error_message = error.response.get('Error', {}).get('Message', 'AWS service error')
        
        # Sanitize error message to avoid exposing sensitive information (Requirement 4.5)
        sanitized_message = _sanitize_embedding_error_message(error_message)
        
        if error_code == 'ThrottlingException':
            print(f"WARNING: AWS rate limiting encountered for {context}. "
                  f"Consider implementing request batching or delays. Details: {sanitized_message}")
        
        elif error_code == 'ValidationException':
            print(f"WARNING: AWS validation error for {context}. "
                  f"Check request parameters and input text format. Details: {sanitized_message}")
        
        elif error_code == 'AccessDeniedException':
            print(f"WARNING: AWS access denied for {context}. "
                  f"Check IAM permissions for bedrock:InvokeModel on {EMBEDDING_MODEL_NAME}. Details: {sanitized_message}")
        
        elif error_code == 'ServiceUnavailableException':
            print(f"WARNING: AWS Bedrock service unavailable for {context}. "
                  f"Service may be experiencing issues or model unavailable in region. Details: {sanitized_message}")
        
        elif error_code == 'ModelNotReadyException':
            print(f"WARNING: AWS embedding model not ready for {context}. "
                  f"Model may be loading or unavailable in region {AWS_REGION}. Details: {sanitized_message}")
        
        elif error_code == 'InternalServerException':
            print(f"WARNING: AWS internal server error for {context}. "
                  f"Temporary service issue. Details: {sanitized_message}")
        
        elif error_code == 'ResourceNotFoundException':
            print(f"WARNING: AWS resource not found for {context}. "
                  f"Model may not exist in this region. Details: {sanitized_message}")
        
        elif error_code == 'ModelTimeoutException':
            print(f"WARNING: AWS model timeout for {context}. "
                  f"Model processing took too long. Details: {sanitized_message}")
        
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
    
    # Handle general exceptions
    else:
        print(f"WARNING: Unexpected error for {context}. Details: {type(error).__name__}")


def _sanitize_embedding_error_message(message):
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
    # Truncate very long messages that might contain sensitive data
    if len(message) > 200:
        message = message[:200] + "... [TRUNCATED]"
    return message


def retry_embedding_with_backoff(client, text, max_retries=2, base_delay=1.0):
    """
    Retry embedding generation with exponential backoff for rate limiting.
    
    Args:
        client: boto3 bedrock-runtime client
        text: Text to embed
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
    
    Returns:
        Embedding vector or None if all retries failed
    """
    import time
    for attempt in range(max_retries + 1):
        try:
            response = client.invoke_model(
                modelId=EMBEDDING_MODEL_NAME,
                body=json.dumps({
                    "inputText": text,
                    "dimensions": 1024,
                    "normalize": True
                })
            )
            response_body = json.loads(response['body'].read())
            # Validate response structure
            if 'embedding' not in response_body:
                raise ValueError("No embedding in Titan response")
            return response_body['embedding']
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'ThrottlingException' and attempt < max_retries:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                print(f"INFO: Rate limited, retrying embedding in {delay:.1f} seconds (attempt {attempt + 1}/{max_retries + 1})")
                time.sleep(delay)
                continue
            else:
                # Don't retry for non-throttling errors or max retries reached
                handle_aws_embedding_error(e, "Titan embedding generation")
                return None
        except Exception as e:
            handle_aws_embedding_error(e, "Titan embedding generation")
            return None
    return None


def generate_embeddings_with_titan(client, texts):
    """
    Generate embeddings using Amazon Titan Text Embeddings v2 with comprehensive error handling.
    
    Args:
        client: boto3 bedrock-runtime client
        texts: List of texts to embed
    
    Returns:
        List of embedding vectors (1024-dimensional)
    """
    embeddings = []
    aws_success_count = 0
    aws_fallback_count = 0
    aws_retry_count = 0
    for i, text in enumerate(texts):
        try:
            if client:
                # Use retry mechanism for rate limiting (Requirement 4.3)
                embedding = retry_embedding_with_backoff(client, text)
                if embedding is not None:
                    embeddings.append(embedding)
                    aws_success_count += 1
                else:
                    # Retry failed, use fallback
                    print(f"INFO: Using random vector fallback for text {i+1}/{len(texts)}")
                    embeddings.append(np.random.rand(VECTOR_DIM).astype(np.float32).tolist())
                    aws_fallback_count += 1
            else:
                # Client not available, use fallback (Requirement 4.4)
                embeddings.append(np.random.rand(VECTOR_DIM).astype(np.float32).tolist())
                aws_fallback_count += 1
        except Exception as e:
            # Ensure processing continues with other texts (Requirement 4.5)
            print(f"WARNING: Unexpected error processing text {i+1}/{len(texts)}. "
                  f"Continuing with remaining texts. Details: {e}")
            embeddings.append(np.random.rand(VECTOR_DIM).astype(np.float32).tolist())
            aws_fallback_count += 1
    # Display progress and success/failure statistics (Requirement 5.5)
    if aws_success_count > 0 or aws_fallback_count > 0:
        total_processed = aws_success_count + aws_fallback_count
        success_rate = (aws_success_count / total_processed) * 100 if total_processed > 0 else 0
        print(f"AWS Batch Stats: {aws_success_count}/{total_processed} successful ({success_rate:.1f}%), "
              f"{aws_fallback_count} fallbacks")
        if aws_fallback_count > 0:
            print(f"INFO: Application continues functioning with {aws_fallback_count} fallback embeddings")
    return embeddings


# --- 1. Initialize Clients ---
try:
    print(f"\n--- AI Mode Detected: {AI_MODE} ---")
    if AI_MODE == "AWS":
        print(f"--- Initializing AWS Bedrock client for region '{AWS_REGION}'...")
        print(f"--- Using embedding model: {EMBEDDING_MODEL_NAME}")
        try:
            # Initialize boto3 Bedrock client during startup (Requirement 3.2)
            bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=AWS_REGION
            )
            
            # Test connection and validate permissions (Requirement 4.2)
            try:
                bedrock_client.list_foundation_models()
                print(f"✅ AWS Bedrock client initialized successfully")
                print(f"✅ AWS embedding model '{EMBEDDING_MODEL_NAME}' configured. Vector dimension: {VECTOR_DIM}")
                print(f"✅ AWS credentials validated and connection established")
            except ClientError as test_error:
                test_error_code = test_error.response.get('Error', {}).get('Code', 'Unknown')
                if test_error_code == 'AccessDeniedException':
                    print(f"WARNING: AWS credentials lack Bedrock permissions. Details: {test_error}")
                    print("Please ensure your AWS credentials have bedrock:ListFoundationModels and bedrock:InvokeModel permissions.")
                    print("Continuing with fallback to random embeddings for AWS mode.")
                    bedrock_client = None
                else:
                    # Re-raise for general handling below
                    raise test_error
                    
        except NoCredentialsError as e:
            print(f"WARNING: AWS credentials not found or invalid. Details: {e}")
            print("Please ensure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set, or use IAM roles.")
            print("Alternatively, configure AWS CLI with 'aws configure' or use EC2 instance profiles.")
            print("Continuing with fallback to random embeddings for AWS mode.")
            bedrock_client = None
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            if error_code == 'UnauthorizedOperation':
                print(f"WARNING: AWS credentials lack necessary permissions. Details: {error_message}")
                print("Please ensure your AWS credentials have bedrock:* permissions.")
            elif error_code == 'InvalidRegion':
                print(f"WARNING: Invalid AWS region '{AWS_REGION}'. Details: {error_message}")
                print("Please check that Bedrock is available in your specified region.")
                print("Available regions for Bedrock: us-east-1, us-west-2, eu-west-1, ap-southeast-1, ap-northeast-1")
            elif error_code == 'ServiceUnavailableException':
                print(f"WARNING: AWS Bedrock service unavailable in region '{AWS_REGION}'. Details: {error_message}")
                print("Service may be experiencing issues or not available in this region.")
            elif error_code == 'ThrottlingException':
                print(f"WARNING: AWS rate limiting during initialization. Details: {error_message}")
                print("Too many requests during startup. Consider adding delays between operations.")
            else:
                print(f"WARNING: AWS Bedrock client error ({error_code}). Details: {error_message}")
            
            print("Continuing with fallback to random embeddings for AWS mode.")
            bedrock_client = None
            
        except Exception as e:
            # Handle network timeouts and other unexpected errors (Requirement 4.4)
            if hasattr(e, '__class__') and 'timeout' in e.__class__.__name__.lower():
                print(f"WARNING: Network timeout initializing AWS Bedrock client. Details: {e}")
                print("Check network connectivity to AWS services.")
            else:
                print(f"WARNING: Unexpected error initializing AWS Bedrock client. Details: {e}")
            
            print("Continuing with fallback to random embeddings for AWS mode.")
            bedrock_client = None
    elif AI_MODE == "GCP":
        print(f"--- Initializing Vertex AI for project '{GCP_PROJECT}' in '{GCP_LOCATION}'...")
        vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
        model = TextEmbeddingModel.from_pretrained(MODEL_NAME)
        print(f"✅ GCP model '{MODEL_NAME}' configured. Vector dimension: {VECTOR_DIM}")
    elif AI_MODE == "LOCAL":
        print(f"--- Initializing local embedding model '{MODEL_NAME}'...")
        model = SentenceTransformer(MODEL_NAME)
        print(f"✅ Local model '{MODEL_NAME}' configured. Vector dimension: {VECTOR_DIM}")

    if IS_CLUSTER:
        mode_message = "Cluster"
        print(f"\n--- Connecting to Valkey Cluster at entrypoint {VALKEY_HOST}:{VALKEY_PORT}...")
        startup_nodes = [ClusterNode(host=VALKEY_HOST, port=VALKEY_PORT)]
        r = ValkeyCluster(startup_nodes=startup_nodes, decode_responses=True)
        primary_node_objects = r.get_primaries()
        primary_nodes = [{'host': node.host, 'port': node.port} for node in primary_node_objects]

        if not primary_nodes:
            print("Error: Could not find any primary (master) nodes.", file=sys.stderr)
            exit(1)

        r = ValkeyCluster(startup_nodes=startup_nodes)

    else:
        mode_message = "Standalone"
        print(f"\n--- Connecting to standalone Valkey server at {VALKEY_HOST}:{VALKEY_PORT}...")
        r = valkey.Valkey(host=VALKEY_HOST, port=VALKEY_PORT)
        primary_nodes = [{"host": VALKEY_HOST, "port": VALKEY_PORT}]

    r.ping()
    print(f"✅ Successfully connected to Valkey ({mode_message} mode).")

except Exception as e:
    print(f"Error during initialization: {e}")
    if AI_MODE == "AWS":
        print("Please check your AWS credentials, region, and Valkey connection details.")
    elif AI_MODE == "GCP":
        print("Please check your GCP project, authentication, and Valkey connection details.")
    else:
        print("Please check your Valkey connection details and ensure AI libraries are installed.")
    exit(1)


# --- 2. Prepare Nodes for Flushing ---
if FLUSH_DATA:
    print("\n--- Flushing server(s) ...")
    print(f"⚠️  WARNING: This will delete ALL data from the Valkey server! ⚠️")
    print(f"⚠️  WARNING: This operation is irreversible! ⚠️")

    confirm = input("Are you sure you want to proceed? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Operation cancelled by user.")
        exit(0)

    success_count = 0
    error_count = 0
    for node in primary_nodes:
        node_host = node['host']
        node_port = node['port']
        try:
            node_conn = valkey.Valkey(host=node_host, port=node_port)
            node_conn.flushall()
            print(f"✅ Successfully flushed {node_host}:{node_port}")
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to flush {node_host}:{node_port}. Error: {e}", file=sys.stderr)
            error_count += 1
    print(f"Summary: {success_count} node(s) flushed, {error_count} failed.")


# --- 3. Find, Load, and Prepare Data ---
print("\n--- Finding and Preparing Product Data ---")
REQUIRED_PRODUCT_HEADER = [
    "Unnamed: 0",
    "name", "main_category", "sub_category", "image", "link",
    "ratings", "no_of_ratings", "discount_price", "actual_price"
]
matching_csv_paths = []
print(f"Searching for all product data files in '{DATA_DIR}' ...")

for root, dirs, files in os.walk(DATA_DIR):
    for file in files:
        if file.lower().endswith(".csv"):
            potential_path = os.path.join(root, file)
            try:
                df_header = pd.read_csv(potential_path, nrows=0)
                if list(df_header.columns) == REQUIRED_PRODUCT_HEADER:
                    print(f"Found product data file: {potential_path}")
                    matching_csv_paths.append(potential_path)
            except Exception as e:
                print(f"❌ Could not read header of {potential_path}. Skipping. Error: {e}")

if not matching_csv_paths:
    print(f"❌ Error: No CSV files with the required header were found in '{DATA_DIR}' or its subdirectories.")
    exit(1)

print(f"Loading and combining data from {len(matching_csv_paths)} file(s)...")
try:
    list_of_dfs = [
        pd.read_csv(path, index_col=0, on_bad_lines='skip')
        for path in matching_csv_paths
    ]
    df = pd.concat(list_of_dfs, ignore_index=True)
except Exception as e:
    print(f"❌ Error loading or concatenating CSV files. Details: {e}")
    exit(1)
print(f"✅ Data prepared. Processing all {len(df)} records.")



# --- 4. Process Data in Batches (Generate Embeddings and Load to Valkey) ---
print("\n--- Generating Product Embeddings and Loading to Valkey in Batches ---")
for i in tqdm(range(0, len(df), BATCH_SIZE), desc="Processing Batches"):
    batch_df = df.iloc[i:i+BATCH_SIZE]

    texts_to_embed = []
    for index, row in batch_df.iterrows():
        text = f"Product: {row.get('name', '')}. Brand: {extract_brand(row.get('name', ''))}. Category: {row.get('main_category', '')}, {row.get('sub_category', '')}."
        texts_to_embed.append(text)

    if AI_MODE == "AWS":
        embedding_vectors = generate_embeddings_with_titan(bedrock_client, texts_to_embed)
    elif AI_MODE == "GCP":
        response = model.get_embeddings(texts_to_embed)
        embedding_vectors = [item.values for item in response]
    else: # LOCAL mode
        embedding_vectors = model.encode(texts_to_embed, convert_to_numpy=True)

    pipe = r.pipeline(transaction=False)
    for (index, row), embedding_vector in zip(batch_df.iterrows(), embedding_vectors):
        product_key = f"product:{index}"
        brand = extract_brand(row['name'])
        region = random.choice(REGIONS)
        combined_text_for_tags = f"{row['name']} {brand} {row['main_category']} {row['sub_category']} {region}"

        product_data = {
            'id': index,
            'name': row['name'], 'brand': brand, 'main_category': row['main_category'],
            'sub_category': row['sub_category'], 'link': row['link'], 'image_url': row['image'],
            'rating': clean_numeric(row.get('ratings')),
            'review_count': clean_numeric(row.get('no_of_ratings')),
            'price': clean_numeric(row.get('discount_price')),
            'original_price': clean_numeric(row.get('actual_price')),
            'brand_tags': generate_tags(brand), 'search_tags': generate_tags(combined_text_for_tags),
            'region': region,
            'embedding': np.array(embedding_vector, dtype=np.float32).tobytes()
        }
        pipe.hset(product_key, mapping=product_data)

    pipe.execute()

print("✅ Data loading and embedding generation process finished successfully.")



# --- 5. Final Instruction: Create the Full Index (VECTOR_DIM is dynamic) ---
print(f"\n--- Preparing index '{INDEX_NAME}'... ---")
print(f"Index configuration: AI_MODE={AI_MODE}, VECTOR_DIM={VECTOR_DIM}, DISTANCE_METRIC={DISTANCE_METRIC}")

# Log the AI mode specific embedding model information
if AI_MODE == "AWS":
    print(f"AWS Bedrock embedding model: {EMBEDDING_MODEL_NAME} (1024 dimensions)")
elif AI_MODE == "GCP":
    print(f"GCP Vertex AI embedding model: {MODEL_NAME} (768 dimensions)")
else:  # LOCAL
    print(f"Local embedding model: {MODEL_NAME} (384 dimensions)")

# This version is more precise. It attempts to drop the index and will ONLY
# ignore the specific error that Valkey returns when the index doesn't exist.
# Any other error during the drop command will correctly halt the script.
try:
    print(f"Attempting to drop index '{INDEX_NAME}' to ensure a clean slate...")
    r.execute_command("FT.DROPINDEX", INDEX_NAME)
    print(f"✅ Existing index '{INDEX_NAME}' dropped successfully.")
except Exception as e:
    # This is the correct way to handle this: check if the error message
    # indicates the index was not found, which is an expected and safe condition.
    if "Index with name" in str(e):
        print(f"Index '{INDEX_NAME}' did not exist, which is fine.")
    else:
        # If it's a different error, something is wrong, so we re-raise it.
        print(f"❌ An unexpected error occurred while trying to drop the index: {e}")
        raise e

# Now, create the index. This part is guaranteed to run on a clean slate.
try:
    print(f"Creating index '{INDEX_NAME}' with the following specifications:")
    print(f"  - Vector dimension: {VECTOR_DIM} (optimized for {AI_MODE} mode)")
    print(f"  - Distance metric: {DISTANCE_METRIC}")
    print(f"  - Vector type: FLOAT32")
    print(f"  - Algorithm: HNSW")
    print(f"  - Document prefix: {DOC_PREFIX}")
    
    command_args = [
        "FT.CREATE", INDEX_NAME,
        "ON", "HASH",
        "PREFIX", "1", DOC_PREFIX,
        "SCHEMA",
        "brand_tags", "TAG", "SEPARATOR", ",",
        "search_tags", "TAG", "SEPARATOR", ",",
        "region", "TAG",
        "price", "NUMERIC",
        "rating", "NUMERIC",
        "review_count", "NUMERIC",
        "embedding", "VECTOR", "HNSW", "6",
            "TYPE", "FLOAT32",
            "DIM", str(VECTOR_DIM),
            "DISTANCE_METRIC", DISTANCE_METRIC
    ]
    r.execute_command(*command_args)
    print(f"✅ Index '{INDEX_NAME}' created successfully with {VECTOR_DIM}-dimensional vectors for {AI_MODE} backend.")
    print(f"✅ Vector search is now optimized for embeddings generated by {AI_MODE} mode.")

except Exception as e:
    print(f"❌ Failed to create index '{INDEX_NAME}' with {VECTOR_DIM}-dimensional vectors.")
    print(f"AI Mode: {AI_MODE}, Vector Dimension: {VECTOR_DIM}")
    print(f"Details: {e}")
    exit(1)
 
 
 
 # --- 6. Create Users ---
print("\n--- Loading Persona Dataset ---")
PERSONAS_CSV_PATH = "data/personas.csv"
try:
    df = pd.read_csv(PERSONAS_CSV_PATH)
    print(f"✅ Successfully loaded {len(df)} personas from CSV.")
except FileNotFoundError:
    print(f"❌ FATAL: The persona database file '{PERSONAS_CSV_PATH}' was not found.")
    exit(1)

print(f"\n--- Generating Persona Embeddings and Storing {len(df)} in Valkey  ---")

# Process personas in batches for better efficiency, especially for AWS Bedrock (Requirement 5.2)
PERSONA_BATCH_SIZE = 50  # Smaller batch size for personas to balance efficiency and memory usage
pipe = r.pipeline(transaction=False)

for i in tqdm(range(0, len(df), PERSONA_BATCH_SIZE), desc="Processing Persona Batches"):
    batch_df = df.iloc[i:i+PERSONA_BATCH_SIZE]
    
    # Prepare texts for batch embedding generation
    texts_to_embed = []
    persona_info = []  # Store persona data for later processing
    
    for index, persona in batch_df.iterrows():
        user_id = persona['id']
        text = f"User Persona: {persona['bio']} User Interests: {persona['interests_for_embedding']}"
        texts_to_embed.append(text)
        persona_info.append((index, persona, user_id))
    
    # Generate embeddings for the entire batch
    try:
        if AI_MODE == "AWS":
            # Use batch processing for AWS Bedrock embeddings (Requirement 5.2)
            embedding_vectors = generate_embeddings_with_titan(bedrock_client, texts_to_embed)
        elif AI_MODE == "GCP":
            response = model.get_embeddings(texts_to_embed)
            embedding_vectors = [item.values for item in response]
        else:  # LOCAL mode
            embedding_vectors = model.encode(texts_to_embed, convert_to_numpy=True)
    except Exception as e:
        # Enhanced error handling for persona batch embedding generation (Requirement 5.3)
        print(f"WARNING: Could not generate embeddings for persona batch {i//PERSONA_BATCH_SIZE + 1}. "
              f"Using random vector fallbacks for all personas in this batch. "
              f"Processing will continue with remaining batches. Details: {e}")
        # Create fallback embeddings for the entire batch
        embedding_vectors = [np.random.rand(VECTOR_DIM).astype(np.float32) for _ in range(len(texts_to_embed))]
    
    # Process each persona in the batch with its corresponding embedding
    for (index, persona, user_id), embedding_vector in zip(persona_info, embedding_vectors):
        try:
            # Ensure embedding_vector is properly formatted
            if not isinstance(embedding_vector, np.ndarray):
                embedding_vector = np.array(embedding_vector, dtype=np.float32)
            
            # Prepare data for Valkey JSON. The purchase_history is already a JSON string from the CSV.
            persona_data = {
                "id": user_id,
                "name": persona.get("name", f"User {user_id}"),
                "bio": persona.get("bio", ""),
                "purchase_history": json.loads(persona.get("purchase_history", "[]")),
                # "embedding": embedding_vector.tobytes(),
                "embedding": embedding_vector.tolist(),
                "avatar": generate_avatar_data_uri(user_id)
            }
            pipe.execute_command("JSON.SET", user_id, "$", json.dumps(persona_data))
            
        except Exception as e:
            # Individual persona error handling (Requirement 5.3)
            print(f"WARNING: Could not process persona {user_id} ({persona.get('name', 'Unknown')}). "
                  f"Using random vector fallback. Processing will continue with remaining personas. Details: {e}")
            
            # Create fallback embedding and data
            fallback_embedding = np.random.rand(VECTOR_DIM).astype(np.float32)
            persona_data = {
                "id": user_id,
                "name": persona.get("name", f"User {user_id}"),
                "bio": persona.get("bio", ""),
                "purchase_history": json.loads(persona.get("purchase_history", "[]")),
                # "embedding": embedding_vector.tobytes(),
                "embedding": fallback_embedding.tolist(),
                "avatar": generate_avatar_data_uri(user_id)
            }
            pipe.execute_command("JSON.SET", user_id, "$", json.dumps(persona_data))


try:
    print("Saving personas to Valkey ...")
    pipe.execute()
    print("✅ Successfully stored personas in Valkey.")
    
    # Display final statistics for persona processing
    if AI_MODE == "AWS":
        print(f"✅ AWS Bedrock persona processing completed:")
        print(f"   - Total personas processed: {len(df)}")
        print(f"   - Batch size used: {PERSONA_BATCH_SIZE}")
        print(f"   - Vector dimension: {VECTOR_DIM} (Titan Text Embeddings v2)")
        print(f"   - All personas stored successfully in Valkey")
    
except Exception as e:
    print(f"❌ Failed to save personas to Valkey. Error: {e}")
    if AI_MODE == "AWS":
        print(f"❌ AWS Bedrock persona processing failed during Valkey storage")
        print(f"   - Personas processed: {len(df)}")
        print(f"   - Error occurred during final storage step")
