# Strategy Synthesis Prompt

You are analyzing a collection of validated trading strategies to identify cross-strategy opportunities.

## Validated Strategies

{{ validated_strategies }}

## Validated Ideas

{{ validated_ideas }}

## Available Data Sources

### QuantConnect Native
- US Equities (prices, fundamentals, corporate actions)
- US Options (chains, Greeks, IV)
- Futures (major contracts)
- Forex (major pairs)
- Crypto (major exchanges)

### Custom Data (Object Store)
{{ custom_data_sources }}

## Your Task

As {{ persona_name }}, analyze these strategies and provide insights according to your specialty.

Consider:
1. What patterns do you see across the validated strategies?
2. What opportunities for combination or enhancement exist?
3. What's missing that could improve the overall portfolio?
4. What specific, actionable recommendations do you have?

Be specific and reference strategy IDs directly. Focus on practical, implementable opportunities.

Respond with your analysis in the JSON format specified in your persona definition.
