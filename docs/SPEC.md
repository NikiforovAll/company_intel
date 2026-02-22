# Company Intelligence Assistant — Specification

## Overview

Build a tool that allows users to enter the name of a company, automatically gathers as much information about it as possible from public sources, builds a local knowledge base, and enables a chat interface to ask questions about the company without using the internet.

## Core Requirements

### 1. Input

- Accept company names as input (e.g., Figma, Spotify, Airbnb)

### 2. Data Collection

Retrieve content from publicly available sources:

- Company websites
- Wikipedia
- News articles
- Crunchbase
- Other publicly available sources

### 3. Storage

- Structure and store information locally
- Use embeddings or comparable search-optimized formats

### 4. Chat Interface

Implement CLI or web chat enabling questions such as:

- Who are the company's competitors?
- What is the company's business model?
- When was the company founded?
- How does the company make money?

### 5. Constraints

- Answers must be derived **exclusively** from stored information
- **No live web access** during the chat/query phase

