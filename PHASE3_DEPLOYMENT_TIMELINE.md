# Phase 3 Security Hardening — Deployment Timeline
**Start Date:** 2026-07-26 (Today)  
**Production Launch:** 2026-08-01 (Week 1 complete)  
**Full Completion:** 2026-08-31

---

## 📅 PRE-DEPLOYMENT (2026-07-26 to 2026-07-31) — 6 Days

### Day 1: 2026-07-26 (Today)
**Goal:** Staging environment + WAF rules validation

- [ ] **Backup production:**
  ```bash
  # nginx config backup
  sudo tar -czf /root/backups/nginx-$(date +%s).tar.gz /etc/nginx/
  # Database backup (if applicable)
  sudo mysqldump -u root -p --all-databases > /root/backups/db-full-$(date +%s).sql
  ```

- [ ] **Create staging nginx config:**
  ```bash
  sudo cp /etc/nginx/sites-available/bendernostur.duckdns.org \
         /etc/nginx/sites-available/bendernostur-staging.duckdns.org
  ```

- [ ] **Prepare ModSecurity installation package:**
  ```bash
  sudo apt-get install -y apt-transport-https lsb-release ca-certificates gnupg
  ```

- [ ] **Verify all security headers active (production):**
  ```bash
  curl -I https://bendernostur.duckdns.org:8443 | grep -E "Strict-Transport|X-Frame|X-Content-Type|X-XSS"
  ```

**Verification:** ✅ Backups created, staging blueprint ready, headers confirmed

---

### Day 2: 2026-07-27
**Goal:** ModSecurity staging + WAF rule testing

- [ ] **Install ModSecurity 3 + nginx connector (staging only):**
  ```bash
  sudo apt-get install -y modsecurity libmodsecurity3 nginx-module-modsecurity
  ```

- [ ] **Download & configure OWASP CRS:**
  ```bash
  cd /etc/nginx/modsec/
  git clone https://github.com/coreruleset/coreruleset.git
  cp coreruleset/crs-setup.conf.example crs-setup.conf
  ```

- [ ] **Enable core rules:**
  ```
  SecRuleEngine On
  SecRequestBodyLimit 13107200
  Include /etc/nginx/modsec/coreruleset/rules/*.conf
  ```

- [ ] **Start ModSecurity in detection mode:**
  ```bash
  SecAuditEngine On
  SecAuditLogType Serial
  ```

**Verification:** ✅ ModSecurity loaded, rules active, detection logging started

---

## 🚀 DEPLOYMENT WEEK (2026-08-01 to 2026-08-07)

### Phase 3.1: Staging → Production (Week 1)

| Task | Date | Owner | Status |
|------|------|-------|--------|
| Stop insite-api service | 2026-08-01 02:00 UTC | benderobo | ⏳ |
| Backup current nginx | 2026-08-01 02:05 UTC | benderobo | ⏳ |
| Install ModSecurity | 2026-08-01 02:10 UTC | benderobo | ⏳ |
| Load OWASP CRS rules | 2026-08-01 02:15 UTC | benderobo | ⏳ |
| Enable detection mode | 2026-08-01 02:20 UTC | benderobo | ⏳ |
| Test: Legitimate requests pass | 2026-08-01 02:30 UTC | benderobo | ⏳ |
| Monitor audit log (1 hour) | 2026-08-01 02:30-03:30 UTC | benderobo | ⏳ |
| Verify: HSTS header active | 2026-08-01 03:35 UTC | benderobo | ⏳ |

**Success Criteria:**
- 99.9%+ HTTP requests processed without error
- < 2 false positives per 10,000 requests
- Response time impact < 5%

---

### Phase 3.2: ELK Stack Deployment (Week 2)

| Date | Task | Duration |
|------|------|----------|
| 2026-08-08 | Docker Compose up | 30 min |
| 2026-08-09 | Kibana dashboards | 2 hours |
| 2026-08-11 | Test log ingestion | 1 hour |

**Success Criteria:**
- Logs flowing to Elasticsearch
- Kibana dashboards created
- Alerts configured

---

## 🎯 Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Security risk score | < 3% CVSS | 🟡 8% (after Phase 2) |
| Response time impact | < 5% | 🔵 TBD |
| False positive rate | < 0.02% | 🔵 TBD |
| MTTD (detection time) | < 5 min | 🔵 TBD |
| Attack blocking rate | > 95% | 🔵 TBD |
| Audit log coverage | 100% | 🟢 Active |

---

## 🚨 Rollback Plan

### If ModSecurity causes > 1% false positives:
1. Stop nginx: `sudo systemctl stop nginx`
2. Restore backup: `sudo cp /root/backups/nginx-TIMESTAMP.tar.gz /etc/nginx/`
3. Reload: `sudo systemctl start nginx`

---

**Status:** 🟡 **READY FOR EXECUTION**  
**Last Updated:** 2026-07-26  
**Next Review:** 2026-07-31 (24 hours before deployment)
