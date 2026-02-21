# Company Intelligence Assistant — Specification

> Source: <https://sites.google.com/gen.tech/aileadtesttask/home>

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

## Context

This is a test task from **OBRIO (Nebula)** — a product IT company within the Genesis ecosystem. The team of 350+ professionals develops Nebula, the largest brand in the spiritual self-discovery niche with 70M+ users globally. Nebula holds multiple #1 rankings in Apple Store and Play Market across USA, Canada, and Australia (iOS, Android, Web).
