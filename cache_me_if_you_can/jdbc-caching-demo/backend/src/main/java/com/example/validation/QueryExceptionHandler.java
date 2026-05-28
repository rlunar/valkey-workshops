package com.example.validation;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;

import java.util.Map;

@ControllerAdvice
public class QueryExceptionHandler {

    @ExceptionHandler(InvalidQueryException.class)
    public ResponseEntity<Map<String, String>> handleInvalidQuery(InvalidQueryException ex) {
        return ResponseEntity
                .status(HttpStatus.BAD_REQUEST)
                .body(Map.of("error", ex.getUserMessage()));
    }
}
