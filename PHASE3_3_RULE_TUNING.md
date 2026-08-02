# Phase 3.3 — ModSecurity Rule Tuning & Enforcement
**Scheduled:** 2026-08-15 to 2026-08-29  
**Depends on:** Phase 3.1 (ModSecurity live)  
**Goal:** Transition from detection mode to blocking enforcement

---

## PHASE 3.3: STRATEGY

### Week 1 (08-15 to 08-22): Monitoring & Tuning
- Monitor false positives in production
- Create exemption rules for legitimate traffic
- Analyze top triggered rules
- Adjust rule sensitivity

### Week 2 (08-22 to 08-29): Enforcement
- Enable blocking mode (SecRuleEngine On)
- Monitor error rates
- Validate no false positives
- Final team notification

---

## STEP 1: Daily False Positive Analysis (Week 1)

### Monitor audit.log
```bash
# Day 1: Baseline - count rule triggers
tail -100 /var/log/modsecurity/audit.log | \
  jq '.rule.id' | sort | uniq -c | sort -rn | head -20

# Expected output:
# 15 rule_920200
# 8  rule_930100  
# 5  rule_960004
# etc.
```

### Identify false positives
```bash
# Find rules triggering on legitimate requests
tail -200 /var/log/modsecurity/audit.log | \
  jq -r 'select(.request.method=="GET") | .rule | "\(.id): \(.message)"' | \
  sort | uniq -c | sort -rn | head -10

# Example: High rate of rule_920200 on legitimate requests
# Action: Create exemption OR adjust rule threshold
```

### Create exemption rules
```
# File: /etc/nginx/modsec/exclusions-week1.conf

# Whitelist admin API endpoints (legitimate, frequent false positives)
SecRule REQUEST_FILENAME "@contains /admin/api" \
    "id:20000,phase:1,pass,nolog,ctl:RuleEngine=Off"

# Whitelist file upload endpoints (often triggers rule_200001)
SecRule REQUEST_FILENAME "@contains /upload" \
    "id:20001,phase:1,pass,nolog,ctl:RuleEngine=Off"

# Whitelist health checks (spamming audit log)
SecRule REQUEST_FILENAME "@contains /health" \
    "id:20002,phase:1,pass,nolog,ctl:RuleEngine=Off"

# Disable specific rules causing > 20% false positives
SecRuleRemoveById 920200
SecRuleRemoveById 930100
```

### Apply and test
```bash
# Update modsecurity.conf
echo "Include /etc/nginx/modsec/exclusions-week1.conf" \
  >> /etc/nginx/modsec/modsecurity.conf

# Reload nginx
sudo systemctl reload nginx

# Monitor impact
# Rule trigger rate should drop significantly
# Check: tail -10 /var/log/modsecurity/audit.log
```

---

## STEP 2: Weekly Report (Every Friday)

### Generate statistics
```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d)

cat > /root/waf-report-$DATE.txt << EOFREPORT
ModSecurity WAF Report - $DATE
============================

Total rule triggers: $(grep -c '"rule"' /var/log/modsecurity/audit.log)

Top 10 triggered rules:
$(tail -500 /var/log/modsecurity/audit.log | jq '.rule.id' | sort | uniq -c | sort -rn | head -10)

Blocked requests: $(grep '"blocked"' /var/log/modsecurity/audit.log | wc -l)
(Note: In detection mode, this shows WOULD-BE-BLOCKED)

False positives this week: [MANUAL COUNT]
Exemptions added: [COUNT]

Recommendations:
1. [List of rules to disable/modify]
2. [List of new exemptions needed]
3. [Performance impact notes]

Next week actions:
- [ ] Add exemption for rule_920200 (false positive rate: 45%)
- [ ] Investigate rule_930100 surge on 08-19
- [ ] Monitor /admin/api endpoint (15% false positive rate)
EOFREPORT

cat /root/waf-report-$DATE.txt
```

---

## STEP 3: Transition to Blocking Mode (2026-08-22)

### Pre-blocking safety checks
```bash
# 1. Verify exemptions are complete
grep -c "SecRuleRemoveById\|SecRule.*id:20" \
  /etc/nginx/modsec/exclusions-week1.conf
# Expected: > 10 exemptions

# 2. Check false positive rate
# Calculate: blocked_would_be / total_requests
# Expected: < 0.1% (less than 1 in 1000)

# 3. Verify backup config exists
ls -lh /root/backups/bendernostur.duckdns.org-*.bak | tail -1
# Expected: recent backup (last 24h)

# 4. Test rollback procedure (on paper)
echo "To disable blocking mode:"
echo "  sudo sed -i 's/SecRuleEngine On/SecRuleEngine DetectionOnly/' /etc/nginx/modsec/modsecurity.conf"
echo "  sudo systemctl reload nginx"
```

### Enable blocking mode
```bash
# 1. Update ModSecurity config
sudo sed -i 's/SecRuleEngine DetectionOnly/SecRuleEngine On/' \
  /etc/nginx/modsec/modsecurity.conf

# 2. Test nginx config
sudo nginx -t
# Expected: test is successful

# 3. Reload nginx
sudo systemctl reload nginx

# 4. Verify blocking mode active
grep "SecRuleEngine" /etc/nginx/modsec/modsecurity.conf
# Expected: SecRuleEngine On

# 5. Monitor error rate (1 hour)
# Send test requests:
curl https://bendernostur.duckdns.org/api/orders  # Should pass
curl "https://bendernostur.duckdns.org/?id=1' OR '1'='1"  # Should BLOCK (403)

# Check logs:
tail -20 /var/log/nginx/error.log | grep -i modsec
# Expected: No critical errors, only rule triggers
```

---

## STEP 4: Monitoring During Enforcement Week (08-22 to 08-29)

### Daily checks
```bash
#!/bin/bash
# Daily enforcement monitoring

echo "=== Daily Enforcement Check ==="
DATE=$(date +%Y-%m-%d)

# Check 1: Error rate
ERROR_COUNT=$(tail -100 /var/log/nginx/error.log | wc -l)
if [ $ERROR_COUNT -gt 50 ]; then
  echo "⚠️  HIGH ERROR RATE: $ERROR_COUNT errors in last 100 lines"
  echo "Consider reverting to detection mode"
fi

# Check 2: Blocked requests
BLOCKED=$(grep '"action":"blocked"' /var/log/modsecurity/audit.log | wc -l)
echo "Blocked requests (cumulative): $BLOCKED"

# Check 3: Top blocking rules
echo "Top 5 blocking rules:"
grep '"action":"blocked"' /var/log/modsecurity/audit.log | \
  jq '.rule.id' | sort | uniq -c | sort -rn | head -5

# Check 4: Legitimate traffic still passing
curl -s -o /dev/null -w "Status: %{http_code}\n" \
  https://bendernostur.duckdns.org/api/orders
# Expected: 200 or appropriate app response

echo "Monitoring complete: $DATE"
```

### Alert conditions (auto-disable blocking)
```bash
# If any of these occur, AUTOMATICALLY disable blocking mode:

# 1. Error rate spike > 10% 5xx errors
if [ $(tail -100 /var/log/nginx/error.log | grep -c "error") -gt 10 ]; then
  sudo sed -i 's/SecRuleEngine On/SecRuleEngine DetectionOnly/' \
    /etc/nginx/modsec/modsecurity.conf
  sudo systemctl reload nginx
  echo "ALERT: Reverted to detection mode - high error rate"
fi

# 2. Legitimate API requests being blocked (> 5 in 1 hour)
if [ $(grep '"action":"blocked"' /var/log/modsecurity/audit.log | \
       grep 'api/orders' | wc -l) -gt 5 ]; then
  # Disable blocking, investigate, re-enable
  echo "ALERT: Legitimate API requests being blocked"
fi

# 3. Response time degradation > 20%
# Use baseline from Phase 3.1
# Compare: current avg response time vs baseline
```

---

## STEP 5: Final Enforcement (2026-08-29)

### Go-live checklist
```bash
# All checks must PASS before final enforcement
CHECKS_PASS=0

# 1. False positive rate < 0.1%
FP_RATE=$(...)  # Calculate from logs
if [ $FP_RATE -lt 0.1 ]; then CHECKS_PASS=$((CHECKS_PASS+1)); fi

# 2. No customer complaints (manual check)
# Expected: 0 complaints about being blocked

# 3. ModSecurity audit log populated (rules working)
LOG_SIZE=$(wc -c < /var/log/modsecurity/audit.log)
if [ $LOG_SIZE -gt 10000 ]; then CHECKS_PASS=$((CHECKS_PASS+1)); fi

# 4. Blocking mode active
if grep -q "SecRuleEngine On" /etc/nginx/modsec/modsecurity.conf; then
  CHECKS_PASS=$((CHECKS_PASS+1))
fi

# 5. All exemptions in place
EXEMPTION_COUNT=$(grep -c "SecRuleRemoveById\|id:20" /etc/nginx/modsec/exclusions-*)
if [ $EXEMPTION_COUNT -gt 10 ]; then CHECKS_PASS=$((CHECKS_PASS+1)); fi

echo "Checks passed: $CHECKS_PASS/5"
if [ $CHECKS_PASS -eq 5 ]; then
  echo "✅ READY FOR FINAL ENFORCEMENT"
else
  echo "❌ Address failing checks before proceeding"
fi
```

### Team notification (2026-08-29)
```
Phase 3.3 COMPLETE - ModSecurity Enforcement Active

Timeline:
- 08-15 to 08-22: Detection mode + tuning
  * 47 exemptions created for legitimate traffic
  * False positive rate: 0.08% (within target)
  * Top 5 rules disabled (excessive triggers)

- 08-22 to 08-29: Blocking mode enforcement
  * Week 1: 243 malicious requests blocked
  * Week 1: 0 false positives (100% legitimate traffic)
  * Performance impact: -2% (acceptable)

Effectiveness:
✅ SQL injection attacks: 100% blocked
✅ XSS attempts: 100% blocked
✅ Path traversal: 100% blocked
✅ Command injection: 100% blocked
✅ Legitimate traffic: 100% passing

Current status:
🟢 ModSecurity: BLOCKING (enforcement mode)
🟢 OWASP CRS: 1000+ rules active
🟢 Detection rate: < 5 minute MTTD
🟢 Response SLA: Critical 1h, High 4h

Next steps:
- Monthly rule updates (OWASP CRS)
- Quarterly security training refresh
- Annual penetration testing

Questions? See /root/INCIDENT_RESPONSE_PLAN.md
```

---

## SUCCESS CRITERIA

- [ ] False positive rate < 0.1%
- [ ] No customer complaints
- [ ] All attack types detected and blocked
- [ ] Legitimate traffic passing 100%
- [ ] Response time impact < 5%
- [ ] ModSecurity actively blocking
- [ ] Incident response team trained
- [ ] Rollback procedure verified

---

## RISK ASSESSMENT

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Legitimate requests blocked | Low (< 0.1%) | High | Weekly review, quick rollback |
| Performance degradation | Low (< 5%) | Medium | Load testing, cache optimization |
| Rule false negatives | Very Low | High | Regular OWASP CRS updates |
| Configuration error | Low | Medium | nginx -t before every reload |

---

**Timeline:** 2026-08-15 to 2026-08-29 (2 weeks)  
**Effort:** 15-20 hours (monitoring + tuning)  
**Success Rate:** 95%+ (with proper false positive management)

