"""
Unit tests for ticker extraction logic from worker.py

Tests cover:
- AI ticker special handling ($AI, C3.ai)
- Contraction false positives (don't → DON)
- Dollar prefix patterns ($TICKER)
- Plain ticker patterns (TICKER)
- Edge cases and boundary conditions
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import worker
sys.path.insert(0, str(Path(__file__).parent.parent))

from worker.worker import extract_tickers


class TestAITickerHandling:
    """Test special handling for AI ticker to avoid false positives."""

    valid_tickers = {'AI', 'TSLA', 'NVDA', 'AAPL'}

    def test_bare_ai_not_matched(self):
        """Bare 'AI' in text should NOT match."""
        assert extract_tickers("AI is changing the world", self.valid_tickers) == []

    def test_multiple_bare_ai_not_matched(self):
        """Multiple 'AI' mentions should NOT match."""
        assert extract_tickers("AI AI AI everywhere", self.valid_tickers) == []

    def test_ai_in_sentence_not_matched(self):
        """AI as a word in sentence should NOT match."""
        assert extract_tickers("The AI revolution is here", self.valid_tickers) == []

    def test_dollar_ai_matched(self):
        """$AI with dollar prefix SHOULD match."""
        result = extract_tickers("$AI is going to the moon", self.valid_tickers)
        assert 'AI' in result

    def test_c3ai_lowercase_matched(self):
        """c3.ai (lowercase) SHOULD match AI ticker."""
        result = extract_tickers("c3.ai stock is great", self.valid_tickers)
        assert 'AI' in result

    def test_c3ai_uppercase_matched(self):
        """C3.ai SHOULD match AI ticker."""
        result = extract_tickers("C3.ai earnings beat", self.valid_tickers)
        assert 'AI' in result

    def test_c3ai_mixed_case_matched(self):
        """C3.AI (mixed case) SHOULD match AI ticker."""
        result = extract_tickers("C3.AI is bullish", self.valid_tickers)
        assert 'AI' in result

    def test_c3_space_ai_matched(self):
        """C3 AI (with space) SHOULD match AI ticker."""
        result = extract_tickers("C3 AI company", self.valid_tickers)
        assert 'AI' in result

    def test_ai_with_other_tickers(self):
        """AI in text with other tickers should only match others."""
        result = extract_tickers("AI is great but I like TSLA more", self.valid_tickers)
        assert 'AI' not in result
        assert 'TSLA' in result


class TestContractionHandling:
    """Test that contractions don't create false positive ticker matches."""

    valid_tickers = {'DON', 'IM', 'WON', 'CANT', 'WONT', 'TSLA', 'AAPL'}

    def test_dont_not_matched(self):
        """don't should NOT match DON ticker."""
        result = extract_tickers("I don't think TSLA will moon", self.valid_tickers)
        assert 'DON' not in result
        assert 'TSLA' in result

    def test_im_contraction_not_matched(self):
        """I'm should NOT match IM ticker."""
        result = extract_tickers("I'm buying AAPL", self.valid_tickers)
        assert 'IM' not in result
        assert 'AAPL' in result

    def test_wont_not_matched(self):
        """won't should NOT match WON ticker."""
        result = extract_tickers("It won't go up", self.valid_tickers)
        assert 'WON' not in result
        assert 'WONT' not in result

    def test_cant_not_matched(self):
        """can't should NOT match CANT ticker."""
        result = extract_tickers("I can't believe this", self.valid_tickers)
        assert 'CANT' not in result

    def test_multiple_contractions(self):
        """Multiple contractions in same text."""
        result = extract_tickers("I don't think I'm ready", self.valid_tickers)
        assert 'DON' not in result
        assert 'IM' not in result


class TestDollarPrefixPatterns:
    """Test ticker extraction with $ prefix."""

    valid_tickers = {'TSLA', 'NVDA', 'AAPL', 'MSFT', 'AI', 'GME', 'AMC'}

    def test_single_dollar_ticker(self):
        """Single $TICKER should match."""
        result = extract_tickers("$TSLA to the moon", self.valid_tickers)
        assert 'TSLA' in result

    def test_multiple_dollar_tickers(self):
        """Multiple $TICKER in one text should all match."""
        result = extract_tickers("$TSLA $NVDA $AAPL", self.valid_tickers)
        assert set(result) == {'TSLA', 'NVDA', 'AAPL'}

    def test_dollar_ticker_at_start(self):
        """$TICKER at start of text."""
        result = extract_tickers("$GME is squeezing", self.valid_tickers)
        assert 'GME' in result

    def test_dollar_ticker_at_end(self):
        """$TICKER at end of text."""
        result = extract_tickers("I'm buying $AMC", self.valid_tickers)
        assert 'AMC' in result

    def test_dollar_ticker_in_sentence(self):
        """$TICKER in middle of sentence."""
        result = extract_tickers("I think $MSFT will beat earnings", self.valid_tickers)
        assert 'MSFT' in result

    def test_invalid_dollar_ticker_not_matched(self):
        """$TICKER not in valid_tickers should not match."""
        result = extract_tickers("$FAKE $NOTREAL", self.valid_tickers)
        assert result == []

    def test_dollar_with_contraction(self):
        """$TICKER works even near contractions."""
        result = extract_tickers("I'm buying $AAPL", self.valid_tickers)
        assert 'AAPL' in result
        assert len(result) == 1  # Only AAPL, not IM


class TestPlainTickerPatterns:
    """Test ticker extraction without $ prefix."""

    valid_tickers = {'TSLA', 'NVDA', 'AAPL', 'MSFT', 'GME', 'AMD', 'AI'}

    def test_single_plain_ticker(self):
        """Plain TICKER (uppercase) should match."""
        result = extract_tickers("TSLA is going up", self.valid_tickers)
        assert 'TSLA' in result

    def test_multiple_plain_tickers(self):
        """Multiple plain tickers should all match."""
        result = extract_tickers("TSLA and NVDA are bullish", self.valid_tickers)
        assert set(result) == {'TSLA', 'NVDA'}

    def test_lowercase_ticker_not_matched(self):
        """Lowercase ticker should NOT match."""
        result = extract_tickers("tsla is great", self.valid_tickers)
        assert result == []

    def test_mixed_case_ticker_not_matched(self):
        """Mixed case ticker should NOT match."""
        result = extract_tickers("Tesla or Tsla", self.valid_tickers)
        assert result == []

    def test_ticker_with_punctuation(self):
        """Ticker followed by punctuation should match."""
        result = extract_tickers("Buy AAPL! Sell MSFT.", self.valid_tickers)
        assert set(result) == {'AAPL', 'MSFT'}

    def test_ticker_in_parentheses(self):
        """Ticker in parentheses should match."""
        result = extract_tickers("Apple (AAPL) is great", self.valid_tickers)
        assert 'AAPL' in result

    def test_two_letter_ticker(self):
        """Two-letter tickers should work if valid."""
        valid = {'AI', 'GM', 'GE', 'BP'}
        # Note: AI is special cased, so test with GM
        result = extract_tickers("GM earnings", {'GM'})
        assert 'GM' in result

    def test_five_letter_ticker(self):
        """Five-letter tickers should work."""
        result = extract_tickers("AAPL stock", {'AAPL'})
        assert 'AAPL' in result

    def test_six_letter_ticker_not_matched(self):
        """Six+ letter tickers should NOT match (not valid ticker format)."""
        result = extract_tickers("TOOLONG", {'TOOLONG'})
        assert result == []


class TestMixedPatterns:
    """Test combinations of $ and plain patterns."""

    valid_tickers = {'TSLA', 'NVDA', 'AAPL', 'MSFT', 'AI'}

    def test_dollar_and_plain_same_ticker(self):
        """$TSLA and TSLA should only return one TSLA."""
        result = extract_tickers("$TSLA and TSLA", self.valid_tickers)
        assert result.count('TSLA') == 1

    def test_dollar_and_plain_different_tickers(self):
        """Mix of $ and plain tickers should all match."""
        result = extract_tickers("$TSLA NVDA $AAPL", self.valid_tickers)
        assert set(result) == {'TSLA', 'NVDA', 'AAPL'}

    def test_complex_sentence(self):
        """Complex sentence with multiple patterns."""
        text = "I'm buying $TSLA, selling NVDA, and holding AAPL. Don't miss out!"
        result = extract_tickers(text, self.valid_tickers)
        assert set(result) == {'TSLA', 'NVDA', 'AAPL'}


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    valid_tickers = {'TSLA', 'NVDA', 'AAPL'}

    def test_empty_string(self):
        """Empty string should return empty list."""
        assert extract_tickers("", self.valid_tickers) == []

    def test_no_tickers(self):
        """Text with no tickers should return empty list."""
        assert extract_tickers("This has no tickers", self.valid_tickers) == []

    def test_only_invalid_tickers(self):
        """Text with only invalid tickers should return empty list."""
        assert extract_tickers("$FAKE NOTREAL", self.valid_tickers) == []

    def test_special_characters_only(self):
        """String with only special characters."""
        assert extract_tickers("!@#$%^&*()", self.valid_tickers) == []

    def test_numbers_and_ticker(self):
        """Tickers mixed with numbers."""
        result = extract_tickers("TSLA at $250.50", self.valid_tickers)
        assert 'TSLA' in result

    def test_url_with_ticker(self):
        """Ticker in URL should still match."""
        result = extract_tickers("Check https://example.com/TSLA/news", self.valid_tickers)
        assert 'TSLA' in result

    def test_duplicate_tickers(self):
        """Same ticker mentioned multiple times should return once."""
        result = extract_tickers("TSLA TSLA TSLA", self.valid_tickers)
        assert result.count('TSLA') == 1

    def test_empty_valid_tickers(self):
        """Empty valid_tickers set should return empty list."""
        assert extract_tickers("TSLA NVDA", set()) == []


class TestRealWorldExamples:
    """Test with real-world Reddit-style text."""

    valid_tickers = {'TSLA', 'NVDA', 'AAPL', 'SPY', 'GME', 'AMC', 'AI', 'PLTR', 'VOO'}

    def test_wsb_style_post(self):
        """Typical WallStreetBets style post."""
        text = "$GME to the moon! 🚀 Don't miss out. I'm all in on $AMC too!"
        result = extract_tickers(text, self.valid_tickers)
        assert set(result) == {'GME', 'AMC'}

    def test_technical_analysis_post(self):
        """Post with technical analysis."""
        text = "TSLA showing bullish divergence. SPY at resistance. I don't see NVDA breaking out yet."
        result = extract_tickers(text, self.valid_tickers)
        assert set(result) == {'TSLA', 'SPY', 'NVDA'}

    def test_portfolio_discussion(self):
        """Portfolio discussion post."""
        text = "My portfolio: 40% VOO, 30% AAPL, 20% NVDA, 10% cash. I won't sell."
        result = extract_tickers(text, self.valid_tickers)
        assert set(result) == {'VOO', 'AAPL', 'NVDA'}

    def test_ai_discussion_no_false_positive(self):
        """AI discussion without AI ticker match."""
        text = "AI is revolutionizing everything. Machine learning and AI models are incredible."
        result = extract_tickers(text, self.valid_tickers)
        assert 'AI' not in result

    def test_ai_discussion_with_c3ai(self):
        """AI discussion mentioning C3.ai company."""
        text = "AI is great but C3.ai stock specifically is undervalued."
        result = extract_tickers(text, self.valid_tickers)
        assert 'AI' in result

    def test_options_discussion(self):
        """Options trading discussion."""
        text = "Bought $TSLA 300c 1/20. I'm bullish. Don't think it'll drop."
        result = extract_tickers(text, self.valid_tickers)
        assert 'TSLA' in result
        # Should not match DON from "Don't"

    def test_comparison_post(self):
        """Comparing multiple stocks."""
        text = "NVDA vs AMD vs PLTR - which AI play is best? I don't know."
        result = extract_tickers(text, self.valid_tickers)
        assert 'NVDA' in result
        assert 'PLTR' in result
        # AI should not match, AMD not in valid_tickers
