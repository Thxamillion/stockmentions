import re
import os
from typing import List, Tuple, Set

class TickerExtractor:
    def __init__(self):
        self.valid_tickers = self._load_ticker_list()
        self.stoplist = self._load_stoplist()
        self.finance_context_words = {
            'stock', 'stocks', 'shares', 'share', 'earnings', 'options', 'calls', 'puts',
            'price', 'target', 'buy', 'sell', 'hold', 'bullish', 'bearish', 'dd',
            'analysis', 'revenue', 'profit', 'margin', 'valuation', 'trade', 'trading',
            'portfolio', 'investment', 'invest', 'market', 'equity', 'security',
            'dividend', 'yield', 'eps', 'pe', 'ratio', 'financials', 'quarterly',
            'annual', 'report', 'guidance', 'forecast', 'catalyst', 'moat'
        }

        # Regex patterns
        self.cashtag_pattern = re.compile(r'\$([A-Z]{1,5})\b')
        self.caps_word_pattern = re.compile(r'\b([A-Z]{1,5})\b')
        self.word_boundary_pattern = re.compile(r'\b\w+\b')

    def _load_ticker_list(self) -> Set[str]:
        """Load valid ticker symbols from file"""
        ticker_file = os.path.join(os.path.dirname(__file__), 'tickers', 'tickers_list.txt')
        try:
            with open(ticker_file, 'r') as f:
                return set(line.strip().upper() for line in f if line.strip())
        except FileNotFoundError:
            print(f"Warning: Ticker list file not found at {ticker_file}")
            return set()

    def _load_stoplist(self) -> Set[str]:
        """Load words to exclude from ticker detection"""
        return {
            'A', 'AI', 'ALL', 'FOR', 'ON', 'OR', 'IT', 'DD', 'YOLO', 'RH', 'OPEN',
            'ARE', 'ONE', 'CAR', 'WELL', 'RUN', 'IN', 'GO', 'SO', 'UP', 'NOW',
            'OUT', 'LIVE', 'AT', 'BE', 'BY', 'DO', 'HE', 'IF', 'MY', 'NO',
            'OF', 'TO', 'WE', 'AN', 'AS', 'HI', 'IS', 'ME', 'US', 'AM', 'EG'
        }

    def extract_tickers(self, text: str) -> List[Tuple[str, float]]:
        """
        Extract ticker symbols from text with confidence scores
        Returns: List of (ticker, confidence) tuples
        """
        if not text:
            return []

        text_upper = text.upper()
        found_tickers = []

        # 1. Extract cashtag format ($TICKER) - highest confidence
        cashtag_matches = self.cashtag_pattern.findall(text_upper)
        for ticker in cashtag_matches:
            if self._is_valid_ticker(ticker):
                found_tickers.append((ticker, 0.99))

        # 2. Extract all-caps words and validate
        caps_matches = self.caps_word_pattern.findall(text_upper)
        for ticker in caps_matches:
            if self._is_valid_ticker(ticker) and ticker not in [t[0] for t in found_tickers]:
                confidence = self._calculate_context_confidence(ticker, text_upper)
                if confidence > 0.5:  # Only include if reasonable confidence
                    found_tickers.append((ticker, confidence))

        # Remove duplicates and sort by confidence
        seen = set()
        unique_tickers = []
        for ticker, confidence in sorted(found_tickers, key=lambda x: x[1], reverse=True):
            if ticker not in seen:
                seen.add(ticker)
                unique_tickers.append((ticker, confidence))

        return unique_tickers

    def _is_valid_ticker(self, ticker: str) -> bool:
        """Check if ticker is valid and not in stoplist"""
        ticker = ticker.upper()

        # Check length
        if len(ticker) < 1 or len(ticker) > 5:
            return False

        # Check stoplist
        if ticker in self.stoplist:
            return False

        # Check against valid ticker list
        if self.valid_tickers and ticker not in self.valid_tickers:
            return False

        return True

    def _calculate_context_confidence(self, ticker: str, text: str) -> float:
        """Calculate confidence based on surrounding context"""
        words = self.word_boundary_pattern.findall(text.lower())

        # Find positions of the ticker
        ticker_positions = [i for i, word in enumerate(words) if word.upper() == ticker]

        if not ticker_positions:
            return 0.7  # Default confidence for valid ticker

        # Look for finance context words within 8 words of ticker mentions
        context_found = False
        for pos in ticker_positions:
            start = max(0, pos - 8)
            end = min(len(words), pos + 9)
            context_words = words[start:end]

            if any(word in self.finance_context_words for word in context_words):
                context_found = True
                break

        # Adjust confidence based on context
        base_confidence = 0.7
        if context_found:
            base_confidence += 0.2

        # Boost confidence for well-known tickers
        major_tickers = {'AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META'}
        if ticker in major_tickers:
            base_confidence += 0.1

        return min(base_confidence, 0.98)  # Cap at 0.98 (cashtags get 0.99)

    def extract_tickers_with_context(self, text: str) -> List[dict]:
        """
        Extract tickers with surrounding context for storage
        Returns: List of dicts with ticker, confidence, and context
        """
        tickers = self.extract_tickers(text)
        result = []

        for ticker, confidence in tickers:
            context = self._extract_context(ticker, text)
            result.append({
                'ticker': ticker,
                'confidence': confidence,
                'context': context
            })

        return result

    def _extract_context(self, ticker: str, text: str, context_size: int = 50) -> str:
        """Extract surrounding context for a ticker mention"""
        # Find ticker position (case insensitive)
        text_lower = text.lower()
        ticker_lower = ticker.lower()

        # Look for both $TICKER and TICKER formats
        patterns = [f'${ticker_lower}', ticker_lower]

        for pattern in patterns:
            pos = text_lower.find(pattern)
            if pos != -1:
                start = max(0, pos - context_size)
                end = min(len(text), pos + len(pattern) + context_size)
                return text[start:end].strip()

        return ""

# Example usage and testing
if __name__ == "__main__":
    extractor = TickerExtractor()

    test_texts = [
        "I think $TSLA is a great buy right now",
        "AAPL earnings are coming up next week, bullish on the stock",
        "My portfolio has GOOGL, MSFT, and AMZN shares",
        "DD on NVDA: this company has a strong moat",
        "FOR SALE: my CAR is WELL maintained"  # Should not detect stoplist words
    ]

    for text in test_texts:
        print(f"\nText: {text}")
        tickers = extractor.extract_tickers(text)
        for ticker, confidence in tickers:
            print(f"  {ticker}: {confidence:.2f}")