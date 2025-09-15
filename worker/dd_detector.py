import re
from typing import Dict, List, Tuple
from config import config

class DDDetector:
    def __init__(self):
        # DD-specific keywords (strong indicators)
        self.dd_keywords = {
            'due diligence', 'dd', 'deep dive', 'analysis', 'research',
            'valuation', 'dcf', 'discounted cash flow', 'price target', 'pt',
            'fair value', 'intrinsic value', 'thesis', 'bull case', 'bear case',
            'catalyst', 'moat', 'competitive advantage', 'financial analysis',
            'fundamental analysis', 'comprehensive analysis'
        }

        # Financial terms (supporting indicators)
        self.financial_terms = {
            'revenue', 'earnings', 'ebitda', 'margin', 'profit', 'loss',
            'debt', 'cash flow', 'balance sheet', 'income statement',
            'pe ratio', 'p/e', 'eps', 'book value', 'market cap',
            'float', 'short interest', 'insider trading', 'quarterly',
            'annual', 'guidance', 'forecast', 'outlook', 'growth',
            'dividend', 'yield', 'payout', 'ratio', 'multiple',
            'operating', 'net income', 'gross', 'expenses', 'costs'
        }

        # Structure indicators
        self.structure_keywords = {
            'summary:', 'tldr:', 'tl;dr:', 'conclusion:', 'thesis:',
            'overview:', 'background:', 'financials:', 'risks:',
            'pros:', 'cons:', 'bull case:', 'bear case:', 'valuation:',
            'catalysts:', 'investment thesis:', 'key points:'
        }

        # Regex patterns for data/numbers
        self.number_patterns = [
            re.compile(r'\d+\.\d+%'),       # Percentages like 15.5%
            re.compile(r'\$\d+[\.,]?\d*[BMK]?'),  # Dollar amounts like $100M, $5.2B
            re.compile(r'\d+[BMK]\s*\$'),   # Market cap style like 100B $
            re.compile(r'P/E\s*:\s*\d+'),   # P/E ratios
            re.compile(r'\d+x\s*(revenue|earnings|sales)'),  # Multiples
        ]

    def detect_dd(self, title: str, content: str, subreddit: str) -> Dict:
        """
        Detect if a post is due diligence content
        Returns: Dict with is_dd (bool), score (int), reasons (list)
        """
        if not title or not content:
            return {'is_dd': False, 'score': 0, 'reasons': []}

        title_lower = title.lower()
        content_lower = content.lower()
        combined_text = f"{title_lower} {content_lower}"

        score = 0
        reasons = []

        # 1. Check for DD keywords in title (high weight)
        title_dd_count = sum(1 for keyword in self.dd_keywords if keyword in title_lower)
        if title_dd_count > 0:
            points = min(title_dd_count * 3, 6)  # Max 6 points from title
            score += points
            reasons.append(f"DD keywords in title (+{points})")

        # 2. Check for DD keywords in content
        content_dd_count = sum(1 for keyword in self.dd_keywords if keyword in content_lower)
        if content_dd_count > 0:
            points = min(content_dd_count * 2, 4)  # Max 4 points from content
            score += points
            reasons.append(f"DD keywords in content (+{points})")

        # 3. Financial terms density
        financial_count = sum(1 for term in self.financial_terms if term in combined_text)
        if financial_count >= 3:
            points = min(financial_count, 5)  # Max 5 points
            score += points
            reasons.append(f"Financial terms density (+{points})")

        # 4. Content length analysis
        word_count = len(content.split())
        if word_count >= config.DD_MIN_WORD_COUNT:
            if word_count >= 1000:
                points = 4
            elif word_count >= 500:
                points = 3
            else:
                points = 2
            score += points
            reasons.append(f"Long form content ({word_count} words, +{points})")

        # 5. Structure indicators
        structure_count = sum(1 for keyword in self.structure_keywords if keyword in combined_text)
        if structure_count > 0:
            points = min(structure_count * 2, 4)  # Max 4 points
            score += points
            reasons.append(f"Structured format (+{points})")

        # 6. Quantitative data presence
        data_indicators = 0
        for pattern in self.number_patterns:
            if pattern.search(combined_text):
                data_indicators += 1

        if data_indicators >= 2:
            points = min(data_indicators, 3)  # Max 3 points
            score += points
            reasons.append(f"Quantitative data (+{points})")

        # 7. Apply subreddit weighting
        subreddit_weight = config.SUBREDDIT_WEIGHTS.get(subreddit, 1.0)
        if subreddit_weight != 1.0:
            original_score = score
            score = int(score * subreddit_weight)
            reasons.append(f"Subreddit weight {subreddit_weight}x ({original_score} → {score})")

        # 8. Negative indicators (reduce score)
        negative_keywords = {'yolo', 'moon', '🚀', 'diamond hands', 'hodl', 'ape', 'retard'}
        negative_count = sum(1 for keyword in negative_keywords if keyword in combined_text)
        if negative_count > 0:
            penalty = min(negative_count * 2, 4)
            score -= penalty
            reasons.append(f"Meme language penalty (-{penalty})")

        # Final determination
        is_dd = score >= config.DD_SCORE_THRESHOLD

        return {
            'is_dd': is_dd,
            'score': max(score, 0),  # Don't allow negative scores
            'reasons': reasons,
            'word_count': word_count,
            'dd_confidence': min(score / 15.0, 1.0)  # Normalize to 0-1
        }

    def extract_dd_metadata(self, title: str, content: str) -> Dict:
        """Extract metadata specific to DD posts"""
        combined_text = f"{title} {content}".lower()

        # Detect potential tags based on content
        tags = []

        tag_keywords = {
            'Valuation': ['valuation', 'dcf', 'intrinsic value', 'fair value', 'undervalued', 'overvalued'],
            'Earnings': ['earnings', 'eps', 'quarterly', 'annual', 'revenue', 'profit'],
            'Thesis': ['thesis', 'bull case', 'bear case', 'investment case'],
            'Risks': ['risks', 'risk factors', 'concerns', 'headwinds', 'challenges'],
            'Catalyst': ['catalyst', 'catalysts', 'upcoming', 'events', 'announcement'],
            'DCF': ['dcf', 'discounted cash flow', 'free cash flow', 'terminal value'],
            'Moat': ['moat', 'competitive advantage', 'barriers to entry', 'network effect'],
            'Technical': ['support', 'resistance', 'chart', 'technical analysis', 'pattern']
        }

        for tag, keywords in tag_keywords.items():
            if any(keyword in combined_text for keyword in keywords):
                tags.append(tag)

        # Detect if post has charts/tables (basic heuristics)
        has_charts = any(indicator in content.lower() for indicator in [
            'chart', 'graph', 'image', 'screenshot', 'table', '|', '---'
        ])

        has_tables = '|' in content and '---' in content  # Markdown table indicators

        return {
            'tags': tags,
            'has_charts': has_charts,
            'has_tables': has_tables,
            'word_count': len(content.split())
        }

    def get_dd_quality_indicators(self, title: str, content: str) -> Dict[str, bool]:
        """Get boolean indicators for DD quality"""
        combined_text = f"{title} {content}".lower()

        return {
            'has_dd_keywords': any(keyword in combined_text for keyword in self.dd_keywords),
            'has_financial_data': any(keyword in combined_text for keyword in self.financial_terms),
            'is_long_form': len(content.split()) >= config.DD_MIN_WORD_COUNT,
            'has_structure': any(keyword in combined_text for keyword in self.structure_keywords),
            'has_quantitative_data': any(pattern.search(combined_text) for pattern in self.number_patterns),
            'minimal_meme_language': not any(word in combined_text for word in ['yolo', 'moon', '🚀'])
        }

# Example usage and testing
if __name__ == "__main__":
    detector = DDDetector()

    test_posts = [
        {
            'title': 'DD: Tesla Q4 Analysis - Why TSLA is Undervalued',
            'content': '''
            After reviewing Tesla's latest quarterly earnings and cash flow statements,
            I believe the company is significantly undervalued at current prices.

            Key metrics:
            - Revenue growth: 15.3% YoY
            - Free cash flow: $2.1B
            - P/E ratio: 25x (vs industry average of 30x)
            - Gross margin improvement to 18.7%

            The company's expansion into energy storage and autonomous driving
            provides significant catalysts for 2024. My DCF analysis suggests
            a fair value of $280 per share.
            ''',
            'subreddit': 'SecurityAnalysis'
        },
        {
            'title': 'YOLO into GME 🚀🚀🚀',
            'content': 'Diamond hands baby! This is going to the moon!',
            'subreddit': 'wallstreetbets'
        },
        {
            'title': 'What do you think about AAPL?',
            'content': 'Just curious about your thoughts on Apple stock.',
            'subreddit': 'stocks'
        }
    ]

    for i, post in enumerate(test_posts, 1):
        print(f"\n--- Test Post {i} ---")
        print(f"Title: {post['title']}")
        print(f"Subreddit: {post['subreddit']}")

        result = detector.detect_dd(post['title'], post['content'], post['subreddit'])
        print(f"Is DD: {result['is_dd']}")
        print(f"Score: {result['score']}")
        print(f"Confidence: {result['dd_confidence']:.2f}")
        print("Reasons:")
        for reason in result['reasons']:
            print(f"  - {reason}")

        if result['is_dd']:
            metadata = detector.extract_dd_metadata(post['title'], post['content'])
            print(f"Tags: {metadata['tags']}")
            print(f"Word count: {metadata['word_count']}")