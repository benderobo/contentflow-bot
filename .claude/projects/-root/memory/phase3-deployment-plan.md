---
name: phase3_deployment_ready
description: Phase 3 security hardening deployment plan (2026-07-26 to 2026-08-31)
metadata:
  type: project
---

# Phase 3 Deployment Plan — READY TO EXECUTE

**Status:** ✅ Ready  
**Timeline:** 2026-07-26 to 2026-08-31 (6-week deployment window)  
**Target Risk Reduction:** 77% (baseline) → 8% (Phase 2) → 3% (Phase 3 full)

## Pre-Deployment Week (2026-07-26 to 2026-07-31)

**5-day prep schedule with daily action items:**
- **Day 1 (07-26):** Create backups (3-2-1 rule), document baseline metrics
- **Day 2 (07-27):** Staging setup, ModSecurity research, Docker verification
- **Day 3 (07-29):** ModSecurity + OWASP CRS installation (staging only)
- **Day 4 (07-30):** False positive tuning, ELK docker-compose prep
- **Day 5 (07-31):** Final pre-flight checks, production readiness verification

**Estimated effort:** ~14.5 hours total (1-4 hours per day)

**Files created:**
- `/root/PHASE3_DEPLOYMENT_TIMELINE.md` — detailed timeline with commands
- `/root/PHASE3_DAILY_CHECKLIST.md` — daily action items with bash commands
- `/root/DEPLOYMENT_CHECKLIST.txt` — final pre-deployment verification checklist

## Phase 3.1: ModSecurity WAF (2026-08-01)

**Deployment Window:** 2026-08-01 02:00 UTC (90 minutes)

**What deploys:**
- ModSecurity 3 (nginx WAF module)
- OWASP CRS v4.0+ (1000+ security rules)
- Custom rules for CSRF validation, rate limiting, Telegram auth
- Detection mode (alerts but doesn't block initially)

**Success criteria:**
- 99.9%+ requests pass without error
- < 2 false positives per 10,000 requests
- Response time impact < 5%

## Phase 3.2: ELK Stack (2026-08-08)

**Deployment Window:** Week of 2026-08-08

**What deploys:**
- Elasticsearch 8.x (log aggregation)
- Kibana 8.x (dashboards + visualization)
- Logstash 8.x (log ingestion pipeline)

**Log sources:**
- nginx access logs (all requests)
- ModSecurity audit log (rule triggers)
- /tmp/shell_audit.log (command execution)

**Success criteria:**
- Logs flowing from all sources
- Kibana dashboards accessible
- Retention: 30 days (expandable to 1 year)

## Phase 3.3: Rule Tuning (2026-08-15 to 2026-08-29)

**Timeline:**
- Week 3 (08-15): Monitor production, identify false positives
- Week 4 (08-22): Create rule exemptions, fine-tune detection
- Week 4 (08-29): Enable blocking mode, full enforcement active

**Expected metrics after Phase 3:**
- MTTD (mean time to detect): < 5 minutes
- MTTR (mean time to respond): Critical 1h, High 4h
- Attack blocking rate: > 95%
- False positive rate: < 0.02%

## Key Dependencies

✅ **Already met:**
- Phase 1 complete (env variables, audit logging)
- Phase 2 complete (CSRF, CSP, rate limiting)
- HSTS + TLS hardening deployed
- nginx + SSL working
- Docker available on host
- sudo access available

⏳ **Will need before deployment:**
- ModSecurity 3 installed
- OWASP CRS v4.0+ downloaded
- ELK docker-compose ready
- Backups created (3-2-1 rule)
- Team briefed on SLA

## Escalation & SLA

**Incident Response SLA:**
- Critical (RCE, data breach): 1 hour response
- High (account compromise, XSS): 4 hours
- Medium (rate limiting bypass): 24 hours
- Low (denial of service, brute force): 1 week

**Escalation path:**
benderobo (primary) → on-call engineer → incident commander

## Related Documents

- [[security_hardening_phases_1_3]] — overview of all 3 phases
- [[kill_error_log_phase_3_updates]] — Phase 3 progress tracking
- [[incident_response_sla_matrix]] — incident response procedures

## Next Steps

**Immediate (Today):**
1. Review `/root/PHASE3_DAILY_CHECKLIST.md`
2. Start Day 1 tasks (backups, baseline metrics)
3. Schedule deployment window (2026-08-01 02:00 UTC)

**This Week:**
1. Complete Days 1-5 pre-deployment tasks
2. Create staging environment
3. Prepare ModSecurity + OWASP CRS
4. Brief team on Phase 3 changes

**Deployment Week (08-01):**
1. Execute Phase 3.1 (ModSecurity to production)
2. Monitor for 1 hour
3. Declare Phase 3.1 complete

---

**Status Updated:** 2026-07-26  
**Deployment Ready:** ✅ Yes  
**Risk Reduction Path:** 77% → 35% (Phase 1) → 8% (Phase 2) → 3% (Phase 3)
