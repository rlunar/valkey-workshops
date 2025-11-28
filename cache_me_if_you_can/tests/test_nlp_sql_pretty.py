#!/usr/bin/env python3
"""
Quick test of the enhanced NLP to SQL with rich pretty printing and validation
"""

from daos.nlp_to_sql import NLPToSQL

# Test SQL validation and pretty printing
converter = NLPToSQL(knowledge_base_path="knowledge_base", model="tinyllama")

# Test with some sample SQL queries
test_sqls = [
    # Valid SQL
    "SELECT * FROM airport WHERE iata_code = 'JFK' LIMIT 10",
    
    # SQL with warning (no LIMIT)
    "SELECT airport_id, name FROM airport WHERE country = 'USA'",
    
    # Invalid SQL (unbalanced parentheses)
    "SELECT * FROM airport WHERE (iata_code = 'JFK' LIMIT 10",
    
    # Invalid SQL (unbalanced quotes)
    "SELECT * FROM airport WHERE name = 'O'Hare LIMIT 10",
]

print("\n" + "=" * 70)
print("Testing SQL Validation and Pretty Printing")
print("=" * 70)

for i, sql in enumerate(test_sqls, 1):
    print(f"\n\nTest {i}:")
    converter.pretty_print_sql(sql, title=f"Test Query {i}")
