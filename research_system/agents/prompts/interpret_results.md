# Interpret Results Prompt Template

Use this template when asking personas to interpret validation results.

## Prompt

```
You are the {{ persona_name }} persona. Your role and perspective are defined in your persona document.

## Context

A validation test has been completed for catalog entry {{ component_id }}.

### Component Information
- **ID**: {{ component_id }}
- **Name**: {{ component_name }}
- **Type**: {{ component_type }}
- **Hypothesis**: {{ hypothesis }}

### Test Configuration
- **Test Type**: {{ test_type }} (is = in-sample, oos = out-of-sample)
- **Period**: {{ start_date }} to {{ end_date }}
- **Base Strategy**: {{ base_strategy }}
- **Filter Configuration**: {{ filter_config }}

### Backtest Results

**Performance Metrics:**
- Sharpe Ratio: {{ sharpe_ratio }}
- Alpha (annualized): {{ alpha }}%
- CAGR: {{ cagr }}%
- Maximum Drawdown: {{ max_drawdown }}%
- Total Trades: {{ total_trades }}
- Win Rate: {{ win_rate }}%

**Comparison to Baseline:**
- Baseline Sharpe: {{ baseline_sharpe }}
- Sharpe Improvement: {{ sharpe_improvement }}
- Baseline Max DD: {{ baseline_max_dd }}%
- Drawdown Improvement: {{ drawdown_improvement }}%

**Regime Performance:**
{% for regime in regime_results %}
- {{ regime.name }}: Sharpe={{ regime.sharpe }}, Return={{ regime.returns }}%
{% endfor %}

### Statistical Analysis
- p-value: {{ p_value }}
- Bonferroni-corrected p: {{ bonferroni_p }}
- Number of tests: {{ n_tests }}
- Statistically significant: {{ is_significant }}
- Effect size (Sharpe improvement): {{ effect_size }}

### Sanity Flags
{% if sanity_flags %}
{% for flag in sanity_flags %}
- [{{ flag.severity }}] {{ flag.code }}: {{ flag.message }}
{% endfor %}
{% else %}
- No sanity flags raised
{% endif %}

## Your Task

Analyze these results from your {{ persona_name }} perspective. Consider:
1. What do these results mean from your specific viewpoint?
2. What are the key strengths you see?
3. What concerns do you have?
4. What are the trading/investment implications?
5. What would you recommend as next steps?

Provide your analysis in the JSON format specified in your persona document.
```

## Usage Notes

- Fill in template variables with actual values from validation results
- Ensure all metrics use consistent units (percentages as decimals or whole numbers)
- Include regime results if available
- Provide baseline comparison when testing filters
- Always include sanity flags to inform the persona's analysis
