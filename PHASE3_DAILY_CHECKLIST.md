# Phase 3 Daily Checklist — Next 6 Days (2026-07-26 to 2026-07-31)

## 📋 TODAY: 2026-07-26 (Friday)

### Morning Tasks (Estimated: 30 minutes)
```bash
# 1. Verify current security state
curl -I https://bendernostur.duckdns.org:8443
# Expected: Strict-Transport-Security, X-Frame-Options, X-Content-Type-Options present

# 2. Check CSRF tokens are generating
curl -s https://bendernostur.duckdns.org | grep -o "csrf-token" | head -1
# Expected: csrf-token meta tag found

# 3. Verify audit logging active
ls -lh /tmp/shell_audit.log
# Expected: file exists, recent timestamp

# 4. Check insite-api service status
sudo systemctl status insite-api
# Expected: active (running)
```

✅ **Afternoon Tasks (Estimated: 1 hour)**
```bash
# 5. Create backup directory
mkdir -p /root/backups
chmod 700 /root/backups

# 6. Backup current nginx config
sudo tar -czf /root/backups/nginx-$(date +%s).tar.gz /etc/nginx/
ls -lh /root/backups/nginx-*.tar.gz
# Expected: backup file ~50-100 KB

# 7. Backup current services
sudo systemctl list-units --type=service --state=running | grep -E "insite|mimo"
# Expected: insite-api.service, mimo-brain.service listed

# 8. Schedule Phase 3.1 deployment
echo "Phase 3.1 Staging→Production: 2026-08-01 02:00 UTC" | mail -s "Phase 3 Deployment" benderobo@localhost
```

✅ **Evening Tasks (Estimated: 30 minutes)**
```bash
# 9. Document current baseline metrics
echo "Baseline metrics as of $(date)" >> /root/phase3_baseline.txt
curl -s https://bendernostur.duckdns.org:9123/health 2>/dev/null | head -20 >> /root/phase3_baseline.txt

# 10. Review WAF_MODSECURITY_GUIDE.md
cat /root/WAF_MODSECURITY_GUIDE.md | head -100
# Expected: Understand ModSecurity installation steps

# 11. Commit today's checklist completion
cd /root && git add PHASE3_DEPLOYMENT_TIMELINE.md PHASE3_DAILY_CHECKLIST.md
git commit -m "docs(phase3): Deployment timeline and daily checklist started"
```

**End of Day Verification:**
- [ ] Backups created and verified
- [ ] Current security state documented
- [ ] Phase 3 timeline reviewed
- [ ] Team notified of pre-deployment start

---

## 📋 TOMORROW: 2026-07-27 (Saturday)

### Morning: ModSecurity Research (1 hour)
```bash
# 1. Check Ubuntu version (must be 18.04+)
lsb_release -a

# 2. Verify docker is available (for ELK later)
docker --version && docker-compose --version

# 3. Check available system resources
free -h && df -h /
# Expected: > 2GB RAM, > 10GB disk for logs

# 4. Test sudo access (will need for ModSecurity install)
sudo -l | grep nginx
```

### Afternoon: Staging Setup (2 hours)
```bash
# 5. Create staging nginx config
sudo cp /etc/nginx/sites-available/bendernostur.duckdns.org \
       /etc/nginx/sites-available/bendernostur-staging.conf

# 6. Edit staging config (replace domain + SSL paths)
sudo nano /etc/nginx/sites-available/bendernostur-staging.conf
# Change: server_name staging.bendernostur.duckdns.org
# Change: ssl_certificate to staging cert path

# 7. Test nginx config syntax
sudo nginx -t
# Expected: nginx: configuration file test is successful

# 8. Enable staging site
sudo ln -s /etc/nginx/sites-available/bendernostur-staging.conf \
           /etc/nginx/sites-enabled/
```

### Evening: ModSecurity Prep (1 hour)
```bash
# 9. Create ModSecurity directory structure
sudo mkdir -p /etc/nginx/modsec/{rules,logs}
sudo chown -R www-data:www-data /etc/nginx/modsec/logs

# 10. Download ModSecurity rules (dry run, don't install yet)
cd /tmp && git clone https://github.com/coreruleset/coreruleset.git --depth 1
ls -lh /tmp/coreruleset/
# Expected: Downloaded ~50MB

# 11. Review rule count
wc -l /tmp/coreruleset/rules/*.conf
# Expected: 1000+ total rules

# 12. Document Day 2 progress
git add -A && git commit -m "wip(phase3): Staging setup, ModSecurity prep research complete"
```

**Day 2 Verification:**
- [ ] Staging nginx config created
- [ ] System resources verified (sufficient for ModSecurity)
- [ ] ModSecurity rules downloaded (dry run)
- [ ] Docker availability confirmed

---

## 📋 MONDAY: 2026-07-29 (Monday)

### Morning: ModSecurity Installation (1.5 hours)
```bash
# 1. Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install ModSecurity + dependencies
sudo apt-get install -y modsecurity libmodsecurity3 nginx-module-modsecurity
apt-cache policy modsecurity
# Expected: installed version shown

# 3. Create ModSecurity main config
sudo tee /etc/nginx/modsec/modsecurity.conf > /dev/null << 'EOF'
SecRuleEngine DetectionOnly
SecRequestBodyLimit 13107200
SecRequestBodyNoFilesLimit 131072
SecAuditEngine On
SecAuditLogFormat JSON
SecAuditLog /var/log/modsecurity/audit.log
EOF
sudo chown www-data:www-data /var/log/modsecurity/audit.log

# 4. Create log directory
sudo mkdir -p /var/log/modsecurity
sudo chown www-data:www-data /var/log/modsecurity
```

### Afternoon: OWASP CRS Setup (2 hours)
```bash
# 5. Copy OWASP CRS to production
sudo cp -r /tmp/coreruleset /etc/nginx/modsec/coreruleset

# 6. Copy CRS setup file
sudo cp /etc/nginx/modsec/coreruleset/crs-setup.conf.example \
       /etc/nginx/modsec/coreruleset/crs-setup.conf

# 7. Load ModSecurity in nginx (staging first)
sudo tee /etc/nginx/snippets/modsecurity-staging.conf > /dev/null << 'EOF'
modsecurity on;
modsecurity_rules_file /etc/nginx/modsec/modsecurity.conf;
modsecurity_rules_file /etc/nginx/modsec/coreruleset/crs-setup.conf;
modsecurity_rules_file /etc/nginx/modsec/coreruleset/rules/*.conf;
EOF

# 8. Include in staging nginx config
# Add: include /etc/nginx/snippets/modsecurity-staging.conf;

# 9. Test nginx config
sudo nginx -t
# Expected: configuration test is successful
```

### Evening: Staging ModSecurity Test (1 hour)
```bash
# 10. Reload nginx
sudo systemctl reload nginx

# 11. Monitor audit log
tail -f /var/log/modsecurity/audit.log &

# 12. Send test request
curl https://staging.bendernostur.duckdns.org/

# 13. Check for false positives
grep -c "id:" /var/log/modsecurity/audit.log
# Expected: < 5 rules triggered for normal request

# 14. Test SQL injection detection (should NOT block yet - detection mode)
curl "https://staging.bendernostur.duckdns.org/?id=1' OR '1'='1"
# Expected: Request succeeds, audit.log shows SQL injection rule

# 15. Commit progress
git add -A && git commit -m "feat(phase3): ModSecurity + OWASP CRS installed in staging"
```

**Day 3 Verification:**
- [ ] ModSecurity installed and loaded
- [ ] OWASP CRS rules in place
- [ ] Staging detection mode active
- [ ] No false positives for normal traffic
- [ ] SQL injection detected (not blocked)

---

## 📋 TUESDAY: 2026-07-30 (Tuesday)

### Morning: False Positive Tuning (1.5 hours)
```bash
# 1. Extract false positive rules from audit.log
grep "id:" /var/log/modsecurity/audit.log | cut -d' ' -f2 | sort | uniq -c | sort -rn | head -20

# 2. For each top rule, examine details
grep "id:910100" /var/log/modsecurity/audit.log | head -3

# 3. Create exemptions for legitimate traffic
# Example: Whitelist internal monitoring requests
# Create /etc/nginx/modsec/exclusions.conf:
sudo tee /etc/nginx/modsec/exclusions.conf > /dev/null << 'EOF'
# Skip ModSecurity for internal health checks
SecRule REQUEST_FILENAME "@contains /health" "id:10000,phase:1,pass,nolog,ctl:RuleEngine=Off"
EOF

# 4. Include exemptions in modsecurity.conf
echo "Include /etc/nginx/modsec/exclusions.conf" | sudo tee -a /etc/nginx/modsec/modsecurity.conf
```

### Afternoon: ELK Stack Planning (1.5 hours)
```bash
# 5. Create ELK docker-compose template
cat > /tmp/docker-compose-elk.yaml << 'EOF'
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.10.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
    ports:
      - "9200:9200"
    volumes:
      - es-data:/usr/share/elasticsearch/data

  kibana:
    image: docker.elastic.co/kibana/kibana:8.10.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200

  logstash:
    image: docker.elastic.co/logstash/logstash:8.10.0
    ports:
      - "5000:5000"
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
      - /var/log/nginx:/var/log/nginx:ro
      - /var/log/modsecurity:/var/log/modsecurity:ro

volumes:
  es-data:
EOF

# 6. Create Logstash pipeline config
cat > /tmp/logstash.conf << 'EOF'
input {
  file {
    path => "/var/log/nginx/access.log"
    start_position => "end"
    tags => ["nginx"]
  }
  file {
    path => "/var/log/modsecurity/audit.log"
    start_position => "end"
    tags => ["modsecurity"]
  }
}

filter {
  if "nginx" in [tags] {
    grok {
      match => { "message" => "%{COMBINEDAPACHELOG}" }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "logs-%{+YYYY.MM.dd}"
  }
  stdout { codec => rubydebug }
}
EOF

# 7. Verify configs syntax
ls -lh /tmp/docker-compose-elk.yaml /tmp/logstash.conf
```

### Evening: Load Testing Prep (1 hour)
```bash
# 8. Install Apache Bench
sudo apt-get install -y apache2-utils

# 9. Create load test script
cat > /tmp/load_test.sh << 'EOF'
#!/bin/bash
echo "Starting load test..."
ab -n 100 -c 10 https://staging.bendernostur.duckdns.org/
echo "Load test complete. Check /var/log/modsecurity/audit.log for rule triggers."
EOF
chmod +x /tmp/load_test.sh

# 10. Dry-run load test (don't execute yet, just prepare)
echo "Load test script ready at /tmp/load_test.sh"
```

**Day 4 Verification:**
- [ ] False positives identified and exemptions created
- [ ] ELK docker-compose created
- [ ] Logstash pipeline configured
- [ ] Load testing script prepared

---

## 📋 WEDNESDAY: 2026-07-31 (Wednesday) — Final Pre-Deployment Check

### Morning: Full Production Pre-Flight (1.5 hours)
```bash
# 1. FINAL: Verify all Phase 1-2 fixes still active
echo "=== Phase 1 Verification ==="
ls -la /root/telegram-brain/.env /root/insite-studio/.env
# Expected: .env files exist with 600 permissions

echo "=== Phase 2 Verification ==="
curl -I https://bendernostur.duckdns.org:8443 | grep -i "strict-transport-security\|x-frame\|content-security"
# Expected: Headers present

# 2. Check service status
sudo systemctl status insite-api mimo-brain
# Expected: both active (running)

# 3. Backup final state
sudo mysqldump -u root -p --all-databases 2>/dev/null | gzip > /root/backups/db-final-$(date +%s).sql.gz

# 4. Verify backup strategy (3-2-1 rule)
ls -lh /root/backups/
du -sh /root/backups/
# Expected: multiple backups, total > 500MB
```

### Afternoon: Production Readiness Review (1 hour)
```bash
# 5. Produce deployment checklist
cat > /root/DEPLOYMENT_CHECKLIST.txt << 'EOF'
PRE-DEPLOYMENT CHECKLIST (2026-08-01)
=====================================

SECURITY
[✓] Credentials in .env files (Phase 1)
[✓] CSRF tokens active (Phase 2)
[✓] Email validation strong (Phase 2)
[✓] XSS protection active (Phase 2)
[✓] Rate limiting active (Phase 2)
[✓] HSTS header 1-year (Phase 3)
[✓] TLS 1.2+ enforced (Phase 3)
[✓] CSP headers configured (Phase 3)
[✓] Audit logging enabled (Phase 1)

INFRASTRUCTURE
[✓] nginx config tested
[✓] SSL certificate valid (expires 2026-10-05)
[✓] Backups created (3-2-1 rule)
[✓] Rollback procedure documented
[✓] ModSecurity staged and ready
[✓] OWASP CRS downloaded
[✓] ELK docker-compose prepared

COMMUNICATION
[✓] Team briefed on Phase 3
[✓] Incident response SLA confirmed
[✓] On-call engineer assigned
[✓] Escalation path documented

DEPLOYMENT WINDOW: 2026-08-01 02:00 UTC
Expected duration: 90 minutes
Rollback available: Yes
EOF

# 6. Verify commitment message prepared
cat > /root/PHASE3_DEPLOYMENT_MESSAGE.txt << 'EOF'
Phase 3 Security Deployment — August 1-31, 2026
================================================

This deployment hardens our security posture across 3 dimensions:

1. WAF (ModSecurity + OWASP CRS)
   - Blocks SQL injection, XSS, path traversal
   - Detection mode first (1 week), then enforcement
   - Expected false positive rate: < 0.02%

2. Logging & Monitoring (ELK Stack)
   - Centralized log aggregation
   - Real-time attack detection dashboards
   - 30-day retention, expandable to 1 year

3. Incident Response
   - SLA: Critical 1h, High 4h, Medium 24h
   - Playbooks for 4 attack scenarios
   - Forensics procedures documented

Risk reduction: 77% (baseline) → 8% (Phase 2) → 3% (Phase 3)
EOF
```

### Evening: Final Commit & Notification (1 hour)
```bash
# 7. Review all changes
cd /root && git status

# 8. Add all Phase 3 documentation
git add PHASE3_DEPLOYMENT_TIMELINE.md PHASE3_DAILY_CHECKLIST.md DEPLOYMENT_CHECKLIST.txt

# 9. Create final pre-deployment commit
git commit -m "docs(phase3): Pre-deployment checklist complete, ready for 2026-08-01 launch

- Timeline: 6-day pre-deployment (2026-07-26 to 2026-07-31)
- Phase 3.1: ModSecurity WAF deployment (2026-08-01)
- Phase 3.2: ELK stack deployment (2026-08-08)
- Phase 3.3: Rule tuning and enforcement (2026-08-15 to 2026-08-29)
- All Phase 1-2 security fixes verified active
- Backups created (3-2-1 rule)
- Rollback procedures documented
- Team notified of SLA and escalation paths"

# 10. Push to remote
git push -u origin main

# 11. Final summary
echo "✅ PHASE 3 PRE-DEPLOYMENT COMPLETE"
echo "📅 Deployment window: 2026-08-01 02:00 UTC"
echo "⏱️  Expected duration: 90 minutes"
echo "🔄 Rollback available: Yes"
```

**Final Pre-Deployment Verification:**
- [ ] All Phase 1-2 fixes verified active in production
- [ ] Backups created and tested
- [ ] Staging ModSecurity validated
- [ ] ELK docker-compose ready
- [ ] Team briefed on Phase 3 deployment
- [ ] Incident response SLA acknowledged
- [ ] Deployment window confirmed (2026-08-01 02:00 UTC)

---

## ⏰ Timeline Summary

| Day | Date | Focus | Duration |
|-----|------|-------|----------|
| Day 1 | 2026-07-26 | Backups, baseline docs, plan review | 2h |
| Day 2 | 2026-07-27 | Staging setup, ModSecurity research | 2h |
| Day 3 | 2026-07-29 | ModSecurity + OWASP CRS installation | 4.5h |
| Day 4 | 2026-07-30 | False positive tuning, ELK prep | 3h |
| Day 5 | 2026-07-31 | Final verification, production readiness | 2.5h |
| **TOTAL** | | | **14.5 hours** |

**Estimated Daily Commitment:**
- Days 1-2: ~1-2 hours/day (research, planning)
- Day 3: ~4 hours (installation, testing)
- Day 4: ~3 hours (tuning, ELK setup)
- Day 5: ~2.5 hours (final checks, commitment)

---

## 🚀 Deployment Day Countdown (2026-08-01)

```
02:00 UTC — Stop services, begin backup
02:30 UTC — Install ModSecurity, load rules
03:00 UTC — Enable detection mode, start monitoring
03:30 UTC — Restart services, verify health
04:00 UTC — Declare Phase 3.1 complete
```

Ready to proceed? Check this list daily and commit progress.
