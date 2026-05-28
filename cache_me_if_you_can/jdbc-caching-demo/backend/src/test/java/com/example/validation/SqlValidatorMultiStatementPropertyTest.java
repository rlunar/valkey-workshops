package com.example.validation;

import net.jqwik.api.*;

import java.util.List;

// Feature: jdbc-query-cache-workshop, Property 3: Multi-statement rejection
/**
 * Property-based test for multi-statement query rejection.
 *
 * Validates: Requirements 7.6
 *
 * Property 3: Multi-statement rejection
 * For any SQL string that contains a semicolon followed by one or more additional
 * non-whitespace characters (indicating a multi-statement query), the SQL validator
 * SHALL reject the query regardless of whether the first statement is a valid SELECT.
 */
class SqlValidatorMultiStatementPropertyTest {

    private static final List<String> SECOND_STATEMENTS = List.of(
        "DROP TABLE users",
        "DELETE FROM accounts",
        "INSERT INTO logs VALUES (1, 'x')",
        "UPDATE users SET name = 'hacked'",
        "SELECT 1",
        "TRUNCATE TABLE sessions",
        "ALTER TABLE users ADD COLUMN pwned INT",
        "CREATE TABLE evil (id INT)",
        "GRANT ALL ON *.* TO attacker",
        "REVOKE SELECT ON db.* FROM user"
    );

    // --- Generators ---

    @Provide
    Arbitrary<String> validSelectFirstStatement() {
        Arbitrary<String> selectKeyword = selectKeywordVariant();
        Arbitrary<String> columns = columnList();
        Arbitrary<String> tables = tableName();
        Arbitrary<String> whereClauses = whereClause();

        return Combinators.combine(selectKeyword, columns, tables, whereClauses)
            .as((sel, cols, tbl, where) -> sel + " " + cols + " FROM " + tbl + where);
    }

    @Provide
    Arbitrary<String> semicolonSpacing() {
        return Arbitraries.of(";", "; ", ";  ", ";\t", ";\n", "; \t");
    }

    @Provide
    Arbitrary<String> secondStatements() {
        return Arbitraries.of(SECOND_STATEMENTS);
    }

    @Provide
    Arbitrary<String> multiStatementQueries() {
        return Combinators.combine(validSelectFirstStatement(), semicolonSpacing(), secondStatements())
            .as((first, sep, second) -> first + sep + second);
    }

    @Provide
    Arbitrary<String> multiStatementWithLeadingWhitespace() {
        Arbitrary<String> whitespace = Arbitraries.of(" ", "  ", "\t", "\n", "\r\n", "  \t\n");
        return Combinators.combine(whitespace, multiStatementQueries())
            .as((ws, query) -> ws + query);
    }

    @Provide
    Arbitrary<String> multiStatementWithLeadingComments() {
        Arbitrary<String> comment = Arbitraries.of(
            "/* comment */ ",
            "/* multi\nline */ ",
            "-- line comment\n",
            "/* hint */ -- another\n"
        );
        return Combinators.combine(comment, multiStatementQueries())
            .as((c, query) -> c + query);
    }

    // --- Property Tests ---

    /**
     * Validates: Requirements 7.6
     *
     * Any valid SELECT followed by a semicolon and another statement must be rejected
     * with the message "Multi-statement queries are not allowed".
     */
    @Property(tries = 100)
    void multiStatementQueriesAlwaysRejected(
            @ForAll("multiStatementQueries") String query) {
        try {
            SqlValidator.validate(query);
            throw new AssertionError("Expected InvalidQueryException for: " + query);
        } catch (InvalidQueryException e) {
            if (!"Multi-statement queries are not allowed".equals(e.getMessage())) {
                throw new AssertionError(
                    "Expected message 'Multi-statement queries are not allowed' but got: '"
                    + e.getMessage() + "' for query: " + query);
            }
        }
    }

    /**
     * Validates: Requirements 7.6
     *
     * Multi-statement queries with leading whitespace must still be rejected.
     */
    @Property(tries = 100)
    void multiStatementWithLeadingWhitespaceRejected(
            @ForAll("multiStatementWithLeadingWhitespace") String query) {
        try {
            SqlValidator.validate(query);
            throw new AssertionError("Expected InvalidQueryException for: " + query);
        } catch (InvalidQueryException e) {
            if (!"Multi-statement queries are not allowed".equals(e.getMessage())) {
                throw new AssertionError(
                    "Expected message 'Multi-statement queries are not allowed' but got: '"
                    + e.getMessage() + "' for query: " + query);
            }
        }
    }

    /**
     * Validates: Requirements 7.6
     *
     * Multi-statement queries with leading SQL comments must still be rejected.
     */
    @Property(tries = 100)
    void multiStatementWithLeadingCommentsRejected(
            @ForAll("multiStatementWithLeadingComments") String query) {
        try {
            SqlValidator.validate(query);
            throw new AssertionError("Expected InvalidQueryException for: " + query);
        } catch (InvalidQueryException e) {
            if (!"Multi-statement queries are not allowed".equals(e.getMessage())) {
                throw new AssertionError(
                    "Expected message 'Multi-statement queries are not allowed' but got: '"
                    + e.getMessage() + "' for query: " + query);
            }
        }
    }

    /**
     * Validates: Requirements 7.6
     *
     * Various spacing between the semicolon and the second statement must all be rejected,
     * as long as there is at least one non-whitespace character after the semicolon.
     */
    @Property(tries = 100)
    void variousSpacingBetweenStatementsRejected(
            @ForAll("validSelectFirstStatement") String firstStmt,
            @ForAll("secondStatements") String secondStmt) {
        // The pattern ;\\s*\\S requires non-whitespace after the semicolon.
        // All our second statements start with a non-whitespace character,
        // so even with spacing they should be detected.
        String query = firstStmt + "; " + secondStmt;
        try {
            SqlValidator.validate(query);
            throw new AssertionError("Expected InvalidQueryException for: " + query);
        } catch (InvalidQueryException e) {
            if (!"Multi-statement queries are not allowed".equals(e.getMessage())) {
                throw new AssertionError(
                    "Expected message 'Multi-statement queries are not allowed' but got: '"
                    + e.getMessage() + "' for query: " + query);
            }
        }
    }

    // --- Helper Generators ---

    private Arbitrary<String> selectKeywordVariant() {
        return Arbitraries.of("SELECT", "select", "Select", "sElEcT");
    }

    private Arbitrary<String> columnList() {
        Arbitrary<String> singleCol = identifier();
        return singleCol.list().ofMinSize(1).ofMaxSize(4)
            .map(cols -> String.join(", ", cols));
    }

    private Arbitrary<String> tableName() {
        return identifier();
    }

    private Arbitrary<String> identifier() {
        return Arbitraries.strings()
            .withCharRange('a', 'z')
            .ofMinLength(2)
            .ofMaxLength(10);
    }

    private Arbitrary<String> whereClause() {
        return Arbitraries.of(
            "",
            " WHERE id > 0",
            " WHERE name IS NOT NULL",
            " WHERE status = 'active'",
            " WHERE created_at > '2020-01-01'"
        );
    }
}
