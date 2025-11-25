# Natural Language to SQL (NLP to SQL)

## Overview

Natural Language to SQL (NLP to SQL) is a technique that uses Generative AI models to convert human-readable questions into executable SQL queries. This approach democratizes database access by allowing users to query databases using natural language instead of learning SQL syntax.

## Core Concepts

### 1. Knowledge Base Context

The system uses a structured knowledge base containing:
- **Database Schema**: Table structures, columns, data types, relationships
- **Query Patterns**: Common SQL patterns and best practices
- **Example Queries**: Natural language to SQL mappings
- **Conversion Rules**: Entity recognition and keyword mappings

### 2. Prompt Engineering

The system constructs a comprehensive prompt that includes:
- Database schema information
- Table relationships and foreign keys
- Query examples and patterns
- Conversion rules and best practices
- The user's natural language query

### 3. LLM Integration

Uses Ollama (local LLM runtime) to:
- Process the enriched prompt
- Generate SQL queries based on context
- Apply learned patterns from examples
- Follow specified rules and constraints

## Architecture Flow

```mermaid
graph TB
    A[User Input: Natural Language Query] --> B[NLPToSQL Class]
    B --> C[Load Knowledge Base]
    C --> D[Database Schema]
    C --> E[Query Patterns]
    C --> F[Example Queries]
    C --> G[Conversion Rules]
    
    D --> H[Build Context String]
    E --> H
    F --> H
    G --> H
    
    H --> I[Construct Prompt]
    A --> I
    
    I --> J[Send to Ollama API]
    J --> K[LLM Processing]
    K --> L[Generated SQL Response]
    
    L --> M[Clean & Parse Response]
    M --> N[Validate SQL]
    N --> O[Format & Display]
    
    style A fill:#e1f5ff
    style J fill:#fff4e1
    style K fill:#ffe1e1
    style O fill:#e1ffe1
```

## Detailed Component Flow

### Knowledge Base Loading

```mermaid
sequenceDiagram
    participant Init as Initialization
    participant KB as Knowledge Base
    participant Files as JSON Files
    participant Context as Context Builder
    
    Init->>KB: Load Knowledge Base
    KB->>Files: Read database_schema_overview.json
    Files-->>KB: Database metadata
    KB->>Files: Read table schemas (airport, flight, etc.)
    Files-->>KB: Table structures
    KB->>Files: Read query_patterns.json
    Files-->>KB: SQL patterns
    KB->>Files: Read nl_sql_examples.json
    Files-->>KB: Example mappings
    KB->>Context: Combine all information
    Context-->>Init: Formatted context string
    
    Note over Context: Context includes:<br/>- Table schemas<br/>- Foreign keys<br/>- Query examples<br/>- Conversion rules
```

### Query Generation Process

```mermaid
sequenceDiagram
    participant User
    participant NLP as NLPToSQL
    participant Prompt as Prompt Builder
    participant Ollama as Ollama API
    participant Clean as SQL Cleaner
    participant Valid as Validator
    
    User->>NLP: "Show flights from JFK to LAX"
    NLP->>Prompt: Build prompt with context
    Prompt-->>NLP: Complete prompt
    NLP->>Ollama: POST /api/generate
    
    Note over Ollama: Model: codellama<br/>Temperature: 0.1<br/>Processing...
    
    Ollama-->>NLP: Raw SQL response
    NLP->>Clean: Remove markdown, explanations
    Clean-->>NLP: Clean SQL query
    NLP->>Valid: Validate syntax
    Valid-->>NLP: Validation result
    NLP-->>User: Formatted SQL + Stats
```

## Ollama Integration

### How Ollama Works

```mermaid
graph LR
    A[Application] -->|HTTP POST| B[Ollama Server<br/>localhost:11434]
    B --> C{Model Loaded?}
    C -->|No| D[Load Model<br/>codellama/llama2]
    C -->|Yes| E[Process Request]
    D --> E
    E --> F[Tokenize Prompt]
    F --> G[Generate Tokens]
    G --> H[Decode Response]
    H -->|JSON Response| A
    
    style B fill:#4a90e2
    style E fill:#f39c12
    style G fill:#e74c3c
```

### Request/Response Flow

```mermaid
sequenceDiagram
    participant App as Application
    participant API as Ollama API
    participant Model as LLM Model
    participant GPU as GPU/CPU
    
    App->>API: POST /api/generate
    Note over App,API: Payload:<br/>{model, prompt, options}
    
    API->>Model: Load model if needed
    Model->>GPU: Allocate resources
    
    API->>Model: Tokenize prompt
    Model-->>API: Token IDs
    
    loop Generate Tokens
        API->>GPU: Process next token
        GPU-->>API: Token prediction
    end
    
    API->>Model: Decode tokens to text
    Model-->>API: Generated SQL
    
    API-->>App: JSON Response
    Note over API,App: {response, tokens,<br/>timing stats}
```

## Pseudocode Examples

### 1. Initialization

```pseudocode
CLASS NLPToSQL:
    FUNCTION __init__(knowledge_base_path, model):
        // Load configuration from environment
        SET kb_path = knowledge_base_path OR env.KNOWLEDGE_BASE_PATH
        SET ollama_url = env.OLLAMA_URL OR "http://localhost:11434/api/generate"
        SET model = model OR env.OLLAMA_MODEL OR "codellama"
        
        // Load and prepare context
        SET context = load_knowledge_base()
        
        // Calculate statistics
        CALCULATE context_lines, context_chars, estimated_tokens
        DISPLAY initialization_info()
```

### 2. Knowledge Base Loading

```pseudocode
FUNCTION load_knowledge_base():
    INITIALIZE context_parts = []
    
    // Load database overview
    IF EXISTS(kb_path / "database_schema_overview.json"):
        overview = READ_JSON("database_schema_overview.json")
        APPEND "=== DATABASE OVERVIEW ===" TO context_parts
        APPEND database_name, description TO context_parts
        
        FOR EACH table IN overview.tables:
            APPEND table.name, table.description TO context_parts
    
    // Load table schemas
    tables = ["airport", "flight", "passenger", "booking", ...]
    APPEND "=== TABLE SCHEMAS ===" TO context_parts
    
    FOR EACH table_name IN tables:
        IF EXISTS(kb_path / "{table_name}.json"):
            table_data = READ_JSON("{table_name}.json")
            APPEND table_name TO context_parts
            APPEND columns, types TO context_parts
            APPEND foreign_keys TO context_parts
            APPEND indexes TO context_parts
    
    // Load query patterns
    IF EXISTS(kb_path / "query_patterns.json"):
        patterns = READ_JSON("query_patterns.json")
        APPEND "=== QUERY PATTERNS ===" TO context_parts
        FOR EACH pattern IN patterns.patterns:
            APPEND pattern.name, use_case, example TO context_parts
    
    // Load NL to SQL examples
    IF EXISTS(kb_path / "nl_sql_examples.json"):
        examples = READ_JSON("nl_sql_examples.json")
        APPEND "=== EXAMPLE QUERIES ===" TO context_parts
        FOR EACH example IN examples:
            APPEND example.prompt, example.sql TO context_parts
    
    RETURN JOIN(context_parts, "\n")
```

### 3. Prompt Construction

```pseudocode
FUNCTION build_prompt(natural_language_query):
    prompt = """
    You are a SQL query generator for the Flughafen airport database.
    
    {context}
    
    IMPORTANT RULES:
    1. Use backticks for reserved keywords: `from`, `to`
    2. Use table aliases: a (airport), f (flight), p (passenger)
    3. Use LEFT JOIN for optional relationships
    4. Use INNER JOIN for required relationships
    5. Always add LIMIT clause
    6. Return ONLY the SQL query, no explanations
    7. Use best practices
    8. Be explicit about table names and fields
    9. Use LIMIT and OFFSET for pagination
    
    Natural Language Query: {natural_language_query}
    
    SQL Query:
    """
    
    RETURN prompt
```

### 4. SQL Generation

```pseudocode
FUNCTION generate_sql(natural_language_query):
    // Build the prompt
    prompt = build_prompt(natural_language_query)
    
    // Prepare API payload
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": false,
        "options": {
            "temperature": 0.1,    // Low for deterministic output
            "top_p": 0.9,          // Nucleus sampling
            "top_k": 40            // Top-k sampling
        }
    }
    
    TRY:
        // Send request to Ollama
        START_TIMER()
        response = HTTP_POST(ollama_url, payload, timeout=120)
        END_TIMER()
        
        // Extract response
        result = PARSE_JSON(response)
        sql_query = result.response.STRIP()
        
        // Clean the SQL
        sql_query = clean_sql(sql_query)
        
        // Return with metadata
        RETURN {
            "sql": sql_query,
            "time_taken": elapsed_time,
            "prompt_eval_count": result.prompt_eval_count,
            "eval_count": result.eval_count,
            "total_tokens": prompt_tokens + output_tokens
        }
    
    CATCH RequestException AS e:
        RETURN {
            "sql": "Error: " + e.message,
            "time_taken": 0,
            "tokens": 0
        }
```

### 5. SQL Cleaning

```pseudocode
FUNCTION clean_sql(sql):
    // Remove markdown code blocks
    sql = REMOVE(sql, "```sql", "```")
    
    // Remove common prefixes
    prefixes = ["SQL Query:", "Query:", "SQL:"]
    FOR EACH prefix IN prefixes:
        IF sql.STARTS_WITH(prefix):
            sql = sql.SUBSTRING(LENGTH(prefix)).STRIP()
    
    // Split into lines
    lines = SPLIT(sql, "\n")
    sql_lines = []
    found_semicolon = false
    
    FOR EACH line IN lines:
        line_stripped = STRIP(line)
        
        // Skip empty lines at start
        IF EMPTY(sql_lines) AND EMPTY(line_stripped):
            CONTINUE
        
        // Check for explanation patterns
        explanation_patterns = [
            "this sql", "this query", "note:", 
            "explanation:", "this will"
        ]
        
        is_explanation = ANY(
            line_stripped.STARTS_WITH(pattern) 
            FOR pattern IN explanation_patterns
        )
        
        // Stop if we hit an explanation after SQL
        IF NOT EMPTY(sql_lines) AND is_explanation:
            BREAK
        
        // Check for SQL keywords
        sql_keywords = [
            "SELECT", "FROM", "WHERE", "JOIN", 
            "LIMIT", "ORDER", "GROUP"
        ]
        
        first_word = FIRST_WORD(line_stripped).UPPER()
        
        IF EMPTY(sql_lines):
            // First line must start with SQL keyword
            IF first_word IN sql_keywords:
                APPEND line TO sql_lines
        ELSE:
            // Subsequent lines
            IF NOT EMPTY(line_stripped) AND NOT is_explanation:
                APPEND line TO sql_lines
                IF ";" IN line:
                    found_semicolon = true
    
    // Join and clean
    sql = JOIN(sql_lines, "\n").STRIP()
    sql = REMOVE_TRAILING(sql, ";").STRIP()
    
    RETURN sql
```

### 6. SQL Validation

```pseudocode
FUNCTION validate_sql(sql):
    result = {
        "is_valid": false,
        "formatted_sql": "",
        "errors": [],
        "warnings": []
    }
    
    TRY:
        // Parse SQL
        parsed = SQL_PARSE(sql)
        
        IF EMPTY(parsed):
            APPEND "Empty or invalid SQL query" TO result.errors
            RETURN result
        
        // Format SQL
        result.formatted_sql = SQL_FORMAT(sql, {
            "reindent": true,
            "keyword_case": "upper",
            "indent_width": 2
        })
        
        // Validation checks
        sql_upper = UPPER(sql)
        
        IF NOT CONTAINS(parsed, "SELECT"):
            APPEND "Not a SELECT statement" TO result.warnings
        
        IF CONTAINS(sql_upper, "SELECT *"):
            APPEND "Using SELECT * - specify columns" TO result.warnings
        
        IF NOT CONTAINS(sql_upper, "LIMIT"):
            APPEND "No LIMIT clause" TO result.warnings
        
        // Check balanced parentheses
        IF COUNT(sql, "(") != COUNT(sql, ")"):
            APPEND "Unbalanced parentheses" TO result.errors
            RETURN result
        
        // Check balanced quotes
        IF COUNT(sql, "'") % 2 != 0:
            APPEND "Unbalanced quotes" TO result.errors
            RETURN result
        
        // Mark as valid
        result.is_valid = true
        
    CATCH Exception AS e:
        APPEND "Parsing error: " + e.message TO result.errors
    
    RETURN result
```

## Key Parameters

### Ollama Configuration

```pseudocode
ollama_options = {
    "temperature": 0.1,     // Low = more deterministic, focused
                            // High = more creative, varied
    
    "top_p": 0.9,          // Nucleus sampling threshold
                            // Consider tokens with cumulative 
                            // probability up to 0.9
    
    "top_k": 40,           // Consider only top 40 tokens
                            // Limits vocabulary at each step
    
    "stream": false        // Get complete response at once
                            // vs. streaming tokens
}
```

### Temperature Effects

```mermaid
graph LR
    A[Temperature] --> B{Value}
    B -->|0.0 - 0.3| C[Deterministic<br/>Consistent SQL]
    B -->|0.4 - 0.7| D[Balanced<br/>Some Variation]
    B -->|0.8 - 1.0| E[Creative<br/>More Diverse]
    
    C --> F[Best for:<br/>Production queries]
    D --> G[Best for:<br/>Exploration]
    E --> H[Best for:<br/>Alternatives]
    
    style C fill:#90EE90
    style D fill:#FFD700
    style E fill:#FF6347
```

## Performance Metrics

### Token Processing

```mermaid
graph TB
    A[Total Processing Time] --> B[Prompt Evaluation]
    A --> C[Response Generation]
    
    B --> D[Input Tokens<br/>prompt_eval_count]
    C --> E[Output Tokens<br/>eval_count]
    
    D --> F[Context Size<br/>~4000-8000 tokens]
    E --> G[SQL Query<br/>~50-200 tokens]
    
    F --> H[Evaluation Speed<br/>tokens/second]
    G --> H
    
    style A fill:#e1f5ff
    style B fill:#fff4e1
    style C fill:#ffe1e1
    style H fill:#e1ffe1
```

### Typical Metrics

```pseudocode
// Example performance metrics
metrics = {
    "context_size": "4000-8000 tokens",
    "input_tokens": "4000-8000 (context + query)",
    "output_tokens": "50-200 (SQL query)",
    "generation_time": "2-10 seconds",
    "tokens_per_second": "20-50 tokens/s",
    "output_input_ratio": "0.01-0.05"
}
```

## Error Handling

```mermaid
graph TD
    A[Generate SQL] --> B{Ollama Available?}
    B -->|No| C[Connection Error]
    B -->|Yes| D{Model Loaded?}
    D -->|No| E[Model Loading Error]
    D -->|Yes| F{Valid Response?}
    F -->|No| G[Parse Error]
    F -->|Yes| H[Clean SQL]
    H --> I{Valid SQL?}
    I -->|No| J[Validation Warnings]
    I -->|Yes| K[Success]
    
    C --> L[Return Error Message]
    E --> L
    G --> L
    J --> M[Return with Warnings]
    K --> N[Return Clean SQL]
    
    style C fill:#ff6b6b
    style E fill:#ff6b6b
    style G fill:#ff6b6b
    style J fill:#ffd93d
    style K fill:#6bcf7f
```

## Best Practices

### 1. Context Optimization

```pseudocode
// Keep context focused and relevant
context_strategy = {
    "include": [
        "Relevant table schemas only",
        "Common query patterns",
        "5-10 example queries",
        "Critical foreign key relationships"
    ],
    
    "exclude": [
        "Unused tables",
        "Excessive examples",
        "Redundant information",
        "Implementation details"
    ],
    
    "optimize": [
        "Use concise descriptions",
        "Prioritize recent patterns",
        "Group related information",
        "Limit token count to 8000"
    ]
}
```

### 2. Prompt Engineering

```pseudocode
// Effective prompt structure
prompt_structure = {
    "1_role": "Define AI role and purpose",
    "2_context": "Provide database schema and rules",
    "3_examples": "Show input/output patterns",
    "4_constraints": "Specify limitations and requirements",
    "5_query": "Present user's natural language query",
    "6_instruction": "Clear output format instruction"
}
```

### 3. Response Processing

```pseudocode
// Clean and validate responses
response_pipeline = [
    "Remove markdown formatting",
    "Strip explanatory text",
    "Extract pure SQL",
    "Validate syntax",
    "Format consistently",
    "Check for common issues",
    "Add helpful warnings"
]
```

## Use Cases

### Simple Queries
- Single table lookups
- Basic filtering
- Column selection

### Complex Queries
- Multi-table joins
- Aggregations and grouping
- Subqueries
- Window functions

### Advanced Patterns
- Recursive CTEs
- Conditional logic
- Date/time operations
- String manipulation

## Limitations

1. **Context Window**: Limited by model's token capacity
2. **Accuracy**: Depends on quality of examples and schema
3. **Complexity**: Very complex queries may need refinement
4. **Ambiguity**: Natural language can be interpreted multiple ways
5. **Performance**: Generation takes 2-10 seconds per query

## Future Enhancements

```mermaid
graph LR
    A[Current System] --> B[Query Refinement Loop]
    A --> C[Multi-Model Support]
    A --> D[Query Optimization]
    A --> E[Caching Layer]
    A --> F[Feedback Learning]
    
    B --> G[Iterative Improvement]
    C --> H[Model Selection]
    D --> I[Performance Tuning]
    E --> J[Faster Responses]
    F --> K[Better Accuracy]
    
    style A fill:#4a90e2
    style G fill:#6bcf7f
    style H fill:#6bcf7f
    style I fill:#6bcf7f
    style J fill:#6bcf7f
    style K fill:#6bcf7f
```

## Conclusion

NLP to SQL bridges the gap between natural language and database queries by leveraging:
- **Structured knowledge bases** for context
- **LLM capabilities** for understanding and generation
- **Prompt engineering** for accurate results
- **Validation and formatting** for reliability

This approach makes database querying accessible to non-technical users while maintaining the power and precision of SQL.
