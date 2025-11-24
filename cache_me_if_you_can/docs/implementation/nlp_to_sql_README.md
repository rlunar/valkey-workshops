# Natural Language to SQL Query Generator

Convert natural language queries to SQL using LLMs via Ollama with knowledge base context.

## ⚠️ Important Note

**TinyLlama is too small for accurate SQL generation.** While the script works with TinyLlama, it often hallucinates incorrect table names and generates invalid SQL. 

**Recommended models for better results:**
- `llama3.2` (3B) - Good balance of speed and accuracy
- `llama2` (7B) - Better accuracy
- `mistral` (7B) - Excellent for code generation
- `codellama` (7B+) - Specialized for code

## Prerequisites

1. **Ollama installed and running**
   ```bash
   # Install Ollama (if not already installed)
   # Visit: https://ollama.ai
   
   # Pull a recommended model (choose one)
   ollama pull llama3.2
   ollama pull mistral
   ollama pull codellama
   
   # Start Ollama (if not running)
   ollama serve
   ```

2. **Python dependencies**
   ```bash
   pip install requests
   ```

## Usage

### Demo Mode (Default)

Run with pre-defined test queries:

```bash
cd samples
python nlp_to_sql.py
```

### Interactive Mode

Enter your own queries interactively:

```bash
python nlp_to_sql.py tinyllama interactive
```

### Using Different Models

**Recommended approach** - use a better model:

```bash
# Using Llama 3.2 (RECOMMENDED)
ollama pull llama3.2
uv run python nlp_to_sql.py llama3.2

# Using Mistral (RECOMMENDED)
ollama pull mistral
uv run python nlp_to_sql.py mistral

# Using CodeLlama (RECOMMENDED for SQL)
ollama pull codellama
uv run python nlp_to_sql.py codellama

# Interactive mode with better model
uv run python nlp_to_sql.py llama3.2 interactive
```

## Example Queries

The system can handle various types of queries:

**Simple Lookups:**
- "Get airport by IATA code JFK"
- "Find airline with ID 5"
- "Show passenger with passport P103014"

**Joins:**
- "Get airport with geographic details by IATA code JFK"
- "Show passenger with their contact details"
- "Get flight with airline information"

**Complex Queries:**
- "Show me all flights from JFK to LAX"
- "Find passengers from United States"
- "Get complete booking details with passenger and flight info"

**Aggregations:**
- "How many bookings does passenger 1000 have?"
- "Show the top 10 passengers by number of flights"
- "What are the most profitable routes?"

## How It Works

1. **Knowledge Base Loading**: The system loads JSON files from `../knowledge_base/`:
   - Database schema overview
   - Table definitions with columns and relationships
   - Natural language to SQL conversion guide
   - Example queries with SQL translations

2. **Context Building**: Creates a compact context string with:
   - Database structure
   - Key table schemas
   - Join patterns
   - Conversion rules
   - Example queries

3. **Prompt Engineering**: Builds a prompt with:
   - Knowledge base context
   - Conversion rules
   - The natural language query
   - Instructions for SQL generation

4. **LLM Generation**: Sends to Ollama API with:
   - Low temperature (0.1) for consistency
   - Streaming disabled for complete responses
   - Response cleaning and formatting

## Knowledge Base Files Used

- `database_schema_overview.json` - High-level database structure
- `airport.json`, `flight.json`, `passenger.json`, etc. - Table schemas
- `nl_to_sql_guide.json` - Conversion rules and patterns
- `nl_sql_examples.json` - Example query mappings

## Output Format

The system returns clean SQL queries ready to execute:

```sql
SELECT a.airport_id, a.iata, a.icao, a.name, ag.city, ag.country, ag.latitude, ag.longitude 
FROM airport a 
LEFT JOIN airport_geo ag ON a.airport_id = ag.airport_id 
WHERE a.iata = 'JFK';
```

## Troubleshooting

**Ollama not responding:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
ollama serve
```

**Model not found:**
```bash
# Pull the model
ollama pull tinyllama
```

**Poor quality results:**
- Try a larger model (llama2, mistral)
- Ensure knowledge base files are present
- Check that queries are clear and specific

## Customization

You can modify the system by:

1. **Adjusting temperature** in `generate_sql()` method (lower = more deterministic)
2. **Adding more examples** to `nl_sql_examples.json`
3. **Updating conversion rules** in `nl_to_sql_guide.json`
4. **Using different models** via command line argument
