"""Code-aware tokenizer for BM25 lexical indexing and search query processing."""

import re

# Regex patterns for camelCase, PascalCase, snake_case, and identifier boundaries
RAW_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_\-\./]+")
CAMEL_SPLIT_PATTERN1 = re.compile(r"([a-z0-9])([A-Z])")
CAMEL_SPLIT_PATTERN2 = re.compile(r"([A-Z]+)([A-Z][a-z])")
PUNCTUATION_STRIP_PATTERN = re.compile(r"^[\s\._\-\/]+|[\s\._\-\/]+$")


class CodeTokenizer:
    """Tokenizer designed for code identifiers, qualified names, file paths, and natural text queries."""

    def __init__(self, preserve_original_case: bool = False) -> None:
        self.preserve_original_case = preserve_original_case

    def tokenize(self, text: str) -> list[str]:
        """Tokenize code text or query string into code-aware lexical tokens.

        Preserves exact identifiers (case-folded) alongside camelCase, PascalCase, snake_case,
        and path-separated sub-words.

        Args:
            text: Raw source code, metadata, or query string.

        Returns:
            List of normalized token strings.
        """
        if not text or not text.strip():
            return []

        tokens: list[str] = []
        raw_matches = RAW_TOKEN_PATTERN.findall(text)

        for raw_token in raw_matches:
            clean_raw = PUNCTUATION_STRIP_PATTERN.sub("", raw_token)
            if not clean_raw:
                continue

            lower_raw = clean_raw.lower()

            # 1. Preserve original full token (case-folded)
            tokens.append(lower_raw)

            # 2. Decompose sub-words (camelCase, snake_case, paths, dots)
            sub_words = self._decompose_identifier(clean_raw)
            for sub_w in sub_words:
                sub_lower = sub_w.lower()
                # Append sub-word if it's non-empty and distinct from full token
                if sub_lower and sub_lower != lower_raw:
                    tokens.append(sub_lower)

        return tokens

    def _decompose_identifier(self, identifier: str) -> list[str]:
        """Decompose an identifier into constituent sub-word tokens."""
        # Replace path slashes, dots, hyphens, and underscores with space delimiters
        parts = re.split(r"[\s\._\-\/]+", identifier)
        sub_words: list[str] = []

        for part in parts:
            clean_part = part.strip()
            if not clean_part:
                continue

            # Preserve whole sub-identifier (e.g. "AuthService", "PaymentService")
            sub_words.append(clean_part)

            # Expand camelCase / PascalCase transitions: e.g. "PaymentService" -> "Payment Service"
            s1 = CAMEL_SPLIT_PATTERN1.sub(r"\1 \2", clean_part)
            s2 = CAMEL_SPLIT_PATTERN2.sub(r"\1 \2", s1)

            for word in s2.split():
                clean_word = word.strip()
                if clean_word and clean_word.lower() != clean_part.lower():
                    sub_words.append(clean_word)

        return sub_words


# Default singleton instance
default_tokenizer = CodeTokenizer()


def tokenize_code(text: str) -> list[str]:
    """Convenience function to tokenize code text using default CodeTokenizer."""
    return default_tokenizer.tokenize(text)


def tokenize_query(query: str) -> list[str]:
    """Convenience function to tokenize search query using default CodeTokenizer."""
    return default_tokenizer.tokenize(query)
