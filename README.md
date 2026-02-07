# geo-audit

Instant GEO (Generative Engine Optimization) audit for any website. Get your GEO score in under 30 seconds.

```bash
$ geo-audit stripe.com

🔍 GEO Audit
────────────────────────────────
https://stripe.com

GEO Score: ███████████████░░░░░ 72/100

Check              Score   Status
llms.txt            0/25   1 error
Structured Data    20/25   OK
Meta Tags          15/20   1 warning
Content Structure  14/20   OK
Technical           9/10   OK

🎯 Top Quick Wins:
1. No llms.txt file found
   → Create /llms.txt with company info. See llmstxt.org

2. Meta description too short
   → Expand to 150-160 characters
```

## What is GEO?

**Generative Engine Optimization (GEO)** is SEO for AI. It's about optimizing your content so that LLMs like ChatGPT, Claude, and Perplexity mention your product when users ask relevant questions.

Research shows that proper GEO optimization can increase AI visibility by **up to 40%**.

## Install

```bash
pip install geo-audit
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uvx geo-audit stripe.com
```

## Usage

### Audit a site

```bash
geo-audit example.com
# or explicitly:
geo-audit scan example.com
```

### Generate fixes (llms.txt + JSON-LD)

```bash
# Preview what would be generated
geo-audit fix example.com --print-only

# Generate files in current directory
geo-audit fix example.com

# Generate to specific directory
geo-audit fix example.com -o ./output
```

### Test LLM visibility

```bash
# Does ChatGPT know about your brand?
geo-audit test "Stripe"

# With industry context
geo-audit test "Vercel" --industry "cloud hosting"

# Test specific LLMs
geo-audit test "OpenAI" --provider openai --provider google
```

Requires API keys:
```bash
export OPENAI_API_KEY=sk-...      # ChatGPT
export ANTHROPIC_API_KEY=...      # Claude
export GOOGLE_API_KEY=...         # Gemini
export PERPLEXITY_API_KEY=...     # Perplexity
```

### More options

```bash
# Show all findings (not just issues)
geo-audit example.com --verbose

# JSON output (for scripting)
geo-audit example.com --json

# Only generate llms.txt (no schema)
geo-audit fix example.com --no-schema

# Only generate Organization schema
geo-audit fix example.com --no-llms-txt --schema-type Organization
```

## What It Checks

| Check | Description | Max Score |
|-------|-------------|-----------|
| **llms.txt** | Presence and quality of llms.txt file | 25 |
| **Structured Data** | JSON-LD schema markup quality | 25 |
| **Meta Tags** | Title, description, Open Graph tags | 20 |
| **Content Structure** | Headings, lists, tables, FAQs | 20 |
| **Technical** | HTTPS, robots.txt, sitemap, mobile | 10 |

### llms.txt

The [llms.txt specification](https://llmstxt.org/) is an emerging standard for helping AI systems understand your site. Only ~0.3% of top websites have one — easy competitive advantage.

### Structured Data (JSON-LD)

LLMs love machine-readable data. The audit checks for:
- High-value schema types (Organization, Product, Article, FAQPage, etc.)
- Completeness of Organization schema
- Entity linking via `sameAs` properties

### Meta Tags

- Title length and quality
- Meta description length
- Open Graph tag coverage
- Canonical URL

### Content Structure

LLM-friendly content patterns:
- Single, clear H1 heading
- Logical heading hierarchy
- Lists (bulleted/numbered)
- Tables with headers
- FAQ sections
- Reasonable paragraph length

### Technical

- HTTPS
- robots.txt (checks for AI crawler blocks)
- sitemap.xml
- Mobile viewport
- Language declaration

## Scoring

- **80-100**: Excellent GEO optimization
- **60-79**: Good, with room for improvement
- **40-59**: Needs work
- **0-39**: Significant optimization needed

## Roadmap

- [x] `geo-audit fix` — Auto-generate llms.txt and JSON-LD schemas
- [x] `geo-audit test` — Query LLMs to check if they know your brand
- [ ] Batch URL auditing
- [ ] CI/CD integration (GitHub Action)
- [ ] PyPI publishing

## Contributing

Contributions welcome! Please read our contributing guidelines first.

```bash
git clone https://github.com/huiren/geo-audit
cd geo-audit
pip install -e ".[dev]"
pytest
```

## License

MIT

## Links

- [llms.txt Specification](https://llmstxt.org/)
- [GEO Research Paper](https://arxiv.org/abs/2311.09735) (Princeton/Georgia Tech)
- [Awesome GEO Resources](https://github.com/amplifying-ai/awesome-generative-engine-optimization)
