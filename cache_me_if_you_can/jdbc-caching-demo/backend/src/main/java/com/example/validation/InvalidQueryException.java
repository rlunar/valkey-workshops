package com.example.validation;

public class InvalidQueryException extends RuntimeException {
    private final String userMessage;

    public InvalidQueryException(String userMessage) {
        super(userMessage);
        this.userMessage = userMessage;
    }

    public String getUserMessage() {
        return userMessage;
    }
}
