# Suggest Combinations Prompt Template

Use this template when asking personas to suggest new combinations to test.

## Prompt

```
You are the {{ persona_name }} persona. Your role and perspective are defined in your persona document.

## Context

We are looking for new indicator + strategy combinations to test. Based on what we've learned so far, suggest promising combinations.

### Validated Indicators (Available for Combinations)
{% for ind in validated_indicators %}
- **{{ ind.id }}**: {{ ind.name }}
  - Status: {{ ind.status }}
  - Sharpe: {{ ind.sharpe }}
  - Best Regime: {{ ind.best_regime }}
  - Key Characteristic: {{ ind.characteristic }}
{% endfor %}

### Invalidated Indicators (What Didn't Work)
{% for ind in invalidated_indicators %}
- **{{ ind.id }}**: {{ ind.name }}
  - Failure Mode: {{ ind.failure_reason }}
  - Lesson Learned: {{ ind.lesson }}
{% endfor %}

### Recent Test Results (What We've Learned)
{% for result in recent_results %}
- **{{ result.id }}**: {{ result.name }}
  - Combination: {{ result.indicator }} + {{ result.strategy }}
  - Outcome: {{ result.outcome }}
  - Key Finding: {{ result.finding }}
{% endfor %}

### Base Strategies Available
{% for strat in strategies %}
- **{{ strat.id }}**: {{ strat.name }}
  - Description: {{ strat.description }}
  - When It Works: {{ strat.when_works }}
{% endfor %}

### Untested Combinations
These combinations haven't been tested yet:
{% for combo in untested_combinations %}
- {{ combo.indicator }} + {{ combo.strategy }} ({{ combo.role }})
{% endfor %}

## Your Task

Based on your {{ persona_name }} perspective, suggest up to 5 combinations that you believe are most promising. For each suggestion:

1. **What combination?** (indicator + strategy + filter role)
2. **Why this combination?** (rationale from your perspective)
3. **What hypothesis would you test?** (specific, testable)
4. **Expected outcome?** (what you expect to see if it works)
5. **Risk/concern?** (what might make it fail)

Provide your suggestions in this format:

```json
{
  "perspective": "{{ persona_name }}",
  "suggestions": [
    {
      "rank": 1,
      "indicator_id": "IND-XXX",
      "strategy_id": "STRATEGY_NAME",
      "filter_role": "entry|exit|both",
      "rationale": "Why this combination makes sense...",
      "hypothesis": "Specific testable hypothesis...",
      "expected_outcome": {
        "sharpe_improvement": 0.X,
        "drawdown_reduction": "X%",
        "when_works": "Market conditions..."
      },
      "risks": [
        "What could make this fail..."
      ],
      "confidence": 0.0-1.0
    }
  ],
  "meta_observations": [
    "Patterns you notice across suggestions..."
  ],
  "what_to_avoid": [
    "Combinations that seem tempting but should be avoided..."
  ]
}
```
```

## Usage Notes

- Provide comprehensive context about what's been validated and invalidated
- Include lessons learned from failed tests
- List untested combinations to help personas identify gaps
- Each persona will suggest based on their unique perspective:
  - Momentum trader: Trend-following combinations
  - Risk manager: Risk-reducing combinations
  - Quant researcher: Statistically robust combinations
  - Contrarian: Non-obvious or against-the-grain combinations
