# 📊 Performance Diagrams

Performance characteristics and cost analysis.

## Diagrams

### 1. Caching Impact
**File**: `04_caching_impact.png`

Performance comparison with visual weight:
- **Cache Hit (90%)**: 17ms response, $0.0001 per request
- **Cache Miss (10%)**: 820ms response, $0.002 per request
- Line thickness dramatically shows traffic distribution

**Key Insight**: 16x performance improvement for cached requests.

### 2. Cost Analysis
**File**: `08_cost_analysis.png`

Business value visualization:
- **Without cache**: $2,000/day for 1M requests
- **With cache**: $290/day (85% reduction)
- Daily savings: $1,710

**Key Insight**: Caching provides massive cost savings at scale.

## Visual Conventions
- **Line thickness** represents traffic percentage (7px vs 1px)
- **Green** for optimal path, **orange** for degraded
- **Cost annotations** show business impact
